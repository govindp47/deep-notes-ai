# ─── Cell 10: Middleware ──────────────────────────────────────────────────────
#
# Provides:
#   - YouTube URL validation (regex-based, handles all URL formats)
#   - Prompt injection sanitisation (pattern-based redaction)
#   - Tenacity retry decorator (exponential backoff)
#   - LLM JSON output validator (dual-strategy Pydantic parsing)
#   - Video title fetcher (no API key required)

# -- YouTube URL Validation --

_YT_PATTERNS = [
    r'(?:https?://)?(?:www\.)?youtube\.com/watch\?(?:.*&)?v=([a-zA-Z0-9_-]{11})',
    r'(?:https?://)?(?:www\.)?youtu\.be/([a-zA-Z0-9_-]{11})',
    r'(?:https?://)?(?:www\.)?youtube\.com/embed/([a-zA-Z0-9_-]{11})',
    r'(?:https?://)?(?:www\.)?youtube\.com/shorts/([a-zA-Z0-9_-]{11})',
    r'(?:https?://)?(?:www\.)?youtube\.com/v/([a-zA-Z0-9_-]{11})',
    r'(?:https?://)?(?:www\.)?youtube\.com/live/([a-zA-Z0-9_-]{11})',
]


def extract_video_id(url: str) -> Optional[str]:
    'Extract 11-character YouTube video ID from any URL format.'
    for pattern in _YT_PATTERNS:
        m = re.search(pattern, url)
        if m:
            return m.group(1)
    return None


def validate_youtube_url(url: str) -> Tuple[bool, str]:
    'Validate a YouTube URL. Returns (True, video_id) or (False, error_message).'
    if not url or not isinstance(url, str):
        return False, "URL must be a non-empty string"
    if len(url) > 500:
        return False, "URL exceeds maximum length (500 chars)"
    url = url.strip()
    if not url.startswith(("http://", "https://", "www.", "youtu")):
        return False, f"Not a recognisable YouTube URL: {url!r}"
    vid = extract_video_id(url)
    if not vid:
        return False, f"Cannot extract video ID from: {url!r}"
    if not re.match(r'^[a-zA-Z0-9_-]{11}$', vid):
        return False, f"Invalid video ID characters: {vid!r}"
    return True, vid


# -- Prompt Injection Guard --

_INJECTION_PATTERNS = [
    r'(?i)ignore\s+(all\s+)?previous\s+instructions?',
    r'(?i)forget\s+(all\s+)?previous\s+instructions?',
    r'(?i)\bsystem\s*:\s*',
    r'(?i)\bassistant\s*:\s*',
    r'(?i)you\s+are\s+now\s+',
    r'(?i)disregard\s+(the\s+)?above',
    r'(?i)new\s+instructions?\s*:',
]


def sanitize_for_llm(text: str) -> str:
    'Sanitize user content before LLM embedding. Redacts injection patterns.'
    for pat in _INJECTION_PATTERNS:
        text = re.sub(pat, '[REDACTED]', text)
    return text


# -- Retry Decorator --

def with_retry(max_attempts: int = 3,
               wait_min: float = 1.0,
               wait_max: float = 30.0,
               reraise: bool = True):
    'Decorator: exponential-backoff retry via Tenacity.'
    def decorator(fn):
        @retry(
            stop=stop_after_attempt(max_attempts),
            wait=wait_exponential(multiplier=1, min=wait_min, max=wait_max),
            before_sleep=before_sleep_log(logger, logging.WARNING),
            reraise=reraise,
        )
        @wraps(fn)
        def wrapper(*args, **kwargs):
            return fn(*args, **kwargs)
        return wrapper
    return decorator


# -- LLM Output Validator --

class LLMOutputError(ValueError):
    'Raised when LLM output fails Pydantic validation.'


def parse_llm_json(response_text: str, model_cls: type) -> Any:
    'Parse and validate LLM JSON output via Pydantic (two-strategy fallback).'
    # Strategy 1: direct parse
    try:
        data = json.loads(response_text)
        return model_cls(**data)
    except Exception:
        pass

    # Strategy 2: extract first {...} block
    m = re.search(r'\{.*\}', response_text, re.DOTALL)
    if m:
        try:
            data = json.loads(m.group())
            return model_cls(**data)
        except Exception:
            pass

    raise LLMOutputError(
        f"Cannot parse LLM output as {model_cls.__name__}.\n"
        f"Response (first 500 chars): {response_text[:500]}"
    )


# -- Video Title Fetcher --

def fetch_video_title(video_id: str) -> str:
    'Fetch video title via lightweight HTTP request (no API key needed).'
    import urllib.request
    url = f"https://www.youtube.com/watch?v={video_id}"
    try:
        req = urllib.request.Request(
            url, headers={"User-Agent": "Mozilla/5.0 (compatible; DeepNotesBot/1.0)"}
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
        for pat in [
            r'<title>(.*?) - YouTube</title>',
            r'"og:title"\s+content="([^"]+)"',
            r'"title":"([^"]+)"',
        ]:
            m = re.search(pat, html)
            if m:
                title = m.group(1).strip()
                for esc, rep in [("&amp;", "&"), ("&#39;", "'"),
                                  ("&quot;", '"'), ("&lt;", "<"), ("&gt;", ">")]:
                    title = title.replace(esc, rep)
                return title
    except Exception as exc:
        logger.debug("Title fetch failed for %s: %s", video_id, exc)
    return f"YouTube Video ({video_id})"


print("✅ Middleware layer ready")
print("   URL validation + Prompt injection guard + Retry + LLM validator + Title fetcher")
