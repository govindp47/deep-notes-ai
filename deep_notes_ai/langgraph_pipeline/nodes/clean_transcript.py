"""
deep_notes_ai/langgraph_pipeline/nodes/clean_transcript.py

Node 2: clean_transcript

Responsibility: Send the raw transcript to the cleaning LLM and receive
bullet-form cleaned text.

For transcripts whose token count exceeds the per-chunk budget, the node
splits the content into N chunks, cleans each independently, caches each
part artifact, then joins and persists the final result.

Reads from state: raw_content, content_token_count
Calls: LangChain chain (cleaning prompt | cleaning LLM)
Returns: {"cleaned_content": str}
Error handling: LLMCallError on LLM failure → graph terminates.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from langchain_core.runnables import Runnable

from deep_notes_ai.domain import algorithms
from deep_notes_ai.domain.models import LLMCallError
from deep_notes_ai.langgraph_pipeline.state import PipelineState
from deep_notes_ai.services.persistence_service import PersistenceService
from deep_notes_ai.services.tokenizer_service import TokenizerService

if TYPE_CHECKING:
    from deep_notes_ai.services.progress_service import ProgressService

logger = logging.getLogger(__name__)

_NODE = "clean_transcript"
_STAGE = "Cleaning Transcript"


def _normalise_llm_result(result: object) -> str:
    """Convert an LLM result (AIMessage or plain str) to a plain string."""
    if hasattr(result, "content"):
        return result.content  # type: ignore[attr-defined]
    return str(result)


def _invoke_llm(llm_chain: Runnable, text: str) -> str:
    """
    Invoke the cleaning LLM chain and return the normalised string result.

    Raises:
        LLMCallError: if the underlying LLM call fails.
    """
    try:
        result = llm_chain.invoke(text)
    except Exception as exc:
        raise LLMCallError(f"Cleaning LLM call failed: {exc}") from exc
    return _normalise_llm_result(result)


def make_clean_transcript_node(
    llm_chain: Runnable,
    persistence_service: PersistenceService,
    tokenizer_service: TokenizerService,
    chunk_tokens: int,
    overlap_chars: int,
    progress_service: "ProgressService | None" = None,
):
    """
    Factory that returns a clean_transcript node bound to the given LLM chain.

    Args:
        llm_chain:           A LangChain Runnable (cleaning prompt | cleaning LLM).
        persistence_service: PersistenceService for caching.
        tokenizer_service:   TokenizerService for token counting.
        chunk_tokens:        Maximum number of tokens per cleaning chunk.
        overlap_chars:       Character overlap between adjacent chunks.
        progress_service:    Optional ProgressService for user-facing progress.

    Returns:
        A callable compatible with LangGraph node interface.
    """

    def clean_transcript(state: PipelineState) -> dict:
        """
        Send the raw transcript to the cleaning LLM, chunk-by-chunk if needed.

        Reads:
            state["raw_content"]: str
            state["current_run_dir"]: Path

        Returns:
            {"cleaned_content": str}

        Raises:
            LLMCallError: if any LLM call fails.
        """
        raw_content: str = state["raw_content"]
        current_run_dir: Path = state["current_run_dir"]

        artifacts_path = current_run_dir / "cleaned_content.txt"

        if persistence_service.exists(artifacts_path):
            cleaned = persistence_service.load_text(artifacts_path)
            logger.info("Found existing cleaned content. Restoring state from disk.")
            if progress_service is not None:
                progress_service.emit_info(
                    node_name=_NODE,
                    stage=_STAGE,
                    message="Cleaned transcript restored from cache",
                )
            return {"cleaned_content": cleaned}

        if progress_service is not None:
            progress_service.emit_start(node_name=_NODE, stage=_STAGE)

        token_count = tokenizer_service.count_tokens(raw_content)
        chunk_count = algorithms.count_chunks(token_count, chunk_tokens)

        logger.info(
            "Cleaning started — total_tokens=%d, chunk_count=%d, input_chars=%d",
            token_count,
            chunk_count,
            len(raw_content),
        )

        if chunk_count == 1:
            try:
                cleaned = _invoke_llm(llm_chain, raw_content)
            except Exception:
                if progress_service is not None:
                    progress_service.emit_failed(
                        node_name=_NODE,
                        stage=_STAGE,
                        message="LLM cleaning call failed",
                    )
                raise
            logger.info("Content cleaned, output_chars=%d", len(cleaned))
            persistence_service.save_text(artifacts_path, cleaned)
            if progress_service is not None:
                progress_service.emit_completed(node_name=_NODE, stage=_STAGE)
            return {"cleaned_content": cleaned}

        chunks = algorithms.split_text_into_chunks(raw_content, chunk_count, overlap_chars)
        cleaned_parts: list[str | None] = [None] * chunk_count

        # Chunks that actually require LLM processing.
        pending_inputs: list[str] = []
        pending_indices: list[int] = []

        for i, _chunk in enumerate(chunks):
            chunk_num = i + 1
            part_path = current_run_dir / f"cleaned_content_part_{chunk_num:03d}_{chunk_count:03d}.txt"

            if persistence_service.exists(part_path):
                cleaned_parts[i] = persistence_service.load_text(part_path)
                logger.info("Chunk %d/%d restored from cache.", chunk_num, chunk_count)
                if progress_service is not None:
                    progress_service.emit_progress(
                        node_name=_NODE,
                        stage=_STAGE,
                        message=f"Chunk {chunk_num} / {chunk_count} (cached)",
                        current=chunk_num,
                        total=chunk_count,
                    )
                continue

            pending_inputs.append(_chunk)
            pending_indices.append(i)

        # ── Batch LLM call for missing chunks ─────────────────────────────────────────
        if pending_inputs:
            logger.info("Processing %d transcript chunks in batch.", len(pending_inputs))

            try:
                results = llm_chain.batch(pending_inputs)
            except Exception as exc:
                if progress_service is not None:
                    progress_service.emit_failed(
                        node_name=_NODE,
                        stage=_STAGE,
                        message=f"Batch LLM cleaning failed: {exc}",
                    )
                raise LLMCallError(f"Cleaning batch LLM call failed: {exc}") from exc

            if len(results) != len(pending_inputs):
                raise LLMCallError("Cleaning batch returned an unexpected number of results.")

            for idx, result in zip(pending_indices, results, strict=True):
                chunk_num = idx + 1
                cleaned_part = _normalise_llm_result(result)
                cleaned_parts[idx] = cleaned_part
                part_path = current_run_dir / f"cleaned_content_part_{chunk_num:03d}_{chunk_count:03d}.txt"

                persistence_service.save_text(part_path, cleaned_part)

                logger.info("Chunk %d/%d persisted.", chunk_num, chunk_count)
                if progress_service is not None:
                    progress_service.emit_progress(
                        node_name=_NODE,
                        stage=_STAGE,
                        message=f"Chunk {chunk_num} / {chunk_count}",
                        current=chunk_num,
                        total=chunk_count,
                    )

        # ── Join and persist final artifact ───────────────────────────────────
        assert all(part is not None for part in cleaned_parts)
        logger.info("Joining cleaned transcript from %d chunks.", chunk_count)
        cleaned = "\n".join(cleaned_parts)

        persistence_service.save_text(artifacts_path, cleaned)

        # ── Remove temporary chunk artifacts ──────────────────────────────────
        for i in range(chunk_count):
            chunk_num = i + 1
            part_path = current_run_dir / f"cleaned_content_part_{chunk_num:03d}_{chunk_count:03d}.txt"
            if persistence_service.exists(part_path):
                try:
                    part_path.unlink()
                except OSError as exc:
                    logger.warning(
                        "Failed to remove temporary chunk artifact %s: %s", part_path, exc
                    )

        logger.info("Temporary artifacts removed. Cleaning complete.")

        if progress_service is not None:
            progress_service.emit_completed(node_name=_NODE, stage=_STAGE)

        return {"cleaned_content": cleaned}

    return clean_transcript
