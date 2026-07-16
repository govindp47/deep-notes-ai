# 09 — Error Handling

## Design Philosophy

- **Translate at the boundary.** External exceptions (LLM API, file system, YouTube API) are caught at the service boundary and wrapped in domain-specific exceptions. Internal code only handles domain exceptions.
- **Classify, then decide.** Every exception is classified as either recoverable (retry), repartitionable (increase partition count), or unrecoverable (propagate to caller).
- **Don't swallow errors silently.** The notebook's bare `except` in Cell 0 is a bug. All errors must be logged and classified.
- **Fail fast on unrecoverable errors.** Nodes that encounter unrecoverable errors let the exception propagate. LangGraph terminates the graph. The caller handles it.

---

## Exception Hierarchy

```
Exception
├── TranscriptFetchError         — YouTube API failure
├── LLMCallError                 — LLM API call failure (network, auth, rate limit)
├── PromptNotFoundError          — Prompt file missing
├── PersistenceError             — File I/O failure (read or write)
├── AlgorithmError               — Domain algorithm failure (e.g. bad numbering)
├── HierarchyValidationError     — Hierarchy has zero CONTENT nodes
├── BatchValidationError         — LLM batch response validation failure
│   ├── BatchCountMismatchError  — Wrong number of items
│   ├── DuplicateIdsError        — Duplicate IDs in response
│   └── IncorrectIdsError        — IDs don't match expected set
├── RetryExhaustedError          — All retry attempts consumed
├── ContentGenerationError       — Content batch generation failed permanently
└── SummaryGenerationError       — Summary batch generation failed permanently
```

---

## Error Classification Table

| Error | Recoverable? | Strategy |
|-------|-------------|---------|
| `TranscriptFetchError` | No | Log + terminate graph |
| `LLMCallError` (network/timeout) | Yes | Retry via `RetryService` |
| `LLMCallError` (auth/quota) | No | Log + terminate graph |
| `PromptNotFoundError` | No | Log + terminate (programmer error) |
| `PersistenceError` (write) | Sometimes | Log + terminate (disk full → no) |
| `PersistenceError` (read) | No | Log + terminate |
| `AlgorithmError` | No | Log + terminate |
| `HierarchyValidationError` | No | Route to error node, set `hierarchy_valid=False` |
| `BatchCountMismatchError` | Yes | Repartition (not retry) |
| `DuplicateIdsError` | Yes | Retry same partition via `RetryService` |
| `IncorrectIdsError` | Yes | Retry same partition via `RetryService` |
| `RetryExhaustedError` | No | Propagate as `ContentGenerationError` or `SummaryGenerationError` |

---

## Retry Strategy

### Where retries are applied

Retries apply only inside `ContentService` and `SummaryService`. The retry unit is one partition batch call.

### Retryable conditions

| Condition | Why retryable |
|-----------|--------------|
| `DuplicateIdsError` | LLM non-determinism — a fresh call usually succeeds |
| `IncorrectIdsError` | LLM non-determinism — a fresh call usually succeeds |
| `LLMCallError` (transient) | Transient network/API issue |

### Non-retryable conditions

| Condition | Why not retryable |
|-----------|------------------|
| `BatchCountMismatchError` | Suggests context length issue → repartition, not retry |
| `LLMCallError` (auth/quota) | Environment problem, retrying won't help |
| `PersistenceError` | Disk problem, retrying won't help |

### Retry parameters

From `settings.py`:
- `max_retries: int = 2` — maximum attempts per partition call
- Attempts are sequential (not parallel)
- No exponential backoff in V1 (can be added later)

### Repartition Strategy

When `BatchCountMismatchError` is raised:
1. Abort the current partition run entirely.
2. Restart with `fallback_partitions` (default 6, vs initial 4).
3. If the fallback also fails → `ContentGenerationError` / `SummaryGenerationError`.

```
generate_structured_content():
    try:
        _process_partitions(INITIAL_PARTITIONS)
    except BatchCountMismatchError:
        _process_partitions(FALLBACK_PARTITIONS)
    except RetryExhaustedError:
        raise ContentGenerationError(...)
```

---

## LLM Failure Handling

### Transient LLM failures

Examples: network timeout, rate limit 429, temporary 500.

**Strategy:** Catch inside `RetryService.invoke()`. Classify using `is_retryable`. Retry up to `max_retries`.

```python
def is_llm_retryable(e: Exception) -> bool:
    if isinstance(e, LLMCallError):
        return e.is_transient  # True for 429, 503, network errors
    return False
```

### Auth/quota LLM failures

