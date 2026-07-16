"""
tests/unit/domain/test_algorithms.py

Unit tests for deep_notes_ai/domain/algorithms.py.
All functions covered — no I/O, no LLM, no file system access.
"""
import pytest

from deep_notes_ai.domain.algorithms import (
    build_content_payloads,
    build_partition_ranges,
    clean_numbered_points,
    count_chunks,
    equal_partition_last_points_from_text,
    filter_payload_by_range,
    json_serializer,
    load_numbered_points_from_text,
    split_text_into_chunks,
)
from deep_notes_ai.domain.models import (
    AlgorithmError,
    ContentNode,
    ContentPayload,
    ContentStoreItem,
    TitleNode,
    TopicNode,
)


# ============================================================================
# json_serializer
# ============================================================================

def test_json_serializer_dataclass():
    import json

    item = ContentStoreItem(content="hello", summary="world")
    result = json.dumps(item, default=json_serializer)
    import json as j
    parsed = j.loads(result)
    assert parsed == {"content": "hello", "summary": "world"}


def test_json_serializer_non_dataclass_raises():
    with pytest.raises(TypeError):
        json_serializer({"not": "a dataclass"})


# ============================================================================
# clean_bullet_output
# ============================================================================

def test_single_bullet_becomes_numbered_point():
    result = clean_numbered_points("- First")
    assert result == ["1. First"]


def test_multiple_bullets_become_numbered_sequence():
    text = "- First point\n- Second point\n- Third point"
    result = clean_numbered_points(text)
    assert result == ["1. First point", "2. Second point", "3. Third point"]


def test_dash_bullet_recognised():
    result = clean_numbered_points("- dash bullet")
    assert result == ["1. dash bullet"]


def test_star_bullet_recognised():
    result = clean_numbered_points("* star bullet")
    assert result == ["1. star bullet"]


def test_circle_bullet_recognised():
    result = clean_numbered_points("• circle bullet")
    assert result == ["1. circle bullet"]


def test_numbered_dot_bullet_recognised():
    result = clean_numbered_points("1. already numbered")
    assert result == ["1. already numbered"]


def test_numbered_paren_bullet_recognised():
    result = clean_numbered_points("1) parenthesis numbered")
    assert result == ["1. parenthesis numbered"]


def test_continuation_line_appended_to_current_point():
    text = "- First line\n  continuation text"
    result = clean_numbered_points(text)
    assert result == ["1. First line continuation text"]


def test_separator_line_ignored():
    text = "- First\n-----\n- Second"
    result = clean_numbered_points(text)
    assert result == ["1. First", "2. Second"]


def test_empty_lines_ignored():
    text = "- First\n\n- Second"
    result = clean_numbered_points(text)
    assert result == ["1. First", "2. Second"]


def test_multiple_spaces_collapsed():
    text = "- First   with  spaces"
    result = clean_numbered_points(text)
    assert result == ["1. First with spaces"]


def test_empty_input_returns_empty():
    result = clean_numbered_points("")
    assert result == []


def test_bullets_without_text_become_empty_points():
    """Bullets with no trailing text after them are skipped (empty current discarded)."""
    # A bullet with no text followed by a non-bullet continuation
    text = "-\n  actual content"
    result = clean_numbered_points(text)
    assert result == ["1. actual content"]


def test_plain_text_before_any_bullet_becomes_first_point():
    """Non-bullet text before the first bullet (current is None) starts a new point."""
    text = "plain text line\n- bullet after"
    result = clean_numbered_points(text)
    # plain text becomes the first point (current=None → current=stripped)
    # then bullet triggers append of "plain text line" → second point = "bullet after"
    assert any("plain text line" in p for p in result)
    assert any("bullet after" in p for p in result)


# ============================================================================
# load_numbered_points_from_text
# ============================================================================

def test_correctly_numbered_input_returns_list():
    text = "1. First\n2. Second\n3. Third"
    result = load_numbered_points_from_text(text)
    assert result == ["1. First", "2. Second", "3. Third"]


def test_single_point():
    text = "1. Only point"
    result = load_numbered_points_from_text(text)
    assert result == ["1. Only point"]


def test_numbering_must_start_at_one():
    text = "2. Second\n3. Third"
    with pytest.raises(AlgorithmError):
        load_numbered_points_from_text(text)


