# 03 — Target Architecture

## Architectural Style

The target is a **LangGraph-orchestrated, modular Python application** following these architectural principles:

- **Domain-Driven Layering** — business logic lives in a pure domain layer with no framework dependencies.
- **Dependency Inversion** — high-level orchestration depends on abstract interfaces, not concrete implementations.
- **Single Responsibility** — every module does one thing. Prompts, models, LLM calls, persistence, and rendering are each in their own modules.
- **Typed Python** — `TypedDict`, Pydantic, dataclasses, and `typing` annotations throughout.
- **Configuration-driven** — no hardcoded video IDs, file paths, model names, or retry counts.
- **Testability** — every component can be tested in isolation by injecting stubs.

---

## Layered Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         ENTRYPOINT                           │
│   main.py / CLI   →   PipelineRunner                        │
└──────────────────────────────┬──────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────┐
│                     GRAPH ORCHESTRATION                       │
│   langgraph_pipeline/graph.py                                │
│   LangGraph StateGraph + nodes + edges + checkpointer        │
└──────────────────────────────┬──────────────────────────────┘
                               │ (nodes call into)
┌──────────────────────────────▼──────────────────────────────┐
│                       SERVICE LAYER                           │
│   services/                                                  │
│     transcript_service.py   — YouTube extraction             │
│     llm_service.py          — LLM client factory             │
│     prompt_service.py       — prompt loading / rendering     │
│     partition_service.py    — transcript partitioning        │
│     validation_service.py   — batch response validation      │
│     persistence_service.py  — file I/O                       │
│     retry_service.py        — retry orchestration            │
│     content_service.py      — content generation batching    │
│     summary_service.py      — summary generation batching    │
│     markdown_service.py     — markdown rendering             │
└──────────────────────────────┬──────────────────────────────┘
                               │ (services use)
