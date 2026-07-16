"""
deep_notes_ai/langgraph_pipeline/nodes/extract_content_nodes.py

Node 6: extract_content_nodes

Responsibility: Extract all CONTENT leaf nodes, build UUID-keyed metadata,
build lightweight Node hierarchy, build ContentPayload list.

Reads from state: raw_hierarchy, content_points_list
Calls: algorithms.build_content_payloads(raw_hierarchy.hierarchy, content_points_list)
Returns:
  {
    "content_payload": list[ContentPayload],
    "nodes_content": dict[str, ContentStoreItem],
    "nodes_hierarchy": list[Node],
  }
Error handling: AlgorithmError if extraction fails.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from deep_notes_ai.domain.algorithms import build_content_payloads, rebuild_content_payloads
from deep_notes_ai.domain.models import (
    ContentNodeCountMismatchError,
    ContentPayload,
    ContentStoreItem,
    Node,
    TranscriptHierarchy,
)
from deep_notes_ai.langgraph_pipeline.state import PipelineState
from deep_notes_ai.services.persistence_service import PersistenceService

if TYPE_CHECKING:
    from deep_notes_ai.services.progress_service import ProgressService

logger = logging.getLogger(__name__)

_NODE = "extract_content_nodes"
_STAGE = "Extracting Content Nodes"


def make_extract_content_nodes(
    persistence_service: PersistenceService,
    progress_service: "ProgressService | None" = None,
):
    def extract_content_nodes(state: PipelineState) -> dict:
        """
        Extract CONTENT nodes and build the content payload from the hierarchy.

        Reads:
            state["raw_hierarchy"]: TranscriptHierarchy
            state["content_points"]: list[str]
            state["current_run_dir"]: Path

        Returns:
            {
                "content_payload": list[ContentPayload],
                "nodes_content": dict[str, ContentStoreItem],
                "nodes_hierarchy": list[Node],
            }

        Raises:
            AlgorithmError: if extraction logic fails.
        """
        raw_hierarchy: TranscriptHierarchy = state["raw_hierarchy"]
        content_points: list[str] = state["content_points"]
        current_run_dir: Path = state["current_run_dir"]
        content_node_count: int = state["content_node_count"]

        nodes_hierarchy_path = current_run_dir / "artifacts" / "nodes_hierarchy.json"
        nodes_content_path = current_run_dir / "artifacts" / "nodes_content.json"

        if persistence_service.exists(nodes_hierarchy_path) and persistence_service.exists(nodes_content_path):
            logger.info("nodes_hierarchy.json and nodes_content.json exist, loading from persistence")
            nodes_hierarchy = persistence_service.load_nodes_hierarchy(nodes_hierarchy_path)
            nodes_content = persistence_service.load_nodes_content(nodes_content_path)
            content_payload = rebuild_content_payloads(
                hierarchy=raw_hierarchy.hierarchy,
                converted_hierarchy=nodes_hierarchy,
                content_points=content_points,
            )

            if len(payload_result) != content_node_count:
                raise ContentNodeCountMismatchError(
                    "Cached hierarchy/content is inconsistent with the validated "
                    f"hierarchy. Expected {content_node_count} content nodes, "
                    f"but reconstructed {len(payload_result)} payloads."
                )
            
            if progress_service is not None:
                progress_service.emit_info(
                    node_name=_NODE,
                    stage=_STAGE,
                    message="Content nodes restored from cache",
                )
            return {
                "content_payload": content_payload,
                "nodes_content": nodes_content,
                "nodes_hierarchy": nodes_hierarchy,
            }

        logger.info(
            "Extracting content nodes from raw hierarchy with %d top-level nodes",
            len(raw_hierarchy.hierarchy),
        )

        if progress_service is not None:
            progress_service.emit_start(node_name=_NODE, stage=_STAGE)

        payload_result = build_content_payloads(
            hierarchy=raw_hierarchy.hierarchy,
            content_points=content_points,
        )

        if len(payload_result.payload) != content_node_count:
            raise ContentNodeCountMismatchError(
                "Content payload generation produced an unexpected number of "
                f"content nodes. Expected {content_node_count}, got {len(payload_result.payload)}."
            )

        logger.info(
            "Extracted %d CONTENT nodes (UUIDs generated)",
            len(payload_result.payload),
        )

        persistence_service.save_nodes_hierarchy(nodes_hierarchy_path, payload_result.nodes)
        persistence_service.save_nodes_content(nodes_content_path, payload_result.metadata)

        if progress_service is not None:
            progress_service.emit_completed(node_name=_NODE, stage=_STAGE)

        return {
            "content_payload": payload_result.payload,
            "nodes_content": payload_result.metadata,
            "nodes_hierarchy": payload_result.nodes,
        }

    return extract_content_nodes
