"""
deep_notes_ai/langgraph_pipeline/nodes/markdown/load_markdown.py

Node: load_markdown

Responsibility:
    Load a markdown document from either a local filesystem path or a remote
    URL, extract its metadata, determine the content-specific output
    directory, persist the raw markdown into that directory, initialize the
    processing context for downstream execution, and expose the resulting
    metadata.

This node represents the ingestion stage for Markdown-based sources. It is
responsible only for loading the source, extracting metadata, establishing the
content directory, persisting the original markdown, and initializing the
pipeline processing context. Parsing the markdown into a hierarchy/content
store and all subsequent processing are handled by downstream nodes.

Reads from state:
    source
    content_base_dir

Returns:
    {
        "metadata": MarkdownMetadata,
        "content_base_dir": Path,
        "current_run_dir": Path,
        "processing_context": ProcessingContext,
    }
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Callable

from deep_notes_ai.domain.models import (
    MarkdownLoadError,
    MarkdownMetadataError,
    ProcessingContext,
    TranscriptProcessingMode,
)
from deep_notes_ai.langgraph_pipeline.state import PipelineState
from deep_notes_ai.services.markdown.markdown_loader_service import (
    MarkdownLoaderService,
)
from deep_notes_ai.services.markdown.markdown_metadata_service import MarkdownMetadataService
from deep_notes_ai.services.persistence_service import PersistenceService

if TYPE_CHECKING:
    from deep_notes_ai.services.progress_service import ProgressService

logger = logging.getLogger(__name__)

_NODE = "load_markdown"
_STAGE = "Loading Markdown"


def make_load_markdown_node(
    markdown_loader_service: MarkdownLoaderService,
    markdown_metadata_service: MarkdownMetadataService,
    persistence_service: PersistenceService,
    progress_service: "ProgressService | None" = None,
) -> Callable[[PipelineState], dict]:
    """
    Factory that creates the load_markdown LangGraph node.
    """

    def load_markdown(
        state: PipelineState,
    ) -> dict:
        """
        Load markdown from either a local filesystem path or a remote URL,
        extract its metadata, create the content-specific output directory,
        persist the raw markdown, initialize the processing context, and
        return the metadata required by downstream nodes.

        Reads:
            state["source"]
            state["content_base_dir"]

        Returns:
            {
                "metadata": MarkdownMetadata,
                "content_base_dir": Path,
                "current_run_dir": Path,
                "processing_context": ProcessingContext,
            }

        Raises:
            MarkdownLoadError
            MarkdownMetadataError
        """
        source: str = state["source"]

        logger.info("Loading markdown source: %s", source)

        if progress_service is not None:
            progress_service.emit_start(node_name=_NODE, stage=_STAGE)

        try:
            markdown = markdown_loader_service.load(source)
            metadata = markdown_metadata_service.build_metadata(source=source, markdown=markdown)
        except MarkdownLoadError:
            if progress_service is not None:
                progress_service.emit_failed(
                    node_name=_NODE,
                    stage=_STAGE,
                    message="Failed to load markdown.",
                )
            raise
        except MarkdownMetadataError:
            if progress_service is not None:
                progress_service.emit_failed(
                    node_name=_NODE,
                    stage=_STAGE,
                    message="Failed to extract markdown metadata.",
                )
            raise

        base_dir = state["content_base_dir"]
        content_base_dir = base_dir / metadata.id
        current_run_dir = content_base_dir / "artifacts"
        content_path = current_run_dir / "raw_content.txt"

        if persistence_service.exists(content_path):
            logger.info("Markdown loaded (id = %s)and persisted: %s", metadata.id, content_path)
            persistence_service.clear_directory(current_run_dir)

        persistence_service.save_markdown(content_path, metadata.raw_content)

        logger.info("Markdown loaded (id = %s)and persisted: %s", metadata.id, content_path)

        if progress_service is not None:
            progress_service.emit_completed(
                node_name=_NODE,
                stage=_STAGE,
            )

        return {
            "metadata": metadata,
            "content_base_dir": content_base_dir,
            "current_run_dir": current_run_dir,
            "processing_context": ProcessingContext(
                    processing_mode=TranscriptProcessingMode.SINGLE,
                    current_part=2,
                    total_parts=1,
                    content_parts=[],
                ),
        }

    return load_markdown