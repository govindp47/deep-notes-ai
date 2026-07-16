# 06 — State Design

## Design Principle

The `PipelineState` is the **single source of truth** for all data flowing through the LangGraph pipeline. It is a `TypedDict` because LangGraph requires `TypedDict` for state schemas. It is never mutated in place — nodes return partial dictionaries that LangGraph merges into the state.

---

## `PipelineState` (TypedDict)

Defined in `deep_notes_ai/langgraph_pipeline/state.py`.

```python
from __future__ import annotations

from pathlib import Path
from typing import Optional, TypedDict

from deep_notes_ai.domain.models import (
    ContentPayload,
    ContentStoreItem,
    Node,
    TranscriptHierarchy,
)


class PipelineState(TypedDict, total=False):

    # ── Inputs (set before graph invocation, never changed by nodes) ──────────
    content_id: str
    content_title: str
    output_dir: Path

    # ── Stage 1: Transcript Extraction ───────────────────────────────────────
    raw_content: str

    # ── Stage 2: Transcript Cleaning ─────────────────────────────────────────
    cleaned_content: str

    # ── Stage 3: Point Numbering ──────────────────────────────────────────────
    content_points: str
    content_points_path: Path
    content_points_list: list[str]

    # ── Stage 4: Hierarchy Generation ────────────────────────────────────────
    raw_hierarchy: TranscriptHierarchy

    # ── Stage 5: Hierarchy Validation ────────────────────────────────────────
    hierarchy_valid: bool
    content_node_count: int

    # ── Stage 6: Content Node Extraction ─────────────────────────────────────
    content_payload: list[ContentPayload]
    nodes_content: dict[str, ContentStoreItem]
    nodes_hierarchy: list[Node]

    # ── Stage 7: Structured Content Generation ───────────────────────────────
    # nodes_content updated in-place; no new top-level fields added

    # ── Stage 8: Summary Generation ──────────────────────────────────────────
    # nodes_content updated in-place; no new top-level fields added

    # ── Stage 9: Persistence ─────────────────────────────────────────────────
    hierarchy_json_path: Path
    content_json_path: Path

    # ── Stage 10: Markdown Rendering ─────────────────────────────────────────
    content_md_path: Path
    summary_md_path: Path

    # ── Pipeline Control ─────────────────────────────────────────────────────
    pipeline_complete: bool
    error_message: Optional[str]
```

---

## Field Reference

### Input Fields (immutable after graph start)

| Field | Type | Set by | Read by |
|-------|------|--------|---------|
| `content_id` | `str` | Caller | `extract_transcript` |
| `content_title` | `str` | Caller | `render_markdown` |
| `output_dir` | `Path` | Caller | `number_transcript`, `persist_artefacts`, `render_markdown` |

**Why immutable:** These represent the original intent of the run. Nodes must never overwrite them.

---

### Stage 1 Fields

| Field | Type | Set by | Read by |
|-------|------|--------|---------|
| `raw_content` | `str` | `extract_transcript` | `clean_transcript` |

**Lifecycle:** Written once. Never overwritten.

**Rationale:** The raw transcript is needed by no stage after cleaning, but it is preserved for debugging and potential reprocessing.

---

### Stage 2 Fields

| Field | Type | Set by | Read by |
|-------|------|--------|---------|
| `cleaned_content` | `str` | `clean_transcript` | `number_transcript` |

**Lifecycle:** Written once. Never overwritten.

**Rationale:** Preserving the cleaned (but unnumbered) form allows re-running the numbering step without re-calling the cleaning LLM.

---

### Stage 3 Fields

| Field | Type | Set by | Read by |
|-------|------|--------|---------|
| `content_points` | `str` | `number_transcript` | `generate_hierarchy`, `generate_content` (via service) |
| `content_points_path` | `Path` | `number_transcript` | `persist_artefacts` (optional reference) |
| `content_points_list` | `list[str]` | `number_transcript` | `extract_content_nodes` |

**Lifecycle:** Written once.

**`content_points_list`:** A 0-indexed list where `content_points_list[i]` is `"{i+1}. {text}"`. This is the authoritative reference list for all transcript point lookups.

---

### Stage 4 Fields

| Field | Type | Set by | Read by |
|-------|------|--------|---------|
| `raw_hierarchy` | `TranscriptHierarchy` | `generate_hierarchy` | `validate_hierarchy`, `extract_content_nodes` |

**Lifecycle:** Written once. The raw Pydantic model is preserved even after extraction so it can be inspected for debugging.

**Mutability:** Immutable after assignment. `TranscriptHierarchy` and `TopicNode` are Pydantic models; they should not be mutated.

---

### Stage 5 Fields

| Field | Type | Set by | Read by |
|-------|------|--------|---------|
| `hierarchy_valid` | `bool` | `validate_hierarchy` | Conditional edge router |
| `content_node_count` | `int` | `validate_hierarchy` | Logging, observability |

