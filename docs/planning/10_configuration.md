# 10 — Configuration

## Design Philosophy

All configuration is externalised. No hardcoded values exist in source code. Configuration is loaded once at startup from environment variables and a `.env` file using Pydantic `BaseSettings`.

---

## Configuration Sources

| Priority | Source | Notes |
|----------|--------|-------|
| 1 (highest) | Shell environment variables | Override everything |
| 2 | `.env` file in project root | Loaded by `python-dotenv` |
| 3 | `BaseSettings` field defaults | Safe defaults where appropriate |

---

## Settings Model

**File:** `deep_notes_ai/config/settings.py`

```python
from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):

    # ── LLM Provider API Keys ─────────────────────────────────────────────────
    openai_api_key: str = Field(..., alias="OPENAI_API_KEY")
    nvidia_api_key: str = Field(default="", alias="NVIDIA_API_KEY")

    # ── LLM Model Configuration ───────────────────────────────────────────────
    cleaning_model_provider: str = Field(default="openai", alias="CLEANING_MODEL_PROVIDER")
    cleaning_model_name: str = Field(default="gpt-4o-mini", alias="CLEANING_MODEL_NAME")

    hierarchy_model_provider: str = Field(default="openai", alias="HIERARCHY_MODEL_PROVIDER")
    hierarchy_model_name: str = Field(default="gpt-4o-mini", alias="HIERARCHY_MODEL_NAME")

    content_model_provider: str = Field(default="openai", alias="CONTENT_MODEL_PROVIDER")
    content_model_name: str = Field(default="gpt-4o-mini", alias="CONTENT_MODEL_NAME")

    summary_model_provider: str = Field(default="openai", alias="SUMMARY_MODEL_PROVIDER")
    summary_model_name: str = Field(default="gpt-4o-mini", alias="SUMMARY_MODEL_NAME")

    # ── LLM Behaviour ─────────────────────────────────────────────────────────
    llm_temperature: float = Field(default=0.0, alias="LLM_TEMPERATURE")

    # ── Retry Configuration ───────────────────────────────────────────────────
    max_retries: int = Field(default=2, alias="MAX_RETRIES")

    # ── Partition Configuration ───────────────────────────────────────────────
    content_initial_partitions: int = Field(default=4, alias="CONTENT_INITIAL_PARTITIONS")
    content_fallback_partitions: int = Field(default=6, alias="CONTENT_FALLBACK_PARTITIONS")
    summary_initial_partitions: int = Field(default=4, alias="SUMMARY_INITIAL_PARTITIONS")
    summary_fallback_partitions: int = Field(default=6, alias="SUMMARY_FALLBACK_PARTITIONS")

    # ── Path Configuration ────────────────────────────────────────────────────
    output_base_dir: Path = Field(default=Path("output"), alias="OUTPUT_BASE_DIR")
    artefacts_dir: Path = Field(default=Path("artefacts"), alias="ARTEFACTS_DIR")
    prompts_dir: Path = Field(
        default=Path("deep_notes_ai/domain/prompts"),
        alias="PROMPTS_DIR",
    )
    checkpoints_db: Path = Field(
        default=Path("artefacts/checkpoints.db"),
        alias="CHECKPOINTS_DB",
    )

    # ── Feature Flags ─────────────────────────────────────────────────────────
    use_sqlite_checkpointer: bool = Field(default=True, alias="USE_SQLITE_CHECKPOINTER")
    enable_structured_logging: bool = Field(default=True, alias="ENABLE_STRUCTURED_LOGGING")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        populate_by_name=True,
        extra="ignore",
    )
```

---

## Environment Variables Reference

### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `OPENAI_API_KEY` | OpenAI API key | `sk-...` |

### Optional Variables (with defaults)

| Variable | Default | Description |
|----------|---------|-------------|
| `NVIDIA_API_KEY` | `""` | NVIDIA NIM API key (only if using NVIDIA models) |
| `CLEANING_MODEL_PROVIDER` | `openai` | Provider for transcript cleaning LLM |
| `CLEANING_MODEL_NAME` | `gpt-4o-mini` | Model name for transcript cleaning |
| `HIERARCHY_MODEL_PROVIDER` | `openai` | Provider for hierarchy generation LLM |
| `HIERARCHY_MODEL_NAME` | `gpt-4o-mini` | Model name for hierarchy generation |
| `CONTENT_MODEL_PROVIDER` | `openai` | Provider for content structuring LLM |
| `CONTENT_MODEL_NAME` | `gpt-4o-mini` | Model name for content structuring |
| `SUMMARY_MODEL_PROVIDER` | `openai` | Provider for summary generation LLM |
| `SUMMARY_MODEL_NAME` | `gpt-4o-mini` | Model name for summary generation |
| `LLM_TEMPERATURE` | `0.0` | Temperature for all LLM calls |
| `MAX_RETRIES` | `2` | Maximum retry attempts per batch call |
| `CONTENT_INITIAL_PARTITIONS` | `4` | Initial partition count for content generation |
| `CONTENT_FALLBACK_PARTITIONS` | `6` | Fallback partition count for content generation |
| `SUMMARY_INITIAL_PARTITIONS` | `4` | Initial partition count for summary generation |
| `SUMMARY_FALLBACK_PARTITIONS` | `6` | Fallback partition count for summary generation |
| `OUTPUT_BASE_DIR` | `output` | Base directory for per-video output |
| `ARTEFACTS_DIR` | `artefacts` | Directory for system artefacts (checkpoints, etc.) |
| `PROMPTS_DIR` | `deep_notes_ai/domain/prompts` | Directory containing prompt `.txt` files |
| `CHECKPOINTS_DB` | `artefacts/checkpoints.db` | Path to SQLite checkpoint database |
| `USE_SQLITE_CHECKPOINTER` | `true` | Use SQLite checkpointing (false = in-memory only) |
| `ENABLE_STRUCTURED_LOGGING` | `true` | Enable JSON structured logging |
| `LOG_LEVEL` | `INFO` | Logging level |

