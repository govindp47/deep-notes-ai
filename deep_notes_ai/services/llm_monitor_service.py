"""
deep_notes_ai/services/llm_monitor_service.py

LLMMonitorService — central LLM observability service.

Responsibilities:
  - Accumulate LLMCallRecord instances (thread-safe).
  - Compute aggregate statistics (LLMUsageSummary).
  - Render llm_usage.json and llm_usage.md reports.
  - Delegate all file I/O to PersistenceService.

Nodes must never interact with this service directly.
Only LLMService communicates with LLMMonitorService.
"""
from __future__ import annotations

import dataclasses
import logging
import threading
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from deep_notes_ai.domain.models import LLMCallRecord, LLMUsageSummary

if TYPE_CHECKING:
    from deep_notes_ai.services.persistence_service import PersistenceService
    from deep_notes_ai.services.pricing_service import PricingService

logger = logging.getLogger(__name__)


class LLMMonitorService:
    """
    Centralized LLM observability service.

    Thread-safe accumulation of call records with report generation.

    Usage:
        monitor = LLMMonitorService(pricing_service, persistence_service)
        # LLMService records calls via monitor.record(record)
        monitor.save_reports(run_dir)
    """

    def __init__(
        self,
        pricing_service: "PricingService",
        persistence_service: "PersistenceService",
    ) -> None:
        self._pricing_service = pricing_service
        self._persistence_service = persistence_service
        self._calls: list[LLMCallRecord] = []
        self._lock = threading.Lock()

    # -------------------------------------------------------------------------
    # Public API — called by LLMService only
    # -------------------------------------------------------------------------

    def record(self, record: LLMCallRecord) -> None:
        """
        Append a completed LLM call record.

        Thread-safe. Called by LLMService after every invocation.
        """
        with self._lock:
            self._calls.append(record)

        status = "success" if record.success else "FAILED"
        logger.info(
            "LLM call recorded: node=%r operation=%r provider=%r model=%r "
            "input_tokens=%s output_tokens=%s cost=%s duration_ms=%.1f "
            "status=%s",
            record.node_name,
            record.operation_name,
            record.provider,
            record.model,
            record.input_tokens,
            record.output_tokens,
            record.estimated_cost,
            record.duration_ms,
            status,
        )

    def get_all_calls(self) -> list[LLMCallRecord]:
        """Return a snapshot copy of all recorded calls."""
        with self._lock:
            return list(self._calls)

    def build_summary(self) -> LLMUsageSummary:
        """Compute aggregate statistics over all recorded calls."""
        calls = self.get_all_calls()

        successful = [c for c in calls if c.success]
        failed = [c for c in calls if not c.success]

        total_input = sum(c.input_tokens or 0 for c in calls)
        total_output = sum(c.output_tokens or 0 for c in calls)
        total_tokens = sum(c.total_tokens or 0 for c in calls)
        total_duration = sum(c.duration_ms for c in calls)

        costs = [c.estimated_cost for c in calls if c.estimated_cost is not None]
        total_cost: float | None = round(sum(costs), 8) if costs else None

        return LLMUsageSummary(
            total_calls=len(calls),
            successful_calls=len(successful),
            failed_calls=len(failed),
            total_input_tokens=total_input,
            total_output_tokens=total_output,
            total_tokens=total_tokens,
            estimated_total_cost=total_cost,
            total_duration_ms=round(total_duration, 2),
        )

    def save_reports(self, run_dir: Path) -> None:
        """
        Persist llm_usage.json and llm_usage.md inside run_dir.

        Delegates all file I/O to PersistenceService.

        Args:
            run_dir: The pipeline run directory (e.g. output/<content_id>/<run_id>).
        """
        calls = self.get_all_calls()
        summary = self.build_summary()

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        json_path = run_dir / "artifacts" / f"llm_usage_{timestamp}.json"
        md_path = run_dir / "artifacts" / f"llm_usage_{timestamp}.md"

        self._persistence_service.save_json(json_path, self._build_json_report(calls, summary))
        logger.info("LLM usage JSON report saved to %s", json_path)

        self._persistence_service.save_text(md_path, self._build_markdown_report(calls, summary))
        logger.info("LLM usage Markdown report saved to %s", md_path)

    # -------------------------------------------------------------------------
    # Report builders (private)
    # -------------------------------------------------------------------------

    def _build_json_report(
        self, calls: list[LLMCallRecord], summary: LLMUsageSummary
    ) -> dict:
        """Build the dict for llm_usage.json."""
        serialised_calls = []
        for c in calls:
            d = dataclasses.asdict(c)
            # Convert datetime objects to ISO strings for JSON serialisation.
            d["started_at"] = c.started_at.isoformat()
            d["finished_at"] = c.finished_at.isoformat()
            serialised_calls.append(d)

        return {
            "calls": serialised_calls,
            "summary": dataclasses.asdict(summary),
            "per_node": self._aggregate_by(calls, "node_name"),
            "per_operation": self._aggregate_by(calls, "operation_name"),
            "per_provider": self._aggregate_by(calls, "provider"),
            "per_model": self._aggregate_by(calls, "model"),
        }

    def _build_markdown_report(
        self, calls: list[LLMCallRecord], summary: LLMUsageSummary
    ) -> str:
        """Build the content of llm_usage.md."""
        lines: list[str] = []

        lines.append("# LLM Usage Report\n")
        lines.append(
            f"_Generated at {datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ')}_\n"
        )

        # -- Pipeline summary --------------------------------------------------
        lines.append("## Pipeline Summary\n")
        lines.append("| Metric | Value |")
        lines.append("|---|---|")
        lines.append(f"| Total Calls | {summary.total_calls} |")
        lines.append(f"| Successful Calls | {summary.successful_calls} |")
        lines.append(f"| Failed Calls | {summary.failed_calls} |")
        lines.append(f"| Total Input Tokens | {summary.total_input_tokens:,} |")
        lines.append(f"| Total Output Tokens | {summary.total_output_tokens:,} |")
        lines.append(f"| Total Tokens | {summary.total_tokens:,} |")
        cost_str = (
            f"${summary.estimated_total_cost:.6f}"
            if summary.estimated_total_cost is not None
            else "N/A"
        )
        lines.append(f"| Estimated Total Cost | {cost_str} |")
        lines.append(f"| Total Duration | {summary.total_duration_ms:,.1f} ms |")
        lines.append("")

        # -- Per-node breakdown ------------------------------------------------
        lines.append("## Per-Node Breakdown\n")
        lines.extend(self._render_aggregation_table(calls, "node_name", "Node"))
        lines.append("")

        # -- Per-operation breakdown -------------------------------------------
        lines.append("## Per-Operation Breakdown\n")
        lines.extend(self._render_aggregation_table(calls, "operation_name", "Operation"))
        lines.append("")

        # -- Per-provider breakdown --------------------------------------------
        lines.append("## Per-Provider Breakdown\n")
        lines.extend(self._render_aggregation_table(calls, "provider", "Provider"))
        lines.append("")

        # -- Per-model breakdown -----------------------------------------------
        lines.append("## Per-Model Breakdown\n")
        lines.extend(self._render_aggregation_table(calls, "model", "Model"))
        lines.append("")

        # -- Individual call table ---------------------------------------------
        lines.append("## Individual Calls\n")
        if not calls:
            lines.append("_No LLM calls recorded._\n")
        else:
            lines.append(
                "| # | Node | Operation | Provider | Model | Input | Output | "
                "Tokens | Cost | Duration (ms) | Status |"
            )
            lines.append("|---|---|---|---|---|---|---|---|---|---|---|")
            for i, c in enumerate(calls, start=1):
                cost_val = f"${c.estimated_cost:.6f}" if c.estimated_cost is not None else "N/A"
                status = "✅" if c.success else "❌"
                exc = f" `{c.exception_type}`" if c.exception_type else ""
                lines.append(
                    f"| {i} | {c.node_name} | {c.operation_name} | {c.provider} | "
                    f"`{c.model}` | {c.input_tokens or 'N/A'} | {c.output_tokens or 'N/A'} | "
                    f"{c.total_tokens or 'N/A'} | {cost_val} | {c.duration_ms:.1f} | "
                    f"{status}{exc} |"
                )
            lines.append("")

        return "\n".join(lines)

    # -------------------------------------------------------------------------
    # Aggregation helpers (private)
    # -------------------------------------------------------------------------

    def _aggregate_by(self, calls: list[LLMCallRecord], field: str) -> dict:
        """Group calls by a field name and return summary dicts keyed by value."""
        groups: dict[str, list[LLMCallRecord]] = {}
        for c in calls:
            key = str(getattr(c, field))
            groups.setdefault(key, []).append(c)

        result = {}
        for key, group_calls in groups.items():
            input_t = sum(c.input_tokens or 0 for c in group_calls)
            output_t = sum(c.output_tokens or 0 for c in group_calls)
            total_t = sum(c.total_tokens or 0 for c in group_calls)
            costs = [c.estimated_cost for c in group_calls if c.estimated_cost is not None]
            total_cost: float | None = round(sum(costs), 8) if costs else None
            result[key] = {
                "calls": len(group_calls),
                "successful": sum(1 for c in group_calls if c.success),
                "failed": sum(1 for c in group_calls if not c.success),
                "input_tokens": input_t,
                "output_tokens": output_t,
                "total_tokens": total_t,
                "estimated_cost": total_cost,
                "duration_ms": round(sum(c.duration_ms for c in group_calls), 2),
            }
        return result

    def _render_aggregation_table(
        self, calls: list[LLMCallRecord], field: str, label: str
    ) -> list[str]:
        """Render a Markdown aggregation table grouped by field."""
        agg = self._aggregate_by(calls, field)
        if not agg:
            return [f"_No {label.lower()} data._\n"]

        rows = [
            f"| {label} | Calls | Success | Failed | Input Tokens | "
            f"Output Tokens | Total Tokens | Cost | Duration (ms) |",
            "|---|---|---|---|---|---|---|---|---|",
        ]
        for key, stats in sorted(agg.items()):
            cost_val = (
                f"${stats['estimated_cost']:.6f}"
                if stats["estimated_cost"] is not None
                else "N/A"
            )
            rows.append(
                f"| {key} | {stats['calls']} | {stats['successful']} | "
                f"{stats['failed']} | {stats['input_tokens']:,} | "
                f"{stats['output_tokens']:,} | {stats['total_tokens']:,} | "
                f"{cost_val} | {stats['duration_ms']:,.1f} |"
            )
        return rows
