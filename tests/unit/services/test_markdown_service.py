"""
tests/unit/services/test_markdown_service.py

Unit tests for MarkdownService.

No I/O, no LLM. Uses in-memory TitleNode/ContentNode objects and dict.
"""
import pytest

from deep_notes_ai.domain.models import (
    ContentNode,
    ContentStoreItem,
    TitleNode,
)
from deep_notes_ai.services.markdown_service import MarkdownService


@pytest.fixture
def service() -> MarkdownService:
    return MarkdownService()


# ============================================================================
# test_content_title_becomes_h1
# ============================================================================

def test_content_title_becomes_h1(service: MarkdownService) -> None:
    result = service.build_document(
        content_title="My Course",
        hierarchy=[],
        content_store={},
    )
    assert result.startswith("# My Course")


# ============================================================================
# test_single_content_node
# ============================================================================

def test_single_content_node(service: MarkdownService) -> None:
    uuid = "uuid-1"
    content_store = {uuid: ContentStoreItem(content="## Section\n\n- Point 1")}
    hierarchy = [ContentNode(id=uuid)]

    result = service.build_document("Title", hierarchy, content_store)

    assert "## Section\n\n- Point 1" in result


# ============================================================================
# test_title_node_with_child_content_node
# ============================================================================

def test_title_node_with_child_content_node(service: MarkdownService) -> None:
    uuid = "uuid-2"
    content_store = {uuid: ContentStoreItem(content="Content text here.")}
    hierarchy = [
        TitleNode(
            name="Topic A",
            subtopics=[ContentNode(id=uuid)],
        )
    ]

    result = service.build_document("Title", hierarchy, content_store)

    assert "## Topic A" in result
    assert "Content text here." in result


# ============================================================================
# test_nested_title_nodes_increment_heading_level
# ============================================================================

def test_nested_title_nodes_increment_heading_level(service: MarkdownService) -> None:
    uuid = "uuid-3"
    content_store = {uuid: ContentStoreItem(content="Leaf content.")}
    hierarchy = [
        TitleNode(
            name="Root",
            subtopics=[
                TitleNode(
                    name="Child",
                    subtopics=[ContentNode(id=uuid)],
                )
            ],
        )
    ]

    result = service.build_document("Title", hierarchy, content_store)

    assert "## Root" in result
    assert "### Child" in result
    assert "Leaf content." in result


# ============================================================================
# test_summary_flag_uses_summary_field
# ============================================================================

def test_summary_flag_uses_summary_field(service: MarkdownService) -> None:
    uuid = "uuid-4"
    content_store = {
        uuid: ContentStoreItem(
            content="Full content.",
            summary="Short summary.",
        )
    }
    hierarchy = [ContentNode(id=uuid)]

    result = service.build_document("Title", hierarchy, content_store, summary=True)

    assert "Short summary." in result
    assert "Full content." not in result


# ============================================================================
# test_content_flag_uses_content_field
# ============================================================================

def test_content_flag_uses_content_field(service: MarkdownService) -> None:
    uuid = "uuid-5"
    content_store = {
        uuid: ContentStoreItem(
            content="Full content.",
            summary="Short summary.",
        )
    }
    hierarchy = [ContentNode(id=uuid)]

    result = service.build_document("Title", hierarchy, content_store, summary=False)

    assert "Full content." in result
    assert "Short summary." not in result


# ============================================================================
# test_document_ends_with_newline
# ============================================================================

def test_document_ends_with_newline(service: MarkdownService) -> None:
    result = service.build_document("Title", [], {})
    assert result.endswith("\n")


# ============================================================================
# test_multi_root_nodes
# ============================================================================

def test_multi_root_nodes(service: MarkdownService) -> None:
    uuid_a = "uuid-a"
    uuid_b = "uuid-b"
    content_store = {
        uuid_a: ContentStoreItem(content="Content A."),
        uuid_b: ContentStoreItem(content="Content B."),
    }
    hierarchy = [
        TitleNode(name="Alpha", subtopics=[ContentNode(id=uuid_a)]),
        TitleNode(name="Beta", subtopics=[ContentNode(id=uuid_b)]),
    ]

    result = service.build_document("Title", hierarchy, content_store)

    assert "## Alpha" in result
    assert "## Beta" in result
    assert "Content A." in result
    assert "Content B." in result


# ============================================================================
# test_empty_content_omitted
# ============================================================================

def test_empty_content_omitted(service: MarkdownService) -> None:
    uuid = "uuid-empty"
    content_store = {uuid: ContentStoreItem(content="", summary="")}
    hierarchy = [ContentNode(id=uuid)]

    result = service.build_document("Title", hierarchy, content_store)

    # The document should just be the title
    stripped = result.strip()
    assert stripped == "# Title"


# ============================================================================
# test_title_node_at_root_produces_h2_heading
# ============================================================================

def test_title_node_at_root_produces_h2_heading(service: MarkdownService) -> None:
    hierarchy = [TitleNode(name="Section", subtopics=[])]
    result = service.build_document("Title", hierarchy, {})
    assert "## Section" in result


# ============================================================================
# test_deeply_nested_heading_levels
# ============================================================================

def test_deeply_nested_heading_levels(service: MarkdownService) -> None:
    uuid = "deep"
    content_store = {uuid: ContentStoreItem(content="Deep content.")}
    hierarchy = [
        TitleNode(
            name="L1",
            subtopics=[
                TitleNode(
                    name="L2",
                    subtopics=[
                        TitleNode(
                            name="L3",
                            subtopics=[ContentNode(id=uuid)],
                        )
                    ],
                )
            ],
        )
    ]

    result = service.build_document("Title", hierarchy, content_store)

    assert "## L1" in result
    assert "### L2" in result
    assert "#### L3" in result
    assert "Deep content." in result
