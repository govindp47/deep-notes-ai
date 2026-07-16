"""
tests/unit/nodes/test_ingest_placeholders.py
"""
import pytest

from deep_notes_ai.langgraph_pipeline.state import PipelineState
from deep_notes_ai.langgraph_pipeline.nodes.ingest_placeholders import (
    ingest_article,
    ingest_documentation,
    ingest_book,
    ingest_presentation,
)


def test_ingest_article():
    state: PipelineState = {"source": "some_article"}
    with pytest.raises(NotImplementedError, match="Article ingestion is not yet supported."):
        ingest_article(state)


def test_ingest_documentation():
    state: PipelineState = {"source": "some_doc"}
    with pytest.raises(NotImplementedError, match="Documentation ingestion is not yet supported."):
        ingest_documentation(state)


def test_ingest_book():
    state: PipelineState = {"source": "some_book"}
    with pytest.raises(NotImplementedError, match="Book ingestion is not yet supported."):
        ingest_book(state)


def test_ingest_presentation():
    state: PipelineState = {"source": "some_presentation"}
    with pytest.raises(NotImplementedError, match="Presentation ingestion is not yet supported."):
        ingest_presentation(state)