Examples: invalid API key (401), quota exceeded permanently.

**Strategy:** Raise `LLMCallError(is_transient=False)`. `RetryService` re-raises immediately. Node propagates to graph. Graph terminates.

### Structured output parsing failures

LangChain's `.with_structured_output()` can raise `OutputParserException` if the LLM returns malformed JSON.

**Strategy:** Catch `OutputParserException`, wrap in `LLMCallError(is_transient=True)`, retry.

---

## Validation Failures

### `BatchCountMismatchError`

The LLM returned a different number of items than expected. This is usually a context-length symptom: the LLM truncated its response.

**Detection:** `len(response.items) != len(expected_ids)`

**Response:** Do not retry. Repartition into more, smaller batches.

### `DuplicateIdsError`

The LLM returned duplicate N-identifiers in the same batch.

**Detection:** Any `id` appears more than once in `response.items`.

**Response:** Retry the same batch. Usually caused by LLM non-determinism and resolves on retry.

### `IncorrectIdsError`

The LLM returned IDs that don't exactly match the expected set (wrong IDs, modified IDs like `N01` instead of `N1`).

**Detection:** `set(returned_ids) != expected_ids`.

**Response:** Retry the same batch.

---

## Recoverable Failures (Detailed)

| Failure | Node | Recovery |
|---------|------|----------|
| Transient LLM call error | `clean_transcript`, `generate_hierarchy`, `generate_content`, `generate_summaries` | `RetryService` retries the call |
| `DuplicateIdsError` on content batch | `generate_content` | `RetryService` retries the partition call |
| `IncorrectIdsError` on content batch | `generate_content` | `RetryService` retries the partition call |
| `DuplicateIdsError` on summary batch | `generate_summaries` | `RetryService` retries the partition call |
| `IncorrectIdsError` on summary batch | `generate_summaries` | `RetryService` retries the partition call |
| `BatchCountMismatchError` | `generate_content` / `generate_summaries` | Repartition to `fallback_partitions` |

---

## Unrecoverable Failures (Detailed)

| Failure | Node | Behaviour |
|---------|------|-----------|
| `TranscriptFetchError` | `extract_transcript` | Propagate → graph raises |
| `LLMCallError(is_transient=False)` | Any LLM node | Propagate → graph raises |
| `PromptNotFoundError` | Any LLM node (on startup) | Propagate → application fails to start |
| `PersistenceError` (write) | `number_transcript`, `persist_artefacts`, `render_markdown` | Propagate → graph raises |
| `PersistenceError` (read) | `generate_content`, `generate_summaries` | Propagate → graph raises |
| `RetryExhaustedError` (content) | `generate_content` | Wrap in `ContentGenerationError`, propagate |
| `RetryExhaustedError` (summary) | `generate_summaries` | Wrap in `SummaryGenerationError`, propagate |
| `AlgorithmError` | `number_transcript`, `extract_content_nodes` | Propagate → graph raises |

---

## Validation Failures

### Hierarchy validation

**Where:** `validate_hierarchy` node.

**Failure condition:** `count_content_nodes(raw_hierarchy) == 0`.

**Strategy:** Do not raise. Set `state["hierarchy_valid"] = False`. The conditional edge routes to `hierarchy_validation_failed` node which:
1. Logs the failure with the video ID.
2. Sets `state["error_message"]` with a descriptive message.
3. Sets `state["pipeline_complete"] = False`.
4. Returns to END.

**Rationale:** This is a semantic validation failure, not a system failure. The graph should terminate cleanly with a meaningful error state rather than raising an exception.

### Numbered transcript validation

**Where:** `algorithms.load_numbered_points_from_text()`.

**Failure condition:** Point numbers are not `1..N` in sequence.

**Strategy:** Raise `AlgorithmError`. Propagates to `number_transcript` node, then to graph. This indicates the cleaning LLM produced non-standard output.

---

## Persistence Failures

### Write failure

**Strategy:** Wrap `OSError` / `IOError` in `PersistenceError`. Propagate to node. Graph raises. Caller must investigate disk/permissions.

### Read failure (missing file)

**Strategy:** Wrap `FileNotFoundError` in `PersistenceError`. Propagate. This indicates a pipeline state corruption (e.g. resuming a run whose artefacts were deleted).

---

## Error Reporting to Caller

All unhandled exceptions propagate through LangGraph to the `graph.invoke()` call site. The caller is responsible for:
1. Catching the exception.
2. Logging with the video ID and step name.
3. Reporting to the user.
4. Optionally re-invoking with the same `thread_id` (checkpointer allows resumption).
