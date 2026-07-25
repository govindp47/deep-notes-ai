"""
deep_notes_ai/services/article/article_metadata_service.py

ArticleMetadataService

Responsible for extracting article metadata from downloaded HTML and
constructing the project's ArticleMetadata domain model.

Responsibilities:
    • Extract metadata from HTML.
    • Apply sensible fallback values.
    • Normalize metadata.
    • Construct ArticleMetadata.

This service intentionally performs NO HTTP requests.

This service intentionally performs NO article body extraction.

This service intentionally performs NO document structure parsing.

Input:
    - source URL
    - raw HTML

Output:
    - ArticleMetadata
"""

from __future__ import annotations

import hashlib
import logging
import re
from datetime import datetime
from dateutil.parser import ParserError
from email.utils import parsedate_to_datetime
from typing import Callable, NamedTuple
from urllib.parse import parse_qsl, urlencode, urljoin, urlparse, urlunparse

import trafilatura
from bs4 import BeautifulSoup
from dateutil import parser as date_parser
from trafilatura.settings import Document

from deep_notes_ai.domain.models import (
    ArticleMetadata,
    ArticleMetadataError,
)

logger = logging.getLogger(__name__)


class MetadataField(NamedTuple):
    value: str
    source: str


class ArticleMetadataService:
    """
    Builds an ArticleMetadata object from raw HTML.

    Metadata is extracted primarily using Trafilatura. Missing values are
    recovered using common HTML metadata tags before sensible defaults are
    applied.

    The returned model is compatible with the existing PipelineState and the
    remainder of the pipeline.
    """

    _TITLE_META_KEYS = (
        "og:title",
        "twitter:title",
        "dc.title",
        "headline",
    )

    _DESCRIPTION_META_KEYS = (
        "description",
        "og:description",
        "twitter:description",
        "dc.description",
    )

    _AUTHOR_META_KEYS = (
        "author",
        "article:author",
        "og:author",
        "parsely-author",
        "dc.creator",
        "dc.creator.author",
        "dc.contributor",
        "byl",
        "byline",
    )

    _PUBLISH_DATE_META_KEYS = (
        "article:published_time",
        "article:modified_time",
        "publish_date",
        "publication_date",
        "date",
        "dc.date",
        "dc.date.issued",
        "pubdate",
    )

    def build_metadata(
        self,
        url: str,
        html: str,
    ) -> ArticleMetadata:
        """
        Build an ArticleMetadata object.

        Args:
            url:
                Original article URL.

            html:
                Raw downloaded HTML.

        Returns:
            ArticleMetadata

        Raises:
            ArticleMetadataError
        """
        logger.info("Extracting article metadata.")

        if not html.strip():
            raise ArticleMetadataError(
                "Cannot extract metadata from empty HTML."
            )

        try:
            extracted: Document = trafilatura.extract_metadata(html)
        except Exception as exc:
            logger.exception(
                "Trafilatura metadata extraction failed."
            )
            raise ArticleMetadataError(
                f"Metadata extraction failed: {exc}"
            ) from exc

        soup: BeautifulSoup | None = None
        meta_name: dict[str, str] = {}
        meta_property: dict[str, str] = {}
        canonical_url: str | None = None

        def get_soup() -> BeautifulSoup:
            nonlocal soup, meta_name, meta_property, canonical_url

            if soup is None:
                soup = BeautifulSoup(html, "lxml")
                (
                    meta_name,
                    meta_property,
                ) = self._build_meta_cache(soup)
                canonical_url = self._canonical_url(soup, url)

            return soup
        
        def cached_meta(*names: str) -> str:
            get_soup()
            return self._cached_meta_property(
                meta_name,
                meta_property,
                *names,
            )

        title_field = self._extract_field(
            extracted,
            "title",
            lambda: (
                cached_meta(
                    *self._TITLE_META_KEYS,
                )
                or self._html_title(get_soup())
            ),
            default="Untitled Article",
        )

        description_field = self._extract_field(
            extracted,
            "description",
            lambda: cached_meta(
                *self._DESCRIPTION_META_KEYS,
            ),
        )

        author_field = self._extract_field(
            extracted,
            "author",
            lambda: cached_meta(
                *self._AUTHOR_META_KEYS,
            ),
        )

        publish_date_field = self._extract_field(
            extracted,
            "date",
            lambda: cached_meta(
                *self._PUBLISH_DATE_META_KEYS,
            ),
        )

        get_soup()

        description = self._normalize_description(description_field.value)
        author = self._normalize_author(author_field.value)
        publish_date = self._normalize_publish_date(publish_date_field.value)
        final_url = self._normalize_url(canonical_url or url)
        content_id = self._build_content_id(final_url)

        metadata = ArticleMetadata(
            id=content_id,
            url=final_url,
            title=title_field.value,
            description=description,
            upload_date=publish_date,
            author=author,
            raw_html=html,
        )

        logger.info(
            "Metadata extracted successfully.",
            extra={
                "content_id": metadata.id,
                "url": metadata.url,
                "title": metadata.title,
                "title_source": title_field.source,
                "description_source": description_field.source,
                "author": metadata.author,
                "author_source": author_field.source,
                "publish_date": metadata.upload_date,
                "publish_date_source": publish_date_field.source,
            },
        )

        return metadata

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #

    def _extract_field(
        self,
        metadata: Document | None,
        metadata_attribute: str,
        fallback: Callable[[], str],
        default: str = "",
    ) -> MetadataField:
        """
        Extract a metadata field using the following priority:

        1. Trafilatura metadata
        2. HTML fallback
        3. Default value

        Returns both the extracted value and the source used.
        """
        value = self._metadata_value(
            metadata,
            metadata_attribute,
        )

        if value:
            return MetadataField(value, "trafilatura")

        value = fallback()

        if value:
            return MetadataField(value, "html")

        return MetadataField(default, "default")

    @staticmethod
    def _metadata_value(
        metadata: Document | None,
        attribute: str,
    ) -> str:
        """
        Safely read a Trafilatura metadata attribute.
        """
        if metadata is None:
            return ""

        value = getattr(metadata, attribute, None)

        if value is None:
            return ""

        if isinstance(value, str):
            return value.strip()

        if isinstance(value, datetime):
            return value.isoformat()

        return str(value).strip()
    
    @staticmethod
    def _build_content_id(
        url: str,
    ) -> str:
        """
        Generate a deterministic collision-resistant identifier.

        The identifier is derived from a normalized canonical URL to ensure
        stable IDs across repeated ingestions.
        """
        return hashlib.sha256(
            url.encode("utf-8")
        ).hexdigest()[:16]

    @staticmethod
    def _normalize_description(
        description: str,
    ) -> str:
        """
        Normalize article description whitespace.
        """
        if not description:
            return ""

        return " ".join(description.split())

    @staticmethod
    def _normalize_author(
        author: str,
    ) -> str:
        """
        Normalize author names.

        Removes common prefixes while preserving the author name.
        """
        if not author:
            return ""

        author = author.strip()

        author = re.sub(
            r"^(by|author)\s*[:\-]?\s*",
            "",
            author,
            flags=re.IGNORECASE,
        )

        return " ".join(author.split())

    @staticmethod
    def _normalize_publish_date(
        publish_date: str,
    ) -> str:
        """
        Normalize publish dates into ISO-8601 format whenever possible.
        """
        if not publish_date:
            return ""

        publish_date = publish_date.strip()

        try:
            return date_parser.parse(
                publish_date
            ).isoformat()
        except (ParserError, TypeError, ValueError):
            pass

        try:
            return parsedate_to_datetime(
                publish_date
            ).isoformat()
        except (TypeError, ValueError):
            pass

        return publish_date

    @staticmethod
    def _html_title(
        soup: BeautifulSoup,
    ) -> str:
        """
        Extract the HTML <title>.
        """
        if soup.title is None or soup.title.string is None:
            return ""

        return soup.title.string.strip()

    @staticmethod
    def _canonical_url(
        soup: BeautifulSoup,
        base_url: str,
    ) -> str:
        """
        Extract and normalize the canonical URL.

        Relative canonical URLs are resolved against the original URL.
        """
        for tag in soup.find_all("link"):
            rel = tag.get("rel")

            if not rel:
                continue

            if isinstance(rel, str):
                rel_values = {
                    value.lower()
                    for value in rel.split()
                }
            else:
                rel_values = {
                    value.lower()
                    for value in rel
                }

            if "canonical" not in rel_values:
                continue

            href = tag.get("href")

            if href:
                return urljoin(
                    base_url,
                    href.strip(),
                )

        return ""
    
    @staticmethod
    def _normalize_url(url: str) -> str:
        """
        Normalize a URL before generating a content identifier.

        Normalization performed:

        - Remove URL fragment (#...)
        - Remove common tracking query parameters (utm_*, fbclid, gclid, etc.)
        - Remove trailing slash from non-root paths
        """
        parsed = urlparse(url)

        tracking_prefixes = ("utm_",)

        tracking_keys = {
            "fbclid",
            "gclid",
            "mc_cid",
            "mc_eid",
        }

        filtered_query = [
            (key, value)
            for key, value in parse_qsl(
                parsed.query,
                keep_blank_values=True,
            )
            if (
                not key.startswith(tracking_prefixes)
                and key not in tracking_keys
            )
        ]

        path = parsed.path

        if path != "/":
            path = path.rstrip("/")

        normalized = parsed._replace(
            scheme=parsed.scheme.lower(),
            netloc=parsed.netloc.lower(),
            path=path,
            query=urlencode(filtered_query),
            fragment="",
        )

        return urlunparse(normalized)

    @staticmethod
    def _build_meta_cache(
        soup: BeautifulSoup,
    ) -> tuple[dict[str, str], dict[str, str]]:
        """
        Build lookup tables for all HTML metadata.

        This avoids repeated DOM traversals when resolving multiple metadata
        fields.
        """
        meta_name: dict[str, str] = {}
        meta_property: dict[str, str] = {}

        for tag in soup.find_all("meta"):
            content = tag.get("content")

            if not content:
                continue

            content = content.strip()

            name = tag.get("name")
            if name:
                meta_name[name.strip().lower()] = content

            prop = tag.get("property")
            if prop:
                meta_property[prop.strip().lower()] = content

        return meta_name, meta_property

    @staticmethod
    def _cached_meta_property(
        meta_name: dict[str, str],
        meta_property: dict[str, str],
        *names: str,
    ) -> str:
        """
        Retrieve metadata from cached HTML metadata lookups.
        """
        for name in names:
            key = name.strip().lower()

            if key in meta_name:
                return meta_name[key]

            if key in meta_property:
                return meta_property[key]

        return ""