---

## Model Configuration

Each pipeline stage uses a specific LLM configured independently. This allows:
- Using a more capable model for hierarchy generation.
- Using a faster/cheaper model for summary generation.
- Switching providers per stage without changing code.

### Stage-to-model mapping (defaults)

| Stage | Provider | Model |
|-------|----------|-------|
| Transcript cleaning | openai | gpt-4o-mini |
| Hierarchy generation | openai | gpt-4o-mini |
| Content structuring | openai | gpt-4o-mini |
| Summary generation | openai | gpt-4o-mini |

### Overriding for production

```bash
# Use GPT-5 for hierarchy (higher quality hierarchy)
HIERARCHY_MODEL_NAME=gpt-4o

# Use cheaper model for summary (lower quality acceptable)
SUMMARY_MODEL_NAME=gpt-4o-mini

# Use NVIDIA for content (alternative provider)
CONTENT_MODEL_PROVIDER=nvidia
CONTENT_MODEL_NAME=meta/llama-3.3-70b-instruct
```

---

## Retry Configuration

```bash
MAX_RETRIES=2                      # 2 retries per batch call (3 total attempts)
CONTENT_INITIAL_PARTITIONS=4       # split transcript into 4 initial batches
CONTENT_FALLBACK_PARTITIONS=6      # fall back to 6 batches if any batch fails
```

**Rationale for defaults:**
- `MAX_RETRIES=2`: Balances reliability against cost. Most ID failures resolve within 1 retry.
- `INITIAL_PARTITIONS=4`: Observed to work well for ~600-point transcripts at gpt-4o-mini context limits.
- `FALLBACK_PARTITIONS=6`: 50% more partitions reduces per-batch token count by ~33%.

---

## Path Configuration

Per-video output is organised under `OUTPUT_BASE_DIR/{content_id}/`:

```
output/
  jGg_1h0qzaM/
    transcript_raw.txt                  (optional, for debugging)
    transcript_cleaned.md
    transcript_numbered.md
    transcript_hierarchy.json
    nodes_hierarchy.json
    nodes_content.json
    course_content.md
    course_summary.md
```

This ensures:
- Multiple videos can be processed without file collisions.
- Each video's artefacts are isolated.
- Re-running a video overwrites only its own directory.

---

## Prompt Configuration

Prompts are stored as plain text files in `PROMPTS_DIR`. The four prompt files are:

```
deep_notes_ai/domain/prompts/
  cleaning.txt      → used by clean_transcript node
  hierarchy.txt     → used by generate_hierarchy node
  content.txt       → used by generate_content node
  summary.txt       → used by generate_summaries node
```

To update a prompt, edit the `.txt` file and restart the application. No code changes required.

---

## Feature Flags

| Flag | Default | When to toggle |
|------|---------|----------------|
| `USE_SQLITE_CHECKPOINTER` | `true` | Set to `false` for in-memory testing or single-run CLI usage |
| `ENABLE_STRUCTURED_LOGGING` | `true` | Set to `false` for human-readable console logging during development |
| `LOG_LEVEL` | `INFO` | Set to `DEBUG` for verbose tracing during development |

---

## `.env` File Template

```bash
# Required
OPENAI_API_KEY=sk-...

# Optional — override defaults
# NVIDIA_API_KEY=nvapi-...
# CLEANING_MODEL_NAME=gpt-4o-mini
# HIERARCHY_MODEL_NAME=gpt-4o
# CONTENT_MODEL_NAME=gpt-4o-mini
# SUMMARY_MODEL_NAME=gpt-4o-mini
# MAX_RETRIES=2
# CONTENT_INITIAL_PARTITIONS=4
# CONTENT_FALLBACK_PARTITIONS=6
# SUMMARY_INITIAL_PARTITIONS=4
# SUMMARY_FALLBACK_PARTITIONS=6
# OUTPUT_BASE_DIR=output
# LOG_LEVEL=INFO
```

---

## Settings Singleton Pattern

The `Settings` object is instantiated once at application start and injected into components via constructor:

```python
# main.py
settings = Settings()
transcript_service = TranscriptService()
persistence_service = PersistenceService(base_dir=settings.output_base_dir)
llm_service = LLMService(settings=settings)
# ... etc
```

Components that need configuration receive `Settings` or relevant sub-fields via constructor injection. They do not call `Settings()` internally.
