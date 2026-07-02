# ─── Cell 15: Phase 3+4 - Topic Extractor & Mapper ───────────────────────────

def _flatten_hierarchy(items: List[Dict],
                       parent_id: Optional[str],
                       video_id: str,
                       depth: int = 0) -> List[TopicNode]:
    'Recursively flatten a nested topic dict into a flat list of TopicNodes.'
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
    'Call LLM to extract topic hierarchy from notes; return flat TopicNode list.'
    if count_tokens(notes) > 60_000:
        enc   = tiktoken.encoding_for_model(MODELS["extraction"])
        notes = enc.decode(enc.encode(notes, disallowed_special=())[:60_000])
        logger.warning("  Notes truncated to 60k tokens for %s", video_id)

    prompt   = NOTES_TO_TOPICS_PROMPT.format(notes=sanitize_for_llm(notes))
    in_tok   = count_tokens(prompt)
    response = llm.invoke([HumanMessage(content=prompt)])
    out_tok  = count_tokens(response.content)
    cost_tracker.record(MODELS["extraction"], in_tok, out_tok)

    hierarchy_output = parse_llm_json(response.content, TopicHierarchyOutput)
    raw_topics       = [t.model_dump() for t in hierarchy_output.topics]
    return _flatten_hierarchy(raw_topics, None, video_id, 0)


def topic_extractor(state: PipelineState) -> Dict:
    'Phase 3: Extract recursive topic hierarchies from each video study notes.'
    logger.info("[Phase 3] Extracting Topic Hierarchies")
    video_documents  = state.get("video_documents", [])
    structured_notes = state.get("structured_notes", {})
    topic_trees      = dict(state.get("topic_trees", {}))
    all_topic_nodes  = list(state.get("topic_nodes", []))
    errors           = list(state.get("errors", []))
    llm              = make_llm(MODELS["extraction"], temperature=0.0, json_mode=True)

    for doc in video_documents:
        notes = structured_notes.get(doc.video_id, "")
        if not notes:
            logger.warning("  No notes for %s - skipping", doc.video_id)
            continue
        logger.info("  EXTRACTING topics: %s", doc.title)
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
            logger.info("  OK: %d nodes (max depth: %d)", len(nodes), max_depth)
        except Exception as exc:
            msg = f"Topic extraction failed for {doc.video_id}: {exc}"
            errors.append(msg)
            logger.error("  FAIL: %s", msg)

    logger.info("  -> %d total topic nodes across all videos", len(all_topic_nodes))
    return {
        "topic_trees":   topic_trees,
        "topic_nodes":   all_topic_nodes,
        "errors":        errors,
        "current_phase": "topic_extractor_complete",
    }


def topic_mapper(state: PipelineState) -> Dict:
    'Phase 4: Persist all TopicNodes to SQLite storage.'
    logger.info("[Phase 4] Persisting Topic Nodes to SQLite")
    topic_nodes = state.get("topic_nodes", [])
    errors      = list(state.get("errors", []))
    saved       = 0

    for node in topic_nodes:
        try:
            sqlite_store.save_topic_node(node)
            saved += 1
        except Exception as exc:
            errors.append(f"Save topic node {node.topic_id}: {exc}")

    logger.info("  OK: Saved %d/%d nodes", saved, len(topic_nodes))
    return {"errors": errors, "current_phase": "topic_mapper_complete"}


print("✅ Phase 3+4 nodes defined: topic_extractor, topic_mapper")
