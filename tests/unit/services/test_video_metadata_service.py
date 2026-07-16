"""
Tests for VideoMetadataService.
"""
import urllib.error
from unittest.mock import MagicMock, patch

import pytest

from deep_notes_ai.domain.models import InvalidYoutubeUrlError
from deep_notes_ai.services.video_metadata_service import VideoMetadataService


@pytest.fixture
def settings(mocker):
    """Mocked settings."""
    mock_settings = mocker.MagicMock()
    mock_settings.youtube_request_timeout = 5
    mock_settings.youtube_user_agent = "TestAgent"
    return mock_settings


@pytest.fixture
def service(settings):
    return VideoMetadataService(settings)


class TestVideoMetadataServiceValidation:

    def test_validate_youtube_url_success(self, service):
        service.validate_youtube_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        service.validate_youtube_url("youtu.be/dQw4w9WgXcQ")

    def test_validate_youtube_url_empty(self, service):
        with pytest.raises(InvalidYoutubeUrlError, match="non-empty string"):
            service.validate_youtube_url("")

    def test_validate_youtube_url_excessively_long(self, service):
        long_url = "https://youtube.com/watch?v=" + "a" * 2000
        with pytest.raises(InvalidYoutubeUrlError, match="excessively long"):
            service.validate_youtube_url(long_url)

    def test_validate_youtube_url_invalid_host(self, service):
        with pytest.raises(InvalidYoutubeUrlError, match="Invalid host"):
            service.validate_youtube_url("https://vimeo.com/123456")


class TestVideoMetadataServiceExtraction:

    @pytest.mark.parametrize(
        "url,expected",
        [
            ("dQw4w9WgXcQ", "dQw4w9WgXcQ"),
            ("https://www.youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ"),
            ("http://youtube.com/watch?v=dQw4w9WgXcQ&t=42s", "dQw4w9WgXcQ"),
            ("https://youtu.be/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
            ("https://www.youtube.com/embed/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
            ("https://www.youtube.com/shorts/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
            ("https://www.youtube.com/v/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
            ("https://www.youtube.com/live/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ],
    )
    def test_extract_content_id_success(self, service, url, expected):
        assert service.extract_content_id(url) == expected

    def test_extract_content_id_invalid(self, service):
        with pytest.raises(InvalidYoutubeUrlError, match="Could not extract"):
            service.extract_content_id("https://www.youtube.com/watch?v=short")

    def test_normalize_url(self, service):
        assert service.normalize_url("dQw4w9WgXcQ") == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

    def test_normalize_url_invalid(self, service):
        with pytest.raises(InvalidYoutubeUrlError):
            service.normalize_url("bad-id")


class TestVideoMetadataServiceFetching:

    def test_fetch_metadata_success(self, service):
        html_content = b'''
        <html>
            <title>Test Video Title - YouTube</title>
            <meta itemprop="uploadDate" content="2023-01-01">
            <link itemprop="name" content="Test Channel">
        </html>
        '''
        mock_response = MagicMock()
        mock_response.read.return_value = html_content
        mock_response.__enter__.return_value = mock_response

        with patch("urllib.request.urlopen", return_value=mock_response):
            metadata = service.fetch_video_metadata("dQw4w9WgXcQ")

        assert metadata == {
            "content_title": "Test Video Title",
            "upload_date": "2023-01-01",
            "author_name": "Test Channel"
        }

    def test_fetch_metadata_og_title_fallback(self, service):
        html_content = b'''
        <html>
            <meta property="og:title" content="Test OG Title">
        </html>
        '''
        mock_response = MagicMock()
        mock_response.read.return_value = html_content
        mock_response.__enter__.return_value = mock_response

        with patch("urllib.request.urlopen", return_value=mock_response):
            metadata = service.fetch_video_metadata("dQw4w9WgXcQ")

        assert metadata["content_title"] == "Test OG Title"
        assert "upload_date" not in metadata
        assert "author_name" not in metadata

    def test_fetch_metadata_network_error(self, service):
        with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("Timeout")):
            metadata = service.fetch_video_metadata("dQw4w9WgXcQ")

        assert metadata == {
            "content_title": "YouTube Video (dQw4w9WgXcQ)"
        }
