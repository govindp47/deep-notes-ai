# ─── Cell 19: Phase 8 - Summary Generator ────────────────────────────────────

@with_retry(max_attempts=3, wait_min=2, wait_max=20)
def _generate_single_summary(topic_name: str,
                               content: str,
                               llm: ChatOpenAI) -> TopicSummaryOutput:
    'Single LLM call for one topic summary.'
    if count_tokens(content) > 30_000:
        enc     = tiktoken.encoding_for_model(MODELS["extraction"])
        content = enc.decode(
            enc.encode(content, disallowed_special=())[:30_000]
        ) + "\n...[content truncated for summary]"

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
    'Phase 8: Generate concise retrieval-optimised summaries for all topics.'
    logger.info("[Phase 8] Generating Topic Summaries")
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

            # Embed summary and upsert into Qdrant for semantic search
            summary_text = f"{doc.canonical_name}: {out.summary}"
            try:
                emb = emb_model.embed_documents([summary_text])[0]
                cost_tracker.record(MODELS["embedding"], count_tokens(summary_text))
                qdrant_store.upsert_summary(
                    doc.canonical_id, doc.canonical_name, out.summary, emb
                )
            except Exception as exc:
                logger.warning("  Qdrant summary upsert failed: %s", exc)

            logger.info("  OK: '%s' - %d key points",
                        doc.canonical_name, len(out.key_points))

        except Exception as exc:
            msg = f"Summary failed for '{doc.canonical_name}': {exc}"
            errors.append(msg)
            logger.error("  FAIL: %s", msg)

    logger.info("  OK: Generated %d summaries", len(summaries))
    return {
        "summaries":           summaries,
        "errors":              errors,
        "current_phase":       "pipeline_complete",
        "processing_complete": True,
    }


print("✅ Phase 8 node defined: summary_generator_node")
