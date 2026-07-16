# 12 — Testing Strategy

## Design Principles

- **Test the contract, not the implementation.** Tests verify what a function produces given inputs, not how it gets there.
- **Isolate from external systems.** No unit test makes a real LLM call or file system write.
- **Domain logic is the highest-priority test target.** Pure algorithms in `domain/algorithms.py` are 100% unit-testable.
- **Services are tested with mocked dependencies.**
- **Integration tests verify component wiring with all LLMs mocked.**

---

## Test Pyramid

```
           ┌──────────────────┐
           │  Integration      │  ~5 tests — full graph, all LLMs mocked
           ├──────────────────┤
           │  Service Unit     │  ~40 tests — each service isolated
           ├──────────────────┤
           │  Domain Unit      │  ~50 tests — pure algorithms & models
           └──────────────────┘
```

---

## Test Framework

| Concern | Tool |
|---------|------|
| Test runner | `pytest` |
| Mock/stub | `pytest-mock` (`mocker`) + `unittest.mock` |
| File I/O in tests | `pytest` `tmp_path` fixture |
| Fixtures | `conftest.py` shared fixtures |
| Snapshot tests | `syrupy` (optional, for golden output comparison) |

---

## Domain Unit Tests

**Directory:** `tests/unit/domain/`

### `test_algorithms.py`

Tests all functions in `deep_notes_ai/domain/algorithms.py`.

#### `clean_bullet_output()`

```
test_single_bullet_becomes_numbered_point
test_multiple_bullets_become_numbered_sequence
test_dash_bullet_recognised
test_star_bullet_recognised
test_circle_bullet_recognised
test_numbered_dot_bullet_recognised
test_numbered_paren_bullet_recognised
test_continuation_line_appended_to_current_point
test_separator_line_ignored
test_empty_lines_ignored
test_multiple_spaces_collapsed
test_empty_input_returns_empty
test_bullets_without_text_become_empty_points
```

**Example:**
```python
def test_multiple_bullets_become_numbered_sequence():
    text = "- First point\n- Second point\n- Third point"
    result = clean_bullet_output(text)
    assert result == "1. First point\n2. Second point\n3. Third point"
```

---

#### `load_numbered_points_from_text()`

```
test_correctly_numbered_input_returns_list
test_single_point
test_numbering_must_start_at_one
test_gap_in_numbering_raises_algorithm_error
test_duplicate_number_raises_algorithm_error
test_empty_text_returns_empty_list
```

---

#### `equal_partition_last_points_from_text()`

```
test_one_partition_returns_last_point
test_four_partitions_returns_four_boundary_points
test_last_point_always_equals_total_point_count
test_single_point_transcript
test_n_greater_than_point_count_returns_all_points
```

---

#### `build_partition_ranges()`

```
test_single_last_point
test_multiple_last_points
test_ranges_are_contiguous
test_first_range_starts_at_one
test_last_range_ends_at_max_point
```

---

#### `build_content_payloads()`

```
test_single_content_node_produces_single_payload
test_two_content_nodes_produce_two_payloads
test_hierarchy_path_preserved_in_payload
test_content_points_list_sliced_correctly
test_gap_filling_extends_range_to_cover_uncovered_points
test_uuids_are_unique_per_content_node
test_content_store_initialised_with_empty_strings
test_metadata_dict_keyed_by_uuid
test_nodes_hierarchy_mirrors_input_hierarchy
```

---

#### `filter_payload_by_range()`

```
test_all_items_in_range
test_no_items_in_range
test_partial_filter
test_boundary_items_included
```

---

### `test_models.py`

Tests model construction and invariants.

```
test_content_store_item_default_empty_strings
test_content_node_type_literal
test_title_node_type_literal
test_topic_node_content_sentinel
test_transcript_hierarchy_model_validate_from_dict
test_structured_content_batch_item_count
test_content_summary_batch_item_count
```

---

## Service Unit Tests

**Directory:** `tests/unit/services/`

### `test_validation_service.py`

```
test_valid_batch_does_not_raise
test_count_mismatch_raises_batch_count_mismatch_error
test_duplicate_ids_raises_duplicate_ids_error
test_incorrect_ids_raises_incorrect_ids_error
test_correct_count_wrong_ids_raises_incorrect_ids_error
test_single_item_batch_valid
```

**All tests use stub `StructuredContentBatch` / `ContentSummaryBatch` objects — no LLM calls.**

---

### `test_partition_service.py`

```
test_compute_last_points_n_equals_one
test_compute_last_points_n_equals_four
test_compute_ranges_from_last_points
test_single_partition_range
```

---

### `test_persistence_service.py`

```
test_save_and_load_text_roundtrip
test_save_and_load_json_roundtrip
test_save_and_load_nodes_hierarchy_roundtrip
test_save_and_load_nodes_content_roundtrip
test_save_markdown_creates_file
test_load_text_missing_file_raises_persistence_error
test_parent_directories_created_automatically
```

**All tests use `tmp_path` fixture for real file I/O (acceptable in unit test because it has no external network calls).**

---

### `test_retry_service.py`

```
test_succeeds_on_first_attempt
test_retries_on_retryable_error
test_succeeds_on_second_attempt_after_failure
test_raises_retry_exhausted_after_max_retries
test_non_retryable_error_propagates_immediately
test_correct_number_of_attempts
```

**Using `unittest.mock.Mock` for the callable and predicates.**

---

### `test_content_service.py`

