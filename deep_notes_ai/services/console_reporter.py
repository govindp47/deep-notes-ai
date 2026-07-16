"""
deep_notes_ai/services/console_reporter.py

ConsoleReporter — production-quality console progress renderer.

Renders ProgressEvent instances as clean, human-readable lines on sys.stdout.

Output style:

  ────────────────────────────────────────
  ⟳ Extracting Video Metadata
  ✓ Video Metadata Extracted
  ⟳ Downloading Transcript
  ✓ Transcript Downloaded
  ⟳ Cleaning Transcript
      Chunk 1 / 6
      Chunk 2 / 6
      Chunk 3 / 6
  ✓ Transcript Cleaned
  ...
  ────────────────────────────────────────

Design:
  - No third-party libraries (no Rich, no TQDM).
  - Uses sys.stdout directly (not logging) — progress and logs are separate.
  - RUNNING events with current/total overwrite the previous progress line
    using carriage return, giving a compact in-place counter.
  - Thread-safe output via a threading.Lock.
"""
from __future__ import annotations

import sys
import threading

from deep_notes_ai.domain.models import ProgressEvent, ProgressStatus
from deep_notes_ai.services.progress_reporter import ProgressReporter

# Width of the decorative separator line.
_SEPARATOR_WIDTH = 48
_SEPARATOR = "─" * _SEPARATOR_WIDTH

# Status prefix symbols.
_SYMBOL = {
    ProgressStatus.STARTED:   "⟳",
    ProgressStatus.RUNNING:   " ",
    ProgressStatus.COMPLETED: "✓",
    ProgressStatus.FAILED:    "✗",
    ProgressStatus.INFO:      "·",
}


class ConsoleReporter(ProgressReporter):
    """
    Renders progress events as clean, readable console output.

    Instantiate with no arguments; pass to ProgressService:

        reporter = ConsoleReporter()
        service  = ProgressService(reporters=[reporter])
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        # Tracks whether the last line written was an in-place progress line
        # (i.e. used \\r) so we know whether to emit a leading newline first.
        self._last_was_progress: bool = False
        self._header_printed: bool = False

    # -------------------------------------------------------------------------
    # ProgressReporter interface
    # -------------------------------------------------------------------------

    def report(self, event: ProgressEvent) -> None:
        """
        Render a single ProgressEvent to sys.stdout.

        Thread-safe. Never raises.
        """
        with self._lock:
            try:
                self._render(event)
            except Exception:  # noqa: BLE001
                # Must never raise — silently skip broken output.
                pass

    # -------------------------------------------------------------------------
    # Rendering (private)
    # -------------------------------------------------------------------------

    def _render(self, event: ProgressEvent) -> None:
        """Dispatch to the appropriate renderer based on event status."""
        if not self._header_printed:
            self._print_separator()
            self._header_printed = True

        if event.status == ProgressStatus.STARTED:
            self._render_started(event)
        elif event.status == ProgressStatus.RUNNING:
            self._render_running(event)
        elif event.status == ProgressStatus.COMPLETED:
            self._render_completed(event)
        elif event.status == ProgressStatus.FAILED:
            self._render_failed(event)
        elif event.status == ProgressStatus.INFO:
            self._render_info(event)

    def _render_started(self, event: ProgressEvent) -> None:
        """Print a starting indicator: ⟳ Stage Name"""
        self._flush_progress_line()
        symbol = _SYMBOL[ProgressStatus.STARTED]
        self._writeln(f"{symbol} {event.stage}")

    def _render_running(self, event: ProgressEvent) -> None:
        """
        Print an in-place progress counter using carriage return.

        If current and total are present:   [  progress line using \\r  ]
        Otherwise: a plain indented message line.
        """
        if event.current is not None and event.total is not None:
            line = f"    {event.message}  ({event.current} / {event.total})"
            # Pad to a fixed width to overwrite any longer previous line.
            padded = line.ljust(_SEPARATOR_WIDTH)
            sys.stdout.write(f"\r{padded}")
            sys.stdout.flush()
            self._last_was_progress = True
        else:
            self._flush_progress_line()
            self._writeln(f"    {event.message}")

    def _render_completed(self, event: ProgressEvent) -> None:
        """Print a completion tick: ✓ Stage Name"""
        self._flush_progress_line()
        symbol = _SYMBOL[ProgressStatus.COMPLETED]
        self._writeln(f"{symbol} {event.stage}")

    def _render_failed(self, event: ProgressEvent) -> None:
        """Print a failure marker and the error message."""
        self._flush_progress_line()
        symbol = _SYMBOL[ProgressStatus.FAILED]
        self._writeln(f"{symbol} {event.stage}")
        if event.message:
            self._writeln(f"    {event.message}")

    def _render_info(self, event: ProgressEvent) -> None:
        """Print a plain informational line."""
        self._flush_progress_line()
        symbol = _SYMBOL[ProgressStatus.INFO]
        self._writeln(f"{symbol} {event.message}")

    # -------------------------------------------------------------------------
    # Output helpers (private)
    # -------------------------------------------------------------------------

    def _flush_progress_line(self) -> None:
        """
        If the last write was an in-place \\r progress line, emit a newline
        to advance the cursor before writing the next full line.
        """
        if self._last_was_progress:
            sys.stdout.write("\n")
            sys.stdout.flush()
            self._last_was_progress = False

    def _writeln(self, text: str) -> None:
        """Write text followed by a newline and flush immediately."""
        sys.stdout.write(text + "\n")
        sys.stdout.flush()

    def _print_separator(self) -> None:
        """Print the decorative horizontal rule."""
        sys.stdout.write(_SEPARATOR + "\n")
        sys.stdout.flush()
