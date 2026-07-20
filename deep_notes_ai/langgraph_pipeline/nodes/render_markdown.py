"""
deep_notes_ai/langgraph_pipeline/nodes/render_markdown.py

Node: render_markdown

Responsibility:
Load the processed transcript artefacts (single-part or multi-part), merge
them into one logical transcript, render the final markdown documents, and
persist them.

Reads from state:
    metadata
    processing_context
    content_base_dir

Calls:
    TranscriptMergeService.merge(...)
    MarkdownService.build_document(...)
    MarkdownService.build_readme(...)
    PersistenceService.save_markdown(...)

Returns:
    {
        "pipeline_complete": True,
    }

Error handling:
    Any merge/persistence failure is translated into PersistenceError and
    allowed to propagate to the graph-level error handling.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from deep_notes_ai.domain.models import (
    ContentMetadata,
    PersistenceError,
    ProcessingContext,
)
from deep_notes_ai.langgraph_pipeline.state import PipelineState
from deep_notes_ai.services.markdown_service import MarkdownService
from deep_notes_ai.services.persistence_service import PersistenceService
from deep_notes_ai.services.transcript_merge_service import (
    TranscriptMergeService,
)

if TYPE_CHECKING:
    from deep_notes_ai.services.progress_service import ProgressService

logger = logging.getLogger(__name__)

_NODE = "render_markdown"
_STAGE = "Rendering Markdown"


def make_render_markdown_node(
    markdown_service: MarkdownService,
    transcript_merge_service: TranscriptMergeService,
    persistence_service: PersistenceService,
    progress_service: "ProgressService | None" = None,
):
    """
    Factory that returns a render_markdown node.

    Args:
        markdown_service:
            Markdown renderer.

        transcript_merge_service:
            Service responsible for merging transcript-part artefacts.

        persistence_service:
            PersistenceService used for saving markdown files.

        progress_service:
            Optional ProgressService.

    Returns:
        LangGraph-compatible node callable.
    """

    def render_markdown(state: PipelineState) -> dict:
        """
        Render the final markdown documents.

        Reads:
            state["metadata"]
            state["processing_context"]
            state["content_base_dir"]

        Returns:
            {
                "pipeline_complete": True,
            }

        Raises:
            PersistenceError:
                If transcript artefacts cannot be loaded or markdown files
                cannot be written.
        """
        metadata: ContentMetadata = state["metadata"]
        processing_context: ProcessingContext = state["processing_context"]
        content_base_dir: Path = state["content_base_dir"]

        logger.info("Rendering final markdown documents.")

        if progress_service is not None:
            progress_service.emit_start(
                node_name=_NODE,
                stage=_STAGE,
            )

        # Merge transcript artefacts.
        logger.info("Loading processed transcript artefacts.")

        try:
            merged = transcript_merge_service.merge(
                processing_context=processing_context,
                content_base_dir=content_base_dir,
            )
        except Exception as exc:
            raise PersistenceError(
                f"Failed to merge transcript artefacts: {exc}"
            ) from exc

        logger.info(
            "Merged transcript successfully "
            "(hierarchy_nodes=%d, content_nodes=%d).",
            len(merged.hierarchy),
            len(merged.content_store),
        )

        # Render full content.
        logger.info("Rendering content markdown.")

        content_markdown = markdown_service.build_document(
            content_title=metadata.title,
            hierarchy=merged.hierarchy,
            content_store=merged.content_store,
            summary=False,
        )

        content_path = content_base_dir / "content.md"

        persistence_service.save_markdown(
            content_path,
            content_markdown,
        )

        logger.info(
            "Saved content markdown to %s",
            content_path,
        )

        # Render summaries.
        logger.info("Rendering summary markdown.")

        summary_markdown = markdown_service.build_document(
            content_title=metadata.title,
            hierarchy=merged.hierarchy,
            content_store=merged.content_store,
            summary=True,
        )

        summary_path = content_base_dir / "summary.md"

        persistence_service.save_markdown(
            summary_path,
            summary_markdown,
        )

        logger.info(
            "Saved summary markdown to %s",
            summary_path,
        )

        # Render README.
        logger.info("Rendering README.")

        readme_markdown = markdown_service.build_readme(
            content_title=metadata.title,
            content_id=metadata.id,
            author_name=metadata.author,
            upload_date=metadata.upload_date,
            content_url=metadata.url,
            hierarchy=merged.hierarchy,
        )

        readme_path = content_base_dir / "README.md"

        persistence_service.save_markdown(
            readme_path,
            readme_markdown,
        )

        logger.info(
            "Saved README markdown to %s",
            readme_path,
        )

        if progress_service is not None:
            progress_service.emit_completed(
                node_name=_NODE,
                stage=_STAGE,
            )

            progress_service.emit_info(
                node_name=_NODE,
                stage="Pipeline",
                message="Pipeline finished — notes ready.",
            )

        logger.info("Markdown rendering completed successfully.")

        return {
            "pipeline_complete": True,
        }

    return render_markdown