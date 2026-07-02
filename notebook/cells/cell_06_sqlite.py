# ─── Cell 6: SQLite Storage Layer ────────────────────────────────────────────
#
# Schema decisions:
#   - JSON arrays stored as JSON strings (portable to PostgreSQL via JSONB)
#   - WAL journal mode for concurrent read performance
#   - graph_edges table acts as Neo4j fallback adjacency store

_SQLITE_DDL = (
    "PRAGMA journal_mode=WAL;"
    "PRAGMA foreign_keys=ON;"

    "CREATE TABLE IF NOT EXISTS videos ("
    "    video_id         TEXT PRIMARY KEY,"
    "    title            TEXT NOT NULL,"
    "    url              TEXT NOT NULL,"
    "    channel          TEXT DEFAULT 'Unknown',"
    "    duration_seconds INTEGER DEFAULT 0,"
    "    transcript       TEXT NOT NULL,"
    "    word_count       INTEGER DEFAULT 0,"
    "    fetched_at       TEXT NOT NULL"
    ");"

    "CREATE TABLE IF NOT EXISTS structured_notes ("
    "    video_id       TEXT PRIMARY KEY,"
    "    notes_markdown TEXT NOT NULL,"
    "    created_at     TEXT NOT NULL,"
    "    FOREIGN KEY (video_id) REFERENCES videos(video_id)"
    ");"

    "CREATE TABLE IF NOT EXISTS topic_nodes ("
    "    topic_id        TEXT PRIMARY KEY,"
    "    topic_name      TEXT NOT NULL,"
    "    parent_topic_id TEXT,"
    "    depth           INTEGER NOT NULL DEFAULT 0,"
    "    source_video_id TEXT NOT NULL,"
    "    content         TEXT NOT NULL,"
    "    canonical_id    TEXT,"
    "    created_at      TEXT NOT NULL,"
    "    FOREIGN KEY (source_video_id) REFERENCES videos(video_id)"
    ");"

    "CREATE TABLE IF NOT EXISTS canonical_topics ("
    "    canonical_id     TEXT PRIMARY KEY,"
    "    canonical_name   TEXT NOT NULL,"
    "    aliases          TEXT NOT NULL DEFAULT '[]',"
    "    source_video_ids TEXT NOT NULL DEFAULT '[]',"
    "    merged_topic_ids TEXT NOT NULL DEFAULT '[]',"
    "    created_at       TEXT NOT NULL"
    ");"

    "CREATE TABLE IF NOT EXISTS master_documents ("
    "    canonical_id     TEXT PRIMARY KEY,"
    "    canonical_name   TEXT NOT NULL,"
    "    content          TEXT NOT NULL,"
    "    source_video_ids TEXT NOT NULL DEFAULT '[]',"
    "    token_count      INTEGER DEFAULT 0,"
    "    created_at       TEXT NOT NULL,"
    "    FOREIGN KEY (canonical_id) REFERENCES canonical_topics(canonical_id)"
    ");"

    "CREATE TABLE IF NOT EXISTS topic_summaries ("
    "    canonical_id   TEXT PRIMARY KEY,"
    "    canonical_name TEXT NOT NULL,"
    "    summary        TEXT NOT NULL,"
    "    key_points     TEXT NOT NULL DEFAULT '[]',"
    "    created_at     TEXT NOT NULL,"
    "    FOREIGN KEY (canonical_id) REFERENCES canonical_topics(canonical_id)"
    ");"

    "CREATE TABLE IF NOT EXISTS graph_edges ("
    "    edge_id      TEXT PRIMARY KEY,"
    "    from_id      TEXT NOT NULL,"
    "    from_type    TEXT NOT NULL,"
    "    to_id        TEXT NOT NULL,"
    "    to_type      TEXT NOT NULL,"
    "    relationship TEXT NOT NULL,"
    "    created_at   TEXT NOT NULL"
    ");"

    "CREATE INDEX IF NOT EXISTS idx_topic_nodes_video  ON topic_nodes(source_video_id);"
    "CREATE INDEX IF NOT EXISTS idx_topic_nodes_canon  ON topic_nodes(canonical_id);"
    "CREATE INDEX IF NOT EXISTS idx_topic_nodes_parent ON topic_nodes(parent_topic_id);"
    "CREATE INDEX IF NOT EXISTS idx_graph_edges_from   ON graph_edges(from_id);"
    "CREATE INDEX IF NOT EXISTS idx_graph_edges_to     ON graph_edges(to_id);"
    "CREATE INDEX IF NOT EXISTS idx_graph_edges_rel    ON graph_edges(relationship);"
)


