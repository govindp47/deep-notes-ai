# 02 — Existing Pipeline Analysis

This document reverse-engineers the notebook `content_extraction.ipynb` as-is.
It describes execution order, every function, every object, every dependency, and every persistence point.

---

## Cell-by-Cell Execution Map

### Cell 0 — Transcript Extraction (`id: f11bcb9c`)

**Imports:** `YouTubeTranscriptApi` from `youtube_transcript_api`

**Logic:**
```python
content_id = "jGg_1h0qzaM"
ytt_api = YouTubeTranscriptApi()
fetched_transcript = ytt_api.fetch(content_id)
transcript = " ".join(snippet.text for snippet in fetched_transcript)
```

- Calls the YouTube Transcript API with a hardcoded video ID.
- Fetches a list of `FetchedTranscript` snippet objects (each has `.text` and `.start` / `.duration`).
- Joins all snippet texts with a single space to produce one long raw string.
- Assigns result to the global notebook variable `transcript`.
- Error is caught silently (bare `except`).

**Outputs (global variables):** `transcript: str`
**Persistence:** None

---

### Cell 1 — Cleaning Prompt Definition (`id: a9cd3a6a`)

**Logic:** Defines `prompt_template: str` — a multiline string.

**Prompt purpose:** Convert raw YouTube transcript into professional bullet-per-statement written English.

**Prompt rules (summary):**
- Remove filler words, speech artifacts, course navigation statements.
- Preserve every educational statement as a separate bullet (`-`).
- No headings, no hierarchy, no section grouping.
- No summarisation or compression.
- Preserve all code identifiers, examples, and reasoning chains.
- Output: one bullet per educational statement, in original order.

**Outputs (global variables):** `prompt_template: str`
**Persistence:** None

---

### Cell 2 — LLM Setup & Async Invocation (`id: e1502a01`)

**Imports:**
- `pathlib.Path`
- `dotenv.load_dotenv`
- `langchain_core.prompts.ChatPromptTemplate`
- `langchain_openai.ChatOpenAI`
- `langchain_nvidia_ai_endpoints.ChatNVIDIA`

**Logic:**
```python
load_dotenv()
gpt_client = ChatOpenAI(model="gpt-4o-mini", temperature=0)
deepseek_client = ChatNVIDIA(model="deepseek-ai/deepseek-v4-pro", ...)
prompt = ChatPromptTemplate.from_template(prompt_template)
chain = prompt | gpt_client

async def structureTranscript():
    response = await chain.ainvoke({
        "RAW_TRANSCRIPT": transcript[(len(transcript)//6)*5:]
    })
    structured_notes = response.content
    Path("yt_cleaned_gpt54omini_1_6.md").write_text(structured_notes, encoding="utf-8")

await structureTranscript()
```

**Notable facts:**
- Only the **last 1/6th** of the transcript is processed in this cell (exploratory slicing).
- The full transcript processing happens by running this cell multiple times with different slices, resulting in multiple partial output files (e.g. `_1.md`, `_2.md`, ..., `_6.md`).
- The DeepSeek client is defined but not used in this cell.
- The final combined output is `yt_cleaned_gpt54omini_1.md` (assembled manually from the slice files, implied by cell 4).

**Outputs (files):** `yt_cleaned_gpt54omini_1_6.md` (one slice per run)
**Global variables written:** None (writes to file directly)

---

### Cell 3 — Point Numbering Function (`id: b47adbba`)

**Logic:** Defines `clean_bullet_output(text: str) -> str`

**Algorithm:**
1. Normalise line endings.
2. For each line:
   - If it matches a bullet pattern (`-`, `*`, `•`, numbered `1.`, `1)`, etc.) → start a new point, extract text after bullet symbol.
   - If it is a non-empty continuation line → append to current point with a space.
   - If it is a separator (`---`, `===`, etc.) → ignore.
3. Collapse multiple spaces within each point.
4. Number all points sequentially: `1. ...\n2. ...\n...`

**Regex patterns:**
- `bullet_pattern`: matches lines starting with `-`, `*`, `•`, `●`, `○`, `◦`, `▪`, `▸`, `►`, `▶`, `▫`, or `\d+[.)]`
- `separator_pattern`: matches lines of 5+ repetitions of `-`, `=`, `*`, `_`, `~`

**Returns:** numbered transcript as a single newline-separated string.

