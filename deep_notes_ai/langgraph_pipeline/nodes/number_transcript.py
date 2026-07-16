"""
deep_notes_ai/langgraph_pipeline/nodes/number_transcript.py

Node 3: number_transcript

Responsibility: Apply clean_bullet_output() to the cleaned transcript and
persist the numbered file.

Reads from state: cleaned_content, current_run_dir, content_id
Calls:
  - algorithms.clean_bullet_output(cleaned_content)
  - algorithms.load_numbered_points_from_text(numbered_text)
  - PersistenceService.save_text(path, numbered_text)
Returns:
  {
    "content_points": str,
    "content_points_path": Path,
    "content_points_list": list[str],
  }
Error handling: PersistenceError on write failure.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from deep_notes_ai.domain import algorithms
from deep_notes_ai.langgraph_pipeline.state import PipelineState
from deep_notes_ai.services.persistence_service import PersistenceService

if TYPE_CHECKING:
    pass

if TYPE_CHECKING:
    from deep_notes_ai.services.progress_service import ProgressService

logger = logging.getLogger(__name__)

_NODE = "number_transcript"
_STAGE = "Numbering Transcript"


def make_number_transcript_node(
    persistence_service: PersistenceService,
    progress_service: "ProgressService | None" = None,
):
    """
    Factory that returns a number_transcript node bound to the given service.

    Args:
        persistence_service: PersistenceService for saving the numbered file.
        progress_service:    Optional ProgressService for user-facing progress.

    Returns:
        A callable compatible with LangGraph node interface.
    """

    def number_transcript(state: PipelineState) -> dict:
        """
        Convert the cleaned bullet transcript to a numbered list and persist it.

        Reads:
            state["cleaned_content"]: str
            state["current_run_dir"]: Path
            state["content_id"]: str

        Returns:
            {
                "content_points": str,
                "content_points_path": Path,
                "content_points_list": list[str],
            }

        Raises:
            PersistenceError: if the file cannot be written.
        """
        cleaned_content: str = state["cleaned_content"]
        current_run_dir: Path = state["current_run_dir"]

        logger.info("cleaned content numbering")

        content_points_path = current_run_dir / "artifacts" / "content_points.txt"

        if persistence_service.exists(content_points_path):
            content_points_txt = persistence_service.load_text(content_points_path)
            content_points = algorithms.load_numbered_points_from_text(content_points_txt)
            logger.info("Found existing numbered content points. Restoring state from disk.")
            if progress_service is not None:
                progress_service.emit_info(
                    node_name=_NODE,
                    stage=_STAGE,
                    message="Numbered points restored from cache",
                )
            return {"content_points": content_points}

        if progress_service is not None:
            progress_service.emit_start(node_name=_NODE, stage=_STAGE)

        content_points = algorithms.clean_numbered_points(cleaned_content)
        content_points_txt = "\n".join(content_points)

        persistence_service.save_text(content_points_path, content_points_txt)

        logger.info(
            "Numbered content points saved to %s (%d points)",
            content_points_path,
            len(content_points)
        )

        if progress_service is not None:
            progress_service.emit_completed(node_name=_NODE, stage=_STAGE)

        return {"content_points": content_points}

    return number_transcript
