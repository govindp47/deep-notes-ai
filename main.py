"""
main.py

CLI entry point for the deep-notes-ai pipeline.

Usage:
    python main.py --youtube-url <URL> [--output-dir <DIR>]
"""
from __future__ import annotations

import argparse
from datetime import datetime
import logging
from pathlib import Path
import shutil
import sys

from deep_notes_ai.domain.models import ContentMetadata, ProcessingContext
from deep_notes_ai.services.llm_monitor_service import LLMMonitorService


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse and return CLI arguments."""
    parser = argparse.ArgumentParser(
        prog="deep-notes-ai",
        description=(
            "Transform a YouTube lecture transcript into structured "
            "markdown notes using an LLM pipeline."
        ),
    )
    parser.add_argument(
        "--source",
        required=True,
        metavar="SOURCE",
        help="Content source (e.g., YouTube URL, file path).",
    )
    parser.add_argument(
        "--source-type",
        required=True,
        metavar="TYPE",
        help="Type of the source (e.g., youtube, article, book).",
    )
    return parser.parse_args(argv)


def _collect_breakpoint_selection(interrupt_value: dict) -> dict:
    """
    Collect transcript breakpoint selection from the user.

    The interrupt payload is produced by ChapterSelectionService and contains:

        {
            "type": "chapter_selection",
            "summary": {
                "total_chapters": ...,
                "total_tokens": ...,
                "max_tokens_per_part": ...
            },
            "chapters": [
                "[00] 00:00:00 |  2,381 tokens | Introduction",
                ...
            ],
            "instructions": [
                "...",
                ...
            ]
        }

    Returns:
        {
            "selected_indices": list[int]
        }
    """
    summary: dict = interrupt_value.get("summary", {})
    chapters: list[str] = interrupt_value.get("chapters", [])
    instructions: list[str] = interrupt_value.get("instructions", [])

    total_tokens: int = summary.get("total_tokens", 0)
    max_tokens: int = summary.get("max_tokens_per_part", 50_000)
    total_chapters: int = summary.get("total_chapters", len(chapters))

    print("\n" + "─" * 72)
    print("  ⚡  Multi-Part Transcript Processing")
    print("─" * 72)
    print(f"  Transcript size : {total_tokens:,} tokens")
    print(f"  Maximum per part: {max_tokens:,} tokens")
    print(f"  Chapters found  : {total_chapters}")
    print("─" * 72)

    print("\n  Available chapters:\n")

    for chapter in chapters:
        print(f"    {chapter}")

    print("\n" + "─" * 72)

    print("  Instructions:\n")
    for instruction in instructions:
        print(f"    • {instruction}")

    print("─" * 72)

    valid_indices = set(range(total_chapters))

    while True:
        raw = input(
            "\n  Enter chapter indices that should START a new transcript part\n"
            "  (comma-separated, e.g. 3,7,12)\n\n"
            "  Selection: "
        ).strip()

        if not raw:
            print("\n  ⚠  Please enter at least one chapter index.\n")
            continue

        try:
            selected = sorted(
                {
                    int(value.strip())
                    for value in raw.split(",")
                    if value.strip()
                }
            )
        except ValueError:
            print(
                "\n  ⚠  Invalid input. Please enter only integer values "
                "separated by commas.\n"
            )
            continue

        invalid = [
            index
            for index in selected
            if index not in valid_indices
        ]

        if invalid:
            print(
                f"\n  ⚠  Invalid chapter indices: {invalid}\n"
                f"  Valid range: 0-{total_chapters - 1}\n"
            )
            continue

        print("\n  ✓ Selected breakpoint chapters:\n")

        for index in selected:
            print(f"    {chapters[index]}")

        print("\n" + "─" * 72 + "\n")

        return {
            "selected_indices": selected,
        }
    

def _persist_pipeline_reports(
    logger_name: str,
    log_file_path: Path,
    reports_dir: Path,
    monitor_service: LLMMonitorService | None = None,
) -> None:
    """
    Persist all pipeline reports generated during execution.

    Responsibilities:
        - Save LLM monitoring reports.
        - Move the pipeline log into the run's logs directory.

    This function should be called once after graph execution has completed
    (whether successfully or unsuccessfully).

    Args:
        logger_name:
            Name of the configured pipeline logger.

        log_file_path:
            Temporary pipeline log file generated during execution.
        
        reports_dir:

        monitor_service:
            Optional LLMMonitorService instance.
    """

    if monitor_service is not None:
        print("\n[INFO] Saving LLM monitoring report.")

        try:
            monitor_service.save_reports(reports_dir)
            print("[INFO] LLM monitoring report saved successfully.")

        except Exception as exc:
            print(
                f"[ERROR] LLM monitoring report failed: {exc}",
                file=sys.stderr,
            )

    print("\n[INFO] Moving pipeline log.")

    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        destination_log = (
            reports_dir
            / f"pipeline_{timestamp}.log"
        )

        logger = logging.getLogger(logger_name)

        for handler in logger.handlers:
            handler.flush()
            handler.close()

        if log_file_path.exists():
            destination_log.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            shutil.move(
                log_file_path,
                destination_log,
            )

            print(
                f"[INFO] Pipeline log moved to: {destination_log}"
            )

        else:
            print(
                f"[ERROR] Pipeline log not found: {log_file_path}",
                file=sys.stderr,
            )

    except Exception as exc:
        print(
            f"[ERROR] Moving pipeline log failed: {exc}",
            file=sys.stderr,
        )


def main(argv: list[str] | None = None) -> int:
    """
    CLI entry point.

    Returns:
        0 on success, 1 on failure.
    """
    args = _parse_args(argv)

    # ── Load settings ─────────────────────────────────────────────────────────
    try:
        from deep_notes_ai.config.settings import Settings

        kwargs: dict = {}

        settings = Settings(**kwargs)
    except Exception as exc:  # noqa: BLE001
        print(f"[ERROR] Failed to load settings: {exc}", file=sys.stderr)
        return 1

    # ── Configure logging ─────────────────────────────────────────────────────
    from deep_notes_ai.config.logging_setup import configure_logging

    logger_name = "deep_notes_ai"
    log_file_path = configure_logging(
        logger_name=logger_name,
        log_level=settings.log_level,
        structured=settings.enable_structured_logging,
        log_dir=settings.logs_dir,
    )

    # ── Build graph ───────────────────────────────────────────────────────────
    try:
        from deep_notes_ai.langgraph_pipeline.graph import build_graph

        graph, monitor_service = build_graph(settings)
    except Exception as exc:  # noqa: BLE001
        print(f"[ERROR] Failed to build pipeline graph: {exc}", file=sys.stderr)
        return 1

    # ── Construct initial state ───────────────────────────────────────────────
    from deep_notes_ai.domain.models import SourceType
    
    initial_state = {
        "source": args.source,
        "source_type": args.source_type,
        "pipeline_complete": False,
        "error_message": None,
    }

    # ── Invoke graph (with interrupt-resume support for multi-part mode) ──────────
    print(f"[INFO] Starting pipeline for source: {args.source} (type: {args.source_type})")
    try:
        from langgraph.types import Command

        config: dict = {"configurable": {"thread_id": args.source}}

        # graph.invoke() returns the current state when an interrupt fires.
        # We loop until no pending interrupt remains.
        result = graph.invoke(initial_state, config=config)

        while isinstance(result, dict) and result.get("__interrupt__"):
            interrupt_events = result["__interrupt__"]
            # Each interrupt event has a .value attribute with the payload.
            interrupt_value = interrupt_events[0].value
            user_input = _collect_breakpoint_selection(interrupt_value)
            result = graph.invoke(Command(resume=user_input), config=config)

        final_state = result
        print("[INFO] Pipeline completed successfully.")
    except Exception as exc:  # noqa: BLE001
        print(f"[ERROR] Pipeline failed: {exc}", file=sys.stderr)
        _persist_pipeline_reports(
            logger_name=logger_name,
            log_file_path=log_file_path,
            reports_dir=Path("pipeline_crash_logs"),
            monitor_service=monitor_service
        )
        return -1
    
    # ── Report results ────────────────────────────────────────────────────────
    if not final_state.get("pipeline_complete"):
        error_msg = final_state.get("error_message", "Unknown error")
        print(f"[ERROR] Pipeline did not complete successfully: {error_msg}", file=sys.stderr)

    print("\n[INFO] Pipeline Final State")
    print("─" * 72)

    metadata: ContentMetadata = final_state.get("metadata")
    processing_context: ProcessingContext = final_state.get("processing_context")

    print(f"  Source              : {final_state.get('source')}")
    print(f"  Source Type         : {final_state.get('source_type')}")
    print(f"  Content Base Dir    : {final_state.get('content_base_dir')}")

    if metadata is not None:
        print(f"  Content ID          : {metadata.id}")
        print(f"  Content Title       : {metadata.title}")
        print(f"  Author Name         : {metadata.author}")
        print(f"  Upload Date         : {metadata.upload_date}")
        print(f"  Content URL         : {metadata.url}")
    else:
        print("  Metadata            : <not available>")

    print(
        f"  Chapters            : "
        f"{len(final_state.get('chapters', []))}"
    )

    if processing_context is not None:
        print(f"  Processing Mode     : {processing_context.processing_mode}")
        print(f"  Total Parts         : {processing_context.total_parts}")
        print(f"  Current Part        : {processing_context.current_part}")
    else:
        print("  Processing Context  : <not available>")

    print(f"  Pipeline Complete   : {final_state.get('pipeline_complete')}")
    print(f"  Error Message       : {final_state.get('error_message')}")

    print("─" * 72)

    reports_dir: Path = final_state.get("content_base_dir") / "logs"
    _persist_pipeline_reports(
        logger_name=logger_name,
        log_file_path=log_file_path,
        reports_dir=reports_dir,
        monitor_service=monitor_service
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
