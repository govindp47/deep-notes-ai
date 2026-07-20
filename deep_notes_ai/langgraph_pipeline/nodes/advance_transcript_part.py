"""
deep_notes_ai/langgraph_pipeline/nodes/advance_transcript_part.py

Node: advance_transcript_part

Responsibility:
Prepare the currently selected transcript part for execution.

This node is responsible only for preparing the execution context for the
current transcript part. It does NOT advance to the next part. Incrementing
`current_part` is handled exclusively by the `complete_transcript_part` node.

Responsibilities:
    - Read the current ProcessingContext.
    - Resolve the active ContentPart.
    - Populate `raw_content` for downstream nodes.
    - Resolve the correct run directory for this part.
    - Emit progress and logs.

Reads from state:
    processing_context
    content_base_dir

Returns:
    {
        "processing_context": ProcessingContext,
        "current_run_dir": Path,
        "raw_content": str,
    }

Raises:
    InvalidProcessingContextError:
        If the ProcessingContext is inconsistent.
"""
from __future__ import annotations

import logging
from copy import deepcopy
from pathlib import Path
from typing import TYPE_CHECKING, Callable

from deep_notes_ai.domain.models import (
    ContentPart,
    InvalidProcessingContextError,
    ProcessingContext,
    TranscriptProcessingMode,
)
from deep_notes_ai.langgraph_pipeline.state import PipelineState
from deep_notes_ai.services.persistence_service import PersistenceService

if TYPE_CHECKING:
    from deep_notes_ai.services.progress_service import ProgressService

logger = logging.getLogger(__name__)

_NODE = "advance_transcript_part"
_STAGE = "Preparing Transcript Part"


def make_advance_transcript_part_node(
    persistence_service: PersistenceService,
    progress_service: "ProgressService | None" = None,
) -> Callable[[PipelineState], dict]:
    """
    Factory that returns an advance_transcript_part node.

    Args:
        progress_service:
            Optional ProgressService for user-facing progress reporting.

    Returns:
        LangGraph-compatible node callable.
    """

    def advance_transcript_part(state: PipelineState) -> dict:
        """
        Prepare the transcript part indicated by the current ProcessingContext.

        Reads:
            state["processing_context"]
            state["content_base_dir"]

        Returns:
            {
                "processing_context": ProcessingContext,
                "current_run_dir": Path,
                "raw_content": str,
            }
        """
        processing_context: ProcessingContext = deepcopy(
            state["processing_context"]
        )

        content_base_dir: Path = state["content_base_dir"]

        if progress_service is not None:
            progress_service.emit_start(
                node_name=_NODE,
                stage=_STAGE,
            )

        #
        # Validate processing context.
        #
        if processing_context.total_parts <= 0:
            raise InvalidProcessingContextError(
                "ProcessingContext.total_parts must be greater than zero."
            )

        if not processing_context.content_parts:
            raise InvalidProcessingContextError(
                "ProcessingContext.content_parts is empty."
            )

        if processing_context.current_part < 1:
            raise InvalidProcessingContextError(
                "ProcessingContext.current_part must be >= 1."
            )

        if processing_context.current_part > processing_context.total_parts:
            raise InvalidProcessingContextError(
                "Current part exceeds total_parts."
            )

        part_index = processing_context.current_part - 1

        if part_index >= len(processing_context.content_parts):
            raise InvalidProcessingContextError(
                "Current part does not exist in content_parts."
            )

        current_part: ContentPart = processing_context.content_parts[part_index]

        if (
            processing_context.processing_mode
            == TranscriptProcessingMode.SINGLE
        ):
            current_run_dir = (
                content_base_dir
                / "artifacts"
            )
        else:
            current_run_dir = (
                content_base_dir
                / "artifacts"
                / current_part.part_title
            )

        logger.info(
            "Preparing transcript part %d/%d (%s).",
            processing_context.current_part,
            processing_context.total_parts,
            current_part.part_title,
        )

        logger.debug(
            "Resolved run directory: %s",
            current_run_dir,
        )

        if progress_service is not None:
            progress_service.emit_info(
                node_name=_NODE,
                stage=_STAGE,
                message=(
                    f"Processing part "
                    f"{processing_context.current_part}/"
                    f"{processing_context.total_parts}"
                ),
            )

        artifact_path = current_run_dir / "raw_content.txt"

        if persistence_service.exists(artifact_path):
            raw_content = persistence_service.load_text(artifact_path)
            logger.info("Found existing raw content. Restoring state from disk.")
            if progress_service is not None:
                progress_service.emit_info(
                    node_name=_NODE,
                    stage=_STAGE,
                    message="Raw content restored from cache",
                )
            return {
                "processing_context": processing_context,
                "current_run_dir": current_run_dir,
                "raw_content": raw_content,
            }

        logger.info("loading raw content with %d tokens.", current_part.tokens)
        raw_content = current_part.content

        persistence_service.save_text(artifact_path, raw_content)

        if progress_service is not None:
            progress_service.emit_completed(node_name=_NODE, stage=_STAGE)


        return {
            "processing_context": processing_context,
            "current_run_dir": current_run_dir,
            "raw_content": raw_content,
        }

    return advance_transcript_part