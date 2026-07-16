# 08 — Data Models

## Overview

All data models live in `deep_notes_ai/domain/models.py`.

Models are divided into three categories:
1. **Dataclasses** — lightweight data containers, serialisable with `dataclasses.asdict()`.
2. **Pydantic models** — used for LLM structured output and external data validation.
3. **TypedDict** — used for LangGraph state.

---

## Dataclasses

### `ContentStoreItem`

```python
@dataclass(slots=True)
class ContentStoreItem:
    content: str = ""
    summary: str = ""
```

**Purpose:** Holds the generated structured markdown and revision summary for a single CONTENT leaf node.

**Ownership:** Created by `_extract_content_nodes()` with empty strings. Content populated by `ContentService`. Summary populated by `SummaryService`.

**Who reads it:**
- `ContentService` (reads `.content` when building summary input)
- `SummaryService` (reads `.content` to generate summaries)
- `PersistenceService` (serialises both fields to JSON)
- `MarkdownService` (reads `.content` or `.summary` based on `summary` flag)

**Lifecycle:**
1. Created empty by `_extract_content_nodes()`.
2. `.content` populated by `ContentService.generate()`.
3. `.summary` populated by `SummaryService.generate()`.
4. Persisted to `nodes_content.json`.
5. Loaded back from JSON by `PersistenceService.load_nodes_content()`.
6. Read by `MarkdownService.build_document()`.

**Mutability:** Mutable. Both fields are updated during pipeline execution.

---

### `ContentNode`

```python
@dataclass(slots=True)
class ContentNode:
    type: Literal["content"] = "content"
    id: str = ""
```

**Purpose:** Lightweight representation of a CONTENT leaf in the final node hierarchy. Carries only the UUID needed to look up the corresponding `ContentStoreItem`.

**Ownership:** Created by `_extract_content_nodes()` when `node.name == "CONTENT"`.

**Who reads it:**
- `MarkdownService._render_node()` — looks up `content_store[node.id]`.
- `PersistenceService` — serialises to JSON via `asdict()`.

**Lifecycle:** Created once during extraction. Never mutated.

**Mutability:** Immutable after creation.

---

### `TitleNode`

```python
@dataclass(slots=True)
class TitleNode:
    type: Literal["topic"] = "topic"
    name: str = ""
    subtopics: list["Node"] = field(default_factory=list)
```

**Purpose:** Lightweight representation of a topic node in the final hierarchy. Carries the topic name and ordered list of child nodes.

**Ownership:** Created by `_extract_content_nodes()` when `node.name != "CONTENT"`.

**Who reads it:**
- `MarkdownService._render_node()` — renders heading, then recurses children.
- `PersistenceService` — serialises to JSON via `asdict()`.

**Lifecycle:** Created once during extraction. Never mutated.

**Mutability:** Immutable after creation (though `subtopics` is a list, it is not appended to after construction).

---

### `Node` (Type Alias)

```python
Node = TitleNode | ContentNode
```

**Purpose:** Union type representing any node in the lightweight hierarchy. Used throughout as the element type of `list[Node]`.

---

### `ContentExtraction`

```python
@dataclass(slots=True)
class ContentExtraction:
    id: str
    hierarchy_path: list[str]
    starting_point: int
    ending_point: int
```

**Purpose:** Intermediate result produced during CONTENT node traversal. Carries enough information to build a `ContentPayload` after the traversal completes.

**Ownership:** Created by `_extract_content_nodes()` for each CONTENT leaf.

**Who reads it:**
- `build_content_payloads()` — uses all fields to construct `ContentPayload`.

**Lifecycle:** Exists only inside `build_content_payloads()`. Never stored in state or persisted.

**Mutability:** Immutable after creation.

---

### `ExtractionResult`

```python
@dataclass(slots=True)
class ExtractionResult:
    extracted: list[ContentExtraction]
    metadata: dict[str, ContentStoreItem]
    node: Node
```

**Purpose:** Aggregated return value of `_extract_content_nodes()`. Packages the list of all CONTENT extractions found under a subtree, the UUID-to-ContentStoreItem map, and the corresponding lightweight `Node`.

**Ownership:** Created and consumed entirely within `build_content_payloads()`.

