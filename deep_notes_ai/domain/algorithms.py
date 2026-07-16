"""
deep_notes_ai/domain/algorithms.py

Pure domain algorithms. Accept only primitive types and domain models.
No I/O, no side effects, no framework dependencies.
"""
from __future__ import annotations

import math
import re
from uuid import uuid4

from deep_notes_ai.domain.models import (
    AlgorithmError,
    ContentExtraction,
    ContentNode,
    ContentPayload,
    ContentStoreItem,
    ExtractionResult,
    HierarchyMismatchError,
    Node,
    PayloadResult,
    TextChunkingError,
    TitleNode,
    TopicNode,
)


# ============================================================================
# TRANSCRIPT CLEANING
# ============================================================================

def clean_numbered_points(text: str) -> list[str]:
    """
    Convert a bullet-formatted LLM response to a numbered list.

    Normalises line endings, detects bullet patterns, and numbers all points
    sequentially starting at 1. Continuation lines (non-bullet, non-empty)
    are appended to the current point. Separator lines are ignored.
    """
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    lines = text.split("\n")

    bullet_pattern = re.compile(
        r"""
        ^\s*
        (?:
            [-*•●○◦▪▸►▶▫]+      # bullet symbols
            |
            \d+[.)]             # numbered bullets
        )
        (?:\s+(.*))?            # optional text on same line
        $
        """,
        re.VERBOSE,
    )

    separator_pattern = re.compile(
        r"^\s*[-=*_~]{5,}\s*$"
    )

    cleaned_points: list[str] = []
    current: str | None = None

    for raw_line in lines:
        line = raw_line.rstrip()

        # Ignore separator lines
        if separator_pattern.match(line):
            continue

        if not line.strip():
            continue

        match = bullet_pattern.match(line)

        if match:
            if current is not None:
                cleaned_points.append(current.strip())

            text_after_bullet = match.group(1)

            if text_after_bullet:
                current = text_after_bullet.strip()
            else:
                current = ""

        else:
            stripped = line.strip()

            if not stripped:
                continue  # pragma: no cover

            if current is None:
                current = stripped
            elif current == "":
                current = stripped
            else:
                current += " " + stripped

    if current is not None and current.strip():
        cleaned_points.append(current.strip())

    # Collapse multiple spaces
    cleaned_points = [
        re.sub(r"[ \t]+", " ", p).strip()
        for p in cleaned_points
    ]

    output = []
    for i, point in enumerate(cleaned_points, start=1):
        output.append(f"{i}. {point}")

    return output



def count_chunks(total_tokens: int, chunk_tokens: int) -> int:
    """
    Calculate the number of chunks required to cover total_tokens given a
    per-chunk token budget.

    Args:
        total_tokens: Total token count of the content to split.
        chunk_tokens: Maximum token budget per chunk (> 0).

    Returns:
        Number of chunks (>= 1).

    Raises:
        ValueError: if chunk_tokens <= 0.
    """
    if chunk_tokens <= 0:
        raise TextChunkingError("chunk_tokens must be greater than zero.")

    if total_tokens <= 0:
        return 1

    return math.ceil(total_tokens / chunk_tokens)


def split_text_into_chunks(
    text: str,
    n: int,
    overlap_chars: int = 500,
) -> list[str]:
    """
    Split text into approximately equal-sized chunks by character count.

    Unlike transcript-point partitioning, this function simply divides the
    raw text into contiguous character ranges. A configurable overlap can be
    included between adjacent chunks to preserve context for LLM processing.

    Args:
        text:
            Input text.

        n:
            Number of chunks to generate (> 0).

        overlap_chars:
            Number of characters from the previous chunk to include at the
            beginning of the next chunk.

    Returns:
        List of ordered text chunks.

    Raises:
        ValueError:
            If n <= 0.
            If overlap_chars < 0.
            If text is empty.
    """
    if n <= 0:
        raise TextChunkingError("n must be greater than zero.")

    if overlap_chars < 0:
        raise TextChunkingError("overlap_chars must be non-negative.")

    if not text.strip():
        raise TextChunkingError("text must not be empty.")

    if n == 1:
        return [text]

    text_length = len(text)

    # Don't generate more chunks than characters.
    n = min(n, text_length)

    chunk_size = math.ceil(text_length / n)

    chunks: list[str] = []

    for i in range(n):
        start = max(0, i * chunk_size - overlap_chars)
        end = min(text_length, (i + 1) * chunk_size)

        if start >= end:
            continue

        chunks.append(text[start:end])

    return chunks


# ============================================================================
# CONTENT NODE EXTRACTION
# ============================================================================

def _extract_content_nodes(
    node: TopicNode,
    path: tuple[str, ...] = (),
) -> ExtractionResult:
    """
    Traverse the TopicNode hierarchy once.

    Simultaneously:
    1. Extracts every CONTENT node.
    2. Generates UUIDs (single point of UUID creation).
    3. Creates the metadata dictionary (ContentStoreItem per UUID).
    4. Builds the lightweight Node hierarchy (TitleNode / ContentNode).
    """
    if node.name == "CONTENT":
        content_id = str(uuid4())

        return ExtractionResult(
            extracted=[
                ContentExtraction(
                    id=content_id,
                    hierarchy_path=list(path),
                    starting_point=node.start_point,
                    ending_point=node.end_point,
                )
            ],
            metadata={
                content_id: ContentStoreItem(),
            },
            node=ContentNode(
                id=content_id,
            ),
        )

    current_path = (*path, node.name)
    extracted: list[ContentExtraction] = []
    metadata: dict[str, ContentStoreItem] = {}
    children: list[Node] = []

    for child in node.children:
        result = _extract_content_nodes(child, current_path)
        extracted.extend(result.extracted)
        metadata.update(result.metadata)
        children.append(result.node)

    return ExtractionResult(
        extracted=extracted,
        metadata=metadata,
        node=TitleNode(
            name=node.name,
            subtopics=children,
        ),
    )


