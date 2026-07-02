# ─── Cell 7: Neo4j Knowledge Graph Store ─────────────────────────────────────
#
# Neo4j is OPTIONAL. If unavailable the pipeline uses the SQLite graph_edges table.
#
# To start Neo4j with Docker (run in a TERMINAL, not the notebook):
#   docker run --rm -d \
#     --name neo4j \
#     -p 7474:7474 -p 7687:7687 \
#     -e NEO4J_AUTH=neo4j/password \
#     neo4j:5-community
#
# Then browse to http://localhost:7474 to inspect the graph.
#
# Relationships modelled:
#   (:Video)-[:CONTAINS]->(:Topic)
#   (:Topic)-[:HAS_CHILD]->(:Topic)
#   (:Topic)-[:MAPS_TO]->(:CanonicalTopic)

class Neo4jStore:
    'Knowledge graph storage backed by Neo4j, with transparent SQLite fallback.'

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
            logger.info("Connected to Neo4j at %s", NEO4J_URI)
        except Exception as exc:
            logger.warning("Neo4j unavailable (%s) - using SQLite graph fallback", exc)
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
                "CREATE CONSTRAINT IF NOT EXISTS FOR (v:Video)          REQUIRE v.video_id    IS UNIQUE",
                "CREATE CONSTRAINT IF NOT EXISTS FOR (t:Topic)          REQUIRE t.topic_id    IS UNIQUE",
                "CREATE CONSTRAINT IF NOT EXISTS FOR (c:CanonicalTopic) REQUIRE c.canonical_id IS UNIQUE",
            ]:
                s.run(stmt)

    # -- Node creation --

    def create_video_node(self, video):
        if not self._available:
            return
        with self.driver.session() as s:
            s.run(
                "MERGE (v:Video {video_id: $vid}) "
                "SET v.title=$title, v.url=$url, v.channel=$channel",
                vid=video.video_id, title=video.title,
                url=video.url, channel=video.channel
            )

    def create_topic_node(self, node):
        if not self._available:
            return
        with self.driver.session() as s:
            s.run(
                "MERGE (t:Topic {topic_id: $tid}) "
                "SET t.topic_name=$name, t.depth=$depth, "
                "    t.source_video_id=$svid, t.content_preview=$preview",
                tid=node.topic_id, name=node.topic_name,
                depth=node.depth, svid=node.source_video_id,
                preview=node.content[:500]
            )

    def create_canonical_topic_node(self, ct):
        if not self._available:
            return
        with self.driver.session() as s:
            s.run(
                "MERGE (c:CanonicalTopic {canonical_id: $cid}) "
                "SET c.canonical_name=$name, c.aliases=$aliases",
                cid=ct.canonical_id, name=ct.canonical_name, aliases=ct.aliases
            )

    # -- Relationship creation --

    def video_contains_topic(self, video_id: str, topic_id: str):
        if not self._available:
            return
        with self.driver.session() as s:
            s.run(
                "MATCH (v:Video {video_id:$vid}) "
                "MATCH (t:Topic {topic_id:$tid}) "
                "MERGE (v)-[:CONTAINS]->(t)",
                vid=video_id, tid=topic_id
            )

    def topic_has_child(self, parent_id: str, child_id: str):
        if not self._available:
            return
        with self.driver.session() as s:
            s.run(
                "MATCH (p:Topic {topic_id:$pid}) "
                "MATCH (c:Topic {topic_id:$cid}) "
                "MERGE (p)-[:HAS_CHILD]->(c)",
                pid=parent_id, cid=child_id
            )

    def topic_maps_to_canonical(self, topic_id: str, canonical_id: str):
        if not self._available:
            return
        with self.driver.session() as s:
            s.run(
                "MATCH (t:Topic {topic_id:$tid}) "
                "MATCH (c:CanonicalTopic {canonical_id:$cid}) "
                "MERGE (t)-[:MAPS_TO]->(c)",
                tid=topic_id, cid=canonical_id
            )

    # -- Queries --

    def get_topics_for_video(self, video_id: str) -> List[Dict]:
        if not self._available:
            return []
        with self.driver.session() as s:
            res = s.run(
                "MATCH (v:Video {video_id:$vid})-[:CONTAINS]->(t:Topic) "
                "RETURN t.topic_id AS topic_id, t.topic_name AS topic_name, t.depth AS depth "
                "ORDER BY t.depth, t.topic_name",
                vid=video_id
            )
            return [dict(r) for r in res]

    def close(self):
        if self.driver:
            self.driver.close()


neo4j_store = Neo4jStore()
print(f"✅ Neo4j store initialised (available: {neo4j_store._available})")
if not neo4j_store._available:
    print("   -> Graph relationships will be stored in SQLite (graph_edges table)")
