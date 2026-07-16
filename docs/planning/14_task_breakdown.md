# 14 — Task Breakdown

## Instructions for Implementors

This document is the authoritative implementation task list.

Each task is:
- **Atomic** — it touches one module or one group of closely related files.
- **Independently verifiable** — it has acceptance criteria that can be checked without running the full pipeline.
- **Traceable** — every task maps back to planning documents and notebook cells.
- **Ordered** — dependencies are resolved; implement tasks in the order listed.

Do not begin implementation of a task until all tasks it depends on are complete and verified.

---

## Phase 0 — Foundation

---

### TASK-001: Create Package Scaffold

**Description:** Create the complete directory and `__init__.py` file structure for the `deep_notes_ai` package and all sub-packages.

**Files to create:**
```
deep_notes_ai/__init__.py
deep_notes_ai/config/__init__.py
deep_notes_ai/domain/__init__.py
deep_notes_ai/domain/prompts/                (directory only — no Python file)
deep_notes_ai/services/__init__.py
deep_notes_ai/langgraph_pipeline/__init__.py
deep_notes_ai/langgraph_pipeline/nodes/__init__.py
tests/__init__.py
tests/unit/__init__.py
tests/unit/domain/__init__.py
tests/unit/services/__init__.py
tests/integration/__init__.py
tests/fixtures/                              (directory only)
tests/golden/                                (directory only)
```

**`__init__.py` contents:** Empty files (no imports at this stage).

**References:** `04_project_structure.md`

**Acceptance criteria:**
- `python -c "import deep_notes_ai"` succeeds from the project root.
- `python -c "import deep_notes_ai.config"` succeeds.
- `python -c "import deep_notes_ai.domain"` succeeds.
- `python -c "import deep_notes_ai.services"` succeeds.
- `python -c "import deep_notes_ai.langgraph_pipeline"` succeeds.
- `python -m pytest tests/` exits with "no tests collected" (not an import error).

---

### TASK-002: Update pyproject.toml

**Description:** Add all new development and runtime dependencies required for the production application.

**New dependencies to add to `[project].dependencies`:**
```
pydantic-settings>=2.7.0
python-json-logger>=3.2.0
```

**New dev dependencies to add under `[dependency-groups]` or `[project.optional-dependencies]`:**
```
pytest>=8.0.0
pytest-mock>=3.14.0
```

**References:** `12_testing_strategy.md`, `10_configuration.md`

**Acceptance criteria:**
- `uv sync` completes without error.
- `python -c "from pydantic_settings import BaseSettings"` succeeds.
- `python -c "from pythonjsonlogger import jsonlogger"` succeeds.
- `uv run pytest --version` succeeds.

---

### TASK-003: Create Settings Model

**Description:** Implement `deep_notes_ai/config/settings.py` with the `Settings` Pydantic `BaseSettings` class.

**File:** `deep_notes_ai/config/settings.py`

**Must implement exactly the fields described in `10_configuration.md`:**
- `openai_api_key`
- `nvidia_api_key`
- `cleaning_model_provider`, `cleaning_model_name`
- `hierarchy_model_provider`, `hierarchy_model_name`
- `content_model_provider`, `content_model_name`
- `summary_model_provider`, `summary_model_name`
- `llm_temperature`
- `max_retries`
- `content_initial_partitions`, `content_fallback_partitions`
- `summary_initial_partitions`, `summary_fallback_partitions`
- `output_base_dir`
- `artefacts_dir`
- `prompts_dir`
- `checkpoints_db`
- `use_sqlite_checkpointer`
- `enable_structured_logging`
- `log_level`

**References:** `10_configuration.md`

**Acceptance criteria:**
- `Settings(OPENAI_API_KEY="test-key")` instantiates without error.
- `Settings(OPENAI_API_KEY="test-key").max_retries == 2` is `True`.
- `Settings(OPENAI_API_KEY="test-key", MAX_RETRIES=5).max_retries == 5` is `True`.
- Instantiating without `OPENAI_API_KEY` raises `ValidationError`.

---