**Outputs (global variables):** function definition only
**Persistence:** None

---

### Cell 4 — Apply Numbering (`id: d680cc94`)

**Logic:**
```python
input_file = Path("yt_cleaned_gpt54omini_1.md")
output_file = Path("yt_cleaned_gpt54omini_1_numbered.md")
text = input_file.read_text(encoding="utf-8")
cleaned = clean_bullet_output(text)
output_file.write_text(cleaned, encoding="utf-8")
```

**Reads:** `yt_cleaned_gpt54omini_1.md`
**Writes:** `yt_cleaned_gpt54omini_1_numbered.md`
**Global variables written:** None (pure file transformation)

---

### Cell 5 — Hierarchy Pydantic Models (`id: cfd439dc`)

**Imports:** `pydantic.BaseModel`, `pydantic.Field`, `typing.List`

**Models defined:**

```python
class TopicNode(BaseModel):
    name: str         # "CONTENT" or a topic title
    start_point: int  # inclusive start transcript point
    end_point: int    # inclusive end transcript point
    children: List["TopicNode"]  # recursive

TopicNode.model_rebuild()  # required for self-referential model

class TranscriptHierarchy(BaseModel):
    hierarchy: List[TopicNode]  # top-level nodes
```

**Key design decisions:**
- `name == "CONTENT"` is the sentinel that marks a leaf content node.
- `start_point` / `end_point` are immutable references into the numbered transcript.
- `children` is empty on CONTENT nodes by definition.

**Outputs (global variables):** `TopicNode`, `TranscriptHierarchy` classes
**Persistence:** None

---

### Cell 6 — Hierarchy Prompt Definition (`id: 26aa7361`)

**Logic:** Defines `topics_prompt: str`

**Prompt purpose:** Discover the logical hierarchical structure already present in the numbered transcript.

**Prompt rules (summary):**
- Role: expert educational content architect.
- Input: numbered transcript inside `<CLEANED_NUMBERED_TRANSCRIPT_CONTENT>` tags.
- Output: `TranscriptHierarchy` structured JSON.
- Rules: preserve transcript order, never modify point numbers, create CONTENT leaf nodes for atomic regions, allow overlapping ranges, fill entire transcript, prefer deepest meaningful hierarchy.
- Template variable: `{CLEANED_NUMBERED_TRANSCRIPT}`

**Outputs (global variables):** `topics_prompt: str`
**Persistence:** None

---

### Cell 7 — Hierarchy LLM Invocation (`id: c1834e55`)

**Logic:**
```python
structured_llm = ChatOpenAI(model="gpt-5-mini", temperature=0
    ).with_structured_output(TranscriptHierarchy)
prompt = ChatPromptTemplate.from_template(topics_prompt)
file = Path("yt_cleaned_gpt54omini_1_numbered.md")
cleaned_content = file.read_text(encoding="utf-8")
chain = prompt | structured_llm
response = chain.invoke({"CLEANED_NUMBERED_TRANSCRIPT": cleaned_content})
output_path = Path("transcript_hierarchy_5mini_2.json")
with output_path.open("w", encoding="utf-8") as f:
    json.dump(response.model_dump(), f, indent=4, ensure_ascii=False)
```

**Reads:** `yt_cleaned_gpt54omini_1_numbered.md`
**LLM call:** 1 structured-output call to `gpt-5-mini`
**Writes:** `transcript_hierarchy_5mini_2.json`
**Returns:** `TranscriptHierarchy` Pydantic model (also stored in `response`)

---

### Cell 8 — Core Data Model & Utility Functions (`id: 3dfa2492`)

**Imports:**
- Standard: `json`, `math`, `re`, `dataclasses`, `pathlib`, `typing`, `uuid`, `itertools`

**Dataclasses defined:**

