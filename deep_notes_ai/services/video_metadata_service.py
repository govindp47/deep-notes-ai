"""
deep_notes_ai/services/video_metadata_service.py

VideoMetadataService — fetch metadata (ID, title, etc) from a YouTube URL.
"""
from __future__ import annotations

import logging
import re
import urllib.request
import urllib.error
from typing import TYPE_CHECKING
from urllib.parse import urlparse

from deep_notes_ai.domain.models import InvalidYoutubeUrlError, VideoMetadataError

if TYPE_CHECKING:
    from deep_notes_ai.config.settings import Settings

logger = logging.getLogger(__name__)


class VideoMetadataService:
    """
    Validates YouTube URLs and fetches watch page metadata without external libraries.
    """

    # Matches standard 11-character YouTube video IDs
    ID_REGEX = re.compile(r"^[a-zA-Z0-9_-]{11}$")

    # Patterns inspired by the notebook implementation for robust extraction
    URL_PATTERNS = [
        re.compile(r"(?:https?://)?(?:www\.)?youtube\.com/watch\?(?:.*&)?v=([a-zA-Z0-9_-]{11})"),
        re.compile(r"(?:https?://)?(?:www\.)?youtu\.be/([a-zA-Z0-9_-]{11})"),
        re.compile(r"(?:https?://)?(?:www\.)?youtube\.com/embed/([a-zA-Z0-9_-]{11})"),
        re.compile(r"(?:https?://)?(?:www\.)?youtube\.com/shorts/([a-zA-Z0-9_-]{11})"),
        re.compile(r"(?:https?://)?(?:www\.)?youtube\.com/v/([a-zA-Z0-9_-]{11})"),
        re.compile(r"(?:https?://)?(?:www\.)?youtube\.com/live/([a-zA-Z0-9_-]{11})"),
    ]

    def __init__(self, settings: "Settings"):
        self.settings = settings
        self.timeout = settings.youtube_request_timeout
        self.user_agent = settings.youtube_user_agent

    def validate_youtube_url(self, url: str) -> None:
        """
        Validate that a URL is a reasonably well-formed string before regex matching.
        """
        if not url or not isinstance(url, str):
            raise InvalidYoutubeUrlError("URL must be a non-empty string.")
        
        url_stripped = url.strip()
        if len(url_stripped) > 2000:
            raise InvalidYoutubeUrlError("URL is excessively long.")
            
        # If it's just an 11-char ID, it's valid for our purposes
        if self.ID_REGEX.match(url_stripped):
            return
            
        try:
            parsed = urlparse(url_stripped if "://" in url_stripped else f"https://{url_stripped}")
            if parsed.netloc and not parsed.netloc.endswith(("youtube.com", "youtu.be")):
                raise InvalidYoutubeUrlError(f"Invalid host in URL: {parsed.netloc}")
        except ValueError as exc:
            raise InvalidYoutubeUrlError(f"Malformed URL: {url_stripped}") from exc

    def extract_content_id(self, url: str) -> str:
        """
        Extract the 11-character YouTube video ID from various URL formats.
        Raises InvalidYoutubeUrlError if extraction fails.
        """
        self.validate_youtube_url(url)
        url_stripped = url.strip()

        # If it's already an 11-char ID, just return it
        if self.ID_REGEX.match(url_stripped):
            return url_stripped

        for pattern in self.URL_PATTERNS:
            match = pattern.search(url_stripped)
            if match:
                content_id = match.group(1)
                # Double-check length just in case
                if len(content_id) == 11:
                    return content_id

        raise InvalidYoutubeUrlError(f"Could not extract a valid 11-character video ID from: {url}")

    def normalize_url(self, content_id: str) -> str:
        """
        Normalize a video ID into the canonical watch URL.
        """
        if not self.ID_REGEX.match(content_id):
            raise InvalidYoutubeUrlError(f"Invalid video ID format for normalization: {content_id}")
        return f"https://www.youtube.com/watch?v={content_id}"

    def fetch_video_metadata(self, content_id: str) -> dict[str, str]:
        """
        Fetch HTML from the YouTube watch page and extract metadata using regex.
        Does NOT raise on missing metadata; returns what it can find.
        """
        url = self.normalize_url(content_id)
        logger.info("Fetching metadata for content_id=%s from %s", content_id, url)
        
        req = urllib.request.Request(
            url, 
            headers={"User-Agent": self.user_agent}
        )
        
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                html = response.read().decode("utf-8", errors="ignore")
        except urllib.error.URLError as exc:
            logger.warning("Failed to fetch metadata for %s: %s", content_id, exc)
            return self._fallback_metadata(content_id)
        except Exception as exc:
            logger.warning("Unexpected error fetching metadata for %s: %s", content_id, exc)
            return self._fallback_metadata(content_id)

        # Parse HTML
        metadata = {}
        
        # 1. Title
        title_match = re.search(r"<title>(.*?) - YouTube</title>", html)
        if title_match:
            metadata["content_title"] = title_match.group(1).strip()
        else:
            # Try og:title
            og_match = re.search(r'<meta property="og:title" content="(.*?)">', html)
            if og_match:
                metadata["content_title"] = og_match.group(1).strip()
            else:
                metadata["content_title"] = self._fallback_metadata(content_id)["content_title"]

        # 2. Upload Date
        date_match = re.search(r'<meta itemprop="uploadDate" content="(.*?)">', html)
        if date_match:
            metadata["upload_date"] = date_match.group(1).strip()

        # 3. Channel Name
        channel_match = re.search(r'<link itemprop="name" content="(.*?)">', html)
        if channel_match:
            metadata["author_name"] = channel_match.group(1).strip()
            
        logger.info("Metadata fetched successfully for content_id=%s", content_id)
        return metadata

    def _fallback_metadata(self, content_id: str) -> dict[str, str]:
        """
        Return sensible defaults when metadata extraction fails.
        """
        logger.info("Using fallback metadata for content_id=%s", content_id)
        return {
            "content_title": f"YouTube Video ({content_id})"
        }
