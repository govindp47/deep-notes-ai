"""
deep_notes_ai/langgraph_pipeline/nodes/ingest_placeholders.py

Placeholder nodes for future ingestion sources.
These nodes raise NotImplementedError when called.
"""
from __future__ import annotations

import logging

from deep_notes_ai.langgraph_pipeline.state import PipelineState

logger = logging.getLogger(__name__)


def ingest_article(state: PipelineState) -> dict:
    """
    Placeholder ingestion node for articles.
    
    Reads:
        state["source"]: str
        
    Returns:
        dict (currently raises NotImplementedError)
        
    Raises:
        NotImplementedError: Always, until implemented.
    """
    source = state.get("source")
    logger.error("Article ingestion not yet implemented for source: %s", source)
    raise NotImplementedError("Article ingestion is not yet supported.")


def ingest_documentation(state: PipelineState) -> dict:
    """
    Placeholder ingestion node for documentation.
    
    Reads:
        state["source"]: str
        
    Returns:
        dict (currently raises NotImplementedError)
        
    Raises:
        NotImplementedError: Always, until implemented.
    """
    source = state.get("source")
    logger.error("Documentation ingestion not yet implemented for source: %s", source)
    raise NotImplementedError("Documentation ingestion is not yet supported.")


def ingest_book(state: PipelineState) -> dict:
    """
    Placeholder ingestion node for books.
    
    Reads:
        state["source"]: str
        
    Returns:
        dict (currently raises NotImplementedError)
        
    Raises:
        NotImplementedError: Always, until implemented.
    """
    source = state.get("source")
    logger.error("Book ingestion not yet implemented for source: %s", source)
    raise NotImplementedError("Book ingestion is not yet supported.")


def ingest_presentation(state: PipelineState) -> dict:
    """
    Placeholder ingestion node for presentations.
    
    Reads:
        state["source"]: str
        
    Returns:
        dict (currently raises NotImplementedError)
        
    Raises:
        NotImplementedError: Always, until implemented.
    """
    source = state.get("source")
    logger.error("Presentation ingestion not yet implemented for source: %s", source)
    raise NotImplementedError("Presentation ingestion is not yet supported.")
