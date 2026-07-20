"""
deep_notes_ai/langgraph_pipeline/nodes/complete_transcript_part.py

Node: complete_transcript_part

Responsibility:
Mark the currently active transcript part as completed and advance the
ProcessingContext to the next part.

This node is executed after the reusable processing subgraph has completed
successfully for the current transcript part.

It does not prepare the next part. Its only responsibility is updating the
ProcessingContext. The AdvanceTranscriptPart node is responsible for preparing
the next execution.

Reads from state:
    processing_context

Returns:
    {
        "processing_context": ProcessingContext,
    }

Graph routing is expected to inspect the updated ProcessingContext to decide
whether another transcript part should be processed or whether rendering can
begin.
"""
from __future__ import annotations

import logging
from copy import deepcopy
from typing import TYPE_CHECKING, Callable

from deep_notes_ai.domain.models import (
    ProcessingContext,
    TranscriptProcessingMode,
)
from deep_notes_ai.langgraph_pipeline.state import PipelineState

if TYPE_CHECKING:
    from deep_notes_ai.services.progress_service import ProgressService

logger = logging.getLogger(__name__)

_NODE = "complete_transcript_part"
_STAGE = "Completing Transcript Part"


def make_complete_transcript_part_node(
    progress_service: "ProgressService | None" = None,
) -> Callable[[PipelineState], dict]:
    """
    Factory that returns a complete_transcript_part node.

    Args:
        progress_service:
            Optional ProgressService for user-facing progress reporting.

    Returns:
        A callable compatible with the LangGraph node interface.
    """

    def complete_transcript_part(state: PipelineState) -> dict:
        """
        Mark the current transcript part as completed.

        Reads:
            state["processing_context"]

        Returns:
            {
                "processing_context": ProcessingContext,
            }
        """
        processing_context: ProcessingContext = deepcopy(state["processing_context"])

        if progress_service is not None:
            progress_service.emit_start(
                node_name=_NODE,
                stage=_STAGE,
            )

        if (
            processing_context.processing_mode
            == TranscriptProcessingMode.SINGLE
        ):
            logger.info(
                "Single transcript part completed."
            )

            if progress_service is not None:
                progress_service.emit_completed(
                    node_name=_NODE,
                    stage=_STAGE,
                    message="Transcript processing completed.",
                )

            processing_context.current_part += 1

            return {
                "processing_context": processing_context,
            }

        current_part = processing_context.current_part
        total_parts = processing_context.total_parts

        logger.info(
            "Completed transcript part %d/%d.",
            current_part,
            total_parts,
        )

        if current_part >= total_parts:
            logger.info(
                "All transcript parts have been completed."
            )

            if progress_service is not None:
                progress_service.emit_completed(
                    node_name=_NODE,
                    stage=_STAGE,
                    message="All transcript parts completed.",
                )

            processing_context.current_part += 1

            return {
                "processing_context": processing_context,
            }

        processing_context.current_part += 1

        logger.info(
            "Advancing processing context to transcript part %d/%d.",
            processing_context.current_part,
            processing_context.total_parts,
        )

        if progress_service is not None:
            progress_service.emit_info(
                node_name=_NODE,
                stage=_STAGE,
                message=(
                    f"Completed part {current_part}/{total_parts}. "
                    f"Next: part {processing_context.current_part}/{total_parts}."
                ),
            )

        return {
            "processing_context": processing_context,
        }

    return complete_transcript_part