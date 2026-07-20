"""
deep_notes_ai/langgraph_pipeline/nodes/extract_transcript.py

Node 1: extract_transcript

Responsibility:
Fetch the YouTube transcript and split it into chapter transcripts using the
chapter metadata extracted earlier in the pipeline.

Reads from state:
    metadata

Returns:
    {
        "chapters": list[ChapterTranscript]
    }

Error handling:
    Raises TranscriptFetchError on failure → graph terminates.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Callable, cast

from deep_notes_ai.domain.models import EmptyTranscriptError, TranscriptFetchError, VideoMetadata
from deep_notes_ai.langgraph_pipeline.state import PipelineState
from deep_notes_ai.services.transcript_service import TranscriptService

if TYPE_CHECKING:
    from deep_notes_ai.services.progress_service import ProgressService

logger = logging.getLogger(__name__)

_NODE = "extract_transcript"
_STAGE = "Downloading Transcript"


def make_extract_transcript_node(
    transcript_service: TranscriptService,
    progress_service: "ProgressService | None" = None,
) -> Callable[[PipelineState], dict]:
    """
    Factory that creates the extract_transcript LangGraph node.

    Args:
        transcript_service:
            Service responsible for fetching and partitioning the transcript.

        progress_service:
            Optional ProgressService used for user-facing execution updates.

    Returns:
        A LangGraph-compatible node callable.
    """

    def extract_transcript(state: PipelineState) -> dict:
        """
        Fetch the transcript and split it into chapter transcripts.

        Reads:
            state["metadata"]

        Returns:
            {
                "chapters": list[ChapterTranscript]
            }

        Raises:
            TranscriptFetchError:
                Propagated from TranscriptService when transcript retrieval
                fails.
        """
        metadata = cast(VideoMetadata, state["metadata"])

        if progress_service is not None:
            progress_service.emit_start(
                node_name=_NODE,
                stage=_STAGE,
            )

        logger.info(
            "Fetching transcript for content_id=%s",
            metadata.id,
        )

        try:
            chapters = transcript_service.fetch(
                content_id=metadata.id,
                chapters=metadata.chapters,
            )
        except EmptyTranscriptError:
            if progress_service is not None:
                progress_service.emit_failed(
                    node_name=_NODE,
                    stage=_STAGE,
                    message="The video transcript is empty.",
                )
            raise
        except TranscriptFetchError:
            if progress_service is not None:
                progress_service.emit_failed(
                    node_name=_NODE,
                    stage=_STAGE,
                    message="Failed to download transcript.",
                )
            raise

        logger.info(
            "Transcript fetched successfully for content_id=%s (%d chapter%s).",
            metadata.id,
            len(chapters),
            "" if len(chapters) == 1 else "s",
        )

        if progress_service is not None:
            progress_service.emit_completed(
                node_name=_NODE,
                stage=_STAGE,
            )

        return {
            "chapters": chapters,
        }

    return extract_transcript
