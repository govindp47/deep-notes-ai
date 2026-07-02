# ─── Cell 14: Phase 2 - Note Generator ───────────────────────────────────────

@with_retry(max_attempts=3, wait_min=2, wait_max=30)
def _call_llm_for_notes(prompt: str, llm: ChatOpenAI) -> str:
    'Single LLM call with retry and cost tracking.'
    in_tok  = count_tokens(prompt)
    resp    = llm.invoke([HumanMessage(content=prompt)])
    out_tok = count_tokens(resp.content)
    cost_tracker.record(MODELS["extraction"], in_tok, out_tok)
    return resp.content


def _generate_notes_for_video(doc: VideoDocument, llm: ChatOpenAI) -> str:
    'Generate structured notes for a video. Multi-chunk: process then merge.'
    if len(doc.transcript_chunks) == 1:
        prompt = TRANSCRIPT_TO_NOTES_PROMPT.format(
            transcript=sanitize_for_llm(doc.transcript_chunks[0])
        )
        return _call_llm_for_notes(prompt, llm)

    # Multi-chunk: process each chunk independently
    chunk_notes = []
    for i, chunk in enumerate(doc.transcript_chunks, 1):
        logger.info("    Chunk %d/%d...", i, len(doc.transcript_chunks))
        prompt = TRANSCRIPT_TO_NOTES_PROMPT.format(
            transcript=sanitize_for_llm(chunk)
        )
        chunk_notes.append(_call_llm_for_notes(prompt, llm))

    # Merge pass (if combined fits in context)
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
        return _call_llm_for_notes(merge_prompt, llm)

    # Fallback: concatenate if too long to merge
    return combined


def note_generator(state: PipelineState) -> Dict:
    'Phase 2: Convert transcripts into structured Markdown study notes.'
    logger.info("[Phase 2] Generating Structured Notes")
    video_documents  = state.get("video_documents", [])
    structured_notes = dict(state.get("structured_notes", {}))
    errors           = list(state.get("errors", []))
    llm              = make_llm(MODELS["extraction"], temperature=0.1)

    for doc in video_documents:
        # Cache check
        cached = sqlite_store.get_structured_notes(doc.video_id)
        if cached:
            logger.info("  CACHE HIT notes: %s", doc.video_id)
            structured_notes[doc.video_id] = cached
            continue

        logger.info("  GENERATING notes: %s", doc.title)
        try:
            notes = _generate_notes_for_video(doc, llm)
            structured_notes[doc.video_id] = notes
            sqlite_store.save_structured_notes(doc.video_id, notes)
            logger.info("  OK: ~%d tokens", count_tokens(notes))
        except Exception as exc:
            msg = f"Note generation failed for {doc.video_id}: {exc}"
            errors.append(msg)
            logger.error("  FAIL: %s", msg)

    logger.info("  -> Notes ready for %d video(s)", len(structured_notes))
    return {
        "structured_notes": structured_notes,
        "errors":           errors,
        "current_phase":    "note_generator_complete",
    }


print("✅ Phase 2 node defined: note_generator")
