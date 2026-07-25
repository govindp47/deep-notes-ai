"""
deep_notes_ai/domain/models.py

All data models used throughout the system.
No logic. No I/O.

Categories:
  - Dataclasses: lightweight containers, serialisable with dataclasses.asdict()
  - Pydantic models: used for LLM structured output and external data validation
"""
from __future__ import annotations

from abc import ABC
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


class EmptyTranscriptError(TranscriptFetchError):
    """
    Raised when YouTube returns an empty or whitespace-only transcript.
    """


class UnsupportedLLMProviderError(Exception):
    """Raised when an unsupported LLM provider is requested."""


class LLMCallError(Exception):
    """Raised when an LLM API call fails."""


class PromptNotFoundError(Exception):
    """Raised when a prompt template file does not exist."""


class PersistenceError(Exception):
    """Raised on any file I/O failure."""


class InvalidProcessingContextError(Exception):
    """
    Raised when the current pipeline processing context is invalid or inconsistent.
    Indicates that execution cannot safely continue with the available state.
    """
    

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


class TranscriptTooLargeError(Exception):
    """
    Raised when a transcript exceeds the configured token limit and no
    timestamp chapters are available for partitioning.
    """


class TimestampExtractionError(Exception):
    """Raised when timestamp chapter extraction fails unexpectedly."""

class InvalidBreakpointSelectionError(Exception):
    """Raised when user-selected breakpoints fail validation."""


class TranscriptPartitionError(Exception):
    """
    Raised when splitting the transcript produces a part that exceeds
    the configured per-part token limit.
    """


class ArticleDownloadError(Exception):
    """
    Raised when an article cannot be downloaded.

    Typical causes include:
        - Invalid URL
        - Network timeout
        - DNS failure
        - HTTP error
        - Redirect limit exceeded
    """


class ArticleExtractionError(Exception):
    """
    Raised when the downloaded HTML cannot be converted into readable content.

    Typical causes include:
        - Unsupported page structure
        - Extraction library failure
        - Empty extracted content
    """


class NoChaptersFoundError(ArticleExtractionError):
    """
    Raised when no valid chapter structure can be extracted from the article.
    Indicates that the downloaded content could not be organized into chapters.
    """


class ArticleMetadataError(Exception):
    """
    Raised when article metadata cannot be extracted or normalized.
    """


class ArticleStructureError(Exception):
    """
    Raised when extracted markdown cannot be converted into a valid document
    structure.
    """


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


class TranscriptProcessingMode(StrEnum):
    """
    Processing mode determined after token calculation.

    SINGLE     — transcript fits within the per-part limit; processed in one pass.
    MULTI_PART — transcript exceeds the limit; requires user-selected breakpoints.
    """
    SINGLE     = "single"
    MULTI_PART = "multi_part"


# ============================================================================
# DATACLASSES
# ============================================================================

@dataclass(slots=True)
class TimestampChapter:
    """
    One timestamp chapter parsed from a YouTube video description.

    Attributes:
        title:             Human-readable chapter name.
        timestamp_seconds: Chapter start offset in seconds from the beginning.
        display:           Formatted timestamp string exactly as it appeared
                           in the description (e.g. "01:23:45" or "04:32").
    """
    title: str
    timestamp_seconds: int
    display: str


@dataclass(slots=True)
class DocumentSection:
    """
    Represents a logical section extracted from an article.

    The MarkdownStructureService converts extracted markdown into a sequence of
    DocumentSection objects. These sections are later transformed into
    ChapterTranscript objects so the remaining LangGraph pipeline can remain
    completely source-agnostic.

    Attributes:
        heading:
            Human-readable section heading.

        level:
            Markdown heading level.

        content:
            Plain markdown/text belonging to this section only.
            Child sections are represented by separate DocumentSection objects.
    """

    heading: str
    level: int
    content: str

    def __post_init__(self) -> None:
        self.heading = self.heading.strip()
        self.content = self.content.strip()

        if not self.heading:
            raise ValueError("DocumentSection.heading must not be empty.")

        if self.level < 1:
            raise ValueError("DocumentSection.level must be >= 1.")

        first_line = self.content.split("\n", 1)[0].strip()

        if first_line.startswith("#"):
            raise ValueError(
                "DocumentSection.content must not include a markdown heading. "
                "The heading must be stored only in DocumentSection.heading."
            )


@dataclass(slots=True)
class ChapterTranscript:
    """
    Transcript segment corresponding to a single chapter.

    Attributes:
        title:
            Human-readable chapter title.

        display:
            Formatted timestamp string indicating the chapter's starting
            position (e.g. "01:23:45" or "04:32").

        transcript:
            Transcript text belonging to this chapter.

        tokens:
            Total number of tokens in ``transcript`` as calculated by the
            project's TokenizerService.
    """
    title: str
    display: str
    transcript: str
    tokens: int


@dataclass(slots=True)
class ContentPart:
    """
    A logical transcript partition processed independently by the pipeline.

    Each part represents a contiguous section of the original transcript,
    bounded by two chapter timestamps (or the end of the transcript for the
    final part).

    Attributes:
        part_title:
            Filesystem-safe identifier describing the transcript range covered
            by this part.

            The title is derived from the starting timestamp of this part and
            the starting timestamp of the following part.

            Examples:
                "00-00_to_08-35"
                "08-35_to_15-42"
                "15-42_to_27-10"
                "27-10_to_END"

            This value is intended for use as a directory name and therefore
            must contain only filesystem-safe characters.

        content:
            The raw transcript text belonging exclusively to this part. This
            content is passed through the existing processing pipeline
            (cleaning, hierarchy generation, content generation, summaries,
            etc.) independently of the other parts.

        tokens:
            Total number of tokens.
    """
    part_title: str
    content: str
    tokens: int

@dataclass(slots=True)
class ProcessingContext:
    """
    Holds the current execution state for transcript processing, including the
    selected processing mode and the content parts being processed.
    """
    processing_mode: TranscriptProcessingMode
    current_part: int
    total_parts: int
    content_parts: list[ContentPart]

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
class MergedTranscript:
    """
    Result of merging one or more processed transcript parts.

    Attributes:
        hierarchy:
            Combined hierarchy preserving the original transcript order.

        content_store:
            Combined UUID → ContentStoreItem mapping.
    """

    hierarchy: list[Node]
    content_store: dict[str, ContentStoreItem]


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

class ContentMetadata(BaseModel, ABC):
    """
    Generic metadata shared across all supported content sources.

    This model is intended to be extended by source-specific metadata models
    (e.g. YouTube videos, PDFs, websites, documents).
    """

    id: str = Field(...)
    url: str = Field(...)
    title: str = Field(...)
    description: str = Field(default="")
    upload_date: str = Field(default="")
    author: str = Field(default="")


class VideoMetadata(ContentMetadata):
    """
    Metadata specific to video-based content.
    """

    chapters: list[TimestampChapter] = Field(default_factory=list)


class ArticleMetadata(ContentMetadata):
    """
    Metadata specific to article-like sources.

    This model extends the generic ContentMetadata while remaining compatible
    with the existing PipelineState. The processing pipeline only depends on
    ContentMetadata fields, while article ingestion may use the additional
    attributes during extraction and diagnostics.
    """

    raw_html: str = Field(...)


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
