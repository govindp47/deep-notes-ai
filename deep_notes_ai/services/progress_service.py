"""
deep_notes_ai/services/progress_service.py

ProgressService — the single point of contact for all progress reporting.

Responsibilities:
  - Accept a list of ProgressReporter instances at construction time.
  - Expose convenience emit helpers used exclusively by nodes.
  - Forward every ProgressEvent to all registered reporters.

Design principles:
  - Nodes interact ONLY with ProgressService; they never know about reporters.
  - Supports multiple reporters simultaneously (console + WebSocket, etc.).
  - Reporter errors are caught and logged — they must never abort a pipeline.
  - No global state; fully dependency-injected.
  - Negligible overhead: no serialisation, no reflection.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from deep_notes_ai.domain.models import ProgressEvent, ProgressStatus

if TYPE_CHECKING:
    from deep_notes_ai.services.progress_reporter import ProgressReporter

logger = logging.getLogger(__name__)


class ProgressService:
    """
    Central progress reporting hub for the pipeline.

    Usage:
        reporter = ConsoleReporter()
        service = ProgressService(reporters=[reporter])
        # In a node:
        service.emit_start(node_name="clean_transcript", stage="Cleaning Transcript")
        service.emit_progress(node_name="clean_transcript", stage="Cleaning Transcript",
                              message="Chunk 3 / 6", current=3, total=6)
        service.emit_completed(node_name="clean_transcript", stage="Cleaning Transcript")
    """

    def __init__(self, reporters: list["ProgressReporter"]) -> None:
        """
        Initialise with a list of reporters.

        Args:
            reporters: Any number of ProgressReporter implementations.
                       An empty list is valid (silent mode).
        """
        self._reporters = list(reporters)

    # -------------------------------------------------------------------------
    # Public emit helpers — called exclusively by nodes
    # -------------------------------------------------------------------------

    def emit_start(self, node_name: str, stage: str, message: str = "") -> None:
        """
        Emit a STARTED event for the beginning of a node.

        Args:
            node_name: Pipeline node identifier (e.g. "clean_transcript").
            stage:     Human-readable stage label shown to the user.
            message:   Optional supplementary detail.
        """
        self._emit(
            node_name=node_name,
            stage=stage,
            status=ProgressStatus.STARTED,
            message=message or f"Starting {stage}",
        )

    def emit_running(
        self,
        node_name: str,
        stage: str,
        message: str,
        current: int | None = None,
        total: int | None = None,
    ) -> None:
        """
        Emit a RUNNING event for an incremental mid-node update.

        Args:
            node_name: Pipeline node identifier.
            stage:     Human-readable stage label.
            message:   Descriptive progress message.
            current:   Current item index (1-based), if applicable.
            total:     Total item count, if applicable.
        """
        self._emit(
            node_name=node_name,
            stage=stage,
            status=ProgressStatus.RUNNING,
            message=message,
            current=current,
            total=total,
        )

    def emit_progress(
        self,
        node_name: str,
        stage: str,
        message: str,
        current: int,
        total: int,
    ) -> None:
        """
        Emit a RUNNING event for an item in a counted sequence.

        Convenience wrapper for loops with a known total.

        Args:
            node_name: Pipeline node identifier.
            stage:     Human-readable stage label.
            message:   Description of the current item.
            current:   Current item index (1-based).
            total:     Total number of items.
        """
        self._emit(
            node_name=node_name,
            stage=stage,
            status=ProgressStatus.RUNNING,
            message=message,
            current=current,
            total=total,
        )

    def emit_completed(
        self, node_name: str, stage: str, message: str = ""
    ) -> None:
        """
        Emit a COMPLETED event when a node finishes successfully.

        Args:
            node_name: Pipeline node identifier.
            stage:     Human-readable stage label.
            message:   Optional supplementary detail.
        """
        self._emit(
            node_name=node_name,
            stage=stage,
            status=ProgressStatus.COMPLETED,
            message=message or f"{stage} complete",
        )

    def emit_failed(
        self, node_name: str, stage: str, message: str = ""
    ) -> None:
        """
        Emit a FAILED event when a node terminates with an error.

        This does NOT raise or swallow exceptions — call this immediately
        before re-raising in an except block.

        Args:
            node_name: Pipeline node identifier.
            stage:     Human-readable stage label.
            message:   Human-readable description of the failure.
        """
        self._emit(
            node_name=node_name,
            stage=stage,
            status=ProgressStatus.FAILED,
            message=message or f"{stage} failed",
        )

    def emit_info(self, node_name: str, stage: str, message: str) -> None:
        """
        Emit an INFO event for a notable informational milestone.

        Args:
            node_name: Pipeline node identifier.
            stage:     Human-readable stage label.
            message:   Informational message.
        """
        self._emit(
            node_name=node_name,
            stage=stage,
            status=ProgressStatus.INFO,
            message=message,
        )

    # -------------------------------------------------------------------------
    # Internal dispatch (private)
    # -------------------------------------------------------------------------

    def _emit(
        self,
        node_name: str,
        stage: str,
        status: ProgressStatus,
        message: str,
        current: int | None = None,
        total: int | None = None,
    ) -> None:
        """
        Build a ProgressEvent and forward it to all reporters.

        Reporter errors are caught individually so one broken reporter
        cannot silence the others or abort the pipeline.
        """
        event = ProgressEvent(
            timestamp=datetime.now(timezone.utc),
            node_name=node_name,
            stage=stage,
            status=status,
            message=message,
            current=current,
            total=total,
        )
        for reporter in self._reporters:
            try:
                reporter.report(event)
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "Progress reporter %r raised an error: %s",
                    type(reporter).__name__,
                    exc,
                )