### TASK-004: Create Logging Setup

**Description:** Implement `deep_notes_ai/config/logging_setup.py` with the `configure_logging()` function.

**File:** `deep_notes_ai/config/logging_setup.py`

**Must implement:**
- `configure_logging(log_level: str, structured: bool) -> None`
- When `structured=True`: uses `pythonjsonlogger.JsonFormatter`
- When `structured=False`: uses `logging.Formatter` with human-readable format
- Attaches handler to `logging.getLogger("deep_notes_ai")`
- Sets `propagate = False`

**References:** `11_logging_observability.md`

**Acceptance criteria:**
- `configure_logging("INFO", structured=False)` does not raise.
- `configure_logging("DEBUG", structured=True)` does not raise.
- After calling with `structured=True`, a log record from `logging.getLogger("deep_notes_ai.test")` produces a line parseable as JSON.

---

### TASK-005: Create .env.example

**Description:** Create `.env.example` file in the project root with all documented environment variables.

**File:** `.env.example`

**References:** `10_configuration.md`

**Acceptance criteria:** `.env.example` exists and contains all documented environment variable names with placeholder values.

---

## Phase 1 — Domain Layer

---

### TASK-006: Port Data Models

**Description:** Implement `deep_notes_ai/domain/models.py` with all data models ported exactly from the notebook.

**Models to implement (in this order):**

1. **`ContentStoreItem`** (dataclass) — from notebook Cell 8
   ```python
   @dataclass(slots=True)
   class ContentStoreItem:
       content: str = ""
       summary: str = ""
   ```

2. **`ContentNode`** (dataclass) — from notebook Cell 8
   ```python
   @dataclass(slots=True)
   class ContentNode:
       type: Literal["content"] = "content"
       id: str = ""
   ```

3. **`TitleNode`** (dataclass) — from notebook Cell 8
   ```python
   @dataclass(slots=True)
   class TitleNode:
       type: Literal["topic"] = "topic"
       name: str = ""
       subtopics: list["Node"] = field(default_factory=list)
   ```

4. **`Node`** (type alias): `Node = TitleNode | ContentNode`

5. **`ContentExtraction`** (dataclass) — from notebook Cell 8

6. **`ExtractionResult`** (dataclass) — from notebook Cell 8

7. **`ContentPayload`** (dataclass) — from notebook Cell 8

8. **`StructuredContentPayload`** (dataclass) — from notebook Cell 8

9. **`PayloadResult`** (dataclass) — from notebook Cell 8

10. **`TopicNode`** (Pydantic `BaseModel`) — from notebook Cell 5
    - Must include `TopicNode.model_rebuild()` call at module level

11. **`TranscriptHierarchy`** (Pydantic `BaseModel`) — from notebook Cell 5

12. **`StructuredContent`** (Pydantic `BaseModel`) — from notebook Cell 10

13. **`StructuredContentBatch`** (Pydantic `BaseModel`) — from notebook Cell 10

14. **`ContentSummary`** (Pydantic `BaseModel`) — from notebook Cell 10

15. **`ContentSummaryBatch`** (Pydantic `BaseModel`) — from notebook Cell 10

**Custom exceptions to add to this file or a sibling `exceptions.py`:**
- `TranscriptFetchError`, `LLMCallError`, `PromptNotFoundError`, `PersistenceError`
- `AlgorithmError`, `HierarchyValidationError`
- `BatchCountMismatchError`, `DuplicateIdsError`, `IncorrectIdsError`
- `RetryExhaustedError`
- `ContentGenerationError`, `SummaryGenerationError`

**References:** `08_data_models.md`, notebook cells 5, 8, 10

**Acceptance criteria:**
- `from deep_notes_ai.domain.models import ContentStoreItem, TopicNode, TranscriptHierarchy` succeeds.
- `ContentStoreItem()` produces `ContentStoreItem(content="", summary="")`.
- `TopicNode(name="Test", start_point=1, end_point=5)` is valid.
- `TranscriptHierarchy.model_validate({"hierarchy": []})` succeeds.
- `TopicNode(name="CONTENT", start_point=1, end_point=1, children=[])` is valid.
- All unit tests in `tests/unit/domain/test_models.py` pass.