┌──────────────────────────────▼──────────────────────────────┐
│                       DOMAIN LAYER                            │
│   domain/                                                    │
│     models.py       — all dataclasses & Pydantic models      │
│     algorithms.py   — pure algorithms (partition, extract)   │
│     prompts/        — prompt template files                  │
└─────────────────────────────────────────────────────────────┘
```

---

## Package Boundaries and Responsibilities

### `deep_notes_ai/` (root package)

The single importable Python package. All public API lives here.

---

### `deep_notes_ai/domain/`

**Contains:** Pure business objects and algorithms. Zero framework dependencies. Zero I/O.

| Module | Responsibility |
|--------|---------------|
| `models.py` | All dataclasses (`ContentStoreItem`, `ContentNode`, `TitleNode`, `ContentExtraction`, `ExtractionResult`, `ContentPayload`, `StructuredContentPayload`, `PayloadResult`) and Pydantic models (`TopicNode`, `TranscriptHierarchy`, `StructuredContent`, `StructuredContentBatch`, `ContentSummary`, `ContentSummaryBatch`) |
| `algorithms.py` | `clean_bullet_output()`, `load_numbered_points()`, `equal_partition_last_points()`, `build_partition_ranges()`, `_extract_content_nodes()`, `build_content_payloads()`, `filter_payload_by_range()` |
| `prompts/` | Directory containing raw prompt template files as plain text |

**Dependency direction:** Domain depends on nothing outside the Python standard library and Pydantic.

---

### `deep_notes_ai/services/`

**Contains:** Components that interact with external systems or orchestrate domain logic.

| Module | Responsibility |
|--------|---------------|
| `transcript_service.py` | Wrap `YouTubeTranscriptApi`, return raw transcript string |
| `llm_service.py` | LLM client factory — given model name, return configured `BaseChatModel` |
| `prompt_service.py` | Load prompt templates from `domain/prompts/`, render with variables, return `ChatPromptTemplate` |
| `partition_service.py` | Wrap partition/range algorithms, inject transcript file path |
| `validation_service.py` | `validate_batch_response()` logic |
| `persistence_service.py` | All file I/O — read/write numbered transcript, hierarchy JSON, content JSON, markdown files |
| `retry_service.py` | Retry loop logic, retry count, error classification |
| `content_service.py` | Orchestrate batched content generation (partition → temp-ID → LLM → map back → store) |
| `summary_service.py` | Orchestrate batched summary generation (same pattern as content) |
| `markdown_service.py` | `_render_node()`, `build_markdown_document()`, `_load_node()`, hierarchy loading |

**Dependency direction:** Services depend on domain. Services never depend on each other directly (they may receive collaborators via dependency injection).

---

### `deep_notes_ai/langgraph_pipeline/`

**Contains:** LangGraph graph definition and all node implementations.

| Module | Responsibility |
|--------|---------------|
| `state.py` | `PipelineState` TypedDict — the single shared state object |
| `graph.py` | Graph construction: `StateGraph`, nodes, edges, conditional edges, checkpointer setup |
| `nodes/extract_transcript.py` | LangGraph node: call `transcript_service` |
| `nodes/clean_transcript.py` | LangGraph node: call cleaning LLM |
| `nodes/number_transcript.py` | LangGraph node: apply `clean_bullet_output`, write numbered file |
| `nodes/generate_hierarchy.py` | LangGraph node: call hierarchy LLM |
| `nodes/validate_hierarchy.py` | LangGraph node: validate hierarchy has CONTENT nodes |
| `nodes/extract_content_nodes.py` | LangGraph node: call `build_content_payloads` |
| `nodes/generate_content.py` | LangGraph node: call `content_service` |
| `nodes/generate_summaries.py` | LangGraph node: call `summary_service` |
| `nodes/persist_artefacts.py` | LangGraph node: call `persistence_service` |
| `nodes/render_markdown.py` | LangGraph node: call `markdown_service` |

**Dependency direction:** Graph nodes depend on services. Graph nodes never contain business logic — they delegate entirely to services.

---

### `deep_notes_ai/config/`

| Module | Responsibility |
|--------|---------------|
| `settings.py` | Pydantic `Settings` model reading from environment + `.env` file |
| `prompts.py` | Prompt-related configuration (model assignments per stage) |

---

### `tests/`

| Directory | Responsibility |
|-----------|---------------|
| `tests/unit/` | Unit tests for domain algorithms and service logic |
| `tests/integration/` | Tests with real file I/O and real LLM (optional) |
| `tests/fixtures/` | Sample transcript files, hierarchy JSON, content JSON |
| `tests/golden/` | Golden output files for snapshot-style testing |

---

## Dependency Direction (Strict Rule)

```
config → (nothing)
domain → (nothing outside stdlib + pydantic)
services → domain, config
langgraph_pipeline → services, domain, config
tests → everything
```

**Forbidden:**
- Domain importing from services.
- Services importing from `langgraph_pipeline`.
- Circular imports of any kind.

---

## Separation of Concerns

| Concern | Where it lives |
|---------|---------------|
| Data shape | `domain/models.py` |
| Pure algorithms | `domain/algorithms.py` |
| Prompt text | `domain/prompts/*.txt` |
| LLM client configuration | `services/llm_service.py` |
| Prompt rendering | `services/prompt_service.py` |
| Retry logic | `services/retry_service.py` |
| Batch validation | `services/validation_service.py` |
| Batch content generation | `services/content_service.py` |
| Batch summary generation | `services/summary_service.py` |
| File I/O | `services/persistence_service.py` |
| Markdown building | `services/markdown_service.py` |
| Graph state | `langgraph_pipeline/state.py` |
| Graph wiring | `langgraph_pipeline/graph.py` |
| Node execution | `langgraph_pipeline/nodes/*.py` |
| Environment configuration | `config/settings.py` |

---

## Key Architectural Decisions

### Decision 1: One LangGraph graph for the entire pipeline

The pipeline maps cleanly to a single linear LangGraph graph because:
- Each stage has a clear predecessor and successor.
- State flows forward only.
- Retry logic is within individual nodes, not between nodes.
- A single checkpointer enables resumption from any node.

### Decision 2: Services receive dependencies via constructor injection

Instead of module-level globals, services accept their dependencies in `__init__`. This enables:
- Swapping the LLM client in tests.
- Using a mock persistence layer.
- Testing retry logic with a stub that always fails on attempt 1.

### Decision 3: Prompts are files, not Python strings

Moving prompt templates to `domain/prompts/*.txt` enables:
- Version control of prompts independently of code.
- Easy A/B testing of prompts.
- Prompt-specific testing.

### Decision 4: Temporary ID mapping is explicit and isolated

The `N1..Nk` ↔ UUID mapping lives entirely inside `content_service` and `summary_service`. The LangGraph state and domain models never see temporary IDs.

### Decision 5: Partition configuration is explicit

`INITIAL_PARTITIONS`, `FALLBACK_PARTITIONS`, and `MAX_RETRIES` come from `config/settings.py`, not hardcoded in service classes.
