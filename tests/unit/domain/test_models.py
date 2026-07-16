"""
tests/unit/domain/test_models.py

Unit tests for deep_notes_ai/domain/models.py.
Tests model construction and invariants — no I/O, no LLM.
"""
import pytest

from deep_notes_ai.domain.models import (
    ContentNode,
    ContentStoreItem,
    ContentSummary,
    ContentSummaryBatch,
    StructuredContent,
    StructuredContentBatch,
    TitleNode,
    TopicNode,
    TranscriptHierarchy,
)


# ============================================================================
# ContentStoreItem
# ============================================================================

def test_content_store_item_default_empty_strings():
    item = ContentStoreItem()
    assert item.content == ""
    assert item.summary == ""


def test_content_store_item_with_values():
    item = ContentStoreItem(content="## Hello", summary="Hello world.")
    assert item.content == "## Hello"
    assert item.summary == "Hello world."


# ============================================================================
# ContentNode
# ============================================================================

def test_content_node_type_literal():
    node = ContentNode()
    assert node.type == "content"


def test_content_node_with_id():
    node = ContentNode(id="some-uuid")
    assert node.id == "some-uuid"
    assert node.type == "content"


# ============================================================================
# TitleNode
# ============================================================================

def test_title_node_type_literal():
    node = TitleNode()
    assert node.type == "topic"


def test_title_node_default_empty_subtopics():
    node = TitleNode(name="Introduction")
    assert node.name == "Introduction"
    assert node.subtopics == []


def test_title_node_with_children():
    child = ContentNode(id="child-uuid")
    node = TitleNode(name="Topic A", subtopics=[child])
    assert len(node.subtopics) == 1
    assert node.subtopics[0].id == "child-uuid"


# ============================================================================
# TopicNode (Pydantic)
# ============================================================================

def test_topic_node_content_sentinel():
    """TopicNode with name='CONTENT' is the leaf sentinel."""
    node = TopicNode(name="CONTENT", start_point=1, end_point=1, children=[])
    assert node.name == "CONTENT"
    assert node.children == []


def test_topic_node_with_children():
    child = TopicNode(name="CONTENT", start_point=1, end_point=3, children=[])
    parent = TopicNode(
        name="TypedDict",
        start_point=1,
        end_point=3,
        children=[child],
    )
    assert parent.name == "TypedDict"
    assert len(parent.children) == 1
    assert parent.children[0].name == "CONTENT"


def test_topic_node_default_empty_children():
    node = TopicNode(name="Test", start_point=1, end_point=5)
    assert node.children == []


def test_topic_node_start_end_point():
    node = TopicNode(name="Intro", start_point=10, end_point=20)
    assert node.start_point == 10
    assert node.end_point == 20


# ============================================================================
# TranscriptHierarchy (Pydantic)
# ============================================================================

def test_transcript_hierarchy_model_validate_from_dict():
    th = TranscriptHierarchy.model_validate({"hierarchy": []})
    assert th.hierarchy == []


def test_transcript_hierarchy_with_nodes():
    data = {
        "hierarchy": [
            {
                "name": "LangGraph",
                "start_point": 1,
                "end_point": 10,
                "children": [
                    {
                        "name": "CONTENT",
                        "start_point": 1,
                        "end_point": 5,
                        "children": [],
                    }
                ],
            }
        ]
    }
    th = TranscriptHierarchy.model_validate(data)
    assert len(th.hierarchy) == 1
    assert th.hierarchy[0].name == "LangGraph"
    assert th.hierarchy[0].children[0].name == "CONTENT"


# ============================================================================
# StructuredContentBatch (Pydantic)
# ============================================================================

def test_structured_content_batch_item_count():
    batch = StructuredContentBatch(
        items=[
            StructuredContent(id="N1", markdown="## A\n\n- Point 1"),
            StructuredContent(id="N2", markdown="## B\n\n- Point 2"),
        ]
    )
    assert len(batch.items) == 2
    assert batch.items[0].id == "N1"
    assert batch.items[1].id == "N2"


def test_structured_content_batch_empty():
    batch = StructuredContentBatch(items=[])
    assert batch.items == []


# ============================================================================
# ContentSummaryBatch (Pydantic)
# ============================================================================

def test_content_summary_batch_item_count():
    batch = ContentSummaryBatch(
        items=[
            ContentSummary(id="N1", summary="Short summary."),
            ContentSummary(id="N2", summary="Another summary."),
            ContentSummary(id="N3", summary="Third summary."),
        ]
    )
    assert len(batch.items) == 3
    assert batch.items[2].summary == "Third summary."


def test_content_summary_batch_empty():
    batch = ContentSummaryBatch(items=[])
    assert batch.items == []