---

### TASK-007: Port Domain Algorithms

**Description:** Implement `deep_notes_ai/domain/algorithms.py` with all pure algorithms ported exactly from the notebook.

**Functions to implement (in this order):**

1. **`json_serializer(obj) -> Any`** — custom JSON default for dataclasses (from Cell 8)

2. **`clean_bullet_output(text: str) -> str`** — from notebook Cell 3
   - Must pass the same tests as the notebook function
   - Normalise line endings, detect bullet patterns, number sequentially

3. **`load_numbered_points_from_text(text: str) -> list[str]`** — adapted from `load_numbered_points()` in Cell 8
   - Accept text instead of file path
   - Raise `AlgorithmError` if numbering is invalid

4. **`equal_partition_last_points_from_text(text: str, n: int) -> list[int]`** — adapted from Cell 8
   - Accept text instead of file path

5. **`build_partition_ranges(last_points: list[int]) -> list[tuple[int, int]]`** — from Cell 8

6. **`_extract_content_nodes(node: TopicNode, path: tuple[str, ...] = ()) -> ExtractionResult`** — from Cell 8
   - Identical logic to notebook
   - UUID generation must happen here

7. **`build_content_payloads(hierarchy: list[TopicNode], content_points_list: list[str]) -> PayloadResult`** — from Cell 8
   - Identical logic to notebook including gap filling

8. **`filter_payload_by_range(payload: list[ContentPayload], start_point: int, end_point: int) -> list[ContentPayload]`** — from Cell 8

**References:** `08_data_models.md`, `07_component_design.md`, notebook cells 3, 8

**Acceptance criteria:**
- All unit tests in `tests/unit/domain/test_algorithms.py` pass (100% coverage).
- `clean_bullet_output("- First\n- Second")` returns `"1. First\n2. Second"`.
- `build_partition_ranges([145, 287, 421])` returns `[(1, 145), (146, 287), (288, 421)]`.
- `build_content_payloads` produces correct UUIDs and empty `ContentStoreItem` objects.

---

### TASK-008: Extract Prompt Files

**Description:** Extract the four prompt template strings from the notebook and write them as plain text files.

**Files to create:**

1. `deep_notes_ai/domain/prompts/cleaning.txt`
   - Source: notebook Cell 1 (`prompt_template` variable)
   - Template variable: `{RAW_TRANSCRIPT}`

2. `deep_notes_ai/domain/prompts/hierarchy.txt`
   - Source: notebook Cell 6 (`topics_prompt` variable)
   - Template variable: `{CLEANED_NUMBERED_TRANSCRIPT}`

3. `deep_notes_ai/domain/prompts/content.txt`
   - Source: notebook Cell 11 (`content_nodes_prompt` variable)
   - Template variable: `{NODES_CONTENT}`

4. `deep_notes_ai/domain/prompts/summary.txt`
   - Source: notebook Cell 14 (`nodes_summary_prompt` variable)
   - Template variable: `{NODES_CONTENT}`

**Important:** Copy prompt text verbatim. Do not modify wording, structure, or variable names.

**References:** `04_project_structure.md`, `10_configuration.md`, notebook cells 1, 6, 11, 14

**Acceptance criteria:**
- All four `.txt` files exist.
- Each file contains the exact prompt text from the corresponding notebook cell.
- `open("deep_notes_ai/domain/prompts/cleaning.txt").read()` contains `{RAW_TRANSCRIPT}`.
- `open("deep_notes_ai/domain/prompts/hierarchy.txt").read()` contains `{CLEANED_NUMBERED_TRANSCRIPT}`.
- `open("deep_notes_ai/domain/prompts/content.txt").read()` contains `{NODES_CONTENT}`.
- `open("deep_notes_ai/domain/prompts/summary.txt").read()` contains `{NODES_CONTENT}`.

---

### TASK-009: Create Domain Unit Test Suite

**Description:** Write all domain unit tests for models and algorithms.

