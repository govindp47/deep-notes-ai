# 04 — Project Structure

## Complete Directory Tree

```
deep-notes-ai/
│
├── pyproject.toml                    # project metadata, dependencies
├── .python-version                   # Python version pin
├── .env                              # environment variables (not committed)
├── .gitignore
├── README.md
├── main.py                           # CLI entrypoint
│
├── notebook/                         # legacy notebook (read-only reference)
│   └── content_extraction.ipynb
│
├── docs/
│   └── planning/                     # architectural planning documents
│       ├── 01_system_overview.md
│       ├── 02_existing_pipeline_analysis.md
│       ├── 03_target_architecture.md
│       ├── 04_project_structure.md
│       ├── 05_langgraph_design.md
│       ├── 06_state_design.md
│       ├── 07_component_design.md
│       ├── 08_data_models.md
│       ├── 09_error_handling.md
│       ├── 10_configuration.md
│       ├── 11_logging_observability.md
│       ├── 12_testing_strategy.md
│       ├── 13_migration_strategy.md
│       └── 14_task_breakdown.md
│
├── deep_notes_ai/                    # main Python package
│   ├── __init__.py
│   │
│   ├── config/                       # configuration management
│   │   ├── __init__.py
│   │   └── settings.py               # Pydantic Settings model (env + .env)
│   │
│   ├── domain/                       # pure business logic — no framework deps
│   │   ├── __init__.py
│   │   ├── models.py                 # all dataclasses and Pydantic models
│   │   ├── algorithms.py             # pure algorithms (partition, extract, number)
│   │   └── prompts/                  # prompt template files (plain text)
│   │       ├── cleaning.txt          # transcript cleaning prompt
│   │       ├── hierarchy.txt         # hierarchy generation prompt
│   │       ├── content.txt           # structured content generation prompt
│   │       └── summary.txt           # revision-note summary prompt
│   │
│   ├── services/                     # external integrations and orchestration
│   │   ├── __init__.py
│   │   ├── transcript_service.py     # YouTube transcript extraction
│   │   ├── llm_service.py            # LLM client factory
│   │   ├── prompt_service.py         # prompt loading and rendering
│   │   ├── partition_service.py      # transcript partitioning helpers
│   │   ├── validation_service.py     # LLM batch response validation
│   │   ├── persistence_service.py    # file read/write operations
│   │   ├── retry_service.py          # retry loop and error classification
│   │   ├── content_service.py        # batched content generation orchestration
│   │   ├── summary_service.py        # batched summary generation orchestration
│   │   └── markdown_service.py       # markdown rendering and Node hierarchy loading
│   │
│   └── langgraph_pipeline/           # LangGraph graph definition and nodes
│       ├── __init__.py
│       ├── state.py                  # PipelineState TypedDict
│       ├── graph.py                  # StateGraph construction and compilation
│       └── nodes/                    # one file per LangGraph node
│           ├── __init__.py
│           ├── extract_transcript.py # Stage 1: fetch YouTube transcript
│           ├── clean_transcript.py   # Stage 2: LLM cleaning
│           ├── number_transcript.py  # Stage 3: point numbering
│           ├── generate_hierarchy.py # Stage 4: LLM hierarchy generation
│           ├── validate_hierarchy.py # Stage 5: hierarchy validation
│           ├── extract_content_nodes.py # Stage 6: CONTENT node extraction
│           ├── generate_content.py   # Stage 7: structured content generation
│           ├── generate_summaries.py # Stage 8: revision summary generation
│           ├── persist_artefacts.py  # Stage 9: JSON persistence
│           └── render_markdown.py    # Stage 10: final markdown rendering
│
└── tests/
    ├── __init__.py
    ├── conftest.py                   # shared fixtures
    │
    ├── fixtures/                     # static test data files
    │   ├── sample_numbered.md        # minimal numbered transcript
    │   ├── sample_hierarchy.json     # small TranscriptHierarchy JSON
    │   ├── sample_nodes_hierarchy.json  # small Node hierarchy JSON
    │   └── sample_nodes_content.json   # small nodes_content JSON
    │
    ├── golden/                       # golden output files for snapshot tests
    │   ├── course_content.md
    │   └── course_summary.md
    │
    ├── unit/                         # unit tests — no I/O, no real LLM
    │   ├── __init__.py
    │   ├── domain/
    │   │   ├── __init__.py
    │   │   ├── test_models.py
    │   │   └── test_algorithms.py
    │   └── services/
    │       ├── __init__.py
    │       ├── test_validation_service.py
    │       ├── test_partition_service.py
    │       ├── test_persistence_service.py
    │       ├── test_content_service.py
    │       ├── test_summary_service.py
    │       └── test_markdown_service.py
    │
    └── integration/                  # integration tests — real file I/O, mocked LLM
        ├── __init__.py
        ├── test_pipeline_flow.py     # full pipeline with all LLMs mocked
        └── test_langgraph_graph.py   # LangGraph graph smoke test
```

