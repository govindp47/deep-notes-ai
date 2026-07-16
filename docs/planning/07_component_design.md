# 07 — Component Design

## Component Inventory

The system is decomposed into the following reusable components. Each component has a single responsibility and a narrow public interface.

---

## Component 1: TranscriptLoader

**Module:** `deep_notes_ai/services/transcript_service.py`

**Responsibility:** Fetch a raw YouTube transcript given a video ID.

**Interface:**
```python
class TranscriptService:
    def fetch(self, content_id: str) -> str:
        """
        Fetch and join all transcript snippets into a single string.
        
        Returns:
            Raw transcript as one long string.
            
        Raises:
            TranscriptFetchError: if the API call fails or returns no transcript.
        """
```

**Dependencies:** `YouTubeTranscriptApi` from `youtube_transcript_api`

**Design notes:**
- No caching. Caller is responsible for persisting the result.
- Error translation: wraps all API exceptions in `TranscriptFetchError`.
- Snippet joining: `" ".join(snippet.text for snippet in fetched)` — identical to notebook.

**Test strategy:** Inject a mock `YouTubeTranscriptApi` instance. Test success path and all failure modes.

---

## Component 2: LLMService

**Module:** `deep_notes_ai/services/llm_service.py`

**Responsibility:** Factory that constructs LLM client instances from configuration.

**Interface:**
```python
class LLMService:
    def get_chat_model(
        self,
        provider: str,           # "openai" | "nvidia"
        model: str,
        temperature: float = 0,
    ) -> BaseChatModel:
        ...

    def get_structured_model(
        self,
        provider: str,
        model: str,
        output_schema: type[BaseModel],
        temperature: float = 0,
    ) -> Runnable:
        ...
```

**Dependencies:** `langchain_openai.ChatOpenAI`, `langchain_nvidia_ai_endpoints.ChatNVIDIA`

**Design notes:**
- Reads API keys from `Settings` (injected via constructor, not from os.environ directly).
- `get_structured_model` chains `.with_structured_output(output_schema)`.
- Each call creates a new client instance (no global singleton).
- Provider string is case-insensitive.

**Test strategy:** Mock at the `BaseChatModel` level — do not test actual LLM calls in unit tests.

---

## Component 3: PromptService

**Module:** `deep_notes_ai/services/prompt_service.py`

**Responsibility:** Load prompt templates from files and return `ChatPromptTemplate` instances.

**Interface:**
```python
class PromptService:
    def __init__(self, prompts_dir: Path): ...

    def load(self, name: str) -> ChatPromptTemplate:
        """
        Load a prompt template by name.
        name maps to {prompts_dir}/{name}.txt
        """
```

**Dependencies:** `langchain_core.prompts.ChatPromptTemplate`

**Design notes:**
- Prompt files are plain text with `{VARIABLE}` placeholders.
- Templates are cached in memory after first load (use `functools.lru_cache` or a dict).
- Raises `PromptNotFoundError` if the file does not exist.

**Prompt names:**
- `"cleaning"` → `cleaning.txt`
- `"hierarchy"` → `hierarchy.txt`
- `"content"` → `content.txt`
- `"summary"` → `summary.txt`

**Test strategy:** Create a temp directory with stub prompt files. Assert correct template loading.

---

## Component 4: PartitionService

**Module:** `deep_notes_ai/services/partition_service.py`

**Responsibility:** Compute transcript partitions for batched LLM calls.

**Interface:**
```python
class PartitionService:
    def compute_last_points(
        self,
        transcript_text: str,
        n: int,
    ) -> list[int]:
        """
        Compute the last point number for each of n equal-length partitions.
        """

    def compute_ranges(
        self,
        last_points: list[int],
    ) -> list[tuple[int, int]]:
        """
        Convert [145, 287, 421] → [(1,145), (146,287), (288,421)]
        """
```

**Dependencies:** `domain/algorithms.py` (`equal_partition_last_points_from_text`, `build_partition_ranges`)

**Design notes:**
- Accepts transcript text directly (not a file path), making it fully testable without I/O.
- Validates `n > 0`.
- Returns empty list if transcript has no numbered points.

---

## Component 5: ValidationService

**Module:** `deep_notes_ai/services/validation_service.py`

