"""
Tests for extract_video_metadata node.
"""
from unittest.mock import MagicMock

import pytest

from deep_notes_ai.domain.models import InvalidYoutubeUrlError
from deep_notes_ai.langgraph_pipeline.nodes.extract_video_metadata import make_extract_video_metadata_node
from deep_notes_ai.langgraph_pipeline.state import PipelineState
from deep_notes_ai.services.video_metadata_service import VideoMetadataService


@pytest.fixture
def mock_service():
    service = MagicMock(spec=VideoMetadataService)
    service.extract_content_id.return_value = "dQw4w9WgXcQ"
    service.normalize_url.return_value = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    service.fetch_video_metadata.return_value = {
        "content_title": "Test Title",
        "upload_date": "2023-01-01",
        "author_name": "Test Channel"
    }
    return service


def test_extract_video_metadata_success(mock_service):
    node = make_extract_video_metadata_node(mock_service)
    state: PipelineState = {"source": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"}
    
    result = node(state)
    
    mock_service.extract_content_id.assert_called_once_with("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    mock_service.fetch_video_metadata.assert_called_once_with("dQw4w9WgXcQ")
    
    from pathlib import Path
    assert result == {
        "current_run_dir": Path("output") / "dQw4w9WgXcQ",
        "content_id": "dQw4w9WgXcQ",
        "content_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "content_title": "Test Title",
        "upload_date": "2023-01-01",
        "author_name": "Test Channel"
    }


def test_extract_video_metadata_invalid_url(mock_service):
    mock_service.extract_content_id.side_effect = InvalidYoutubeUrlError("Invalid URL")
    node = make_extract_video_metadata_node(mock_service)
    state: PipelineState = {"source": "invalid"}
    
    with pytest.raises(InvalidYoutubeUrlError):
        node(state)
