"""
deep_notes_ai/services/llm_service.py

LLMService — factory that constructs LLM client instances from configuration.

When an LLMMonitorService is provided, every model returned by this factory
carries a _MonitoringCallbackHandler injected into its default callbacks.
The handler transparently records every invocation across ALL execution modes:

    invoke / ainvoke / batch / abatch / stream / astream / with_structured_output

Nodes and higher-level services are completely unaware of monitoring.
"""
from __future__ import annotations

import logging
import threading
import time
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any
from uuid import UUID

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.language_models import BaseChatModel
from langchain_core.outputs import ChatGeneration, LLMResult
from langchain_core.runnables import Runnable
from pydantic import BaseModel

from deep_notes_ai.domain.models import LLMCallRecord, UnsupportedLLMProviderError

if TYPE_CHECKING:
    from deep_notes_ai.config.settings import Settings
    from deep_notes_ai.services.llm_monitor_service import LLMMonitorService

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Private monitoring callback handler
# ---------------------------------------------------------------------------

class _MonitoringCallbackHandler(BaseCallbackHandler):
    """
    LangChain callback handler that records every LLM invocation.

    Attached to a BaseChatModel's default_callbacks so it fires for every
    execution mode: invoke, ainvoke, batch, abatch, stream, astream, and
    with_structured_output chains — without any caller awareness.

    Thread-safety:
        All mutable state is keyed by run_id (a UUID assigned by LangChain
        per execution) and protected by a threading.Lock.  There is no shared
        mutable state across concurrent executions.

    Monitoring failures:
        All callback methods are fully guarded.  Any exception is logged at
        DEBUG level and suppressed so it can never interrupt pipeline execution.
    """

    # raise_error=False ensures LangChain never propagates handler exceptions.
    raise_error = False

    def __init__(
        self,
        node_name: str,
        operation_name: str,
        provider: str,
        model: str,
        monitor_service: "LLMMonitorService",
    ) -> None:
        super().__init__()
        self._node_name = node_name
        self._operation_name = operation_name
        self._provider = provider
        self._model = model
        self._monitor_service = monitor_service

        # Per-run state: {run_id: {"started_at", "start_ns", "retry_number"}}
        # Protected by _lock for thread-safe concurrent access.
        self._in_flight: dict[UUID, dict[str, Any]] = {}
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _start(self, run_id: UUID) -> None:
        """Record the start of a single LLM execution identified by run_id."""
        with self._lock:
            self._in_flight[run_id] = {
                "started_at": datetime.now(timezone.utc),
                "start_ns": time.perf_counter_ns(),
            }

    def _finish_success(self, run_id: UUID, response: LLMResult) -> None:
        """Record a successful LLM execution and emit a monitoring record."""
        with self._lock:
            run = self._in_flight.pop(run_id, None)

        if run is None:
            logger.debug("_MonitoringCallbackHandler: no start recorded for run_id=%s", run_id)
            return

        finished_at = datetime.now(timezone.utc)
        duration_ms = (time.perf_counter_ns() - run["start_ns"]) / 1_000_000

        input_tokens, output_tokens, total_tokens = _extract_token_usage_from_result(response)

        from deep_notes_ai.services.pricing_service import PricingService
        pricing_service = PricingService()
        estimated_cost = pricing_service.calculate_cost(
            provider=self._provider,
            model=self._model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )

        record = LLMCallRecord(
            node_name=self._node_name,
            operation_name=self._operation_name,
            provider=self._provider,
            model=self._model,
            started_at=run["started_at"],
            finished_at=finished_at,
            duration_ms=round(duration_ms, 2),
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            estimated_cost=estimated_cost,
            success=True,
            exception_type=None,
            exception_message=None,
        )
        self._monitor_service.record(record)


    def _finish_error(self, run_id: UUID, error: BaseException) -> None:
        """Record a failed LLM execution and emit a monitoring record."""
        with self._lock:
            run = self._in_flight.pop(run_id, None)

        if run is None:
            logger.debug("_MonitoringCallbackHandler: no start recorded for run_id=%s", run_id)
            return

        finished_at = datetime.now(timezone.utc)
        duration_ms = (time.perf_counter_ns() - run["start_ns"]) / 1_000_000

        record = LLMCallRecord(
            node_name=self._node_name,
            operation_name=self._operation_name,
            provider=self._provider,
            model=self._model,
            started_at=run["started_at"],
            finished_at=finished_at,
            duration_ms=round(duration_ms, 2),
            input_tokens=None,
            output_tokens=None,
            total_tokens=None,
            estimated_cost=None,
            success=False,
            exception_type=type(error).__name__,
            exception_message=str(error),
        )
        self._monitor_service.record(record)

    # ------------------------------------------------------------------
    # LangChain callback hooks — LLM events
    # ------------------------------------------------------------------

    def on_llm_start(
        self,
        serialized: dict[str, Any],
        prompts: list[str],
        *,
        run_id: UUID,
        **kwargs: Any,
    ) -> None:
        """Called before any LLM invocation (non-chat path; included for completeness)."""
        try:
            self._start(run_id)
        except Exception as exc:  # noqa: BLE001
            logger.debug("Monitoring on_llm_start failed: %s", exc)

    def on_chat_model_start(
        self,
        serialized: dict[str, Any],
        messages: list[list[Any]],
        *,
        run_id: UUID,
        **kwargs: Any,
    ) -> None:
        """Called before a chat model invocation (invoke / batch / stream)."""
        try:
            self._start(run_id)
        except Exception as exc:  # noqa: BLE001
            logger.debug("Monitoring on_chat_model_start failed: %s", exc)

    def on_llm_end(
        self,
        response: LLMResult,
        *,
        run_id: UUID,
        **kwargs: Any,
    ) -> None:
        """
        Called after every successful LLM execution including streaming.

        For streaming, LangChain fires this once after the stream is exhausted,
        making it the correct hook for a single consolidated streaming record.
        """
        try:
            self._finish_success(run_id, response)
        except Exception as exc:  # noqa: BLE001
            logger.debug("Monitoring on_llm_end failed: %s", exc)

    def on_llm_error(
        self,
        error: BaseException,
        *,
        run_id: UUID,
        **kwargs: Any,
    ) -> None:
        """Called when an LLM invocation raises an exception."""
        try:
            self._finish_error(run_id, error)
        except Exception as exc:  # noqa: BLE001
            logger.debug("Monitoring on_llm_error failed: %s", exc)


