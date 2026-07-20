"""
deep_notes_ai/services/video_metadata_service.py

VideoMetadataService — validates YouTube URLs, extracts content IDs,
retrieves video metadata using yt_dlp, and parses timestamp chapters from
either native chapter metadata or the video description.
"""
from __future__ import annotations

import logging
import re
from typing import Any
from yt_dlp import YoutubeDL
from urllib.parse import ParseResult, parse_qs, urlparse

from deep_notes_ai.domain.models import InvalidYoutubeUrlError, TimestampChapter, VideoMetadata, VideoMetadataError

logger = logging.getLogger(__name__)


class VideoMetadataService:
    """
    Service responsible for YouTube URL validation, video ID extraction,
    URL normalization, and metadata retrieval.
    """

    # ------------------------------------------------------------------
    # Constants
    # ------------------------------------------------------------------

    _MAX_URL_LENGTH = 2000

    _CANONICAL_URL = "https://www.youtube.com/watch?v={}"

    _VIDEO_ID_REGEX = re.compile(r"^[A-Za-z0-9_-]{11}$")

    _VALID_HOSTS = {
        "youtube.com",
        "www.youtube.com",
        "m.youtube.com",
        "music.youtube.com",
        "youtu.be",
        "www.youtu.be",
    }

    # Path based URL formats.
    _PATH_PATTERNS = (
        re.compile(r"^/embed/([A-Za-z0-9_-]{11})(?:/|$)"),
        re.compile(r"^/shorts/([A-Za-z0-9_-]{11})(?:/|$)"),
        re.compile(r"^/live/([A-Za-z0-9_-]{11})(?:/|$)"),
        re.compile(r"^/v/([A-Za-z0-9_-]{11})(?:/|$)"),
        re.compile(r"^/([A-Za-z0-9_-]{11})(?:/|$)"),  # youtu.be/<id>
    )

    # Matches optional H:, then MM:SS or M:SS at a word boundary.
    # Anchored at start-of-word so it does not match mid-string decimals.
    _TIMESTAMP_PATTERN = re.compile(
        r"(?:^|(?<=\s)|(?<=[\-–—|•]))"   # start of string or whitespace/dash
        r"(?P<h>\d{1,2}:)?"              # optional hours
        r"(?P<m>\d{1,2})"                # minutes
        r":(?P<s>\d{2})"                 # :seconds (always 2 digits)
        r"(?=\s|$|[^\d])"                # must not run into more digits
    )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    
    def fetch_metadata(self, url: str) -> VideoMetadata:
        """
        Fetch metadata for a YouTube video using ``yt_dlp``.

        Does not require the YouTube Data API and is significantly more robust
        than parsing the watch page HTML.

        Raises:
            VideoMetadataError:
                If metadata cannot be retrieved even after retrying with the
                normalized watch URL.
        """
        logger.info("Fetching metadata from %s", url)

        try:
            info = self._extract_info(url)

        except Exception as exc:
            logger.debug(
                "Metadata fetch failed for original URL: %s",
                exc,
            )

            content_id = self.extract_content_id(url)
            normalized_url = self._normalize_url(content_id)

            try:
                info = self._extract_info(normalized_url)

            except Exception as exc:
                logger.warning(
                    "Failed to fetch metadata for content_id=%s: %s",
                    content_id,
                    exc,
                )
                raise VideoMetadataError(
                    f"Failed to fetch metadata for content_id={content_id}"
                ) from exc

        content_id = self._safe_get(info, "id", self.extract_content_id(url))
        content_url = self._safe_get(info, "webpage_url", self._normalize_url(content_id))
        content_title = self._safe_get(info, "title", f"YouTube Video ({content_id})")
        description = self._safe_get(info, "description")
        upload_date_raw = self._safe_get(info, "upload_date")
        upload_date = self._format_upload_date(upload_date_raw)
        author_name = self._safe_get(info, "uploader")

        chapters = self.build_chapters_from_info(info)
        
        if chapters:
            logger.info("Loaded %d chapter(s) from yt_dlp metadata.", len(chapters))
        else:
            logger.info("yt_dlp did not provide chapters. Falling back to description parsing.")
            chapters = self.parse_chapters(description)

        logger.info(
            "Metadata fetched successfully for content_id=%s",
            content_id,
        )

        return VideoMetadata(
            id=content_id,
            url=content_url,
            title=content_title,
            description=description,
            upload_date=upload_date,
            author=author_name,
            chapters=chapters,
        )
    
    # -------------------------------------------------------------------------
    # Public helpers
    # -------------------------------------------------------------------------

    def extract_content_id(self, url: str) -> str:
        """
        Extract and validate the YouTube video ID.

        Supported formats:

        - https://www.youtube.com/watch?v=...
        - https://youtu.be/...
        - https://www.youtube.com/embed/...
        - https://www.youtube.com/shorts/...
        - https://www.youtube.com/live/...
        - https://www.youtube.com/v/...
        - raw 11-character video ID

        Args:
            url:
                YouTube URL or raw video ID.

        Returns:
            Validated 11-character video ID.

        Raises:
            InvalidYoutubeUrlError:
                If the URL is invalid or no valid video ID can be extracted.
        """
        if not isinstance(url, str) or not url.strip():
            raise InvalidYoutubeUrlError("YouTube URL must be a non-empty string.")

        url = url.strip()

        if len(url) > self._MAX_URL_LENGTH:
            raise InvalidYoutubeUrlError("YouTube URL exceeds the maximum allowed length.")

        # Raw video ID
        if self._is_valid_video_id(url):
            return url

        parsed = self._parse_url(url)

        # Validate host
        host = parsed.hostname.lower() if parsed.hostname else ""

        if host not in self._VALID_HOSTS:
            raise InvalidYoutubeUrlError(
                f"Unsupported YouTube host: {parsed.hostname}"
            )

        # watch?v=<id>
        if parsed.path == "/watch":
            query = parse_qs(parsed.query)

            video_id = query.get("v", [None])[0]

            if self._is_valid_video_id(video_id):
                return video_id

        # Path-based formats
        for pattern in self._PATH_PATTERNS:
            match = pattern.match(parsed.path)

            if not match:
                continue

            video_id = match.group(1)

            if self._is_valid_video_id(video_id):
                return video_id

        raise InvalidYoutubeUrlError(
            f"Could not extract a valid YouTube video ID from URL: {url}"
        )
    
    def build_chapters_from_info(
        self,
        info: dict[str, Any],
    ) -> list[TimestampChapter]:
        """
        Build TimestampChapter objects from the ``chapters`` field returned by
        ``yt_dlp``.

        Expected structure::

            [
                {
                    "start_time": 0,
                    "end_time": 84,
                    "title": "Introduction",
                },
                ...
            ]

        Invalid chapter entries are skipped.

        Returns:
            Ordered list of TimestampChapter objects.
        """
        raw_chapters = info.get("chapters") or []

        if not raw_chapters:
            return []

        chapters: list[TimestampChapter] = []

        for chapter in raw_chapters:
            try:
                seconds = int(chapter["start_time"])
                title = str(chapter["title"]).strip()

                chapters.append(
                    TimestampChapter(
                        title=title,
                        timestamp_seconds=seconds,
                        display=self._seconds_to_display(seconds),
                    )
                )

            except (KeyError, TypeError, ValueError):
                logger.debug(
                    "Skipping malformed yt_dlp chapter: %r",
                    chapter,
                )

        return chapters
    
    def parse_chapters(self, description: str) -> list[TimestampChapter]:
        """
        Extract ordered timestamp chapters from a YouTube description.

        Each line that contains a timestamp is treated as one chapter.
        The timestamp may appear anywhere on the line; the remainder of the
        line (with the timestamp removed) is used as the chapter title.

        Lines without a valid timestamp are silently skipped.
        Lines whose timestamp is lower than the previous chapter's timestamp
        are skipped to preserve strictly ascending order.

        Args:
            description: Raw description text (may be empty).

        Returns:
            Ordered list of TimestampChapter objects.  Empty list if none found.
        """
        if not description:
            logger.debug("Empty description — no chapters to parse.")
            return []

        chapters: list[TimestampChapter] = []
        previous_seconds = -1

        for line in description.splitlines():
            line = line.strip()
            if not line:
                continue

            match = self._TIMESTAMP_PATTERN.search(line)
            if not match:
                continue

            try:
                seconds = self._match_to_seconds(match)
            except ValueError:
                logger.debug("Skipping malformed timestamp on line: %r", line)
                continue

            # Enforce strictly ascending order.
            if seconds <= previous_seconds and chapters:
                logger.debug(
                    "Skipping out-of-order timestamp %ds (previous=%ds) on line: %r",
                    seconds,
                    previous_seconds,
                    line,
                )
                continue

            display = self._seconds_to_display(seconds)
            title = (
                line[:match.start()]
                + line[match.end():]
            ).strip(" -–—|•").strip()
            if not title:
                title = display

            chapters.append(
                TimestampChapter(
                    title=title,
                    timestamp_seconds=seconds,
                    display=display,
                )
            )
            previous_seconds = seconds

        logger.debug("Parsed %d timestamp chapter(s) from description.", len(chapters))
        return chapters

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _extract_info(self, url: str) -> dict[str, Any]:
        """
        Retrieve raw metadata from yt_dlp.

        Args:
            url:
                YouTube URL.

        Returns:
            Metadata dictionary returned by yt_dlp.

        Raises:
            Exception:
                Propagates any yt_dlp exception to the caller.
        """
        ydl_opts = {
            "quiet": True,
            "skip_download": True,
            "no_warnings": True,
            "extract_flat": False,
            "ignoreerrors": False,
        }

        with YoutubeDL(ydl_opts) as ydl:
            return ydl.extract_info(url, download=False)


    def _safe_get(
        self,
        info: dict[str, Any],
        key: str,
        default: str = "",
    ) -> str:
        """
        Safely retrieve and normalize a string metadata field.

        Args:
            info:
                yt_dlp metadata dictionary.

            key:
                Metadata field name.

            default:
                Value returned when the field is missing or empty.

        Returns:
            Normalized string value.
        """
        value = info.get(key)

        if value is None:
            logger.info("No %s returned.", key)
            return default

        value = str(value).strip()

        if not value:
            logger.info("Empty %s returned.", key)
            return default

        return value


    def _format_upload_date(self, upload_date_raw: Any) -> str:
        """
        Convert yt_dlp upload_date into ISO-8601 format.

        yt_dlp normally returns YYYYMMDD.

        Args:
            upload_date_raw:
                Raw upload_date value.

        Returns:
            Formatted date string or an empty string.
        """
        if not upload_date_raw:
            return ""

        upload_date = str(upload_date_raw).strip()

        if len(upload_date) == 8:
            return (
                f"{upload_date[:4]}-"
                f"{upload_date[4:6]}-"
                f"{upload_date[6:]}"
            )

        return upload_date

    def _normalize_url(self, content_id: str) -> str:
        """
        Convert a valid YouTube video ID into the canonical watch URL.

        Args:
            content_id:
                Valid YouTube video ID.

        Returns:
            Canonical YouTube watch URL.

        Raises:
            InvalidYoutubeUrlError:
                If the supplied video ID is invalid.
        """
        if not self._is_valid_video_id(content_id):
            raise InvalidYoutubeUrlError(
                f"Invalid YouTube video ID: {content_id}"
            )

        return self._CANONICAL_URL.format(content_id)

    def _parse_url(self, url: str) -> ParseResult:
        """
        Parse a URL while supporting URLs without an explicit scheme.
        """
        try:
            if "://" not in url:
                url = f"https://{url}"

            return urlparse(url)

        except ValueError as exc:
            raise InvalidYoutubeUrlError(
                f"Malformed YouTube URL: {url}"
            ) from exc

    def _is_valid_video_id(self, video_id: str | None) -> bool:
        """
        Return True if the supplied value is a valid YouTube video ID.
        """
        if video_id is None:
            return False

        return bool(self._VIDEO_ID_REGEX.fullmatch(video_id))
    
    def _seconds_to_display(self, seconds: int) -> str:
        """
        Format an integer number of seconds as a timestamp in ``HH:MM:SS`` format.

        Args:
            seconds:
                Non-negative integer number of seconds.

        Returns:
            Timestamp formatted as ``HH:MM:SS``.

        Examples:
            0      -> "00:00:00"
            65     -> "00:01:05"
            3661   -> "01:01:01"
        """
        seconds = max(0, seconds)

        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        seconds = seconds % 60

        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    
    def _match_to_seconds(self, match: re.Match) -> int:
        """Convert a regex match to total seconds."""
        h_str = match.group("h")
        m_str = match.group("m")
        s_str = match.group("s")

        h = int(h_str.rstrip(":")) if h_str else 0
        m = int(m_str)
        s = int(s_str)

        if s >= 60:
            raise ValueError(f"Invalid seconds value: {s}")
        if m >= 60 and h > 0:
            raise ValueError(f"Invalid minutes value: {m}")

        return h * 3600 + m * 60 + s
