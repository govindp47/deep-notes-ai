# ─── Cell 13: Phase 1 - URL Processor & Transcript Extractor ─────────────────

# -- Node 1a: URL Processor --

def url_processor(state: PipelineState) -> Dict:
    'Validate, sanitise, and deduplicate all incoming YouTube URLs.'
    logger.info("[Phase 1a] Processing URLs")
    raw_urls    = state.get("urls", [])
    errors      = list(state.get("errors", []))
    valid_pairs = []
    seen_ids    = set()

    for raw_url in raw_urls:
        ok, result = validate_youtube_url(raw_url)
        if not ok:
            msg = f"Invalid URL '{raw_url}': {result}"
            errors.append(msg)
            logger.warning("  SKIP: %s", msg)
            continue
        video_id = result
        if video_id in seen_ids:
            logger.info("  SKIP duplicate: %s", raw_url)
            continue
        seen_ids.add(video_id)
        valid_pairs.append((raw_url, video_id))
        logger.info("  OK: %s -> %s", raw_url, video_id)

    logger.info("  -> %d valid video(s) to process", len(valid_pairs))
    return {
        "urls":          [u for u, _ in valid_pairs],
        "errors":        errors,
        "current_phase": "url_processor_complete",
    }


# -- Transcript fetcher (with retry) --

@with_retry(max_attempts=3, wait_min=2, wait_max=20)
def _fetch_transcript_raw(video_id: str) -> str:
    'Fetch and concatenate transcript from YouTube (handles both API versions).'
    from youtube_transcript_api import YouTubeTranscriptApi

    # New instance-based API (youtube-transcript-api >= 0.6)
    try:
        api = YouTubeTranscriptApi()
        snippet_list = api.fetch(video_id)
        parts = []
        for s in snippet_list:
            text = s.text if hasattr(s, "text") else s.get("text", "")
            parts.append(text)
        return " ".join(parts)
    except TypeError:
        pass

    # Fallback: class-method API (< 0.6)
    transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
    return " ".join(s.get("text", "") for s in transcript_list)


def _clean_transcript(raw: str) -> str:
    'Remove caption artefacts and normalise whitespace.'
    cleaned = re.sub(r'\[[\w\s]+\]', '', raw)       # [Music], [Applause], etc.
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned


# -- Node 1b: Transcript Extractor --

def transcript_extractor(state: PipelineState) -> Dict:
    'Fetch, clean, and chunk transcripts for every validated URL.'
    logger.info("[Phase 1b] Extracting Transcripts")
    urls            = state.get("urls", [])
    errors          = list(state.get("errors", []))
    video_documents = []

    for url in urls:
        ok, video_id = validate_youtube_url(url)
        if not ok:
            continue

        # Cache check: skip re-fetching if already in SQLite
        cached = sqlite_store.get_video(video_id)
        if cached:
            logger.info("  CACHE HIT: %s (%s)", video_id, cached.title)
            cached.transcript_chunks = chunk_text(cached.transcript)
            video_documents.append(cached)
            continue

        logger.info("  FETCHING: %s", video_id)
        try:
            raw        = _fetch_transcript_raw(video_id)
            transcript = _clean_transcript(raw)
            title      = fetch_video_title(video_id)
            word_count = len(transcript.split())

            doc = VideoDocument(
                video_id          = video_id,
                title             = title,
                url               = url,
                transcript        = transcript,
                word_count        = word_count,
                transcript_chunks = chunk_text(transcript),
            )
            sqlite_store.save_video(doc)
            video_documents.append(doc)
            logger.info("  OK: %s | %d words | %d chunk(s)",
                        title, word_count, len(doc.transcript_chunks))

        except (TranscriptsDisabled, NoTranscriptFound) as exc:
            msg = f"Transcript unavailable for {video_id}: {exc}"
            errors.append(msg)
            logger.error("  FAIL: %s", msg)
        except VideoUnavailable as exc:
            msg = f"Video unavailable: {video_id}: {exc}"
            errors.append(msg)
            logger.error("  FAIL: %s", msg)
        except Exception as exc:
            msg = f"Transcript fetch error for {video_id}: {exc}"
            errors.append(msg)
            logger.error("  FAIL: %s", msg)

    logger.info("  -> %d video(s) loaded successfully", len(video_documents))
    return {
        "video_documents": video_documents,
        "errors":          errors,
        "current_phase":   "transcript_extractor_complete",
    }


# -- Conditional routing --

def _route_after_url_processor(state: PipelineState) -> str:
    if not state.get("urls") and state.get("errors"):
        logger.error("No valid URLs - ending pipeline")
        return END
    return "transcript_extractor"


def _route_after_transcript_extractor(state: PipelineState) -> str:
    if not state.get("video_documents"):
        logger.error("No transcripts available - ending pipeline")
        return END
    return "note_generator"


print("✅ Phase 1 nodes defined: url_processor, transcript_extractor")