**Responsibility:** Validate that an LLM batch response has the correct IDs.

**Interface:**
```python
class ValidationService:
    def validate_batch(
        self,
        response: StructuredContentBatch | ContentSummaryBatch,
        expected_ids: set[str],
        entity_name: str = "CONTENT node",
    ) -> None:
        """
        Raises:
            BatchCountMismatchError: if item count differs.
            DuplicateIdsError: if duplicate IDs found.
            IncorrectIdsError: if IDs don't match expected.
        """
```

**Custom exceptions:**
- `BatchCountMismatchError(expected: int, actual: int)`
- `DuplicateIdsError(duplicates: list[str])`
- `IncorrectIdsError(missing: list[str], unexpected: list[str])`

**Design notes:**
- Three distinct exception types allow callers to handle each failure mode differently.
- `BatchCountMismatchError` signals: repartition (don't retry).
- `DuplicateIdsError` / `IncorrectIdsError` signal: retry the same batch.

---

## Component 6: PersistenceService

**Module:** `deep_notes_ai/services/persistence_service.py`

**Responsibility:** All file I/O for the pipeline. Single point of access for reading and writing artefacts.

**Interface:**
```python
class PersistenceService:
    def __init__(self, base_dir: Path): ...

    def save_text(self, path: Path, text: str) -> None: ...
    def load_text(self, path: Path) -> str: ...
    def save_json(self, path: Path, obj: Any) -> None: ...
    def load_json(self, path: Path) -> Any: ...
    def save_nodes_hierarchy(self, path: Path, nodes: list[Node]) -> None: ...
    def save_nodes_content(self, path: Path, content: dict[str, ContentStoreItem]) -> None: ...
    def load_nodes_hierarchy(self, path: Path) -> list[Node]: ...
    def load_nodes_content(self, path: Path) -> dict[str, ContentStoreItem]: ...
    def save_markdown(self, path: Path, markdown: str) -> None: ...
```

**Design notes:**
- All paths are absolute.
- Creates parent directories if needed.
- All files read/written in UTF-8.
- `save_nodes_hierarchy` and `save_nodes_content` use `json_serializer` for dataclasses.
- `load_nodes_hierarchy` recursively reconstructs `TitleNode` / `ContentNode` from raw dict.
- `load_nodes_content` reconstructs `ContentStoreItem` objects.
- Raises `PersistenceError` on any I/O failure.

**Test strategy:** Use `tmp_path` fixture. Test round-trips for each save/load pair.

---

## Component 7: RetryService

**Module:** `deep_notes_ai/services/retry_service.py`

**Responsibility:** Generic retry loop for callable operations.

**Interface:**
```python
class RetryService:
    def __init__(self, max_retries: int): ...

    def invoke(
        self,
        fn: Callable[[], T],
        is_retryable: Callable[[Exception], bool],
    ) -> T:
        """
        Calls fn() up to max_retries times.
        
        If is_retryable(e) is False → re-raise immediately.
        If all retries exhausted → raise RetryExhaustedError.
        """
```

**Custom exceptions:**
- `RetryExhaustedError(attempts: int, last_error: Exception)`

**Design notes:**
- Pure Python — no `tenacity` dependency (the notebook imports it but doesn't use it).
- `is_retryable` is a predicate function injected by the caller, enabling flexible error classification.
- `fn` is a zero-argument callable (use `functools.partial` to bind arguments).

---

## Component 8: HierarchyService

**Module:** Embedded in `deep_notes_ai/domain/algorithms.py` (pure functions, no class).

**Responsibility:** Extract CONTENT nodes from a `TranscriptHierarchy` and build the UUID-keyed content store.

**Key functions:**
```python
def build_content_payloads(
    hierarchy: list[TopicNode],
    content_points_list: list[str],
) -> PayloadResult: ...

def _extract_content_nodes(
    node: TopicNode,
    path: tuple[str, ...] = (),
) -> ExtractionResult: ...
```

**Design notes:**
- These are pure recursive algorithms with no side effects.
- UUIDs are generated inside `_extract_content_nodes` — this is the single point of UUID creation.
- Gap filling (extending range to cover uncovered points) happens in `build_content_payloads`.

---

## Component 9: ContentService

**Module:** `deep_notes_ai/services/content_service.py`

**Responsibility:** Orchestrate batched structured-content generation across all transcript partitions.

**Interface:**
```python
class ContentService:
    def __init__(
        self,
        llm_chain: Runnable,             # prompt | structured_llm
        partition_service: PartitionService,
        validation_service: ValidationService,
        retry_service: RetryService,
        initial_partitions: int,
        fallback_partitions: int,
    ): ...

    def generate(
        self,
        transcript_text: str,
        payload: list[ContentPayload],
        nodes_content: dict[str, ContentStoreItem],
    ) -> dict[str, ContentStoreItem]:
        """
        Processes all partitions and returns the updated nodes_content dict.
        """
```

**Internal algorithm:**
1. Compute partition ranges for `initial_partitions`.
2. For each partition:
   a. Filter `payload` to items in range.
   b. Build temp-ID mapping (N1..Nk → real UUID).
   c. Build temp `ContentPayload` list with N-IDs.
   d. Call `retry_service.invoke(lambda: llm_chain.invoke(...), is_retryable)`.
   e. Call `validation_service.validate_batch(response, expected_ids)`.
   f. Map N-IDs back to real UUIDs, populate `nodes_content[uuid].content`.
3. If `BatchCountMismatchError`: restart entire process with `fallback_partitions`.
4. Return updated `nodes_content`.

**Design notes:**
- Does not mutate the passed `nodes_content` — creates and returns a new dict.
- The `llm_chain` is injected, allowing easy mocking in tests.

---

## Component 10: SummaryService

**Module:** `deep_notes_ai/services/summary_service.py`

**Responsibility:** Orchestrate batched revision-summary generation across all transcript partitions.

**Interface:**
```python
class SummaryService:
    def __init__(
        self,
        llm_chain: Runnable,
        partition_service: PartitionService,
        validation_service: ValidationService,
        retry_service: RetryService,
        initial_partitions: int,
        fallback_partitions: int,
    ): ...

    def generate(
        self,
        transcript_text: str,
        payload: list[ContentPayload],
        nodes_content: dict[str, ContentStoreItem],
    ) -> dict[str, ContentStoreItem]:
        """
        Processes all partitions and returns the updated nodes_content dict
        with .summary populated.
        """
```

**Internal algorithm:** Identical to `ContentService` except:
- Input payload items are `StructuredContentPayload` (uses `.content` from `nodes_content`).
- Populates `nodes_content[uuid].summary` (not `.content`).

---

## Component 11: MarkdownService

**Module:** `deep_notes_ai/services/markdown_service.py`

**Responsibility:** Render the complete markdown document from a `Node` hierarchy and content store.

**Interface:**
```python
class MarkdownService:
    def build_document(
        self,
        content_title: str,
        hierarchy: list[Node],
        content_store: dict[str, ContentStoreItem],
        summary: bool = False,
    ) -> str:
        """
        Returns the complete markdown string.
        """
```

**Internal algorithm:**
- Starts with `# {content_title}`.
- Calls `_render_node()` recursively at `heading_level=2`.
- `TitleNode` → `"#" * heading_level + " " + node.name`.
- `ContentNode` → looks up `content_store[node.id]`, appends `summary` or `content` based on flag.
- Strips trailing whitespace, adds final newline.

**Design notes:**
- Pure function — no I/O. The caller (`render_markdown` node) handles saving.
- Heading levels increment with nesting depth.

---

## Component Dependency Summary

```
TranscriptService
    ← YouTubeTranscriptApi

LLMService
    ← Settings
    ← langchain_openai, langchain_nvidia_ai_endpoints

PromptService
    ← prompts/*.txt files

PartitionService
    ← domain/algorithms.py

ValidationService
    ← domain/models.py (exception types)

PersistenceService
    ← domain/models.py
    ← domain/algorithms.py (json_serializer)

RetryService
    ← (no domain deps)

ContentService
    ← LLMService (injected chain)
    ← PartitionService
    ← ValidationService
    ← RetryService
    ← domain/models.py

SummaryService
    ← LLMService (injected chain)
    ← PartitionService
    ← ValidationService
    ← RetryService
    ← domain/models.py

MarkdownService
    ← domain/models.py
```
