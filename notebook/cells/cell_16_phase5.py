# ─── Cell 16: Phase 5 - Topic Canonicalizer ──────────────────────────────────
#
# Two-stage deduplication:
#   Stage 1: Embedding cosine similarity  (fast, cheap - filters ~80% of pairs)
#   Stage 2: LLM binary judgment          (accurate - only on candidate pairs)
#
# Union-Find (disjoint-set) groups topics determined to be the same concept.

def _cosine_similarity(a: List[float], b: List[float]) -> float:
    'Exact cosine similarity without numpy.'
    dot   = sum(x * y for x, y in zip(a, b))
    mag_a = sum(x * x for x in a) ** 0.5
    mag_b = sum(x * x for x in b) ** 0.5
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)


class UnionFind:
    'Path-compressed union-find for grouping canonical topics.'

    def __init__(self, ids: List[str]):
        self._parent = {i: i for i in ids}

    def find(self, x: str) -> str:
        while self._parent[x] != x:
            self._parent[x] = self._parent[self._parent[x]]
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
    'LLM binary judgment: are these two topic nodes the same concept?'
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
    'Phase 5: Detect and merge identical topics across videos.'
    logger.info("[Phase 5] Canonicalising Topics")
    topic_nodes = state.get("topic_nodes", [])
    errors      = list(state.get("errors", []))

    if not topic_nodes:
        logger.warning("  No topic nodes to canonicalise")
        return {"canonical_topics": [], "errors": errors,
                "current_phase": "topic_canonicalizer_complete"}

    # Stage 1: Compute embeddings for all topics
    logger.info("  Computing embeddings for %d topics...", len(topic_nodes))
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

    # Stage 2: Union-Find grouping with embedding pre-filter + LLM validation
    uf    = UnionFind([n.topic_id for n in topic_nodes])
    llm   = make_llm(MODELS["extraction"], temperature=0.0, json_mode=True)
    llm_n = 0

    # Group nodes by video
    by_vid: Dict[str, List[TopicNode]] = {}
    for n in topic_nodes:
        by_vid.setdefault(n.source_video_id, []).append(n)

    vid_ids = list(by_vid.keys())
    if len(vid_ids) > 1:
        logger.info("  Comparing topics across %d videos...", len(vid_ids))
        for i in range(len(vid_ids)):
            for j in range(i + 1, len(vid_ids)):
                for na in by_vid[vid_ids[i]]:
                    for nb in by_vid[vid_ids[j]]:
                        if uf.find(na.topic_id) == uf.find(nb.topic_id):
                            continue
                        sim = _cosine_similarity(na.embedding, nb.embedding)
                        if sim < COSINE_SIM_THRESHOLD:
                            continue
                        try:
                            decision = _llm_canonicalize(na, nb, llm)
                            llm_n += 1
                            if (decision and decision.are_same
                                    and decision.confidence >= CANON_LLM_CONFIDENCE):
                                uf.union(na.topic_id, nb.topic_id)
                                logger.info(
                                    "  MERGED: '%s' <-> '%s' (sim=%.2f conf=%.2f)",
                                    na.topic_name, nb.topic_name,
                                    sim, decision.confidence,
                                )
                        except Exception as exc:
                            logger.warning("  Canonicalization LLM error: %s", exc)

    logger.info("  LLM calls: %d (embedding pre-filter active)", llm_n)

    # Build CanonicalTopic objects from union-find groups
    groups       = uf.groups()
    id_to_node   = {n.topic_id: n for n in topic_nodes}
    canon_topics: List[CanonicalTopic] = []

    for root_id, topic_ids in groups.items():
        group_nodes = [id_to_node[tid] for tid in topic_ids if tid in id_to_node]
        names = [n.topic_name for n in group_nodes]

        # Choose canonical name: most frequent, tie-break by length
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
                qdrant_store.upsert_topic(
                    ct.canonical_id, ct.canonical_name, ct.aliases, mean_emb
                )
            except Exception as exc:
                logger.warning("  Qdrant upsert skipped: %s", exc)

        canon_topics.append(ct)

    merged_count = len(topic_nodes) - len(canon_topics)
    logger.info("  OK: %d canonical topics (%d merged)", len(canon_topics), merged_count)

    return {
        "topic_nodes":      topic_nodes,
        "canonical_topics": canon_topics,
        "errors":           errors,
        "current_phase":    "topic_canonicalizer_complete",
    }


print("✅ Phase 5 node defined: topic_canonicalizer")
