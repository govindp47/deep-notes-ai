"""
tests/integration/test_pipeline_flow.py

Integration tests for the full LangGraph pipeline.

All LLM calls and external API calls are mocked. The graph is invoked with a
realistic initial state. File I/O uses tmp_path (real filesystem).

Key design: mock models are wrapped in RunnableLambda so LangChain's pipe
operator creates a valid RunnableSequence that returns the correct type — not
a MagicMock that would break LangGraph's msgpack serializer.

Tests:
  test_full_pipeline_success_path
  test_full_pipeline_produces_output_files
  test_invalid_hierarchy_routes_to_error_node
  test_pipeline_state_has_all_expected_fields_after_success
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from langchain_core.runnables import RunnableLambda

from deep_notes_ai.config.settings import Settings
from deep_notes_ai.domain.models import (
    ContentSummary,
    ContentSummaryBatch,
    StructuredContent,
    StructuredContentBatch,
    TopicNode,
    TranscriptHierarchy,
    SourceType,
)
from deep_notes_ai.langgraph_pipeline.state import PipelineState


# ---------------------------------------------------------------------------
# Minimal AIMessage-like object (avoids importing langchain_core in mocks)
# ---------------------------------------------------------------------------

class _FakeAIMessage:
    """Minimal AIMessage substitute that satisfies the node's hasattr check."""

    def __init__(self, content: str) -> None:
        self.content = content


# ---------------------------------------------------------------------------
# Test data
# ---------------------------------------------------------------------------

SAMPLE_HIERARCHY = TranscriptHierarchy(
    hierarchy=[
        TopicNode(
            name="LangGraph Fundamentals",
            start_point=1,
            end_point=5,
            children=[
                TopicNode(name="CONTENT", start_point=1, end_point=3, children=[]),
                TopicNode(name="CONTENT", start_point=4, end_point=5, children=[]),
            ],
        ),
        TopicNode(
            name="Graph Execution",
            start_point=6,
            end_point=10,
            children=[
                TopicNode(name="CONTENT", start_point=6, end_point=10, children=[]),
            ],
        ),
    ]
)
# 3 CONTENT nodes → N1, N2, N3

EMPTY_HIERARCHY = TranscriptHierarchy(hierarchy=[])

SAMPLE_CLEANED = "\n".join(f"- Point {i}" for i in range(1, 11))

SAMPLE_CONTENT_BATCH = StructuredContentBatch(
    items=[
        StructuredContent(id="N1", markdown="## Fundamentals Part 1\n\n- Point 1"),
        StructuredContent(id="N2", markdown="## Fundamentals Part 2\n\n- Point 4"),
        StructuredContent(id="N3", markdown="## Graph Execution\n\n- Point 6"),
    ]
)

