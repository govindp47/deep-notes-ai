# 13 — Migration Strategy

## Overview

The migration moves the notebook from a research prototype to a production-grade application **without modifying any existing business logic**. The notebook continues to function as the reference implementation throughout the migration. Every implementation step is verified against the notebook's known-good outputs.

---

## Guiding Constraints

1. **No changes to business logic.** Algorithms, prompt text, data models, and LLM call patterns must produce identical outputs.
2. **Notebook is read-only.** The notebook is not touched. It serves as the specification and acceptance test.
3. **Incremental migration.** Each task produces independently runnable, testable code.
4. **Traceability.** Every component maps directly to a specific notebook cell or group of cells.

---

## Migration Phases

### Phase 0: Foundation (Scaffolding)

**Goal:** Create the package structure, configuration, and baseline tooling before any business logic is ported.

**Deliverables:**
- `deep_notes_ai/` package with `__init__.py` files.
- `pyproject.toml` updated with new dev dependencies (`pytest`, `pytest-mock`, `pydantic-settings`, `python-json-logger`).
- `deep_notes_ai/config/settings.py` with `Settings` model.
- `deep_notes_ai/config/logging_setup.py`.
- `.env.example` template.
- `tests/conftest.py` with basic fixtures.

**Acceptance criteria:** `import deep_notes_ai` succeeds. `Settings()` loads from environment.

---

### Phase 1: Domain Layer

**Goal:** Port all data models and pure algorithms from the notebook to the domain layer.

**Source cells → target modules:**

| Notebook cell | Source | Target module |
|---------------|--------|---------------|
| Cell 5 | `TopicNode`, `TranscriptHierarchy` | `domain/models.py` |
| Cell 8 | All dataclasses | `domain/models.py` |
| Cell 10 | `StructuredContent*`, `ContentSummary*` | `domain/models.py` |
| Cell 3 | `clean_bullet_output()` | `domain/algorithms.py` |
| Cell 8 | `load_numbered_points()`, `equal_partition_last_points()`, `build_partition_ranges()`, `_extract_content_nodes()`, `build_content_payloads()`, `filter_payload_by_range()` | `domain/algorithms.py` |

**Prompt files:**
- Extract Cell 1 prompt text → `domain/prompts/cleaning.txt`
- Extract Cell 6 prompt text → `domain/prompts/hierarchy.txt`
- Extract Cell 11 prompt text → `domain/prompts/content.txt`
- Extract Cell 14 prompt text → `domain/prompts/summary.txt`

**Acceptance criteria:**
- All domain unit tests pass (100% coverage on `algorithms.py`).
- `TranscriptHierarchy.model_validate(json.load(...))` produces correct models.
- `build_content_payloads` produces correct `PayloadResult` for a sample input.

---

### Phase 2: Service Layer

**Goal:** Build all service classes with dependency injection.

**Services to build in order (dependencies first):**

1. `ValidationService` — no deps, simplest to build and test first.
2. `RetryService` — no external deps.
3. `PartitionService` — depends on domain/algorithms only.
4. `PersistenceService` — file I/O only.
5. `LLMService` — wraps LangChain, requires API key.
6. `PromptService` — reads prompt files.
7. `TranscriptService` — wraps YouTubeTranscriptApi.
8. `MarkdownService` — depends on domain models only.
9. `ContentService` — depends on LLMService, PartitionService, ValidationService, RetryService.
10. `SummaryService` — same pattern as ContentService.

**Acceptance criteria per service:**
- Service class instantiates without error.
- All unit tests for the service pass.
- Round-trip test for `PersistenceService` (save then load).

---

### Phase 3: LangGraph Pipeline

**Goal:** Build the LangGraph state and graph, connecting nodes to services.

**Build order:**
1. `state.py` — `PipelineState` TypedDict.
2. `nodes/extract_transcript.py` — delegates to `TranscriptService`.
3. `nodes/clean_transcript.py` — delegates to LangChain chain.
4. `nodes/number_transcript.py` — delegates to algorithm + `PersistenceService`.
5. `nodes/generate_hierarchy.py` — delegates to LangChain chain.
6. `nodes/validate_hierarchy.py` — pure validation logic.
7. `nodes/extract_content_nodes.py` — delegates to `build_content_payloads`.
8. `nodes/generate_content.py` — delegates to `ContentService`.
9. `nodes/generate_summaries.py` — delegates to `SummaryService`.
10. `nodes/persist_artefacts.py` — delegates to `PersistenceService`.
11. `nodes/render_markdown.py` — delegates to `MarkdownService` + `PersistenceService`.
12. `graph.py` — assemble `StateGraph`, add nodes, add edges, compile.

