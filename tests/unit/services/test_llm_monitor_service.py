"""
tests/unit/services/test_llm_monitor_service.py

Unit tests for LLMMonitorService.

All LLM calls are mocked. No real API calls.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from deep_notes_ai.domain.models import LLMCallRecord, LLMUsageSummary
from deep_notes_ai.services.llm_monitor_service import LLMMonitorService
from deep_notes_ai.services.persistence_service import PersistenceService
from deep_notes_ai.services.pricing_service import PricingService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_service() -> tuple[LLMMonitorService, PersistenceService]:
    pricing = PricingService()
    persistence = PersistenceService()
    monitor = LLMMonitorService(pricing_service=pricing, persistence_service=persistence)
    return monitor, persistence


def _make_record(
    node_name: str = "clean_transcript",
    operation_name: str = "Transcript Cleaning",
    provider: str = "openai",
    model: str = "gpt-4o-mini",
    input_tokens: int | None = 100,
    output_tokens: int | None = 50,
    total_tokens: int | None = 150,
    duration_ms: float = 250.0,
    success: bool = True,
    retry_number: int = 1,
    exception_type: str | None = None,
    exception_message: str | None = None,
    estimated_cost: float | None = None,
) -> LLMCallRecord:
    now = datetime.now(timezone.utc)
    return LLMCallRecord(
        node_name=node_name,
        operation_name=operation_name,
        provider=provider,
        model=model,
        started_at=now,
        finished_at=now,
        duration_ms=duration_ms,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=total_tokens,
        estimated_cost=estimated_cost,
        success=success,
        retry_number=retry_number,
        exception_type=exception_type,
        exception_message=exception_message,
    )


# ---------------------------------------------------------------------------
# record() and get_all_calls()
# ---------------------------------------------------------------------------

def test_record_appends_call() -> None:
    monitor, _ = _make_service()
    rec = _make_record()
    monitor.record(rec)
    assert len(monitor.get_all_calls()) == 1


def test_get_all_calls_returns_snapshot() -> None:
    """Modifying the returned list does not affect internal state."""
    monitor, _ = _make_service()
    monitor.record(_make_record())
    calls = monitor.get_all_calls()
    calls.clear()
    assert len(monitor.get_all_calls()) == 1


def test_multiple_records_accumulated() -> None:
    monitor, _ = _make_service()
    for i in range(5):
        monitor.record(_make_record(retry_number=i + 1))
    assert len(monitor.get_all_calls()) == 5


# ---------------------------------------------------------------------------
# build_summary()
# ---------------------------------------------------------------------------

def test_summary_empty_monitor() -> None:
    monitor, _ = _make_service()
    summary = monitor.build_summary()
    assert summary.total_calls == 0
    assert summary.successful_calls == 0
    assert summary.failed_calls == 0
    assert summary.total_input_tokens == 0
    assert summary.total_output_tokens == 0
    assert summary.total_tokens == 0
    assert summary.estimated_total_cost is None
    assert summary.total_duration_ms == 0.0


def test_summary_successful_calls_counted() -> None:
    monitor, _ = _make_service()
    monitor.record(_make_record(success=True))
    monitor.record(_make_record(success=True))
    monitor.record(_make_record(success=False, exception_type="ValueError"))
    summary = monitor.build_summary()
    assert summary.total_calls == 3
    assert summary.successful_calls == 2
    assert summary.failed_calls == 1


def test_summary_token_aggregation() -> None:
    monitor, _ = _make_service()
    monitor.record(_make_record(input_tokens=100, output_tokens=50, total_tokens=150))
    monitor.record(_make_record(input_tokens=200, output_tokens=100, total_tokens=300))
    summary = monitor.build_summary()
    assert summary.total_input_tokens == 300
    assert summary.total_output_tokens == 150
    assert summary.total_tokens == 450


def test_summary_none_tokens_treated_as_zero() -> None:
    monitor, _ = _make_service()
    monitor.record(_make_record(input_tokens=None, output_tokens=None, total_tokens=None))
    summary = monitor.build_summary()
    assert summary.total_input_tokens == 0
    assert summary.total_output_tokens == 0


def test_summary_cost_aggregation() -> None:
    monitor, _ = _make_service()
    monitor.record(_make_record(estimated_cost=0.001))
    monitor.record(_make_record(estimated_cost=0.002))
    summary = monitor.build_summary()
    assert summary.estimated_total_cost == pytest.approx(0.003, rel=1e-6)


def test_summary_no_costs_returns_none() -> None:
    monitor, _ = _make_service()
    monitor.record(_make_record(estimated_cost=None))
    summary = monitor.build_summary()
    assert summary.estimated_total_cost is None


def test_summary_duration_aggregation() -> None:
    monitor, _ = _make_service()
    monitor.record(_make_record(duration_ms=100.0))
    monitor.record(_make_record(duration_ms=200.0))
    summary = monitor.build_summary()
    assert summary.total_duration_ms == pytest.approx(300.0, rel=1e-6)


# ---------------------------------------------------------------------------
# Multiple nodes
# ---------------------------------------------------------------------------

def test_multiple_nodes_recorded(tmp_path: Path) -> None:
    monitor, _ = _make_service()
    monitor.record(_make_record(node_name="clean_transcript", operation_name="Transcript Cleaning"))
    monitor.record(_make_record(node_name="generate_hierarchy", operation_name="Hierarchy Generation"))
    monitor.record(_make_record(node_name="generate_content", operation_name="Content Generation"))
    calls = monitor.get_all_calls()
    nodes = {c.node_name for c in calls}
    assert nodes == {"clean_transcript", "generate_hierarchy", "generate_content"}


# ---------------------------------------------------------------------------
# Multiple providers
# ---------------------------------------------------------------------------

def test_multiple_providers_in_summary() -> None:
    monitor, _ = _make_service()
    monitor.record(_make_record(provider="openai", model="gpt-4o-mini", input_tokens=100, output_tokens=50))
    monitor.record(_make_record(provider="nvidia", model="meta/llama-3.1-8b-instruct", input_tokens=200, output_tokens=100))
    summary = monitor.build_summary()
    assert summary.total_calls == 2
    assert summary.total_input_tokens == 300


# ---------------------------------------------------------------------------
# Retry recording — each attempt is its own record
# ---------------------------------------------------------------------------

def test_retry_records_are_separate() -> None:
    monitor, _ = _make_service()
    monitor.record(_make_record(retry_number=1, success=False, exception_type="ValueError"))
    monitor.record(_make_record(retry_number=2, success=False, exception_type="ValueError"))
    monitor.record(_make_record(retry_number=3, success=True))
    calls = monitor.get_all_calls()
    assert len(calls) == 3
    assert calls[0].retry_number == 1
    assert calls[1].retry_number == 2
    assert calls[2].retry_number == 3


def test_failed_call_has_exception_info() -> None:
    monitor, _ = _make_service()
    monitor.record(_make_record(
        success=False,
        exception_type="TimeoutError",
        exception_message="Request timed out",
        input_tokens=None,
        output_tokens=None,
    ))
    calls = monitor.get_all_calls()
    assert calls[0].exception_type == "TimeoutError"
    assert calls[0].exception_message == "Request timed out"
    assert not calls[0].success


# ---------------------------------------------------------------------------
# JSON report
# ---------------------------------------------------------------------------

def test_json_report_structure(tmp_path: Path) -> None:
    monitor, persistence = _make_service()
    monitor.record(_make_record(estimated_cost=0.001))

    json_path = tmp_path / "llm_usage.json"
    md_path = tmp_path / "llm_usage.md"

    monitor.save_reports(tmp_path)

    assert json_path.exists()
    assert md_path.exists()

    data = json.loads(json_path.read_text(encoding="utf-8"))
    assert "calls" in data
    assert "summary" in data
    assert "per_node" in data
    assert "per_operation" in data
    assert "per_provider" in data
    assert "per_model" in data
    assert len(data["calls"]) == 1


def test_json_report_call_fields(tmp_path: Path) -> None:
    monitor, _ = _make_service()
    monitor.record(_make_record(
        node_name="clean_transcript",
        operation_name="Transcript Cleaning",
        provider="openai",
        model="gpt-4o-mini",
        input_tokens=100,
        output_tokens=50,
        total_tokens=150,
        duration_ms=300.0,
        retry_number=1,
        success=True,
    ))
    monitor.save_reports(tmp_path)
    data = json.loads((tmp_path / "llm_usage.json").read_text(encoding="utf-8"))
    call = data["calls"][0]
    assert call["node_name"] == "clean_transcript"
    assert call["operation_name"] == "Transcript Cleaning"
    assert call["provider"] == "openai"
    assert call["model"] == "gpt-4o-mini"
    assert call["input_tokens"] == 100
    assert call["output_tokens"] == 50
    assert call["total_tokens"] == 150
    assert call["success"] is True
    assert call["retry_number"] == 1


def test_json_report_failed_call(tmp_path: Path) -> None:
    monitor, _ = _make_service()
    monitor.record(_make_record(
        success=False,
        exception_type="LLMCallError",
        exception_message="API timeout",
        input_tokens=None,
        output_tokens=None,
        total_tokens=None,
        estimated_cost=None,
    ))
    monitor.save_reports(tmp_path)
    data = json.loads((tmp_path / "llm_usage.json").read_text(encoding="utf-8"))
    call = data["calls"][0]
    assert call["success"] is False
    assert call["exception_type"] == "LLMCallError"


def test_json_report_empty_calls(tmp_path: Path) -> None:
    monitor, _ = _make_service()
    monitor.save_reports(tmp_path)
    data = json.loads((tmp_path / "llm_usage.json").read_text(encoding="utf-8"))
    assert data["calls"] == []
    assert data["summary"]["total_calls"] == 0


# ---------------------------------------------------------------------------
# Markdown report
# ---------------------------------------------------------------------------

def test_markdown_report_generated(tmp_path: Path) -> None:
    monitor, _ = _make_service()
    monitor.record(_make_record())
    monitor.save_reports(tmp_path)
    md = (tmp_path / "llm_usage.md").read_text(encoding="utf-8")
    assert "# LLM Usage Report" in md


def test_markdown_report_has_pipeline_summary(tmp_path: Path) -> None:
    monitor, _ = _make_service()
    monitor.record(_make_record())
    monitor.save_reports(tmp_path)
    md = (tmp_path / "llm_usage.md").read_text(encoding="utf-8")
    assert "Pipeline Summary" in md
    assert "Total Calls" in md


def test_markdown_report_has_per_node_section(tmp_path: Path) -> None:
    monitor, _ = _make_service()
    monitor.record(_make_record(node_name="generate_content"))
    monitor.save_reports(tmp_path)
    md = (tmp_path / "llm_usage.md").read_text(encoding="utf-8")
    assert "Per-Node Breakdown" in md
    assert "generate_content" in md


def test_markdown_report_has_per_model_section(tmp_path: Path) -> None:
    monitor, _ = _make_service()
    monitor.record(_make_record(model="gpt-4o-mini"))
    monitor.save_reports(tmp_path)
    md = (tmp_path / "llm_usage.md").read_text(encoding="utf-8")
    assert "Per-Model Breakdown" in md
    assert "gpt-4o-mini" in md


def test_markdown_report_individual_calls_table(tmp_path: Path) -> None:
    monitor, _ = _make_service()
    monitor.record(_make_record())
    monitor.save_reports(tmp_path)
    md = (tmp_path / "llm_usage.md").read_text(encoding="utf-8")
    assert "Individual Calls" in md


def test_markdown_report_empty_calls_message(tmp_path: Path) -> None:
    monitor, _ = _make_service()
    monitor.save_reports(tmp_path)
    md = (tmp_path / "llm_usage.md").read_text(encoding="utf-8")
    assert "No LLM calls recorded" in md


# ---------------------------------------------------------------------------
# Aggregations
# ---------------------------------------------------------------------------

def test_per_node_aggregation(tmp_path: Path) -> None:
    monitor, _ = _make_service()
    monitor.record(_make_record(node_name="clean_transcript", duration_ms=100.0))
    monitor.record(_make_record(node_name="clean_transcript", duration_ms=200.0))
    monitor.record(_make_record(node_name="generate_hierarchy", duration_ms=150.0))
    monitor.save_reports(tmp_path)
    data = json.loads((tmp_path / "llm_usage.json").read_text(encoding="utf-8"))
    assert data["per_node"]["clean_transcript"]["calls"] == 2
    assert data["per_node"]["generate_hierarchy"]["calls"] == 1


def test_per_provider_aggregation(tmp_path: Path) -> None:
    monitor, _ = _make_service()
    monitor.record(_make_record(provider="openai"))
    monitor.record(_make_record(provider="openai"))
    monitor.record(_make_record(provider="nvidia"))
    monitor.save_reports(tmp_path)
    data = json.loads((tmp_path / "llm_usage.json").read_text(encoding="utf-8"))
    assert data["per_provider"]["openai"]["calls"] == 2
    assert data["per_provider"]["nvidia"]["calls"] == 1


def test_per_operation_aggregation(tmp_path: Path) -> None:
    monitor, _ = _make_service()
    monitor.record(_make_record(operation_name="Transcript Cleaning"))
    monitor.record(_make_record(operation_name="Hierarchy Generation"))
    monitor.record(_make_record(operation_name="Hierarchy Generation"))
    monitor.save_reports(tmp_path)
    data = json.loads((tmp_path / "llm_usage.json").read_text(encoding="utf-8"))
    assert data["per_operation"]["Transcript Cleaning"]["calls"] == 1
    assert data["per_operation"]["Hierarchy Generation"]["calls"] == 2


# ---------------------------------------------------------------------------
# Cost calculation integration (end-to-end through pricing service)
# ---------------------------------------------------------------------------

def test_cost_calculated_for_known_model() -> None:
    """Verifies monitor computes cost correctly using real PricingService."""
    pricing = PricingService()
    persistence = PersistenceService()
    monitor = LLMMonitorService(pricing_service=pricing, persistence_service=persistence)

    # gpt-4o-mini: 0.00015/1k input + 0.0006/1k output
    expected_cost = (1000 / 1000) * 0.00015 + (500 / 1000) * 0.0006
    monitor.record(_make_record(
        model="gpt-4o-mini",
        provider="openai",
        input_tokens=1000,
        output_tokens=500,
        estimated_cost=pricing.calculate_cost("openai", "gpt-4o-mini", 1000, 500),
    ))
    summary = monitor.build_summary()
    assert summary.estimated_total_cost == pytest.approx(expected_cost, rel=1e-6)


# ---------------------------------------------------------------------------
# Persistence integration
# ---------------------------------------------------------------------------

def test_save_reports_creates_both_files(tmp_path: Path) -> None:
    monitor, _ = _make_service()
    monitor.record(_make_record())
    monitor.save_reports(tmp_path)
    assert (tmp_path / "llm_usage.json").exists()
    assert (tmp_path / "llm_usage.md").exists()


def test_save_reports_with_no_calls(tmp_path: Path) -> None:
    monitor, _ = _make_service()
    monitor.save_reports(tmp_path)
    assert (tmp_path / "llm_usage.json").exists()
    assert (tmp_path / "llm_usage.md").exists()


def test_save_reports_creates_parent_dirs(tmp_path: Path) -> None:
    monitor, _ = _make_service()
    nested_dir = tmp_path / "a" / "b" / "c"
    monitor.record(_make_record())
    monitor.save_reports(nested_dir)
    assert (nested_dir / "llm_usage.json").exists()


# ---------------------------------------------------------------------------
# Duration recording
# ---------------------------------------------------------------------------

def test_duration_recorded_in_ms(tmp_path: Path) -> None:
    monitor, _ = _make_service()
    monitor.record(_make_record(duration_ms=1234.56))
    summary = monitor.build_summary()
    assert summary.total_duration_ms == pytest.approx(1234.56, rel=1e-4)

    monitor.save_reports(tmp_path)
    data = json.loads((tmp_path / "llm_usage.json").read_text(encoding="utf-8"))
    assert data["calls"][0]["duration_ms"] == pytest.approx(1234.56, rel=1e-4)


# ---------------------------------------------------------------------------
# Unknown model — cost must be None, no failure
# ---------------------------------------------------------------------------

def test_unknown_model_cost_is_none_no_failure() -> None:
    pricing = PricingService()
    persistence = PersistenceService()
    monitor = LLMMonitorService(pricing_service=pricing, persistence_service=persistence)

    monitor.record(_make_record(
        provider="openai",
        model="nonexistent-model-xyz",
        estimated_cost=pricing.calculate_cost("openai", "nonexistent-model-xyz", 1000, 500),
    ))
    summary = monitor.build_summary()
    # Cost should be None, not raise.
    assert summary.estimated_total_cost is None
