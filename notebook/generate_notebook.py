#!/usr/bin/env python3
"""
generate_notebook.py
Generates the complete deep_notes_knowledge_graph.ipynb notebook.
Run: python generate_notebook.py
"""

import json, uuid, os

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def cid():
    return str(uuid.uuid4())[:8]

def md(source: str):
    return {"cell_type": "markdown", "id": cid(), "metadata": {}, "source": source}

def code(source: str):
    return {"cell_type": "code", "execution_count": None, "id": cid(),
            "metadata": {}, "outputs": [], "source": source}

cells = []

# ===========================================================================
# CELL 1 — Title & Architecture Overview
# ===========================================================================
cells.append(md(r"""# 🧠 Deep Notes AI
## YouTube Knowledge Extraction & Knowledge Graph Platform

A **14-phase LangGraph pipeline** that transforms raw YouTube videos into a structured, queryable personal knowledge base.

---

### System Architecture

```
YouTube URLs
    │
    ▼
┌─────────────────────────────────────────────────────────┐
│                  LangGraph StateGraph                   │
│                                                         │
│  url_processor → transcript_extractor → note_generator │
│       │                                       │         │
│  [Validation]                         [GPT-4o-mini]    │
│                                               │         │
│  topic_extractor → topic_mapper → topic_canonicalizer  │
│  [GPT-4o-mini]      [SQLite]    [Embed+LLM dedup]     │
│                                               │         │
│  graph_writer → topic_aggregator → summary_generator  │
│  [Neo4j/SQLite]    [GPT-4o]        [GPT-4o-mini]      │
└─────────────────────────────────────────────────────────┘
    │
    ▼
┌──────────────────────────────────────────────┐
│              Storage Trinity                  │
│  SQLite (source) │ Neo4j (graph) │ Qdrant    │
└──────────────────────────────────────────────┘
    │
    ▼
query_video() │ query_topic() │ query_topic_summary()
```

### Technology Stack
| Component | Technology | Reason |
|-----------|-----------|--------|
| Orchestration | LangGraph 0.2+ | Production-grade stateful agent graphs |
| LLM Extraction | GPT-4o-mini | Cheap, fast, reliable JSON output |
| LLM Reasoning | GPT-4o | High-quality consolidation & aggregation |
| Embeddings | text-embedding-3-small | Best cost/quality for semantic search |
| Transcripts | youtube-transcript-api | No auth required |
| Schemas | Pydantic v2 | Type-safe, validated data models |
| Retry Logic | Tenacity | Exponential backoff for all API calls |
| Graph DB | Neo4j (optional) | Cypher traversal for topic relationships |
| Vector DB | Qdrant (in-memory) | Zero-infra semantic search |
| SQL DB | SQLite | Zero-infra source of truth, PostgreSQL-ready |
"""))

# ===========================================================================
# CELL 2 — Install Dependencies
# ===========================================================================
cells.append(code(r"""# ─── Cell 2: Install Dependencies ────────────────────────────────────────────
import sys

print("Installing dependencies…")
packages = [
    "langgraph>=0.2.0",
    "langchain>=0.3.0",
    "langchain-openai>=0.2.0",
    "langchain-core>=0.3.0",
    "qdrant-client>=1.7.0",
    "neo4j>=5.0.0",
    "tiktoken>=0.7.0",
    "tenacity>=8.0.0",
    "youtube-transcript-api>=0.6.0",
    "pydantic>=2.0.0",
    "python-dotenv>=1.0.0",
    "httpx>=0.27.0",
    "requests>=2.31.0",
]

import subprocess
result = subprocess.run(
    [sys.executable, "-m", "pip", "install", "-q", "--upgrade"] + packages,
    capture_output=True, text=True
)
if result.returncode != 0:
    print("STDERR:", result.stderr[-2000:])
else:
    print("✅ All dependencies installed successfully")
"""))

# ===========================================================================
# CELL 3 — Imports
# ===========================================================================
cells.append(code(r"""# ─── Cell 3: Core Imports ────────────────────────────────────────────────────
import os, re, json, uuid, sqlite3, logging, operator, hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, TypedDict, Annotated
from functools import wraps
from concurrent.futures import ThreadPoolExecutor, as_completed

import tiktoken
from tenacity import (
    retry, stop_after_attempt, wait_exponential,
    retry_if_exception_type, before_sleep_log,
)
from pydantic import BaseModel, Field, field_validator, model_validator
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_core.messages import HumanMessage, SystemMessage

from langgraph.graph import StateGraph, END, START

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance, VectorParams, PointStruct,
)

# Optional: youtube-transcript-api error types
try:
    from youtube_transcript_api._errors import (
        TranscriptsDisabled, NoTranscriptFound, VideoUnavailable,
    )
except ImportError:
    try:
        from youtube_transcript_api import (
            TranscriptsDisabled, NoTranscriptFound, VideoUnavailable,
        )
    except ImportError:
        TranscriptsDisabled = NoTranscriptFound = VideoUnavailable = Exception

# Optional Neo4j
try:
    from neo4j import GraphDatabase
    NEO4J_AVAILABLE = True
except ImportError:
    NEO4J_AVAILABLE = False

print("✅ All imports successful")
print(f"   Neo4j driver available: {NEO4J_AVAILABLE}")
"""))

# ===========================================================================
# CELL 4 — Configuration & Environment
# ===========================================================================
cells.append(code(r"""# ─── Cell 4: Configuration & Environment ─────────────────────────────────────
load_dotenv()

# ── API Keys ──────────────────────────────────────────────────────────────────
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise EnvironmentError(
        "❌ OPENAI_API_KEY not found.\n"
        "   Add it to your .env file:  OPENAI_API_KEY=sk-..."
    )

# ── Optional: Neo4j ───────────────────────────────────────────────────────────
NEO4J_URI      = os.getenv("NEO4J_URI",      "bolt://localhost:7687")
NEO4J_USER     = os.getenv("NEO4J_USER",     "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")

# ── Optional: LangSmith tracing ───────────────────────────────────────────────
LANGSMITH_API_KEY = os.getenv("LANGSMITH_API_KEY")
if LANGSMITH_API_KEY:
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_API_KEY"]    = LANGSMITH_API_KEY
    os.environ["LANGCHAIN_PROJECT"]    = "deep-notes-ai"
    print("✅ LangSmith tracing enabled")
else:
    os.environ["LANGCHAIN_TRACING_V2"] = "false"

# ── Model selection ───────────────────────────────────────────────────────────
MODELS = {
    "extraction": "gpt-4o-mini",          # cheap, fast, JSON-capable
    "reasoning":  "gpt-4o",               # quality consolidation
    "embedding":  "text-embedding-3-small" # best cost/quality ratio
}

# ── Token pricing ($ per token) ───────────────────────────────────────────────
TOKEN_COSTS: Dict[str, Dict[str, float]] = {
    "gpt-4o-mini":            {"input": 0.15  / 1_000_000, "output": 0.60  / 1_000_000},
    "gpt-4o":                 {"input": 2.50  / 1_000_000, "output": 10.00 / 1_000_000},
    "text-embedding-3-small": {"input": 0.02  / 1_000_000, "output": 0.0},
}

# ── Processing constants ──────────────────────────────────────────────────────
MAX_TOKENS_PER_CHUNK    = 6_000   # safe for gpt-4o-mini 128k context
EMBEDDING_BATCH_SIZE    = 100
COSINE_SIM_THRESHOLD    = 0.85    # embedding pre-filter for canonicalization
CANON_LLM_CONFIDENCE    = 0.70    # min LLM confidence to merge topics

# ── Storage paths ─────────────────────────────────────────────────────────────
DB_PATH = Path("./deep_notes.db")

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("deep-notes")

print(f"✅ Configuration loaded")
print(f"   Extraction model : {MODELS['extraction']}")
print(f"   Reasoning model  : {MODELS['reasoning']}")
print(f"   Embedding model  : {MODELS['embedding']}")
print(f"   Database path    : {DB_PATH.resolve()}")
"""))

# ===========================================================================
# CELL 5 — Pydantic Schemas
# ===========================================================================
cells.append(code(r"""# ─── Cell 5: Pydantic v2 Data Schemas ────────────────────────────────────────

class VideoDocument(BaseModel):
    """A YouTube video with its cleaned transcript."""
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
    """One node in the per-video topic hierarchy."""
    topic_id:       str           = Field(default_factory=lambda: str(uuid.uuid4()))
    topic_name:     str           = Field(..., description="Normalised topic name")
    parent_topic_id: Optional[str] = Field(default=None)
    depth:          int           = Field(default=0, ge=0, description="0=root, 1=subtopic…")
    source_video_id: str          = Field(..., description="Video this node came from")
    content:        str           = Field(..., description="Content relevant to this topic")
    canonical_id:   Optional[str] = Field(default=None)
    embedding:      Optional[List[float]] = Field(default=None, exclude=True)

    model_config = {"arbitrary_types_allowed": True}


class TopicTree(BaseModel):
    """Full hierarchy extracted from a single video."""
    video_id:    str                   = Field(...)
    root_topics: List[TopicNode]       = Field(default_factory=list)
    all_nodes:   Dict[str, TopicNode]  = Field(default_factory=dict)


class CanonicalTopic(BaseModel):
    """Unified representation of a topic concept across all videos."""
    canonical_id:     str        = Field(default_factory=lambda: str(uuid.uuid4()))
    canonical_name:   str        = Field(..., description="Representative name")
    aliases:          List[str]  = Field(default_factory=list)
    source_video_ids: List[str]  = Field(default_factory=list)
    merged_topic_ids: List[str]  = Field(default_factory=list)


class MasterTopicDocument(BaseModel):
    """Aggregated, deduplicated content for a canonical topic."""
    canonical_id:     str       = Field(...)
    canonical_name:   str       = Field(...)
    content:          str       = Field(..., description="Aggregated content (markdown)")
    source_video_ids: List[str] = Field(default_factory=list)
    token_count:      int       = Field(default=0)


class TopicSummary(BaseModel):
    """Concise retrieval-optimised summary for a canonical topic."""
    canonical_id:   str       = Field(...)
    canonical_name: str       = Field(...)
    summary:        str       = Field(..., description="Dense summary paragraph")
    key_points:     List[str] = Field(default_factory=list)


# ── LLM Output Schemas ────────────────────────────────────────────────────────

class TopicHierarchyItem(BaseModel):
    """Recursive topic hierarchy item returned by the LLM."""
    name:      str                    = Field(...)
    content:   str                    = Field(default="")
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


# ── LangGraph Pipeline State ──────────────────────────────────────────────────

class PipelineState(TypedDict):
    urls:               List[str]
    video_documents:    List[VideoDocument]
    structured_notes:   Dict[str, str]          # video_id → markdown notes
    topic_trees:        Dict[str, TopicTree]     # video_id → tree
    topic_nodes:        List[TopicNode]
    canonical_topics:   List[CanonicalTopic]
    master_documents:   List[MasterTopicDocument]
    summaries:          List[TopicSummary]
    errors:             List[str]
    current_phase:      str
    processing_complete: bool

print("✅ All Pydantic schemas defined")
"""))

