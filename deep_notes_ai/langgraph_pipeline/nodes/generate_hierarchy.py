"""
deep_notes_ai/langgraph_pipeline/nodes/generate_hierarchy.py

Node 4: generate_hierarchy

Responsibility: Send the numbered transcript to the hierarchy LLM and receive
a TranscriptHierarchy.

Reads from state: content_points
Calls: LangChain chain (hierarchy prompt | hierarchy LLM with structured output)
Returns: {"raw_hierarchy": TranscriptHierarchy}
Error handling: LLMCallError or ValidationError on failure → graph terminates.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from langchain_core.runnables import Runnable

from deep_notes_ai.domain.models import LLMCallError, TopicNode, TranscriptHierarchy
from deep_notes_ai.langgraph_pipeline.state import PipelineState
from deep_notes_ai.services.persistence_service import PersistenceService
from deep_notes_ai.services.tokenizer_service import TokenizerService
from pathlib import Path

if TYPE_CHECKING:
    from deep_notes_ai.services.progress_service import ProgressService

logger = logging.getLogger(__name__)

_NODE = "generate_hierarchy"
_STAGE = "Generating Topic Hierarchy"


def _count_content_nodes(nodes: list[TopicNode]) -> int:
    """
    Recursively count CONTENT leaf nodes in a list of TopicNodes.

    A CONTENT node is identified by name == "CONTENT".
    """
    count = 0
    for node in nodes:
        if node.name == "CONTENT":
            count += 1
        else:
            count += _count_content_nodes(node.children)
    return count


def make_generate_hierarchy_node(
    llm_chain: Runnable,
    persistence_service: PersistenceService,
    tokenizer_service: TokenizerService,
    ideal_input_tokens: int,
    progress_service: "ProgressService | None" = None,
):
    """
    Factory that returns a generate_hierarchy node bound to the given LLM chain.

    Args:
        llm_chain: A LangChain Runnable (hierarchy prompt | structured LLM).
                   Must return TranscriptHierarchy instances.
        persistence_service: PersistenceService for caching.
        progress_service:    Optional ProgressService for user-facing progress.

    Returns:
        A callable compatible with LangGraph node interface.
    """

    def generate_hierarchy(state: PipelineState) -> dict:
        """
        Send the numbered transcript to the hierarchy LLM.

        Reads:
            state["content_points"]: str

        Returns:
            {"raw_hierarchy": TranscriptHierarchy}

        Raises:
            LLMCallError: if the LLM call fails.
        """
        content_points: list[str] = state["content_points"]
        current_run_dir: Path = state["current_run_dir"]

        artifact_path = current_run_dir / "artifacts" / "raw_hierarchy.json"

        if persistence_service.exists(artifact_path):
            raw_hierarchy = persistence_service.load_hierarchy(artifact_path)
            logger.info("Found existing raw hierarchy. Restoring state from disk.")
            content_node_count = _count_content_nodes(raw_hierarchy.hierarchy)
            if progress_service is not None:
                progress_service.emit_info(
                    node_name=_NODE,
                    stage=_STAGE,
                    message="Hierarchy restored from cache",
                )
            return {
                "raw_hierarchy": raw_hierarchy,
                "content_node_count": content_node_count
            }
        
        content_points_txt = "\n".join(content_points)
        token_count = tokenizer_service.count_tokens(content_points_txt)

        logger.info("Generating hierarchy from numbered content points, length=%d points, input_tokens=%d", len(content_points), token_count)
        if progress_service is not None:
            progress_service.emit_start(node_name=_NODE, stage=_STAGE)

        if token_count > ideal_input_tokens:
            logger.warning("Input token count for hierarchy generation exceeds limit. input_tokens=%d, ideal_input_tokens=%d", token_count, ideal_input_tokens)
            progress_service.emit_info(node_name=_NODE, stage=_STAGE, message=f"Input token count exceeds ideal limit: {token_count} > {ideal_input_tokens}")

        try:
            raw_hierarchy: TranscriptHierarchy = llm_chain.invoke(content_points_txt)
        except Exception as exc:
            if progress_service is not None:
                progress_service.emit_failed(
                    node_name=_NODE,
                    stage=_STAGE,
                    message="Hierarchy LLM call failed",
                )
            raise LLMCallError(
                f"Hierarchy LLM call failed: {exc}"
            ) from exc

        logger.info("Hierarchy generated with %d top-level nodes", len(raw_hierarchy.hierarchy))

        content_node_count = _count_content_nodes(raw_hierarchy.hierarchy)

        persistence_service.save_hierarchy(artifact_path, raw_hierarchy)

        if progress_service is not None:
            progress_service.emit_completed(node_name=_NODE, stage=_STAGE)

        return {
            "raw_hierarchy": raw_hierarchy,
            "content_node_count": content_node_count
        }

    return generate_hierarchy