| Class | Fields | Purpose |
|-------|--------|---------|
| `ContentStoreItem` | `content: str`, `summary: str` | Stores generated markdown and summary for one CONTENT node |
| `ContentNode` | `type: Literal["content"]`, `id: str` | Lightweight leaf node in final hierarchy |
| `TitleNode` | `type: Literal["topic"]`, `name: str`, `subtopics: list[Node]` | Lightweight topic node in final hierarchy |
| `ContentExtraction` | `id`, `hierarchy_path`, `starting_point`, `ending_point` | Intermediate extraction result for one CONTENT node |
| `ExtractionResult` | `extracted: list[ContentExtraction]`, `metadata: dict`, `node: Node` | Return type of `_extract_content_nodes()` |
| `ContentPayload` | `id`, `hierarchy_path`, `range`, `content_points_list` | Input payload sent to the content-structuring LLM |
| `StructuredContentPayload` | `id`, `hierarchy_path`, `structured_content` | Input payload sent to the summary LLM |
| `PayloadResult` | `payload`, `metadata`, `nodes` | Return type of `build_content_payloads()` |

**Type alias:**
```python
Node = TitleNode | ContentNode
```

**Utility functions:**

#### `json_serializer(obj)`
- Custom JSON encoder default.
- Handles dataclasses via `dataclasses.asdict()`.

#### `load_json(path)` → `dict`
- Opens file, returns `json.load()`.

#### `save_json(obj, path)` → `None`
- Opens file, writes `json.dump()` with indent=4.

#### `load_numbered_points(file) → List[str]`
- Reads a numbered transcript file.
- Parses every `N. text` line using regex `^\s*(\d+)\.\s+(.*)$`.
- Validates numbering is exactly `1..N`.
- Returns 0-indexed list (index 0 → point 1).
- Raises `AssertionError` if numbering is not continuous.

#### `equal_partition_last_points(file, n) → List[int]`
- Computes `n` partition boundaries by character position.
- For each partition `1..n`: finds the last point number whose character position ≤ `target_position = ceil(total_length * part / n)`.
- Forces `boundaries[-1]` to equal the last point number.
- Returns list of last-point-numbers (e.g. `[211, 366, 492, 624]` for n=4).

#### `build_partition_ranges(last_points) → list[tuple[int,int]]`
- Converts `[145, 287, 421]` → `[(1,145), (146,287), (288,421)]`.
- Uses `itertools.pairwise` for adjacent pairs.

#### `_extract_content_nodes(node, path=()) → ExtractionResult`
- Recursively traverses a `TopicNode` hierarchy.
- When `node.name == "CONTENT"`:
  - Generates a new UUID.
  - Returns `ExtractionResult` with a single `ContentExtraction`, a `ContentStoreItem` with empty strings, and a `ContentNode`.
- Otherwise:
  - Appends `node.name` to `current_path`.
  - Recursively processes all children.
  - Returns merged `ExtractionResult` and a `TitleNode`.

#### `build_content_payloads(hierarchy, content_points_list) → PayloadResult`
- Calls `_extract_content_nodes()` for each top-level `TopicNode`.
- Merges all `ContentExtraction` results in order.
- For each extraction, expands range to fill any uncovered gap (`previous_end + 1 < start`).
- Builds `ContentPayload` for each extraction, slicing `content_points_list` to include the actual transcript lines.
- Returns `PayloadResult`.

#### `filter_payload_by_range(payload, start_point, end_point) → list[ContentPayload]`
- Returns only items whose `range[1]` (end point) falls within `[start_point, end_point]`.

**Outputs (global variables):** all classes and functions above
**Persistence:** None

---

### Cell 9 — Load & Build Payloads (`id: 4b74693c`)

**Logic:**
```python
transcript_file = Path("yt_cleaned_gpt54omini_1_numbered.md")
hierarchy_file = Path("transcript_hierarchy_5mini_2.json")

numbered_points = load_numbered_points(transcript_file)
hierarchy_data = load_json(hierarchy_file)
hierarchy = TranscriptHierarchy.model_validate(hierarchy_data)
payload_data = build_content_payloads(hierarchy.hierarchy, numbered_points)

updated_hierarchy_nodes = payload_data.nodes    # list[Node]
nodes_content = payload_data.metadata           # dict[str, ContentStoreItem]
payload = payload_data.payload                  # list[ContentPayload]
```

**Reads:** both intermediate files
**Global variables written:** `numbered_points`, `hierarchy_data`, `hierarchy`, `payload_data`, `updated_hierarchy_nodes`, `nodes_content`, `payload`

---

### Cell 10 — Batch Output Pydantic Models (`id: 9ce6f227`)

**Models defined:**

