"""
deep_notes_ai/langgraph_pipeline/nodes/generate_content.py

Node 7: generate_content

Responsibility: Generate structured markdown for every CONTENT node via
batched, partitioned LLM calls.

Reads from state:
  - content_points: str
  - content_payload: list[ContentPayload]
  - nodes_content: dict[str, ContentStoreItem]
Calls: ContentService.generate(...)
Returns: {"nodes_content": dict[str, ContentStoreItem]}  # updated with .content
Error handling: ContentGenerationError wraps any internal failure.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from deep_notes_ai.domain import algorithms
from deep_notes_ai.domain.models import (
    ContentPayload,
    ContentStoreItem,
)
from deep_notes_ai.langgraph_pipeline.state import PipelineState
from deep_notes_ai.services.content_service import ContentService
from deep_notes_ai.services.tokenizer_service import TokenizerService
from deep_notes_ai.services.persistence_service import PersistenceService
from pathlib import Path

if TYPE_CHECKING:
    from deep_notes_ai.services.progress_service import ProgressService

logger = logging.getLogger(__name__)

_NODE = "generate_content"
_STAGE = "Generating Structured Content"


def make_generate_content_node(
    content_service: ContentService,
    persistence_service: PersistenceService,
    tokenizer_service: TokenizerService,
    ideal_input_tokens: int,
    input_tokens_fallback: int,
    progress_service: "ProgressService | None" = None,
):
    """
    Factory that returns a generate_content node bound to the given service.

    Args:
        content_service:  Configured ContentService instance.
        persistence_service: PersistenceService for caching.
        progress_service: Optional ProgressService for user-facing progress.

    Returns:
        A callable compatible with LangGraph node interface.
    """

    def generate_content(state: PipelineState) -> dict:
        """
        Generate structured content for all CONTENT nodes.

        Reads:
            state["content_payload"]: list[ContentPayload]
            state["nodes_content"]: dict[str, ContentStoreItem]

        Returns:
            {"nodes_content": dict[str, ContentStoreItem]}  # with .content populated

        Raises:
            ContentGenerationError: if generation fails after fallback.
        """
        content_payload: list[ContentPayload] = state["content_payload"]
        nodes_content: dict[str, ContentStoreItem] = state["nodes_content"]
        current_run_dir: Path = state["current_run_dir"]
        content_node_count: int = state["content_node_count"]

        PAYLOAD_METADATA_AVERAGE_TOKENS = 60

        artifact_path = current_run_dir / "artifacts" / "nodes_content.json"

        is_complete = True
        for expected_uuid in nodes_content:
            if not nodes_content[expected_uuid].content:
                is_complete = False
                break

        if is_complete:
            logger.info("Structured content already generated.")
            if progress_service is not None:
                progress_service.emit_info(
                    node_name=_NODE,
                    stage=_STAGE,
                    message="Structured content restored from cache",
                )
            return {}

        logger.info(
            "Generating structured content for %d CONTENT nodes",
            len(content_payload),
        )

        if progress_service is not None:
            progress_service.emit_start(node_name=_NODE, stage=_STAGE)

        content_points_txt = "\n".join(
            point
            for payload in content_payload
            for point in payload.content_points_list
        )
        point_tokens = tokenizer_service.count_tokens(content_points_txt)
        payload_metadata_tokens = PAYLOAD_METADATA_AVERAGE_TOKENS * content_node_count
        total_input_tokens = point_tokens + payload_metadata_tokens
        initial_chunk_count = algorithms.count_chunks(total_input_tokens, ideal_input_tokens)
        fallback_chunk_count = algorithms.count_chunks(total_input_tokens, input_tokens_fallback)

        try:
            updated_nodes_content = content_service.generate(
                payload=content_payload,
                nodes_content=nodes_content,
                initial_partitions=initial_chunk_count,
                fallback_partitions=fallback_chunk_count,
            )
        except Exception:
            if progress_service is not None:
                progress_service.emit_failed(
                    node_name=_NODE,
                    stage=_STAGE,
                    message="Content generation failed",
                )
            raise

        logger.info(
            "Content generation complete for %d nodes",
            len(updated_nodes_content),
        )

        persistence_service.save_nodes_content(artifact_path, updated_nodes_content)

        if progress_service is not None:
            progress_service.emit_completed(node_name=_NODE, stage=_STAGE)

        return {"nodes_content": updated_nodes_content}

    return generate_content
