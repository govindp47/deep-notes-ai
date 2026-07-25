"""
deep_notes_ai/langgraph_pipeline/graph.py

Graph Assembly — build and compile the LangGraph StateGraph pipeline.

This module wires all nodes, edges, and checkpointer together.

The compiled graph:
- Accepts an initial PipelineState dict.
- Runs all 10 processing nodes in sequence.
- Applies one conditional edge from validate_hierarchy.
- Attaches a checkpointer (MemorySaver or SqliteSaver based on settings).

Usage:
    graph = build_graph(settings)
    result = graph.invoke(initial_state, config={"configurable": {"thread_id": content_id}})
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from langchain_core.runnables import Runnable
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from deep_notes_ai.domain.models import SourceType, TranscriptProcessingMode, UnsupportedSourceTypeError
from deep_notes_ai.langgraph_pipeline.nodes.advance_transcript_part import make_advance_transcript_part_node
from deep_notes_ai.langgraph_pipeline.nodes.article.extract_article import make_extract_article_node
from deep_notes_ai.langgraph_pipeline.nodes.article.extract_article_metadata import make_extract_article_metadata_node
from deep_notes_ai.langgraph_pipeline.nodes.complete_transcript_part import make_complete_transcript_part_node
from deep_notes_ai.langgraph_pipeline.state import PipelineState
from deep_notes_ai.langgraph_pipeline.nodes.extract_video_metadata import (
    make_extract_video_metadata_node,
)
from deep_notes_ai.langgraph_pipeline.nodes.extract_transcript import (
    make_extract_transcript_node,
)
from deep_notes_ai.langgraph_pipeline.nodes.determine_processing_mode import (
    make_determine_processing_mode_node,
)
from deep_notes_ai.langgraph_pipeline.nodes.select_transcript_breakpoints import (
    make_select_transcript_breakpoints_node,
)
from deep_notes_ai.langgraph_pipeline.nodes.clean_transcript import (
    make_clean_transcript_node,
)
from deep_notes_ai.langgraph_pipeline.nodes.number_transcript import (
    make_number_transcript_node,
)
from deep_notes_ai.langgraph_pipeline.nodes.generate_hierarchy import (
    make_generate_hierarchy_node,
)
from deep_notes_ai.langgraph_pipeline.nodes.extract_content_nodes import (
    make_extract_content_nodes,
)
from deep_notes_ai.langgraph_pipeline.nodes.generate_content import (
    make_generate_content_node,
)
from deep_notes_ai.langgraph_pipeline.nodes.generate_summaries import (
    make_generate_summaries_node,
)
from deep_notes_ai.langgraph_pipeline.nodes.render_markdown import (
    make_render_markdown_node,
)
from deep_notes_ai.langgraph_pipeline.nodes.route_source import (
    make_route_source_node,
)
from deep_notes_ai.langgraph_pipeline.nodes.ingest_placeholders import (
    ingest_documentation,
    ingest_book,
    ingest_presentation,
)
from deep_notes_ai.services.article.article_download_service import ArticleDownloadService
from deep_notes_ai.services.article.article_extraction_service import ArticleExtractionService
from deep_notes_ai.services.article.article_metadata_service import ArticleMetadataService
from deep_notes_ai.services.article.markdown_structure_service import MarkdownStructureService
from deep_notes_ai.services.chapter_selection_service import ChapterSelectionService
from deep_notes_ai.services.transcript_merge_service import TranscriptMergeService
from deep_notes_ai.services.transcript_service import TranscriptService
from deep_notes_ai.services.video_metadata_service import VideoMetadataService
from deep_notes_ai.services.content_service import ContentService
from deep_notes_ai.services.llm_service import LLMService
from deep_notes_ai.services.llm_monitor_service import LLMMonitorService
from deep_notes_ai.services.markdown_service import MarkdownService
from deep_notes_ai.services.partition_service import PartitionService
from deep_notes_ai.services.persistence_service import PersistenceService
from deep_notes_ai.services.pricing_service import PricingService
from deep_notes_ai.services.progress_service import ProgressService
from deep_notes_ai.services.console_reporter import ConsoleReporter
from deep_notes_ai.services.prompt_service import PromptService
from deep_notes_ai.services.retry_service import RetryService
from deep_notes_ai.services.summary_service import SummaryService
from deep_notes_ai.services.tokenizer_service import TokenizerService
from deep_notes_ai.services.transcript_partition_service import TranscriptPartitionService

if TYPE_CHECKING:
    from deep_notes_ai.config.settings import Settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Node name constants (used in edges and test assertions)
# ---------------------------------------------------------------------------

NODE_ROUTE_SOURCE = "route_source"

NODE_EXTRACT_VIDEO_METADATA = "extract_video_metadata"
NODE_EXTRACT_TRANSCRIPT = "extract_transcript"

NODE_EXTRACT_ARTICLE_METADATA = "extract_article_metadata"
NODE_EXTRACT_ARTICLE = "extract_article"

NODE_INGEST_DOCUMENTATION = "ingest_documentation"
NODE_INGEST_BOOK = "ingest_book"
NODE_INGEST_PRESENTATION = "ingest_presentation"

NODE_DETERMINE_PROCESSING_MODE = "determine_processing_mode"
NODE_SELECT_TRANSCRIPT_BREAKPOINTS = "select_transcript_breakpoints"
NODE_ADVANCE_TRANSCRIPT_PART = "advance_transcript_part"

NODE_CLEAN_TRANSCRIPT = "clean_transcript"
NODE_CLEAN_ARTICLE = "clean_article"
NODE_NUMBER_TRANSCRIPT = "number_transcript"
NODE_GENERATE_HIERARCHY = "generate_hierarchy"
NODE_EXTRACT_CONTENT_NODES = "extract_content_nodes"
NODE_GENERATE_CONTENT = "generate_content"
NODE_GENERATE_SUMMARIES = "generate_summaries"

NODE_COMPLETE_TRANSCRIPT_PART = "complete_transcript_part"
NODE_RENDER_MARKDOWN = "render_markdown"

NODE_HIERARCHY_VALIDATION_FAILED = "hierarchy_validation_failed"
NODE_INVALID_TRANSCRIPT_BREAKDOWN = "invalid_transcript_breakdown"


# ---------------------------------------------------------------------------
# Terminal error node
# ---------------------------------------------------------------------------

def make_hierarchy_validation_failed_node(progress_service: ProgressService | None = None):
    def hierarchy_validation_failed(state: PipelineState) -> dict:
        """
        Terminal error node reached when the hierarchy has zero CONTENT nodes.

        Sets pipeline_complete=False and records an error message.
        """
        content_count = state.get("content_node_count", 0)
        msg = (
            f"Hierarchy validation failed: found {content_count} CONTENT node(s). "
            "At least one CONTENT node is required."
        )
        logger.error(msg)
        if progress_service is not None:
            progress_service.emit_failed(
                node_name=NODE_HIERARCHY_VALIDATION_FAILED,
                stage="Hierarchy Validation",
                message=msg,
            )
        return {
            "pipeline_complete": False,
            "error_message": msg,
        }
    return hierarchy_validation_failed

def make_invalid_transcript_breakdown_node(progress_service: ProgressService | None = None):
    """
    Factory for the terminal node reached when the transcript cannot be
    partitioned into valid parts using the user-selected breakpoints.
    """

    def invalid_transcript_breakdown(state: PipelineState) -> dict:
        """
        Terminal error node reached when no valid transcript partitioning is
        possible.

        This occurs when one or more transcript parts still exceed the
        configured maximum token limit after applying all user-selected
        breakpoints.

        Returns:
            Pipeline state update marking the pipeline as failed.
        """
        error_msg = state.get("error_message") or (
            "Unable to split the transcript into valid parts. "
            "One or more transcript parts still exceed the configured "
            "maximum token limit. Please choose additional breakpoints "
            "or reduce the maximum token limit."
        )
        logger.error(error_msg)
        if progress_service is not None:
            progress_service.emit_failed(
                node_name=NODE_INVALID_TRANSCRIPT_BREAKDOWN,
                stage="Transcript Partitioning",
                message=error_msg,
            )
        return {
            "pipeline_complete": False,
            "error_message": error_msg,
        }
    return invalid_transcript_breakdown


# ---------------------------------------------------------------------------
# Conditional edge router
# ---------------------------------------------------------------------------

def determine_source_route(state: PipelineState) -> str:
    """
    Determine the next node based on source_type.
    """
    source_type = state.get("source_type")
    
    if source_type == SourceType.YOUTUBE:
        return NODE_EXTRACT_VIDEO_METADATA
    elif source_type == SourceType.ARTICLE:
        return NODE_EXTRACT_ARTICLE_METADATA
    elif source_type == SourceType.DOCUMENTATION:
        return NODE_INGEST_DOCUMENTATION
    elif source_type == SourceType.BOOK:
        return NODE_INGEST_BOOK
    elif source_type == SourceType.PRESENTATION:
        return NODE_INGEST_PRESENTATION
    
    # Fallback, though route_source node should have caught this.
    raise UnsupportedSourceTypeError(f"Unsupported route for source type: {source_type}")

def route_after_determine_mode(state: PipelineState) -> str:
    """
    Conditional router executed after determine_processing_mode.

    Routes:
        NODE_ADVANCE_TRANSCRIPT_PART
            Transcript fits within the configured token limit and can be
            processed as a single part.

        NODE_SELECT_TRANSCRIPT_BREAKPOINTS
            Transcript exceeds the configured token limit and requires the
            user to select transcript breakpoints before processing.
    """
    mode = state["processing_context"].processing_mode

    if mode == TranscriptProcessingMode.MULTI_PART:
        return NODE_SELECT_TRANSCRIPT_BREAKPOINTS

    return NODE_ADVANCE_TRANSCRIPT_PART

def route_after_select_breakpoints(state: PipelineState) -> str:
    """
    Conditional edge router called after select_transcript_breakpoints.

    Routes:
        NODE_ADVANCE_TRANSCRIPT_PART
            User-selected breakpoints produced a valid transcript partitioning.

        NODE_INVALID_TRANSCRIPT_BREAKDOWN
            No valid transcript partitioning could be created. At least one
            resulting transcript part still exceeds the configured maximum
            token limit.
    """
    total_parts = state["processing_context"].total_parts

    if total_parts <= 0:
        return NODE_INVALID_TRANSCRIPT_BREAKDOWN

    return NODE_ADVANCE_TRANSCRIPT_PART

def route_after_complete_transcript_part(state: PipelineState) -> str:
    """
    Conditional edge router called after complete_transcript_part.

    Returns:
        "advance_transcript_part"   — additional transcript parts remain.
        "render_markdown"    — all transcript parts have been processed.
    """
    processing_context = state["processing_context"]

    if (processing_context.processing_mode == TranscriptProcessingMode.SINGLE):
        return NODE_RENDER_MARKDOWN

    current_part = processing_context.current_part
    total_parts = processing_context.total_parts

    if current_part > total_parts:
        return NODE_RENDER_MARKDOWN

    return NODE_ADVANCE_TRANSCRIPT_PART

def route_after_advance_transcript_part(state: PipelineState) -> str:
    """
    Route to the appropriate cleaner based on the source type.
    """
    source_type: SourceType = state.get("source_type")

    if source_type == SourceType.YOUTUBE:
        return NODE_CLEAN_TRANSCRIPT
    elif source_type == SourceType.ARTICLE:
        return NODE_CLEAN_ARTICLE

    raise ValueError(f"Unsupported source_type: {source_type!r}")

def route_after_validation(state: PipelineState) -> str:
    """
    Route based on hierarchy_valid flag.

    Returns:
        "extract_content_nodes" if valid.
        "hierarchy_validation_failed" if invalid.
    """
    if state.get("content_node_count", 0) > 0:
        return NODE_EXTRACT_CONTENT_NODES
    return NODE_HIERARCHY_VALIDATION_FAILED


# ---------------------------------------------------------------------------
# Graph builder
# ---------------------------------------------------------------------------

def build_graph(settings: "Settings") -> tuple:
    """
    Build and compile the deep-notes-ai LangGraph pipeline.

    Constructs all services from the Settings, wires all processing nodes,
    adds edges (including conditional edges for single/multi-part routing and
    the hierarchy validation branch), and attaches a checkpointer.

    Args:
        settings: Application settings (injected).

    Returns:
        A 2-tuple of (compiled_graph, llm_monitor_service).
        Call ``llm_monitor_service.save_reports(run_dir)`` after the graph
        completes to persist llm_usage.json and llm_usage.md.
        llm_monitor_service is None when enable_llm_monitoring=False.
    """
    logger.info("Building pipeline graph")

    # ── Service construction ─────────────────────────────────────────────────
    persistence_service = PersistenceService()
    video_metadata_service = VideoMetadataService()
    prompt_service = PromptService(settings.prompts_dir)
    partition_service = PartitionService()
    transcript_cleaning_tokenizer_service = TokenizerService(settings.transcript_cleaning_model_name)
    article_cleaning_tokenizer_service = TokenizerService(settings.article_cleaning_model_name)
    hierarchy_tokenizer_service = TokenizerService(settings.hierarchy_model_name)
    content_tokenizer_service = TokenizerService(settings.content_model_name)
    summary_tokenizer_service = TokenizerService(settings.summary_model_name)
    # Reuse the cleaning tokenizer as the canonical transcript size counter.
    transcript_tokenizer_service = transcript_cleaning_tokenizer_service
    transcript_service = TranscriptService(
        tokenizer_service=transcript_tokenizer_service
    )
    validation_service = _make_validation_service()
    retry_service = RetryService(max_retries=settings.max_retries)
    markdown_service = MarkdownService()
    partition_service_transcript = TranscriptPartitionService(max_tokens_per_part=settings.transcript_max_tokens_per_part)
    chapter_selection_service = ChapterSelectionService(max_tokens_per_part=settings.transcript_max_tokens_per_part)
    transcript_merge_service = TranscriptMergeService(persistence_service=persistence_service)
    article_download_service = ArticleDownloadService(settings=settings)
    article_metadata_service = ArticleMetadataService()
    markdown_structure_service = MarkdownStructureService()
    article_tokenizer_service = article_cleaning_tokenizer_service
    article_extraction_service = ArticleExtractionService(
        markdown_structure_service=markdown_structure_service,
        tokenizer_service=article_tokenizer_service
    )

    # ── Monitoring & Progress services ───────────────────────────────────────
    pricing_service = PricingService()
    monitor_service: LLMMonitorService | None = None
    if settings.enable_llm_monitoring:
        monitor_service = LLMMonitorService(
            pricing_service=pricing_service,
            persistence_service=persistence_service,
        )
        logger.info("LLM monitoring enabled.")
    else:
        logger.info("LLM monitoring disabled.")

    console_reporter = ConsoleReporter()
    progress_service = ProgressService(reporters=[console_reporter])

    llm_service = LLMService(settings, monitor_service=monitor_service)

    # ── LLM chains ──────────────────────────────────────────────────────────
    # Node 2: cleaning chain
    transcript_cleaning_prompt = prompt_service.load("yt_transcript_cleaner")
    transcript_cleaning_model = llm_service.get_chat_model(
        provider=settings.transcript_cleaning_model_provider,
        model=settings.transcript_cleaning_model_name,
        temperature=settings.transcript_cleaning_model_temperature,
        node_name=NODE_CLEAN_TRANSCRIPT,
        operation_name="Transcript Cleaning",
    )
    transcript_cleaning_chain: Runnable = transcript_cleaning_prompt | transcript_cleaning_model

    article_cleaning_prompt = prompt_service.load("article_cleaner")
    article_cleaning_model = llm_service.get_chat_model(
        provider=settings.article_cleaning_model_provider,
        model=settings.article_cleaning_model_name,
        temperature=settings.article_cleaning_model_temperature,
        node_name=NODE_CLEAN_ARTICLE,
        operation_name="Article Cleaning",
    )
    article_cleaning_chain: Runnable = article_cleaning_prompt | article_cleaning_model

    # Node 4: hierarchy chain (structured output)
    from deep_notes_ai.domain.models import TranscriptHierarchy
    hierarchy_prompt = prompt_service.load("hierarchy_extractor")
    hierarchy_model = llm_service.get_structured_model(
        provider=settings.hierarchy_model_provider,
        model=settings.hierarchy_model_name,
        output_schema=TranscriptHierarchy,
        temperature=settings.hierarchy_model_temperature,
        node_name=NODE_GENERATE_HIERARCHY,
        operation_name="Hierarchy Generation",
    )
    hierarchy_chain: Runnable = hierarchy_prompt | hierarchy_model

    # Node 7: content chain (structured output)
    from deep_notes_ai.domain.models import StructuredContentBatch
    content_prompt = prompt_service.load("content_structurer")
    content_model = llm_service.get_structured_model(
        provider=settings.content_model_provider,
        model=settings.content_model_name,
        output_schema=StructuredContentBatch,
        temperature=settings.content_model_temperature,
        node_name=NODE_GENERATE_CONTENT,
        operation_name="Content Generation",
    )
    content_chain: Runnable = content_prompt | content_model

    # Node 8: summary chain (structured output)
    from deep_notes_ai.domain.models import ContentSummaryBatch
    summary_prompt = prompt_service.load("content_summarizer")
    summary_model = llm_service.get_structured_model(
        provider=settings.summary_model_provider,
        model=settings.summary_model_name,
        output_schema=ContentSummaryBatch,
        temperature=settings.summary_model_temperature,
        node_name=NODE_GENERATE_SUMMARIES,
        operation_name="Summary Generation",
    )
    summary_chain: Runnable = summary_prompt | summary_model

    # ── Service instances ────────────────────────────────────────────────────
    content_service = ContentService(
        llm_chain=content_chain,
        partition_service=partition_service,
        validation_service=validation_service,
        retry_service=retry_service,
        progress_service=progress_service,
    )
    summary_service = SummaryService(
        llm_chain=summary_chain,
        partition_service=partition_service,
        validation_service=validation_service,
        retry_service=retry_service,
        progress_service=progress_service,
    )

    # ── Node callables ───────────────────────────────────────────────────────
    route_source_node = make_route_source_node(settings.output_base_dir)
    extract_video_metadata_node = make_extract_video_metadata_node(
        service=video_metadata_service, 
        progress_service=progress_service,
    )
    extract_transcript_node = make_extract_transcript_node(
        transcript_service=transcript_service,
        progress_service=progress_service,
    )
    extract_article_metadata_node = make_extract_article_metadata_node(
        article_download_service=article_download_service,
        article_metadata_service=article_metadata_service,
        progress_service=progress_service,
    )
    extract_article_node = make_extract_article_node(
        article_extraction_service=article_extraction_service,
        progress_service=progress_service,
    )
    determine_processing_mode_node = make_determine_processing_mode_node(
        max_tokens_per_part=settings.transcript_max_tokens_per_part,
        progress_service=progress_service,
    )
    select_transcript_breakpoints_node = make_select_transcript_breakpoints_node(
        chapter_selection_service=chapter_selection_service,
        partition_service=partition_service_transcript,
        progress_service=progress_service,
    )
    advance_transcript_part_node = make_advance_transcript_part_node(
        persistence_service=persistence_service,
        progress_service=progress_service
    )
    clean_transcript_node = make_clean_transcript_node(
        llm_chain=transcript_cleaning_chain,
        persistence_service=persistence_service,
        tokenizer_service=transcript_cleaning_tokenizer_service,
        chunk_tokens=settings.transcript_cleaning_chunk_tokens,
        overlap_chars=settings.transcript_cleaning_chunk_overlap_chars,
        progress_service=progress_service,
    )
    clean_article_node = make_clean_transcript_node(
        llm_chain=article_cleaning_chain,
        persistence_service=persistence_service,
        tokenizer_service=article_cleaning_tokenizer_service,
        chunk_tokens=settings.article_cleaning_chunk_tokens,
        overlap_chars=settings.article_cleaning_chunk_overlap_chars,
        progress_service=progress_service,
    )
    number_transcript_node = make_number_transcript_node(persistence_service, progress_service)
    generate_hierarchy_node = make_generate_hierarchy_node(
        llm_chain=hierarchy_chain,
        persistence_service=persistence_service,
        tokenizer_service=hierarchy_tokenizer_service,
        ideal_input_tokens=settings.hierarchy_input_tokens,
        progress_service=progress_service
    )
    extract_content_nodes = make_extract_content_nodes(persistence_service, progress_service)
    generate_content_node = make_generate_content_node(
        content_service=content_service,
        persistence_service=persistence_service,
        tokenizer_service=content_tokenizer_service,
        ideal_input_tokens=settings.content_input_tokens,
        input_tokens_fallback=settings.content_input_tokens_fallback,
        progress_service=progress_service
    )
    generate_summaries_node = make_generate_summaries_node(
        summary_service=summary_service,
        persistence_service=persistence_service,
        tokenizer_service=summary_tokenizer_service,
        ideal_input_tokens=settings.summary_input_tokens,
        input_tokens_fallback=settings.summary_input_tokens_fallback,
        progress_service=progress_service
    )
    complete_transcript_part_node = make_complete_transcript_part_node(progress_service=progress_service)
    render_markdown_node = make_render_markdown_node(
        markdown_service=markdown_service,
        transcript_merge_service=transcript_merge_service,
        persistence_service=persistence_service,
        progress_service=progress_service
    )
    hierarchy_validation_failed_node = make_hierarchy_validation_failed_node(progress_service)
    invalid_transcript_breakdown_node = make_invalid_transcript_breakdown_node(progress_service)

    # ── Graph construction ───────────────────────────────────────────────────
    graph = StateGraph(PipelineState)

    # Register nodes
    graph.add_node(NODE_ROUTE_SOURCE, route_source_node)

    graph.add_node(NODE_EXTRACT_VIDEO_METADATA, extract_video_metadata_node)
    graph.add_node(NODE_EXTRACT_TRANSCRIPT, extract_transcript_node)

    graph.add_node(NODE_EXTRACT_ARTICLE_METADATA, extract_article_metadata_node)
    graph.add_node(NODE_EXTRACT_ARTICLE, extract_article_node)

    graph.add_node(NODE_INGEST_DOCUMENTATION, ingest_documentation)
    graph.add_node(NODE_INGEST_BOOK, ingest_book)
    graph.add_node(NODE_INGEST_PRESENTATION, ingest_presentation)

    graph.add_node(NODE_DETERMINE_PROCESSING_MODE, determine_processing_mode_node)
    graph.add_node(NODE_SELECT_TRANSCRIPT_BREAKPOINTS, select_transcript_breakpoints_node)
    graph.add_node(NODE_ADVANCE_TRANSCRIPT_PART, advance_transcript_part_node)

    graph.add_node(NODE_CLEAN_TRANSCRIPT, clean_transcript_node)
    graph.add_node(NODE_CLEAN_ARTICLE, clean_article_node)
    graph.add_node(NODE_NUMBER_TRANSCRIPT, number_transcript_node)
    graph.add_node(NODE_GENERATE_HIERARCHY, generate_hierarchy_node)
    graph.add_node(NODE_EXTRACT_CONTENT_NODES, extract_content_nodes)
    graph.add_node(NODE_GENERATE_CONTENT, generate_content_node)
    graph.add_node(NODE_GENERATE_SUMMARIES, generate_summaries_node)

    graph.add_node(NODE_COMPLETE_TRANSCRIPT_PART, complete_transcript_part_node)
    graph.add_node(NODE_RENDER_MARKDOWN, render_markdown_node)

    graph.add_node(NODE_HIERARCHY_VALIDATION_FAILED, hierarchy_validation_failed_node)
    graph.add_node(NODE_INVALID_TRANSCRIPT_BREAKDOWN, invalid_transcript_breakdown_node)

    # ── Routing ──────────────────────────────────────────────────────────────
    graph.add_edge(START, NODE_ROUTE_SOURCE)

    graph.add_conditional_edges(
        NODE_ROUTE_SOURCE,
        determine_source_route,
        {
            NODE_EXTRACT_VIDEO_METADATA: NODE_EXTRACT_VIDEO_METADATA,
            NODE_EXTRACT_ARTICLE_METADATA: NODE_EXTRACT_ARTICLE_METADATA,
            NODE_INGEST_DOCUMENTATION: NODE_INGEST_DOCUMENTATION,
            NODE_INGEST_BOOK: NODE_INGEST_BOOK,
            NODE_INGEST_PRESENTATION: NODE_INGEST_PRESENTATION,
        },
    )

    # Ingestion branches converging on END
    graph.add_edge(NODE_INGEST_DOCUMENTATION, END)
    graph.add_edge(NODE_INGEST_BOOK, END)
    graph.add_edge(NODE_INGEST_PRESENTATION, END)

    # ── YouTube path: metadata → transcript → token count → mode decision ────
    graph.add_edge(NODE_EXTRACT_VIDEO_METADATA, NODE_EXTRACT_TRANSCRIPT)
    graph.add_edge(NODE_EXTRACT_TRANSCRIPT, NODE_DETERMINE_PROCESSING_MODE)

    # ── Article path ────
    graph.add_edge(NODE_EXTRACT_ARTICLE_METADATA, NODE_EXTRACT_ARTICLE)
    graph.add_edge(NODE_EXTRACT_ARTICLE, NODE_DETERMINE_PROCESSING_MODE)

    # After mode determination
    graph.add_conditional_edges(
        NODE_DETERMINE_PROCESSING_MODE,
        route_after_determine_mode,
        {
            NODE_ADVANCE_TRANSCRIPT_PART: NODE_ADVANCE_TRANSCRIPT_PART,
            NODE_SELECT_TRANSCRIPT_BREAKPOINTS: NODE_SELECT_TRANSCRIPT_BREAKPOINTS,
        },
    )
    graph.add_conditional_edges(
        NODE_SELECT_TRANSCRIPT_BREAKPOINTS,
        route_after_select_breakpoints,
        {
            NODE_ADVANCE_TRANSCRIPT_PART: NODE_ADVANCE_TRANSCRIPT_PART,
            NODE_INVALID_TRANSCRIPT_BREAKDOWN: NODE_INVALID_TRANSCRIPT_BREAKDOWN,
        },
    )

    graph.add_conditional_edges(
        NODE_ADVANCE_TRANSCRIPT_PART,
        route_after_advance_transcript_part,
        {
            NODE_CLEAN_TRANSCRIPT: NODE_CLEAN_TRANSCRIPT,
            NODE_CLEAN_ARTICLE: NODE_CLEAN_ARTICLE,
        },
    )
    graph.add_edge(NODE_CLEAN_TRANSCRIPT, NODE_NUMBER_TRANSCRIPT)
    graph.add_edge(NODE_CLEAN_ARTICLE, NODE_NUMBER_TRANSCRIPT)
    graph.add_edge(NODE_NUMBER_TRANSCRIPT, NODE_GENERATE_HIERARCHY)
    graph.add_conditional_edges(
        NODE_GENERATE_HIERARCHY,
        route_after_validation,
        {
            NODE_EXTRACT_CONTENT_NODES: NODE_EXTRACT_CONTENT_NODES,
            NODE_HIERARCHY_VALIDATION_FAILED: NODE_HIERARCHY_VALIDATION_FAILED,
        },
    )
    graph.add_edge(NODE_EXTRACT_CONTENT_NODES, NODE_GENERATE_CONTENT)
    graph.add_edge(NODE_GENERATE_CONTENT, NODE_GENERATE_SUMMARIES)
    graph.add_edge(NODE_GENERATE_SUMMARIES, NODE_COMPLETE_TRANSCRIPT_PART)

    graph.add_conditional_edges(
        NODE_COMPLETE_TRANSCRIPT_PART,
        route_after_complete_transcript_part,
        {
            NODE_ADVANCE_TRANSCRIPT_PART: NODE_ADVANCE_TRANSCRIPT_PART,
            NODE_RENDER_MARKDOWN: NODE_RENDER_MARKDOWN,
        },
    )

    graph.add_edge(NODE_INVALID_TRANSCRIPT_BREAKDOWN, END)
    graph.add_edge(NODE_RENDER_MARKDOWN, END)
    graph.add_edge(NODE_HIERARCHY_VALIDATION_FAILED, END)

    # ── Checkpointer ─────────────────────────────────────────────────────────
    checkpointer = _build_checkpointer(settings)

    # interrupt_before is used so LangGraph checkpoints state before the
    # interrupt node executes, enabling clean resume via Command(resume=...).
    compiled = graph.compile(
        checkpointer=checkpointer,
    )
    logger.info(
        "Graph compiled with %s checkpointer",
        type(checkpointer).__name__,
    )
    return compiled, monitor_service


def _make_validation_service():
    """Construct a ValidationService instance."""
    from deep_notes_ai.services.validation_service import ValidationService
    return ValidationService()


def _build_checkpointer(settings: "Settings"):
    """
    Build the appropriate checkpointer based on settings.

    Uses SqliteSaver when use_sqlite_checkpointer=True and the package is
    available. Falls back to MemorySaver otherwise.
    """
    if settings.use_sqlite_checkpointer:
        try:
            from langgraph.checkpoint.sqlite import SqliteSaver
            settings.checkpoints_db.parent.mkdir(parents=True, exist_ok=True)
            checkpointer = SqliteSaver.from_conn_string(
                str(settings.checkpoints_db)
            )
            logger.info(
                "Using SqliteSaver checkpointer at %s", settings.checkpoints_db
            )
            return checkpointer
        except ImportError:
            logger.warning(
                "langgraph-checkpoint-sqlite not installed; "
                "falling back to MemorySaver. "
                "Install langgraph-checkpoint-sqlite for persistent checkpoints."
            )

    logger.info("Using MemorySaver checkpointer (in-process only)")
    return MemorySaver()