```python
class StructuredContent(BaseModel):
    id: str       # temporary N-identifier echoed back
    markdown: str # structured markdown for this CONTENT node

class StructuredContentBatch(BaseModel):
    items: list[StructuredContent]

class ContentSummary(BaseModel):
    id: str       # temporary N-identifier echoed back
    summary: str  # revision-note markdown for this CONTENT node

class ContentSummaryBatch(BaseModel):
    items: list[ContentSummary]
```

Also defines:
- `save_nodes_hierarchy(updated_nodes_hierarchy, output_file)` — serializes `list[Node]` to JSON using `json_serializer`.
- `save_nodes_content(nodes_content, output_file)` — serializes `dict[str, ContentStoreItem]` to JSON.
- `validate_batch_response(response, expected_ids, entity_name)` — validates LLM batch response:
  - Checks item count matches `len(expected_ids)`.
  - Checks no duplicate IDs.
  - Checks returned IDs exactly match expected IDs.
  - Raises `ValueError` with descriptive messages on failure.

---

### Cell 11 — Content Structuring Prompt (`id: a254ced6`)

**Logic:** Defines `content_nodes_prompt: str`

**Prompt purpose:** Transform numbered transcript points into well-structured markdown documentation for each CONTENT node, without summarising.

**Key rules:**
- Role: expert technical editor.
- Input: `list[ContentPayload]` serialised as JSON inside `<TOPIC_NODES_CONTENT>` tags.
- Output: `StructuredContentBatch` (one `StructuredContent` per input item).
- Every CONTENT node is independent — never merge across nodes.
- No markdown headings of any kind (`#`, `##`, etc.).
- No information invention or hallucination.
- Safe restructuring is encouraged (grouping, tables, blockquotes, bullets).
- Identifier fidelity: copy `id` field exactly from input to output.
- Template variable: `{NODES_CONTENT}`

---

### Cell 12 — Content Generation Orchestration (`id: 3d0c4d1a`)

**Constants:**
```python
MAX_RETRIES = 2
INITIAL_PARTITIONS = 4
FALLBACK_PARTITIONS = 6
```

**LLM setup:**
```python
structured_llm = ChatOpenAI(model="gpt-5-mini", temperature=0
    ).with_structured_output(StructuredContentBatch)
prompt = ChatPromptTemplate.from_template(content_nodes_prompt)
chain = prompt | structured_llm
```

**Function: `invoke_structured_batch(filtered_payload, retry_count=MAX_RETRIES) → StructuredContentBatch`**

```
for attempt in 1..retry_count:
    response = chain.invoke({"NODES_CONTENT": json.dumps(temp_payload)})
    try:
        validate_batch_response(response, expected_ids)
        return response
    except ValueError as e:
        if "Expected ... but LLM returned" in message:
            raise  # wrong count → caller handles repartitioning
        print retry message
raise RuntimeError after exhausting retries
```

**Function: `_process_partitions(partition_count) → None`**

```
partition_points = equal_partition_last_points(transcript_file, partition_count)
partition_ranges = build_partition_ranges(partition_points)
for start_point, end_point in partition_ranges:
    filtered_payload = filter_payload_by_range(payload, start_point, end_point)
    # Build temp_payload with N1..Nk IDs, build temp_to_real mapping
    response = invoke_structured_batch(temp_payload)
    for item in response.items:
        real_id = temp_to_real[item.id]
        nodes_content[real_id].content = item.markdown
```

**Function: `generate_structured_content() → None`**

```
try:
    _process_partitions(INITIAL_PARTITIONS)
except ValueError as e:
    if "Expected ... but LLM returned" in message:
        print("Retrying with FALLBACK_PARTITIONS...")
        _process_partitions(FALLBACK_PARTITIONS)
    else:
        raise
```

**Side effects:** Mutates `nodes_content[uuid].content` for all CONTENT nodes.

---

### Cell 13 — Execute Content Generation (`id: e8138e60`)

```python
generate_structured_content()
```

**Output (printed):**
```
Processing points 1 -> 211
Processing points 212 -> 366
Processing points 367 -> 492
Processing points 493 -> 624
```

---

### Cell 14 — Summary Prompt Definition (`id: 805e3ae5`)

**Logic:** Defines `nodes_summary_prompt: str`

**Prompt purpose:** Transform structured markdown for each CONTENT node into dense revision notes optimised for memory reconstruction.

