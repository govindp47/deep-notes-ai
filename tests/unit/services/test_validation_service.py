"""
tests/unit/services/test_validation_service.py

Unit tests for ValidationService.

All tests use stub StructuredContentBatch / ContentSummaryBatch objects.
No LLM calls.
"""
import pytest

from deep_notes_ai.domain.models import (
    BatchCountMismatchError,
    ContentSummary,
    ContentSummaryBatch,
    DuplicateIdsError,
    IncorrectIdsError,
    StructuredContent,
    StructuredContentBatch,
)
from deep_notes_ai.services.validation_service import ValidationService


@pytest.fixture
def service() -> ValidationService:
    return ValidationService()


# ---------------------------------------------------------------------------
# Helper factories
# ---------------------------------------------------------------------------

def make_content_batch(ids: list[str]) -> StructuredContentBatch:
    return StructuredContentBatch(
        items=[StructuredContent(id=iid, markdown=f"Content for {iid}") for iid in ids]
    )


def make_summary_batch(ids: list[str]) -> ContentSummaryBatch:
    return ContentSummaryBatch(
        items=[ContentSummary(id=iid, summary=f"Summary for {iid}") for iid in ids]
    )


# ---------------------------------------------------------------------------
# test_valid_batch_does_not_raise
# ---------------------------------------------------------------------------

def test_valid_batch_does_not_raise(service: ValidationService) -> None:
    batch = make_content_batch(["N1", "N2", "N3"])
    # Should not raise
    service.validate_batch(batch, expected_ids={"N1", "N2", "N3"})


def test_single_item_batch_valid(service: ValidationService) -> None:
    batch = make_content_batch(["N1"])
    service.validate_batch(batch, expected_ids={"N1"})


def test_valid_summary_batch_does_not_raise(service: ValidationService) -> None:
    batch = make_summary_batch(["N1", "N2"])
    service.validate_batch(batch, expected_ids={"N1", "N2"})


# ---------------------------------------------------------------------------
# test_count_mismatch_raises_batch_count_mismatch_error
# ---------------------------------------------------------------------------

def test_count_mismatch_raises_batch_count_mismatch_error(service: ValidationService) -> None:
    batch = make_content_batch(["N1", "N2"])  # 2 items
    with pytest.raises(BatchCountMismatchError) as exc_info:
        service.validate_batch(batch, expected_ids={"N1", "N2", "N3"})  # expected 3
    assert exc_info.value.expected == 3
    assert exc_info.value.actual == 2


def test_count_mismatch_too_many_items(service: ValidationService) -> None:
    batch = make_content_batch(["N1", "N2", "N3", "N4"])  # 4 items
    with pytest.raises(BatchCountMismatchError) as exc_info:
        service.validate_batch(batch, expected_ids={"N1", "N2"})
    assert exc_info.value.expected == 2
    assert exc_info.value.actual == 4


# ---------------------------------------------------------------------------
# test_duplicate_ids_raises_duplicate_ids_error
# ---------------------------------------------------------------------------

def test_duplicate_ids_raises_duplicate_ids_error(service: ValidationService) -> None:
    batch = make_content_batch(["N1", "N1"])  # duplicate N1
    with pytest.raises(DuplicateIdsError) as exc_info:
        service.validate_batch(batch, expected_ids={"N1", "N2"})
    assert "N1" in exc_info.value.duplicates


def test_duplicate_ids_error_lists_all_duplicates(service: ValidationService) -> None:
    batch = make_content_batch(["N1", "N1", "N2", "N2"])
    with pytest.raises(DuplicateIdsError) as exc_info:
        service.validate_batch(batch, expected_ids={"N1", "N2", "N3", "N4"})
    assert set(exc_info.value.duplicates) == {"N1", "N2"}


# ---------------------------------------------------------------------------
# test_incorrect_ids_raises_incorrect_ids_error
# ---------------------------------------------------------------------------

def test_incorrect_ids_raises_incorrect_ids_error(service: ValidationService) -> None:
    batch = make_content_batch(["N1", "N3"])  # N3 unexpected, N2 missing
    with pytest.raises(IncorrectIdsError) as exc_info:
        service.validate_batch(batch, expected_ids={"N1", "N2"})
    assert "N2" in exc_info.value.missing
    assert "N3" in exc_info.value.unexpected


def test_correct_count_wrong_ids_raises_incorrect_ids_error(service: ValidationService) -> None:
    batch = make_content_batch(["N1", "WRONG"])  # same count, wrong IDs
    with pytest.raises(IncorrectIdsError) as exc_info:
        service.validate_batch(batch, expected_ids={"N1", "N2"})
    assert "N2" in exc_info.value.missing
    assert "WRONG" in exc_info.value.unexpected


def test_incorrect_ids_error_attributes_populated(service: ValidationService) -> None:
    batch = make_content_batch(["N99"])
    with pytest.raises(IncorrectIdsError) as exc_info:
        service.validate_batch(batch, expected_ids={"N1"})
    err = exc_info.value
    assert "N1" in err.missing
    assert "N99" in err.unexpected