---

## Module Responsibilities (Detailed)

### `main.py`

- CLI entrypoint using Python `argparse` or `typer`.
- Accepts: `--video-id`, `--title`, `--output-dir`.
- Loads config from environment.
- Constructs the LangGraph pipeline.
- Invokes the pipeline with the input state.
- Prints status and final output paths.

---

### `deep_notes_ai/config/settings.py`

- Pydantic `BaseSettings` model.
- Reads from environment variables and `.env` file via `python-dotenv`.
- Fields: `openai_api_key`, `nvidia_api_key`, `cleaning_model`, `hierarchy_model`, `content_model`, `summary_model`, `initial_partitions`, `fallback_partitions`, `max_retries`, `output_dir`, `artefacts_dir`.

---

### `deep_notes_ai/domain/models.py`

All data shapes used throughout the system. No logic. No I/O.

- `ContentStoreItem` dataclass
- `ContentNode` dataclass
- `TitleNode` dataclass
- `Node` type alias
- `ContentExtraction` dataclass
- `ExtractionResult` dataclass
- `ContentPayload` dataclass
- `StructuredContentPayload` dataclass
- `PayloadResult` dataclass
- `TopicNode` Pydantic model
- `TranscriptHierarchy` Pydantic model
- `StructuredContent` Pydantic model
- `StructuredContentBatch` Pydantic model
- `ContentSummary` Pydantic model
- `ContentSummaryBatch` Pydantic model

---

### `deep_notes_ai/domain/algorithms.py`

Pure functions. Accept only primitive types and domain models. No I/O.

- `clean_bullet_output(text: str) -> str`
- `load_numbered_points_from_text(text: str) -> list[str]` _(text-based version of the original file-based function)_
- `equal_partition_last_points_from_text(text: str, n: int) -> list[int]`
- `build_partition_ranges(last_points: list[int]) -> list[tuple[int, int]]`
- `_extract_content_nodes(node: TopicNode, path: tuple[str, ...]) -> ExtractionResult`
- `build_content_payloads(hierarchy: list[TopicNode], content_points_list: list[str]) -> PayloadResult`
- `filter_payload_by_range(payload: list[ContentPayload], start: int, end: int) -> list[ContentPayload]`

---

### `deep_notes_ai/domain/prompts/`

Plain text files. Each file is one prompt template with `{VARIABLE_NAME}` placeholders.

- `cleaning.txt` — transcript cleaning prompt (from Cell 1). Variable: `{RAW_TRANSCRIPT}`
- `hierarchy.txt` — hierarchy generation prompt (from Cell 6). Variable: `{CLEANED_NUMBERED_TRANSCRIPT}`
- `content.txt` — content structuring prompt (from Cell 11). Variable: `{NODES_CONTENT}`
- `summary.txt` — revision summary prompt (from Cell 14). Variable: `{NODES_CONTENT}`

---

### `deep_notes_ai/services/transcript_service.py`

```
TranscriptService
    fetch(content_id: str) -> str
```

- Wraps `YouTubeTranscriptApi`.
- Returns joined raw transcript string.
- Raises `TranscriptFetchError` on failure.

---

### `deep_notes_ai/services/llm_service.py`

```
LLMService
    get_client(provider: str, model: str, **kwargs) -> BaseChatModel
    get_structured_client(provider: str, model: str, schema: type) -> Runnable
```

- Provider options: `"openai"`, `"nvidia"`.
- Returns configured `ChatOpenAI` or `ChatNVIDIA` instances.
- `get_structured_client` chains `.with_structured_output(schema)`.