# ===========================================================================
# CELL 6 — SQLite Storage Layer
# ===========================================================================
cells.append(code(r"""# ─── Cell 6: SQLite Storage Layer ────────────────────────────────────────────

class SQLiteStore:
    """
    Primary relational storage layer.
    
    Schema decisions:
    - Aliases & JSON arrays stored as JSON strings (portable to PostgreSQL via JSONB).
    - WAL journal mode for concurrent read performance.
    - Comprehensive indexes on foreign keys and lookup columns.
    - graph_edges table acts as Neo4j fallback adjacency store.
    """

    DDL = """
    PRAGMA journal_mode=WAL;
    PRAGMA foreign_keys=ON;

    CREATE TABLE IF NOT EXISTS videos (
        video_id         TEXT PRIMARY KEY,
        title            TEXT NOT NULL,
        url              TEXT NOT NULL,
        channel          TEXT DEFAULT 'Unknown',
        duration_seconds INTEGER DEFAULT 0,
        transcript       TEXT NOT NULL,
        word_count       INTEGER DEFAULT 0,
        fetched_at       TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS structured_notes (
        video_id         TEXT PRIMARY KEY,
        notes_markdown   TEXT NOT NULL,
        created_at       TEXT NOT NULL,
        FOREIGN KEY (video_id) REFERENCES videos(video_id)
    );

    CREATE TABLE IF NOT EXISTS topic_nodes (
        topic_id         TEXT PRIMARY KEY,
        topic_name       TEXT NOT NULL,
        parent_topic_id  TEXT,
        depth            INTEGER NOT NULL DEFAULT 0,
        source_video_id  TEXT NOT NULL,
        content          TEXT NOT NULL,
        canonical_id     TEXT,
        created_at       TEXT NOT NULL,
        FOREIGN KEY (source_video_id) REFERENCES videos(video_id)
    );

    CREATE TABLE IF NOT EXISTS canonical_topics (
        canonical_id     TEXT PRIMARY KEY,
        canonical_name   TEXT NOT NULL,
        aliases          TEXT NOT NULL DEFAULT '[]',
        source_video_ids TEXT NOT NULL DEFAULT '[]',
        merged_topic_ids TEXT NOT NULL DEFAULT '[]',
        created_at       TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS master_documents (
        canonical_id     TEXT PRIMARY KEY,
        canonical_name   TEXT NOT NULL,
        content          TEXT NOT NULL,
        source_video_ids TEXT NOT NULL DEFAULT '[]',
        token_count      INTEGER DEFAULT 0,
        created_at       TEXT NOT NULL,
        FOREIGN KEY (canonical_id) REFERENCES canonical_topics(canonical_id)
    );

    CREATE TABLE IF NOT EXISTS topic_summaries (
        canonical_id     TEXT PRIMARY KEY,
        canonical_name   TEXT NOT NULL,
        summary          TEXT NOT NULL,
        key_points       TEXT NOT NULL DEFAULT '[]',
        created_at       TEXT NOT NULL,
        FOREIGN KEY (canonical_id) REFERENCES canonical_topics(canonical_id)
    );

    -- Neo4j fallback: adjacency list for the knowledge graph
    CREATE TABLE IF NOT EXISTS graph_edges (
        edge_id      TEXT PRIMARY KEY,
        from_id      TEXT NOT NULL,
        from_type    TEXT NOT NULL,
        to_id        TEXT NOT NULL,
        to_type      TEXT NOT NULL,
        relationship TEXT NOT NULL,
        created_at   TEXT NOT NULL
    );

    CREATE INDEX IF NOT EXISTS idx_topic_nodes_video    ON topic_nodes(source_video_id);
    CREATE INDEX IF NOT EXISTS idx_topic_nodes_canon    ON topic_nodes(canonical_id);
    CREATE INDEX IF NOT EXISTS idx_topic_nodes_parent   ON topic_nodes(parent_topic_id);
    CREATE INDEX IF NOT EXISTS idx_graph_edges_from     ON graph_edges(from_id);
    CREATE INDEX IF NOT EXISTS idx_graph_edges_to       ON graph_edges(to_id);
    CREATE INDEX IF NOT EXISTS idx_graph_edges_rel      ON graph_edges(relationship);
    """

    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._conn() as c:
            c.executescript(self.DDL)
        logger.info("✅ SQLite initialised at %s", self.db_path.resolve())

    # ── Videos ────────────────────────────────────────────────────────────────

    def video_exists(self, video_id: str) -> bool:
        with self._conn() as c:
            return bool(c.execute(
                "SELECT 1 FROM videos WHERE video_id=?", (video_id,)
            ).fetchone())

    def save_video(self, doc: VideoDocument):
        with self._conn() as c:
            c.execute("""
                INSERT OR REPLACE INTO videos
                (video_id,title,url,channel,duration_seconds,transcript,word_count,fetched_at)
                VALUES (?,?,?,?,?,?,?,?)
            """, (doc.video_id, doc.title, doc.url, doc.channel,
                  doc.duration_seconds, doc.transcript, doc.word_count, doc.fetched_at))

    def get_video(self, video_id: str) -> Optional[VideoDocument]:
        with self._conn() as c:
            row = c.execute("SELECT * FROM videos WHERE video_id=?", (video_id,)).fetchone()
        if row:
            return VideoDocument(**{k: row[k] for k in row.keys()})
        return None

    # ── Structured Notes ───────────────────────────────────────────────────────

    def save_structured_notes(self, video_id: str, notes: str):
        with self._conn() as c:
            c.execute("""
                INSERT OR REPLACE INTO structured_notes (video_id,notes_markdown,created_at)
                VALUES (?,?,?)
            """, (video_id, notes, datetime.utcnow().isoformat()))

    def get_structured_notes(self, video_id: str) -> Optional[str]:
        with self._conn() as c:
            row = c.execute(
                "SELECT notes_markdown FROM structured_notes WHERE video_id=?", (video_id,)
            ).fetchone()
        return row["notes_markdown"] if row else None

    # ── Topic Nodes ────────────────────────────────────────────────────────────

    def save_topic_node(self, node: TopicNode):
        with self._conn() as c:
            c.execute("""
                INSERT OR REPLACE INTO topic_nodes
                (topic_id,topic_name,parent_topic_id,depth,source_video_id,content,canonical_id,created_at)
                VALUES (?,?,?,?,?,?,?,?)
            """, (node.topic_id, node.topic_name, node.parent_topic_id, node.depth,
                  node.source_video_id, node.content, node.canonical_id,
                  datetime.utcnow().isoformat()))

    def get_topic_nodes_by_video(self, video_id: str) -> List[TopicNode]:
        with self._conn() as c:
            rows = c.execute(
                "SELECT * FROM topic_nodes WHERE source_video_id=? ORDER BY depth,topic_name",
                (video_id,)
            ).fetchall()
        return [TopicNode(**{k: r[k] for k in r.keys()}) for r in rows]

    def get_all_topic_nodes(self) -> List[TopicNode]:
        with self._conn() as c:
            rows = c.execute("SELECT * FROM topic_nodes ORDER BY depth").fetchall()
        return [TopicNode(**{k: r[k] for k in r.keys()}) for r in rows]

    def update_topic_canonical_id(self, topic_id: str, canonical_id: str):
        with self._conn() as c:
            c.execute(
                "UPDATE topic_nodes SET canonical_id=? WHERE topic_id=?",
                (canonical_id, topic_id)
            )

    # ── Canonical Topics ───────────────────────────────────────────────────────

    def save_canonical_topic(self, ct: CanonicalTopic):
        with self._conn() as c:
            c.execute("""
                INSERT OR REPLACE INTO canonical_topics
                (canonical_id,canonical_name,aliases,source_video_ids,merged_topic_ids,created_at)
                VALUES (?,?,?,?,?,?)
            """, (ct.canonical_id, ct.canonical_name,
                  json.dumps(ct.aliases), json.dumps(ct.source_video_ids),
                  json.dumps(ct.merged_topic_ids), datetime.utcnow().isoformat()))

    def get_all_canonical_topics(self) -> List[CanonicalTopic]:
        with self._conn() as c:
            rows = c.execute("SELECT * FROM canonical_topics").fetchall()
        result = []
        for r in rows:
            result.append(CanonicalTopic(
                canonical_id=r["canonical_id"],
                canonical_name=r["canonical_name"],
                aliases=json.loads(r["aliases"]),
                source_video_ids=json.loads(r["source_video_ids"]),
                merged_topic_ids=json.loads(r["merged_topic_ids"]),
            ))
        return result

    # ── Master Documents ───────────────────────────────────────────────────────

    def save_master_document(self, doc: MasterTopicDocument):
        with self._conn() as c:
            c.execute("""
                INSERT OR REPLACE INTO master_documents
                (canonical_id,canonical_name,content,source_video_ids,token_count,created_at)
                VALUES (?,?,?,?,?,?)
            """, (doc.canonical_id, doc.canonical_name, doc.content,
                  json.dumps(doc.source_video_ids), doc.token_count,
                  datetime.utcnow().isoformat()))

    def get_master_document(self, canonical_id: str) -> Optional[MasterTopicDocument]:
        with self._conn() as c:
            row = c.execute(
                "SELECT * FROM master_documents WHERE canonical_id=?", (canonical_id,)
            ).fetchone()
        if row:
            return MasterTopicDocument(
                canonical_id=row["canonical_id"],
                canonical_name=row["canonical_name"],
                content=row["content"],
                source_video_ids=json.loads(row["source_video_ids"]),
                token_count=row["token_count"],
            )
        return None

    # ── Summaries ──────────────────────────────────────────────────────────────

    def save_topic_summary(self, s: TopicSummary):
        with self._conn() as c:
            c.execute("""
                INSERT OR REPLACE INTO topic_summaries
                (canonical_id,canonical_name,summary,key_points,created_at)
                VALUES (?,?,?,?,?)
            """, (s.canonical_id, s.canonical_name, s.summary,
                  json.dumps(s.key_points), datetime.utcnow().isoformat()))

    def get_topic_summary(self, canonical_id: str) -> Optional[TopicSummary]:
        with self._conn() as c:
            row = c.execute(
                "SELECT * FROM topic_summaries WHERE canonical_id=?", (canonical_id,)
            ).fetchone()
        if row:
            return TopicSummary(
                canonical_id=row["canonical_id"],
                canonical_name=row["canonical_name"],
                summary=row["summary"],
                key_points=json.loads(row["key_points"]),
            )
        return None

    def get_all_summaries(self) -> List[TopicSummary]:
        with self._conn() as c:
            rows = c.execute("SELECT * FROM topic_summaries").fetchall()
        return [TopicSummary(
            canonical_id=r["canonical_id"],
            canonical_name=r["canonical_name"],
            summary=r["summary"],
            key_points=json.loads(r["key_points"]),
        ) for r in rows]

    # ── Graph Edges (Neo4j fallback) ───────────────────────────────────────────

    def save_graph_edge(self, from_id: str, from_type: str, to_id: str,
                        to_type: str, relationship: str):
        with self._conn() as c:
            c.execute("""
                INSERT OR IGNORE INTO graph_edges
                (edge_id,from_id,from_type,to_id,to_type,relationship,created_at)
                VALUES (?,?,?,?,?,?,?)
            """, (str(uuid.uuid4()), from_id, from_type, to_id, to_type,
                  relationship, datetime.utcnow().isoformat()))

    def get_graph_edges(self, node_id: str) -> List[Dict]:
        with self._conn() as c:
            rows = c.execute(
                "SELECT * FROM graph_edges WHERE from_id=? OR to_id=?",
                (node_id, node_id)
            ).fetchall()
        return [dict(r) for r in rows]


# Initialise singleton
sqlite_store = SQLiteStore(DB_PATH)
print("✅ SQLite storage ready")
"""))

# ===========================================================================
# CELL 7 — Neo4j Storage Layer (with graceful fallback)
# ===========================================================================
cells.append(code(r"""# ─── Cell 7: Neo4j Knowledge Graph Store ──────────────────────────────────────
#
# Neo4j is OPTIONAL.  If a connection cannot be established the pipeline
# transparently falls back to the SQLite graph_edges table.
#
# To start Neo4j with Docker (run this in a terminal, NOT the notebook):
#   docker run --rm -d \
#     --name neo4j \
#     -p 7474:7474 -p 7687:7687 \
#     -e NEO4J_AUTH=neo4j/password \
#     neo4j:5-community
#
# Then browse to http://localhost:7474 to inspect the graph.

class Neo4jStore:
    """
    Knowledge graph storage backed by Neo4j.
    All public methods are no-ops when Neo4j is unavailable,
    so the rest of the pipeline does not need to guard on availability.
    
    Relationships modelled:
      (:Video)-[:CONTAINS]->(:Topic)
      (:Topic)-[:HAS_CHILD]->(:Topic)
      (:Topic)-[:MAPS_TO]->(:CanonicalTopic)
      (:CanonicalTopic)-[:RELATED_TO]->(:CanonicalTopic)  [future]
    """

    def __init__(self):
        self.driver = None
        self._available = False
        if NEO4J_AVAILABLE:
            self._connect()

    def _connect(self):
        try:
            self.driver = GraphDatabase.driver(
                NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD)
            )
            self.driver.verify_connectivity()
            self._available = True
            self._create_constraints()
            logger.info("✅ Connected to Neo4j at %s", NEO4J_URI)
        except Exception as exc:
            logger.warning("⚠️  Neo4j unavailable (%s) — using SQLite graph fallback", exc)
            self._available = False
            if self.driver:
                try:
                    self.driver.close()
                except Exception:
                    pass
                self.driver = None

    def _create_constraints(self):
        with self.driver.session() as s:
            for stmt in [
                "CREATE CONSTRAINT IF NOT EXISTS FOR (v:Video)         REQUIRE v.video_id    IS UNIQUE",
                "CREATE CONSTRAINT IF NOT EXISTS FOR (t:Topic)         REQUIRE t.topic_id    IS UNIQUE",
                "CREATE CONSTRAINT IF NOT EXISTS FOR (c:CanonicalTopic) REQUIRE c.canonical_id IS UNIQUE",
            ]:
                s.run(stmt)

    # ── Node creation ──────────────────────────────────────────────────────────

    def create_video_node(self, video: "VideoDocument"):
        if not self._available:
            return
        with self.driver.session() as s:
            s.run("""
                MERGE (v:Video {video_id: $vid})
                SET v.title=$title, v.url=$url, v.channel=$channel
            """, vid=video.video_id, title=video.title,
                 url=video.url, channel=video.channel)

    def create_topic_node(self, node: "TopicNode"):
        if not self._available:
            return
        with self.driver.session() as s:
            s.run("""
                MERGE (t:Topic {topic_id: $tid})
                SET t.topic_name=$name, t.depth=$depth,
                    t.source_video_id=$svid,
                    t.content_preview=$preview
            """, tid=node.topic_id, name=node.topic_name,
                 depth=node.depth, svid=node.source_video_id,
                 preview=node.content[:500])

    def create_canonical_topic_node(self, ct: "CanonicalTopic"):
        if not self._available:
            return
        with self.driver.session() as s:
            s.run("""
                MERGE (c:CanonicalTopic {canonical_id: $cid})
                SET c.canonical_name=$name, c.aliases=$aliases
            """, cid=ct.canonical_id, name=ct.canonical_name,
                 aliases=ct.aliases)

    # ── Relationship creation ──────────────────────────────────────────────────

    def video_contains_topic(self, video_id: str, topic_id: str):
        if not self._available:
            return
        with self.driver.session() as s:
            s.run("""
                MATCH (v:Video {video_id:$vid})
                MATCH (t:Topic {topic_id:$tid})
                MERGE (v)-[:CONTAINS]->(t)
            """, vid=video_id, tid=topic_id)

    def topic_has_child(self, parent_id: str, child_id: str):
        if not self._available:
            return
        with self.driver.session() as s:
            s.run("""
                MATCH (p:Topic {topic_id:$pid})
                MATCH (c:Topic {topic_id:$cid})
                MERGE (p)-[:HAS_CHILD]->(c)
            """, pid=parent_id, cid=child_id)

    def topic_maps_to_canonical(self, topic_id: str, canonical_id: str):
        if not self._available:
            return
        with self.driver.session() as s:
            s.run("""
                MATCH (t:Topic {topic_id:$tid})
                MATCH (c:CanonicalTopic {canonical_id:$cid})
                MERGE (t)-[:MAPS_TO]->(c)
            """, tid=topic_id, cid=canonical_id)

    # ── Queries ────────────────────────────────────────────────────────────────

    def get_topics_for_video(self, video_id: str) -> List[Dict]:
        if not self._available:
            return []
        with self.driver.session() as s:
            res = s.run("""
                MATCH (v:Video {video_id:$vid})-[:CONTAINS]->(t:Topic)
                RETURN t.topic_id AS topic_id, t.topic_name AS topic_name, t.depth AS depth
                ORDER BY t.depth, t.topic_name
            """, vid=video_id)
            return [dict(r) for r in res]

    def get_related_canonical_topics(self, canonical_id: str) -> List[Dict]:
        if not self._available:
            return []
        with self.driver.session() as s:
            res = s.run("""
                MATCH (c:CanonicalTopic {canonical_id:$cid})<-[:MAPS_TO]-(t:Topic)
                      -[:HAS_CHILD|^HAS_CHILD*1..2]-(t2:Topic)
                      -[:MAPS_TO]->(c2:CanonicalTopic)
                WHERE c2.canonical_id <> $cid
                RETURN DISTINCT c2.canonical_id AS canonical_id,
                       c2.canonical_name AS canonical_name
                LIMIT 10
            """, cid=canonical_id)
            return [dict(r) for r in res]

    def close(self):
        if self.driver:
            self.driver.close()


neo4j_store = Neo4jStore()
print(f"✅ Neo4j store initialised (available: {neo4j_store._available})")
if not neo4j_store._available:
    print("   → Graph relationships will be stored in SQLite (graph_edges table)")
"""))

# ===========================================================================
# CELL 8 — Qdrant Vector Store
# ===========================================================================
cells.append(code(r"""# ─── Cell 8: Qdrant Vector Store (in-memory) ─────────────────────────────────
#
# Using QdrantClient(":memory:") — zero infrastructure required.
# To persist to disk: QdrantClient(path="./qdrant_data")
# To use a server: QdrantClient(host="localhost", port=6333)

class QdrantStore:
    """
    In-memory Qdrant vector store for semantic topic search.
    
    Collections:
      topic_embeddings   — canonical topic names + aliases → vector
      summary_embeddings — topic summaries → vector
    """

    TOPIC_COLL   = "topic_embeddings"
    SUMMARY_COLL = "summary_embeddings"
    VECTOR_SIZE  = 1536   # text-embedding-3-small dimensionality

    def __init__(self):
        self.client = QdrantClient(":memory:")
        self._embeddings = OpenAIEmbeddings(
            model=MODELS["embedding"],
            openai_api_key=OPENAI_API_KEY,
        )
        self._init_collections()

    def _init_collections(self):
        existing = {c.name for c in self.client.get_collections().collections}
        for name in [self.TOPIC_COLL, self.SUMMARY_COLL]:
            if name not in existing:
                self.client.create_collection(
                    collection_name=name,
                    vectors_config=VectorParams(
                        size=self.VECTOR_SIZE,
                        distance=Distance.COSINE,
                    ),
                )

    # ── Embedding helpers ──────────────────────────────────────────────────────

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Embed in batches to respect rate limits."""
        result = []
        for i in range(0, len(texts), EMBEDDING_BATCH_SIZE):
            batch = texts[i : i + EMBEDDING_BATCH_SIZE]
            result.extend(self._embeddings.embed_documents(batch))
        return result

    def embed_query(self, text: str) -> List[float]:
        return self._embeddings.embed_query(text)

    # ── Upsert ────────────────────────────────────────────────────────────────

    def upsert_topic(self, canonical_id: str, name: str,
                     aliases: List[str], embedding: List[float]):
        self.client.upsert(
            collection_name=self.TOPIC_COLL,
            points=[PointStruct(
                id=canonical_id,           # Qdrant accepts UUID strings
                vector=embedding,
                payload={"canonical_id": canonical_id,
                         "canonical_name": name,
                         "aliases": aliases},
            )],
        )

    def upsert_summary(self, canonical_id: str, name: str,
                       summary: str, embedding: List[float]):
        self.client.upsert(
            collection_name=self.SUMMARY_COLL,
            points=[PointStruct(
                id=canonical_id,
                vector=embedding,
                payload={"canonical_id": canonical_id,
                         "canonical_name": name,
                         "summary": summary},
            )],
        )

    # ── Search ────────────────────────────────────────────────────────────────

    def search_similar_topics(self, query_vec: List[float],
                               top_k: int = 5) -> List[Dict]:
        hits = self.client.search(
            collection_name=self.TOPIC_COLL,
            query_vector=query_vec,
            limit=top_k,
        )
        return [{"canonical_id":   h.payload["canonical_id"],
                 "canonical_name": h.payload["canonical_name"],
                 "aliases":        h.payload.get("aliases", []),
                 "score":          h.score} for h in hits]

    def search_summaries(self, query_vec: List[float],
                          top_k: int = 5) -> List[Dict]:
        hits = self.client.search(
            collection_name=self.SUMMARY_COLL,
            query_vector=query_vec,
            limit=top_k,
        )
        return [{"canonical_id":   h.payload["canonical_id"],
                 "canonical_name": h.payload["canonical_name"],
                 "summary":        h.payload.get("summary", ""),
                 "score":          h.score} for h in hits]


qdrant_store = QdrantStore()
print("✅ Qdrant in-memory vector store ready")
print(f"   Collections: {[c.name for c in qdrant_store.client.get_collections().collections]}")
"""))

# ===========================================================================
# CELL 9 — Cost Tracker & Token Utilities
# ===========================================================================
cells.append(code(r"""# ─── Cell 9: Cost Tracker & Token Utilities ──────────────────────────────────

class CostTracker:
    """Tracks cumulative token usage and estimated USD cost per model."""

    def __init__(self):
        self._usage: Dict[str, Dict[str, Any]] = {}
        self.total_cost: float = 0.0

    def record(self, model: str, input_tokens: int, output_tokens: int = 0):
        if model not in self._usage:
            self._usage[model] = {"input_tokens": 0, "output_tokens": 0, "cost": 0.0}
        costs = TOKEN_COSTS.get(model, {"input": 0.0, "output": 0.0})
        cost  = input_tokens * costs["input"] + output_tokens * costs.get("output", 0.0)
        self._usage[model]["input_tokens"]  += input_tokens
        self._usage[model]["output_tokens"] += output_tokens
        self._usage[model]["cost"]          += cost
        self.total_cost                     += cost

    def report(self) -> str:
        lines = ["", "╔══════════════════════════════════╗",
                     "║       💰 Cost Report              ║",
                     "╚══════════════════════════════════╝"]
        for model, stats in self._usage.items():
            lines += [
                f"  {model}",
                f"    Input  tokens : {stats['input_tokens']:>10,}",
                f"    Output tokens : {stats['output_tokens']:>10,}",
                f"    Cost          : ${stats['cost']:>10.4f}",
            ]
        lines += ["  " + "─" * 34,
                  f"  Total estimated : ${self.total_cost:>10.4f}", ""]
        return "\n".join(lines)


cost_tracker = CostTracker()


def count_tokens(text: str, model: str = "gpt-4o-mini") -> int:
    """Return token count for text using tiktoken."""
    try:
        enc = tiktoken.encoding_for_model(model)
    except KeyError:
        enc = tiktoken.get_encoding("cl100k_base")
    return len(enc.encode(text, disallowed_special=()))


def chunk_text(text: str,
               max_tokens: int = MAX_TOKENS_PER_CHUNK,
               model: str = "gpt-4o-mini",
               overlap_tokens: int = 150) -> List[str]:
    """
    Split text into overlapping chunks that each fit within max_tokens.
    Overlap preserves cross-boundary context.
    """
    try:
        enc = tiktoken.encoding_for_model(model)
    except KeyError:
        enc = tiktoken.get_encoding("cl100k_base")

    tokens = enc.encode(text, disallowed_special=())
    if len(tokens) <= max_tokens:
        return [text]

    chunks, start = [], 0
    while start < len(tokens):
        end = min(start + max_tokens, len(tokens))
        chunks.append(enc.decode(tokens[start:end]))
        if end >= len(tokens):
            break
        start = end - overlap_tokens

    return chunks


print(f"✅ CostTracker & token utilities ready")
print(f"   Max tokens per chunk : {MAX_TOKENS_PER_CHUNK:,}")
print(f"   Embedding batch size : {EMBEDDING_BATCH_SIZE}")
"""))

# ===========================================================================
# CELL 10 — Middleware: Validation, Retry, Guardrails
# ===========================================================================
cells.append(code(r"""# ─── Cell 10: Middleware ─────────────────────────────────────────────────────

# ── YouTube URL Validation ─────────────────────────────────────────────────────

_YT_PATTERNS = [
    r'(?:https?://)?(?:www\.)?youtube\.com/watch\?(?:.*&)?v=([a-zA-Z0-9_-]{11})',
    r'(?:https?://)?(?:www\.)?youtu\.be/([a-zA-Z0-9_-]{11})',
    r'(?:https?://)?(?:www\.)?youtube\.com/embed/([a-zA-Z0-9_-]{11})',
    r'(?:https?://)?(?:www\.)?youtube\.com/shorts/([a-zA-Z0-9_-]{11})',
    r'(?:https?://)?(?:www\.)?youtube\.com/v/([a-zA-Z0-9_-]{11})',
    r'(?:https?://)?(?:www\.)?youtube\.com/live/([a-zA-Z0-9_-]{11})',
]


def extract_video_id(url: str) -> Optional[str]:
    """Extract 11-character YouTube video ID from any URL format."""
    for pattern in _YT_PATTERNS:
        m = re.search(pattern, url)
        if m:
            return m.group(1)
    return None


def validate_youtube_url(url: str) -> Tuple[bool, str]:
    """
    Validate a YouTube URL.
    Returns (True, video_id) on success, (False, error_message) on failure.
    """
    if not url or not isinstance(url, str):
        return False, "URL must be a non-empty string"
    if len(url) > 500:
        return False, "URL exceeds maximum length (500 chars)"

    url = url.strip()
    # Allow relative-style shortlinks that start with youtu
    if not url.startswith(("http://", "https://", "www.", "youtu")):
        return False, f"Not a recognisable YouTube URL: {url!r}"

    vid = extract_video_id(url)
    if not vid:
        return False, f"Cannot extract video ID from: {url!r}"
    if not re.match(r'^[a-zA-Z0-9_-]{11}$', vid):
        return False, f"Invalid video ID characters: {vid!r}"

    return True, vid


# ── Prompt Injection Guard ─────────────────────────────────────────────────────

_INJECTION_PATTERNS = [
    r'(?i)ignore\s+(all\s+)?previous\s+instructions?',
    r'(?i)forget\s+(all\s+)?previous\s+instructions?',
    r'(?i)\bsystem\s*:\s*',
    r'(?i)\bassistant\s*:\s*',
    r'(?i)you\s+are\s+now\s+',
    r'(?i)disregard\s+(the\s+)?above',
    r'(?i)new\s+instructions?\s*:',
]


def sanitize_for_llm(text: str) -> str:
    """
    Sanitize user-controlled content before embedding in LLM prompts.
    Replaces prompt-injection patterns with [REDACTED].
    """
    for pat in _INJECTION_PATTERNS:
        text = re.sub(pat, '[REDACTED]', text)
    return text


# ── Retry Decorator ────────────────────────────────────────────────────────────

def with_retry(max_attempts: int = 3,
               wait_min: float = 1.0,
               wait_max: float = 30.0,
               reraise: bool = True):
    """
    Decorator: exponential-backoff retry via Tenacity.
    Retries on ANY exception; logs warnings before each sleep.
    """
    def decorator(fn):
        @retry(
            stop=stop_after_attempt(max_attempts),
            wait=wait_exponential(multiplier=1, min=wait_min, max=wait_max),
            before_sleep=before_sleep_log(logger, logging.WARNING),
            reraise=reraise,
        )
        @wraps(fn)
        def wrapper(*args, **kwargs):
            return fn(*args, **kwargs)
        return wrapper
    return decorator


# ── LLM Output Validator ───────────────────────────────────────────────────────

class LLMOutputError(ValueError):
    """Raised when LLM output fails Pydantic validation."""


def parse_llm_json(response_text: str, model_cls: type) -> Any:
    """
    Parse and validate LLM JSON output via Pydantic.
    Attempts two strategies:
      1. Direct json.loads on the full response.
      2. Regex extraction of the first {...} block.
    Raises LLMOutputError on complete failure.
    """
    # Strategy 1: direct parse
    try:
        data = json.loads(response_text)
        return model_cls(**data)
    except (json.JSONDecodeError, Exception):
        pass

    # Strategy 2: extract JSON block
    m = re.search(r'\{.*\}', response_text, re.DOTALL)
    if m:
        try:
            data = json.loads(m.group())
            return model_cls(**data)
        except Exception:
            pass

    raise LLMOutputError(
        f"Cannot parse LLM output as {model_cls.__name__}.\n"
        f"Response (first 500 chars): {response_text[:500]}"
    )


# ── Safe Video Title Fetcher ───────────────────────────────────────────────────

def fetch_video_title(video_id: str) -> str:
    """Fetch video title via a lightweight HTTP request (no API key needed)."""
    import urllib.request, urllib.error
    url     = f"https://www.youtube.com/watch?v={video_id}"
    headers = {"User-Agent": "Mozilla/5.0 (compatible; DeepNotesBot/1.0)"}
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode("utf-8", errors="ignore")

        for pat in [
            r'<title>(.*?) - YouTube</title>',
            r'"og:title"\s+content="([^"]+)"',
            r'"title":"([^"]+)"',
        ]:
            m = re.search(pat, html)
            if m:
                title = m.group(1).strip()
                # Unescape HTML entities
                title = title.replace("&amp;", "&").replace("&#39;", "'") \
                             .replace("&quot;", '"').replace("&lt;", "<") \
                             .replace("&gt;", ">")
                return title
    except Exception as exc:
        logger.debug("Title fetch failed for %s: %s", video_id, exc)
    return f"YouTube Video ({video_id})"


print("✅ Middleware layer ready")
print("   • URL validation")
print("   • Prompt injection sanitisation")
print("   • Tenacity retry decorator")
print("   • Pydantic LLM output validator")
print("   • Video title fetcher")
"""))

# ===========================================================================
# CELL 11 — Prompt Templates
# ===========================================================================
cells.append(code(r"""# ─── Cell 11: Production-Grade Prompt Templates ──────────────────────────────
#
# Design rationale is documented inline for each prompt.

# ── Prompt 1: Transcript → Structured Notes ───────────────────────────────────
#
# Design decisions:
#   • Role-based system framing ("expert knowledge engineer") biases the
#     model toward precise, organised output.
#   • XML-delimited <TRANSCRIPT_CONTENT> prevents injection attacks: the model
#     is explicitly told the block contains raw user content.
#   • Explicit "DO NOT add information not present" guard reduces hallucination.
#   • Prescribed output format (headings list) ensures consistent structure
#     across all videos — critical for downstream topic extraction.

TRANSCRIPT_TO_NOTES_PROMPT = """\
You are an expert knowledge engineer specialising in creating structured study \
materials from video transcripts.

Convert the raw transcript below into comprehensive, well-organised Markdown study notes.

STRICT RULES:
1. Preserve ALL technical information, definitions, examples, and code snippets.
2. Remove conversational filler ("um", "you know", repetitions) and off-topic tangents.
3. Organise content under clear ## headings with logical flow.
4. Bold (**term**) every key definition on first occurrence.
5. Use numbered lists for step-by-step processes; bullet lists for enumerations.
6. Wrap any code in ```language fenced blocks.
7. DO NOT add information, examples, or claims not present in the transcript.
8. DO NOT editorialize or add your own opinions.

REQUIRED OUTPUT STRUCTURE:
# [Descriptive Title]

## Overview
[2–3 sentence executive summary of what this video covers]

## Core Concepts
[Key terms and their definitions]

## [Main Topic A]
[Detailed notes]

## [Main Topic B]
[Detailed notes]

…(as many ## sections as needed)…

## Practical Examples
[Every concrete example or demo from the video]

## Key Takeaways
- [Most important lesson 1]
- …(5–10 bullets)…

<TRANSCRIPT_CONTENT>
{transcript}
</TRANSCRIPT_CONTENT>

Return ONLY the Markdown notes. No preamble, no commentary.\
"""


# ── Prompt 2: Notes → Topic Hierarchy ─────────────────────────────────────────
#
# Design decisions:
#   • Few-shot JSON example anchors the expected output format precisely.
#     Without this, the depth and structure vary wildly across calls.
#   • response_format={"type":"json_object"} (set on the LLM client) guarantees
#     parseable output without needing to strip markdown fences.
#   • "Decompose until no meaningful further subdivision" prevents stopping too
#     early (flat list) or going too deep (atomic sentences as topics).

NOTES_TO_TOPICS_PROMPT = """\
You are a knowledge graph architect. Extract a complete, deeply nested topic hierarchy \
from the study notes below.

RULES:
1. Identify ALL main topics, subtopics, and nested subtopics.
2. Decompose recursively until no meaningful further subdivision exists.
3. Each topic MUST include a "content" field with the relevant excerpt from the notes.
4. Normalise topic names: Title Case, concise (2–5 words preferred).
5. Parent topics must not repeat content already captured in their children.

EXAMPLE OUTPUT (for a LangGraph video):
{{
  "topics": [
    {{
      "name": "LangGraph",
      "content": "LangGraph is a library for building stateful multi-actor LLM applications…",
      "subtopics": [
        {{
          "name": "State Management",
          "content": "State in LangGraph is a TypedDict that holds all shared data…",
          "subtopics": [
            {{
              "name": "State Schema Definition",
              "content": "Define a TypedDict class with typed fields for each state attribute…",
              "subtopics": []
            }}
          ]
        }},
        {{
          "name": "Conditional Edges",
          "content": "Conditional edges route execution based on a Python function…",
          "subtopics": []
        }}
      ]
    }}
  ]
}}

Return ONLY valid JSON. No prose outside the JSON object.

<NOTES>
{notes}
</NOTES>\
"""


# ── Prompt 3: Topic Canonicalization ──────────────────────────────────────────
#
# Design decisions:
#   • Embedding similarity is the primary filter (fast, cheap).
#     LLM is invoked ONLY when cosine similarity ≥ COSINE_SIM_THRESHOLD.
#     This reduces LLM calls by ~80 % in practice.
#   • Confidence field allows the pipeline to ignore uncertain decisions.
#   • Canonical name field eliminates a separate rename pass.
#   • "Representative content" (first 300 chars) gives the LLM context
#     without inflating prompt cost.

CANONICALIZATION_PROMPT = """\
You are a knowledge deduplication expert. Decide whether these two topics represent \
the same underlying concept.

Topic A: {topic_a}
Representative content: {content_a}

Topic B: {topic_b}
Representative content: {content_b}

Consider: same concept if named differently (e.g. "LangGraph State" = "Graph State" = \
"Application State" in a LangGraph tutorial).
Different concept if they cover genuinely distinct ideas (e.g. "State Management" ≠ \
"Conditional Edges").

Return JSON only:
{{
  "are_same": true | false,
  "confidence": <0.0–1.0>,
  "canonical_name": "<best representative name if same; Topic A name if different>",
  "reasoning": "<one sentence>"
}}\
"""


# ── Prompt 4: Topic Aggregation ────────────────────────────────────────────────
#
# Design decisions:
#   • Uses GPT-4o (not mini) because merging multi-source content without
#     hallucinating or silently resolving contradictions requires stronger
#     reasoning.
#   • "DO NOT add information" + "surface contradictions" are the two most
#     critical guardrails for a knowledge-base aggregator.
#   • Source labels (### Source 1) help the model attribute and not homogenise.

AGGREGATION_PROMPT = """\
You are a technical writer specialising in knowledge synthesis for a personal knowledge base.

You have been given {source_count} content piece(s) about the same topic from different \
video sources. Produce ONE comprehensive, authoritative Markdown document.

STRICT RULES:
1. Include ALL unique information present across sources.
2. Remove exact duplicates; keep variant explanations if they add clarity.
3. If sources CONTRADICT each other, include BOTH viewpoints explicitly with a note:
   > ⚠️ Sources disagree: Source 1 says X, Source 2 says Y.
4. Maintain technical precision — do not simplify or paraphrase technical terms.
5. Use clear markdown structure (##, ###, bullets, code blocks).
6. DO NOT invent any information not present in the source material.
7. DO NOT add external knowledge or examples not present in the sources.

Topic: {topic_name}

<SOURCE_DOCUMENTS>
{source_content}
</SOURCE_DOCUMENTS>

Write the comprehensive Markdown document now:\
"""


# ── Prompt 5: Topic Summary ────────────────────────────────────────────────────
#
# Design decisions:
#   • "retrieval-optimised" framing biases the model toward keyword-rich,
#     information-dense prose rather than conversational narrative.
#   • "A student should be able to answer exam questions" is a well-studied
#     prompt framing that dramatically increases factual density.
#   • key_points as a separate list makes summaries scannable and reusable
#     for both full-text and bullet-retrieval use cases.

SUMMARY_PROMPT = """\
You are an expert at creating retrieval-optimised knowledge summaries for a personal \
AI knowledge base.

Write a dense, self-contained summary of the topic below. Requirements:
- A student should be able to answer detailed exam questions using ONLY this summary.
- Include the most important definitions, relationships, and facts.
- Use precise technical language; avoid vague generalities.
- The summary paragraph should be 3–5 sentences.
- The key_points list should have 5–8 specific, actionable insights.

Return JSON only:
{{
  "summary": "<3-5 sentence dense summary paragraph>",
  "key_points": [
    "<specific insight 1>",
    "…"
  ]
}}

Topic: {topic_name}

<CONTENT>
{content}
</CONTENT>\
"""


# ── Prompt 6: Retrieval Answering ──────────────────────────────────────────────
#
# Design decisions:
#   • Ground the answer strictly to the retrieved context to prevent
#     hallucination when used as a RAG response generator.
#   • "If the context does not contain…" instruction prevents confident
#     wrong answers.

RETRIEVAL_ANSWER_PROMPT = """\
You are a knowledgeable assistant for a personal YouTube knowledge base.
Answer the user's question using ONLY the context provided below.

If the context does not contain sufficient information to answer the question,
say "I don't have enough information about this in my knowledge base."
Do NOT use external knowledge.

<CONTEXT>
{context}
</CONTEXT>

Question: {question}

Answer:\
"""

print("✅ All 6 prompt templates defined")
"""))

# ===========================================================================
# CELL 12 — LLM Client Factory
# ===========================================================================
cells.append(code(r"""# ─── Cell 12: LLM Client Factory ─────────────────────────────────────────────

def make_llm(model: str,
             temperature: float = 0.0,
             json_mode: bool = False,
             max_tokens: Optional[int] = None) -> ChatOpenAI:
    """
    Factory that returns a configured ChatOpenAI client.
    
    Args:
        model:       Model name (from MODELS dict or any OpenAI model string).
        temperature: Sampling temperature.  Use 0 for deterministic extraction.
        json_mode:   If True, sets response_format={"type":"json_object"}.
                     The prompt MUST include the word "JSON" when using this.
        max_tokens:  Optional output token cap (cost control).
    """
    kwargs: Dict[str, Any] = {
        "model":          model,
        "temperature":    temperature,
        "openai_api_key": OPENAI_API_KEY,
        "max_retries":    2,
    }
    if json_mode:
        kwargs["model_kwargs"] = {"response_format": {"type": "json_object"}}
    if max_tokens:
        kwargs["max_tokens"] = max_tokens
    return ChatOpenAI(**kwargs)


# Pre-warm clients (validates API key immediately)
_extraction_llm = make_llm(MODELS["extraction"], temperature=0.1)
_json_llm       = make_llm(MODELS["extraction"], temperature=0.0, json_mode=True)
_reasoning_llm  = make_llm(MODELS["reasoning"],  temperature=0.2)

print("✅ LLM clients ready")
print(f"   Extraction : {MODELS['extraction']}")
print(f"   Reasoning  : {MODELS['reasoning']}")
"""))

# ===========================================================================
# CELL 13 — Phase 1: URL Processor + Transcript Extractor
# ===========================================================================
cells.append(code(r"""# ─── Cell 13: Phase 1 — URL Processor & Transcript Extractor ─────────────────

# ── Node 1a: URL Processor ────────────────────────────────────────────────────

def url_processor(state: PipelineState) -> Dict:
    """
    Validate, sanitise, and deduplicate all incoming YouTube URLs.
    Removes invalid URLs from the pipeline with informative error messages.
    """
    logger.info("🔗 [Phase 1a] Processing URLs")
    raw_urls     = state.get("urls", [])
    errors       = list(state.get("errors", []))
    valid_pairs  = []   # (url, video_id)
    seen_ids     = set()

    for raw_url in raw_urls:
        ok, result = validate_youtube_url(raw_url)
        if not ok:
            msg = f"Invalid URL '{raw_url}': {result}"
            errors.append(msg)
            logger.warning("  ❌ %s", msg)
            continue
        video_id = result
        if video_id in seen_ids:
            logger.info("  ⚠️  Duplicate skipped: %s", raw_url)
            continue
        seen_ids.add(video_id)
        valid_pairs.append((raw_url, video_id))
        logger.info("  ✅ Valid URL  →  %s", video_id)

    logger.info("  → %d valid video(s) to process", len(valid_pairs))
    return {
        "urls":          [u for u, _ in valid_pairs],
        "errors":        errors,
        "current_phase": "url_processor_complete",
    }


# ── Transcript fetcher (with retry) ───────────────────────────────────────────

@with_retry(max_attempts=3, wait_min=2, wait_max=20)
def _fetch_transcript_raw(video_id: str) -> str:
    """
    Fetch transcript from YouTube.  Handles both the legacy dict API and
    the new object API introduced in youtube-transcript-api 0.6+.
    """
    from youtube_transcript_api import YouTubeTranscriptApi

    # Try new instance-based API (>=0.6)
    try:
        api = YouTubeTranscriptApi()
        snippet_list = api.fetch(video_id)
        # New API: each item is a TranscriptSnippet with .text
        parts = []
        for s in snippet_list:
            text = s.text if hasattr(s, "text") else s.get("text", "")
            parts.append(text)
        return " ".join(parts)
    except TypeError:
        pass

    # Fallback to class-method API (<0.6)
    transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
    return " ".join(s.get("text", "") for s in transcript_list)


def _clean_transcript(raw: str) -> str:
    """Remove auto-caption artefacts and normalise whitespace."""
    # Strip [Music], [Applause], [Laughter], etc.
    cleaned = re.sub(r'\[[\w\s]+\]', '', raw)
    # Collapse excessive whitespace
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned


# ── Node 1b: Transcript Extractor ─────────────────────────────────────────────

def transcript_extractor(state: PipelineState) -> Dict:
    """
    Fetch, clean, and chunk transcripts for every validated URL.
    Uses SQLite as a transcript cache — re-running the notebook skips
    already-processed videos instantly.
    """
    logger.info("📝 [Phase 1b] Extracting Transcripts")
    urls            = state.get("urls", [])
    errors          = list(state.get("errors", []))
    video_documents = []

    for url in urls:
        ok, video_id = validate_youtube_url(url)
        if not ok:
            continue

        # ── Cache check ────────────────────────────────────────────────────────
        cached = sqlite_store.get_video(video_id)
        if cached:
            logger.info("  💾 Cache hit: %s (%s)", video_id, cached.title)
            cached.transcript_chunks = chunk_text(cached.transcript)
            video_documents.append(cached)
            continue

        # ── Fetch from YouTube ─────────────────────────────────────────────────
        logger.info("  🎬 Fetching transcript: %s", video_id)
        try:
            raw        = _fetch_transcript_raw(video_id)
            transcript = _clean_transcript(raw)
            title      = fetch_video_title(video_id)
            word_count = len(transcript.split())

            doc = VideoDocument(
                video_id         = video_id,
                title            = title,
                url              = url,
                transcript       = transcript,
                word_count       = word_count,
                transcript_chunks= chunk_text(transcript),
            )
            sqlite_store.save_video(doc)
            video_documents.append(doc)
            logger.info("  ✅ %s: %d words, %d chunk(s)",
                        title, word_count, len(doc.transcript_chunks))

        except (TranscriptsDisabled, NoTranscriptFound) as exc:
            msg = f"Transcript unavailable for {video_id}: {exc}"
            errors.append(msg)
            logger.error("  ❌ %s", msg)
        except VideoUnavailable as exc:
            msg = f"Video unavailable: {video_id}: {exc}"
            errors.append(msg)
            logger.error("  ❌ %s", msg)
        except Exception as exc:
            msg = f"Transcript fetch failed for {video_id}: {exc}"
            errors.append(msg)
            logger.error("  ❌ %s", msg)

    logger.info("  → %d video(s) loaded successfully", len(video_documents))
    return {
        "video_documents": video_documents,
        "errors":          errors,
        "current_phase":   "transcript_extractor_complete",
    }


# ── Conditional routing ────────────────────────────────────────────────────────

def _route_after_url_processor(state: PipelineState) -> str:
    if not state.get("urls") and state.get("errors"):
        logger.error("❌ No valid URLs — ending pipeline")
        return END
    return "transcript_extractor"


def _route_after_transcript_extractor(state: PipelineState) -> str:
    if not state.get("video_documents"):
        logger.error("❌ No transcripts available — ending pipeline")
        return END
    return "note_generator"


print("✅ Phase 1 nodes defined: url_processor, transcript_extractor")
"""))

# ===========================================================================
# CELL 14 — Phase 2: Note Generator
# ===========================================================================
cells.append(code(r"""# ─── Cell 14: Phase 2 — Note Generator ───────────────────────────────────────

@with_retry(max_attempts=3, wait_min=2, wait_max=30)
def _call_llm_for_notes(prompt: str, llm: ChatOpenAI) -> str:
    """Single LLM call with retry and cost tracking."""
    in_tok  = count_tokens(prompt)
    resp    = llm.invoke([HumanMessage(content=prompt)])
    out_tok = count_tokens(resp.content)
    cost_tracker.record(MODELS["extraction"], in_tok, out_tok)
    return resp.content


def _generate_notes_for_video(doc: VideoDocument, llm: ChatOpenAI) -> str:
    """
    Generate structured notes for a video.
    For multi-chunk videos, processes each chunk then merges with a second LLM pass.
    """
    if len(doc.transcript_chunks) == 1:
        prompt = TRANSCRIPT_TO_NOTES_PROMPT.format(
            transcript=sanitize_for_llm(doc.transcript_chunks[0])
        )
        return _call_llm_for_notes(prompt, llm)

    # Multi-chunk: process each chunk independently
    chunk_notes = []
    for i, chunk in enumerate(doc.transcript_chunks, 1):
        logger.info("    Chunk %d/%d…", i, len(doc.transcript_chunks))
        prompt = TRANSCRIPT_TO_NOTES_PROMPT.format(
            transcript=sanitize_for_llm(chunk)
        )
        note = _call_llm_for_notes(prompt, llm)
        chunk_notes.append(note)

    # Merge pass — if combined fits in context
    combined = "\n\n---\n\n".join(chunk_notes)
    if count_tokens(combined) < 50_000:
        merge_prompt = (
            "Merge these partial notes from the same video into ONE coherent document.\n"
            "Remove duplications. Preserve all unique information. Unify headings.\n\n"
            "<PARTIAL_NOTES>\n"
            f"{sanitize_for_llm(combined)}\n"
            "</PARTIAL_NOTES>\n\n"
            "Return only the merged Markdown document."
        )
        merged = _call_llm_for_notes(merge_prompt, llm)
        return merged

    # Fallback: simple concatenation if too long to merge
    return combined


def note_generator(state: PipelineState) -> Dict:
    """
    Phase 2: Convert each video's transcript into structured Markdown study notes.
    Results are cached in SQLite — already-generated notes are not regenerated.
    """
    logger.info("📚 [Phase 2] Generating Structured Notes")
    video_documents  = state.get("video_documents", [])
    structured_notes = dict(state.get("structured_notes", {}))
    errors           = list(state.get("errors", []))
    llm              = make_llm(MODELS["extraction"], temperature=0.1)

    for doc in video_documents:
        # Cache check
        cached = sqlite_store.get_structured_notes(doc.video_id)
        if cached:
            logger.info("  💾 Notes cache hit: %s", doc.video_id)
            structured_notes[doc.video_id] = cached
            continue

        logger.info("  ✍️  Generating notes: %s", doc.title)
        try:
            notes = _generate_notes_for_video(doc, llm)
            structured_notes[doc.video_id] = notes
            sqlite_store.save_structured_notes(doc.video_id, notes)
            logger.info("  ✅ Notes: ~%d tokens", count_tokens(notes))
        except Exception as exc:
            msg = f"Note generation failed for {doc.video_id}: {exc}"
            errors.append(msg)
            logger.error("  ❌ %s", msg)

    logger.info("  → Notes ready for %d video(s)", len(structured_notes))
    return {
        "structured_notes": structured_notes,
        "errors":           errors,
        "current_phase":    "note_generator_complete",
    }


print("✅ Phase 2 node defined: note_generator")
"""))

# ===========================================================================
# CELL 15 — Phase 3+4: Topic Extractor + Mapper
# ===========================================================================
cells.append(code(r"""# ─── Cell 15: Phase 3+4 — Topic Extractor & Mapper ──────────────────────────

def _flatten_hierarchy(items: List[Dict],
                       parent_id: Optional[str],
                       video_id: str,
                       depth: int = 0) -> List[TopicNode]:
    """
    Recursively flatten a nested topic hierarchy dict into a flat list of
    TopicNode objects with parent pointers.
    """
    nodes = []
    for item in items:
        node = TopicNode(
            topic_name      = item.get("name", "Unknown"),
            parent_topic_id = parent_id,
            depth           = depth,
            source_video_id = video_id,
            content         = item.get("content", ""),
        )
        nodes.append(node)
        children = item.get("subtopics", [])
        if children:
            nodes.extend(_flatten_hierarchy(children, node.topic_id, video_id, depth + 1))
    return nodes


@with_retry(max_attempts=3, wait_min=2, wait_max=30)
def _extract_hierarchy_for_video(notes: str, video_id: str,
                                  llm: ChatOpenAI) -> List[TopicNode]:
    """
    Single LLM call to extract the topic hierarchy from study notes.
    Returns a flat list of TopicNode objects.
    """
    # Truncate notes if too long (keep first 60 k tokens)
    if count_tokens(notes) > 60_000:
        enc   = tiktoken.encoding_for_model(MODELS["extraction"])
        notes = enc.decode(enc.encode(notes, disallowed_special=())[:60_000])
        logger.warning("  ⚠️  Notes truncated to 60k tokens for %s", video_id)

    prompt   = NOTES_TO_TOPICS_PROMPT.format(notes=sanitize_for_llm(notes))
    in_tok   = count_tokens(prompt)
    response = llm.invoke([HumanMessage(content=prompt)])
    out_tok  = count_tokens(response.content)
    cost_tracker.record(MODELS["extraction"], in_tok, out_tok)

    hierarchy_output = parse_llm_json(response.content, TopicHierarchyOutput)
    raw_topics       = [t.model_dump() for t in hierarchy_output.topics]
    return _flatten_hierarchy(raw_topics, None, video_id, 0)


def topic_extractor(state: PipelineState) -> Dict:
    """
    Phase 3: Extract recursive topic hierarchies from each video's study notes.
    Builds TopicTree objects and a flat list of TopicNodes.
    """
    logger.info("🌳 [Phase 3] Extracting Topic Hierarchies")
    video_documents  = state.get("video_documents", [])
    structured_notes = state.get("structured_notes", {})
    topic_trees      = dict(state.get("topic_trees", {}))
    all_topic_nodes  = list(state.get("topic_nodes", []))
    errors           = list(state.get("errors", []))
    llm              = make_llm(MODELS["extraction"], temperature=0.0, json_mode=True)

    for doc in video_documents:
        notes = structured_notes.get(doc.video_id, "")
        if not notes:
            logger.warning("  ⚠️  No notes for %s — skipping", doc.video_id)
            continue
        logger.info("  🌿 Extracting topics: %s", doc.title)
        try:
            nodes = _extract_hierarchy_for_video(notes, doc.video_id, llm)
            tree  = TopicTree(
                video_id    = doc.video_id,
                root_topics = [n for n in nodes if n.parent_topic_id is None],
                all_nodes   = {n.topic_id: n for n in nodes},
            )
            topic_trees[doc.video_id] = tree
            all_topic_nodes.extend(nodes)
            max_depth = max((n.depth for n in nodes), default=0)
            logger.info("  ✅ %d nodes extracted (max depth: %d)", len(nodes), max_depth)
        except Exception as exc:
            msg = f"Topic extraction failed for {doc.video_id}: {exc}"
            errors.append(msg)
            logger.error("  ❌ %s", msg)

    logger.info("  → %d total topic nodes across all videos", len(all_topic_nodes))
    return {
        "topic_trees":   topic_trees,
        "topic_nodes":   all_topic_nodes,
        "errors":        errors,
        "current_phase": "topic_extractor_complete",
    }


# ── Node: Topic Mapper ────────────────────────────────────────────────────────

def topic_mapper(state: PipelineState) -> Dict:
    """
    Phase 4: Persist all TopicNodes to SQLite.
    Separating persistence from extraction keeps each node single-responsibility.
    """
    logger.info("🗺️  [Phase 4] Persisting Topic Nodes to SQLite")
    topic_nodes = state.get("topic_nodes", [])
    errors      = list(state.get("errors", []))
    saved       = 0

    for node in topic_nodes:
        try:
            sqlite_store.save_topic_node(node)
            saved += 1
        except Exception as exc:
            errors.append(f"Save topic node {node.topic_id}: {exc}")

    logger.info("  ✅ Saved %d/%d nodes", saved, len(topic_nodes))
    return {"errors": errors, "current_phase": "topic_mapper_complete"}


print("✅ Phase 3+4 nodes defined: topic_extractor, topic_mapper")
"""))

# ===========================================================================
# CELL 16 — Phase 5: Topic Canonicalizer
# ===========================================================================
cells.append(code(r"""# ─── Cell 16: Phase 5 — Topic Canonicalizer ──────────────────────────────────
#
# Two-stage deduplication:
#   Stage 1: Embedding cosine similarity  (fast, cheap — filters ~80% of pairs)
#   Stage 2: LLM binary judgment          (accurate — only on candidate pairs)
#
# Union-Find (disjoint-set) groups topics that are determined to be the same.

def _cosine_similarity(a: List[float], b: List[float]) -> float:
    """Exact cosine similarity (no numpy dependency)."""
    dot   = sum(x * y for x, y in zip(a, b))
    mag_a = sum(x * x for x in a) ** 0.5
    mag_b = sum(x * x for x in b) ** 0.5
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)


class UnionFind:
    """Path-compressed union-find for grouping canonical topics."""

    def __init__(self, ids: List[str]):
        self._parent = {i: i for i in ids}

    def find(self, x: str) -> str:
        while self._parent[x] != x:
            self._parent[x] = self._parent[self._parent[x]]  # path compression
            x = self._parent[x]
        return x

    def union(self, x: str, y: str):
        px, py = self.find(x), self.find(y)
        if px != py:
            self._parent[px] = py

    def groups(self) -> Dict[str, List[str]]:
        g: Dict[str, List[str]] = {}
        for item in self._parent:
            root = self.find(item)
            g.setdefault(root, []).append(item)
        return g


@with_retry(max_attempts=2, wait_min=1, wait_max=10)
def _llm_canonicalize(node_a: TopicNode, node_b: TopicNode,
                       llm: ChatOpenAI) -> Optional[CanonicalizationDecision]:
    prompt  = CANONICALIZATION_PROMPT.format(
        topic_a   = node_a.topic_name,
        content_a = sanitize_for_llm(node_a.content[:300]),
        topic_b   = node_b.topic_name,
        content_b = sanitize_for_llm(node_b.content[:300]),
    )
    in_tok  = count_tokens(prompt)
    resp    = llm.invoke([HumanMessage(content=prompt)])
    out_tok = count_tokens(resp.content)
    cost_tracker.record(MODELS["extraction"], in_tok, out_tok)
    return parse_llm_json(resp.content, CanonicalizationDecision)


def topic_canonicalizer(state: PipelineState) -> Dict:
    """
    Phase 5: Detect and merge identical topics across videos.
    Uses embeddings as a pre-filter (cosine ≥ COSINE_SIM_THRESHOLD) then
    validates with LLM before merging.
    """
    logger.info("🔀 [Phase 5] Canonicalising Topics")
    topic_nodes = state.get("topic_nodes", [])
    errors      = list(state.get("errors", []))

    if not topic_nodes:
        logger.warning("  ⚠️  No topic nodes to canonicalise")
        return {"canonical_topics": [], "errors": errors,
                "current_phase": "topic_canonicalizer_complete"}

    # ── Stage 1: Compute embeddings ───────────────────────────────────────────
    logger.info("  🔢 Computing embeddings for %d topics…", len(topic_nodes))
    emb_model  = OpenAIEmbeddings(model=MODELS["embedding"],
                                   openai_api_key=OPENAI_API_KEY)
    texts      = [f"{n.topic_name}: {n.content[:200]}" for n in topic_nodes]
    embeddings = []
    for i in range(0, len(texts), EMBEDDING_BATCH_SIZE):
        batch = texts[i : i + EMBEDDING_BATCH_SIZE]
        embeddings.extend(emb_model.embed_documents(batch))
        cost_tracker.record(MODELS["embedding"],
                            sum(count_tokens(t) for t in batch))

    for node, emb in zip(topic_nodes, embeddings):
        node.embedding = emb

    # ── Stage 2: Union-Find grouping ──────────────────────────────────────────
    uf      = UnionFind([n.topic_id for n in topic_nodes])
    llm     = make_llm(MODELS["extraction"], temperature=0.0, json_mode=True)
    llm_n   = 0
    by_vid: Dict[str, List[TopicNode]] = {}
    for n in topic_nodes:
        by_vid.setdefault(n.source_video_id, []).append(n)

    vid_ids = list(by_vid.keys())
    if len(vid_ids) > 1:
        logger.info("  🔍 Comparing topics across %d videos…", len(vid_ids))
        for i in range(len(vid_ids)):
            for j in range(i + 1, len(vid_ids)):
                for na in by_vid[vid_ids[i]]:
                    for nb in by_vid[vid_ids[j]]:
                        if uf.find(na.topic_id) == uf.find(nb.topic_id):
                            continue
                        sim = _cosine_similarity(na.embedding, nb.embedding)
                        if sim < COSINE_SIM_THRESHOLD:
                            continue
                        # ── LLM validation ────────────────────────────────────
                        try:
                            decision = _llm_canonicalize(na, nb, llm)
                            llm_n += 1
                            if decision and decision.are_same \
                               and decision.confidence >= CANON_LLM_CONFIDENCE:
                                uf.union(na.topic_id, nb.topic_id)
                                logger.info(
                                    "    🔗 Merged: '%s' ↔ '%s' (sim=%.2f conf=%.2f)",
                                    na.topic_name, nb.topic_name,
                                    sim, decision.confidence,
                                )
                        except Exception as exc:
                            logger.warning("    ⚠️  Canonicalization LLM error: %s", exc)

    logger.info("  📊 LLM calls: %d (embedding pre-filter active)", llm_n)

    # ── Build CanonicalTopic objects ──────────────────────────────────────────
    groups          = uf.groups()  # root_id → [topic_ids]
    id_to_node      = {n.topic_id: n for n in topic_nodes}
    canonical_topics: List[CanonicalTopic] = []

    for root_id, topic_ids in groups.items():
        group_nodes = [id_to_node[tid] for tid in topic_ids if tid in id_to_node]
        names       = [n.topic_name for n in group_nodes]

        # Choose canonical name: most frequent, tie-break by length (longer = clearer)
        freq = {}
        for nm in names:
            freq[nm] = freq.get(nm, 0) + 1
        canonical_name = max(freq, key=lambda k: (freq[k], len(k)))

        ct = CanonicalTopic(
            canonical_name   = canonical_name,
            aliases          = list(set(names)),
            source_video_ids = list({n.source_video_id for n in group_nodes}),
            merged_topic_ids = [n.topic_id for n in group_nodes],
        )

        # Update nodes with canonical_id
        for node in group_nodes:
            node.canonical_id = ct.canonical_id
            sqlite_store.update_topic_canonical_id(node.topic_id, ct.canonical_id)

        sqlite_store.save_canonical_topic(ct)

        # Upsert mean embedding into Qdrant
        valid_embs = [n.embedding for n in group_nodes if n.embedding]
        if valid_embs:
            mean_emb = [
                sum(row[k] for row in valid_embs) / len(valid_embs)
                for k in range(len(valid_embs[0]))
            ]
            try:
                qdrant_store.upsert_topic(ct.canonical_id, ct.canonical_name,
                                          ct.aliases, mean_emb)
            except Exception as exc:
                logger.warning("  Qdrant upsert skipped: %s", exc)

        canonical_topics.append(ct)

    merged_count = len(topic_nodes) - len(canonical_topics)
    logger.info("  ✅ %d canonical topics (%d merged)", len(canonical_topics), merged_count)

    return {
        "topic_nodes":      topic_nodes,
        "canonical_topics": canonical_topics,
        "errors":           errors,
        "current_phase":    "topic_canonicalizer_complete",
    }


print("✅ Phase 5 node defined: topic_canonicalizer")
"""))

# ===========================================================================
# CELL 17 — Phase 6: Knowledge Graph Writer
# ===========================================================================
cells.append(code(r"""# ─── Cell 17: Phase 6 — Knowledge Graph Writer ───────────────────────────────

def graph_writer_node(state: PipelineState) -> Dict:
    """
    Phase 6: Write the knowledge graph to Neo4j (if available) or to the
    SQLite graph_edges adjacency table as a transparent fallback.
    
    Relationships written:
      (:Video)-[:CONTAINS]->(:Topic)
      (:Topic)-[:HAS_CHILD]->(:Topic)
      (:Topic)-[:MAPS_TO]->(:CanonicalTopic)
    """
    logger.info("🕸️  [Phase 6] Writing Knowledge Graph")
    video_documents  = state.get("video_documents", [])
    topic_nodes      = state.get("topic_nodes", [])
    canonical_topics = state.get("canonical_topics", [])
    errors           = list(state.get("errors", []))
    use_neo4j        = neo4j_store._available

    backend = "Neo4j" if use_neo4j else "SQLite adjacency table"
    logger.info("  📊 Backend: %s", backend)

    # ── Write video nodes ─────────────────────────────────────────────────────
    for video in video_documents:
        if use_neo4j:
            try:
                neo4j_store.create_video_node(video)
            except Exception as exc:
                errors.append(f"Neo4j video node: {exc}")

    # ── Write topic nodes + CONTAINS + HAS_CHILD edges ────────────────────────
    for node in topic_nodes:
        if use_neo4j:
            try:
                neo4j_store.create_topic_node(node)
                neo4j_store.video_contains_topic(node.source_video_id, node.topic_id)
            except Exception as exc:
                errors.append(f"Neo4j topic node/CONTAINS: {exc}")
        else:
            sqlite_store.save_graph_edge(
                node.source_video_id, "Video",
                node.topic_id,        "Topic",
                "CONTAINS",
            )

        if node.parent_topic_id:
            if use_neo4j:
                try:
                    neo4j_store.topic_has_child(node.parent_topic_id, node.topic_id)
                except Exception as exc:
                    errors.append(f"Neo4j HAS_CHILD: {exc}")
            else:
                sqlite_store.save_graph_edge(
                    node.parent_topic_id, "Topic",
                    node.topic_id,        "Topic",
                    "HAS_CHILD",
                )

    # ── Write canonical topics + MAPS_TO edges ────────────────────────────────
    for ct in canonical_topics:
        if use_neo4j:
            try:
                neo4j_store.create_canonical_topic_node(ct)
            except Exception as exc:
                errors.append(f"Neo4j CanonicalTopic node: {exc}")

        for tid in ct.merged_topic_ids:
            if use_neo4j:
                try:
                    neo4j_store.topic_maps_to_canonical(tid, ct.canonical_id)
                except Exception as exc:
                    errors.append(f"Neo4j MAPS_TO: {exc}")
            else:
                sqlite_store.save_graph_edge(
                    tid,             "Topic",
                    ct.canonical_id, "CanonicalTopic",
                    "MAPS_TO",
                )

    logger.info(
        "  ✅ Graph written: %d videos, %d topics, %d canonical topics",
        len(video_documents), len(topic_nodes), len(canonical_topics),
    )
    return {"errors": errors, "current_phase": "graph_writer_complete"}


print("✅ Phase 6 node defined: graph_writer_node")
"""))

# ===========================================================================
# CELL 18 — Phase 7: Topic Aggregator
# ===========================================================================
cells.append(code(r"""# ─── Cell 18: Phase 7 — Topic Aggregator ────────────────────────────────────

@with_retry(max_attempts=2, wait_min=2, wait_max=30)
def _aggregate_with_llm(topic_name: str,
                         source_content: str,
                         source_count: int,
                         llm: ChatOpenAI) -> str:
    """Single GPT-4o call to aggregate multi-source content."""
    prompt  = AGGREGATION_PROMPT.format(
        topic_name     = topic_name,
        source_count   = source_count,
        source_content = sanitize_for_llm(source_content),
    )
    in_tok  = count_tokens(prompt)
    resp    = llm.invoke([HumanMessage(content=prompt)])
    out_tok = count_tokens(resp.content)
    cost_tracker.record(MODELS["reasoning"], in_tok, out_tok)
    return resp.content


def topic_aggregator(state: PipelineState) -> Dict:
    """
    Phase 7: Aggregate content across videos for each canonical topic.
    
    Single-source topics are passed through without an LLM call (cost saving).
    Multi-source topics use GPT-4o for quality synthesis.
    """
    logger.info("🔄 [Phase 7] Aggregating Topic Content")
    canonical_topics = state.get("canonical_topics", [])
    topic_nodes      = state.get("topic_nodes", [])
    errors           = list(state.get("errors", []))

    # Build lookup: canonical_id → [TopicNode]
    by_canon: Dict[str, List[TopicNode]] = {}
    for n in topic_nodes:
        if n.canonical_id:
            by_canon.setdefault(n.canonical_id, []).append(n)

    llm            = make_llm(MODELS["reasoning"], temperature=0.2)
    master_docs: List[MasterTopicDocument] = []
    enc            = tiktoken.encoding_for_model(MODELS["reasoning"])

    for ct in canonical_topics:
        group = by_canon.get(ct.canonical_id, [])
        if not group:
            continue

        # ── Single source: pass-through ───────────────────────────────────────
        if len(group) == 1:
            n = group[0]
            doc = MasterTopicDocument(
                canonical_id     = ct.canonical_id,
                canonical_name   = ct.canonical_name,
                content          = n.content,
                source_video_ids = [n.source_video_id],
                token_count      = count_tokens(n.content),
            )
            sqlite_store.save_master_document(doc)
            master_docs.append(doc)
            continue

        # ── Multi-source: LLM aggregation ─────────────────────────────────────
        logger.info("  🔀 Aggregating: '%s' (%d sources)", ct.canonical_name, len(group))

        # Build source block (truncate each proportionally if needed)
        MAX_SRC_TOKENS = 80_000
        total_content  = sum(count_tokens(n.content) for n in group)
        parts          = []
        for i, n in enumerate(group, 1):
            content = n.content
            if total_content > MAX_SRC_TOKENS:
                max_for_node = MAX_SRC_TOKENS // len(group)
                toks = enc.encode(content, disallowed_special=())
                if len(toks) > max_for_node:
                    content = enc.decode(toks[:max_for_node]) + "\n…[truncated]"
            parts.append(f"### Source {i} (video: {n.source_video_id})\n{content}")

        source_content = "\n\n---\n\n".join(parts)

        try:
            aggregated = _aggregate_with_llm(
                ct.canonical_name, source_content, len(group), llm
            )
            doc = MasterTopicDocument(
                canonical_id     = ct.canonical_id,
                canonical_name   = ct.canonical_name,
                content          = aggregated,
                source_video_ids = ct.source_video_ids,
                token_count      = count_tokens(aggregated),
            )
        except Exception as exc:
            # Graceful fallback: concatenate without LLM
            fallback = f"# {ct.canonical_name}\n\n{source_content}"
            doc = MasterTopicDocument(
                canonical_id     = ct.canonical_id,
                canonical_name   = ct.canonical_name,
                content          = fallback,
                source_video_ids = ct.source_video_ids,
                token_count      = count_tokens(fallback),
            )
            errors.append(f"Aggregation LLM failed for '{ct.canonical_name}': {exc}")
            logger.error("  ❌ Aggregation fallback used for '%s'", ct.canonical_name)

        sqlite_store.save_master_document(doc)
        master_docs.append(doc)

    logger.info("  ✅ Created %d master documents", len(master_docs))
    return {
        "master_documents": master_docs,
        "errors":           errors,
        "current_phase":    "topic_aggregator_complete",
    }


print("✅ Phase 7 node defined: topic_aggregator")
"""))

# ===========================================================================
# CELL 19 — Phase 8: Summary Generator
# ===========================================================================
cells.append(code(r"""# ─── Cell 19: Phase 8 — Summary Generator ────────────────────────────────────

@with_retry(max_attempts=3, wait_min=2, wait_max=20)
def _generate_single_summary(topic_name: str,
                               content: str,
                               llm: ChatOpenAI) -> TopicSummaryOutput:
    """Single LLM call for one topic summary. Tracked for cost."""
    # Truncate content to 30k tokens to stay within context
    if count_tokens(content) > 30_000:
        enc     = tiktoken.encoding_for_model(MODELS["extraction"])
        content = enc.decode(
            enc.encode(content, disallowed_special=())[:30_000]
        ) + "\n…[content truncated for summary]"

    prompt  = SUMMARY_PROMPT.format(
        topic_name = topic_name,
        content    = sanitize_for_llm(content),
    )
    in_tok  = count_tokens(prompt)
    resp    = llm.invoke([HumanMessage(content=prompt)])
    out_tok = count_tokens(resp.content)
    cost_tracker.record(MODELS["extraction"], in_tok, out_tok)
    return parse_llm_json(resp.content, TopicSummaryOutput)


def summary_generator_node(state: PipelineState) -> Dict:
    """
    Phase 8: Generate concise, retrieval-optimised summaries for every
    canonical topic.  Summaries are stored in SQLite and their embeddings
    are upserted into Qdrant for semantic search.
    """
    logger.info("📝 [Phase 8] Generating Topic Summaries")
    master_documents = state.get("master_documents", [])
    errors           = list(state.get("errors", []))
    llm              = make_llm(MODELS["extraction"], temperature=0.1, json_mode=True)
    emb_model        = OpenAIEmbeddings(model=MODELS["embedding"],
                                        openai_api_key=OPENAI_API_KEY)
    summaries: List[TopicSummary] = []

    for doc in master_documents:
        try:
            out = _generate_single_summary(doc.canonical_name, doc.content, llm)
            summary = TopicSummary(
                canonical_id   = doc.canonical_id,
                canonical_name = doc.canonical_name,
                summary        = out.summary,
                key_points     = out.key_points,
            )
            sqlite_store.save_topic_summary(summary)
            summaries.append(summary)

            # Embed summary and upsert into Qdrant
            summary_text = f"{doc.canonical_name}: {out.summary}"
            try:
                emb = emb_model.embed_documents([summary_text])[0]
                cost_tracker.record(MODELS["embedding"], count_tokens(summary_text))
                qdrant_store.upsert_summary(
                    doc.canonical_id, doc.canonical_name, out.summary, emb
                )
            except Exception as exc:
                logger.warning("  Qdrant summary upsert failed: %s", exc)

            logger.info("  ✅ '%s' — %d key points", doc.canonical_name,
                        len(out.key_points))

        except Exception as exc:
            msg = f"Summary failed for '{doc.canonical_name}': {exc}"
            errors.append(msg)
            logger.error("  ❌ %s", msg)

    logger.info("  ✅ Generated %d summaries", len(summaries))
    return {
        "summaries":          summaries,
        "errors":             errors,
        "current_phase":      "pipeline_complete",
        "processing_complete": True,
    }


print("✅ Phase 8 node defined: summary_generator_node")
"""))

# ===========================================================================
# CELL 20 — LangGraph StateGraph Assembly + Diagram
# ===========================================================================
cells.append(code(r"""# ─── Cell 20: LangGraph StateGraph Assembly ──────────────────────────────────

builder = StateGraph(PipelineState)

# ── Add all nodes ─────────────────────────────────────────────────────────────
builder.add_node("url_processor",        url_processor)
builder.add_node("transcript_extractor", transcript_extractor)
builder.add_node("note_generator",       note_generator)
builder.add_node("topic_extractor",      topic_extractor)
builder.add_node("topic_mapper",         topic_mapper)
builder.add_node("topic_canonicalizer",  topic_canonicalizer)
builder.add_node("graph_writer",         graph_writer_node)
builder.add_node("topic_aggregator",     topic_aggregator)
builder.add_node("summary_generator",    summary_generator_node)

# ── Entry point ───────────────────────────────────────────────────────────────
builder.add_edge(START, "url_processor")

# ── Conditional routing: bail out early on no valid input ─────────────────────
builder.add_conditional_edges(
    "url_processor",
    _route_after_url_processor,
    {"transcript_extractor": "transcript_extractor", END: END},
)
builder.add_conditional_edges(
    "transcript_extractor",
    _route_after_transcript_extractor,
    {"note_generator": "note_generator", END: END},
)

# ── Sequential pipeline ───────────────────────────────────────────────────────
builder.add_edge("note_generator",      "topic_extractor")
builder.add_edge("topic_extractor",     "topic_mapper")
builder.add_edge("topic_mapper",        "topic_canonicalizer")
builder.add_edge("topic_canonicalizer", "graph_writer")
builder.add_edge("graph_writer",        "topic_aggregator")
builder.add_edge("topic_aggregator",    "summary_generator")
builder.add_edge("summary_generator",   END)

# ── Compile ───────────────────────────────────────────────────────────────────
pipeline = builder.compile()

print("✅ LangGraph pipeline compiled")
print()

# ── Display graph diagram ─────────────────────────────────────────────────────
try:
    from IPython.display import Image, display
    img_bytes = pipeline.get_graph().draw_mermaid_png()
    display(Image(img_bytes))
    print("📊 Pipeline graph rendered above")
except Exception:
    # Fallback: print Mermaid source
    print("📊 Pipeline Mermaid diagram:")
    print(pipeline.get_graph().draw_mermaid())
"""))

# ===========================================================================
# CELL 21 — Retrieval & Query Layer
# ===========================================================================
cells.append(code(r"""# ─── Cell 21: Retrieval & Query Layer (Phase 9 + Phase 14) ──────────────────

# ── Internal: find canonical topic by name ────────────────────────────────────

def _find_canonical_topic(topic_name: str) -> Optional[CanonicalTopic]:
    """
    Multi-strategy lookup:
      1. Exact canonical name match (case-insensitive)
      2. Alias match
      3. Partial substring match
      4. Vector similarity (Qdrant) — fallback
    Returns None if no match found.
    """
    all_ct = sqlite_store.get_all_canonical_topics()
    lower  = topic_name.strip().lower()

    # Strategy 1: exact name
    for ct in all_ct:
        if ct.canonical_name.lower() == lower:
            return ct

    # Strategy 2: alias
    for ct in all_ct:
        if any(a.lower() == lower for a in ct.aliases):
            return ct

    # Strategy 3: partial name
    for ct in all_ct:
        if lower in ct.canonical_name.lower():
            return ct

    # Strategy 4: vector similarity
    try:
        emb_model = OpenAIEmbeddings(model=MODELS["embedding"],
                                      openai_api_key=OPENAI_API_KEY)
        query_emb = emb_model.embed_query(topic_name)
        cost_tracker.record(MODELS["embedding"], count_tokens(topic_name))
        hits = qdrant_store.search_similar_topics(query_emb, top_k=1)
        if hits and hits[0]["score"] >= 0.70:
            cid = hits[0]["canonical_id"]
            for ct in all_ct:
                if ct.canonical_id == cid:
                    return ct
    except Exception as exc:
        logger.warning("Vector search failed: %s", exc)

    return None


# ── query_video ───────────────────────────────────────────────────────────────

def query_video(video_id: str) -> Dict[str, Any]:
    """
    Return all knowledge associated with a specific video.
    
    Includes:
      - Video metadata
      - Structured study notes (full Markdown)
      - Topic hierarchy in original video order
      - Canonical topic IDs for each topic (cross-reference to query_topic)
    """
    video = sqlite_store.get_video(video_id)
    if not video:
        return {"error": f"Video '{video_id}' not found in knowledge base."}

    notes   = sqlite_store.get_structured_notes(video_id)
    t_nodes = sqlite_store.get_topic_nodes_by_video(video_id)

    # Build topic hierarchy for display
    def _build_tree(node: TopicNode) -> Dict:
        children = [n for n in t_nodes if n.parent_topic_id == node.topic_id]
        return {
            "topic":           node.topic_name,
            "depth":           node.depth,
            "canonical_id":    node.canonical_id,
            "content_preview": (node.content[:300] + "…")
                               if len(node.content) > 300 else node.content,
            "subtopics":       [_build_tree(c) for c in children],
        }

    root_nodes = [n for n in t_nodes if n.parent_topic_id is None]
    return {
        "video_id":        video_id,
        "title":           video.title,
        "url":             video.url,
        "channel":         video.channel,
        "word_count":      video.word_count,
        "fetched_at":      video.fetched_at,
        "structured_notes": notes,
        "topic_hierarchy": [_build_tree(r) for r in root_nodes],
        "total_topics":    len(t_nodes),
    }


# ── query_topic ───────────────────────────────────────────────────────────────

def query_topic(topic_name: str) -> Dict[str, Any]:
    """
    Return the consolidated knowledge document for a topic concept.
    
    Searches by: exact name → alias → partial match → vector similarity.
    Returns full aggregated Markdown content + summary + key points.
    """
    ct = _find_canonical_topic(topic_name)
    if not ct:
        all_names = [c.canonical_name for c in sqlite_store.get_all_canonical_topics()]
        return {
            "error": f"Topic '{topic_name}' not found.",
            "available_topics": all_names[:20],
        }

    master = sqlite_store.get_master_document(ct.canonical_id)
    summ   = sqlite_store.get_topic_summary(ct.canonical_id)
    edges  = sqlite_store.get_graph_edges(ct.canonical_id)

    return {
        "canonical_id":     ct.canonical_id,
        "canonical_name":   ct.canonical_name,
        "aliases":          ct.aliases,
        "source_video_ids": ct.source_video_ids,
        "content":          master.content if master else "No aggregated content yet.",
        "token_count":      master.token_count if master else 0,
        "summary":          summ.summary if summ else None,
        "key_points":       summ.key_points if summ else [],
        "graph_edges":      edges[:10],   # first 10 for preview
    }


# ── query_topic_summary ───────────────────────────────────────────────────────

def query_topic_summary(topic_name: str) -> str:
    """
    Return a concise, formatted summary for a topic — optimised for quick retrieval.
    This is the lightest-weight query; suitable for API responses or UI tooltips.
    """
    result = query_topic(topic_name)
    if "error" in result:
        return f"⚠️  {result['error']}"

    name       = result["canonical_name"]
    summary    = result.get("summary", "")
    key_points = result.get("key_points", [])
    aliases    = result.get("aliases", [])
    sources    = result.get("source_video_ids", [])

    if not summary:
        return f"No summary available for '{name}'."

    lines = [f"## {name}", "", summary, ""]
    if key_points:
        lines.append("**Key Points:**")
        for p in key_points:
            lines.append(f"- {p}")
        lines.append("")
    if len(aliases) > 1:
        other = [a for a in aliases if a != name]
        lines.append(f"*Also known as: {', '.join(other[:5])}*")
    lines.append(f"*Covered in {len(sources)} video(s)*")

    return "\n".join(lines)


# ── list_all_topics ───────────────────────────────────────────────────────────

def list_all_topics() -> List[Dict]:
    """Return a sorted list of all canonical topics in the knowledge base."""
    all_ct       = sqlite_store.get_all_canonical_topics()
    summ_by_id   = {s.canonical_id: s for s in sqlite_store.get_all_summaries()}
    result       = []
    for ct in all_ct:
        s        = summ_by_id.get(ct.canonical_id)
        preview  = (s.summary[:120] + "…") if s and len(s.summary) > 120 else (s.summary if s else "")
        result.append({
            "canonical_name":  ct.canonical_name,
            "aliases":         ct.aliases,
            "source_count":    len(ct.source_video_ids),
            "summary_preview": preview,
        })
    return sorted(result, key=lambda x: x["canonical_name"])


# ── search_topics_semantic ────────────────────────────────────────────────────

def search_topics_semantic(query: str, top_k: int = 5) -> List[Dict]:
    """
    Semantic search across all topic summaries using Qdrant.
    Returns the top-k most relevant topics for a natural language query.
    """
    try:
        emb_model = OpenAIEmbeddings(model=MODELS["embedding"],
                                      openai_api_key=OPENAI_API_KEY)
        q_emb     = emb_model.embed_query(query)
        cost_tracker.record(MODELS["embedding"], count_tokens(query))
        return qdrant_store.search_summaries(q_emb, top_k=top_k)
    except Exception as exc:
        logger.error("Semantic search error: %s", exc)
        return []


# ── ask_knowledge_base ────────────────────────────────────────────────────────

def ask_knowledge_base(question: str, top_k: int = 3) -> str:
    """
    RAG-style Q&A: retrieve relevant topic summaries, then generate an answer.
    Uses RETRIEVAL_ANSWER_PROMPT with GPT-4o for high-quality responses.
    """
    hits = search_topics_semantic(question, top_k=top_k)
    if not hits:
        return "No relevant topics found in the knowledge base."

    context_parts = []
    for h in hits:
        ct = _find_canonical_topic(h["canonical_name"])
        if ct:
            md = sqlite_store.get_master_document(ct.canonical_id)
            if md:
                context_parts.append(
                    f"### {ct.canonical_name}\n"
                    f"{md.content[:1500]}{'…' if len(md.content) > 1500 else ''}"
                )

    if not context_parts:
        return "Could not retrieve content for matched topics."

    context = "\n\n---\n\n".join(context_parts)
    prompt  = RETRIEVAL_ANSWER_PROMPT.format(context=context, question=question)
    in_tok  = count_tokens(prompt)
    llm     = make_llm(MODELS["reasoning"], temperature=0.1)
    resp    = llm.invoke([HumanMessage(content=prompt)])
    out_tok = count_tokens(resp.content)
    cost_tracker.record(MODELS["reasoning"], in_tok, out_tok)
    return resp.content


print("✅ Query layer ready:")
print("   query_video(video_id)              → full video knowledge")
print("   query_topic(topic_name)            → consolidated topic document")
print("   query_topic_summary(topic_name)    → concise formatted summary")
print("   list_all_topics()                  → all topics in knowledge base")
print("   search_topics_semantic(query)      → vector similarity search")
print("   ask_knowledge_base(question)       → RAG Q&A answer")
"""))

# ===========================================================================
# CELL 22 — End-to-End Demo Execution
# ===========================================================================
cells.append(code(r"""# ─── Cell 22: End-to-End Demo ────────────────────────────────────────────────
#
# ┌──────────────────────────────────────────────────────────────────┐
# │ Replace the URLs below with any YouTube videos you want to index │
# └──────────────────────────────────────────────────────────────────┘

DEMO_URLS = [
    # Two videos covering LangGraph — canonical topic merging will be demonstrated
    "https://www.youtube.com/watch?v=sFHolMMYF5c",  # LangGraph tutorial
    "https://www.youtube.com/watch?v=lvQ96Ssesfk",  # LangGraph agents deep-dive
]

print("╔══════════════════════════════════════════════════════════════╗")
print("║          🧠 Deep Notes AI — Pipeline Execution               ║")
print("╚══════════════════════════════════════════════════════════════╝")
print(f"\nProcessing {len(DEMO_URLS)} video(s):")
for u in DEMO_URLS:
    print(f"  • {u}")
print()

initial_state: PipelineState = {
    "urls":               DEMO_URLS,
    "video_documents":    [],
    "structured_notes":   {},
    "topic_trees":        {},
    "topic_nodes":        [],
    "canonical_topics":   [],
    "master_documents":   [],
    "summaries":          [],
    "errors":             [],
    "current_phase":      "initialised",
    "processing_complete": False,
}

# ── Run the pipeline ──────────────────────────────────────────────────────────
final_state = pipeline.invoke(initial_state, {"recursion_limit": 100})

# ── Results summary ───────────────────────────────────────────────────────────
print("\n" + "═" * 62)
print("✅ Pipeline complete!")
print(f"   Videos processed    : {len(final_state['video_documents'])}")
print(f"   Topic nodes         : {len(final_state['topic_nodes'])}")
print(f"   Canonical topics    : {len(final_state['canonical_topics'])}")
print(f"   Master documents    : {len(final_state['master_documents'])}")
print(f"   Summaries generated : {len(final_state['summaries'])}")

if final_state.get("errors"):
    print(f"\n⚠️  Warnings / Errors ({len(final_state['errors'])}):")
    for e in final_state["errors"][:5]:
        print(f"   • {e}")
    if len(final_state["errors"]) > 5:
        print(f"   … and {len(final_state['errors'])-5} more")

print(cost_tracker.report())
"""))

# ===========================================================================
# CELL 23 — Query Examples & Results
# ===========================================================================
cells.append(code(r"""# ─── Cell 23: Query Examples ─────────────────────────────────────────────────

SEP = "═" * 62

# ══════════════════════════════════════════════════════════════
# Example 1: Query by video — get full video knowledge
# ══════════════════════════════════════════════════════════════
print(SEP)
print("📹  QUERY 1: query_video()")
print(SEP)

if final_state["video_documents"]:
    vid_id = final_state["video_documents"][0].video_id
    result = query_video(vid_id)

    print(f"Title      : {result['title']}")
    print(f"Video ID   : {result['video_id']}")
    print(f"Word count : {result['word_count']:,}")
    print(f"Topics     : {result['total_topics']}")
    print()
    print("Topic Hierarchy (first 4 roots, up to 2 children each):")
    for root in result["topic_hierarchy"][:4]:
        print(f"  📌 {root['topic']}")
        for child in root["subtopics"][:2]:
            print(f"      └── {child['topic']}")
            for grandchild in child["subtopics"][:1]:
                print(f"              └── {grandchild['topic']}")
    print()
    if result.get("structured_notes"):
        print("Structured Notes Preview (first 600 chars):")
        print(result["structured_notes"][:600] + "…")
else:
    print("No videos in final state.")

# ══════════════════════════════════════════════════════════════
# Example 2: List all topics
# ══════════════════════════════════════════════════════════════
print()
print(SEP)
print("📚  QUERY 2: list_all_topics()")
print(SEP)

topics = list_all_topics()
print(f"Total canonical topics in knowledge base: {len(topics)}\n")
for t in topics[:15]:
    aliases_str = (", ".join(t["aliases"][:2])
                   if len(t["aliases"]) > 1 else "")
    alias_note  = f"  [also: {aliases_str}]" if aliases_str else ""
    print(f"  • {t['canonical_name']}{alias_note}")
    if t["summary_preview"]:
        print(f"    {t['summary_preview']}")

if len(topics) > 15:
    print(f"  … and {len(topics)-15} more topics")

# ══════════════════════════════════════════════════════════════
# Example 3: Query topic — full consolidated document
# ══════════════════════════════════════════════════════════════
print()
print(SEP)
print("🔍  QUERY 3: query_topic()")
print(SEP)

if topics:
    target_topic = topics[0]["canonical_name"]
    result = query_topic(target_topic)
    if "error" not in result:
        print(f"Canonical name : {result['canonical_name']}")
        print(f"Aliases        : {result['aliases']}")
        print(f"Source videos  : {len(result['source_video_ids'])}")
        print(f"Content tokens : {result['token_count']:,}")
        print()
        print("Summary:")
        print(result.get("summary", "N/A"))
        print()
        print("Key Points:")
        for kp in result.get("key_points", [])[:5]:
            print(f"  - {kp}")
        print()
        print("Content Preview (first 800 chars):")
        print(result["content"][:800] + "…")
    else:
        print(result["error"])

# ══════════════════════════════════════════════════════════════
# Example 4: Topic summary — concise formatted output
# ══════════════════════════════════════════════════════════════
print()
print(SEP)
print("📋  QUERY 4: query_topic_summary()")
print(SEP)

if topics:
    summary_output = query_topic_summary(topics[0]["canonical_name"])
    print(summary_output)

# ══════════════════════════════════════════════════════════════
# Example 5: Semantic search
# ══════════════════════════════════════════════════════════════
print()
print(SEP)
print("🔎  QUERY 5: search_topics_semantic()")
print(SEP)

search_query = "how does state management work in AI agent workflows"
print(f"Query: \"{search_query}\"\n")
hits = search_topics_semantic(search_query, top_k=5)
if hits:
    for i, h in enumerate(hits, 1):
        print(f"  {i}. {h['canonical_name']}  (score: {h['score']:.3f})")
        print(f"     {h['summary'][:120]}…")
else:
    print("  No results (Qdrant in-memory resets between kernel restarts).")

# ══════════════════════════════════════════════════════════════
# Example 6: RAG Q&A
# ══════════════════════════════════════════════════════════════
print()
print(SEP)
print("🤖  QUERY 6: ask_knowledge_base()")
print(SEP)

rag_question = "What are the key differences between nodes and edges in LangGraph?"
print(f"Question: \"{rag_question}\"\n")
answer = ask_knowledge_base(rag_question, top_k=3)
print("Answer:")
print(answer)

# ══════════════════════════════════════════════════════════════
# Final cost report
# ══════════════════════════════════════════════════════════════
print()
print(SEP)
print("💰  Final Cost Report")
print(SEP)
print(cost_tracker.report())
"""))

# ===========================================================================
# Build and write the notebook
# ===========================================================================
notebook = {
    "nbformat":       4,
    "nbformat_minor": 5,
    "metadata": {
        "kernelspec": {
            "display_name": "Python 3",
            "language":     "python",
            "name":         "python3",
        },
        "language_info": {
            "name":    "python",
            "version": "3.12.0",
        },
    },
    "cells": cells,
}

output_path = os.path.join(os.path.dirname(__file__), "deep_notes_knowledge_graph.ipynb")
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(notebook, f, indent=1, ensure_ascii=False)

nb_size = os.path.getsize(output_path) / 1024
print(f"✅ Notebook written: {output_path}")
print(f"   Cells   : {len(cells)}")
print(f"   Size    : {nb_size:.1f} KB")