**Key rules:**
- Role: expert technical summariser.
- Input: `list[StructuredContentPayload]` serialised as JSON inside `<TOPIC_NODES_CONTENT>` tags.
- Output: `ContentSummaryBatch` (one `ContentSummary` per input item).
- Classify information into four levels: Critical, Important, Supporting, Discardable.
- Remove Discardable aggressively.
- Preserve all implementation knowledge, APIs, identifiers, workflows.
- No headings of any kind.
- No hallucination.
- Target: concise handwritten engineering revision notes.
- Template variable: `{NODES_CONTENT}`

---

### Cell 15 — Summary Generation Orchestration (`id: 8171e347`)

**Constants:**
```python
MAX_RETRIES = 2
INITIAL_SUMMARY_PARTITIONS = 4
FALLBACK_SUMMARY_PARTITIONS = 6
```

**LLM setup:**
```python
node_summary_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0
    ).with_structured_output(ContentSummaryBatch)
summary_prompt = ChatPromptTemplate.from_template(nodes_summary_prompt)
summary_chain = summary_prompt | node_summary_llm
```

**Function: `invoke_summary_batch(summary_input, retry_count=MAX_RETRIES) → ContentSummaryBatch`**

Same structure as `invoke_structured_batch`. Uses `summary_chain`. Mutates nothing — returns response.

**Function: `_process_summary_partitions(partition_count) → None`**

```
partition_points = equal_partition_last_points(transcript_file, partition_count)
partition_ranges = build_partition_ranges(partition_points)
for start_point, end_point in partition_ranges:
    filtered_payload = filter_payload_by_range(payload, start_point, end_point)
    # Build summary_input: StructuredContentPayload items using nodes_content[id].content
    # Build temp N-ID mapping
    response = invoke_summary_batch(summary_input)
    for item in response.items:
        real_id = temp_to_real[item.id]
        nodes_content[real_id].summary = item.summary
```

**Function: `generate_summaries() → None`**

Same structure as `generate_structured_content`. Uses `INITIAL_SUMMARY_PARTITIONS` / `FALLBACK_SUMMARY_PARTITIONS`.

**Side effects:** Mutates `nodes_content[uuid].summary` for all CONTENT nodes.

---

### Cell 16 — Execute Summary Generation (`id: 235a3fd2`)

```python
generate_summaries()
```

---

### Cell 17 — Persist Hierarchy and Content (`id: f71480ff`)

```python
save_nodes_hierarchy(updated_hierarchy_nodes, Path("nodes_hierarchy.json"))
save_nodes_content(nodes_content, Path("nodes_content2.json"))
```

**Writes:**
- `nodes_hierarchy.json` — serialised `list[Node]`
- `nodes_content2.json` — serialised `dict[str, ContentStoreItem]`

---

### Cell 18 — Markdown Renderer & Loaders (`id: 28afcc87`)

**Constants:**
```python
TRANSCRIPT_TITLE = "LangGraph Course"
HIERARCHY_FILE = Path("nodes_hierarchy.json")
CONTENT_FILE = Path("nodes_content2.json")
CONTENT_OUTPUT = Path("course_content.md")
SUMMARY_OUTPUT = Path("course_summary.md")
```

**Functions:**

#### `_load_node(data: dict) → Node`
- Reconstructs `ContentNode` or `TitleNode` dataclasses from raw JSON `dict`.
- Raises `ValueError` for unknown `type` values.

#### `load_nodes_hierarchy(path) → list[Node]`
- Reads JSON file, calls `_load_node` for each root entry.

#### `load_nodes_content(path) → dict[str, ContentStoreItem]`
- Reads JSON file, reconstructs `ContentStoreItem` objects.

#### `_render_node(node, content_store, output, *, summary, heading_level)`
- Recursively builds markdown:
  - `TitleNode` → appends `"#" * heading_level + " " + node.name`, then recurses children at `heading_level + 1`.
  - `ContentNode` → looks up `content_store[node.id]`, appends `item.summary` or `item.content` depending on `summary` flag.

#### `build_markdown_document(*, content_title, hierarchy, content_store, summary=False) → str`
- Starts output with `# {content_title}`.
- Calls `_render_node` for each root node at `heading_level=2`.
- Joins with `"\n"`, strips trailing whitespace, adds final newline.

#### `save_markdown(markdown, path)`
- Writes to file with UTF-8 encoding.

---

### Cell 19 — Render and Save Markdown (`id: 70c4afd5`)

