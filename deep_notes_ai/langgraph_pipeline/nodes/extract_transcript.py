"""
deep_notes_ai/langgraph_pipeline/nodes/extract_transcript.py

Node 1: extract_transcript

Responsibility: Fetch the raw YouTube transcript for the given video ID and
count its tokens once for use by downstream nodes.

Reads from state: content_id
Returns: {"raw_content": str, "content_token_count": int}
Error handling: Raises TranscriptFetchError on failure → graph terminates.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Callable, TYPE_CHECKING

from deep_notes_ai.domain.models import TranscriptFetchError
from deep_notes_ai.langgraph_pipeline.state import PipelineState
from deep_notes_ai.services.persistence_service import PersistenceService
from deep_notes_ai.services.transcript_service import TranscriptService

if TYPE_CHECKING:
    from deep_notes_ai.services.progress_service import ProgressService

logger = logging.getLogger(__name__)

_NODE = "extract_transcript"
_STAGE = "Downloading Transcript"


def make_extract_transcript_node(
    persistence_service: PersistenceService,
    transcript_service: TranscriptService,
    progress_service: "ProgressService | None" = None,
) -> Callable[[PipelineState], dict]:
    """
    Factory that returns an extract_transcript node bound to the given services.

    Args:
        persistence_service: PersistenceService for caching the transcript.
        transcript_service:  TranscriptService for fetching from YouTube.
        progress_service:    Optional ProgressService for user-facing progress.

    Returns:
        A callable compatible with LangGraph node interface.
    """

    def extract_transcript(state: PipelineState) -> dict:
        """
        Fetch the raw YouTube transcript for the video ID in state.
        Caches to raw_content.txt and counts tokens once.

        Reads:
            state["content_id"]: str
            state["current_run_dir"]: Path

        Returns:
            {"raw_content": str}

        Raises:
            TranscriptFetchError: if the transcript cannot be fetched.
        """
        content_id: str = state["content_id"]
        current_run_dir: Path = state["current_run_dir"]

        artifact_path = current_run_dir / "artifacts" / "raw_content.txt"

        if persistence_service.exists(artifact_path):
            raw_content = persistence_service.load_text(artifact_path)
            logger.info("Found existing raw content. Restoring state from disk.")
            if progress_service is not None:
                progress_service.emit_info(
                    node_name=_NODE,
                    stage=_STAGE,
                    message="Transcript restored from cache",
                )
            return {"raw_content": raw_content}

        if progress_service is not None:
            progress_service.emit_start(node_name=_NODE, stage=_STAGE)

        logger.info("Fetching raw content for content_id=%s", content_id)

        try:
            raw_content = transcript_service.fetch(content_id)
        except Exception:
            if progress_service is not None:
                progress_service.emit_failed(
                    node_name=_NODE,
                    stage=_STAGE,
                    message="Failed to download transcript",
                )
            raise

        logger.info(
            "Fetched raw content for content_id=%s, length=%d chars",
            content_id,
            len(raw_content),
        )

        persistence_service.save_text(artifact_path, raw_content)

        if progress_service is not None:
            progress_service.emit_completed(node_name=_NODE, stage=_STAGE)

        return {"raw_content": raw_content}

    return extract_transcript
