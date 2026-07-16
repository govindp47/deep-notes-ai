"""
tests/unit/services/test_partition_service.py

Unit tests for PartitionService.
"""
import pytest

from deep_notes_ai.services.partition_service import PartitionService


@pytest.fixture
def service() -> PartitionService:
    return PartitionService()


# Sample 6-point transcript text
SAMPLE_SIX_POINTS = (
    "1. First point here.\n"
    "2. Second point here.\n"
    "3. Third point here.\n"
    "4. Fourth point here.\n"
    "5. Fifth point here.\n"
    "6. Sixth point here."
)

# Sample 3-point transcript text
SAMPLE_THREE_POINTS = (
    "1. A.\n"
    "2. B.\n"
    "3. C."
)


# ---------------------------------------------------------------------------
# compute_last_points
# ---------------------------------------------------------------------------

def test_compute_last_points_n_equals_one(service: PartitionService) -> None:
    result = service.compute_last_points(SAMPLE_SIX_POINTS, n=1)
    assert result == [6]


def test_compute_last_points_n_equals_four(service: PartitionService) -> None:
    result = service.compute_last_points(SAMPLE_SIX_POINTS, n=4)
    assert len(result) == 4
    # Last boundary must always be the last point
    assert result[-1] == 6


def test_compute_last_points_n_equals_two_three_points(service: PartitionService) -> None:
    result = service.compute_last_points(SAMPLE_THREE_POINTS, n=2)
    assert len(result) == 2
    assert result[-1] == 3


def test_compute_last_points_n_greater_than_point_count(service: PartitionService) -> None:
    # n=10 but only 3 points — returns 10 boundaries, all clamped to last point
    result = service.compute_last_points(SAMPLE_THREE_POINTS, n=10)
    assert result[-1] == 3
    assert len(result) == 10


def test_compute_last_points_empty_transcript(service: PartitionService) -> None:
    result = service.compute_last_points("", n=4)
    assert result == []


def test_compute_last_points_n_zero_raises(service: PartitionService) -> None:
    with pytest.raises(ValueError):
        service.compute_last_points(SAMPLE_SIX_POINTS, n=0)


def test_compute_last_points_n_negative_raises(service: PartitionService) -> None:
    with pytest.raises(ValueError):
        service.compute_last_points(SAMPLE_SIX_POINTS, n=-1)


# ---------------------------------------------------------------------------
# compute_ranges
# ---------------------------------------------------------------------------

def test_compute_ranges_from_last_points(service: PartitionService) -> None:
    ranges = service.compute_ranges([145, 287, 421])
    assert ranges == [(1, 145), (146, 287), (288, 421)]


def test_single_partition_range(service: PartitionService) -> None:
    ranges = service.compute_ranges([10])
    assert ranges == [(1, 10)]


def test_compute_ranges_empty_list(service: PartitionService) -> None:
    ranges = service.compute_ranges([])
    assert ranges == []


def test_compute_ranges_two_partitions(service: PartitionService) -> None:
    ranges = service.compute_ranges([5, 10])
    assert ranges == [(1, 5), (6, 10)]