```python
hierarchy = load_nodes_hierarchy(HIERARCHY_FILE)
nodes_content = load_nodes_content(CONTENT_FILE)

content_md = build_markdown_document(
    content_title=TRANSCRIPT_TITLE,
    hierarchy=hierarchy,
    content_store=nodes_content,
    summary=False,
)
summary_md = build_markdown_document(
    content_title=TRANSCRIPT_TITLE,
    hierarchy=hierarchy,
    content_store=nodes_content,
    summary=True,
)

save_markdown(content_md, CONTENT_OUTPUT)
save_markdown(summary_md, SUMMARY_OUTPUT)
```

**Writes:** `course_content.md`, `course_summary.md`

---

## Global Variable Dependency Graph

```
transcript                  ← Cell 0
prompt_template             ← Cell 1
gpt_client, chain           ← Cell 2
(file: yt_cleaned_*.md)     ← Cell 2 writes
clean_bullet_output         ← Cell 3
(file: *_numbered.md)       ← Cell 4 writes
TopicNode, TranscriptHierarchy ← Cell 5
topics_prompt               ← Cell 6
(file: transcript_hierarchy.json) ← Cell 7 writes
All dataclasses + utilities ← Cell 8
numbered_points, hierarchy, payload, updated_hierarchy_nodes, nodes_content ← Cell 9
StructuredContent*, ContentSummary*, validate_batch_response, save_nodes_* ← Cell 10
content_nodes_prompt        ← Cell 11
generate_structured_content, _process_partitions, invoke_structured_batch ← Cell 12
[nodes_content[].content populated] ← Cell 13
nodes_summary_prompt        ← Cell 14
generate_summaries, _process_summary_partitions, invoke_summary_batch ← Cell 15
[nodes_content[].summary populated] ← Cell 16
(files: nodes_hierarchy.json, nodes_content.json) ← Cell 17 writes
_load_node, load_nodes_*, _render_node, build_markdown_document, save_markdown ← Cell 18
(files: course_content.md, course_summary.md) ← Cell 19 writes
```

---

## Intermediate Artefacts

| Artefact | Type | Created by | Consumed by |
|----------|------|-----------|-------------|
| `transcript` variable | `str` | Cell 0 | Cell 2 |
| `yt_cleaned_*.md` | File | Cell 2 | Cell 4 |
| `yt_cleaned_*_numbered.md` | File | Cell 4 | Cells 7, 9, 12, 15 |
| `transcript_hierarchy_*.json` | File | Cell 7 | Cell 9 |
| `numbered_points` variable | `list[str]` | Cell 9 | Cell 9 internally |
| `payload` variable | `list[ContentPayload]` | Cell 9 | Cells 12, 15 |
| `nodes_content` variable | `dict[str, ContentStoreItem]` | Cell 9 | Cells 12, 13, 15, 16, 17 |
| `updated_hierarchy_nodes` variable | `list[Node]` | Cell 9 | Cell 17 |
| `nodes_hierarchy.json` | File | Cell 17 | Cell 19 |
| `nodes_content.json` | File | Cell 17 | Cell 19 |
| `course_content.md` | File | Cell 19 | End user |
| `course_summary.md` | File | Cell 19 | End user |

---

## Known Limitations of the Notebook

1. **Hardcoded video ID.** `content_id = "jGg_1h0qzaM"` is fixed.
2. **Hardcoded file paths.** All intermediate files have hardcoded names.
3. **Hardcoded transcript title.** `TRANSCRIPT_TITLE = "LangGraph Course"`.
4. **Manual slicing for cleaning.** The cleaning LLM is called on one sixth of the transcript at a time, manually.
5. **Silent exception swallowing.** `except Exception as e:` in Cell 0 has no body.
6. **Global mutable state.** `nodes_content` is mutated across multiple cells.
7. **No resumption.** If the notebook fails mid-way, re-running from the middle requires manual state inspection.
8. **Mixed concerns.** Model definitions, prompt definitions, orchestration logic, and persistence are all interleaved in cells without clear separation.
9. **No validation of hierarchy before content generation.** If `TranscriptHierarchy` has no CONTENT nodes, subsequent steps silently do nothing.
10. **Temporary ID collision risk.** The `N1..Nk` mapping is rebuilt per partition but could collide if the same partition boundary is used twice.
