# 05 — LangGraph Design

## Overview

The pipeline is implemented as a **single linear LangGraph StateGraph** with 10 processing nodes. Each node corresponds to one pipeline stage. Most edges are unconditional. One conditional edge handles hierarchy validation. An inner retry mechanism handles LLM failures inside content and summary generation nodes.

---

## Graph Boundaries

**One graph, one run per video.**

The graph is compiled once at application startup and invoked once per video. It is not a multi-turn conversation graph. There are no loops in the main graph. Retry logic lives within individual node implementations, not as graph-level loops.

---

## Node Definitions

### Node 1: `extract_transcript`

**File:** `nodes/extract_transcript.py`

**Responsibility:** Fetch the raw YouTube transcript for the given video ID.

**Reads from state:**
- `content_id: str`

**Calls:** `TranscriptService.fetch(content_id)`

**Returns:**
```python
{"raw_content": str}
```

**Error handling:** Raises `TranscriptFetchError` on failure → graph terminates.

---

### Node 2: `clean_transcript`

**File:** `nodes/clean_transcript.py`

**Responsibility:** Send the raw transcript to the cleaning LLM and receive bullet-form cleaned text.

**Reads from state:**
- `raw_content: str`

**Calls:** LangChain chain (cleaning prompt | cleaning LLM).

**Returns:**
```python
{"cleaned_content": str}
```

**Error handling:** `LLMCallError` on LLM failure → graph terminates.

**Note:** The cleaning LLM is called on the entire raw transcript (unlike the exploratory notebook which sliced manually). For very long transcripts, a future enhancement can split into chunks.

---

### Node 3: `number_transcript`

**File:** `nodes/number_transcript.py`

**Responsibility:** Apply `clean_bullet_output()` to the cleaned transcript and persist the numbered file.

**Reads from state:**
- `cleaned_content: str`

**Calls:**
- `algorithms.clean_bullet_output(cleaned_content)`
- `PersistenceService.save_text(content_points_path, numbered_text)`

**Returns:**
```python
{
    "content_points": str,          # full text
    "content_points_path": Path,    # where it was saved
    "content_points_list": list[str],      # parsed numbered points
}
```

**Error handling:** `PersistenceError` on write failure.

---

### Node 4: `generate_hierarchy`

**File:** `nodes/generate_hierarchy.py`

**Responsibility:** Send the numbered transcript to the hierarchy LLM and receive a `TranscriptHierarchy`.

**Reads from state:**
- `content_points: str`

**Calls:** LangChain chain (hierarchy prompt | hierarchy LLM with structured output).

**Returns:**
```python
{"raw_hierarchy": TranscriptHierarchy}
```

**Error handling:** `LLMCallError` or `ValidationError` on failure → graph terminates.

---

### Node 5: `validate_hierarchy`

**File:** `nodes/validate_hierarchy.py`

**Responsibility:** Validate that the hierarchy contains at least one CONTENT leaf node. Guard against silent empty runs.

**Reads from state:**
- `raw_hierarchy: TranscriptHierarchy`

**Calls:** Pure validation logic (counts CONTENT nodes recursively).

**Returns:**
```python
{"hierarchy_valid": bool, "content_node_count": int}
```

**Error handling:** Sets `hierarchy_valid = False` if zero CONTENT nodes found.

---

### Node 6: `extract_content_nodes`

**File:** `nodes/extract_content_nodes.py`

**Responsibility:** Extract all CONTENT leaf nodes, build UUID-keyed metadata, build lightweight Node hierarchy, build ContentPayload list.

**Reads from state:**
- `raw_hierarchy: TranscriptHierarchy`
- `content_points_list: list[str]`

**Calls:** `algorithms.build_content_payloads(raw_hierarchy.hierarchy, content_points_list)`

**Returns:**
```python
{
    "content_payload": list[ContentPayload],
    "nodes_content": dict[str, ContentStoreItem],
    "nodes_hierarchy": list[Node],
}
```

**Error handling:** `AlgorithmError` if extraction fails.

---

### Node 7: `generate_content`

**File:** `nodes/generate_content.py`

**Responsibility:** Generate structured markdown for every CONTENT node via batched, partitioned LLM calls.

**Reads from state:**
- `content_points: str`
- `content_payload: list[ContentPayload]`
- `nodes_content: dict[str, ContentStoreItem]` (will be mutated via returned dict)

**Calls:** `ContentService.generate(...)`

**Returns:**
```python
{"nodes_content": dict[str, ContentStoreItem]}  # updated with .content fields
```

**Error handling:** `ContentGenerationError` wraps any internal failure.

---

### Node 8: `generate_summaries`

**File:** `nodes/generate_summaries.py`

**Responsibility:** Generate revision-note summaries for every CONTENT node via batched, partitioned LLM calls.

**Reads from state:**
- `content_points: str`
- `content_payload: list[ContentPayload]`
- `nodes_content: dict[str, ContentStoreItem]`

**Calls:** `SummaryService.generate(...)`

**Returns:**
```python
{"nodes_content": dict[str, ContentStoreItem]}  # updated with .summary fields
```

**Error handling:** `SummaryGenerationError` wraps any internal failure.

---

### Node 9: `persist_artefacts`

**File:** `nodes/persist_artefacts.py`

**Responsibility:** Write `nodes_hierarchy.json` and `nodes_content.json` to the output directory.

