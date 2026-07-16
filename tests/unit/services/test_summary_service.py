"""
tests/unit/services/test_summary_service.py

Unit tests for SummaryService.

Mirrors test_content_service.py with SummaryService and ContentSummaryBatch.
"""
from __future__ import annotations

import pytest
from unittest.mock import Mock

from deep_notes_ai.domain.models import (
    ContentPayload,
    ContentStoreItem,
    ContentSummary,
    ContentSummaryBatch,
    SummaryGenerationError,
)
from deep_notes_ai.services.partition_service import PartitionService
from deep_notes_ai.services.retry_service import RetryService
from deep_notes_ai.services.summary_service import SummaryService
from deep_notes_ai.services.validation_service import ValidationService


# ============================================================================
# Fixtures and helpers
# ============================================================================

UUID_1 = "aaaaaaaa-0000-0000-0000-000000000001"
UUID_2 = "bbbbbbbb-0000-0000-0000-000000000002"

TRANSCRIPT_2_POINTS = "1. Point one here.\n2. Point two here."

PAYLOAD_1 = [
    ContentPayload(
        id=UUID_1,
        hierarchy_path=["Topic"],
        range=(1, 2),
        content_points_list=["1. Point one here.", "2. Point two here."],
    )
]

PAYLOAD_2 = [
    ContentPayload(
        id=UUID_1,
        hierarchy_path=["Topic", "Sub A"],
        range=(1, 1),
        content_points_list=["1. Point one here."],
    ),
    ContentPayload(
        id=UUID_2,
        hierarchy_path=["Topic", "Sub B"],
        range=(2, 2),
        content_points_list=["2. Point two here."],
    ),
]


def make_service(
    llm_chain: Mock,
    initial_partitions: int = 1,
    fallback_partitions: int = 2,
    max_retries: int = 2,
) -> SummaryService:
    return SummaryService(
        llm_chain=llm_chain,
        partition_service=PartitionService(),
        validation_service=ValidationService(),
        retry_service=RetryService(max_retries=max_retries),
        initial_partitions=initial_partitions,
        fallback_partitions=fallback_partitions,
    )


# ============================================================================
# test_successful_single_partition_summary
# ============================================================================

def test_successful_single_partition_summary() -> None:
    mock_chain = Mock()
    mock_chain.invoke.return_value = ContentSummaryBatch(
        items=[ContentSummary(id="N1", summary="Short summary.")]
    )
    service = make_service(mock_chain)
    nodes_content = {UUID_1: ContentStoreItem(content="## Topic\n\n- Point 1")}

    result = service.generate(
        transcript_text=TRANSCRIPT_2_POINTS,
        payload=PAYLOAD_1,
        nodes_content=nodes_content,
    )

    assert result[UUID_1].summary == "Short summary."
    mock_chain.invoke.assert_called_once()


# ============================================================================
# test_nodes_content_summary_field_populated
# ============================================================================

def test_nodes_content_summary_field_populated() -> None:
    mock_chain = Mock()
    mock_chain.invoke.return_value = ContentSummaryBatch(
        items=[ContentSummary(id="N1", summary="My summary.")]
    )
    service = make_service(mock_chain)
    result = service.generate(
        transcript_text=TRANSCRIPT_2_POINTS,
        payload=PAYLOAD_1,
        nodes_content={UUID_1: ContentStoreItem(content="Content text")},
    )
    assert result[UUID_1].summary == "My summary."


# ============================================================================
# test_content_field_preserved_after_summary
# ============================================================================

def test_content_field_preserved_after_summary() -> None:
    """The .content field on the result should be preserved, not overwritten."""
    mock_chain = Mock()
    mock_chain.invoke.return_value = ContentSummaryBatch(
        items=[ContentSummary(id="N1", summary="Sum")]
    )
    service = make_service(mock_chain)
    original_content = "## Existing content"
    result = service.generate(
        transcript_text=TRANSCRIPT_2_POINTS,
        payload=PAYLOAD_1,
        nodes_content={UUID_1: ContentStoreItem(content=original_content)},
    )
    assert result[UUID_1].content == original_content
    assert result[UUID_1].summary == "Sum"


# ============================================================================
# test_repartition_on_count_mismatch_summary
# ============================================================================

def test_repartition_on_count_mismatch_summary() -> None:
    call_count = [0]

    def fake_invoke(text: str) -> ContentSummaryBatch:
        call_count[0] += 1
        if call_count[0] == 1:
            return ContentSummaryBatch(items=[])  # wrong count
        return ContentSummaryBatch(
            items=[ContentSummary(id="N1", summary="Fallback summary")]
        )

    mock_chain = Mock()
    mock_chain.invoke.side_effect = fake_invoke
    service = make_service(mock_chain, initial_partitions=1, fallback_partitions=1)

    result = service.generate(
        transcript_text=TRANSCRIPT_2_POINTS,
        payload=PAYLOAD_1,
        nodes_content={UUID_1: ContentStoreItem(content="Content")},
    )
    assert result[UUID_1].summary == "Fallback summary"
    assert call_count[0] == 2


# ============================================================================
# test_retry_exhausted_raises_summary_generation_error
# ============================================================================

def test_retry_exhausted_raises_summary_generation_error() -> None:
    mock_chain = Mock()
    mock_chain.invoke.return_value = ContentSummaryBatch(
        items=[ContentSummary(id="WRONG", summary="Bad")]
    )
    service = make_service(mock_chain, initial_partitions=1, max_retries=2)

    with pytest.raises(SummaryGenerationError):
        service.generate(
            transcript_text=TRANSCRIPT_2_POINTS,
            payload=PAYLOAD_1,
            nodes_content={UUID_1: ContentStoreItem(content="Content")},
        )


# ============================================================================
# test_two_nodes_summary_populated_correctly
# ============================================================================

def test_two_nodes_summary_populated_correctly() -> None:
    mock_chain = Mock()
    mock_chain.invoke.return_value = ContentSummaryBatch(
        items=[
            ContentSummary(id="N1", summary="Summary A"),
            ContentSummary(id="N2", summary="Summary B"),
        ]
    )
    service = make_service(mock_chain, initial_partitions=1)

    result = service.generate(
        transcript_text=TRANSCRIPT_2_POINTS,
        payload=PAYLOAD_2,
        nodes_content={
            UUID_1: ContentStoreItem(content="Content A"),
            UUID_2: ContentStoreItem(content="Content B"),
        },
    )

    assert result[UUID_1].summary == "Summary A"
    assert result[UUID_2].summary == "Summary B"


# ============================================================================
# test_structured_content_payload_uses_content_field
# ============================================================================

def test_structured_content_payload_uses_content_field() -> None:
    """Verify the LLM input contains the .content from nodes_content."""
    captured_inputs: list[str] = []

    def fake_invoke(text: str) -> ContentSummaryBatch:
        captured_inputs.append(text)
        return ContentSummaryBatch(
            items=[ContentSummary(id="N1", summary="S")]
        )

    mock_chain = Mock()
    mock_chain.invoke.side_effect = fake_invoke
    service = make_service(mock_chain, initial_partitions=1)

    the_content = "## My structured markdown content"
    service.generate(
        transcript_text=TRANSCRIPT_2_POINTS,
        payload=PAYLOAD_1,
        nodes_content={UUID_1: ContentStoreItem(content=the_content)},
    )

    assert captured_inputs
    assert the_content in captured_inputs[0]