---

### `deep_notes_ai/services/prompt_service.py`

```
PromptService
    load(prompt_name: str) -> ChatPromptTemplate
    render(prompt_name: str, variables: dict) -> str
```

- Loads prompt templates from `domain/prompts/`.
- Returns `ChatPromptTemplate` ready for chaining.

---

### `deep_notes_ai/services/partition_service.py`

```
PartitionService
    compute_last_points(transcript_text: str, n: int) -> list[int]
    compute_ranges(last_points: list[int]) -> list[tuple[int, int]]
```

- Delegates to `domain/algorithms.py`.
- Accepts transcript text directly (no file path).

---

### `deep_notes_ai/services/validation_service.py`

```
ValidationService
    validate_batch(response: Any, expected_ids: set[str], entity_name: str) -> None
```

- Raises `BatchCountMismatchError` if item count is wrong.
- Raises `DuplicateIdsError` if duplicate IDs found.
- Raises `IncorrectIdsError` if IDs don't match expected.

---

### `deep_notes_ai/services/persistence_service.py`

```
PersistenceService
    save_text(path: Path, text: str) -> None
    load_text(path: Path) -> str
    save_json(path: Path, obj: Any) -> None
    load_json(path: Path) -> Any
    save_nodes_hierarchy(path: Path, nodes: list[Node]) -> None
    save_nodes_content(path: Path, content: dict[str, ContentStoreItem]) -> None
    load_nodes_hierarchy(path: Path) -> list[Node]
    load_nodes_content(path: Path) -> dict[str, ContentStoreItem]
    save_markdown(path: Path, markdown: str) -> None
```

- All I/O in UTF-8.
- Uses `json_serializer` for dataclasses.

---

### `deep_notes_ai/services/retry_service.py`

```
RetryService
    invoke_with_retry(
        fn: Callable,
        args: tuple,
        max_retries: int,
        is_retryable: Callable[[Exception], bool],
    ) -> Any
```

- Generic retry loop.
- Calls `fn(*args)` up to `max_retries` times.
- If `is_retryable(e)` returns `False`, re-raises immediately.
- Raises `RetryExhaustedError` after all attempts.

---

### `deep_notes_ai/services/content_service.py`

```
ContentService
    generate(
        transcript_text: str,
        payload: list[ContentPayload],
        nodes_content: dict[str, ContentStoreItem],
        initial_partitions: int,
        fallback_partitions: int,
        max_retries: int,
    ) -> None  # mutates nodes_content in place
```

- Orchestrates partition → temp-ID map → LLM invoke → validation → store.
- Catches `BatchCountMismatchError` and falls back to higher partition count.
- Delegates per-partition calls to `RetryService`.

---

### `deep_notes_ai/services/summary_service.py`

```
SummaryService
    generate(
        transcript_text: str,
        payload: list[ContentPayload],
        nodes_content: dict[str, ContentStoreItem],
        initial_partitions: int,
        fallback_partitions: int,
        max_retries: int,
    ) -> None  # mutates nodes_content in place
```

Same pattern as `ContentService` but uses `summary_chain` and `StructuredContentPayload` input.

---

### `deep_notes_ai/services/markdown_service.py`

```
MarkdownService
    build_document(
        content_title: str,
        hierarchy: list[Node],
        content_store: dict[str, ContentStoreItem],
        summary: bool,
    ) -> str
```

- Delegates to `_render_node()` recursively.
- Returns complete markdown string.

---

### `deep_notes_ai/langgraph_pipeline/state.py`

Defines `PipelineState(TypedDict)` with all pipeline-wide fields.

---

### `deep_notes_ai/langgraph_pipeline/graph.py`

- Constructs `StateGraph(PipelineState)`.
- Adds all nodes.
- Adds all edges.
- Adds conditional edges where needed.
- Attaches a `MemorySaver` or `SqliteSaver` checkpointer.
- Compiles and returns the compiled graph.

---

### `deep_notes_ai/langgraph_pipeline/nodes/*.py`

Each node file exports a single function:

```python
def node_name(state: PipelineState) -> dict:
    ...
    return {"field_name": value}
```

Nodes read from `state`, call services, return a dictionary of updated state fields.
Nodes never mutate state directly.
