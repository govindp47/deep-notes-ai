"""
deep_notes_ai/config/settings.py

Pydantic BaseSettings model. Reads from environment variables and a .env file.
All configuration is externalised — no hardcoded values in source code.
"""
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):

    # ── LLM Provider API Keys ─────────────────────────────────────────────────
    openai_api_key: str = Field(..., alias="OPENAI_API_KEY")
    nvidia_api_key: str = Field(default="", alias="NVIDIA_API_KEY")

    # ── Multi-Part Processing ─────────────────────────────────────────────────────
    transcript_max_tokens_per_part: int = Field(default=50_000, alias="TRANSCRIPT_MAX_TOKENS_PER_PART")

    # ── LLM Model Configuration ───────────────────────────────────────────────
    cleaning_model_provider: str = Field(default="openai", alias="CLEANING_MODEL_PROVIDER")
    cleaning_model_name: str = Field(default="gpt-4o-mini", alias="CLEANING_MODEL_NAME")
    cleaning_model_temperature: float = Field(default=0.0, alias="CLEANING_MODEL_TEMPERATURE")
    cleaning_chunk_tokens: int = Field(default=6000, alias="CLEANING_CHUNK_TOKENS")
    cleaning_chunk_overlap_chars: int = Field(default=500, alias="CLEANING_CHUNK_OVERLAP_CHARS")

    hierarchy_model_provider: str = Field(default="openai", alias="HIERARCHY_MODEL_PROVIDER")
    hierarchy_model_name: str = Field(default="gpt-5-mini", alias="HIERARCHY_MODEL_NAME")
    hierarchy_model_temperature: float = Field(default=0.0, alias="HIERARCHY_MODEL_TEMPERATURE")
    hierarchy_input_tokens: int = Field(default=18000, alias="HIERARCHY_INPUT_TOKENS")

    content_model_provider: str = Field(default="openai", alias="CONTENT_MODEL_PROVIDER")
    content_model_name: str = Field(default="gpt-5-mini", alias="CONTENT_MODEL_NAME")
    content_model_temperature: float = Field(default=0.0, alias="CONTENT_MODEL_TEMPERATURE")
    content_input_tokens: int = Field(default=8000, alias="CONTENT_INPUT_TOKENS")
    content_input_tokens_fallback: int = Field(default=6000, alias="CONTENT_INPUT_TOKENS_FALLBACK")

    summary_model_provider: str = Field(default="openai", alias="SUMMARY_MODEL_PROVIDER")
    summary_model_name: str = Field(default="gpt-4o-mini", alias="SUMMARY_MODEL_NAME")
    summary_model_temperature: float = Field(default=0.0, alias="SUMMARY_MODEL_TEMPERATURE")
    summary_input_tokens: int = Field(default=5000, alias="SUMMARY_INPUT_TOKENS")
    summary_input_tokens_fallback: int = Field(default=4000, alias="SUMMARY_INPUT_TOKENS_FALLBACK")

    # ── Retry Configuration ───────────────────────────────────────────────────
    max_retries: int = Field(default=1, alias="MAX_RETRIES")

    # ── Path Configuration ────────────────────────────────────────────────────
    output_base_dir: Path = Field(default=Path("output"), alias="OUTPUT_BASE_DIR")
    artefacts_dir: Path = Field(default=Path("artefacts"), alias="ARTEFACTS_DIR")
    prompts_dir: Path = Field(default=Path("deep_notes_ai/domain/prompts"), alias="PROMPTS_DIR")
    logs_dir: Path = Field(default=Path("logs"), alias="LOGS_DIR")
    checkpoints_db: Path = Field(default=Path("artefacts/checkpoints.db"), alias="CHECKPOINTS_DB")

    # ── Feature Flags ─────────────────────────────────────────────────────────────
    use_sqlite_checkpointer: bool = Field(default=True, alias="USE_SQLITE_CHECKPOINTER")
    enable_structured_logging: bool = Field(default=True, alias="ENABLE_STRUCTURED_LOGGING")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    enable_llm_monitoring: bool = Field(default=True, alias="ENABLE_LLM_MONITORING")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        populate_by_name=True,
        extra="ignore",
    )
