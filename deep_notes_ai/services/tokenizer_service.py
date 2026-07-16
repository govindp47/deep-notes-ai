"""
deep_notes_ai/services/tokenizer_service.py

TokenizerService — count tokens for a given model using tiktoken.

Single point of responsibility: token counting.
The encoding is resolved and cached once at construction time.
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class TokenizerService:
    """
    Count tokens using tiktoken, matched to the project's cleaning LLM.

    - Encoding resolved by model name (tiktoken's ``encoding_for_model``).
    - Encoding instance cached on ``__init__`` — counted only once per service
      lifetime, not per call.
    - Falls back to ``cl100k_base`` if the model name is not recognised by
      tiktoken (covers future model renames without pipeline breakage).
    """

    def __init__(self, model_name: str) -> None:
        import tiktoken

        try:
            self._encoding = tiktoken.encoding_for_model(model_name)
            logger.debug(
                "TokenizerService initialised with encoding for model=%s", model_name
            )
        except KeyError:
            self._encoding = tiktoken.get_encoding("cl100k_base")
            logger.warning(
                "Unknown model name %r for tiktoken; falling back to cl100k_base.",
                model_name,
            )

    def count_tokens(self, text: str) -> int:
        """
        Count the number of tokens in text.

        Args:
            text: The text to tokenize.

        Returns:
            Number of tokens (0 for empty string).
        """
        if not text:
            return 0
        return len(self._encoding.encode(text))
