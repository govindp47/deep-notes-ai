"""
deep_notes_ai/services/chapter_selection_service.py

ChapterSelectionService

Service responsible for all user-interaction related logic for transcript
chapter selection.

Responsibilities:
    • Build the LangGraph interrupt payload.
    • Format chapter information for display.
    • Parse and validate the interrupt resume payload.

This service intentionally contains no LangGraph-specific logic except the
payload structure itself. It performs no I/O and is fully deterministic.
"""
from __future__ import annotations

from deep_notes_ai.domain.models import (
    ChapterTranscript,
)


class ChapterSelectionService:
    """
    Service responsible for preparing and validating human-in-the-loop
    chapter selection.

    Constructor args:
        max_tokens_per_part: Maximum permitted tokens in each generated part.
    """

    def __init__(
        self,
        max_tokens_per_part: int,
    ) -> None:
        self._max_tokens = max_tokens_per_part
    

    def build_interrupt_payload(
        self,
        chapters: list[ChapterTranscript],
    ) -> dict:
        """
        Build the payload presented to the user during the LangGraph interrupt.

        Every chapter occupies exactly one row to keep the output readable for
        long videos containing many chapters.

        Example:

            [00] 00:00:00 | 2,381 tokens | Introduction
            [01] 04:35    | 4,127 tokens | Python Basics
            [02] 12:10    | 5,203 tokens | LangGraph
            ...
        """
        total_tokens = sum(chapter.tokens for chapter in chapters)

        return {
            "type": "chapter_selection",
            "summary": {
                "total_chapters": len(chapters),
                "total_tokens": total_tokens,
                "max_tokens_per_part": self._max_tokens,
            },
            "chapters": self._format_chapter_rows(chapters),
            "instructions": [
                "Each selected chapter starts a NEW transcript part.",
                "Chapter 0 is automatically included.",
                "Do NOT select chapter 0.",
                "Selections must be in ascending order.",
                "Example:",
                '{"selected_indices": [4, 8, 15]}',
            ],
        }
    

    def extract_selected_indices(
        self,
        resume_value: object,
    ) -> list[int]:
        """
        Extract the selected chapter indices from the interrupt resume payload.

        Expected format

            {
                "selected_indices": [...]
            }
        """
        if not isinstance(resume_value, dict):
            raise ValueError(
                "Expected resume payload to be a dictionary."
            )

        indices = resume_value.get("selected_indices")

        if indices is None:
            raise ValueError(
                "Resume payload does not contain 'selected_indices'."
            )

        if not isinstance(indices, list):
            raise ValueError(
                "'selected_indices' must be a list."
            )

        return indices

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #

    def _format_chapter_rows(
        self,
        chapters: list[ChapterTranscript],
    ) -> list[str]:
        """
        Format chapters into compact one-line strings.
        """
        return [
            f"[{index:02d}] "
            f"{chapter.display:<8} | "
            f"{chapter.tokens:>6,} tokens | "
            f"{chapter.title}"
            for index, chapter in enumerate(chapters)
        ]