```
test_successful_single_partition
test_successful_four_partitions
test_repartition_on_count_mismatch
test_retry_on_duplicate_ids
test_retry_on_incorrect_ids
test_retry_exhausted_raises_content_generation_error
test_temp_id_mapping_is_correct
test_uuid_restored_from_temp_id
test_nodes_content_content_field_populated
test_nodes_content_returned_with_all_uuids
```

**LLM chain is mocked as a `Mock` with configurable return values.**

Example:
```python
def test_successful_single_partition(mock_llm_chain, sample_payload, empty_nodes_content):
    mock_llm_chain.invoke.return_value = StructuredContentBatch(
        items=[StructuredContent(id="N1", markdown="## Topic\n\n- Point 1")]
    )
    service = ContentService(llm_chain=mock_llm_chain, ...)
    result = service.generate(
        transcript_text="1. Point 1",
        payload=sample_payload,
        nodes_content=empty_nodes_content,
    )
    assert result[UUID_1].content == "## Topic\n\n- Point 1"
```

---

### `test_summary_service.py`

Mirrors `test_content_service.py` with `SummaryService` and `ContentSummaryBatch`.

```
test_successful_single_partition_summary
test_repartition_on_count_mismatch_summary
test_nodes_content_summary_field_populated
# ... same pattern as content service
```

---

### `test_markdown_service.py`

```
test_single_content_node
test_title_node_with_child_content_node
test_nested_title_nodes_increment_heading_level
test_summary_flag_uses_summary_field
test_content_flag_uses_content_field
test_content_title_becomes_h1
test_empty_content_omitted
test_document_ends_with_newline
test_multi_root_nodes
```

**No I/O, no LLM. Uses in-memory `TitleNode`/`ContentNode` objects and dict.**

---

## Integration Tests

**Directory:** `tests/integration/`

### `test_pipeline_flow.py`

Tests the full graph with all LLMs mocked. Verifies state transitions.

**Setup:** Each LLM chain is replaced with a `Mock` that returns valid pre-built responses.

**Tests:**

```
test_full_pipeline_success_path
    Given: valid content_id, mocked transcript, mocked all LLM responses
    When: graph is invoked
    Then: final state has pipeline_complete=True, all output files exist

test_invalid_hierarchy_routes_to_error_node
    Given: hierarchy LLM returns a hierarchy with zero CONTENT nodes
    When: graph is invoked
    Then: validate_hierarchy sets hierarchy_valid=False, pipeline_complete=False, no downstream nodes run

test_content_generation_repartitions_on_count_mismatch
    Given: content LLM returns wrong item count on first call, correct on second
    When: graph is invoked
    Then: pipeline completes successfully with fallback_partitions

test_pipeline_state_has_all_expected_fields_after_success
    Then: all fields in PipelineState are populated
```

---

### `test_langgraph_graph.py`

Smoke test that verifies the graph compiles and runs without errors.

```
test_graph_compiles_without_errors
test_graph_has_correct_number_of_nodes
test_graph_start_and_end_nodes_connected
test_conditional_edge_exists_from_validate_hierarchy
```

---

## Test Fixtures

**File:** `tests/conftest.py`

```python
@pytest.fixture
def sample_content_points_text():
    return "1. TypedDict defines state shape.\n2. State is passed to nodes.\n3. Nodes update state."

@pytest.fixture
def sample_topic_node():
    return TopicNode(
        name="TypedDict",
        start_point=1,
        end_point=3,
        children=[
            TopicNode(name="CONTENT", start_point=1, end_point=3, children=[])
        ]
    )

@pytest.fixture
def sample_transcript_hierarchy(sample_topic_node):
    return TranscriptHierarchy(hierarchy=[sample_topic_node])

@pytest.fixture
def sample_content_store_item():
    return ContentStoreItem(content="## TypedDict\n\n- Defines state.", summary="TypedDict: defines state.")

@pytest.fixture
def sample_content_payload():
    return ContentPayload(
        id="test-uuid-1",
        hierarchy_path=["TypedDict"],
        range=(1, 3),
        content_points_list=["1. TypedDict...", "2. State...", "3. Nodes..."],
    )
```

---

## Test Data Files

**Directory:** `tests/fixtures/`

| File | Content |
|------|---------|
| `sample_numbered.md` | 10-line numbered transcript |
| `sample_hierarchy.json` | `TranscriptHierarchy` with 3 CONTENT nodes |
| `sample_nodes_hierarchy.json` | `list[Node]` with 2 topics, 3 CONTENT nodes |
| `sample_nodes_content.json` | `dict` with 3 UUIDs, each with content and summary |

---

## Coverage Targets

| Layer | Target |
|-------|--------|
| `domain/algorithms.py` | 100% |
| `domain/models.py` | 90%+ |
| `services/validation_service.py` | 100% |
| `services/partition_service.py` | 100% |
| `services/retry_service.py` | 100% |
| `services/content_service.py` | 90%+ |
| `services/summary_service.py` | 90%+ |
| `services/persistence_service.py` | 90%+ |
| `services/markdown_service.py` | 100% |
| `langgraph_pipeline/state.py` | N/A (TypedDict) |
| `langgraph_pipeline/nodes/*.py` | 80%+ via integration tests |

---

## Running Tests

```bash
# Run all tests
uv run pytest

# Run only domain unit tests
uv run pytest tests/unit/domain/

# Run with coverage
uv run pytest --cov=deep_notes_ai --cov-report=term-missing

# Run specific test file
uv run pytest tests/unit/services/test_validation_service.py -v

# Run integration tests
uv run pytest tests/integration/ -v
```
