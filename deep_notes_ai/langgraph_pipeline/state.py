"""
deep_notes_ai/langgraph_pipeline/state.py

PipelineState — the single source of truth for all data flowing through
the LangGraph pipeline.

Design:
  - TypedDict because LangGraph requires TypedDict for state schemas.
  - total=False so all fields are optional (nodes return partial dicts).
  - Never mutated in place — nodes return partial dicts that LangGraph merges.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional, TypedDict

from deep_notes_ai.domain.models import (
    ChapterTranscript,
    ContentMetadata,
    ContentPayload,
    ContentStoreItem,
    Node,
    ProcessingContext,
    SourceType,
    TranscriptHierarchy,
)


class PipelineState(TypedDict, total=False):

    # ── Inputs (set before graph invocation, never changed by nodes) ──────────
    source: str
    source_type: SourceType

    # Resolved output execution directory
    content_base_dir: Path
    current_run_dir: Path

    # ── Stage 0: Metadata & Content Extraction ───────────────────────────────────
    metadata: ContentMetadata
    chapters: list[ChapterTranscript]

    # ── Stage 1: Processing Context ─────────────────────────────────────────────────
    processing_context: ProcessingContext

    # ── Stage 2: Raw Content ─────────────────────────────────────────────────
    raw_content: str

    # ── Stage 3: Content Cleaning ─────────────────────────────────────────
    cleaned_content: str

    # ── Stage 4: Point Numbering ──────────────────────────────────────────────
    content_points: list[str]

    # ── Stage 5: Hierarchy Generation ────────────────────────────────────────
    raw_hierarchy: TranscriptHierarchy
    content_node_count: int

    # ── Stage 6: Content Node Extraction ─────────────────────────────────────
    content_payload: list[ContentPayload]
    nodes_content: dict[str, ContentStoreItem]
    nodes_hierarchy: list[Node]

    # ── Stage 7: Structured Content Generation ───────────────────────────────
    # nodes_content updated in-place; no new top-level fields added

    # ── Stage 8: Summary Generation ──────────────────────────────────────────
    # nodes_content updated in-place; no new top-level fields added

    # ── Stage 9: Markdown Rendering ─────────────────────────────────────────
    # content and summary markdown files rendered in content_base_dir path

    # ── Pipeline Control ─────────────────────────────────────────────────────────
    pipeline_complete: bool
    error_message: Optional[str]
