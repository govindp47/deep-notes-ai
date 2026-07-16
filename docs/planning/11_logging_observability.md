# 11 — Logging and Observability

## Design Principles

- **Structured logging** — all log records are emitted as JSON for machine-readable parsing and ingestion into log aggregation systems.
- **Contextual correlation** — every log record carries `content_id` and `node_name` so runs can be filtered and correlated.
- **Non-invasive** — logging is injected at the service and node level. Domain algorithms contain no logging calls.
- **Levelled** — `DEBUG` for trace-level detail, `INFO` for stage progress, `WARNING` for retries and fallbacks, `ERROR` for failures.

---

## Logging Stack

| Concern | Library |
|---------|---------|
| Core logging | Python `logging` stdlib |
| Structured JSON output | `python-json-logger` (`pythonjsonlogger`) |
| Log level control | `settings.log_level` from environment |

---

## Logger Hierarchy

```
deep_notes_ai                          (root package logger)
├── deep_notes_ai.services
│   ├── deep_notes_ai.services.transcript_service
│   ├── deep_notes_ai.services.llm_service
│   ├── deep_notes_ai.services.content_service
│   ├── deep_notes_ai.services.summary_service
│   ├── deep_notes_ai.services.retry_service
│   ├── deep_notes_ai.services.validation_service
│   └── deep_notes_ai.services.persistence_service
└── deep_notes_ai.langgraph_pipeline
    └── deep_notes_ai.langgraph_pipeline.nodes.*
```

Each module acquires its logger with:
```python
import logging
logger = logging.getLogger(__name__)
```

---

## Structured Log Format

When `ENABLE_STRUCTURED_LOGGING=true`, each log record is emitted as a JSON line:

```json
{
  "timestamp": "2026-07-02T12:00:00.000Z",
  "level": "INFO",
  "logger": "deep_notes_ai.langgraph_pipeline.nodes.generate_content",
  "message": "Content generation complete",
  "content_id": "jGg_1h0qzaM",
  "node": "generate_content",
  "partition": 3,
  "total_partitions": 4,
  "content_nodes_processed": 14,
  "duration_ms": 4231
}
```

---

## Log Events by Stage

### Stage 1: extract_transcript

| Event | Level | Fields |
|-------|-------|--------|
| Starting transcript fetch | INFO | `content_id` |
| Transcript fetched successfully | INFO | `content_id`, `raw_length_chars`, `snippet_count` |
| Transcript fetch failed | ERROR | `content_id`, `error`, `error_type` |

---

### Stage 2: clean_transcript

| Event | Level | Fields |
|-------|-------|--------|
| Starting LLM cleaning | INFO | `content_id`, `model`, `input_length_chars` |
| Cleaning complete | INFO | `content_id`, `output_length_chars`, `duration_ms` |
| LLM call failed (transient, retrying) | WARNING | `content_id`, `attempt`, `error` |
| LLM call failed (unrecoverable) | ERROR | `content_id`, `error`, `error_type` |

---

### Stage 3: number_transcript

| Event | Level | Fields |
|-------|-------|--------|
| Numbering transcript | INFO | `content_id` |
| Numbering complete | INFO | `content_id`, `point_count`, `output_path` |
| Numbering validation failed | ERROR | `content_id`, `error` |

---

### Stage 4: generate_hierarchy

| Event | Level | Fields |
|-------|-------|--------|
| Starting hierarchy generation | INFO | `content_id`, `model`, `point_count` |
| Hierarchy generated | INFO | `content_id`, `root_node_count`, `duration_ms` |
| LLM call failed | ERROR | `content_id`, `error`, `error_type` |

---

### Stage 5: validate_hierarchy

| Event | Level | Fields |
|-------|-------|--------|
| Validating hierarchy | INFO | `content_id` |
| Hierarchy valid | INFO | `content_id`, `content_node_count` |
| Hierarchy invalid: zero CONTENT nodes | ERROR | `content_id` |

---

### Stage 6: extract_content_nodes

| Event | Level | Fields |
|-------|-------|--------|
| Extracting content nodes | INFO | `content_id` |
| Extraction complete | INFO | `content_id`, `content_node_count`, `payload_count` |

---

### Stage 7: generate_content

