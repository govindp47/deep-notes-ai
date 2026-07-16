"""
deep_notes_ai/langgraph_pipeline/nodes/render_markdown.py

Node 10: render_markdown

Responsibility: Render the two final markdown documents (full content and
revision summaries).

Reads from state:
  - content_title: str
  - nodes_hierarchy: list[Node]
  - nodes_content: dict[str, ContentStoreItem]
  - current_run_dir: Path
  - content_id: str
Calls:
  - MarkdownService.build_document(..., summary=False) → content_md
  - MarkdownService.build_document(..., summary=True) → summary_md
  - PersistenceService.save_markdown(content_path, content_md)
  - PersistenceService.save_markdown(summary_path, summary_md)
Returns:
  {
    "content_md_path": Path,
    "summary_md_path": Path,
    "pipeline_complete": True,
  }
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from deep_notes_ai.domain.models import ContentStoreItem, Node
from deep_notes_ai.langgraph_pipeline.state import PipelineState
from deep_notes_ai.services.markdown_service import MarkdownService
from deep_notes_ai.services.persistence_service import PersistenceService

if TYPE_CHECKING:
    from deep_notes_ai.services.progress_service import ProgressService

logger = logging.getLogger(__name__)

_NODE = "render_markdown"
_STAGE = "Rendering Markdown"


def make_render_markdown_node(
    markdown_service: MarkdownService,
    persistence_service: PersistenceService,
    progress_service: "ProgressService | None" = None,
):
    """
    Factory that returns a render_markdown node bound to the given services.

    Args:
        markdown_service:    MarkdownService for building the documents.
        persistence_service: PersistenceService for saving the files.
        progress_service:    Optional ProgressService for user-facing progress.

    Returns:
        A callable compatible with LangGraph node interface.
    """

    def render_markdown(state: PipelineState) -> dict:
        """
        Render content and summary markdown documents, then save to disk.

        Reads:
            state["content_title"]: str
            state["nodes_hierarchy"]: list[Node]
            state["nodes_content"]: dict[str, ContentStoreItem]
            state["current_run_dir"]: Path
            state["content_id"]: str

        Returns:
            {
                "content_md_path": Path,
                "summary_md_path": Path,
                "pipeline_complete": True,
            }

        Raises:
            PersistenceError: if file writing fails.
        """
        content_title: str = state["content_title"]
        content_id: str = state["content_id"]
        author_name: str | None = state.get("author_name")
        upload_date: str | None = state.get("upload_date")
        content_url: str = state["content_url"]
        nodes_hierarchy: list[Node] = state["nodes_hierarchy"]
        nodes_content: dict[str, ContentStoreItem] = state["nodes_content"]
        run_dir: Path = state["current_run_dir"]

        logger.info("Rendering markdown documents.")

        if progress_service is not None:
            progress_service.emit_start(node_name=_NODE, stage=_STAGE)

        # Render full content document (summary=False).
        content_md = markdown_service.build_document(
            content_title=content_title,
            hierarchy=nodes_hierarchy,
            content_store=nodes_content,
            summary=False,
        )
        content_md_path = run_dir / "content.md"
        persistence_service.save_markdown(content_md_path, content_md)
        logger.info("Saved content markdown to %s", content_md_path)

        # Render revision summary document (summary=True).
        summary_md = markdown_service.build_document(
            content_title=content_title,
            hierarchy=nodes_hierarchy,
            content_store=nodes_content,
            summary=True,
        )
        summary_md_path = run_dir / "summary.md"
        persistence_service.save_markdown(summary_md_path, summary_md)
        logger.info("Saved summary markdown to %s", summary_md_path)

        # Render README document.
        readme_md = markdown_service.build_readme(
            content_title=content_title,
            content_id=content_id,
            author_name=author_name,
            upload_date=upload_date,
            content_url=content_url,
            hierarchy=nodes_hierarchy,
        )

        readme_path = run_dir / "README.md"
        persistence_service.save_markdown(readme_path, readme_md)
        logger.info("Saved README markdown to %s", readme_path)

        if progress_service is not None:
            progress_service.emit_completed(node_name=_NODE, stage=_STAGE)
            progress_service.emit_info(
                node_name=_NODE,
                stage="Pipeline",
                message="Pipeline finished — notes ready",
            )

        return {"pipeline_complete": True}

    return render_markdown
