"""
tests/integration/test_langgraph_graph.py

Integration smoke tests for the LangGraph graph assembly.

Tests graph compilation and structure WITHOUT making any real LLM calls.

Tests:
  test_graph_compiles_without_errors
  test_graph_has_correct_number_of_nodes
  test_graph_start_and_end_nodes_connected
  test_conditional_edge_exists_from_generate_hierarchy
  test_graph_node_names_match_constants
  test_new_multipart_nodes_present
"""
from __future__ import annotations

import pytest

from deep_notes_ai.config.settings import Settings
from deep_notes_ai.langgraph_pipeline.graph import (
    NODE_EXTRACT_CONTENT_NODES,
    NODE_HIERARCHY_VALIDATION_FAILED,
    NODE_GENERATE_HIERARCHY,
    NODE_ROUTE_SOURCE,
    NODE_INGEST_ARTICLE,
    NODE_INGEST_DOCUMENTATION,
    NODE_INGEST_BOOK,
    NODE_INGEST_PRESENTATION,
    NODE_CALCULATE_TRANSCRIPT_TOKENS,
    NODE_DETERMINE_PROCESSING_MODE,
    NODE_EXTRACT_VIDEO_TIMESTAMPS,
    NODE_SELECT_TRANSCRIPT_BREAKPOINTS,
    NODE_SPLIT_TRANSCRIPT,
    NODE_PROCESS_TRANSCRIPT_PARTS,
    NODE_NO_CHAPTERS_AVAILABLE,
    build_graph,
)


@pytest.fixture
def test_settings() -> Settings:
    """Minimal settings for testing (no real API keys required for compilation)."""
    return Settings(OPENAI_API_KEY="test-key")


@pytest.fixture
def compiled_graph_tuple(test_settings: Settings):
    """Compiled graph under test (returns tuple of (graph, monitor_service))."""
    return build_graph(test_settings)


@pytest.fixture
def compiled_graph(compiled_graph_tuple):
    """Unwrapped compiled graph."""
    graph, _ = compiled_graph_tuple
    return graph


class TestGraphCompilation:
    """Verify the graph compiles and has the correct structure."""

    def test_graph_compiles_without_errors(self, test_settings: Settings) -> None:
        """build_graph() must complete without raising."""
        graph, monitor = build_graph(test_settings)
        assert graph is not None

    def test_graph_has_correct_number_of_nodes(
        self, compiled_graph
    ) -> None:
        """
        Graph must contain exactly the expected set of named processing nodes
        (excluding __start__ and __end__).
        """
        nodes = compiled_graph.get_graph().nodes
        processing_nodes = {n for n in nodes if not n.startswith("__")}
        expected_node_names = {
            "route_source",
            "ingest_article",
            "ingest_documentation",
            "ingest_book",
            "ingest_presentation",
            "extract_video_metadata",
            "extract_transcript",
            # multi-part pipeline additions
            "calculate_transcript_tokens",
            "determine_processing_mode",
            "extract_video_timestamps",
            "select_transcript_breakpoints",
            "split_transcript",
            "process_transcript_parts",
            "no_chapters_available",
            # shared processing path
            "clean_transcript",
            "number_transcript",
            "generate_hierarchy",
            "extract_content_nodes",
            "generate_content",
            "generate_summaries",
            "render_markdown",
            "hierarchy_validation_failed",
        }
        assert processing_nodes == expected_node_names, (
            f"Unexpected nodes.\n"
            f"  Got:      {sorted(processing_nodes)}\n"
            f"  Expected: {sorted(expected_node_names)}"
        )

    def test_graph_start_and_end_nodes_connected(
        self, compiled_graph
    ) -> None:
        """
        __start__ must connect to route_source.
        render_markdown, hierarchy_validation_failed, no_chapters_available,
        and the ingestion stubs must connect to __end__.
        """
        raw_graph = compiled_graph.get_graph()
        edges = raw_graph.edges

        start_targets = [e.target for e in edges if e.source == "__start__"]
        assert "route_source" in start_targets, (
            "__start__ must connect to route_source"
        )

        end_sources = {e.source for e in edges if e.target == "__end__"}
        assert "render_markdown" in end_sources, (
            "render_markdown must connect to __end__"
        )
        assert "hierarchy_validation_failed" in end_sources, (
            "hierarchy_validation_failed must connect to __end__"
        )
        assert "no_chapters_available" in end_sources, (
            "no_chapters_available must connect to __end__"
        )

    def test_conditional_edge_exists_from_generate_hierarchy(
        self, compiled_graph
    ) -> None:
        """
        generate_hierarchy must have conditional edges to both
        extract_content_nodes and hierarchy_validation_failed.
        """
        raw_graph = compiled_graph.get_graph()
        edges = raw_graph.edges

        from_hierarchy = [e for e in edges if e.source == NODE_GENERATE_HIERARCHY]
        target_nodes = {e.target for e in from_hierarchy}

        assert NODE_EXTRACT_CONTENT_NODES in target_nodes, (
            f"generate_hierarchy must connect to {NODE_EXTRACT_CONTENT_NODES}"
        )
        assert NODE_HIERARCHY_VALIDATION_FAILED in target_nodes, (
            f"generate_hierarchy must connect to {NODE_HIERARCHY_VALIDATION_FAILED}"
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
            NODE_CALCULATE_TRANSCRIPT_TOKENS,
            NODE_DETERMINE_PROCESSING_MODE,
            NODE_EXTRACT_VIDEO_TIMESTAMPS,
            NODE_SELECT_TRANSCRIPT_BREAKPOINTS,
            NODE_SPLIT_TRANSCRIPT,
            NODE_PROCESS_TRANSCRIPT_PARTS,
            NODE_NO_CHAPTERS_AVAILABLE,
            NODE_CLEAN_TRANSCRIPT,
            NODE_NUMBER_TRANSCRIPT,
            NODE_GENERATE_HIERARCHY,
            NODE_EXTRACT_CONTENT_NODES,
            NODE_GENERATE_CONTENT,
            NODE_GENERATE_SUMMARIES,
            NODE_RENDER_MARKDOWN,
            NODE_HIERARCHY_VALIDATION_FAILED,
        ]:
            assert const_name in graph_nodes, (
                f"Node constant {const_name!r} not found in compiled graph"
            )

    def test_new_multipart_nodes_present(self, compiled_graph) -> None:
        """All multi-part processing nodes must be registered in the graph."""
        graph_nodes = compiled_graph.get_graph().nodes
        multipart_nodes = [
            NODE_CALCULATE_TRANSCRIPT_TOKENS,
            NODE_DETERMINE_PROCESSING_MODE,
            NODE_EXTRACT_VIDEO_TIMESTAMPS,
            NODE_SELECT_TRANSCRIPT_BREAKPOINTS,
            NODE_SPLIT_TRANSCRIPT,
            NODE_PROCESS_TRANSCRIPT_PARTS,
            NODE_NO_CHAPTERS_AVAILABLE,
        ]
        for node in multipart_nodes:
            assert node in graph_nodes, (
                f"Multi-part node {node!r} not found in compiled graph"
            )
