"""
deep_notes_ai/services/partition_service.py

PartitionService — partition ContentPayload objects into approximately
equal-sized batches for batched LLM processing.
"""

from __future__ import annotations

import math

from deep_notes_ai.domain.models import ContentPayload, ContentStoreItem


class PartitionService:
    """
    Utility service for partitioning ContentPayload objects.

    Partitions are computed using the cumulative character length of each
    payload. Different public methods determine the character length from
    different sources (raw transcript points, generated structured content,
    summaries, etc.), while sharing the same partitioning algorithm.
    """

    def partition_payloads_by_transcript(
        self,
        payloads: list[ContentPayload],
        partitions: int,
    ) -> list[list[ContentPayload]]:
        """
        Partition payloads using the length of their transcript points.

        Character length for each payload is calculated as the total length
        of all strings in ``payload.content_points_list``.
        """
        lengths = [
            sum(len(point) for point in payload.content_points_list)
            for payload in payloads
        ]

        return self._partition_payloads(payloads, lengths, partitions)

    def partition_payloads_by_content(
        self,
        payloads: list[ContentPayload],
        nodes_content: dict[str, ContentStoreItem],
        partitions: int,
    ) -> list[list[ContentPayload]]:
        """
        Partition payloads using the length of generated structured content.

        Character length for each payload is calculated from
        ``nodes_content[payload.id].content``.
        """
        lengths = [
            len(nodes_content[payload.id].content)
            for payload in payloads
        ]

        return self._partition_payloads(payloads, lengths, partitions)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _partition_payloads(
        self,
        payloads: list[ContentPayload],
        lengths: list[int],
        partitions: int,
    ) -> list[list[ContentPayload]]:
        """
        Partition payloads according to the supplied item lengths.
        """
        boundaries = self._compute_partition_boundaries(
            lengths=lengths,
            partitions=partitions,
        )

        result: list[list[ContentPayload]] = []

        start = 0
        for end in boundaries:
            result.append(payloads[start:end])
            start = end

        return result

    @staticmethod
    def _compute_partition_boundaries(
        lengths: list[int],
        partitions: int,
    ) -> list[int]:
        """
        Compute partition boundaries for items with the given lengths.

        The algorithm attempts to distribute the cumulative character length
        as evenly as possible across the requested number of partitions.

        Returns:
            A list containing the exclusive end index of each partition.

        Example:
            lengths = [100, 150, 80, 120, 200]
            partitions = 2

            Returns:
                [3, 5]
        """
        if partitions <= 0:
            raise ValueError("partitions must be greater than zero.")

        if not lengths:
            return []

        total_length = sum(lengths)

        boundaries: list[int] = []

        cumulative = 0
        current_index = 0

        for part in range(1, partitions + 1):
            target_length = math.ceil(total_length * part / partitions)

            while (
                current_index < len(lengths)
                and cumulative < target_length
            ):
                cumulative += lengths[current_index]
                current_index += 1

            boundaries.append(current_index)

        boundaries[-1] = len(lengths)

        return boundaries