# ---------------------------------------------------------------------------
# Token usage extraction from LLMResult (callback payload)
# ---------------------------------------------------------------------------

def _extract_token_usage_from_result(
    response: LLMResult,
) -> tuple[int | None, int | None, int | None]:
    """
    Extract (input_tokens, output_tokens, total_tokens) from an LLMResult.

    Extraction order (most to least reliable):
      1. LLMResult.llm_output["token_usage"] — aggregated by provider adapters
         (OpenAI, NVIDIA, etc.)
      2. ChatGeneration.message.usage_metadata — per-message metadata from
         langchain-core >= 0.2 AIMessage.
      3. ChatGeneration.generation_info — fallback for older adapters.

    Args:
        response: The LLMResult delivered by LangChain to on_llm_end.

    Returns:
        (input_tokens, output_tokens, total_tokens) — any may be None.
        Values are never fabricated; None means data was not available.
    """
    # ------------------------------------------------------------------
    # Path 1: llm_output — most providers set this at the batch level.
    # ------------------------------------------------------------------
    llm_output = response.llm_output or {}
    token_usage = (
        llm_output.get("token_usage")
        or llm_output.get("usage")
        or {}
    )
    if isinstance(token_usage, dict) and token_usage:
        input_t = (
            token_usage.get("prompt_tokens")
            or token_usage.get("input_tokens")
        )
        output_t = (
            token_usage.get("completion_tokens")
            or token_usage.get("output_tokens")
        )
        total_t = token_usage.get("total_tokens")
        if input_t is not None or output_t is not None:
            return (
                int(input_t) if input_t is not None else None,
                int(output_t) if output_t is not None else None,
                int(total_t) if total_t is not None else None,
            )

    # ------------------------------------------------------------------
    # Path 2: ChatGeneration.message.usage_metadata (langchain-core >= 0.2).
    # Aggregate across all generations in case of batch calls.
    # ------------------------------------------------------------------
    agg_input: int | None = None
    agg_output: int | None = None
    agg_total: int | None = None

    for gen_list in response.generations:
        for gen in gen_list:
            if not isinstance(gen, ChatGeneration):
                continue
            msg = getattr(gen, "message", None)
            usage = getattr(msg, "usage_metadata", None)
            if isinstance(usage, dict):
                it = usage.get("input_tokens")
                ot = usage.get("output_tokens")
                tt = usage.get("total_tokens")
                if it is not None:
                    agg_input = (agg_input or 0) + int(it)
                if ot is not None:
                    agg_output = (agg_output or 0) + int(ot)
                if tt is not None:
                    agg_total = (agg_total or 0) + int(tt)

    if agg_input is not None or agg_output is not None:
        return agg_input, agg_output, agg_total

    # ------------------------------------------------------------------
    # Path 3: generation_info — older or non-standard adapters.
    # ------------------------------------------------------------------
    for gen_list in response.generations:
        for gen in gen_list:
            info = getattr(gen, "generation_info", None) or {}
            if not isinstance(info, dict):
                continue
            token_usage = info.get("token_usage") or info.get("usage") or {}
            if isinstance(token_usage, dict) and token_usage:
                input_t = (
                    token_usage.get("prompt_tokens")
                    or token_usage.get("input_tokens")
                )
                output_t = (
                    token_usage.get("completion_tokens")
                    or token_usage.get("output_tokens")
                )
                total_t = token_usage.get("total_tokens")
                if input_t is not None or output_t is not None:
                    return (
                        int(input_t) if input_t is not None else None,
                        int(output_t) if output_t is not None else None,
                        int(total_t) if total_t is not None else None,
                    )

    return None, None, None


