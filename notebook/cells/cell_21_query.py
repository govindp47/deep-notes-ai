# ─── Cell 21: Retrieval & Query Layer (Phase 9 + 14) ─────────────────────────

# -- Internal: find canonical topic by name --

def _find_canonical_topic(topic_name: str) -> Optional[CanonicalTopic]:
    'Multi-strategy lookup: exact -> alias -> partial -> vector similarity.'
    all_ct = sqlite_store.get_all_canonical_topics()
    lower  = topic_name.strip().lower()

    # Strategy 1: exact name match
    for ct in all_ct:
        if ct.canonical_name.lower() == lower:
            return ct

    # Strategy 2: alias match
    for ct in all_ct:
        if any(a.lower() == lower for a in ct.aliases):
            return ct

    # Strategy 3: partial substring match
    for ct in all_ct:
        if lower in ct.canonical_name.lower():
            return ct

    # Strategy 4: vector similarity via Qdrant
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


# -- query_video --

def query_video(video_id: str) -> Dict[str, Any]:
    '''
    Return all knowledge associated with a specific video.

    Returns:
        - Video metadata
        - Full structured study notes (Markdown)
        - Topic hierarchy in original video order
        - Canonical topic IDs for cross-referencing with query_topic()
    '''
    video = sqlite_store.get_video(video_id)
    if not video:
        return {"error": f"Video '{video_id}' not found in knowledge base."}

    notes   = sqlite_store.get_structured_notes(video_id)
    t_nodes = sqlite_store.get_topic_nodes_by_video(video_id)

    def _build_tree(node: TopicNode) -> Dict:
        children = [n for n in t_nodes if n.parent_topic_id == node.topic_id]
        return {
            "topic":           node.topic_name,
            "depth":           node.depth,
            "canonical_id":    node.canonical_id,
            "content_preview": (node.content[:300] + "...") if len(node.content) > 300
                               else node.content,
            "subtopics":       [_build_tree(c) for c in children],
        }

    root_nodes = [n for n in t_nodes if n.parent_topic_id is None]
    return {
        "video_id":         video_id,
        "title":            video.title,
        "url":              video.url,
        "channel":          video.channel,
        "word_count":       video.word_count,
        "fetched_at":       video.fetched_at,
        "structured_notes": notes,
        "topic_hierarchy":  [_build_tree(r) for r in root_nodes],
        "total_topics":     len(t_nodes),
    }


# -- query_topic --

def query_topic(topic_name: str) -> Dict[str, Any]:
    '''
    Return the consolidated knowledge document for a topic concept.

    Searches by: exact name -> alias -> partial match -> vector similarity.
    Returns: aggregated Markdown content + summary + key points + graph edges.
    '''
    ct = _find_canonical_topic(topic_name)
    if not ct:
        all_names = [c.canonical_name for c in sqlite_store.get_all_canonical_topics()]
        return {
            "error":            f"Topic '{topic_name}' not found.",
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
        "graph_edges":      edges[:10],
    }


# -- query_topic_summary --

def query_topic_summary(topic_name: str) -> str:
    'Return a concise formatted summary - optimised for quick retrieval.'
    result = query_topic(topic_name)
    if "error" in result:
        return f"Warning: {result['error']}"

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


# -- list_all_topics --

def list_all_topics() -> List[Dict]:
    'Return a sorted list of all canonical topics in the knowledge base.'
    all_ct     = sqlite_store.get_all_canonical_topics()
    summ_by_id = {s.canonical_id: s for s in sqlite_store.get_all_summaries()}
    result     = []
    for ct in all_ct:
        s       = summ_by_id.get(ct.canonical_id)
        preview = (s.summary[:120] + "...") if s and len(s.summary) > 120 \
                  else (s.summary if s else "")
        result.append({
            "canonical_name":  ct.canonical_name,
            "aliases":         ct.aliases,
            "source_count":    len(ct.source_video_ids),
            "summary_preview": preview,
        })
    return sorted(result, key=lambda x: x["canonical_name"])


# -- search_topics_semantic --

def search_topics_semantic(query: str, top_k: int = 5) -> List[Dict]:
    'Semantic search across all topic summaries using Qdrant vector similarity.'
    try:
        emb_model = OpenAIEmbeddings(model=MODELS["embedding"],
                                      openai_api_key=OPENAI_API_KEY)
        q_emb     = emb_model.embed_query(query)
        cost_tracker.record(MODELS["embedding"], count_tokens(query))
        return qdrant_store.search_summaries(q_emb, top_k=top_k)
    except Exception as exc:
        logger.error("Semantic search error: %s", exc)
        return []


# -- ask_knowledge_base --

def ask_knowledge_base(question: str, top_k: int = 3) -> str:
    'RAG-style Q&A: retrieve relevant topics, then generate an answer with GPT-4o.'
    hits = search_topics_semantic(question, top_k=top_k)
    if not hits:
        return "No relevant topics found in the knowledge base."

    context_parts = []
    for h in hits:
        ct = _find_canonical_topic(h["canonical_name"])
        if ct:
            md = sqlite_store.get_master_document(ct.canonical_id)
            if md:
                preview = md.content[:1500] + ("..." if len(md.content) > 1500 else "")
                context_parts.append(f"### {ct.canonical_name}\n{preview}")

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
print("   query_video(video_id)           -> full video knowledge")
print("   query_topic(topic_name)         -> consolidated topic document")
print("   query_topic_summary(topic_name) -> concise formatted summary")
print("   list_all_topics()               -> all topics in knowledge base")
print("   search_topics_semantic(query)   -> vector similarity search")
print("   ask_knowledge_base(question)    -> RAG Q&A answer")