**Files to create:**
- `tests/unit/domain/test_models.py`
- `tests/unit/domain/test_algorithms.py`
- `tests/conftest.py` (shared fixtures)

**Must include all tests listed in `12_testing_strategy.md` under "Domain Unit Tests".**

**References:** `12_testing_strategy.md`

**Acceptance criteria:**
- `uv run pytest tests/unit/domain/ -v` passes with 0 failures.
- Coverage on `domain/algorithms.py` is 100%.

---

## Phase 2 — Service Layer

---

### TASK-010: Implement ValidationService

**Description:** Implement `deep_notes_ai/services/validation_service.py`.

**Must implement:**
- `ValidationService.validate_batch(response, expected_ids, entity_name)` raising typed errors.

**References:** `07_component_design.md` (Component 5), `09_error_handling.md`

**Acceptance criteria:**
- `ValidationService().validate_batch(valid_response, expected_ids)` does not raise.
- A batch with wrong count raises `BatchCountMismatchError`.
- A batch with duplicate IDs raises `DuplicateIdsError`.
- A batch with incorrect IDs raises `IncorrectIdsError`.
- All tests in `tests/unit/services/test_validation_service.py` pass.

---

### TASK-011: Implement RetryService

**Description:** Implement `deep_notes_ai/services/retry_service.py`.

**Must implement:**
- `RetryService.__init__(max_retries: int)`
- `RetryService.invoke(fn, is_retryable) -> Any`

**References:** `07_component_design.md` (Component 7), `09_error_handling.md`

**Acceptance criteria:**
- Succeeds on first call with no retry.
- Retries when `is_retryable` returns `True`.
- Does not retry when `is_retryable` returns `False`.
- Raises `RetryExhaustedError` after `max_retries` failed attempts.
- All tests in `tests/unit/services/test_retry_service.py` pass.

---

### TASK-012: Implement PartitionService

**Description:** Implement `deep_notes_ai/services/partition_service.py`.

**Must implement:**
- `PartitionService.compute_last_points(transcript_text, n) -> list[int]`
- `PartitionService.compute_ranges(last_points) -> list[tuple[int, int]]`

**References:** `07_component_design.md` (Component 4)

**Acceptance criteria:**
- `compute_last_points("1. A\n2. B\n3. C", 2)` returns `[2, 3]` (or equivalent correct boundary).
- All tests in `tests/unit/services/test_partition_service.py` pass.

---

### TASK-013: Implement PersistenceService

**Description:** Implement `deep_notes_ai/services/persistence_service.py`.

**Must implement all methods listed in `07_component_design.md` (Component 6).**

**Key requirement:** `load_nodes_hierarchy` must reconstruct `TitleNode` / `ContentNode` from raw JSON using `_load_node` logic from notebook Cell 18.

**References:** `07_component_design.md` (Component 6), notebook cells 10, 17, 18

**Acceptance criteria:**
- All unit tests in `tests/unit/services/test_persistence_service.py` pass.
- `save_nodes_hierarchy(path, nodes)` followed by `load_nodes_hierarchy(path)` produces structurally identical objects.
- `save_nodes_content(path, content)` followed by `load_nodes_content(path)` produces identical `ContentStoreItem` objects.
- Non-existent file on `load_text` raises `PersistenceError`.

---

### TASK-014: Implement LLMService

**Description:** Implement `deep_notes_ai/services/llm_service.py`.

**Must implement:**
- `LLMService.__init__(settings: Settings)`
- `LLMService.get_chat_model(provider, model, temperature) -> BaseChatModel`
- `LLMService.get_structured_model(provider, model, output_schema, temperature) -> Runnable`

**Supported providers:** `"openai"`, `"nvidia"`

**References:** `07_component_design.md` (Component 2)

**Acceptance criteria:**
- `LLMService(settings).get_chat_model("openai", "gpt-4o-mini")` returns a `ChatOpenAI` instance.
- `LLMService(settings).get_structured_model("openai", "gpt-4o-mini", StructuredContentBatch)` returns a `Runnable`.
- Unknown provider raises `ValueError`.
- No real LLM call is made in tests (constructor only — method calls are mocked at test level).

