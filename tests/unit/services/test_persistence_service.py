"""
tests/unit/services/test_persistence_service.py

Unit tests for PersistenceService.

Uses tmp_path fixture for real file I/O (no network calls).
"""
import json
from pathlib import Path

import pytest

from deep_notes_ai.domain.models import (
    ContentNode,
    ContentStoreItem,
    PersistenceError,
    TitleNode,
)
from deep_notes_ai.services.persistence_service import PersistenceService


@pytest.fixture
def service(tmp_path: Path) -> PersistenceService:
    return PersistenceService()


# ---------------------------------------------------------------------------
# save_text / load_text
# ---------------------------------------------------------------------------

def test_save_and_load_text_roundtrip(service: PersistenceService, tmp_path: Path) -> None:
    path = tmp_path / "output.txt"
    text = "Hello, World!\nLine 2."
    service.save_text(path, text)
    assert service.load_text(path) == text


def test_save_text_creates_parent_dirs(service: PersistenceService, tmp_path: Path) -> None:
    path = tmp_path / "nested" / "dir" / "file.txt"
    service.save_text(path, "content")
    assert path.exists()


def test_load_text_missing_file_raises_persistence_error(
    service: PersistenceService, tmp_path: Path
) -> None:
    with pytest.raises(PersistenceError):
        service.load_text(tmp_path / "nonexistent.txt")


# ---------------------------------------------------------------------------
# save_json / load_json
# ---------------------------------------------------------------------------

def test_save_and_load_json_roundtrip(service: PersistenceService, tmp_path: Path) -> None:
    path = tmp_path / "data.json"
    obj = {"key": "value", "list": [1, 2, 3]}
    service.save_json(path, obj)
    loaded = service.load_json(path)
    assert loaded == obj


def test_load_json_missing_file_raises_persistence_error(
    service: PersistenceService, tmp_path: Path
) -> None:
    with pytest.raises(PersistenceError):
        service.load_json(tmp_path / "missing.json")


# ---------------------------------------------------------------------------
# save_nodes_hierarchy / load_nodes_hierarchy
# ---------------------------------------------------------------------------

def test_save_and_load_nodes_hierarchy_roundtrip(
    service: PersistenceService, tmp_path: Path
) -> None:
    path = tmp_path / "hierarchy.json"
    nodes = [
        TitleNode(
            name="Topic A",
            subtopics=[
                ContentNode(id="uuid-1"),
                TitleNode(
                    name="Sub B",
                    subtopics=[ContentNode(id="uuid-2")],
                ),
            ],
        )
    ]
    service.save_nodes_hierarchy(path, nodes)
    loaded = service.load_nodes_hierarchy(path)

    assert len(loaded) == 1
    root = loaded[0]
    assert isinstance(root, TitleNode)
    assert root.name == "Topic A"
    assert len(root.subtopics) == 2
    assert isinstance(root.subtopics[0], ContentNode)
    assert root.subtopics[0].id == "uuid-1"
    assert isinstance(root.subtopics[1], TitleNode)
    assert root.subtopics[1].name == "Sub B"
    assert root.subtopics[1].subtopics[0].id == "uuid-2"


def test_save_nodes_hierarchy_content_node(
    service: PersistenceService, tmp_path: Path
) -> None:
    path = tmp_path / "single_content.json"
    nodes = [ContentNode(id="some-uuid")]
    service.save_nodes_hierarchy(path, nodes)
    loaded = service.load_nodes_hierarchy(path)
    assert len(loaded) == 1
    assert isinstance(loaded[0], ContentNode)
    assert loaded[0].id == "some-uuid"


# ---------------------------------------------------------------------------
# save_nodes_content / load_nodes_content
# ---------------------------------------------------------------------------

def test_save_and_load_nodes_content_roundtrip(
    service: PersistenceService, tmp_path: Path
) -> None:
    path = tmp_path / "content.json"
    content = {
        "uuid-1": ContentStoreItem(content="## Topic\n\n- Point 1", summary="Short."),
        "uuid-2": ContentStoreItem(content="## Other\n\n- Point 2", summary="Brief."),
    }
    service.save_nodes_content(path, content)
    loaded = service.load_nodes_content(path)

    assert set(loaded.keys()) == {"uuid-1", "uuid-2"}
    assert loaded["uuid-1"].content == "## Topic\n\n- Point 1"
    assert loaded["uuid-1"].summary == "Short."
    assert loaded["uuid-2"].content == "## Other\n\n- Point 2"


def test_save_nodes_content_empty_dict(
    service: PersistenceService, tmp_path: Path
) -> None:
    path = tmp_path / "empty.json"
    service.save_nodes_content(path, {})
    loaded = service.load_nodes_content(path)
    assert loaded == {}


# ---------------------------------------------------------------------------
# save_markdown
# ---------------------------------------------------------------------------

def test_save_markdown_creates_file(
    service: PersistenceService, tmp_path: Path
) -> None:
    path = tmp_path / "doc.md"
    markdown = "# Title\n\nSome content.\n"
    service.save_markdown(path, markdown)
    assert path.exists()
    assert path.read_text(encoding="utf-8") == markdown


# ---------------------------------------------------------------------------
# parent_directories_created_automatically
# ---------------------------------------------------------------------------

def test_parent_directories_created_automatically(
    service: PersistenceService, tmp_path: Path
) -> None:
    deep_path = tmp_path / "a" / "b" / "c" / "deep.txt"
    service.save_text(deep_path, "deep content")
    assert deep_path.exists()
    assert deep_path.read_text() == "deep content"