**Lifecycle:** Written once by `validate_hierarchy`.

**Rationale:** Separating validation from extraction allows the graph router to terminate cleanly without passing invalid state to downstream nodes.

---

### Stage 6 Fields

| Field | Type | Set by | Read by |
|-------|------|--------|---------|
| `content_payload` | `list[ContentPayload]` | `extract_content_nodes` | `generate_content`, `generate_summaries` |
| `nodes_content` | `dict[str, ContentStoreItem]` | `extract_content_nodes` | `generate_content`, `generate_summaries`, `persist_artefacts`, `render_markdown` |
| `nodes_hierarchy` | `list[Node]` | `extract_content_nodes` | `persist_artefacts`, `render_markdown` |

**`nodes_content` lifecycle (critical):**
- Created by `extract_content_nodes` with empty `content` and `summary` strings.
- Updated by `generate_content` (populates `.content` for each UUID).
- Updated by `generate_summaries` (populates `.summary` for each UUID).
- Read (final) by `persist_artefacts` and `render_markdown`.

**Mutability note:** Because `TypedDict` fields cannot be partially updated (LangGraph merges at the top-level key), nodes that update `nodes_content` must return the **complete updated dictionary**, not just the changed entries.

---

### Stage 9 Fields

| Field | Type | Set by | Read by |
|-------|------|--------|---------|
| `hierarchy_json_path` | `Path` | `persist_artefacts` | Logging, external consumers |
| `content_json_path` | `Path` | `persist_artefacts` | Logging, external consumers |

---

### Stage 10 Fields

| Field | Type | Set by | Read by |
|-------|------|--------|---------|
| `content_md_path` | `Path` | `render_markdown` | Caller (returned in final state) |
| `summary_md_path` | `Path` | `render_markdown` | Caller (returned in final state) |

---

### Pipeline Control Fields

| Field | Type | Set by | Read by |
|-------|------|--------|---------|
| `pipeline_complete` | `bool` | `render_markdown` or `hierarchy_validation_failed` | Caller |
| `error_message` | `Optional[str]` | `hierarchy_validation_failed` or error nodes | Caller |

---

## Mutable vs Immutable Fields

| Field | Mutable during run? | Notes |
|-------|---------------------|-------|
| `content_id` | No | Input constant |
| `content_title` | No | Input constant |
| `output_dir` | No | Input constant |
| `raw_content` | No | Written once |
| `cleaned_content` | No | Written once |
| `content_points` | No | Written once |
| `content_points_list` | No | Written once |
| `raw_hierarchy` | No | Written once |
| `hierarchy_valid` | No | Written once |
| `content_node_count` | No | Written once |
| `content_payload` | No | Written once |
| `nodes_hierarchy` | No | Written once |
| `nodes_content` | **Yes** | Written by Stage 6, then updated by Stages 7 and 8 |
| `pipeline_complete` | No | Written once at terminal node |

**`nodes_content` is the only field that accumulates updates across multiple nodes.** This is an intentional design choice that mirrors the notebook's global dict mutation. Each node that updates it returns the entire dict.

---

## Initial State Construction

The caller (CLI or test) constructs the initial state before invoking the graph:

```python
initial_state: PipelineState = {
    "content_id": "jGg_1h0qzaM",
    "content_title": "LangGraph Course",
    "output_dir": Path("output/jGg_1h0qzaM"),
    "pipeline_complete": False,
    "error_message": None,
}
```

All other fields start absent (due to `total=False`). LangGraph nodes return partial dicts, which are merged in.

---

## State After Successful Run

```python
final_state: PipelineState = {
    "content_id": "jGg_1h0qzaM",
    "content_title": "LangGraph Course",
    "output_dir": Path("output/jGg_1h0qzaM"),
    "raw_content": "...",
    "cleaned_content": "...",
    "content_points": "1. ...\n2. ...",
    "content_points_path": Path("output/jGg_1h0qzaM/transcript_numbered.md"),
    "content_points_list": ["1. ...", "2. ...", ...],
    "raw_hierarchy": TranscriptHierarchy(...),
    "hierarchy_valid": True,
    "content_node_count": 42,
    "content_payload": [...],
    "nodes_content": {"uuid1": ContentStoreItem(content="...", summary="..."), ...},
    "nodes_hierarchy": [...],
    "hierarchy_json_path": Path("output/jGg_1h0qzaM/nodes_hierarchy.json"),
    "content_json_path": Path("output/jGg_1h0qzaM/nodes_content.json"),
    "content_md_path": Path("output/jGg_1h0qzaM/course_content.md"),
    "summary_md_path": Path("output/jGg_1h0qzaM/course_summary.md"),
    "pipeline_complete": True,
    "error_message": None,
}
```
