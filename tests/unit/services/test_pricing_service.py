"""
tests/unit/services/test_pricing_service.py

Unit tests for PricingService.

No real LLM calls. Pure arithmetic on the pricing table.
"""
from __future__ import annotations

import pytest

from deep_notes_ai.services.pricing_service import PricingService


@pytest.fixture
def service() -> PricingService:
    return PricingService()


# ---------------------------------------------------------------------------
# get_cost_per_1k
# ---------------------------------------------------------------------------

def test_known_openai_model_returns_tuple(service: PricingService) -> None:
    result = service.get_cost_per_1k("openai", "gpt-4o-mini")
    assert result is not None
    input_cost, output_cost = result
    assert input_cost > 0
    assert output_cost > 0


def test_known_nvidia_model_returns_tuple(service: PricingService) -> None:
    result = service.get_cost_per_1k("nvidia", "meta/llama-3.1-8b-instruct")
    assert result is not None


def test_provider_is_case_insensitive(service: PricingService) -> None:
    lower = service.get_cost_per_1k("openai", "gpt-4o-mini")
    upper = service.get_cost_per_1k("OpenAI", "gpt-4o-mini")
    assert lower == upper


def test_unknown_model_returns_none(service: PricingService) -> None:
    result = service.get_cost_per_1k("openai", "nonexistent-model-xyz")
    assert result is None


def test_unknown_provider_returns_none(service: PricingService) -> None:
    result = service.get_cost_per_1k("anthropic", "claude-3-opus")
    assert result is None


# ---------------------------------------------------------------------------
# calculate_cost
# ---------------------------------------------------------------------------

def test_calculate_cost_known_model(service: PricingService) -> None:
    # gpt-4o-mini: 0.00015 / 1k input, 0.0006 / 1k output
    cost = service.calculate_cost("openai", "gpt-4o-mini", 1000, 1000)
    assert cost is not None
    assert cost == pytest.approx(0.00015 + 0.0006, rel=1e-6)


def test_calculate_cost_zero_tokens(service: PricingService) -> None:
    cost = service.calculate_cost("openai", "gpt-4o-mini", 0, 0)
    assert cost == pytest.approx(0.0, abs=1e-10)


def test_calculate_cost_none_input_tokens_returns_none(service: PricingService) -> None:
    cost = service.calculate_cost("openai", "gpt-4o-mini", None, 100)
    assert cost is None


def test_calculate_cost_none_output_tokens_returns_none(service: PricingService) -> None:
    cost = service.calculate_cost("openai", "gpt-4o-mini", 100, None)
    assert cost is None


def test_calculate_cost_unknown_model_returns_none(service: PricingService) -> None:
    cost = service.calculate_cost("openai", "no-such-model", 1000, 1000)
    assert cost is None


def test_calculate_cost_unknown_provider_returns_none(service: PricingService) -> None:
    cost = service.calculate_cost("anthropic", "claude-3-opus", 1000, 1000)
    assert cost is None


def test_calculate_cost_large_token_count(service: PricingService) -> None:
    # Verify no overflow / precision issues with large counts.
    cost = service.calculate_cost("openai", "gpt-4o-mini", 1_000_000, 500_000)
    assert cost is not None
    assert cost > 0


def test_calculate_cost_multiple_providers(service: PricingService) -> None:
    """Different providers with same token counts should produce different costs."""
    openai_cost = service.calculate_cost("openai", "gpt-4o", 1000, 1000)
    nvidia_cost = service.calculate_cost("nvidia", "meta/llama-3.1-8b-instruct", 1000, 1000)
    assert openai_cost is not None
    assert nvidia_cost is not None
    # GPT-4o is much more expensive than Llama 8B.
    assert openai_cost > nvidia_cost


def test_calculate_cost_returns_float(service: PricingService) -> None:
    cost = service.calculate_cost("openai", "gpt-4o-mini", 100, 50)
    assert isinstance(cost, float)


def test_gpt5_mini_priced(service: PricingService) -> None:
    """gpt-5-mini is in the pricing table (placeholder pricing)."""
    result = service.get_cost_per_1k("openai", "gpt-5-mini")
    assert result is not None
