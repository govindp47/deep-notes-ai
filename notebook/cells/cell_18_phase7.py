# ─── Cell 18: Phase 7 - Topic Aggregator ─────────────────────────────────────
#
# Single-source topics are passed through without an LLM call (cost saving).
# Multi-source topics use GPT-4o for quality synthesis.

@with_retry(max_attempts=2, wait_min=2, wait_max=30)
def _aggregate_with_llm(topic_name: str, source_content: str,
                         source_count: int, llm: ChatOpenAI) -> str:
    'Single GPT-4o call to aggregate multi-source content.'
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
    'Phase 7: Aggregate content across videos for each canonical topic.'
    logger.info("[Phase 7] Aggregating Topic Content")
    canonical_topics = state.get("canonical_topics", [])
    topic_nodes      = state.get("topic_nodes", [])
    errors           = list(state.get("errors", []))

    # Build lookup: canonical_id -> [TopicNode]
    by_canon: Dict[str, List[TopicNode]] = {}
    for n in topic_nodes:
        if n.canonical_id:
            by_canon.setdefault(n.canonical_id, []).append(n)

    llm         = make_llm(MODELS["reasoning"], temperature=0.2)
    enc         = tiktoken.encoding_for_model(MODELS["reasoning"])
    master_docs: List[MasterTopicDocument] = []

    for ct in canonical_topics:
        group = by_canon.get(ct.canonical_id, [])
        if not group:
            continue

        # Single source: pass through without LLM
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

        # Multi-source: LLM aggregation
        logger.info("  AGGREGATING: '%s' (%d sources)", ct.canonical_name, len(group))

        # Build source block (truncate each proportionally if needed)
        MAX_SRC_TOKENS = 80_000
        total_tokens   = sum(count_tokens(n.content) for n in group)
        parts = []
        for i, n in enumerate(group, 1):
            content = n.content
            if total_tokens > MAX_SRC_TOKENS:
                max_per = MAX_SRC_TOKENS // len(group)
                toks    = enc.encode(content, disallowed_special=())
                if len(toks) > max_per:
                    content = enc.decode(toks[:max_per]) + "\n...[truncated]"
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
            logger.error("  FALLBACK used for '%s'", ct.canonical_name)

        sqlite_store.save_master_document(doc)
        master_docs.append(doc)

    logger.info("  OK: Created %d master documents", len(master_docs))
    return {
        "master_documents": master_docs,
        "errors":           errors,
        "current_phase":    "topic_aggregator_complete",
    }


print("✅ Phase 7 node defined: topic_aggregator")
