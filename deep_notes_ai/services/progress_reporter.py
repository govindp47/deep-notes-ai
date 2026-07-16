"""
deep_notes_ai/services/progress_reporter.py

ProgressReporter — abstract base class for all user-facing progress reporters.

Responsibilities:
  - Define the single contract: receive a ProgressEvent and render it.

Concrete implementations (ConsoleReporter, WebSocketReporter, etc.) inherit
from this class and implement report().

Nodes never interact with reporters directly — they use ProgressService.
"""
from __future__ import annotations

import abc

from deep_notes_ai.domain.models import ProgressEvent


class ProgressReporter(abc.ABC):
    """
    Abstract base class for progress reporters.

    Implement this interface to add a new output target (console, WebSocket,
    REST endpoint, GUI, file, etc.) without touching any pipeline node.

    Usage:
        class MyReporter(ProgressReporter):
            def report(self, event: ProgressEvent) -> None:
                ...  # render the event

        service = ProgressService(reporters=[MyReporter()])
    """

    @abc.abstractmethod
    def report(self, event: ProgressEvent) -> None:
        """
        Receive and render a single progress event.

        Called by ProgressService for every emitted event.
        Must not raise; swallow or log errors internally.

        Args:
            event: The immutable ProgressEvent to render.
        """