**Acceptance criteria:**
- `graph.compile()` succeeds.
- Graph can be drawn with `graph.get_graph().draw_ascii()`.
- Integration test with all LLMs mocked passes.

---

### Phase 4: Entry Point

**Goal:** Build the CLI entry point that wires everything together.

**Deliverables:**
- `main.py` with argument parsing and pipeline invocation.

**CLI signature:**
```bash
python main.py --video-id jGg_1h0qzaM --title "LangGraph Course"
```

**Acceptance criteria:**
- `python main.py --help` prints help text.
- Running with `--video-id jGg_1h0qzaM` (and real API keys) produces the same output as the notebook.

---

### Phase 5: Verification

**Goal:** Confirm production application output matches notebook output.

**Verification approach:**
1. Run the notebook from scratch on the reference video (`jGg_1h0qzaM`). Save outputs.
2. Run the production application on the same video.
3. Compare `nodes_content.json` (content fields) — expect structural equivalence (not character-for-character due to LLM non-determinism, but the same information).
4. Verify `course_content.md` and `course_summary.md` have the same heading structure.

---

## Traceability Map

| Planning Document | Notebook Cells | Target Modules |
|------------------|----------------|----------------|
| `08_data_models.md` | 5, 8, 10 | `domain/models.py` |
| `07_component_design.md` (algorithms) | 3, 8 | `domain/algorithms.py` |
| `10_configuration.md` | — | `config/settings.py` |
| `11_logging_observability.md` | — | `config/logging_setup.py` |
| `07_component_design.md` (Validation) | 10 (`validate_batch_response`) | `services/validation_service.py` |
| `07_component_design.md` (Retry) | 12, 15 (retry loops) | `services/retry_service.py` |
| `07_component_design.md` (Partition) | 8 | `services/partition_service.py` |
| `07_component_design.md` (Persistence) | 10 (`save_nodes_*`), 18 (`load_nodes_*`, `save_markdown`) | `services/persistence_service.py` |
| `07_component_design.md` (LLM) | 2, 7, 12, 15 | `services/llm_service.py` |
| `07_component_design.md` (Prompt) | 1, 6, 11, 14 | `services/prompt_service.py` |
| `07_component_design.md` (Transcript) | 0 | `services/transcript_service.py` |
| `07_component_design.md` (Markdown) | 18 | `services/markdown_service.py` |
| `07_component_design.md` (Content) | 12 | `services/content_service.py` |
| `07_component_design.md` (Summary) | 15 | `services/summary_service.py` |
| `06_state_design.md` | — | `langgraph_pipeline/state.py` |
| `05_langgraph_design.md` | 0 | `nodes/extract_transcript.py` |
| `05_langgraph_design.md` | 2 | `nodes/clean_transcript.py` |
| `05_langgraph_design.md` | 3, 4 | `nodes/number_transcript.py` |
| `05_langgraph_design.md` | 7 | `nodes/generate_hierarchy.py` |
| `05_langgraph_design.md` | — | `nodes/validate_hierarchy.py` |
| `05_langgraph_design.md` | 9 | `nodes/extract_content_nodes.py` |
| `05_langgraph_design.md` | 12, 13 | `nodes/generate_content.py` |
| `05_langgraph_design.md` | 15, 16 | `nodes/generate_summaries.py` |
| `05_langgraph_design.md` | 17 | `nodes/persist_artefacts.py` |
| `05_langgraph_design.md` | 19 | `nodes/render_markdown.py` |
| `05_langgraph_design.md` | — | `langgraph_pipeline/graph.py` |
| — | — | `main.py` |

---

## Risks

| Risk | Likelihood | Mitigation |
|------|-----------|-----------|
| LLM non-determinism causes output drift | High | Use `temperature=0`, accept structural equivalence (not character identity) |
| Context length limits differ from notebook | Low | Keep same partition counts |
| `pydantic_settings` version incompatibility | Low | Pin version in `pyproject.toml` |
| Circular import during package construction | Medium | Enforce dependency direction rules from Day 1 |
| LangGraph checkpointer state schema mismatch | Low | Test checkpoint round-trip in integration tests |

---

## Non-Goals for Migration

The following are explicitly out of scope and are deferred to future iterations:

- Async/parallel LLM calls across partitions.
- Streaming LLM responses.
- Web API or UI wrapper.
- Database storage for content store (beyond JSON files).
- Multi-video batch processing.
- Prompt versioning or A/B testing infrastructure.
- Cost tracking or token accounting.
