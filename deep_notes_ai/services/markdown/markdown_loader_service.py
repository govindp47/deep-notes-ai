"""
deep_notes_ai/services/markdown/markdown_loader_service.py

MarkdownLoaderService

Loads markdown content from either:
- a local filesystem path
- a remote HTTP(S) URL

Raises MarkdownLoadError if the source is invalid or the markdown cannot be
loaded.
"""

from __future__ import annotations

import logging
from pathlib import Path
from urllib.parse import urlparse

import requests

from deep_notes_ai.domain.models import MarkdownLoadError, PersistenceError
from deep_notes_ai.services.persistence_service import PersistenceService

logger = logging.getLogger(__name__)


class MarkdownLoaderService:
    """
    Service responsible for loading markdown from either a local file
    or a remote URL.
    """

    _REQUEST_TIMEOUT_SECONDS = 30

    def __init__(
        self,
        persistence_service: PersistenceService,
    ) -> None:
        """
        Initialize the markdown loader service.

        Args:
            persistence_service:

        """
        self._persistence_service = persistence_service

    def load(
        self,
        source: str,
    ) -> str:
        """
        Load markdown from a filesystem path or URL.

        Args:
            source:
                Local markdown path or HTTP(S) URL.

        Returns:
            Markdown content.

        Raises:
            MarkdownLoadError
        """
        if self._is_url(source):
            return self._load_from_url(source)

        return self._load_from_file(Path(source))

    def _load_from_file(
        self,
        path: Path,
    ) -> str:
        """
        Load markdown from a local file.

        Raises:
            MarkdownLoadError
        """
        logger.info("Loading markdown file: %s", path)

        if not path.exists():
            raise MarkdownLoadError(
                f"Markdown file does not exist: {path}"
            )

        if not path.is_file():
            raise MarkdownLoadError(
                f"Markdown path is not a file: {path}"
            )

        if path.suffix.lower() != ".md":
            raise MarkdownLoadError(
                f"Expected a markdown (.md) file, got: {path}"
            )

        try:
            content = self._persistence_service.load_text(path=path)
        except PersistenceError as exc:
            raise MarkdownLoadError(
                f"Failed to read markdown file: {path}"
                f"{exc}"
            ) from exc

        if not content.strip():
            raise MarkdownLoadError(
                f"Markdown file is empty: {path}"
            )

        return content

    def _load_from_url(
        self,
        url: str,
    ) -> str:
        """
        Load markdown from a remote URL.

        Raises:
            MarkdownLoadError
        """
        logger.info("Downloading markdown from URL: %s", url)

        try:
            response = requests.get(
                url,
                timeout=self._REQUEST_TIMEOUT_SECONDS,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            raise MarkdownLoadError(
                f"Failed to download markdown from URL: {url}"
            ) from exc

        content = response.text

        if not content.strip():
            raise MarkdownLoadError(
                f"Downloaded markdown is empty: {url}"
            )

        return content

    @staticmethod
    def _is_url(
        source: str,
    ) -> bool:
        """
        Return True if the source is an HTTP(S) URL.
        """
        parsed = urlparse(source)
        return parsed.scheme in {"http", "https"} and bool(parsed.netloc)