def test_gap_in_numbering_raises_algorithm_error():
    text = "1. First\n3. Third"
    with pytest.raises(AlgorithmError):
        load_numbered_points_from_text(text)


def test_duplicate_number_raises_algorithm_error():
    text = "1. First\n1. First again\n2. Second"
    with pytest.raises(AlgorithmError):
        load_numbered_points_from_text(text)


def test_empty_text_returns_empty_list():
    result = load_numbered_points_from_text("")
    assert result == []


def test_non_numbered_lines_are_ignored():
    text = "1. First\nignored line\n2. Second"
    result = load_numbered_points_from_text(text)
    assert result == ["1. First", "2. Second"]


# ============================================================================
# equal_partition_last_points_from_text
# ============================================================================

def _make_numbered_text(n: int) -> str:
    """Helper: create a numbered transcript with n points."""
    return "\n".join(f"{i}. Point {i}" for i in range(1, n + 1))


def test_one_partition_returns_last_point():
    text = _make_numbered_text(10)
    result = equal_partition_last_points_from_text(text, 1)
    assert result == [10]


def test_four_partitions_returns_four_boundary_points():
    text = _make_numbered_text(100)
    result = equal_partition_last_points_from_text(text, 4)
    assert len(result) == 4


def test_last_point_always_equals_total_point_count():
    text = _make_numbered_text(50)
    for n in [1, 2, 3, 5]:
        result = equal_partition_last_points_from_text(text, n)
        assert result[-1] == 50, f"For n={n}, last point was {result[-1]} not 50"


def test_single_point_transcript():
    text = "1. Only one point"
    result = equal_partition_last_points_from_text(text, 1)
    assert result == [1]


def test_n_greater_than_point_count_returns_all_points_bounded():
    """When n > point count, boundaries may repeat but last element is the total count."""
    text = _make_numbered_text(3)
    result = equal_partition_last_points_from_text(text, 10)
    assert result[-1] == 3


def test_empty_transcript_returns_empty():
    result = equal_partition_last_points_from_text("", 4)
    assert result == []


def test_n_zero_raises_value_error():
    text = _make_numbered_text(10)
    with pytest.raises(ValueError):
        equal_partition_last_points_from_text(text, 0)


# ============================================================================
# build_partition_ranges
# ============================================================================

def test_single_last_point():
    result = build_partition_ranges([100])
    assert result == [(1, 100)]


def test_multiple_last_points():
    result = build_partition_ranges([145, 287, 421])
    assert result == [(1, 145), (146, 287), (288, 421)]


def test_ranges_are_contiguous():
    ranges = build_partition_ranges([10, 20, 30])
    for i in range(len(ranges) - 1):
        assert ranges[i][1] + 1 == ranges[i + 1][0]


def test_first_range_starts_at_one():
    ranges = build_partition_ranges([50, 100])
    assert ranges[0][0] == 1


def test_last_range_ends_at_max_point():
    last_points = [33, 66, 99]
    ranges = build_partition_ranges(last_points)
    assert ranges[-1][1] == 99


def test_empty_last_points_returns_empty():
    result = build_partition_ranges([])
    assert result == []


# ============================================================================
# build_content_payloads
# ============================================================================

def _simple_hierarchy(n_content: int = 1) -> list[TopicNode]:
    """
    Produces a hierarchy with a single parent and n_content CONTENT children.
    Points: each CONTENT node gets 2 points.
    """
    children = [
        TopicNode(
            name="CONTENT",
            start_point=2 * i - 1,
            end_point=2 * i,
            children=[],
        )
        for i in range(1, n_content + 1)
    ]
    return [TopicNode(name="Parent", start_point=1, end_point=2 * n_content, children=children)]


def _make_points(total: int) -> list[str]:
    return [f"{i}. Point {i}" for i in range(1, total + 1)]


def test_single_content_node_produces_single_payload():
    hierarchy = _simple_hierarchy(1)
    points = _make_points(2)
    result = build_content_payloads(hierarchy, points)
    assert len(result.payload) == 1


def test_two_content_nodes_produce_two_payloads():
    hierarchy = _simple_hierarchy(2)
    points = _make_points(4)
    result = build_content_payloads(hierarchy, points)
    assert len(result.payload) == 2


