# ─── Cell 5: Pydantic v2 Data Schemas ────────────────────────────────────────

class VideoDocument(BaseModel):
    'A YouTube video with its cleaned transcript.'
    video_id:          str            = Field(..., description="11-char YouTube video ID")
    title:             str            = Field(default="Unknown Title")
    url:               str            = Field(..., description="Original YouTube URL")
    channel:           str            = Field(default="Unknown Channel")
    duration_seconds:  int            = Field(default=0)
    transcript:        str            = Field(..., description="Cleaned full transcript")
    transcript_chunks: List[str]      = Field(default_factory=list)
    word_count:        int            = Field(default=0)
    fetched_at:        str            = Field(default_factory=lambda: datetime.utcnow().isoformat())

    @field_validator("video_id")
    @classmethod
    def validate_video_id(cls, v: str) -> str:
        if len(v) != 11:
            raise ValueError(f"Video ID must be 11 chars, got {len(v)}: {v!r}")
        if not re.match(r'^[a-zA-Z0-9_-]{11}$', v):
            raise ValueError(f"Invalid video ID characters: {v!r}")
        return v

    model_config = {"arbitrary_types_allowed": True}


class TopicNode(BaseModel):
    'One node in the per-video topic hierarchy.'
    topic_id:        str            = Field(default_factory=lambda: str(uuid.uuid4()))
    topic_name:      str            = Field(..., description="Normalised topic name")
    parent_topic_id: Optional[str]  = Field(default=None)
    depth:           int            = Field(default=0, ge=0)
    source_video_id: str            = Field(..., description="Video this node came from")
    content:         str            = Field(..., description="Content relevant to this topic")
    canonical_id:    Optional[str]  = Field(default=None)
    embedding:       Optional[List[float]] = Field(default=None, exclude=True)

    model_config = {"arbitrary_types_allowed": True}


class TopicTree(BaseModel):
    'Full hierarchy extracted from a single video.'
    video_id:    str                  = Field(...)
    root_topics: List[TopicNode]      = Field(default_factory=list)
    all_nodes:   Dict[str, TopicNode] = Field(default_factory=dict)


class CanonicalTopic(BaseModel):
    'Unified representation of a topic concept across all videos.'
    canonical_id:     str        = Field(default_factory=lambda: str(uuid.uuid4()))
    canonical_name:   str        = Field(..., description="Representative name")
    aliases:          List[str]  = Field(default_factory=list)
    source_video_ids: List[str]  = Field(default_factory=list)
    merged_topic_ids: List[str]  = Field(default_factory=list)


class MasterTopicDocument(BaseModel):
    'Aggregated, deduplicated content for a canonical topic.'
    canonical_id:     str       = Field(...)
    canonical_name:   str       = Field(...)
    content:          str       = Field(...)
    source_video_ids: List[str] = Field(default_factory=list)
    token_count:      int       = Field(default=0)


class TopicSummary(BaseModel):
    'Concise retrieval-optimised summary for a canonical topic.'
    canonical_id:   str       = Field(...)
    canonical_name: str       = Field(...)
    summary:        str       = Field(..., description="Dense summary paragraph")
    key_points:     List[str] = Field(default_factory=list)


# -- LLM Output Schemas --

class TopicHierarchyItem(BaseModel):
    'Recursive topic hierarchy item returned by the LLM.'
    name:      str                        = Field(...)
    content:   str                        = Field(default="")
    subtopics: List["TopicHierarchyItem"] = Field(default_factory=list)

TopicHierarchyItem.model_rebuild()


class TopicHierarchyOutput(BaseModel):
    topics: List[TopicHierarchyItem] = Field(default_factory=list)


class CanonicalizationDecision(BaseModel):
    are_same:       bool  = Field(...)
    confidence:     float = Field(ge=0.0, le=1.0)
    canonical_name: str   = Field(...)
    reasoning:      str   = Field(default="")


class TopicSummaryOutput(BaseModel):
    summary:    str       = Field(...)
    key_points: List[str] = Field(default_factory=list)


# -- LangGraph Pipeline State --

class PipelineState(TypedDict):
    urls:                List[str]
    video_documents:     List[VideoDocument]
    structured_notes:    Dict[str, str]
    topic_trees:         Dict[str, TopicTree]
    topic_nodes:         List[TopicNode]
    canonical_topics:    List[CanonicalTopic]
    master_documents:    List[MasterTopicDocument]
    summaries:           List[TopicSummary]
    errors:              List[str]
    current_phase:       str
    processing_complete: bool

print("✅ All Pydantic schemas defined")
