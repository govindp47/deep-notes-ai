"""
deep_notes_ai/langgraph_pipeline/nodes/article/extract_article_metadata.py

Node: extract_article_metadata

Responsibility:
    Download an article, extract its metadata, determine the content-specific
    output directory, and return the resulting metadata for downstream nodes.

This node represents the ingestion stage for article-like sources. It is
responsible only for downloading the source HTML, extracting metadata, and
establishing the content directory. Content extraction, document structure
parsing, and chapter generation are handled by downstream nodes.

Reads from state:
    source
    content_base_dir

Returns:
    {
        "metadata": ArticleMetadata,
        "content_base_dir": Path,
    }
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Callable

from deep_notes_ai.domain.models import (
    ArticleDownloadError,
    ArticleMetadataError,
)
from deep_notes_ai.langgraph_pipeline.state import PipelineState
from deep_notes_ai.services.article.article_download_service import (
    ArticleDownloadService,
)
from deep_notes_ai.services.article.article_metadata_service import (
    ArticleMetadataService,
)

if TYPE_CHECKING:
    from deep_notes_ai.services.progress_service import ProgressService

logger = logging.getLogger(__name__)

_NODE = "extract_article_metadata"
_STAGE = "Extracting Article Metadata"


def make_extract_article_metadata_node(
    article_download_service: ArticleDownloadService,
    article_metadata_service: ArticleMetadataService,
    progress_service: "ProgressService | None" = None,
) -> Callable[[PipelineState], dict]:
    """
    Factory that creates the extract_article_metadata LangGraph node.
    """

    def extract_article_metadata(
        state: PipelineState,
    ) -> dict:
        """
        Download the article, extract metadata, and determine the content
        output directory.

        Reads:
            state["source"]
            state["content_base_dir"]

        Returns:
            {
                "metadata": ArticleMetadata,
                "content_base_dir": Path,
            }

        Raises:
            ArticleDownloadError
            ArticleMetadataError
        """
        article_url: str = state["source"]
        logger.info("Extracting article metadata for URL: %s", article_url)

        if progress_service is not None:
            progress_service.emit_start(node_name=_NODE, stage=_STAGE)

        try:
            raw_html = article_download_service.download(article_url)
            metadata = article_metadata_service.build_metadata(url=article_url, html=raw_html)
        except (ArticleDownloadError, ArticleMetadataError):
            if progress_service is not None:
                progress_service.emit_failed(
                    node_name=_NODE,
                    stage=_STAGE,
                    message="Failed to extract article metadata",
                )
            raise

        base_dir = state["content_base_dir"]
        content_base_dir = base_dir / metadata.id

        logger.info("Article metadata extraction complete for content_id=%s", metadata.id)

        if progress_service is not None:
            progress_service.emit_completed(
                node_name=_NODE,
                stage=_STAGE,
            )

        return {
            "metadata": metadata,
            "content_base_dir": content_base_dir,
        }

    return extract_article_metadata