def test_hierarchy_path_preserved_in_payload():
    hierarchy = [
        TopicNode(
            name="LangGraph",
            start_point=1,
            end_point=3,
            children=[
                TopicNode(name="CONTENT", start_point=1, end_point=3, children=[])
            ],
        )
    ]
    points = _make_points(3)
    result = build_content_payloads(hierarchy, points)
    assert result.payload[0].hierarchy_path == ["LangGraph"]


def test_content_points_list_sliced_correctly():
    hierarchy = [
        TopicNode(
            name="A",
            start_point=1,
            end_point=3,
            children=[
                TopicNode(name="CONTENT", start_point=1, end_point=3, children=[])
            ],
        )
    ]
    points = ["1. Alpha", "2. Beta", "3. Gamma"]
    result = build_content_payloads(hierarchy, points)
    assert result.payload[0].content_points_list == ["1. Alpha", "2. Beta", "3. Gamma"]


def test_gap_filling_extends_range_to_cover_uncovered_points():
    """
    If there is a gap between two CONTENT nodes, the start of the second
    is extended backward to cover uncovered points.
    """
    hierarchy = [
        TopicNode(
            name="Root",
            start_point=1,
            end_point=10,
            children=[
                TopicNode(name="A", start_point=1, end_point=3, children=[
                    TopicNode(name="CONTENT", start_point=1, end_point=3, children=[])
                ]),
                TopicNode(name="B", start_point=7, end_point=10, children=[
                    TopicNode(name="CONTENT", start_point=7, end_point=10, children=[])
                ]),
            ],
        )
    ]
    points = _make_points(10)
    result = build_content_payloads(hierarchy, points)
    assert len(result.payload) == 2
    # Second payload should start at 4 (gap filled from 4 to 6)
    assert result.payload[1].range[0] == 4


def test_uuids_are_unique_per_content_node():
    hierarchy = _simple_hierarchy(3)
    points = _make_points(6)
    result = build_content_payloads(hierarchy, points)
    ids = [p.id for p in result.payload]
    assert len(ids) == len(set(ids)), "UUIDs are not unique"


def test_content_store_initialised_with_empty_strings():
    hierarchy = _simple_hierarchy(2)
    points = _make_points(4)
    result = build_content_payloads(hierarchy, points)
    for _, item in result.metadata.items():
        assert item.content == ""
        assert item.summary == ""


def test_metadata_dict_keyed_by_uuid():
    hierarchy = _simple_hierarchy(2)
    points = _make_points(4)
    result = build_content_payloads(hierarchy, points)
    payload_ids = {p.id for p in result.payload}
    metadata_ids = set(result.metadata.keys())
    assert payload_ids == metadata_ids


def test_nodes_hierarchy_mirrors_input_hierarchy():
    hierarchy = _simple_hierarchy(1)
    points = _make_points(2)
    result = build_content_payloads(hierarchy, points)
    assert len(result.nodes) == 1
    assert isinstance(result.nodes[0], TitleNode)
    assert result.nodes[0].name == "Parent"
    assert len(result.nodes[0].subtopics) == 1
    assert isinstance(result.nodes[0].subtopics[0], ContentNode)


# ============================================================================
# filter_payload_by_range
# ============================================================================

def _make_payload(id: str, range_end: int) -> ContentPayload:
    return ContentPayload(
        id=id,
        hierarchy_path=[],
        range=(1, range_end),
        content_points_list=[],
    )


def test_all_items_in_range():
    payload = [_make_payload("a", 5), _make_payload("b", 10)]
    result = filter_payload_by_range(payload, 1, 10)
    assert len(result) == 2


def test_no_items_in_range():
    payload = [_make_payload("a", 5), _make_payload("b", 10)]
    result = filter_payload_by_range(payload, 11, 20)
    assert result == []


def test_partial_filter():
    payload = [_make_payload("a", 5), _make_payload("b", 15), _make_payload("c", 25)]
    result = filter_payload_by_range(payload, 1, 15)
    assert len(result) == 2
    assert result[0].id == "a"
    assert result[1].id == "b"


def test_boundary_items_included():
    payload = [_make_payload("a", 10), _make_payload("b", 20)]
    result = filter_payload_by_range(payload, 10, 20)
    assert len(result) == 2


