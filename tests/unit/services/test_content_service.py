"""
tests/unit/services/test_content_service.py

Unit tests for ContentService.

LLM chain is mocked as a Mock with configurable return values.
No real LLM calls.
"""
from __future__ import annotations

import pytest
from unittest.mock import Mock, patch

from deep_notes_ai.domain.models import (
    BatchCountMismatchError,
    ContentGenerationError,
    ContentPayload,
    ContentStoreItem,
    DuplicateIdsError,
    IncorrectIdsError,
    RetryExhaustedError,
    StructuredContent,
    StructuredContentBatch,
)
from deep_notes_ai.services.content_service import ContentService
from deep_notes_ai.services.partition_service import PartitionService
from deep_notes_ai.services.retry_service import RetryService
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

EMPTY_NODES: dict[str, ContentStoreItem] = {
    UUID_1: ContentStoreItem(),
    UUID_2: ContentStoreItem(),
}


def make_service(
    llm_chain: Mock,
    initial_partitions: int = 1,
    fallback_partitions: int = 2,
    max_retries: int = 2,
) -> ContentService:
    return ContentService(
        llm_chain=llm_chain,
        partition_service=PartitionService(),
        validation_service=ValidationService(),
        retry_service=RetryService(max_retries=max_retries),
        initial_partitions=initial_partitions,
        fallback_partitions=fallback_partitions,
    )


# ============================================================================
# test_successful_single_partition
# ============================================================================

def test_successful_single_partition() -> None:
    mock_chain = Mock()
    mock_chain.invoke.return_value = StructuredContentBatch(
        items=[StructuredContent(id="N1", markdown="## Topic\n\n- Point 1")]
    )
    service = make_service(mock_chain, initial_partitions=1)
    nodes_content: dict[str, ContentStoreItem] = {UUID_1: ContentStoreItem()}

    result = service.generate(
        transcript_text=TRANSCRIPT_2_POINTS,
        payload=PAYLOAD_1,
        nodes_content=nodes_content,
    )

    assert result[UUID_1].content == "## Topic\n\n- Point 1"
    mock_chain.invoke.assert_called_once()


# ============================================================================
# test_nodes_content_content_field_populated
# ============================================================================

def test_nodes_content_content_field_populated() -> None:
    mock_chain = Mock()
    mock_chain.invoke.return_value = StructuredContentBatch(
        items=[StructuredContent(id="N1", markdown="Content here")]
    )
    service = make_service(mock_chain)
    result = service.generate(
        transcript_text=TRANSCRIPT_2_POINTS,
        payload=PAYLOAD_1,
        nodes_content={UUID_1: ContentStoreItem()},
    )
    assert result[UUID_1].content == "Content here"


# ============================================================================
# test_nodes_content_returned_with_all_uuids
# ============================================================================

def test_nodes_content_returned_with_all_uuids() -> None:
    """All UUIDs in the payload must be present in the result."""
    mock_chain = Mock()
    mock_chain.invoke.return_value = StructuredContentBatch(
        items=[
            StructuredContent(id="N1", markdown="Content A"),
            StructuredContent(id="N2", markdown="Content B"),
        ]
    )
    service = make_service(mock_chain, initial_partitions=1)
    result = service.generate(
        transcript_text=TRANSCRIPT_2_POINTS,
        payload=PAYLOAD_2,
        nodes_content={UUID_1: ContentStoreItem(), UUID_2: ContentStoreItem()},
    )
    assert UUID_1 in result
    assert UUID_2 in result
    assert result[UUID_1].content == "Content A"
    assert result[UUID_2].content == "Content B"


# ============================================================================
# test_temp_id_mapping_is_correct
# ============================================================================

def test_temp_id_mapping_is_correct() -> None:
    """Verify N1 maps to first UUID, N2 to second."""
    captured_inputs: list[str] = []

    def fake_invoke(text: str) -> StructuredContentBatch:
        captured_inputs.append(text)
        return StructuredContentBatch(
            items=[
                StructuredContent(id="N1", markdown="A"),
                StructuredContent(id="N2", markdown="B"),
            ]
        )

    mock_chain = Mock()
    mock_chain.invoke.side_effect = fake_invoke
    service = make_service(mock_chain, initial_partitions=1)

    result = service.generate(
        transcript_text=TRANSCRIPT_2_POINTS,
        payload=PAYLOAD_2,
        nodes_content={UUID_1: ContentStoreItem(), UUID_2: ContentStoreItem()},
    )

    assert result[UUID_1].content == "A"
    assert result[UUID_2].content == "B"


# ============================================================================
# test_uuid_restored_from_temp_id
# ============================================================================

def test_uuid_restored_from_temp_id() -> None:
    """Real UUIDs must not be exposed to LLM; N-IDs used instead."""
    mock_chain = Mock()
    mock_chain.invoke.return_value = StructuredContentBatch(
        items=[StructuredContent(id="N1", markdown="Answer")]
    )
    service = make_service(mock_chain)
    result = service.generate(
        transcript_text=TRANSCRIPT_2_POINTS,
        payload=PAYLOAD_1,
        nodes_content={UUID_1: ContentStoreItem()},
    )
    assert UUID_1 in result
    # Ensure the LLM received N1, not the real UUID
    call_arg = mock_chain.invoke.call_args[0][0]
    assert UUID_1 not in call_arg
    assert "N1" in call_arg