SAMPLE_SUMMARY_BATCH = ContentSummaryBatch(
    items=[
        ContentSummary(id="N1", summary="Summary: Part 1"),
        ContentSummary(id="N2", summary="Summary: Part 2"),
        ContentSummary(id="N3", summary="Summary: Execution"),
    ]
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def test_settings(tmp_path: Path) -> Settings:
    """Settings with all output paths pointing to tmp_path."""
    return Settings(
        OPENAI_API_KEY="test-key",
        OUTPUT_BASE_DIR=str(tmp_path / "output"),
        USE_SQLITE_CHECKPOINTER=False,
        CONTENT_INITIAL_PARTITIONS=1,
        CONTENT_FALLBACK_PARTITIONS=2,
        SUMMARY_INITIAL_PARTITIONS=1,
        SUMMARY_FALLBACK_PARTITIONS=2,
    )


# ---------------------------------------------------------------------------
# Helper — build and invoke with all external dependencies mocked
# ---------------------------------------------------------------------------

def _count_content_nodes(hierarchy: TranscriptHierarchy) -> int:
    """Count CONTENT leaf nodes recursively."""
    def _count(nodes: list) -> int:
        total = 0
        for node in nodes:
            if node.name == "CONTENT":
                total += 1
            else:
                total += _count(node.children)
        return total
    return _count(hierarchy.hierarchy)


def _make_content_batch(n: int) -> StructuredContentBatch:
    return StructuredContentBatch(
        items=[
            StructuredContent(id=f"N{i}", markdown=f"## Node {i}\n\n- content {i}")
            for i in range(1, n + 1)
        ]
    )


def _make_summary_batch(n: int) -> ContentSummaryBatch:
    return ContentSummaryBatch(
        items=[
            ContentSummary(id=f"N{i}", summary=f"Summary {i}")
            for i in range(1, n + 1)
        ]
    )


def _build_and_invoke(
    settings: Settings,
    hierarchy: TranscriptHierarchy = SAMPLE_HIERARCHY,
    raw_content: str = "raw transcript text",
    content_id: str = "test-video-id",
    title: str = "Test Course",
) -> dict:
    """
    Build the graph with all LLM and transcript calls mocked, then invoke it.

    Mock strategy:
    - YouTubeTranscriptApi is replaced via sys.modules so the lazy import inside
      TranscriptService.fetch() gets the stub.
    - LLMService.get_chat_model returns a RunnableLambda (cleaning model).
    - LLMService.get_structured_model returns a RunnableLambda for each call:
        1st  → hierarchy model (returns TranscriptHierarchy)
        2nd  → content model  (returns StructuredContentBatch)
        3rd  → summary model  (returns ContentSummaryBatch)
    Using RunnableLambda ensures the pipe operator (|) creates a proper
    RunnableSequence whose outputs are serialisable Pydantic/dataclass objects.
    """
    content_count = _count_content_nodes(hierarchy)
    content_batch = _make_content_batch(content_count)
    summary_batch = _make_summary_batch(content_count)

    # RunnableLambda wrappers — these ARE valid Runnables, no MagicMock leakage
    cleaning_runnable = RunnableLambda(lambda _: _FakeAIMessage(SAMPLE_CLEANED))
    hierarchy_runnable = RunnableLambda(lambda _: hierarchy)
    content_runnable = RunnableLambda(lambda _: content_batch)
    summary_runnable = RunnableLambda(lambda _: summary_batch)

    # Each call to get_structured_model returns the next runnable in sequence
    structured_calls = [hierarchy_runnable, content_runnable, summary_runnable]
    structured_idx = [0]

    def get_structured_side_effect(provider, model, output_schema, temperature=0.0):
        idx = min(structured_idx[0], len(structured_calls) - 1)
        structured_idx[0] += 1
        return structured_calls[idx]

    # Build a stub youtube_transcript_api module so the lazy import succeeds
    import types
    stub_yt_module = types.ModuleType("youtube_transcript_api")
    stub_snippet = type("Snippet", (), {"text": raw_content, "start": 0.0, "duration": 1.0})()
    stub_yt_api_class = type("YouTubeTranscriptApi", (), {
        "get_transcript": staticmethod(
            lambda vid: [stub_snippet]
        ),
        "fetch": lambda self, vid: [stub_snippet]
    })
    stub_yt_module.YouTubeTranscriptApi = stub_yt_api_class

    import sys
    original_yt = sys.modules.get("youtube_transcript_api")
    sys.modules["youtube_transcript_api"] = stub_yt_module

    try:
        with (
            patch(
                "deep_notes_ai.services.video_metadata_service.VideoMetadataService.extract_content_id",
                return_value=content_id,
            ),
            patch(
                "deep_notes_ai.services.video_metadata_service.VideoMetadataService.normalize_url",
                return_value=f"https://www.youtube.com/watch?v={content_id}",
            ),
            patch(
                "deep_notes_ai.services.video_metadata_service.VideoMetadataService.fetch_video_metadata",
                return_value={"content_title": title, "upload_date": "2023", "author_name": "Test"},
            ),
            patch(
                "deep_notes_ai.services.llm_service.LLMService.get_chat_model",
                return_value=cleaning_runnable,
            ),
            patch(
                "deep_notes_ai.services.llm_service.LLMService.get_structured_model",
                side_effect=get_structured_side_effect,
            ),
        ):
            from deep_notes_ai.langgraph_pipeline.graph import build_graph
            graph = build_graph(settings)

            # Graph is now compiled with the mocked chains baked in.
            # Invoke it — the mocked chains/services are captured in node closures.
            
            youtube_url = f"https://www.youtube.com/watch?v={content_id}"
            
            initial_state: PipelineState = {
                "source": youtube_url,
                "source_type": SourceType.YOUTUBE,
                "pipeline_complete": False,
                "error_message": None,
            }

            final_state = graph.invoke(
                initial_state,
                config={"configurable": {"thread_id": youtube_url}},
            )
    finally:
        # Restore original module (or remove stub)
        if original_yt is None:
            sys.modules.pop("youtube_transcript_api", None)
        else:
            sys.modules["youtube_transcript_api"] = original_yt

    return final_state


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestFullPipelineSuccessPath:
    """End-to-end pipeline with all external calls mocked."""

    def test_full_pipeline_success_path(
        self, test_settings: Settings, tmp_path: Path
    ) -> None:
        """
        Given: mocked transcript + all LLM responses
        When: graph is invoked
        Then: pipeline_complete=True
        """
        final_state = _build_and_invoke(test_settings)
        assert final_state.get("pipeline_complete") is True

    def test_full_pipeline_produces_output_files(
        self, test_settings: Settings, tmp_path: Path
    ) -> None:
        """Both markdown files and JSON artefacts must be created."""
        _build_and_invoke(test_settings, content_id="vid-files")

        run_dir = test_settings.output_base_dir / "youtube" / "vid-files"
        assert (run_dir / "course_content.md").exists(), "content markdown missing"
        assert (run_dir / "course_summary.md").exists(), "summary markdown missing"
        assert (run_dir / "nodes_hierarchy.json").exists(), "hierarchy JSON missing"
        assert (run_dir / "nodes_content.json").exists(), "content JSON missing"
        assert (run_dir / "transcript_numbered.txt").exists(), "numbered transcript missing"


class TestInvalidHierarchy:
    """Test routing to error node when hierarchy has no CONTENT nodes."""

    def test_invalid_hierarchy_routes_to_error_node(
        self, test_settings: Settings, tmp_path: Path
    ) -> None:
        """
        Given: hierarchy LLM returns hierarchy with zero CONTENT nodes
        When: graph is invoked
        Then: pipeline_complete=False, error_message is set,
              no content/summary files created
        """
        final_state = _build_and_invoke(
            test_settings,
            hierarchy=EMPTY_HIERARCHY,
            content_id="vid-invalid",
        )

        assert final_state.get("hierarchy_valid") is False
        assert final_state.get("pipeline_complete") is False
        assert final_state.get("error_message") is not None
        assert "CONTENT" in final_state["error_message"] or "content" in final_state["error_message"].lower()

        # No downstream output files should exist
        run_dir = test_settings.output_base_dir / "youtube" / "vid-invalid"
        assert not (run_dir / "course_content.md").exists()
        assert not (run_dir / "course_summary.md").exists()


class TestPipelineStateCompleteness:
    """All state fields must be populated after a successful run."""

    def test_pipeline_state_has_all_expected_fields_after_success(
        self, test_settings: Settings, tmp_path: Path
    ) -> None:
        """Every PipelineState field must be present and non-None."""
        final_state = _build_and_invoke(test_settings, content_id="vid-complete")

        expected_fields = [
            "content_id",
            "content_title",
            "current_run_dir",
            "raw_content",
            "cleaned_content",
            "content_points",
            "content_points_path",
            "content_points_list",
            "raw_hierarchy",
            "hierarchy_valid",
            "content_node_count",
            "content_payload",
            "nodes_content",
            "nodes_hierarchy",
            "hierarchy_json_path",
            "content_json_path",
            "content_md_path",
            "summary_md_path",
            "pipeline_complete",
        ]
        for field in expected_fields:
            assert field in final_state, f"Field {field!r} missing from final state"
            assert final_state[field] is not None, f"Field {field!r} is None"

        assert final_state["pipeline_complete"] is True
        assert final_state["hierarchy_valid"] is True
        assert final_state["content_node_count"] == 3
