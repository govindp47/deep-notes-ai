# ─── Cell 17: Phase 6 - Knowledge Graph Writer ───────────────────────────────
#
# Writes to Neo4j if available, else to SQLite graph_edges table.
#
# Relationships:
#   (:Video)-[:CONTAINS]->(:Topic)
#   (:Topic)-[:HAS_CHILD]->(:Topic)
#   (:Topic)-[:MAPS_TO]->(:CanonicalTopic)

def graph_writer_node(state: PipelineState) -> Dict:
    'Phase 6: Write the knowledge graph to Neo4j (or SQLite fallback).'
    logger.info("[Phase 6] Writing Knowledge Graph")
    video_documents  = state.get("video_documents", [])
    topic_nodes      = state.get("topic_nodes", [])
    canonical_topics = state.get("canonical_topics", [])
    errors           = list(state.get("errors", []))
    use_neo4j        = neo4j_store._available

    logger.info("  Backend: %s", "Neo4j" if use_neo4j else "SQLite adjacency table")

    # Write video nodes
    for video in video_documents:
        if use_neo4j:
            try:
                neo4j_store.create_video_node(video)
            except Exception as exc:
                errors.append(f"Neo4j video node: {exc}")

    # Write topic nodes + CONTAINS + HAS_CHILD
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

    # Write canonical topics + MAPS_TO
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
        "  OK: %d videos, %d topics, %d canonical topics written",
        len(video_documents), len(topic_nodes), len(canonical_topics),
    )
    return {"errors": errors, "current_phase": "graph_writer_complete"}


print("✅ Phase 6 node defined: graph_writer_node")