---

### TASK-015: Implement PromptService

**Description:** Implement `deep_notes_ai/services/prompt_service.py`.

**Must implement:**
- `PromptService.__init__(prompts_dir: Path)`
- `PromptService.load(name: str) -> ChatPromptTemplate`

**References:** `07_component_design.md` (Component 3)

**Acceptance criteria:**
- `PromptService(prompts_dir).load("cleaning")` returns a `ChatPromptTemplate` with variable `RAW_TRANSCRIPT`.
- `PromptService(prompts_dir).load("hierarchy")` returns a `ChatPromptTemplate` with variable `CLEANED_NUMBERED_TRANSCRIPT`.
- `PromptService(prompts_dir).load("nonexistent")` raises `PromptNotFoundError`.
- Templates are cached (calling `load("cleaning")` twice returns the same object).

---

### TASK-016: Implement TranscriptService

**Description:** Implement `deep_notes_ai/services/transcript_service.py`.

**Must implement:**
- `TranscriptService.fetch(content_id: str) -> str`
- Error translation: wrap all `YouTubeTranscriptApi` exceptions in `TranscriptFetchError`.
- Join logic: `" ".join(snippet.text for snippet in fetched)` — identical to Cell 0.

**References:** `07_component_design.md` (Component 1), notebook Cell 0

**Acceptance criteria:**
- With a mock `YouTubeTranscriptApi` returning 3 snippets, `fetch()` returns their joined text.
- When the mock raises any exception, `fetch()` raises `TranscriptFetchError`.

---

### TASK-017: Implement MarkdownService

**Description:** Implement `deep_notes_ai/services/markdown_service.py`.

**Must implement:**
- `MarkdownService.build_document(content_title, hierarchy, content_store, summary) -> str`
- Internal `_render_node()` using identical logic to notebook Cell 18.

**References:** `07_component_design.md` (Component 11), notebook Cell 18

**Acceptance criteria:**
- All tests in `tests/unit/services/test_markdown_service.py` pass.
- A `TitleNode` at root level produces an `##` heading.
- A nested `TitleNode` produces `###`.
- A `ContentNode` with `summary=False` uses `content_store[id].content`.
- A `ContentNode` with `summary=True` uses `content_store[id].summary`.
- Output ends with `\n`.

---

### TASK-018: Implement ContentService

**Description:** Implement `deep_notes_ai/services/content_service.py`.

**Must implement:**
- `ContentService.__init__(llm_chain, partition_service, validation_service, retry_service, initial_partitions, fallback_partitions)`
- `ContentService.generate(transcript_text, payload, nodes_content) -> dict[str, ContentStoreItem]`
- Partition → temp-ID map → invoke → validate → store, with fallback on `BatchCountMismatchError`.

**References:** `07_component_design.md` (Component 9), `09_error_handling.md`, notebook Cell 12

**Acceptance criteria:**
- All tests in `tests/unit/services/test_content_service.py` pass.
- After `generate()`, returned dict has `.content` populated for all UUIDs in payload.
- On `BatchCountMismatchError`, service retries with `fallback_partitions`.
- On `RetryExhaustedError`, raises `ContentGenerationError`.

---

### TASK-019: Implement SummaryService

**Description:** Implement `deep_notes_ai/services/summary_service.py`.

**Identical pattern to `ContentService` except:**
- Input to LLM is `list[StructuredContentPayload]` using `nodes_content[id].content`.
- Output populates `nodes_content[id].summary`.

**References:** `07_component_design.md` (Component 10), notebook Cell 15

**Acceptance criteria:**
- All tests in `tests/unit/services/test_summary_service.py` pass.
- After `generate()`, returned dict has `.summary` populated for all UUIDs.
- On `BatchCountMismatchError`, retries with fallback partitions.

---

### TASK-020: Create Service Unit Test Suite

**Description:** Write all service unit tests.

