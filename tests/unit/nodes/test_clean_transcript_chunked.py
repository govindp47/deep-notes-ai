"""
tests/unit/nodes/test_clean_transcript_chunked.py

Unit tests for the chunked clean_transcript node.

Coverage:
  - Single-chunk transcript (chunk_count=1) → no part files created
  - Multi-chunk: LLM called once per chunk
  - Cache restoration: existing part files skip LLM calls
  - Interrupted execution resumes from last saved chunk
  - Final cleaned_content.txt is written
  - Part files are removed after successful merge
  - Canonical cache hit: no LLM calls and no part files
  - State update: cleaned_content equals the joined result
  - No duplicate LLM calls for cached chunks

All LLM calls are mocked. Persistence uses real tmp_path.
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest
from langchain_core.runnables import Runnable

from deep_notes_ai.langgraph_pipeline.nodes.clean_transcript import make_clean_transcript_node
from deep_notes_ai.services.persistence_service import PersistenceService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_state(tmp_path: Path, token_count: int = 4000) -> dict:
    """Build a minimal PipelineState dict for testing."""
    return {
        "raw_content": "line one\nline two\nline three\nline four\nline five\nline six",
        "transcript_token_count": token_count,
        "current_run_dir": tmp_path,
    }


def _make_mock_chain(return_text: str = "- cleaned bullet") -> MagicMock:
    chain = MagicMock(spec=Runnable)
    chain.invoke.return_value = return_text
    return chain


def _artifacts_dir(tmp_path: Path) -> Path:
    return tmp_path / "artifacts"


def _canonical_path(tmp_path: Path) -> Path:
    return _artifacts_dir(tmp_path) / "cleaned_content.txt"


def _part_path(tmp_path: Path, n: int) -> Path:
    return _artifacts_dir(tmp_path) / f"cleaned_content_part_{n:03d}.txt"


# The PersistenceService takes no constructor args in the current implementation.
@pytest.fixture
def persistence_service() -> PersistenceService:
    return PersistenceService()


# ---------------------------------------------------------------------------
# Canonical cache hit (fast path) — no LLM call, no part files
# ---------------------------------------------------------------------------

def test_canonical_cache_hit_returns_cached_content(
    persistence_service: PersistenceService,
    tmp_path: Path,
) -> None:
    canonical = _canonical_path(tmp_path)
    persistence_service.save_text(canonical, "already cleaned")

    chain = _make_mock_chain()
    node = make_clean_transcript_node(chain, persistence_service, chunk_tokens=6000)
    result = node(_make_state(tmp_path))

    assert result["cleaned_content"] == "already cleaned"
    chain.invoke.assert_not_called()


def test_canonical_cache_hit_no_part_files_created(
    persistence_service: PersistenceService,
    tmp_path: Path,
) -> None:
    canonical = _canonical_path(tmp_path)
    persistence_service.save_text(canonical, "already cleaned")

    chain = _make_mock_chain()
    node = make_clean_transcript_node(chain, persistence_service, chunk_tokens=6000)
    node(_make_state(tmp_path))

    assert not _part_path(tmp_path, 1).exists()


# ---------------------------------------------------------------------------
# Single-chunk path (token_count <= chunk_tokens)
# ---------------------------------------------------------------------------

def test_single_chunk_invokes_llm_once(
    persistence_service: PersistenceService,
    tmp_path: Path,
) -> None:
    """When token_count fits within one chunk, LLM is called exactly once."""
    chain = _make_mock_chain("- cleaned result")
    node = make_clean_transcript_node(chain, persistence_service, chunk_tokens=6000)
    result = node(_make_state(tmp_path, token_count=3000))

    chain.invoke.assert_called_once()
    assert result["cleaned_content"] == "- cleaned result"


def test_single_chunk_writes_canonical_artifact(
    persistence_service: PersistenceService,
    tmp_path: Path,
) -> None:
    chain = _make_mock_chain("- cleaned result")
    node = make_clean_transcript_node(chain, persistence_service, chunk_tokens=6000)
    node(_make_state(tmp_path, token_count=3000))

    assert _canonical_path(tmp_path).exists()
    assert _canonical_path(tmp_path).read_text(encoding="utf-8") == "- cleaned result"


def test_single_chunk_creates_no_part_files(
    persistence_service: PersistenceService,
    tmp_path: Path,
) -> None:
    chain = _make_mock_chain("- cleaned result")
    node = make_clean_transcript_node(chain, persistence_service, chunk_tokens=6000)
    node(_make_state(tmp_path, token_count=3000))

    assert not _part_path(tmp_path, 1).exists()


# ---------------------------------------------------------------------------
# Multi-chunk path
# ---------------------------------------------------------------------------

def _multi_chunk_state(tmp_path: Path) -> dict:
    """State where token_count forces 3 chunks with chunk_tokens=6000."""
    return {
        "raw_content": "\n".join(f"line {i}" for i in range(1, 61)),
        "transcript_token_count": 18001,  # ceil(18001 / 6000) = 4
        "current_run_dir": tmp_path,
    }


def test_multi_chunk_llm_called_per_chunk(
    persistence_service: PersistenceService,
    tmp_path: Path,
) -> None:
    state = _multi_chunk_state(tmp_path)
    chunk_count = 4  # ceil(18001 / 6000)

    chain = _make_mock_chain("- part cleaned")
    node = make_clean_transcript_node(chain, persistence_service, chunk_tokens=6000)
    node(state)

    assert chain.invoke.call_count == chunk_count


def test_multi_chunk_final_artifact_is_joined(
    persistence_service: PersistenceService,
    tmp_path: Path,
) -> None:
    call_num = [0]

    def side_effect(text: str) -> str:
        call_num[0] += 1
        return f"- chunk {call_num[0]}"

    chain = MagicMock(spec=Runnable)
    chain.invoke.side_effect = side_effect

    node = make_clean_transcript_node(chain, persistence_service, chunk_tokens=6000)
    result = node(_multi_chunk_state(tmp_path))

    # Final result must contain output from every chunk
    assert "- chunk 1" in result["cleaned_content"]
    assert "- chunk 4" in result["cleaned_content"]


def test_multi_chunk_part_files_deleted_after_merge(
    persistence_service: PersistenceService,
    tmp_path: Path,
) -> None:
    state = _multi_chunk_state(tmp_path)
    chunk_count = 4

    chain = _make_mock_chain("- cleaned")
    node = make_clean_transcript_node(chain, persistence_service, chunk_tokens=6000)
    node(state)

    for i in range(1, chunk_count + 1):
        assert not _part_path(tmp_path, i).exists(), (
            f"Part file {i} should have been deleted after merge"
        )


def test_multi_chunk_canonical_artifact_written(
    persistence_service: PersistenceService,
    tmp_path: Path,
) -> None:
    chain = _make_mock_chain("- cleaned")
    node = make_clean_transcript_node(chain, persistence_service, chunk_tokens=6000)
    node(_multi_chunk_state(tmp_path))

    assert _canonical_path(tmp_path).exists()


def test_multi_chunk_state_cleaned_content_matches_artifact(
    persistence_service: PersistenceService,
    tmp_path: Path,
) -> None:
    chain = _make_mock_chain("- cleaned")
    node = make_clean_transcript_node(chain, persistence_service, chunk_tokens=6000)
    result = node(_multi_chunk_state(tmp_path))

    on_disk = _canonical_path(tmp_path).read_text(encoding="utf-8")
    assert result["cleaned_content"] == on_disk


# ---------------------------------------------------------------------------
# Cache restoration per chunk
# ---------------------------------------------------------------------------

def test_cached_chunk_is_not_regenerated(
    persistence_service: PersistenceService,
    tmp_path: Path,
) -> None:
    """If a part file already exists, the LLM is NOT called for that chunk."""
    state = _multi_chunk_state(tmp_path)
    chunk_count = 4

    # Pre-populate part 1 and part 2
    persistence_service.save_text(_part_path(tmp_path, 1), "- cached chunk 1")
    persistence_service.save_text(_part_path(tmp_path, 2), "- cached chunk 2")

    chain = _make_mock_chain("- new chunk")
    node = make_clean_transcript_node(chain, persistence_service, chunk_tokens=6000)
    node(state)

    # LLM should only be called for chunks 3 and 4
    assert chain.invoke.call_count == chunk_count - 2


def test_cached_chunk_content_included_in_final(
    persistence_service: PersistenceService,
    tmp_path: Path,
) -> None:
    state = _multi_chunk_state(tmp_path)

    persistence_service.save_text(_part_path(tmp_path, 1), "- cached chunk 1")

    call_num = [1]

    def side_effect(text: str) -> str:
        call_num[0] += 1
        return f"- new chunk {call_num[0]}"

    chain = MagicMock(spec=Runnable)
    chain.invoke.side_effect = side_effect

    node = make_clean_transcript_node(chain, persistence_service, chunk_tokens=6000)
    result = node(state)

    assert "- cached chunk 1" in result["cleaned_content"]


# ---------------------------------------------------------------------------
# Interrupted execution (resume behaviour)
# ---------------------------------------------------------------------------

def test_interrupted_execution_resumes_from_saved_chunks(
    persistence_service: PersistenceService,
    tmp_path: Path,
) -> None:
    """
    Simulate a run that completed chunks 1 and 2 before being interrupted.
    On the second run, only chunks 3 and 4 should invoke the LLM.
    """
    state = _multi_chunk_state(tmp_path)
    chunk_count = 4

    # Simulate first (partial) run: chunks 1 & 2 were persisted
    persistence_service.save_text(_part_path(tmp_path, 1), "- resumed chunk 1")
    persistence_service.save_text(_part_path(tmp_path, 2), "- resumed chunk 2")

    chain = _make_mock_chain("- newly generated")
    node = make_clean_transcript_node(chain, persistence_service, chunk_tokens=6000)
    result = node(state)

    # Only chunks 3 and 4 should have been generated
    assert chain.invoke.call_count == chunk_count - 2

    # All chunk contents must be present in the output
    assert "- resumed chunk 1" in result["cleaned_content"]
    assert "- resumed chunk 2" in result["cleaned_content"]
    assert "- newly generated" in result["cleaned_content"]


def test_second_run_skips_all_work_if_canonical_exists(
    persistence_service: PersistenceService,
    tmp_path: Path,
) -> None:
    """If canonical artifact exists from a previous complete run, nothing is done."""
    canonical = _canonical_path(tmp_path)
    persistence_service.save_text(canonical, "previous complete result")

    chain = _make_mock_chain()
    node = make_clean_transcript_node(chain, persistence_service, chunk_tokens=6000)
    result = node(_multi_chunk_state(tmp_path))

    chain.invoke.assert_not_called()
    assert result["cleaned_content"] == "previous complete result"


# ---------------------------------------------------------------------------
# LLM result normalisation
# ---------------------------------------------------------------------------

def test_ai_message_result_normalised_to_str(
    persistence_service: PersistenceService,
    tmp_path: Path,
) -> None:
    """Results that have a .content attribute are unwrapped (AIMessage pattern)."""
    ai_message = MagicMock()
    ai_message.content = "- normalised content"

    chain = MagicMock(spec=Runnable)
    chain.invoke.return_value = ai_message

    node = make_clean_transcript_node(chain, persistence_service, chunk_tokens=6000)
    result = node(_make_state(tmp_path, token_count=3000))

    assert result["cleaned_content"] == "- normalised content"


# ---------------------------------------------------------------------------
# Cleanup failure is non-fatal
# ---------------------------------------------------------------------------

def test_part_file_cleanup_failure_does_not_raise(
    persistence_service: PersistenceService,
    tmp_path: Path,
) -> None:
    """If deleting a part file fails, the pipeline must not raise."""
    chain = _make_mock_chain("- cleaned")
    node = make_clean_transcript_node(chain, persistence_service, chunk_tokens=6000)

    with patch.object(Path, "unlink", side_effect=OSError("permission denied")):
        # Should complete without raising
        result = node(_multi_chunk_state(tmp_path))

    assert "cleaned_content" in result