**Reads from state:**
- `nodes_hierarchy: list[Node]`
- `nodes_content: dict[str, ContentStoreItem]`
- `output_dir: Path`

**Calls:**
- `PersistenceService.save_nodes_hierarchy(path, nodes_hierarchy)`
- `PersistenceService.save_nodes_content(path, nodes_content)`

**Returns:**
```python
{
    "hierarchy_json_path": Path,
    "content_json_path": Path,
}
```

---

### Node 10: `render_markdown`

**File:** `nodes/render_markdown.py`

**Responsibility:** Render the two final markdown documents.

**Reads from state:**
- `content_title: str`
- `nodes_hierarchy: list[Node]`
- `nodes_content: dict[str, ContentStoreItem]`
- `output_dir: Path`

**Calls:**
- `MarkdownService.build_document(..., summary=False)` → `content_md`
- `MarkdownService.build_document(..., summary=True)` → `summary_md`
- `PersistenceService.save_markdown(content_path, content_md)`
- `PersistenceService.save_markdown(summary_path, summary_md)`

**Returns:**
```python
{
    "content_md_path": Path,
    "summary_md_path": Path,
    "pipeline_complete": True,
}
```

---

## Edges

### Unconditional Edges

```
START → extract_transcript
extract_transcript → clean_transcript
clean_transcript → number_transcript
number_transcript → generate_hierarchy
generate_hierarchy → validate_hierarchy
validate_hierarchy → [conditional]
extract_content_nodes → generate_content
generate_content → generate_summaries
generate_summaries → persist_artefacts
persist_artefacts → render_markdown
render_markdown → END
```

### Conditional Edge: `validate_hierarchy`

After `validate_hierarchy`, route based on `state["hierarchy_valid"]`:

```python
def route_after_validation(state: PipelineState) -> str:
    if state["hierarchy_valid"]:
        return "extract_content_nodes"
    return "hierarchy_validation_failed"
```

The `hierarchy_validation_failed` node is a terminal error node that logs the failure and sets `pipeline_complete = False`.

```
validate_hierarchy → (conditional) → extract_content_nodes
                                   → hierarchy_validation_failed → END
```

---

## Complete Graph Diagram

```
START
  │
  ▼
extract_transcript          [TranscriptFetchError → END]
  │
  ▼
clean_transcript            [LLMCallError → END]
  │
  ▼
number_transcript           [PersistenceError → END]
  │
  ▼
generate_hierarchy          [LLMCallError → END]
  │
  ▼
validate_hierarchy
  │
  ├─── hierarchy_valid=True ────────────────────────────────────┐
  │                                                             │
  └─── hierarchy_valid=False → hierarchy_validation_failed → END
                                                               │
                                                               ▼
                                                   extract_content_nodes
                                                               │
                                                               ▼
                                                   generate_content
                                                               │
                                                               ▼
                                                   generate_summaries
                                                               │
                                                               ▼
                                                   persist_artefacts
                                                               │
                                                               ▼
                                                   render_markdown
                                                               │
                                                               ▼
                                                             END
```

---

## State Model

See `06_state_design.md` for complete field definitions.

---

## Checkpointing

The compiled graph will use a `MemorySaver` by default for in-process checkpointing.

For production, a `SqliteSaver` (or `PostgresSaver`) will be used so:
- A run can be resumed from the last successful node if the process crashes.
- The checkpoint thread ID is derived from `content_id` so each video has its own checkpoint stream.

```python
from langgraph.checkpoint.sqlite import SqliteSaver

checkpointer = SqliteSaver.from_conn_string("artefacts/checkpoints.db")
compiled_graph = graph.compile(checkpointer=checkpointer)
compiled_graph.invoke(
    initial_state,
    config={"configurable": {"thread_id": content_id}},
)
```

---

## Orchestration Flow

1. Caller constructs `initial_state` from CLI inputs + config.
2. Graph is invoked with `initial_state` and a `thread_id`.
3. Each node runs in sequence.
4. If a node raises an unhandled exception, LangGraph propagates it to the caller.
5. If a node is retried internally (inside `ContentService` or `SummaryService`), the graph node completes successfully after retry.
6. The `validate_hierarchy` conditional edge prevents downstream nodes from running on invalid input.
7. Checkpointer persists state after each node completes.

---

## Retry Behaviour

**Node-level retry** (inside `ContentService` and `SummaryService`):
- Retry on `DuplicateIdsError` and `IncorrectIdsError` (ID validation failures).
- Do not retry on `BatchCountMismatchError` — instead, trigger the fallback partition logic.
- Maximum retries: `settings.max_retries` (default 2).

**Graph-level retry:** Not implemented. If a node fails unrecoverably, the graph terminates and the caller must restart the run (checkpointing ensures resumption from the last successful node).

---

## Termination Conditions

| Condition | Behaviour |
|-----------|-----------|
| `render_markdown` completes | Graph ends successfully. `pipeline_complete = True` |
| `TranscriptFetchError` | Graph raises → caller handles |
| `LLMCallError` (unretried) | Graph raises → caller handles |
| `hierarchy_valid = False` | Routed to `hierarchy_validation_failed` → END cleanly |
| `ContentGenerationError` after max retries | Graph raises → caller handles |
| `SummaryGenerationError` after max retries | Graph raises → caller handles |
| `PersistenceError` | Graph raises → caller handles |