**Files to create:**
- `tests/unit/services/test_validation_service.py`
- `tests/unit/services/test_retry_service.py`
- `tests/unit/services/test_partition_service.py`
- `tests/unit/services/test_persistence_service.py`
- `tests/unit/services/test_content_service.py`
- `tests/unit/services/test_summary_service.py`
- `tests/unit/services/test_markdown_service.py`

**Must include all tests listed in `12_testing_strategy.md` under "Service Unit Tests".**

**Acceptance criteria:**
- `uv run pytest tests/unit/services/ -v` passes with 0 failures.

---

## Phase 3 — LangGraph Pipeline

---

### TASK-021: Define PipelineState

**Description:** Implement `deep_notes_ai/langgraph_pipeline/state.py`.

**Must define `PipelineState(TypedDict, total=False)` with all fields documented in `06_state_design.md`.**

**References:** `06_state_design.md`

**Acceptance criteria:**
- `from deep_notes_ai.langgraph_pipeline.state import PipelineState` succeeds.
- `PipelineState` is a subclass of `dict` (TypedDict).
- All fields listed in `06_state_design.md` are present with correct types.

---

### TASK-022: Implement extract_transcript Node

**Description:** Implement `deep_notes_ai/langgraph_pipeline/nodes/extract_transcript.py`.

**Must implement:**
- `extract_transcript(state: PipelineState) -> dict`
- Reads `state["content_id"]`.
- Calls `TranscriptService.fetch()`.
- Returns `{"raw_content": ...}`.

**References:** `05_langgraph_design.md` (Node 1), notebook Cell 0

**Acceptance criteria:**
- With mocked `TranscriptService`, returns `{"raw_content": "..."}`.
- On `TranscriptFetchError`, propagates the exception.

---

### TASK-023: Implement clean_transcript Node

**Description:** Implement `deep_notes_ai/langgraph_pipeline/nodes/clean_transcript.py`.

**Must implement:**
- `clean_transcript(state: PipelineState) -> dict`
- Reads `state["raw_content"]`.
- Invokes cleaning LangChain chain.
- Returns `{"cleaned_content": ...}`.

**References:** `05_langgraph_design.md` (Node 2), notebook Cell 2

**Acceptance criteria:**
- With mocked LLM chain, returns `{"cleaned_content": "- First point\n- Second point"}`.
- LLM failure raises `LLMCallError`.

---

### TASK-024: Implement number_transcript Node

**Description:** Implement `deep_notes_ai/langgraph_pipeline/nodes/number_transcript.py`.

**Must implement:**
- `number_transcript(state: PipelineState) -> dict`
- Reads `state["cleaned_content"]` and `state["output_dir"]`.
- Calls `algorithms.clean_bullet_output()`.
- Calls `algorithms.load_numbered_points_from_text()`.
- Calls `PersistenceService.save_text()`.
- Returns `{"content_points", "content_points_path", "content_points_list"}`.

**References:** `05_langgraph_design.md` (Node 3), notebook Cells 3, 4

**Acceptance criteria:**
- Returns correct `content_points` for sample input.
- `content_points_list` is correctly parsed list.
- File is saved at `output_dir / content_id / "transcript_numbered.md"`.

---

### TASK-025: Implement generate_hierarchy Node

**Description:** Implement `deep_notes_ai/langgraph_pipeline/nodes/generate_hierarchy.py`.

**Must implement:**
- `generate_hierarchy(state: PipelineState) -> dict`
- Reads `state["content_points"]`.
- Invokes hierarchy LangChain chain with structured output.
- Returns `{"raw_hierarchy": TranscriptHierarchy}`.

**References:** `05_langgraph_design.md` (Node 4), notebook Cell 7

**Acceptance criteria:**
- With mocked structured LLM chain returning valid `TranscriptHierarchy`, returns `{"raw_hierarchy": ...}`.

---

### TASK-026: Implement validate_hierarchy Node

**Description:** Implement `deep_notes_ai/langgraph_pipeline/nodes/validate_hierarchy.py`.