# ---------------------------------------------------------------------------
# LLMService
# ---------------------------------------------------------------------------

class LLMService:
    """
    Factory for LLM client instances.

    - Reads API keys from the injected Settings (not from os.environ directly).
    - Each call creates a new client instance (no global singleton).
    - Provider string is case-insensitive.
    - When monitor_service is provided, attaches a _MonitoringCallbackHandler
      to every returned model's default_callbacks for transparent observability.

    Supported providers: "openai", "nvidia".
    """

    def __init__(
        self,
        settings: "Settings",
        monitor_service: "LLMMonitorService | None" = None,
    ) -> None:
        self._settings = settings
        self._monitor_service = monitor_service
    

    def _build_raw_model(
        self,
        provider: str,
        model: str,
        temperature: float = 0.0,
    ) -> BaseChatModel:
        """
        Return a configured chat model for the given provider.

        Args:
            provider:       "openai" or "nvidia" (case-insensitive).
            model:          The model name string (e.g. "gpt-4o-mini").
            temperature:    Sampling temperature.

        Returns:
            A configured BaseChatModel.

        Raises:
            UnsupportedLLMProviderError: if the provider is not recognised.
        """
        provider_lower = provider.lower()

        if provider_lower == "openai":
            from langchain_openai import ChatOpenAI
            logger.debug("Creating ChatOpenAI model=%s temperature=%s", model, temperature)
            return ChatOpenAI(
                model=model,
                temperature=temperature,
                api_key=self._settings.openai_api_key,  # type: ignore[arg-type]
            )

        elif provider_lower == "nvidia":
            from langchain_nvidia_ai_endpoints import ChatNVIDIA
            logger.debug("Creating ChatNVIDIA model=%s temperature=%s", model, temperature)
            return ChatNVIDIA(
                model=model,
                temperature=temperature,
                api_key=self._settings.nvidia_api_key,  # type: ignore[arg-type]
            )

        else:
            raise UnsupportedLLMProviderError(
                f"Unsupported LLM provider: {provider!r}. "
                "Supported providers are: 'openai', 'nvidia'."
            )
    

    def _attach_monitoring(
        self,
        runnable: Runnable,
        provider: str,
        model: str,
        node_name: str,
        operation_name: str,
    ) -> Runnable:
        if self._monitor_service is None:
            return runnable

        handler = _MonitoringCallbackHandler(
            node_name=node_name,
            operation_name=operation_name,
            provider=provider,
            model=model,
            monitor_service=self._monitor_service,
        )
        logger.debug("Attaching _MonitoringCallbackHandler node=%r operation=%r", node_name, operation_name)
        # Bind the handler into the model's default_callbacks so it is
        # inherited by every downstream Runnable (chains, structured output
        # parsers, batch runners, stream iterators) without any explicit
        # config threading by callers.
        return runnable.with_config(callbacks=[handler])
    
    
    def get_chat_model(
        self,
        provider: str,
        model: str,
        temperature: float = 0.0,
        node_name: str = "unknown",
        operation_name: str = "LLM Call",
    ) -> BaseChatModel:
        """
        Return a configured chat model for the given provider.

        When a monitor_service is active, the returned model carries a
        _MonitoringCallbackHandler in its default_callbacks.  All execution
        modes — invoke, ainvoke, batch, abatch, stream, astream, and any
        Runnable chain built from the model — are monitored automatically.

        Args:
            provider:       "openai" or "nvidia" (case-insensitive).
            model:          The model name string (e.g. "gpt-4o-mini").
            temperature:    Sampling temperature.
            node_name:      Pipeline node name for monitoring (e.g. "clean_transcript").
            operation_name: Human-readable operation label (e.g. "Transcript Cleaning").

        Returns:
            A configured BaseChatModel with monitoring attached.

        Raises:
            UnsupportedLLMProviderError: if the provider is not recognised.
        """
        provider_lower = provider.lower()
        raw_model = self._build_raw_model(provider, model, temperature)

        return self._attach_monitoring(
            runnable=raw_model,
            provider=provider_lower,
            model=model,
            node_name=node_name,
            operation_name=operation_name
        )
    

    def get_structured_model(
        self,
        provider: str,
        model: str,
        output_schema: type[BaseModel],
        temperature: float = 0.0,
        node_name: str = "unknown",
        operation_name: str = "LLM Call",
    ) -> Runnable:
        """
        Return a chat model configured for structured output.

        Build the structured chain from the RAW model — never from a
        model that already has .with_config(callbacks=...) applied,
        since with_structured_output()/bind_tools() on a RunnableBinding
        is proxied to the unwrapped bound model and silently drops it.

        Attach monitoring to the final chain so the handler is present
        in the callback manager for the whole run, including the
        nested chat-model step where token usage is emitted.

        Args:
            provider:      "openai" or "nvidia" (case-insensitive).
            model:         The model name string.
            output_schema: The Pydantic BaseModel subclass for structured output.
            temperature:   Sampling temperature.
            node_name:      Pipeline node name for monitoring.
            operation_name: Human-readable operation label.

        Returns:
            A Runnable that returns instances of output_schema.

        Raises:
            UnsupportedLLMProviderError: if the provider is not recognised.
        """
        provider_lower = provider.lower()
        raw_model = self._build_raw_model(provider, model, temperature)
        structured_chain = raw_model.with_structured_output(output_schema)

        return self._attach_monitoring(
            runnable=structured_chain,
            provider=provider_lower,
            model=model,
            node_name=node_name,
            operation_name=operation_name
        )
