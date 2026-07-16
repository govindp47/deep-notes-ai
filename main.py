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
import shutil
import sys


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

    # ── Invoke graph ──────────────────────────────────────────────────────────
    print(f"[INFO] Starting pipeline for source: {args.source} (type: {args.source_type})")
    try:
        final_state = graph.invoke(
            initial_state,
            config={"configurable": {"thread_id": args.source}},
        )
        print("[INFO] Pipeline completed successfully.")
    except Exception as exc:  # noqa: BLE001
        print(f"[ERROR] Pipeline failed: {exc}", file=sys.stderr)
    
    # ── Report results ────────────────────────────────────────────────────────
    if not final_state.get("pipeline_complete"):
        error_msg = final_state.get("error_message", "Unknown error")
        print(f"[ERROR] Pipeline did not complete successfully: {error_msg}", file=sys.stderr)

    print("\n[INFO] Pipeline final state:")
    print(f"      Source            : {final_state.get('source')}")
    print(f"      Source Type       : {final_state.get('source_type')}")
    print(f"      Run Directory     : {final_state.get('current_run_dir')}")
    print(f"      Content Id        : {final_state.get('content_id')}")
    print(f"      Content Title     : {final_state.get('content_title')}")
    print(f"      Author Name       : {final_state.get('author_name')}")
    print(f"      Upload Date       : {final_state.get('upload_date')}")
    print(f"      Content URL       : {final_state.get('content_url')}")
    print(f"      Nodes Count       : {final_state.get('content_node_count')}")
    print(f"      Pipeline Complete : {final_state.get('pipeline_complete')}")
    print(f"      Error Message     : {final_state.get('error_message')}")

    # ── Persist LLM monitoring & log reports ────────────────────────────────────────
    run_dir = final_state.get("current_run_dir")
    if run_dir is not None:
        if monitor_service is not None:
            print("\n[INFO] Saving LLM monitoring report.")
            try:
                monitor_service.save_reports(run_dir)
                print("[INFO] LLM monitoring report saved successfully.")
            except Exception as exc:
                print(f"[ERROR] LLM monitoring report failed: {exc}", file=sys.stderr)
        
        print("\n[INFO] Moving pipeline logs.")
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            destination_log = run_dir / "artifacts" / f"pipeline_{timestamp}.log"
            logger = logging.getLogger(logger_name)

            for handler in logger.handlers:
                handler.flush()
                handler.close()

            if log_file_path.exists():
                destination_log.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(log_file_path, destination_log)
                print(f"[INFO] Pipeline log moved to: {destination_log}")
            else:
                print(f"[ERROR] Pipeline log not found: {log_file_path}", file=sys.stderr)
        except Exception as exc:
            print(f"[ERROR] Moving pipeline log failed: {exc}", file=sys.stderr)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
