"""
deep_notes_ai/services/markdown/markdown_metadata_service.py

MarkdownMetadataService

Builds MarkdownMetadata from raw markdown content.

Since plain Markdown typically does not contain rich metadata, this service
extracts as much information as possible using lightweight heuristics while
remaining deterministic.
"""

from __future__ import annotations

import hashlib
import logging
import re
from pathlib import Path
from urllib.parse import urlparse

from deep_notes_ai.domain.models import (
    MarkdownMetadata,
    MarkdownMetadataError,
)
from deep_notes_ai.services.markdown.markdown_loader_service import MarkdownLoaderService

logger = logging.getLogger(__name__)


class MarkdownMetadataService:
    """
    Builds MarkdownMetadata from raw markdown.

    Extraction heuristics:

    - id:
        SHA-256 hash of the markdown content.

    - url:
        Original source string.

    - title:
        First H1 heading if present.
        Otherwise filename (for local files).
        Otherwise URL basename.
        Otherwise "Untitled".

    - description:
        First meaningful paragraph after the title.

    - author:
        Attempts to detect common author patterns.

    - upload_date:
        Attempts to detect common date patterns.
    """

    _MAX_DESCRIPTION_LENGTH = 500

    _AUTHOR_PATTERNS = (
        re.compile(r"^\*\*Author:\*\*\s*(.+)$", re.IGNORECASE),
        re.compile(r"^Author:\s*(.+)$", re.IGNORECASE),
        re.compile(r"^By\s+(.+)$", re.IGNORECASE),
    )

    _DATE_PATTERNS = (
        re.compile(r"^\*\*Date:\*\*\s*(.+)$", re.IGNORECASE),
        re.compile(r"^Date:\s*(.+)$", re.IGNORECASE),
        re.compile(r"^Published:\s*(.+)$", re.IGNORECASE),
        re.compile(r"^Published on:\s*(.+)$", re.IGNORECASE),
        re.compile(r"^Last updated:\s*(.+)$", re.IGNORECASE),
        re.compile(r"^Updated:\s*(.+)$", re.IGNORECASE),
    )

    _H1_PATTERN = re.compile(
        r"^\s*#\s+(.+?)\s*$",
        re.MULTILINE,
    )

    def build_metadata(
        self,
        source: str,
        markdown: str,
    ) -> MarkdownMetadata:
        """
        Build MarkdownMetadata.

        Args:
            source:
                Original markdown source (path or URL).

            markdown:
                Raw markdown document.

        Returns:
            MarkdownMetadata

        Raises:
            MarkdownMetadataError
        """
        if not markdown.strip():
            raise MarkdownMetadataError("Markdown content is empty.")

        try:
            title = self._extract_title(markdown, source)
            description = self._extract_description(markdown)
            author = self._extract_author(markdown)
            upload_date = self._extract_upload_date(markdown)
            content_id = self._generate_id(source=source, title=title)

            return MarkdownMetadata(
                id=content_id,
                url=source,
                title=title,
                description=description,
                upload_date=upload_date,
                author=author,
                raw_content=markdown,
            )

        except Exception as exc:
            if isinstance(exc, MarkdownMetadataError):
                raise

            raise MarkdownMetadataError(
                "Failed to build markdown metadata."
            ) from exc

    def _generate_id(
        self,
        source: str,
        title: str,
    ) -> str:
        """
        Generate a deterministic content ID from the source and title.
        """
        key = f"{source.strip()}::{title.strip()}"

        return hashlib.sha256(
            key.encode("utf-8")
        ).hexdigest()

    def _extract_title(
        self,
        markdown: str,
        source: str,
    ) -> str:
        """
        Extract document title.
        """
        match = self._H1_PATTERN.search(markdown)
        if match:
            return match.group(1).strip()
        
        if MarkdownLoaderService._is_url(source):
            path = urlparse(source).path
            name = Path(path).stem
        else:
            name = Path(source).stem

        if name:
            return name

        return "Untitled"

    def _extract_description(
        self,
        markdown: str,
    ) -> str:
        """
        Extract the first meaningful paragraph.
        """
        paragraphs = re.split(r"\n\s*\n", markdown)

        for paragraph in paragraphs:
            text = paragraph.strip()

            if not text:
                continue

            if text.startswith("#"):
                continue

            if text.startswith(">"):
                continue

            if text.startswith("<"):
                continue

            if text.startswith("```"):
                continue

            if text.startswith("- "):
                continue

            if text.startswith("* "):
                continue

            text = " ".join(text.split())

            if text:
                return text[: self._MAX_DESCRIPTION_LENGTH]

        return ""

    def _extract_author(
        self,
        markdown: str,
    ) -> str:
        """
        Extract author if present.
        """
        for line in markdown.splitlines():
            line = line.strip()

            for pattern in self._AUTHOR_PATTERNS:
                match = pattern.match(line)
                if match:
                    return match.group(1).strip()

        return ""

    def _extract_upload_date(
        self,
        markdown: str,
    ) -> str:
        """
        Extract upload/publication date if present.
        """
        for line in markdown.splitlines():
            line = line.strip()

            for pattern in self._DATE_PATTERNS:
                match = pattern.match(line)
                if match:
                    return match.group(1).strip()

        return ""
