"""
deep_notes_ai/langgraph_pipeline/nodes/determine_processing_mode.py

Node: determine_processing_mode

Responsibility:
Determine whether the transcript should be processed as a single document
or split into multiple parts.

The node inspects the token counts of all transcript chapters and compares
their combined size against the configured per-part token limit.

If the transcript fits within the configured limit, a single ContentPart is
constructed by joining all chapter transcripts and the pipeline continues in
SINGLE mode.

Otherwise, the pipeline switches to MULTI mode. The actual partitioning of
the transcript is handled by downstream nodes.

Reads from state:
    chapter_transcripts

Returns:
    {
        "processing_mode": TranscriptProcessingMode.SINGLE,
        "total_parts": 1,
        "current_part": 1,
        "content_parts": [...]
    }

or

    {
        "processing_mode": TranscriptProcessingMode.MULTI
    }
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Callable

from deep_notes_ai.domain.models import (
    ChapterTranscript,
    ContentPart,
    ProcessingContext,
    TranscriptProcessingMode,
)
from deep_notes_ai.langgraph_pipeline.state import PipelineState

if TYPE_CHECKING:
    from deep_notes_ai.services.progress_service import ProgressService

logger = logging.getLogger(__name__)

_NODE = "determine_processing_mode"
_STAGE = "Determining Processing Mode"


def make_determine_processing_mode_node(
    max_tokens_per_part: int,
    progress_service: "ProgressService | None" = None,
) -> Callable[[PipelineState], dict]:
    """
    Factory that returns a determine_processing_mode node.

    Args:
        max_tokens_per_part:
            Maximum number of tokens allowed for processing a single transcript
            part.

        progress_service:
            Optional ProgressService for user-facing progress reporting.

    Returns:
        A callable compatible with the LangGraph node interface.
    """

    def determine_processing_mode(state: PipelineState) -> dict:
        """
        Determine whether the transcript should be processed in SINGLE or
        MULTI mode.

        Reads:
            state["chapter_transcripts"]

        Returns:
            SINGLE mode:
                {
                    "processing_mode": TranscriptProcessingMode.SINGLE,
                    "total_parts": 1,
                    "current_part": 1,
                    "content_parts": [...]
                }

            MULTI mode:
                {
                    "processing_mode": TranscriptProcessingMode.MULTI
                }
        """
        chapter_transcripts: list[ChapterTranscript] = state["chapters"]

        if progress_service is not None:
            progress_service.emit_start(
                node_name=_NODE,
                stage=_STAGE,
            )

        total_tokens = sum(chapter.tokens for chapter in chapter_transcripts)

        logger.info(
            "Calculated transcript size from %d chapter(s): %d token(s)",
            len(chapter_transcripts),
            total_tokens,
        )

        if total_tokens <= max_tokens_per_part:
            logger.info(
                "Processing mode: SINGLE (%d tokens <= limit %d)",
                total_tokens,
                max_tokens_per_part,
            )

            if progress_service is not None:
                progress_service.emit_completed(
                    node_name=_NODE,
                    stage=_STAGE,
                    message=(
                        f"Single-part processing selected "
                        f"({total_tokens:,} tokens)"
                    ),
                )

            content = "\n\n".join(
                chapter.transcript
                for chapter in chapter_transcripts
            )

            return {
                "processing_context": ProcessingContext(
                    processing_mode=TranscriptProcessingMode.SINGLE,
                    current_part=1,
                    total_parts=1,
                    content_parts=[
                        ContentPart(
                            part_title="00-00-00",
                            content=content,
                            tokens=total_tokens,
                        )
                    ],
                ),
            }

        logger.info(
            "Processing mode: MULTI (%d tokens > limit %d)",
            total_tokens,
            max_tokens_per_part,
        )

        if progress_service is not None:
            progress_service.emit_info(
                node_name=_NODE,
                stage=_STAGE,
                message=(
                    f"Transcript contains {total_tokens:,} tokens "
                    f"(limit {max_tokens_per_part:,}). "
                    "Multi-part processing required."
                ),
            )

        return {
            "processing_context": ProcessingContext(
                processing_mode=TranscriptProcessingMode.MULTI_PART,
                current_part=0,
                total_parts=0,
                content_parts=[],
            ),
        }

    return determine_processing_mode