**Must implement:**
- `validate_hierarchy(state: PipelineState) -> dict`
- Reads `state["raw_hierarchy"]`.
- Recursively counts CONTENT nodes.
- Returns `{"hierarchy_valid": bool, "content_node_count": int}`.

**References:** `05_langgraph_design.md` (Node 5)

**Acceptance criteria:**
- Hierarchy with 3 CONTENT nodes returns `{"hierarchy_valid": True, "content_node_count": 3}`.
- Hierarchy with 0 CONTENT nodes returns `{"hierarchy_valid": False, "content_node_count": 0}`.

---

### TASK-027: Implement extract_content_nodes Node

**Description:** Implement `deep_notes_ai/langgraph_pipeline/nodes/extract_content_nodes.py`.

**Must implement:**
- `extract_content_nodes(state: PipelineState) -> dict`
- Reads `state["raw_hierarchy"]` and `state["content_points_list"]`.
- Calls `build_content_payloads()`.
- Returns `{"content_payload", "nodes_content", "nodes_hierarchy"}`.

**References:** `05_langgraph_design.md` (Node 6), notebook Cell 9

**Acceptance criteria:**
- Returns non-empty `content_payload` for a valid hierarchy.
- `nodes_content` keys are UUIDs.
- All `ContentStoreItem` values have empty `content` and `summary`.

---

### TASK-028: Implement generate_content Node

**Description:** Implement `deep_notes_ai/langgraph_pipeline/nodes/generate_content.py`.

**Must implement:**
- `generate_content(state: PipelineState) -> dict`
- Reads `state["content_points"]`, `state["content_payload"]`, `state["nodes_content"]`.
- Calls `ContentService.generate()`.
- Returns `{"nodes_content": updated_dict}`.

**References:** `05_langgraph_design.md` (Node 7), notebook Cells 12, 13

**Acceptance criteria:**
- With mocked `ContentService`, returns `{"nodes_content": ...}` with `.content` populated.

---

### TASK-029: Implement generate_summaries Node

**Description:** Implement `deep_notes_ai/langgraph_pipeline/nodes/generate_summaries.py`.

**Must implement:**
- `generate_summaries(state: PipelineState) -> dict`
- Reads `state["content_points"]`, `state["content_payload"]`, `state["nodes_content"]`.
- Calls `SummaryService.generate()`.
- Returns `{"nodes_content": updated_dict}`.

**References:** `05_langgraph_design.md` (Node 8), notebook Cells 15, 16

**Acceptance criteria:**
- With mocked `SummaryService`, returns `{"nodes_content": ...}` with `.summary` populated.

---

### TASK-030: Implement persist_artefacts Node

**Description:** Implement `deep_notes_ai/langgraph_pipeline/nodes/persist_artefacts.py`.

**Must implement:**
- `persist_artefacts(state: PipelineState) -> dict`
- Reads `state["nodes_hierarchy"]`, `state["nodes_content"]`, `state["output_dir"]`, `state["content_id"]`.
- Calls `PersistenceService.save_nodes_hierarchy()` and `PersistenceService.save_nodes_content()`.
- Returns `{"hierarchy_json_path", "content_json_path"}`.

**References:** `05_langgraph_design.md` (Node 9), notebook Cell 17

**Acceptance criteria:**
- Both files are created at correct paths.
- Both paths are returned in state dict.

---

### TASK-031: Implement render_markdown Node

**Description:** Implement `deep_notes_ai/langgraph_pipeline/nodes/render_markdown.py`.

**Must implement:**
- `render_markdown(state: PipelineState) -> dict`
- Reads `state["content_title"]`, `state["nodes_hierarchy"]`, `state["nodes_content"]`, `state["output_dir"]`, `state["content_id"]`.
- Calls `MarkdownService.build_document()` twice (content + summary).
- Calls `PersistenceService.save_markdown()` twice.
- Returns `{"content_md_path", "summary_md_path", "pipeline_complete": True}`.

**References:** `05_langgraph_design.md` (Node 10), notebook Cells 18, 19

**Acceptance criteria:**
- Both markdown files are created at correct paths.
- `pipeline_complete` is `True` in returned dict.

