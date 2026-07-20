"""
deep_notes_ai/services/transcript_partition_service.py

TranscriptPartitionService

Service responsible for converting user-selected transcript chapter
breakpoints into pipeline ContentPart objects.

Responsibilities
----------------
• Validate breakpoint selection.
• Group ChapterTranscript objects into transcript parts.
• Calculate token counts for every generated part.
• Validate every part against the configured token limit.
• Generate filesystem-safe part titles.

This service contains no LangGraph-specific logic and performs no I/O,
making it deterministic and independently testable.
"""
from __future__ import annotations

import re

from deep_notes_ai.domain.models import (
    ChapterTranscript,
    ContentPart,
    InvalidBreakpointSelectionError,
)


class TranscriptPartitionService:
    """
    Service responsible for transcript partitioning.

    The caller supplies:

    - ordered transcript chapters
    - user-selected chapter indices
    - maximum allowed tokens per part

    The service validates the selection, builds ContentPart objects and
    verifies that every generated part satisfies the configured token limit.

    Constructor args:
        max_tokens_per_part: Maximum permitted tokens in each generated part.
    """

    def __init__(
        self,
        max_tokens_per_part: int,
    ) -> None:
        self._max_tokens = max_tokens_per_part

    def build_content_parts(
        self,
        chapters: list[ChapterTranscript],
        selected_indices: list[int],
    ) -> list[ContentPart]:
        """
        Build transcript ContentPart objects from the selected chapter
        breakpoints.

        Args:
            chapters:
                Ordered transcript chapters.

            selected_indices:
                User-selected chapter indices.

                Every selected chapter becomes the FIRST chapter of a new
                transcript part.

                Example

                    Chapters:
                        C0 C1 C2 C3 C4 C5

                    selected_indices:
                        [2, 4]

                    Parts:
                        C0 C1
                        C2 C3
                        C4 C5
                
        Returns:
            List of ContentPart objects.

        Raises:
            InvalidBreakpointSelectionError
                If the selection is invalid or any generated part exceeds
                the configured token limit.
        """
        self.validate_selection(
            chapters=chapters,
            selected_indices=selected_indices,
        )

        groups = self._build_groups(
            chapters=chapters,
            selected_indices=selected_indices,
        )

        parts: list[ContentPart] = []

        for index, group in enumerate(groups):
            token_count = self.calculate_group_tokens(group)

            start_display = group[0].display
            end_display = (
                groups[index + 1][0].display
                if (index + 1) < len(groups)
                else None
            )

            part_title = self._build_part_title(
                start=start_display,
                end=end_display,
            )

            if token_count > self._max_tokens:
                raise InvalidBreakpointSelectionError(
                    (
                        "Transcript part exceeds the configured token limit. "
                        f"Part '{part_title}' contains "
                        f"{token_count:,} tokens "
                        f"(maximum {self._max_tokens:,})."
                    )
                )

            parts.append(
                ContentPart(
                    part_title=part_title,
                    content="\n\n".join(
                        chapter.transcript
                        for chapter in group
                    ),
                    tokens=token_count,
                )
            )

        return parts

    def validate_selection(
        self,
        chapters: list[ChapterTranscript],
        selected_indices: list[int],
    ) -> None:
        """
        Validate the user-selected chapter indices.

        Rules
        -----

        • At least one chapter must exist.
        • Selection may be empty (single part).
        • Indices must be integers.
        • Indices must be unique.
        • Indices must be ordered.
        • First chapter (index 0) cannot be selected because every transcript
          always begins from chapter 0.
        • Indices must exist.
        """
        if not chapters:
            raise InvalidBreakpointSelectionError(
                "Transcript contains no chapters."
            )

        if not selected_indices:
            return

        max_index = len(chapters) - 1

        if any(not isinstance(i, int) for i in selected_indices):
            raise InvalidBreakpointSelectionError(
                "All selected chapter indices must be integers."
            )

        if len(selected_indices) != len(set(selected_indices)):
            raise InvalidBreakpointSelectionError(
                "Duplicate chapter indices are not allowed."
            )

        if selected_indices != sorted(selected_indices):
            raise InvalidBreakpointSelectionError(
                "Chapter indices must be supplied in ascending order."
            )

        if selected_indices[0] == 0:
            raise InvalidBreakpointSelectionError(
                "The first transcript chapter is always included and cannot "
                "be selected as a breakpoint."
            )

        invalid = [
            index
            for index in selected_indices
            if index < 0 or index > max_index
        ]

        if invalid:
            raise InvalidBreakpointSelectionError(
                (
                    "Invalid chapter indices: "
                    f"{invalid}. Valid range: 1-{max_index}."
                )
            )

    def calculate_group_tokens(
        self,
        chapters: list[ChapterTranscript],
    ) -> int:
        """
        Calculate the total token count for a transcript part.
        """
        return sum(chapter.tokens for chapter in chapters)

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #

    def _build_groups(
        self,
        chapters: list[ChapterTranscript],
        selected_indices: list[int],
    ) -> list[list[ChapterTranscript]]:
        """
        Build transcript chapter groups.

        Example

            chapters:
                C0 C1 C2 C3 C4 C5

            selected_indices:
                [2, 4]

            returns

                [
                    [C0,C1],
                    [C2,C3],
                    [C4,C5],
                ]
        """
        boundaries = [0]
        boundaries.extend(selected_indices)
        boundaries.append(len(chapters))

        groups: list[list[ChapterTranscript]] = []

        for start, end in zip(boundaries[:-1], boundaries[1:]):
            groups.append(chapters[start:end])

        return groups

    def _build_part_title(
        self,
        start: str,
        end: str | None,
    ) -> str:
        """
        Generate filesystem-safe transcript part title.

        Examples

            00:00:00 -> 00:46:54

                00-00-00_00-46-54

            01:23:43 -> END

                01-23-43_END
        """
        start = self._normalise_timestamp(start)

        if end is not None:
            end = self._normalise_timestamp(end)
        else:
            end = "END"

        return f"{start}_{end}"

    @staticmethod
    def _normalise_timestamp(
        value: str,
    ) -> str:
        """
        Convert timestamp into a filesystem-safe representation.

        Examples

            00:00
                ->
            00-00

            01:23:44
                ->
            01-23-44
        """
        value = value.strip()

        value = re.sub(
            r"[^0-9:]",
            "",
            value,
        )

        return value.replace(":", "-")
