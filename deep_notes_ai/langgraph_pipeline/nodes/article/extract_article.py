"""
deep_notes_ai/langgraph_pipeline/nodes/article/extract_article.py

Node: extract_article

Responsibility:
    Extract structured chapter content directly from an article's raw HTML
    and convert it into the common ChapterTranscript representation used
    throughout the pipeline.

    After this node completes, the remainder of the pipeline operates on
    ChapterTranscript objects and is agnostic to the original content source.

Reads from state:
    metadata

Returns:
    {
        "chapters": list[ChapterTranscript]
    }

Raises:
    ArticleExtractionError
    ArticleStructureError
    NoChaptersFoundError
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Callable, cast

from deep_notes_ai.domain.models import (
    ArticleExtractionError,
    ArticleMetadata,
    ArticleStructureError,
    ChapterTranscript,
    NoChaptersFoundError,
)
from deep_notes_ai.langgraph_pipeline.state import PipelineState
from deep_notes_ai.services.article.article_extraction_service import ArticleExtractionService

if TYPE_CHECKING:
    from deep_notes_ai.services.progress_service import ProgressService

logger = logging.getLogger(__name__)

_NODE = "extract_article"
_STAGE = "Extracting Article"


def make_extract_article_node(
    article_extraction_service: ArticleExtractionService,
    progress_service: "ProgressService | None" = None,
) -> Callable[[PipelineState], dict]:
    """
    Factory that creates the extract_article LangGraph node.

    Args:
        article_extraction_service:
            Extracts structured ChapterTranscript objects directly from
            the article HTML.

        progress_service:
            Optional ProgressService used for user-facing progress updates.

    Returns:
        A LangGraph-compatible node callable.
    """

    def extract_article(
        state: PipelineState,
    ) -> dict:
        """
        Extract ChapterTranscript objects from the article HTML.

        Reads:
            state["metadata"]

        Returns:
            {
                "chapters": list[ChapterTranscript]
            }

        Raises:
            ArticleExtractionError:
                If article content extraction fails.

            ArticleStructureError:
                If the extracted article structure cannot be interpreted.

            NoChaptersFoundError:
                If no valid chapters are found in the extracted article.
        """
        metadata = cast(ArticleMetadata, state["metadata"])

        if progress_service is not None:
            progress_service.emit_start(node_name=_NODE, stage=_STAGE)

        logger.info("Extracting article for content_id=%s", metadata.id)

        try:
            chapters: ChapterTranscript = article_extraction_service.extract_chapters(html=metadata.raw_html)
        except ArticleExtractionError:
            if progress_service is not None:
                progress_service.emit_failed(
                    node_name=_NODE,
                    stage=_STAGE,
                    message="Failed to extract article content.",
                )
            raise
        except ArticleStructureError:
            if progress_service is not None:
                progress_service.emit_failed(
                    node_name=_NODE,
                    stage=_STAGE,
                    message="Failed to extract markdown sections.",
                )
            raise
        except NoChaptersFoundError:
            if progress_service is not None:
                progress_service.emit_failed(
                    node_name=_NODE,
                    stage=_STAGE,
                    message="No chapters found in the article.",
                )
            raise

        logger.info(
            "Article extracted successfully for content_id=%s (%d chapter%s).",
            metadata.id,
            len(chapters),
            "" if len(chapters) == 1 else "s",
        )

        if progress_service is not None:
            progress_service.emit_completed(
                node_name=_NODE,
                stage=_STAGE,
            )

        return {
            "chapters": chapters,
        }

    return extract_article