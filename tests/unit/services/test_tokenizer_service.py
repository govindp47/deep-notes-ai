"""
tests/unit/services/test_tokenizer_service.py

Unit tests for TokenizerService.

Uses a real tiktoken encoder — no network calls (tiktoken encodes offline).
"""
import pytest

from deep_notes_ai.services.tokenizer_service import TokenizerService


@pytest.fixture
def service() -> TokenizerService:
    return TokenizerService(model_name="gpt-4o-mini")


# ---------------------------------------------------------------------------
# count_tokens — basic behaviour
# ---------------------------------------------------------------------------

def test_count_tokens_empty_string_returns_zero(service: TokenizerService) -> None:
    assert service.count_tokens("") == 0


def test_count_tokens_non_empty_returns_positive_integer(service: TokenizerService) -> None:
    count = service.count_tokens("Hello, world!")
    assert isinstance(count, int)
    assert count > 0


def test_count_tokens_longer_text_has_more_tokens(service: TokenizerService) -> None:
    short_count = service.count_tokens("Hello.")
    long_count = service.count_tokens("Hello. " * 100)
    assert long_count > short_count


def test_count_tokens_whitespace_only_returns_positive(service: TokenizerService) -> None:
    # A space is a valid token in tiktoken encodings.
    count = service.count_tokens("   ")
    assert count > 0


def test_count_tokens_single_word(service: TokenizerService) -> None:
    count = service.count_tokens("transcript")
    assert count >= 1


def test_count_tokens_multiline_text(service: TokenizerService) -> None:
    text = "1. First point.\n2. Second point.\n3. Third point."
    count = service.count_tokens(text)
    assert count > 0


# ---------------------------------------------------------------------------
# fallback encoding for unknown model
# ---------------------------------------------------------------------------

def test_unknown_model_falls_back_gracefully() -> None:
    """TokenizerService must not raise for an unrecognised model name."""
    service = TokenizerService(model_name="unknown-model-xyz-999")
    count = service.count_tokens("hello world")
    assert count > 0


# ---------------------------------------------------------------------------
# determinism
# ---------------------------------------------------------------------------

def test_same_text_always_returns_same_count(service: TokenizerService) -> None:
    text = "Determinism check: every call must return the same value."
    assert service.count_tokens(text) == service.count_tokens(text)