# ============================================================================
# test_repartition_on_count_mismatch
# ============================================================================

def test_repartition_on_count_mismatch() -> None:
    """On BatchCountMismatchError, ContentService retries with fallback partitions."""
    call_count = [0]

    def fake_invoke(text: str) -> StructuredContentBatch:
        call_count[0] += 1
        if call_count[0] == 1:
            # First partition call: return wrong count to trigger mismatch
            return StructuredContentBatch(items=[])  # 0 items, expected 1
        # Subsequent call (fallback): correct response
        return StructuredContentBatch(
            items=[StructuredContent(id="N1", markdown="Fallback content")]
        )

    mock_chain = Mock()
    mock_chain.invoke.side_effect = fake_invoke
    service = make_service(mock_chain, initial_partitions=1, fallback_partitions=1)

    result = service.generate(
        transcript_text=TRANSCRIPT_2_POINTS,
        payload=PAYLOAD_1,
        nodes_content={UUID_1: ContentStoreItem()},
    )
    assert result[UUID_1].content == "Fallback content"
    assert call_count[0] == 2


# ============================================================================
# test_retry_on_duplicate_ids
# ============================================================================

def test_retry_on_duplicate_ids() -> None:
    """DuplicateIdsError causes retry within same partition."""
    call_count = [0]

    def fake_invoke(text: str) -> StructuredContentBatch:
        call_count[0] += 1
        if call_count[0] == 1:
            # First attempt: duplicate IDs
            return StructuredContentBatch(
                items=[
                    StructuredContent(id="N1", markdown="A"),
                    StructuredContent(id="N1", markdown="B"),  # duplicate
                ]
            )
        # Second attempt: correct
        return StructuredContentBatch(
            items=[StructuredContent(id="N1", markdown="Retry success")]
        )

    mock_chain = Mock()
    mock_chain.invoke.side_effect = fake_invoke
    service = make_service(mock_chain, initial_partitions=1, max_retries=3)

    result = service.generate(
        transcript_text=TRANSCRIPT_2_POINTS,
        payload=PAYLOAD_1,
        nodes_content={UUID_1: ContentStoreItem()},
    )
    assert result[UUID_1].content == "Retry success"
    assert call_count[0] == 2


# ============================================================================
# test_retry_on_incorrect_ids
# ============================================================================

def test_retry_on_incorrect_ids() -> None:
    """IncorrectIdsError causes retry within same partition."""
    call_count = [0]

    def fake_invoke(text: str) -> StructuredContentBatch:
        call_count[0] += 1
        if call_count[0] == 1:
            return StructuredContentBatch(
                items=[StructuredContent(id="WRONG", markdown="Bad")]
            )
        return StructuredContentBatch(
            items=[StructuredContent(id="N1", markdown="Correct")]
        )

    mock_chain = Mock()
    mock_chain.invoke.side_effect = fake_invoke
    service = make_service(mock_chain, initial_partitions=1, max_retries=3)

    result = service.generate(
        transcript_text=TRANSCRIPT_2_POINTS,
        payload=PAYLOAD_1,
        nodes_content={UUID_1: ContentStoreItem()},
    )
    assert result[UUID_1].content == "Correct"


# ============================================================================
# test_retry_exhausted_raises_content_generation_error
# ============================================================================

def test_retry_exhausted_raises_content_generation_error() -> None:
    """If retries are exhausted, ContentGenerationError is raised."""
    mock_chain = Mock()
    mock_chain.invoke.return_value = StructuredContentBatch(
        items=[StructuredContent(id="WRONG", markdown="Bad")]
    )
    service = make_service(mock_chain, initial_partitions=1, max_retries=2)

    with pytest.raises(ContentGenerationError):
        service.generate(
            transcript_text=TRANSCRIPT_2_POINTS,
            payload=PAYLOAD_1,
            nodes_content={UUID_1: ContentStoreItem()},
        )


# ============================================================================
# test_successful_four_partitions
# ============================================================================

def test_successful_four_partitions() -> None:
    """With 4 partitions on a 2-point transcript, each partition gets filtered."""
    mock_chain = Mock()
    # With only 2 transcript points, 4 partitions will reduce to 1-2 actual calls
    # (empty partitions are skipped). At minimum one call with N1.
    mock_chain.invoke.return_value = StructuredContentBatch(
        items=[StructuredContent(id="N1", markdown="Done")]
    )
    service = make_service(mock_chain, initial_partitions=4)

    result = service.generate(
        transcript_text=TRANSCRIPT_2_POINTS,
        payload=PAYLOAD_1,
        nodes_content={UUID_1: ContentStoreItem()},
    )
    assert result[UUID_1].content == "Done"