def build_content_payloads(
    hierarchy: list[TopicNode],
    content_points: list[str],
) -> PayloadResult:
    """
    Build the complete content payload from a hierarchy and transcript points.

    Returns a PayloadResult containing:
    - payload: list[ContentPayload] — one entry per CONTENT node
    - metadata: dict[str, ContentStoreItem] — UUID → empty ContentStoreItem
    - nodes: list[Node] — lightweight hierarchy (TitleNode / ContentNode)

    Includes gap filling: if points between two CONTENT nodes are uncovered,
    extends the start of the next node to cover them.
    """
    all_extracted: list[ContentExtraction] = []
    metadata: dict[str, ContentStoreItem] = {}
    converted_hierarchy: list[Node] = []

    for topic in hierarchy:
        result = _extract_content_nodes(topic)
        all_extracted.extend(result.extracted)
        metadata.update(result.metadata)
        converted_hierarchy.append(result.node)
    
    sorted_nodes = sorted(
        all_extracted,
        key=lambda node: (node.starting_point, node.ending_point),
    )
    previous_end = 0
    payload: list[ContentPayload] = []

    for node in sorted_nodes:
        start = node.starting_point
        end = node.ending_point

        # Fill uncovered gaps.
        if previous_end + 1 < start:
            start = previous_end + 1

        previous_end = max(previous_end, end)

        payload.append(
            ContentPayload(
                id=node.id,
                hierarchy_path=node.hierarchy_path,
                range=(start, end),
                content_points_list=content_points[start - 1 : end],
            )
        )

    return PayloadResult(
        payload=payload,
        metadata=metadata,
        nodes=converted_hierarchy,
    )


def _extract_content_payloads(
    topic_node: TopicNode,
    hierarchy_node: Node,
    path: tuple[str, ...] = (),
) -> list[ContentExtraction]:
    """
    Traverse the TopicNode hierarchy together with the converted Node hierarchy.

    Unlike `_extract_content_nodes`, this function does not generate UUIDs or
    metadata. Instead, it reuses the IDs already present in the corresponding
    ContentNode objects from the converted hierarchy.

    Returns a list of ContentExtraction objects that can later be converted
    into ContentPayload objects.
    """
    if topic_node.name == "CONTENT":
        if not isinstance(hierarchy_node, ContentNode):
            raise HierarchyMismatchError(
                "Hierarchy mismatch: expected ContentNode for CONTENT topic."
            )

        return [
            ContentExtraction(
                id=hierarchy_node.id,
                hierarchy_path=list(path),
                starting_point=topic_node.start_point,
                ending_point=topic_node.end_point,
            )
        ]

    if not isinstance(hierarchy_node, TitleNode):
        raise HierarchyMismatchError(
            f"Hierarchy mismatch: expected TitleNode for topic '{topic_node.name}'."
        )

    current_path = (*path, topic_node.name)
    extracted: list[ContentExtraction] = []

    for topic_child, hierarchy_child in zip(
        topic_node.children,
        hierarchy_node.subtopics,
        strict=True,
    ):
        extracted.extend(
            _extract_content_payloads(
                topic_child,
                hierarchy_child,
                current_path,
            )
        )

    return extracted


def rebuild_content_payloads(
    hierarchy: list[TopicNode],
    converted_hierarchy: list[Node],
    content_points: list[str],
) -> list[ContentPayload]:
    """
    Rebuild ContentPayload objects using an existing converted hierarchy.

    Assumes the converted hierarchy already contains the correct ContentNode IDs.
    No UUID generation or metadata creation is performed.
    """
    all_extracted: list[ContentExtraction] = []

    for topic, node in zip(hierarchy, converted_hierarchy, strict=True):
        all_extracted.extend(
            _extract_content_payloads(
                topic,
                node,
            )
        )
    
    sorted_nodes = sorted(
        all_extracted,
        key=lambda node: (node.starting_point, node.ending_point),
    )
    previous_end = 0
    payload: list[ContentPayload] = []

    for node in sorted_nodes:
        start = node.starting_point
        end = node.ending_point

        # Fill uncovered gaps.
        if previous_end + 1 < start:
            start = previous_end + 1

        previous_end = max(previous_end, end)

        payload.append(
            ContentPayload(
                id=node.id,
                hierarchy_path=node.hierarchy_path,
                range=(start, end),
                content_points_list=content_points[start - 1 : end],
            )
        )

    return payload


def filter_payload_by_range(
    payload: list[ContentPayload],
    start_point: int,
    end_point: int,
) -> list[ContentPayload]:
    """
    Return only the ContentPayload items whose ending point lies within the
    specified filter range [start_point, end_point] (inclusive).
    """
    return [
        item
        for item in payload
        if start_point <= item.range[1] <= end_point
    ]