---

### TASK-032: Implement Graph Assembly

**Description:** Implement `deep_notes_ai/langgraph_pipeline/graph.py`.

**Must implement:**
- `build_graph(settings: Settings) -> CompiledGraph`
- Constructs `StateGraph(PipelineState)`.
- Adds all 10 processing nodes.
- Adds all unconditional edges.
- Adds conditional edge from `validate_hierarchy`.
- Adds `hierarchy_validation_failed` terminal error node.
- Attaches `MemorySaver` (when `settings.use_sqlite_checkpointer=False`) or `SqliteSaver`.
- Returns compiled graph.

**References:** `05_langgraph_design.md`, `06_state_design.md`

**Acceptance criteria:**
- `build_graph(settings)` completes without raising.
- `graph.get_graph().nodes` contains all expected node names.
- `graph.get_graph().draw_ascii()` shows correct flow from START to END.
- Integration test with all LLMs mocked passes (`test_langgraph_graph.py`).

---

## Phase 4 — Entry Point

---

### TASK-033: Implement main.py

**Description:** Implement `main.py` as the CLI entry point.

**CLI signature:**
```bash
python main.py --video-id <VIDEO_ID> --title <TRANSCRIPT_TITLE> [--output-dir <DIR>]
```

**Must implement:**
- Argument parsing using `argparse`.
- `Settings()` instantiation.
- `configure_logging()` call.
- `build_graph(settings)` call.
- Initial state construction.
- `graph.invoke(initial_state, config={"configurable": {"thread_id": content_id}})`.
- Print final output paths on success.
- Print error message on failure.

**References:** `04_project_structure.md`, `05_langgraph_design.md`

**Acceptance criteria:**
- `python main.py --help` displays help text.
- Running without `--video-id` prints usage error.

---

## Phase 5 — Integration Tests

---

### TASK-034: Create Integration Tests

**Description:** Write integration tests for the full pipeline and graph.

**Files to create:**
- `tests/integration/test_pipeline_flow.py`
- `tests/integration/test_langgraph_graph.py`
- `tests/fixtures/sample_numbered.md`
- `tests/fixtures/sample_hierarchy.json`
- `tests/fixtures/sample_nodes_hierarchy.json`
- `tests/fixtures/sample_nodes_content.json`

**Must include all tests listed in `12_testing_strategy.md` under "Integration Tests".**

**References:** `12_testing_strategy.md`

**Acceptance criteria:**
- `uv run pytest tests/integration/ -v` passes with 0 failures.
- Full pipeline test with all LLMs mocked completes without error.
- `pipeline_complete=True` in final state.
- Both output markdown files exist in `tmp_path`.

---

## Task Dependency Order

```
TASK-001 → TASK-002 → TASK-003 → TASK-004 → TASK-005
                                      ↓
TASK-006 → TASK-007 → TASK-008 → TASK-009
                                      ↓
TASK-010 → TASK-011 → TASK-012 → TASK-013 →
TASK-014 → TASK-015 → TASK-016 → TASK-017 →
TASK-018 → TASK-019 → TASK-020
                          ↓
TASK-021 → TASK-022 → TASK-023 → TASK-024 →
TASK-025 → TASK-026 → TASK-027 → TASK-028 →
TASK-029 → TASK-030 → TASK-031 → TASK-032
                          ↓
                      TASK-033 → TASK-034
```

---

## Acceptance Criteria Summary

A complete implementation is verified when:

1. `uv run pytest tests/unit/ -v` passes with 0 failures.
2. `uv run pytest tests/integration/ -v` passes with 0 failures.
3. `uv run pytest --cov=deep_notes_ai --cov-fail-under=85` passes.
4. `python main.py --help` succeeds.
5. `python -c "from deep_notes_ai.langgraph_pipeline.graph import build_graph; from deep_notes_ai.config.settings import Settings; g = build_graph(Settings(OPENAI_API_KEY='test'))"` succeeds.
6. The graph produces output files structurally equivalent to the notebook when run with the same video ID and real API keys.