**Who reads it:**
- `build_content_payloads()` — merges `extracted` and `metadata` across all root nodes.

**Lifecycle:** Exists only during the recursive traversal. Never stored in state or persisted.

**Mutability:** Immutable after creation (though internal lists are built by accumulation during recursion).

---

### `ContentPayload`

```python
@dataclass(slots=True)
class ContentPayload:
    id: str
    hierarchy_path: list[str]
    range: tuple[int, int]
    content_points_list: list[str]
```

**Purpose:** The input data for one CONTENT node sent to the content-structuring LLM. Contains the UUID, the topic hierarchy path, the point range covered, and the actual transcript lines.

**Ownership:** Created by `build_content_payloads()`.

**Who reads it:**
- `ContentService` — serialises to JSON for LLM input.
- `SummaryService` — uses `.id` and `.range` to filter and build summary input.
- `filter_payload_by_range()` — filters on `.range[1]`.

**Lifecycle:**
1. Created by `build_content_payloads()` and stored in `state["content_payload"]`.
2. Read by `ContentService.generate()` and `SummaryService.generate()`.
3. Never mutated after creation.

**Mutability:** Immutable after creation.

**Note on `id`:** This carries the real UUID. When sent to the LLM, a temporary ID (N1, N2, ...) is substituted. The UUID is never exposed to the LLM.

---

### `StructuredContentPayload`

```python
@dataclass(slots=True)
class StructuredContentPayload:
    id: str
    hierarchy_path: list[str]
    structured_content: str
```

**Purpose:** The input data for one CONTENT node sent to the summary-generation LLM. Combines the UUID with the hierarchy path and the structured markdown (from `ContentStoreItem.content`).

**Ownership:** Created inside `SummaryService.generate()` from `ContentPayload` + `nodes_content`.

**Who reads it:**
- `SummaryService` — serialises to JSON for LLM input.

**Lifecycle:** Temporary. Created per partition call inside `SummaryService`. Not stored in state.

**Mutability:** Immutable after creation.

---

### `PayloadResult`

```python
@dataclass(slots=True)
class PayloadResult:
    payload: list[ContentPayload]
    metadata: dict[str, ContentStoreItem]
    nodes: list[Node]
```

**Purpose:** Return type of `build_content_payloads()`. Bundles all three outputs of the extraction phase.

**Ownership:** Created by `build_content_payloads()`.

**Who reads it:**
- `extract_content_nodes` LangGraph node — unpacks into three state fields.

**Lifecycle:** Created once by `build_content_payloads()`, immediately unpacked.

**Mutability:** Immutable after creation.

---

## Pydantic Models

### `TopicNode` (Pydantic)

```python
class TopicNode(BaseModel):
    name: str
    start_point: int
    end_point: int
    children: List["TopicNode"] = Field(default_factory=list)
```

**Purpose:** Represents one node in the LLM-generated transcript hierarchy. Used as the output schema for the hierarchy-generation LLM call.

**Ownership:** Validated from LLM structured output by LangChain's `.with_structured_output()`.

**Who reads it:**
- `validate_hierarchy` — counts CONTENT nodes recursively.
- `_extract_content_nodes()` — traverses the hierarchy.

**Lifecycle:** Created from LLM output. Stored in `state["raw_hierarchy"]`. Read-only after creation.

**Special cases:**
- `name == "CONTENT"` is the sentinel for a leaf node.
- `children` is always empty when `name == "CONTENT"`.
- `TopicNode.model_rebuild()` must be called after class definition (Pydantic requirement for self-referential models).

**Mutability:** Immutable (Pydantic default).

---

### `TranscriptHierarchy` (Pydantic)

```python
class TranscriptHierarchy(BaseModel):
    hierarchy: List[TopicNode]
```

**Purpose:** Top-level output schema for the hierarchy LLM call. Wraps the list of root `TopicNode` objects.

**Ownership:** Validated from LLM structured output.

**Who reads it:**
- `validate_hierarchy` — checks `hierarchy` for CONTENT nodes.
- `extract_content_nodes` — passes `hierarchy.hierarchy` to `build_content_payloads()`.
- `PersistenceService` — serialised via `.model_dump()` for JSON persistence.

