"""
deep_notes_ai/services/article/article_extraction_service.py

ArticleExtractionService

Responsible for converting downloaded HTML into clean, structured markdown
using Trafilatura and transforming the extracted document into logical
chapter transcripts.

Responsibilities:
    • Extract the main article body from raw HTML.
    • Remove navigation, ads, headers, footers, comments, and other
      boilerplate content.
    • Produce clean markdown suitable for downstream processing.
    • Parse the markdown into logical document sections.
    • Convert document sections into ChapterTranscript objects with
      estimated timestamps and token counts.

This service intentionally performs NO HTTP requests.

This service intentionally performs NO metadata extraction.

Input:
    Raw HTML

Output:
    • Clean markdown
    • ChapterTranscript objects
"""

from __future__ import annotations

import logging
import re

import trafilatura

from deep_notes_ai.domain.models import ArticleExtractionError, ChapterTranscript, DocumentSection, NoChaptersFoundError
from deep_notes_ai.services.article.markdown_structure_service import MarkdownStructureService
from deep_notes_ai.services.tokenizer_service import TokenizerService

logger = logging.getLogger(__name__)


class ArticleExtractionService:
    """
    Service responsible for extracting article content from raw HTML and
    converting it into chapter transcripts.

    Trafilatura is used to extract the primary article body while removing
    boilerplate content and preserving the document structure as Markdown.

    The extracted markdown is then parsed into logical document sections,
    which are converted into ChapterTranscript objects containing transcript
    text, estimated timestamps, and token counts.

    This service is responsible only for content extraction and document
    segmentation. It does not perform HTTP requests or metadata extraction.
    """

    _TRAFILATURA_OPTIONS = {
        "output_format": "markdown",
        "include_comments": False,
        "include_tables": True,
        "include_links": False,
        "include_images": False,
        "include_formatting": True,
        "favor_precision": True,
        "deduplicate": True,
    }

    _MIN_MARKDOWN_LENGTH = 80

    _AVERAGE_READING_SPEED_TOKENS_PER_SECOND = 2.0

    def __init__(
        self,
        markdown_structure_service: MarkdownStructureService,
        tokenizer_service: "TokenizerService | None" = None,
    ) -> None:
        """
        Initialize the article extraction service.

        Args:
            markdown_structure_service:
                Service responsible for parsing extracted markdown into
                logical document sections.

            tokenizer_service:
                Service used to calculate token counts for each generated
                chapter transcript. Required when transcript token statistics
                are needed.
        """
        self._markdown_structure_service = markdown_structure_service
        self._tokenizer_service = tokenizer_service

    def extract_chapters(
        self,
        html: str,
    ) -> list[ChapterTranscript]:
        """
        Extract chapter transcripts from raw HTML.

        Processing pipeline:

        1. Extract the primary article body as markdown.
        2. Parse the markdown into logical document sections.
        3. Convert each non-empty section into a ChapterTranscript.
        4. Estimate cumulative reading timestamps.
        5. Calculate token counts for every transcript.

        Empty sections are skipped.

        Args:
            html:
                Raw HTML of the article.

        Returns:
            A list of ChapterTranscript objects representing the logical
            sections of the extracted article.

        Raises:
            ArticleExtractionError:
                If article extraction fails.

            NoChaptersFoundError:
                If no non-empty document sections could be converted into
                chapter transcripts.
        """

        markdown: str = self.extract_article(html)
        sections: list[DocumentSection] = self._markdown_structure_service.parse(markdown=markdown)

        logger.info(
            "Building chapter transcripts from %d document section%s.",
            len(sections),
            "" if len(sections) == 1 else "s",
        )

        chapters: list[ChapterTranscript] = []
        chapter_index = 1
        total_tokens = 0

        for section in sections:
            if not section.content.strip():
                logger.debug("Skipping empty document section: %r", section.heading)
                continue

            estimated_reading_seconds = round(total_tokens / self._AVERAGE_READING_SPEED_TOKENS_PER_SECOND)
            hours, remainder = divmod(estimated_reading_seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            formatted_elapsed_time = f"{hours:02}:{minutes:02}:{seconds:02}"

            heading_level = "#" * max(1, min(section.level, 6))
            heading = f"{heading_level} {section.heading.strip()}"

            transcript = (
                f"{heading}\n\n"
                f"{section.content.strip()}"
            )

            tokens = self._tokenizer_service.count_tokens(transcript)

            chapters.append(
                ChapterTranscript(
                    title=heading,
                    display=formatted_elapsed_time,
                    transcript=transcript,
                    tokens=tokens,
                )
            )
            total_tokens += tokens
            chapter_index += 1
        
        skipped = len(sections) - chapter_index + 1
        if skipped:
            logger.info("Skipped %d empty document section%s.", skipped, "" if skipped == 1 else "s")

        if len(chapters) == 0:
            raise NoChaptersFoundError(f"No chapters could be extracted from the article.")

        logger.info(
            "Built %d chapter transcript%s. (total %d tokens)",
            len(chapters),
            "" if len(chapters) == 1 else "s",
            total_tokens,
        )

        return chapters

    def extract_article(
        self,
        html: str,
    ) -> str:
        """
        Extract the primary article content from raw HTML as Markdown.

        Trafilatura is used to remove boilerplate elements such as navigation,
        headers, footers, advertisements, and comments while preserving the
        main article content and document structure.

        The extracted markdown is lightly normalized before being returned.

        Args:
            html:
                Raw HTML downloaded from the source.

        Returns:
            Clean markdown representing the primary article body.

        Raises:
            ArticleExtractionError:
                If the input HTML is empty, extraction fails, or no usable
                article content can be produced.
        """

        if not html.strip():
            raise ArticleExtractionError(
                "Cannot extract article content from empty HTML."
            )

        logger.info(
            "Extracting article content from HTML (%d characters).",
            len(html),
        )

        logger.debug(
            "Trafilatura extraction options: %s",
            self._TRAFILATURA_OPTIONS,
        )

        try:
            markdown = trafilatura.extract(
                html,
                **self._TRAFILATURA_OPTIONS,
            )
        except Exception as exc:
            raise ArticleExtractionError(
                f"Trafilatura extraction failed: {exc}"
            ) from exc

        if markdown is None:
            raise ArticleExtractionError(
                "Trafilatura returned no extractable article content."
            )

        markdown = markdown.strip()
        markdown = markdown.replace("\r\n", "\n")
        markdown = re.sub(r"\n{3,}", "\n\n", markdown)
        markdown = markdown + "\n"

        if not markdown.strip():
            raise ArticleExtractionError(
                "Article body could not be extracted from the supplied HTML."
            )

        if len(markdown) < self._MIN_MARKDOWN_LENGTH:
            logger.warning(
                "Extracted markdown is unusually short (%d characters).",
                len(markdown),
            )

        logger.info(
            "Article extraction completed successfully "
            "(%d markdown characters, %.2f%% of input).",
            len(markdown),
            (len(markdown) / len(html)) * 100,
        )

        return markdown