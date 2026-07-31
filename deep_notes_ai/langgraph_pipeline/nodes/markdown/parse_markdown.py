"""
deep_notes_ai/langgraph_pipeline/nodes/markdown/parse_markdown.py

Node: parse_markdown

Responsibility:
    Parse markdown stored in metadata.raw_content into a Node hierarchy and
    content store, generate content payloads from the reconstructed hierarchy,
    persist the generated artifacts, and return them for downstream nodes.

Reads from state:
    metadata
    current_run_dir

Returns:
    {
        "content_node_count": int,
        "content_payload": list[ContentPayload],
        "nodes_content": dict[str, ContentStoreItem],
        "nodes_hierarchy": list[Node],
    }

Raises:
    MarkdownParseError
    ContentNodeCountMismatchError
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from deep_notes_ai.domain.algorithms import build_content_payloads_from_hierarchy, rebuild_content_payloads
from deep_notes_ai.domain.models import (
    ContentNodeCountMismatchError,
    HierarchyMismatchError,
    MarkdownMetadata,
    MarkdownParseError,
)
from deep_notes_ai.langgraph_pipeline.state import PipelineState
from deep_notes_ai.services.markdown.markdown_parser_service import (
    MarkdownParserService,
)
from deep_notes_ai.services.persistence_service import PersistenceService

if TYPE_CHECKING:
    from deep_notes_ai.services.progress_service import ProgressService

logger = logging.getLogger(__name__)

_NODE = "parse_markdown"
_STAGE = "Parsing Markdown"


def make_parse_markdown_node(
    markdown_parser_service: MarkdownParserService,
    persistence_service: PersistenceService,
    progress_service: "ProgressService | None" = None,
):
    """
    Factory that creates the parse_markdown LangGraph node.
    """

    def parse_markdown(
        state: PipelineState,
    ) -> dict:
        """
        Parse markdown into a Node hierarchy and content store, generate
        content payloads from the reconstructed hierarchy, persist the
        generated artifacts, and return them.

        Reads:
            state["metadata"]
            state["current_run_dir"]

        Returns:
            {
                "content_node_count": int,
                "content_payload": list[ContentPayload],
                "nodes_content": dict[str, ContentStoreItem],
                "nodes_hierarchy": list[Node],
            }

        Raises:
            MarkdownParseError
            ContentNodeCountMismatchError
        """
        metadata: MarkdownMetadata = state["metadata"]
        current_run_dir: Path = state["current_run_dir"]

        nodes_hierarchy_path = current_run_dir / "nodes_hierarchy.json"
        nodes_content_path = current_run_dir / "nodes_content.json"

        logger.info("Parsing markdown into node hierarchy")

        if progress_service is not None:
            progress_service.emit_start(node_name=_NODE, stage=_STAGE)

        try:
            nodes_hierarchy, nodes_content = markdown_parser_service.parse_document(metadata.raw_content)
        except Exception as exc:
            if progress_service is not None:
                progress_service.emit_failed(
                    node_name=_NODE,
                    stage=_STAGE,
                    message="Failed to parse markdown.",
                )
            raise MarkdownParseError("Failed to parse markdown.") from exc
        
        logger.info("building content payload from hierarchy.")

        try:
            content_payload = build_content_payloads_from_hierarchy(hierarchy=nodes_hierarchy)
        except HierarchyMismatchError as exc:
            if progress_service is not None:
                progress_service.emit_failed(
                    node_name=_NODE,
                    stage=_STAGE,
                    message="Failed to build content payload.",
                )
            raise MarkdownParseError("Failed to build content payload.") from exc
        
        content_node_count: int = len(nodes_content)

        if len(content_payload) != content_node_count:
            raise ContentNodeCountMismatchError(
                "Content payload generation produced an unexpected number of "
                f"content nodes. Expected {content_node_count}, got {len(content_payload)}."
            )
        
        persistence_service.save_nodes_hierarchy(nodes_hierarchy_path, nodes_hierarchy)
        persistence_service.save_nodes_content(nodes_content_path, nodes_content)

        logger.info("Parsed markdown into %d content nodes", content_node_count)

        if progress_service is not None:
            progress_service.emit_completed(node_name=_NODE, stage=_STAGE)

        return {
            "content_node_count": content_node_count,
            "content_payload": content_payload,
            "nodes_content": nodes_content,
            "nodes_hierarchy": nodes_hierarchy,
        }

    return parse_markdown