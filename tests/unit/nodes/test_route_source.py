"""
tests/unit/nodes/test_route_source.py
"""
import pytest

from deep_notes_ai.domain.models import SourceType, UnsupportedSourceTypeError, UnsupportedSourceError
from deep_notes_ai.langgraph_pipeline.state import PipelineState
from deep_notes_ai.langgraph_pipeline.nodes.route_source import make_route_source_node, determine_source_route
from pathlib import Path


def test_source_type_enum():
    assert SourceType.YOUTUBE == "youtube"
    assert SourceType.ARTICLE == "article"
    assert SourceType.DOCUMENTATION == "documentation"
    assert SourceType.BOOK == "book"
    assert SourceType.PRESENTATION == "presentation"


def test_route_source_success():
    base_dir = Path("/tmp/base")
    route_source = make_route_source_node(base_dir)
    state: PipelineState = {"source": "some_source", "source_type": SourceType.YOUTUBE}
    result = route_source(state)
    assert result == {"current_run_dir": base_dir / "youtube"}


def test_route_source_coerces_string_to_enum():
    base_dir = Path("/tmp/base")
    route_source = make_route_source_node(base_dir)
    state = {"source": "some_source", "source_type": "youtube"}
    result = route_source(state)  # Should not raise
    assert result == {"current_run_dir": base_dir / "youtube"}


def test_route_source_invalid_source_type():
    base_dir = Path("/tmp/base")
    route_source = make_route_source_node(base_dir)
    state = {"source": "some_source", "source_type": "invalid_type"}
    with pytest.raises(UnsupportedSourceTypeError, match="Invalid source type: invalid_type"):
        route_source(state)


def test_route_source_empty_source():
    base_dir = Path("/tmp/base")
    route_source = make_route_source_node(base_dir)
    state: PipelineState = {"source": "", "source_type": SourceType.YOUTUBE}
    with pytest.raises(UnsupportedSourceError, match="Source cannot be empty."):
        route_source(state)


def test_determine_source_route():
    assert determine_source_route({"source_type": SourceType.YOUTUBE}) == "extract_video_metadata"
    assert determine_source_route({"source_type": SourceType.ARTICLE}) == "ingest_article"
    assert determine_source_route({"source_type": SourceType.DOCUMENTATION}) == "ingest_documentation"
    assert determine_source_route({"source_type": SourceType.BOOK}) == "ingest_book"
    assert determine_source_route({"source_type": SourceType.PRESENTATION}) == "ingest_presentation"


def test_determine_source_route_invalid():
    with pytest.raises(UnsupportedSourceTypeError, match="Unsupported route for source type: invalid"):
        determine_source_route({"source_type": "invalid"})
