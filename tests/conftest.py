"""
tests/conftest.py

Shared fixtures for all tests.
"""
import pytest

from deep_notes_ai.domain.models import (
    ContentPayload,
    ContentStoreItem,
    TopicNode,
    TranscriptHierarchy,
)


@pytest.fixture
def sample_content_points_text() -> str:
    return (
        "1. TypedDict defines state shape.\n"
        "2. State is passed to nodes.\n"
        "3. Nodes update state."
    )


@pytest.fixture
def sample_topic_node() -> TopicNode:
    return TopicNode(
        name="TypedDict",
        start_point=1,
        end_point=3,
        children=[
            TopicNode(name="CONTENT", start_point=1, end_point=3, children=[])
        ],
    )


@pytest.fixture
def sample_transcript_hierarchy(sample_topic_node: TopicNode) -> TranscriptHierarchy:
    return TranscriptHierarchy(hierarchy=[sample_topic_node])


@pytest.fixture
def sample_content_store_item() -> ContentStoreItem:
    return ContentStoreItem(
        content="## TypedDict\n\n- Defines state.",
        summary="TypedDict: defines state.",
    )


@pytest.fixture
def sample_content_payload() -> ContentPayload:
    return ContentPayload(
        id="test-uuid-1",
        hierarchy_path=["TypedDict"],
        range=(1, 3),
        content_points_list=[
            "1. TypedDict...",
            "2. State...",
            "3. Nodes...",
        ],
    )
