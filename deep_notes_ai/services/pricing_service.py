"""
deep_notes_ai/services/pricing_service.py

PricingService — single point of responsibility for LLM cost calculation.

All model pricing lives here. Nothing else in the codebase contains pricing.
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Pricing table
#
# Structure: {(provider_lower, model_name): (input_cost_per_1k, output_cost_per_1k)}
# Costs are in USD per 1 000 tokens.
# ---------------------------------------------------------------------------

_PRICING_TABLE: dict[tuple[str, str], tuple[float, float]] = {
    # -- OpenAI ---------------------------------------------------------------
    ("openai", "gpt-4o"):                       (0.0025, 0.01),
    ("openai", "gpt-4o-2024-11-20"):            (0.0025, 0.01),
    ("openai", "gpt-4o-2024-08-06"):            (0.0025, 0.01),
    ("openai", "gpt-4o-mini"):                  (0.00015, 0.0006),
    ("openai", "gpt-4o-mini-2024-07-18"):       (0.00015, 0.0006),
    ("openai", "gpt-4-turbo"):                  (0.01, 0.03),
    ("openai", "gpt-4-turbo-2024-04-09"):       (0.01, 0.03),
    ("openai", "gpt-4"):                        (0.03, 0.06),
    ("openai", "gpt-3.5-turbo"):                (0.0005, 0.0015),
    ("openai", "gpt-3.5-turbo-0125"):           (0.0005, 0.0015),
    ("openai", "gpt-5"):                        (0.00125, 0.01),
    ("openai", "gpt-5-mini"):                   (0.00025, 0.002),
    ("openai", "o1"):                           (0.015, 0.06),
    ("openai", "o1-mini"):                      (0.003, 0.012),
    ("openai", "o3-mini"):                      (0.0011, 0.0044),
    # -- NVIDIA ---------------------------------------------------------------
    ("nvidia", "meta/llama-3.1-8b-instruct"):   (0.0001, 0.0001),
    ("nvidia", "meta/llama-3.1-70b-instruct"):  (0.00035, 0.00035),
    ("nvidia", "meta/llama-3.1-405b-instruct"): (0.00035, 0.00035),
    ("nvidia", "meta/llama-3.3-70b-instruct"):  (0.00023, 0.00023),
    ("nvidia", "nvidia/llama-3.1-nemotron-70b-instruct"): (0.00035, 0.00035),
    ("nvidia", "mistralai/mixtral-8x7b-instruct-v0.1"):   (0.0006, 0.0006),
    ("nvidia", "mistralai/mistral-7b-instruct-v0.3"):      (0.0002, 0.0002),
}


class PricingService:
    """
    Calculate the estimated cost of an LLM call.

    - All pricing definitions live in this single class.
    - Unknown model+provider combinations return ``None`` -- never raise.
    - Cost is in USD.
    """

    def get_cost_per_1k(
        self,
        provider: str,
        model: str,
    ) -> tuple[float, float] | None:
        """
        Return (input_cost_per_1k_tokens, output_cost_per_1k_tokens) for the
        given provider and model, or None if the model is not known.

        Args:
            provider: Provider string (case-insensitive).
            model:    Model name string.

        Returns:
            A (input_cost, output_cost) tuple in USD / 1 000 tokens, or None.
        """
        key = (provider.lower(), model.lower())
        pricing = _PRICING_TABLE.get(key)
        if pricing is None:
            logger.debug(
                "No pricing found for provider=%r model=%r; cost will be None.",
                provider,
                model,
            )
        return pricing

    def calculate_cost(
        self,
        provider: str,
        model: str,
        input_tokens: int | None,
        output_tokens: int | None,
    ) -> float | None:
        """
        Estimate the total cost of one LLM call.

        Args:
            provider:      Provider string (case-insensitive).
            model:         Model name string.
            input_tokens:  Number of prompt tokens (may be None).
            output_tokens: Number of completion tokens (may be None).

        Returns:
            Estimated cost in USD, or None if pricing is unknown or token
            counts are unavailable.
        """
        if input_tokens is None or output_tokens is None:
            return None

        pricing = self.get_cost_per_1k(provider, model)
        if pricing is None:
            return None

        input_cost_per_1k, output_cost_per_1k = pricing
        cost = (input_tokens / 1_000) * input_cost_per_1k + (
            output_tokens / 1_000
        ) * output_cost_per_1k
        return round(cost, 8)