class SQLiteStore:
    'Primary relational storage layer (zero-infra, PostgreSQL-ready schema).'

    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._conn() as c:
            c.executescript(_SQLITE_DDL)
        logger.info("SQLite initialised at %s", self.db_path.resolve())

    # -- Videos --

    def video_exists(self, video_id: str) -> bool:
        with self._conn() as c:
            return bool(c.execute(
                "SELECT 1 FROM videos WHERE video_id=?", (video_id,)
            ).fetchone())

    def save_video(self, doc: VideoDocument):
        with self._conn() as c:
            c.execute(
                "INSERT OR REPLACE INTO videos "
                "(video_id,title,url,channel,duration_seconds,transcript,word_count,fetched_at) "
                "VALUES (?,?,?,?,?,?,?,?)",
                (doc.video_id, doc.title, doc.url, doc.channel,
                 doc.duration_seconds, doc.transcript, doc.word_count, doc.fetched_at)
            )

    def get_video(self, video_id: str) -> Optional[VideoDocument]:
        with self._conn() as c:
            row = c.execute("SELECT * FROM videos WHERE video_id=?", (video_id,)).fetchone()
        if row:
            d = {k: row[k] for k in row.keys()}
            return VideoDocument(**d)
        return None

    # -- Structured Notes --

    def save_structured_notes(self, video_id: str, notes: str):
        with self._conn() as c:
            c.execute(
                "INSERT OR REPLACE INTO structured_notes (video_id,notes_markdown,created_at) "
                "VALUES (?,?,?)",
                (video_id, notes, datetime.utcnow().isoformat())
            )

    def get_structured_notes(self, video_id: str) -> Optional[str]:
        with self._conn() as c:
            row = c.execute(
                "SELECT notes_markdown FROM structured_notes WHERE video_id=?", (video_id,)
            ).fetchone()
        return row["notes_markdown"] if row else None

    # -- Topic Nodes --

    def save_topic_node(self, node: TopicNode):
        with self._conn() as c:
            c.execute(
                "INSERT OR REPLACE INTO topic_nodes "
                "(topic_id,topic_name,parent_topic_id,depth,source_video_id,content,canonical_id,created_at) "
                "VALUES (?,?,?,?,?,?,?,?)",
                (node.topic_id, node.topic_name, node.parent_topic_id, node.depth,
                 node.source_video_id, node.content, node.canonical_id,
                 datetime.utcnow().isoformat())
            )

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

    # -- Canonical Topics --

    def save_canonical_topic(self, ct: CanonicalTopic):
        with self._conn() as c:
            c.execute(
                "INSERT OR REPLACE INTO canonical_topics "
                "(canonical_id,canonical_name,aliases,source_video_ids,merged_topic_ids,created_at) "
                "VALUES (?,?,?,?,?,?)",
                (ct.canonical_id, ct.canonical_name,
                 json.dumps(ct.aliases), json.dumps(ct.source_video_ids),
                 json.dumps(ct.merged_topic_ids), datetime.utcnow().isoformat())
            )

    def get_all_canonical_topics(self) -> List[CanonicalTopic]:
        with self._conn() as c:
            rows = c.execute("SELECT * FROM canonical_topics").fetchall()
        return [CanonicalTopic(
            canonical_id=r["canonical_id"],
            canonical_name=r["canonical_name"],
            aliases=json.loads(r["aliases"]),
            source_video_ids=json.loads(r["source_video_ids"]),
            merged_topic_ids=json.loads(r["merged_topic_ids"]),
        ) for r in rows]

    # -- Master Documents --

    def save_master_document(self, doc: MasterTopicDocument):
        with self._conn() as c:
            c.execute(
                "INSERT OR REPLACE INTO master_documents "
                "(canonical_id,canonical_name,content,source_video_ids,token_count,created_at) "
                "VALUES (?,?,?,?,?,?)",
                (doc.canonical_id, doc.canonical_name, doc.content,
                 json.dumps(doc.source_video_ids), doc.token_count,
                 datetime.utcnow().isoformat())
            )

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

    # -- Summaries --

    def save_topic_summary(self, s: TopicSummary):
        with self._conn() as c:
            c.execute(
                "INSERT OR REPLACE INTO topic_summaries "
                "(canonical_id,canonical_name,summary,key_points,created_at) "
                "VALUES (?,?,?,?,?)",
                (s.canonical_id, s.canonical_name, s.summary,
                 json.dumps(s.key_points), datetime.utcnow().isoformat())
            )

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

    # -- Graph Edges (Neo4j fallback) --

    def save_graph_edge(self, from_id: str, from_type: str,
                        to_id: str, to_type: str, relationship: str):
        with self._conn() as c:
            c.execute(
                "INSERT OR IGNORE INTO graph_edges "
                "(edge_id,from_id,from_type,to_id,to_type,relationship,created_at) "
                "VALUES (?,?,?,?,?,?,?)",
                (str(uuid.uuid4()), from_id, from_type, to_id, to_type,
                 relationship, datetime.utcnow().isoformat())
            )

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
