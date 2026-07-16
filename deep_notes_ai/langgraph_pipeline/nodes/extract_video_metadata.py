"""
deep_notes_ai/langgraph_pipeline/nodes/extract_video_metadata.py

Node 0: extract_video_metadata

Responsibility: Extract video ID and fetch metadata from a YouTube URL.

Reads from state: youtube_url
Returns: {"content_id": str, "content_title": str, "content_url": str, "upload_date": str, "author_name": str}
Error handling: Raises InvalidYoutubeUrlError on invalid URL -> graph terminates.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Callable

from deep_notes_ai.langgraph_pipeline.state import PipelineState
from deep_notes_ai.services.video_metadata_service import VideoMetadataService

if TYPE_CHECKING:
    from deep_notes_ai.services.progress_service import ProgressService

logger = logging.getLogger(__name__)

_NODE = "extract_video_metadata"
_STAGE = "Extracting Video Metadata"


def make_extract_video_metadata_node(
    service: VideoMetadataService,
    progress_service: "ProgressService | None" = None,
) -> Callable[[PipelineState], dict]:
    """
    Factory for the extract_video_metadata node.
    """

    def extract_video_metadata(state: PipelineState) -> dict:
        """
        Extract video ID and metadata from the youtube_url in state.

        Reads:
            state["source"]: str

        Returns:
            {"content_id": str, "content_title": str, ...}
            
        Raises:
            InvalidYoutubeUrlError: if the URL is invalid.
        """
        youtube_url: str = state["source"]
        logger.info("Extracting metadata for URL: %s", youtube_url)

        if progress_service is not None:
            progress_service.emit_start(node_name=_NODE, stage=_STAGE)

        try:
            content_id = service.extract_content_id(youtube_url)
            metadata = service.fetch_video_metadata(content_id)
        except Exception:
            if progress_service is not None:
                progress_service.emit_failed(
                    node_name=_NODE,
                    stage=_STAGE,
                    message="Failed to extract video metadata",
                )
            raise

        base_dir = state.get("current_run_dir")
        current_run_dir = base_dir / content_id

        result = {
            "current_run_dir": current_run_dir,
            "content_id": content_id,
            "content_url": service.normalize_url(content_id),
            **metadata,
        }

        logger.info("Metadata extraction complete for content_id=%s", content_id)

        if progress_service is not None:
            progress_service.emit_completed(node_name=_NODE, stage=_STAGE)

        return result

    return extract_video_metadata
