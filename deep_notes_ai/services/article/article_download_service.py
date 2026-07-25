"""
deep_notes_ai/services/article/article_download_service.py

ArticleDownloadService

Responsible for downloading raw HTML from article-like web pages.

Responsibilities:
    • Validate article URLs.
    • Download HTML.
    • Follow redirects.
    • Apply browser-like request headers.
    • Translate HTTP/network failures into typed domain exceptions.

This service intentionally performs NO parsing.

Output:
    Raw HTML string only.
"""

from __future__ import annotations

import ipaddress
import logging
import time
from urllib.parse import urlparse

import httpx

from deep_notes_ai.config.settings import Settings
from deep_notes_ai.domain.models import ArticleDownloadError

logger = logging.getLogger(__name__)


class ArticleDownloadService:
    """
    Service responsible for downloading article HTML.

    This service is intentionally independent from any extraction logic.
    HTML parsing, metadata extraction and chapter generation belong to
    downstream services.
    """

    _SUPPORTED_SCHEMES = frozenset({"http", "https"})
    _SUPPORTED_CONTENT_TYPES = (
        "text/html",
        "application/xhtml+xml",
    )
    _MAX_URL_LENGTH = 4096
    _MAX_RETRIES = 3
    _RETRY_STATUS_CODES = frozenset({502, 503, 504})
    _DEFAULT_ARTICLE_READ_TIMEOUT = 30.0
    _DEFAULT_ARTICLE_WRITE_TIMEOUT = 10.0
    _DEFAULT_ARTICLE_POOL_TIMEOUT = 5.0

    def __init__(
        self,
        settings: Settings,
    ) -> None:
        self._timeout = httpx.Timeout(
            connect=settings.article_request_timeout,
            read=self._DEFAULT_ARTICLE_READ_TIMEOUT,
            write=self._DEFAULT_ARTICLE_WRITE_TIMEOUT,
            pool=self._DEFAULT_ARTICLE_POOL_TIMEOUT,
        )
        self._max_redirects = settings.article_max_redirects
        self._follow_redirects = settings.article_follow_redirects
        self._verify_ssl = settings.article_verify_ssl

        self._headers = {
            "User-Agent": settings.article_user_agent,
            "Accept": (
                "text/html,"
                "application/xhtml+xml,"
                "application/xml;q=0.9,"
                "*/*;q=0.8"
            ),
            "Accept-Language": "en-US,en;q=0.9",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
        }

    def download(
        self,
        url: str,
    ) -> str:
        """
        Download the raw HTML for an article.

        Args:
            url:
                Absolute HTTP/HTTPS URL.

        Returns:
            Raw HTML.

        Raises:
            ArticleDownloadError
        """
        url = self._validate_url(url)

        logger.info("Downloading article HTML: %s", url)

        start_time = time.perf_counter()

        last_exception: Exception | None = None

        for attempt in range(1, self._MAX_RETRIES + 1):
            try:
                with httpx.Client(
                    headers=self._headers,
                    timeout=self._timeout,
                    follow_redirects=self._follow_redirects,
                    verify=self._verify_ssl,
                    max_redirects=self._max_redirects,
                    http2=True,
                ) as client:
                    response = client.get(url)

                if response.status_code in self._RETRY_STATUS_CODES:
                    response.raise_for_status()

                response.raise_for_status()

                content_type = (
                    response.headers.get("Content-Type", "")
                    .split(";", 1)[0]
                    .strip()
                    .lower()
                )

                if content_type not in self._SUPPORTED_CONTENT_TYPES:
                    raise ArticleDownloadError(
                        f"Unsupported content type: '{content_type or 'unknown'}'."
                    )

                html = response.text.strip()

                if not html:
                    raise ArticleDownloadError(
                        "Downloaded article HTML is empty."
                    )

                elapsed = time.perf_counter() - start_time

                logger.info(
                    (
                        "Downloaded article HTML "
                        "(status=%d, redirects=%d, %.2fs, %d characters)."
                    ),
                    response.status_code,
                    len(response.history),
                    elapsed,
                    len(html),
                )

                return html

            except httpx.HTTPStatusError as exc:
                last_exception = exc

                if (
                    exc.response.status_code in self._RETRY_STATUS_CODES
                    and attempt < self._MAX_RETRIES
                ):
                    time.sleep(2 ** (attempt - 1))
                    continue

                raise ArticleDownloadError(
                    f"HTTP {exc.response.status_code} while downloading article."
                ) from exc

            except httpx.TimeoutException as exc:
                last_exception = exc

                if attempt < self._MAX_RETRIES:
                    time.sleep(2 ** (attempt - 1))
                    continue

                raise ArticleDownloadError(
                    "Timed out while downloading article."
                ) from exc

            except httpx.RequestError as exc:
                last_exception = exc

                if attempt < self._MAX_RETRIES:
                    time.sleep(2 ** (attempt - 1))
                    continue

                raise ArticleDownloadError(
                    f"Network error while downloading article: {exc}"
                ) from exc

        raise ArticleDownloadError(
            "Failed to download article."
        ) from last_exception

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #

    def _validate_url(
        self,
        url: str,
    ) -> str:
        """
        Validate an article URL.

        Returns:
            Normalized URL.

        Raises:
            ArticleDownloadError
        """
        url = url.strip()

        if not url:
            raise ArticleDownloadError(
                "Article URL cannot be empty."
            )

        parsed = urlparse(url)

        if parsed.scheme.lower() not in self._SUPPORTED_SCHEMES:
            raise ArticleDownloadError(
                f"Unsupported URL scheme: '{parsed.scheme}'."
            )

        if not parsed.hostname:
            raise ArticleDownloadError(
                "Invalid article URL."
            )

        if len(url) > self._MAX_URL_LENGTH:
            raise ArticleDownloadError(
                "Article URL exceeds maximum supported length."
            )

        hostname = parsed.hostname.lower()

        if hostname == "localhost":
            raise ArticleDownloadError(
                "Localhost URLs are not allowed."
            )

        try:
            ip = ipaddress.ip_address(hostname)

            if (
                ip.is_private
                or ip.is_loopback
                or ip.is_link_local
                or ip.is_reserved
                or ip.is_multicast
            ):
                raise ArticleDownloadError(
                    "Private or local network addresses are not allowed."
                )
        except ValueError:
            # Hostname is not a literal IP address.
            pass

        return url