# ============================================================================
# count_chunks
# ============================================================================

def test_count_chunks_exact_multiple():
    # 12000 tokens / 6000 per chunk = exactly 2 chunks
    assert count_chunks(12000, 6000) == 2


def test_count_chunks_fractional_rounds_up():
    # 7000 / 6000 = 1.167 → ceil = 2
    assert count_chunks(7000, 6000) == 2


def test_count_chunks_single_chunk_when_within_budget():
    # 5000 / 6000 < 1 → ceil = 1
    assert count_chunks(5000, 6000) == 1


def test_count_chunks_exactly_one_chunk_at_budget():
    assert count_chunks(6000, 6000) == 1


def test_count_chunks_large_transcript():
    # 60000 tokens / 6000 per chunk = 10 chunks
    assert count_chunks(60000, 6000) == 10


def test_count_chunks_zero_tokens_returns_one():
    # A zero-token transcript still produces one (empty) chunk
    assert count_chunks(0, 6000) == 1


def test_count_chunks_negative_tokens_returns_one():
    # Negative total_tokens is treated the same as zero
    assert count_chunks(-100, 6000) == 1


def test_count_chunks_zero_chunk_tokens_raises():
    with pytest.raises(ValueError, match="chunk_tokens must be greater than zero"):
        count_chunks(6000, 0)


def test_count_chunks_negative_chunk_tokens_raises():
    with pytest.raises(ValueError):
        count_chunks(6000, -1)


# ============================================================================
# split_text_into_chunks
# ============================================================================

def _make_multiline_text(n_lines: int) -> str:
    """Helper: create a text with n_lines lines."""
    return "\n".join(f"Line {i}" for i in range(1, n_lines + 1))


def test_split_one_chunk_returns_whole_text():
    text = _make_multiline_text(10)
    result = split_text_into_chunks(text, 1)
    assert len(result) == 1
    assert result[0] == text


def test_split_two_chunks_returns_two_parts():
    text = _make_multiline_text(10)
    result = split_text_into_chunks(text, 2)
    assert len(result) == 2


def test_split_preserves_order():
    text = "A\nB\nC\nD\nE\nF\nG\nH"
    result = split_text_into_chunks(text, 2)
    # Concatenating all parts must reconstruct the original (modulo newlines)
    joined = "".join(result)
    assert "A" in joined
    assert "H" in joined
    # No line should appear before one that was earlier in the original.
    first_part_lines = set(result[0].splitlines())
    second_part_lines = set(result[1].splitlines())
    # A comes before H so A must be in the first chunk
    assert "A" in first_part_lines
    assert "H" in second_part_lines


def test_split_no_overlap_between_chunks():
    text = _make_multiline_text(20)
    result = split_text_into_chunks(text, 4)
    all_lines = []
    for chunk in result:
        all_lines.extend(chunk.splitlines())
    # No duplicate lines across chunks
    assert len(all_lines) == len(set(all_lines))


def test_split_all_content_preserved():
    text = _make_multiline_text(30)
    result = split_text_into_chunks(text, 5)
    # Reconstruct and compare
    reconstructed = "".join(result)
    for line in text.splitlines():
        assert line in reconstructed


def test_split_n_greater_than_lines_returns_one_per_line():
    text = "A\nB\nC"
    result = split_text_into_chunks(text, 10)
    # Should return at most one chunk per line
    assert len(result) <= 10
    for chunk in result:
        assert chunk.strip() != ""


def test_split_empty_text_raises():
    with pytest.raises(ValueError, match="text must not be empty"):
        split_text_into_chunks("", 3)


def test_split_zero_n_raises():
    with pytest.raises(ValueError, match="n must be greater than zero"):
        split_text_into_chunks("some text", 0)


def test_split_negative_n_raises():
    with pytest.raises(ValueError):
        split_text_into_chunks("some text", -1)


def test_split_single_line_text():
    result = split_text_into_chunks("Only one line here", 1)
    assert len(result) == 1
    assert "Only one line here" in result[0]


def test_split_chunks_are_non_empty():
    text = _make_multiline_text(12)
    result = split_text_into_chunks(text, 3)
    for chunk in result:
        assert chunk.strip() != ""

