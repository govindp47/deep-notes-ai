"""
deep_notes_ai/services/prompt_service.py

PromptService — load prompt templates from files.
"""
from __future__ import annotations

import logging
from pathlib import Path

from langchain_core.prompts import ChatPromptTemplate

from deep_notes_ai.domain.models import PromptNotFoundError

logger = logging.getLogger(__name__)


class PromptService:
    """
    Load prompt templates from .txt files and return ChatPromptTemplate instances.

    Prompt files are plain text with {VARIABLE} placeholders.
    Templates are cached in memory after first load.

    Prompt names:
        "cleaning"  → cleaning.txt   (variable: RAW_TRANSCRIPT)
        "hierarchy" → hierarchy.txt  (variable: CLEANED_NUMBERED_TRANSCRIPT)
        "content"   → content.txt    (variable: NODES_CONTENT)
        "summary"   → summary.txt    (variable: NODES_CONTENT)
    """

    def __init__(self, prompts_dir: Path) -> None:
        self._prompts_dir = prompts_dir
        self._cache: dict[str, ChatPromptTemplate] = {}

    def load(self, name: str) -> ChatPromptTemplate:
        """
        Load a prompt template by name.

        ``name`` maps to ``{prompts_dir}/{name}.txt``.

        Args:
            name: Prompt name without extension (e.g. "cleaning").

        Returns:
            A cached ChatPromptTemplate ready for chaining.

        Raises:
            PromptNotFoundError: if the corresponding .txt file does not exist.
        """
        if name in self._cache:
            logger.debug("Prompt '%s' returned from cache.", name)
            return self._cache[name]

        prompt_path = self._prompts_dir / f"{name}.txt"

        if not prompt_path.exists():
            raise PromptNotFoundError(
                f"Prompt file not found: {prompt_path}"
            )

        template_text = prompt_path.read_text(encoding="utf-8")
        template = ChatPromptTemplate.from_template(template_text)

        self._cache[name] = template
        logger.debug("Prompt '%s' loaded and cached from %s.", name, prompt_path)
        return template
