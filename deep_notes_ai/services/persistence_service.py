"""
deep_notes_ai/services/persistence_service.py

PersistenceService — all file I/O for the pipeline.

Single point of access for reading and writing artefacts.
"""
from __future__ import annotations

import shutil
from dataclasses import asdict, is_dataclass
import json
import logging
from pathlib import Path
from typing import Any

from deep_notes_ai.domain.models import (
    ContentNode,
    ContentStoreItem,
    Node,
    PersistenceError,
    TitleNode,
)

logger = logging.getLogger(__name__)


def json_serializer(obj: Any) -> Any:
    """
    Custom JSON default handler for dataclasses.

    Usage:
        json.dumps(obj, default=json_serializer)
    """
    if is_dataclass(obj) and not isinstance(obj, type):
        return asdict(obj)
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


def _load_node(data: dict[str, Any]) -> Node:
    """
    Recursively reconstruct a TitleNode or ContentNode from a raw dict.
    """
    node_type = data.get("type")
    if node_type == "content":
        return ContentNode(
            type="content",
            id=data["id"],
        )
    elif node_type == "topic":
        subtopics = [_load_node(child) for child in data.get("subtopics", [])]
        return TitleNode(
            type="topic",
            name=data["name"],
            subtopics=subtopics,
        )
    else:
        raise PersistenceError(f"Unknown node type in JSON: {node_type!r}")


class PersistenceService:
    """
    All file I/O operations for the pipeline.

    - All paths are absolute.
    - Creates parent directories automatically.
    - All files read/written in UTF-8.
    - Raises PersistenceError on any I/O failure.
    """

    def exists(self, path: Path) -> bool:
        """Check if an artifact exists on the filesystem."""
        return path.exists()

    # -------------------------------------------------------------------------
    # Raw text
    # -------------------------------------------------------------------------

    def save_text(self, path: Path, text: str) -> None:
        """Write a plain text string to a file, creating parent dirs."""
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
            logger.debug("Saved text to %s", path)
        except OSError as exc:
            raise PersistenceError(f"Failed to write text to {path}: {exc}") from exc

    def load_text(self, path: Path) -> str:
        """Read a plain text file and return its contents."""
        try:
            content = path.read_text(encoding="utf-8")
            logger.debug("Loaded text from %s", path)
            return content
        except FileNotFoundError as exc:
            raise PersistenceError(f"File not found: {path}") from exc
        except OSError as exc:
            raise PersistenceError(f"Failed to read text from {path}: {exc}") from exc

    # -------------------------------------------------------------------------
    # Generic JSON
    # -------------------------------------------------------------------------

    def save_json(self, path: Path, obj: Any) -> None:
        """Serialise obj to JSON and write to path."""
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                json.dumps(obj, default=json_serializer, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            logger.debug("Saved JSON to %s", path)
        except OSError as exc:
            raise PersistenceError(f"Failed to write JSON to {path}: {exc}") from exc

    def load_json(self, path: Path) -> Any:
        """Load and parse a JSON file, returning the raw Python object."""
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            logger.debug("Loaded JSON from %s", path)
            return data
        except FileNotFoundError as exc:
            raise PersistenceError(f"File not found: {path}") from exc
        except (OSError, json.JSONDecodeError) as exc:
            raise PersistenceError(f"Failed to read JSON from {path}: {exc}") from exc

    # -------------------------------------------------------------------------
    # Typed save/load
    # -------------------------------------------------------------------------

    def save_hierarchy(self, path: Path, hierarchy: Any) -> None:
        """Serialise a TranscriptHierarchy to JSON."""
        # Using Any to avoid circular import issues if TranscriptHierarchy isn't imported
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                hierarchy.model_dump_json(indent=2),
                encoding="utf-8",
            )
            logger.debug("Saved transcript hierarchy to %s", path)
        except OSError as exc:
            raise PersistenceError(
                f"Failed to write transcript hierarchy to {path}: {exc}"
            ) from exc

    def load_hierarchy(self, path: Path) -> Any:
        """
        Deserialise a transcript hierarchy JSON file into a TranscriptHierarchy.
        """
        raw = self.load_json(path)
        try:
            from deep_notes_ai.domain.models import TranscriptHierarchy
            return TranscriptHierarchy.model_validate(raw)
        except Exception as exc:
            raise PersistenceError(
                f"Malformed transcript hierarchy JSON at {path}: {exc}"
            ) from exc

    def save_nodes_hierarchy(self, path: Path, nodes: list[Node]) -> None:
        """Serialise a list of Node objects to JSON."""
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            data = [json_serializer(node) for node in nodes]
            path.write_text(
                json.dumps(data, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            logger.debug("Saved nodes hierarchy to %s", path)
        except OSError as exc:
            raise PersistenceError(
                f"Failed to write nodes hierarchy to {path}: {exc}"
            ) from exc

    def save_nodes_content(
        self,
        path: Path,
        content: dict[str, ContentStoreItem],
    ) -> None:
        """Serialise the UUID → ContentStoreItem mapping to JSON."""
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            data = {k: json_serializer(v) for k, v in content.items()}
            path.write_text(
                json.dumps(data, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            logger.debug("Saved nodes content to %s", path)
        except OSError as exc:
            raise PersistenceError(
                f"Failed to write nodes content to {path}: {exc}"
            ) from exc

    def load_nodes_hierarchy(self, path: Path) -> list[Node]:
        """
        Deserialise a nodes hierarchy JSON file into a list of Node objects.

        Uses _load_node() to recursively reconstruct TitleNode / ContentNode.
        """
        raw = self.load_json(path)
        try:
            return [_load_node(item) for item in raw]
        except (KeyError, TypeError) as exc:
            raise PersistenceError(
                f"Malformed nodes hierarchy JSON at {path}: {exc}"
            ) from exc

    def load_nodes_content(
        self,
        path: Path,
    ) -> dict[str, ContentStoreItem]:
        """Deserialise the UUID → ContentStoreItem mapping from JSON."""
        raw = self.load_json(path)
        try:
            return {
                uuid: ContentStoreItem(
                    content=item["content"],
                    summary=item["summary"],
                )
                for uuid, item in raw.items()
            }
        except (KeyError, TypeError) as exc:
            raise PersistenceError(
                f"Malformed nodes content JSON at {path}: {exc}"
            ) from exc

    def save_markdown(self, path: Path, markdown: str) -> None:
        """Write a markdown string to a file."""
        self.save_text(path, markdown)

    # -------------------------------------------------------------------------
    # Directory operations
    # -------------------------------------------------------------------------

    def clear_directory(self, path: Path) -> None:
        """
        Remove all files and subdirectories inside a directory while preserving
        the directory itself.

        Creates the directory if it does not already exist.

        Args:
            path: Directory to clear.

        Raises:
            PersistenceError: If the directory cannot be cleared.
        """
        try:
            path.mkdir(parents=True, exist_ok=True)

            for child in path.iterdir():
                if child.is_dir():
                    shutil.rmtree(child)
                else:
                    child.unlink()

            logger.info("Cleared directory %s", path)

        except OSError as exc:
            raise PersistenceError(
                f"Failed to clear directory {path}: {exc}"
            ) from exc
