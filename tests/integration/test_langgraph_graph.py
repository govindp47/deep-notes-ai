"""
tests/integration/test_langgraph_graph.py

Integration smoke tests for the LangGraph graph assembly.

Tests graph compilation and structure WITHOUT making any real LLM calls.

Tests:
  test_graph_compiles_without_errors
  test_graph_has_correct_number_of_nodes
  test_graph_start_and_end_nodes_connected
  test_conditional_edge_exists_from_validate_hierarchy
"""
from __future__ import annotations

import pytest

from deep_notes_ai.config.settings import Settings
from deep_notes_ai.langgraph_pipeline.graph import (
    NODE_EXTRACT_CONTENT_NODES,
    NODE_HIERARCHY_VALIDATION_FAILED,
    NODE_VALIDATE_HIERARCHY,
    NODE_ROUTE_SOURCE,
    NODE_INGEST_ARTICLE,
    NODE_INGEST_DOCUMENTATION,
    NODE_INGEST_BOOK,
    NODE_INGEST_PRESENTATION,
    build_graph,
)


@pytest.fixture
def test_settings() -> Settings:
    """Minimal settings for testing (no real API keys required for compilation)."""
    return Settings(OPENAI_API_KEY="test-key")


@pytest.fixture
def compiled_graph(test_settings: Settings):
    """Compiled graph under test."""
    return build_graph(test_settings)


class TestGraphCompilation:
    """Verify the graph compiles and has the correct structure."""

    def test_graph_compiles_without_errors(self, test_settings: Settings) -> None:
        """build_graph() must complete without raising."""
        graph = build_graph(test_settings)
        assert graph is not None

    def test_graph_has_correct_number_of_nodes(
        self, compiled_graph
    ) -> None:
        """
        Graph must contain exactly the 10 processing nodes + 1 error node
        (not counting __start__ and __end__).
        """
        nodes = compiled_graph.get_graph().nodes
        # Exclude __start__ and __end__
        # Expect all 11 processing nodes + 1 terminal error node
        processing_nodes = [n for n in nodes if not n.startswith("__")]
        expected_node_names = {
            "route_source",
            "ingest_article",
            "ingest_documentation",
            "ingest_book",
            "ingest_presentation",
            "extract_video_metadata",
            "extract_transcript",
            "clean_transcript",
            "number_transcript",
            "generate_hierarchy",
            "validate_hierarchy",
            "extract_content_nodes",
            "generate_content",
            "generate_summaries",
            "persist_artefacts",
            "render_markdown",
            "hierarchy_validation_failed",
        }
        assert set(processing_nodes) == expected_node_names, (
            f"Unexpected nodes. Got: {set(processing_nodes)}"
        )

    def test_graph_start_and_end_nodes_connected(
        self, compiled_graph
    ) -> None:
        """
        __start__ must connect to extract_transcript.
        render_markdown and hierarchy_validation_failed must connect to __end__.
        """
        raw_graph = compiled_graph.get_graph()
        edges = raw_graph.edges

        # Find edge from __start__ → route_source
        start_targets = [
            e.target for e in edges if e.source == "__start__"
        ]
        assert "route_source" in start_targets, (
            "__start__ must connect to route_source"
        )

        # Find edges to __end__
        end_sources = [e.source for e in edges if e.target == "__end__"]
        assert "render_markdown" in end_sources, (
            "render_markdown must connect to __end__"
        )
        assert "hierarchy_validation_failed" in end_sources, (
            "hierarchy_validation_failed must connect to __end__"
        )

    def test_conditional_edge_exists_from_validate_hierarchy(
        self, compiled_graph
    ) -> None:
        """
        validate_hierarchy must have conditional edges to both
        extract_content_nodes and hierarchy_validation_failed.
        """
        raw_graph = compiled_graph.get_graph()
        edges = raw_graph.edges

        # Find all edges from validate_hierarchy
        from_validate = [e for e in edges if e.source == NODE_VALIDATE_HIERARCHY]
        target_nodes = {e.target for e in from_validate}

        assert NODE_EXTRACT_CONTENT_NODES in target_nodes, (
            f"validate_hierarchy must connect to {NODE_EXTRACT_CONTENT_NODES}"
        )
        assert NODE_HIERARCHY_VALIDATION_FAILED in target_nodes, (
            f"validate_hierarchy must connect to {NODE_HIERARCHY_VALIDATION_FAILED}"
        )

    def test_graph_node_names_match_constants(
        self, compiled_graph
    ) -> None:
        """Node name constants in graph.py must match actual registered nodes."""
        from deep_notes_ai.langgraph_pipeline.graph import (
            NODE_EXTRACT_VIDEO_METADATA,
            NODE_CLEAN_TRANSCRIPT,
            NODE_EXTRACT_TRANSCRIPT,
            NODE_GENERATE_CONTENT,
            NODE_GENERATE_HIERARCHY,
            NODE_GENERATE_SUMMARIES,
            NODE_NUMBER_TRANSCRIPT,
            NODE_PERSIST_ARTEFACTS,
            NODE_RENDER_MARKDOWN,
        )

        graph_nodes = compiled_graph.get_graph().nodes
        for const_name in [
            NODE_ROUTE_SOURCE,
            NODE_INGEST_ARTICLE,
            NODE_INGEST_DOCUMENTATION,
            NODE_INGEST_BOOK,
            NODE_INGEST_PRESENTATION,
            NODE_EXTRACT_VIDEO_METADATA,
            NODE_EXTRACT_TRANSCRIPT,
            NODE_CLEAN_TRANSCRIPT,
            NODE_NUMBER_TRANSCRIPT,
            NODE_GENERATE_HIERARCHY,
            NODE_VALIDATE_HIERARCHY,
            NODE_EXTRACT_CONTENT_NODES,
            NODE_GENERATE_CONTENT,
            NODE_GENERATE_SUMMARIES,
            NODE_PERSIST_ARTEFACTS,
            NODE_RENDER_MARKDOWN,
            NODE_HIERARCHY_VALIDATION_FAILED,
        ]:
            assert const_name in graph_nodes, (
                f"Node constant {const_name!r} not found in compiled graph"
            )
