"""
deep_notes_ai/services/transcript_service.py

TranscriptService — fetch a raw YouTube transcript given a video ID.

Component 1 per 07_component_design.md.
"""
from __future__ import annotations

import logging

from deep_notes_ai.domain.models import TranscriptFetchError

logger = logging.getLogger(__name__)


class TranscriptService:
    """
    Wraps YouTubeTranscriptApi to fetch and join transcript snippets.

    - No caching. Caller is responsible for persisting the result.
    - Error translation: wraps all API exceptions in TranscriptFetchError.
    - Snippet joining: " ".join(snippet.text for snippet in fetched)
      — identical to notebook Cell 0.
    """

    def fetch(self, content_id: str) -> str:
        """
        Fetch and join all transcript snippets into a single string.

        Args:
            content_id: YouTube video ID (e.g. "dQw4w9WgXcQ").

        Returns:
            Raw transcript as one long string (space-joined snippets).

        Raises:
            TranscriptFetchError: if the API call fails or returns no transcript.
        """
        try:
            from youtube_transcript_api import YouTubeTranscriptApi

            ytt_api = YouTubeTranscriptApi()
            fetched_transcript = ytt_api.fetch(content_id)

            transcript = " ".join(snippet.text for snippet in fetched_transcript)
            logger.info(
                "Fetched transcript for content_id=%s, length=%d chars",
                content_id,
                len(transcript),
            )
            return transcript
        except Exception as exc:
            raise TranscriptFetchError(
                f"Failed to fetch transcript for content_id={content_id!r}: {exc}"
            ) from exc