| Event | Level | Fields |
|-------|-------|--------|
| Starting content generation | INFO | `content_id`, `initial_partitions` |
| Processing partition | INFO | `content_id`, `partition_index`, `partition_range`, `node_count` |
| Partition complete | INFO | `content_id`, `partition_index`, `duration_ms` |
| Retry triggered (duplicate/incorrect IDs) | WARNING | `content_id`, `partition_index`, `attempt`, `error` |
| Repartitioning (count mismatch) | WARNING | `content_id`, `expected`, `received`, `fallback_partitions` |
| Retries exhausted | ERROR | `content_id`, `partition_index`, `error` |
| All content generated | INFO | `content_id`, `total_content_nodes`, `duration_ms` |

---

### Stage 8: generate_summaries

Same log events as Stage 7, with `node = "generate_summaries"`.

---

### Stage 9: persist_artefacts

| Event | Level | Fields |
|-------|-------|--------|
| Persisting artefacts | INFO | `content_id`, `output_dir` |
| Hierarchy JSON saved | INFO | `content_id`, `path` |
| Content JSON saved | INFO | `content_id`, `path` |
| Persistence failed | ERROR | `content_id`, `path`, `error` |

---

### Stage 10: render_markdown

| Event | Level | Fields |
|-------|-------|--------|
| Rendering markdown documents | INFO | `content_id` |
| Content document saved | INFO | `content_id`, `path`, `size_bytes` |
| Summary document saved | INFO | `content_id`, `path`, `size_bytes` |
| Pipeline complete | INFO | `content_id`, `total_duration_ms` |

---

## Metrics

The following counters and gauges are tracked in-process (not exported externally in V1, but designed for future Prometheus/OpenTelemetry integration):

| Metric | Type | Description |
|--------|------|-------------|
| `pipeline_runs_total` | Counter | Total pipeline runs (all videos) |
| `pipeline_runs_success_total` | Counter | Successful runs |
| `pipeline_runs_failure_total` | Counter | Failed runs |
| `llm_calls_total` | Counter | Total LLM API calls |
| `llm_calls_retried_total` | Counter | Calls that required at least one retry |
| `llm_tokens_used_total` | Counter | Estimated tokens used (if API returns usage) |
| `content_nodes_processed_total` | Counter | Total CONTENT nodes processed |
| `partition_repartitions_total` | Counter | Times fallback partitioning was triggered |
| `pipeline_duration_seconds` | Histogram | End-to-end duration per run |
| `stage_duration_seconds` | Histogram | Per-stage duration (labelled by `stage_name`) |

In V1, metrics are tracked as simple in-memory counters in a `PipelineMetrics` dataclass and logged at pipeline completion.

---

## Tracing

In V1, correlation is provided by:
- **`content_id`** — all log records for a run carry the video ID.
- **`node_name`** — all log records carry the current LangGraph node name.
- **Timestamps** — ISO 8601 timestamps on all records.

In V2, OpenTelemetry traces can be added by wrapping service calls in `tracer.start_as_current_span()`.

---

## Debugging Strategy

### Debugging a failed run

1. Filter logs by `content_id`.
2. Find the first `ERROR` level record.
3. Use `partition_index` and `partition_range` to identify the exact batch that failed.
4. Use `attempt` to understand how many retries occurred.
5. Re-invoke the pipeline with the same `thread_id` — the checkpointer resumes from the last successful node.

### Debugging LLM output quality

1. Enable `LOG_LEVEL=DEBUG`.
2. This emits the serialised LLM input payload for each batch call.
3. Compare input payload with LLM response to diagnose ID mismatches or count errors.

### Debugging hierarchy structure

1. Inspect `transcript_hierarchy.json` in the output directory.
2. Count CONTENT nodes: `jq '[.. | objects | select(.name=="CONTENT")] | length' transcript_hierarchy.json`

---

## Log Configuration Setup

```python
# deep_notes_ai/config/logging_setup.py

import logging
import sys
from pythonjsonlogger import jsonlogger


def configure_logging(log_level: str, structured: bool) -> None:
    handler = logging.StreamHandler(sys.stdout)

    if structured:
        formatter = jsonlogger.JsonFormatter(
            fmt="%(timestamp)s %(level)s %(name)s %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S",
            rename_fields={"levelname": "level", "asctime": "timestamp"},
        )
    else:
        formatter = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        )

    handler.setFormatter(formatter)

    root_logger = logging.getLogger("deep_notes_ai")
    root_logger.setLevel(getattr(logging, log_level.upper()))
    root_logger.addHandler(handler)
    root_logger.propagate = False
```

Called once from `main.py` before graph invocation.
