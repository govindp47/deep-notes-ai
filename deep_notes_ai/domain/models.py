"""
deep_notes_ai/domain/models.py

All data models used throughout the system.
No logic. No I/O.

Categories:
  - Dataclasses: lightweight containers, serialisable with dataclasses.asdict()
  - Pydantic models: used for LLM structured output and external data validation
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import List, Literal

from pydantic import BaseModel, Field


# ============================================================================
# CUSTOM EXCEPTIONS
# ============================================================================

class InvalidYoutubeUrlError(Exception):
    """Raised when a provided YouTube URL is invalid or malformed."""


class UnsupportedSourceTypeError(Exception):
    """Raised when the specified source type is invalid or not recognised."""


class UnsupportedSourceError(Exception):
    """Raised when the provided source is not supported for the given type."""


class VideoMetadataError(Exception):
    """Raised when video metadata extraction fails unexpectedly."""


class TranscriptFetchError(Exception):
    """Raised when a YouTube transcript cannot be fetched."""


class UnsupportedLLMProviderError(Exception):
    """Raised when an unsupported LLM provider is requested."""


class LLMCallError(Exception):
    """Raised when an LLM API call fails."""


class PromptNotFoundError(Exception):
    """Raised when a prompt template file does not exist."""


class PersistenceError(Exception):
    """Raised on any file I/O failure."""


class AlgorithmError(Exception):
    """Raised when a domain algorithm detects invalid input."""


class TextChunkingError(AlgorithmError):
    """Raised when text cannot be split into valid chunks."""


class HierarchyValidationError(Exception):
    """Raised when the generated hierarchy fails validation."""


class HierarchyMismatchError(Exception):
    """Raised when the updated hierarchy nodes mismatch."""


class ContentNodeCountMismatchError(AlgorithmError):
    """
    Raised when the number of extracted ContentPayload objects does not match
    the number of CONTENT nodes present in the validated hierarchy.
    """


class BatchCountMismatchError(Exception):
    """
    Raised when the number of items returned by the LLM does not match the
    number of expected CONTENT nodes. Signals: repartition (do not retry).
    """

    def __init__(self, expected: int, actual: int, message: str = "") -> None:
        self.expected = expected
        self.actual = actual
        super().__init__(message or f"Expected {expected} items, but LLM returned {actual}.")


class DuplicateIdsError(Exception):
    """
    Raised when the LLM returns duplicate IDs in a batch response.
    Signals: retry the same batch.
    """

    def __init__(self, duplicates: list[str], message: str = "") -> None:
        self.duplicates = duplicates
        super().__init__(message or f"Duplicate IDs returned by LLM: {sorted(duplicates)}")


class IncorrectIdsError(Exception):
    """
    Raised when the LLM returns IDs that do not match the expected set.
    Signals: retry the same batch.
    """

    def __init__(
        self, missing: list[str], unexpected: list[str], message: str = ""
    ) -> None:
        self.missing = missing
        self.unexpected = unexpected
        super().__init__(
            message or f"Incorrect IDs. Missing: {sorted(missing)}, Unexpected: {sorted(unexpected)}"
        )


class RetryExhaustedError(Exception):
    """Raised when all retry attempts are exhausted."""

    def __init__(self, attempts: int, last_error: Exception, message: str = "") -> None:
        self.attempts = attempts
        self.last_error = last_error
        super().__init__(
            message or f"Retries exhausted after {attempts} attempt(s). Last error: {last_error}"
        )


class ContentGenerationError(Exception):
    """Raised when content generation cannot complete after fallback."""


class SummaryGenerationError(Exception):
    """Raised when summary generation cannot complete after fallback."""


# ============================================================================
# ENUMS
# ============================================================================

class SourceType(StrEnum):
    """
    Supported types of content sources for ingestion.
    """
    YOUTUBE = "youtube"
    ARTICLE = "article"
    DOCUMENTATION = "documentation"
    BOOK = "book"
    PRESENTATION = "presentation"


# ============================================================================
# DATACLASSES
# ============================================================================

@dataclass(slots=True)
class ContentStoreItem:
    """
    Holds the generated structured markdown and revision summary for a single
    CONTENT leaf node.
    """
    content: str = ""
    summary: str = ""


@dataclass(slots=True)
class ContentNode:
    """
    Lightweight representation of a CONTENT leaf in the final node hierarchy.
    Carries only the UUID needed to look up the corresponding ContentStoreItem.
    """
    type: Literal["content"] = "content"
    id: str = ""


@dataclass(slots=True)
class TitleNode:
    """
    Lightweight representation of a topic node in the final hierarchy.
    Carries the topic name and ordered list of child nodes.
    """
    type: Literal["topic"] = "topic"
    name: str = ""
    subtopics: list["Node"] = field(default_factory=list)


# Type alias: any node in the lightweight hierarchy.
Node = TitleNode | ContentNode


@dataclass(slots=True)
class ContentExtraction:
    """
    Intermediate result produced during CONTENT node traversal.
    Carries enough information to build a ContentPayload.
    """
    id: str
    hierarchy_path: list[str]
    starting_point: int
    ending_point: int


@dataclass(slots=True)
class ExtractionResult:
    """
    Aggregated return value of _extract_content_nodes().
    Packages the list of all CONTENT extractions, the UUID-to-ContentStoreItem
    map, and the corresponding lightweight Node.
    """
    extracted: list[ContentExtraction]
    metadata: dict[str, ContentStoreItem]
    node: Node


@dataclass(slots=True)
class ContentPayload:
    """
    Input data for one CONTENT node sent to the content-structuring LLM.
    Contains the UUID, the topic hierarchy path, the point range covered,
    and the actual transcript lines.

    Note on `id`: carries the real UUID. When sent to the LLM, a temporary
    ID (N1, N2, ...) is substituted — the UUID is never exposed to the LLM.
    """
    id: str
    hierarchy_path: list[str]
    range: tuple[int, int]
    content_points_list: list[str]


@dataclass(slots=True)
class StructuredContentPayload:
    """
    Input data for one CONTENT node sent to the summary-generation LLM.
    Combines the UUID with the hierarchy path and the structured markdown
    (from ContentStoreItem.content).
    """
    id: str
    hierarchy_path: list[str]
    structured_content: str


@dataclass(slots=True)
class PayloadResult:
    """
    Return type of build_content_payloads(). Bundles all three outputs of the
    extraction phase.
    """
    payload: list[ContentPayload]
    metadata: dict[str, ContentStoreItem]
    nodes: list[Node]


@dataclass(slots=True)
class LLMCallRecord:
    """
    Immutable record of a single LLM invocation.

    Captured automatically by the monitoring layer — nodes never create these.
    """
    node_name: str
    operation_name: str
    provider: str
    model: str
    started_at: datetime
    finished_at: datetime
    duration_ms: float
    input_tokens: int | None
    output_tokens: int | None
    total_tokens: int | None
    estimated_cost: float | None
    success: bool
    exception_type: str | None
    exception_message: str | None


@dataclass(slots=True)
class LLMUsageSummary:
    """
    Aggregate statistics computed from all LLMCallRecord instances.
    """
    total_calls: int
    successful_calls: int
    failed_calls: int
    total_input_tokens: int
    total_output_tokens: int
    total_tokens: int
    estimated_total_cost: float | None
    total_duration_ms: float


# ============================================================================
# PROGRESS REPORTING MODELS
# ============================================================================

class ProgressStatus(StrEnum):
    """
    Lifecycle status values for a ProgressEvent.

    STARTED    — node has just begun execution.
    RUNNING    — node is mid-execution (incremental update).
    COMPLETED  — node finished successfully.
    FAILED     — node terminated with an error.
    INFO       — informational milestone, no status change.
    """
    STARTED   = "started"
    RUNNING   = "running"
    COMPLETED = "completed"
    FAILED    = "failed"
    INFO      = "info"


@dataclass(frozen=True)
class ProgressEvent:
    """
    Immutable record of a single user-facing progress milestone.

    Captured by ProgressService and forwarded to all registered reporters.
    Nodes never create these directly — they call ProgressService helpers.

    Attributes:
        timestamp:  UTC wall-clock time of the event.
        node_name:  Pipeline node that emitted the event.
        stage:      Human-readable label for the current stage.
        status:     Lifecycle status (see ProgressStatus).
        message:    Short, user-facing description.
        current:    For incremental progress: current item index (1-based).
        total:      For incremental progress: total item count.
    """
    timestamp: datetime
    node_name: str
    stage: str
    status: ProgressStatus
    message: str
    current: int | None = None
    total: int | None = None


# ============================================================================
# PYDANTIC MODELS
# ============================================================================

class TopicNode(BaseModel):
    """
    Represents one node in the LLM-generated transcript hierarchy.
    Used as the output schema for the hierarchy-generation LLM call.

    Special: name == "CONTENT" is the sentinel for a leaf node.
    children is always empty when name == "CONTENT".
    """

    name: str = Field(
        description=(
            'Topic title. '
            'Use "CONTENT" ONLY when this node represents transcript content '
            'that cannot be further grouped into meaningful subtopics.'
        )
    )

    start_point: int = Field(
        description="Inclusive starting transcript point number."
    )

    end_point: int = Field(
        description="Inclusive ending transcript point number."
    )

    children: List["TopicNode"] = Field(
        default_factory=list,
        description="Child topic nodes in the same order as the transcript.",
    )


# Required for Pydantic self-referential model resolution.
TopicNode.model_rebuild()


class TranscriptHierarchy(BaseModel):
    """
    Top-level output schema for the hierarchy LLM call.
    Wraps the list of root TopicNode objects.
    """

    hierarchy: List[TopicNode] = Field(
        description="Top-level hierarchy nodes of the transcript."
    )


class StructuredContent(BaseModel):
    """
    Structured markdown generated for a single CONTENT node.
    The `id` is a temporary N-identifier (e.g. N1, N2).
    """

    id: str = Field(
        description=(
            "Temporary CONTENT node identifier "
            "(for example N1, N2, N3) exactly as provided in the input."
        )
    )

    markdown: str = Field(
        description=(
            "Markdown representation of ONLY the transcript points belonging "
            "to this CONTENT node."
        )
    )


class StructuredContentBatch(BaseModel):
    """
    Complete LLM response for one content-generation batch call.
    """

    items: list[StructuredContent]


class ContentSummary(BaseModel):
    """
    One item in the LLM's structured output during summary generation.
    The `id` is a temporary N-identifier.
    """

    id: str = Field(
        description=(
            "Temporary CONTENT node identifier "
            "(for example N1, N2, N3) exactly as provided in the input."
        )
    )

    summary: str = Field(
        description=(
            "Markdown summary of ONLY the transcript content belonging "
            "to this CONTENT node."
        )
    )


class ContentSummaryBatch(BaseModel):
    """
    Complete LLM response for one summary-generation batch call.
    """

    items: list[ContentSummary]
