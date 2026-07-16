import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from langchain_core.runnables import Runnable

from deep_notes_ai.domain.models import ContentStoreItem, TranscriptHierarchy, TopicNode, LLMCallError
from deep_notes_ai.langgraph_pipeline.nodes.extract_transcript import make_extract_transcript_node
from deep_notes_ai.langgraph_pipeline.nodes.clean_transcript import make_clean_transcript_node
from deep_notes_ai.langgraph_pipeline.nodes.generate_hierarchy import make_generate_hierarchy_node
from deep_notes_ai.langgraph_pipeline.nodes.number_transcript import make_number_transcript_node
from deep_notes_ai.langgraph_pipeline.nodes.generate_content import make_generate_content_node
from deep_notes_ai.services.persistence_service import PersistenceService


@pytest.fixture
def persistence_service(tmp_path: Path):
    return PersistenceService()


@pytest.fixture
def state(tmp_path: Path):
    return {
        "content_id": "test_video",
        "current_run_dir": tmp_path,
        "raw_content": "raw text",
        "transcript_token_count": 100,
        "cleaned_content": "- bullet 1",
        "content_points": "1. bullet 1",
        "content_payload": [],
        "nodes_content": {"uuid-1": ContentStoreItem()},
    }


def test_extract_transcript_cache_hit(persistence_service, state, tmp_path):
    artifact_path = tmp_path / "artifacts" / "raw_content.txt"
    persistence_service.save_text(artifact_path, "cached raw text")

    mock_transcript_service = MagicMock()
    mock_tokenizer_service = MagicMock()
    mock_tokenizer_service.count_tokens.return_value = 42

    node = make_extract_transcript_node(
        persistence_service, mock_transcript_service, mock_tokenizer_service
    )
    result = node(state)

    assert result["raw_content"] == "cached raw text"
    assert result["transcript_token_count"] == 42
    mock_transcript_service.fetch.assert_not_called()


def test_extract_transcript_cache_miss(persistence_service, state, tmp_path):
    mock_transcript_service = MagicMock()
    mock_transcript_service.fetch.return_value = "new raw text"
    mock_tokenizer_service = MagicMock()
    mock_tokenizer_service.count_tokens.return_value = 7

    node = make_extract_transcript_node(
        persistence_service, mock_transcript_service, mock_tokenizer_service
    )
    result = node(state)

    assert result["raw_content"] == "new raw text"
    assert result["transcript_token_count"] == 7
    mock_transcript_service.fetch.assert_called_once_with("test_video")

    artifact_path = tmp_path / "artifacts" / "raw_content.txt"
    assert persistence_service.load_text(artifact_path) == "new raw text"


def test_clean_transcript_cache_hit(persistence_service, state, tmp_path):
    artifact_path = tmp_path / "artifacts" / "cleaned_content.txt"
    persistence_service.save_text(artifact_path, "cached cleaned text")

    mock_chain = MagicMock(spec=Runnable)

    node = make_clean_transcript_node(mock_chain, persistence_service, chunk_tokens=6000)
    result = node(state)

    assert result["cleaned_content"] == "cached cleaned text"
    mock_chain.invoke.assert_not_called()


def test_number_transcript_cache_hit(persistence_service, state, tmp_path):
    artifact_path = tmp_path / "artifacts" / "content_points.txt"
    persistence_service.save_text(artifact_path, "1. cached point")

    node = make_number_transcript_node(persistence_service)
    result = node(state)

    assert result["content_points"] == ["1. cached point"]


def test_generate_hierarchy_cache_hit(persistence_service, state, tmp_path):
    artifact_path = tmp_path / "artifacts" / "raw_hierarchy.json"
    hierarchy = TranscriptHierarchy(hierarchy=[TopicNode(name="Test", start_point=1, end_point=1)])
    persistence_service.save_hierarchy(artifact_path, hierarchy)

    mock_chain = MagicMock(spec=Runnable)

    node = make_generate_hierarchy_node(mock_chain, persistence_service)
    result = node(state)

    assert result["raw_hierarchy"].hierarchy[0].name == "Test"
    mock_chain.invoke.assert_not_called()


def test_generate_hierarchy_corrupted_cache(persistence_service, state, tmp_path):
    artifact_path = tmp_path / "artifacts" / "raw_hierarchy.json"
    persistence_service.save_text(artifact_path, "invalid json")

    mock_chain = MagicMock(spec=Runnable)
    hierarchy = TranscriptHierarchy(hierarchy=[TopicNode(name="New", start_point=1, end_point=1)])
    mock_chain.invoke.return_value = hierarchy

    node = make_generate_hierarchy_node(mock_chain, persistence_service)
    result = node(state)

    # Should fall back to generating
    assert result["raw_hierarchy"].hierarchy[0].name == "New"
    mock_chain.invoke.assert_called_once()


def test_generate_content_cache_hit(persistence_service, state, tmp_path):
    artifact_path = tmp_path / "artifacts" / "nodes_content.json"

    # Save partial nodes_content where .content is populated
    cached_nodes = {"uuid-1": ContentStoreItem(content="cached content", summary="")}
    persistence_service.save_nodes_content(artifact_path, cached_nodes)

    mock_content_service = MagicMock()

    node = make_generate_content_node(mock_content_service, persistence_service)
    result = node(state)

    assert result["nodes_content"]["uuid-1"].content == "cached content"
    mock_content_service.generate.assert_not_called()



def test_generate_content_partial_cache_miss(persistence_service, state, tmp_path):
    artifact_path = tmp_path / "artifacts" / "nodes_content.json"

    # Missing .content
    cached_nodes = {"uuid-1": ContentStoreItem(content="", summary="")}
    persistence_service.save_nodes_content(artifact_path, cached_nodes)

    mock_content_service = MagicMock()
    updated_nodes = {"uuid-1": ContentStoreItem(content="new content", summary="")}
    mock_content_service.generate.return_value = updated_nodes

    node = make_generate_content_node(mock_content_service, persistence_service)
    result = node(state)

    assert result["nodes_content"]["uuid-1"].content == "new content"
    mock_content_service.generate.assert_called_once()