**Lifecycle:** Created by LLM call. Stored in `state["raw_hierarchy"]`. Never mutated.

---

### `StructuredContent` (Pydantic)

```python
class StructuredContent(BaseModel):
    id: str
    markdown: str
```

**Purpose:** One item in the LLM's structured output during content generation. The `id` is a temporary N-identifier.

**Ownership:** Created by LangChain's structured output parsing from the content-generation LLM response.

**Who reads it:**
- `ContentService` — reads `.id` for reverse-mapping and `.markdown` for storage.

**Lifecycle:** Temporary. Created per LLM call. Not stored in state.

---

### `StructuredContentBatch` (Pydantic)

```python
class StructuredContentBatch(BaseModel):
    items: list[StructuredContent]
```

**Purpose:** Complete LLM response for one content-generation batch call.

**Who reads it:**
- `ValidationService.validate_batch()` — validates item count and IDs.
- `ContentService` — iterates `.items` to populate `nodes_content`.

**Lifecycle:** Temporary. Created per LLM call.

---

### `ContentSummary` (Pydantic)

```python
class ContentSummary(BaseModel):
    id: str
    summary: str
```

**Purpose:** One item in the LLM's structured output during summary generation.

**Ownership:** Created by LangChain's structured output parsing from the summary LLM response.

**Who reads it:**
- `SummaryService` — reads `.id` for reverse-mapping and `.summary` for storage.

**Lifecycle:** Temporary.

---

### `ContentSummaryBatch` (Pydantic)

```python
class ContentSummaryBatch(BaseModel):
    items: list[ContentSummary]
```

**Purpose:** Complete LLM response for one summary-generation batch call.

**Who reads it:**
- `ValidationService.validate_batch()`.
- `SummaryService`.

---

## LangGraph State TypedDict

### `PipelineState` (TypedDict)

Defined in `deep_notes_ai/langgraph_pipeline/state.py`.

See `06_state_design.md` for complete field definitions.

**Key properties:**
- `total=False` — all fields optional to allow partial state construction.
- Fields are only populated by the node that owns them.
- `nodes_content` is the only field updated by multiple nodes.

---

## Custom Exception Models

Defined in `deep_notes_ai/services/validation_service.py` (or a shared `exceptions.py`):

```python
class TranscriptFetchError(Exception): ...
class LLMCallError(Exception): ...
class PromptNotFoundError(Exception): ...
class PersistenceError(Exception): ...
class BatchCountMismatchError(Exception):
    expected: int
    actual: int
class DuplicateIdsError(Exception):
    duplicates: list[str]
class IncorrectIdsError(Exception):
    missing: list[str]
    unexpected: list[str]
class RetryExhaustedError(Exception):
    attempts: int
    last_error: Exception
class ContentGenerationError(Exception): ...
class SummaryGenerationError(Exception): ...
class AlgorithmError(Exception): ...
class HierarchyValidationError(Exception): ...
```

---

## Model Serialisation

| Model | Serialisation method | Notes |
|-------|---------------------|-------|
| `ContentStoreItem` | `dataclasses.asdict()` | Produces `{"content": str, "summary": str}` |
| `ContentNode` | `dataclasses.asdict()` | Produces `{"type": "content", "id": str}` |
| `TitleNode` | `dataclasses.asdict()` | Produces `{"type": "topic", "name": str, "subtopics": [...]}` |
| `TopicNode` | `.model_dump()` | Pydantic v2 method |
| `TranscriptHierarchy` | `.model_dump()` | Pydantic v2 method |
| `StructuredContentBatch` | N/A (ephemeral) | — |
| `ContentSummaryBatch` | N/A (ephemeral) | — |

---

## Model Deserialisation

| JSON shape | Deserialisation | Where |
|-----------|-----------------|-------|
| `{"hierarchy": [...]}` | `TranscriptHierarchy.model_validate(data)` | `generate_hierarchy` node |
| `[{"type": "topic"/"content", ...}]` | `_load_node(data)` recursively | `PersistenceService.load_nodes_hierarchy()` |
| `{"uuid": {"content": str, "summary": str}}` | Manual dict comprehension | `PersistenceService.load_nodes_content()` |
