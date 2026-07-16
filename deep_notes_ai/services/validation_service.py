"""
deep_notes_ai/services/validation_service.py

ValidationService — validates that an LLM batch response has the correct IDs.
"""
from __future__ import annotations

from deep_notes_ai.domain.models import (
    BatchCountMismatchError,
    ContentSummaryBatch,
    DuplicateIdsError,
    IncorrectIdsError,
    StructuredContentBatch,
)


class ValidationService:
    """
    Validates LLM batch response item counts and IDs.

    Three distinct exception types allow callers to handle each failure
    mode differently:
    - BatchCountMismatchError → repartition (do not retry)
    - DuplicateIdsError       → retry the same partition
    - IncorrectIdsError       → retry the same partition
    """

    def validate_batch(
        self,
        response: StructuredContentBatch | ContentSummaryBatch,
        expected_ids: set[str],
        entity_name: str = "CONTENT node",
    ) -> None:
        """
        Validate that the LLM batch response contains exactly the expected IDs.

        Args:
            response:      The structured LLM response (batch).
            expected_ids:  The set of temporary IDs (e.g. {"N1", "N2"}) that
                           the batch should contain.
            entity_name:   Human-readable name for error messages.

        Raises:
            BatchCountMismatchError: if the item count differs from expected.
            DuplicateIdsError:       if any ID appears more than once.
            IncorrectIdsError:       if the IDs don't match the expected set.
        """
        items = response.items
        expected_count = len(expected_ids)
        actual_count = len(items)

        # 1. Count check first — it's cheapest and most common failure.
        if actual_count != expected_count:
            raise BatchCountMismatchError(
                expected=expected_count,
                actual=actual_count,
            )

        # 2. Duplicate ID check.
        returned_ids: list[str] = [item.id for item in items]
        seen: set[str] = set()
        duplicates: list[str] = []
        for rid in returned_ids:
            if rid in seen:
                duplicates.append(rid)
            seen.add(rid)

        if duplicates:
            raise DuplicateIdsError(duplicates=duplicates)

        # 3. Exact ID match check.
        returned_id_set = set(returned_ids)
        if returned_id_set != expected_ids:
            missing = sorted(expected_ids - returned_id_set)
            unexpected = sorted(returned_id_set - expected_ids)
            raise IncorrectIdsError(missing=missing, unexpected=unexpected)
