"""
deep_notes_ai/langgraph_pipeline/nodes/select_transcript_breakpoints.py

Node: select_transcript_breakpoints

Responsibility:
Pause graph execution using LangGraph's interrupt() mechanism to allow the
user to choose transcript breakpoints.

The node itself remains intentionally thin:

    • Builds the interrupt payload.
    • Waits for human input.
    • Delegates validation and transcript partitioning to
      TranscriptPartitionService.
    • Updates pipeline state.

Reads from state:
    chapters

Returns:

Success
-------
{
    "total_parts": int,
    "current_part": 1,
    "content_parts": list[ContentPart]
}

Validation failure
------------------
{
    "total_parts": 0
}
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Callable

from langgraph.types import interrupt

from deep_notes_ai.domain.models import ChapterTranscript, ProcessingContext, TranscriptProcessingMode
from deep_notes_ai.langgraph_pipeline.state import PipelineState
from deep_notes_ai.services.chapter_selection_service import ChapterSelectionService
from deep_notes_ai.services.transcript_partition_service import (
    TranscriptPartitionService,
)

if TYPE_CHECKING:
    from deep_notes_ai.services.progress_service import ProgressService

logger = logging.getLogger(__name__)

_NODE = "select_transcript_breakpoints"
_STAGE = "Waiting for User Selection"


def make_select_transcript_breakpoints_node(
    chapter_selection_service: ChapterSelectionService,
    partition_service: TranscriptPartitionService,
    progress_service: "ProgressService | None" = None,
) -> Callable[[PipelineState], dict]:
    """
    Factory returning a LangGraph node.

    Args:
        chapter_selection_service:

        partition_service:
            Service responsible for validating chapter selections and
            constructing transcript parts.

        progress_service:
            Optional user-facing progress reporter.
    """

    def select_transcript_breakpoints(
        state: PipelineState,
    ) -> dict:
        """
        Interrupt graph execution and wait for breakpoint selection.
        """
        chapters: list[ChapterTranscript] = state["chapters"]

        if progress_service is not None:
            progress_service.emit_start(
                node_name=_NODE,
                stage=_STAGE,
            )

        logger.info(
            "Preparing chapter selection (%d chapter(s))",
            len(chapters),
        )

        payload = chapter_selection_service.build_interrupt_payload(chapters=chapters)

        logger.info(
            "Interrupting graph for human breakpoint selection."
        )

        resume_value = interrupt(payload)

        logger.info(
            "Graph resumed with user selection."
        )

        selected_indices = chapter_selection_service.extract_selected_indices(resume_value)

        logger.info(
            "User selected breakpoint chapters: %s",
            selected_indices,
        )

        try:
            content_parts = partition_service.build_content_parts(
                chapters=chapters,
                selected_indices=selected_indices,
            )

        except Exception as exc:

            logger.warning(
                "Breakpoint validation failed: %s",
                exc,
            )

            if progress_service is not None:
                progress_service.emit_failed(
                    node_name=_NODE,
                    stage=_STAGE,
                    message=str(exc),
                )

            return {
                "processing_context": ProcessingContext(
                    processing_mode=TranscriptProcessingMode.MULTI_PART,
                    current_part=0,
                    total_parts=0,
                    content_parts=[],
                ),
                "pipeline_complete": False,
                "error_message": str(exc),
            }

        logger.info(
            "Generated %d transcript part(s).",
            len(content_parts),
        )

        if progress_service is not None:
            progress_service.emit_completed(
                node_name=_NODE,
                stage=_STAGE,
                message=(
                    f"{len(content_parts)} transcript part(s) created."
                ),
            )

        return {
            "processing_context": ProcessingContext(
                processing_mode=TranscriptProcessingMode.MULTI_PART,
                current_part=1,
                total_parts=len(content_parts),
                content_parts=content_parts,
            ),
        }

    return select_transcript_breakpoints
