"""
deep_notes_ai/services/transcript_service.py

TranscriptService — fetch YouTube transcripts and partition them into
chapter-aligned transcript segments.

Each returned transcript segment also includes its token count as
calculated by the project's TokenizerService.
"""
from __future__ import annotations

import logging

from deep_notes_ai.domain.models import (
    ChapterTranscript,
    EmptyTranscriptError,
    TimestampChapter,
    TranscriptFetchError,
)
from deep_notes_ai.services.tokenizer_service import TokenizerService

logger = logging.getLogger(__name__)


class TranscriptService:
    """
    Wraps YouTubeTranscriptApi to fetch transcript snippets and build
    chapter-aligned transcript segments.

    Each returned ChapterTranscript includes:

    - chapter metadata
    - transcript text
    - transcript token count

    Characteristics:

    - No caching; callers are responsible for persistence.
    - Wraps YouTubeTranscriptApi errors as TranscriptFetchError.
    - Preserves transcript ordering exactly as returned by YouTube.
    - Computes token counts using the injected TokenizerService.
    - Runs in O(N + M), where:
        N = transcript snippets
        M = timestamp chapters.
    """

    def __init__(
        self,
        tokenizer_service: "TokenizerService | None" = None,
    ) -> None:
        """
        Initialize the service.

        Args:
            tokenizer_service:
                Service used to calculate token counts for each transcript
                segment. Required when transcript token statistics are needed.
        """
        self._tokenizer_service = tokenizer_service
    

    def fetch(
        self,
        content_id: str,
        chapters: list[TimestampChapter],
    ) -> list[ChapterTranscript]:
        """
        Fetch transcript and split it into chapter transcript segments.

        If no chapters are supplied, the entire transcript is returned as a
        single ChapterTranscript whose title and display are empty strings.

        Args:
            content_id:
                YouTube video ID.

            chapters:
                Ordered timestamp chapters.

        Returns:
            Ordered list of ChapterTranscript objects.

            Each object contains:

            - chapter title
            - timestamp display
            - transcript text
            - transcript token count

        Raises:
            TranscriptFetchError:
                If transcript retrieval fails.
        """
        try:
            from youtube_transcript_api import YouTubeTranscriptApi

            ytt_api = YouTubeTranscriptApi()
            fetched_transcript = ytt_api.fetch(content_id)
            
        except Exception as exc:
            raise TranscriptFetchError(
                f"Failed to fetch transcript for content_id={content_id!r}: {exc}"
            ) from exc

        # No timestamp chapters detected -> return the entire transcript as one segment.
        if not chapters:
            transcript = " ".join(
                snippet.text
                for snippet in fetched_transcript
            )

            self._validate_transcript(transcript, content_id)

            tokens = self._tokenizer_service.count_tokens(transcript)

            logger.info(
                "Fetched transcript for content_id=%s (%d chars, %d tokens, single segment).",
                content_id,
                len(transcript),
                tokens,
            )

            return [
                ChapterTranscript(
                    title="",
                    display="00:00:00",
                    transcript=transcript,
                    tokens=tokens,
                )
            ]

        # Partition the transcript into chapter-aligned transcript segments.
        # Ensure chapters are processed in chronological order.
        chapters = sorted(
            chapters,
            key=lambda chapter: chapter.timestamp_seconds,
        )
        chapter_transcripts: list[ChapterTranscript] = []

        chapter_index = 0
        current_buffer: list[str] = []

        for snippet in fetched_transcript:
            # Advance chapter whenever the next chapter starts.
            while (
                chapter_index + 1 < len(chapters)
                and snippet.start >= chapters[chapter_index + 1].timestamp_seconds
            ):
                current_chapter = chapters[chapter_index]
                transcript = " ".join(current_buffer)
                tokens = self._tokenizer_service.count_tokens(transcript)

                chapter_transcripts.append(
                    ChapterTranscript(
                        title=current_chapter.title,
                        display=current_chapter.display,
                        transcript=transcript,
                        tokens=tokens,
                    )
                )

                current_buffer = []
                chapter_index += 1

            current_buffer.append(snippet.text)

        # Flush the final chapter after all transcript snippets have been processed.
        final_chapter = chapters[chapter_index]
        transcript = " ".join(current_buffer)
        tokens = self._tokenizer_service.count_tokens(transcript)

        chapter_transcripts.append(
            ChapterTranscript(
                title=final_chapter.title,
                display=final_chapter.display,
                transcript=transcript,
                tokens=tokens,
            )
        )

        overall_transcript = " ".join(
            chapter.transcript
            for chapter in chapter_transcripts
        )

        self._validate_transcript(
            overall_transcript,
            content_id,
        )

        if len(chapter_transcripts) != len(chapters):
            logger.warning(
                "Transcript segmentation produced "
                f"{len(chapter_transcripts)} chapter(s) but "
                f"{len(chapters)} timestamp chapter(s) were expected. "
                "The transcript appears to be shorter than the detected chapters."
            )

        logger.info(
            "Fetched transcript for content_id=%s (%d chapter, segments).",
            content_id,
            len(chapter_transcripts),
        )

        return chapter_transcripts
    
    def _validate_transcript(
        self,
        transcript: str,
        content_id: str,
    ) -> None:
        """
        Validate that a transcript contains at least one non-whitespace
        character.

        Raises:
            EmptyTranscriptError:
                If the transcript is empty or contains only whitespace.
        """
        if not transcript.strip():
            raise EmptyTranscriptError(
                f"Transcript for content_id={content_id!r} is empty."
            )