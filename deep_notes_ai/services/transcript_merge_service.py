"""
deep_notes_ai/services/transcript_merge_service.py

TranscriptMergeService — merge transcript part artefacts into a single logical
representation for markdown rendering.

Responsibilities:
    - Load nodes_hierarchy.json for every transcript part.
    - Load nodes_content.json for every transcript part.
    - Merge hierarchies while preserving transcript order.
    - Merge content stores.
    - Validate duplicate UUIDs.
    - Return the merged representation.

No rendering is performed here.

No filesystem layout decisions are made here other than loading the expected
artefacts for each ContentPart.
"""
from __future__ import annotations

import logging
from pathlib import Path

from deep_notes_ai.domain.models import (
    ContentStoreItem,
    DuplicateIdsError,
    MergedTranscript,
    Node,
    PersistenceError,
    ProcessingContext,
    TranscriptProcessingMode,
)
from deep_notes_ai.services.persistence_service import PersistenceService

logger = logging.getLogger(__name__)


class TranscriptMergeService:
    """
    Merge transcript-part artefacts into one logical transcript.

    Artefacts expected for every transcript part:

        nodes_hierarchy.json
        nodes_content.json

    The merged output is suitable for MarkdownService.
    """

    def __init__(
        self,
        persistence_service: PersistenceService,
    ) -> None:
        self._persistence_service = persistence_service

    def merge(
        self,
        processing_context: ProcessingContext,
        content_base_dir: Path,
    ) -> MergedTranscript:
        """
        Merge all transcript-part artefacts.

        Args:
            processing_context:
                Current ProcessingContext.

            content_base_dir:
                Root directory of the processed content.

        Returns:
            MergedTranscript

        Raises:
            PersistenceError:
                If any expected artefact is missing or cannot be loaded.

            DuplicateIdsError:
                If duplicate CONTENT UUIDs are discovered.
        """
        if (
            processing_context.processing_mode
            == TranscriptProcessingMode.SINGLE
        ):
            logger.info(
                "Single-part processing detected. Loading artefacts directly."
            )

            run_dir = (
                content_base_dir
                / "artifacts"
            )

            return self._load_part(run_dir)

        logger.info(
            "Merging %d transcript parts.",
            processing_context.total_parts,
        )

        merged_hierarchy: list[Node] = []
        merged_content_store: dict[str, ContentStoreItem] = {}

        for part in processing_context.content_parts:
            logger.info(
                "Loading artefacts for transcript part '%s'.",
                part.part_title,
            )

            run_dir = (
                content_base_dir
                / "artifacts"
                / part.part_title
            )

            processed_content = self._load_part(run_dir)

            self._merge_content_store(
                merged_content_store,
                processed_content.content_store,
            )

            merged_hierarchy.extend(processed_content.hierarchy)

        logger.info(
            "Transcript merge completed successfully "
            "(hierarchy_nodes=%d, content_nodes=%d).",
            len(merged_hierarchy),
            len(merged_content_store),
        )

        return MergedTranscript(
            hierarchy=merged_hierarchy,
            content_store=merged_content_store,
        )

    # ------------------------------------------------------------------ #
    # Private helpers
    # ------------------------------------------------------------------ #

    def _load_part(
        self,
        run_dir: Path,
    ) -> MergedTranscript:
        """
        Load artefacts for one transcript part.
        """
        hierarchy_path = run_dir / "nodes_hierarchy.json"
        content_path = run_dir / "nodes_content.json"

        hierarchy = self._load_hierarchy(hierarchy_path)
        content_store = self._load_content_store(content_path)

        return MergedTranscript(
            hierarchy=hierarchy,
            content_store=content_store,
        )

    def _load_hierarchy(
        self,
        path: Path,
    ) -> list[Node]:
        """
        Load a hierarchy JSON file.
        """
        if not self._persistence_service.exists(path):
            raise PersistenceError(
                f"Hierarchy artefact not found: {path}"
            )

        logger.debug(
            "Loading hierarchy from %s",
            path,
        )

        return self._persistence_service.load_nodes_hierarchy(path)

    def _load_content_store(
        self,
        path: Path,
    ) -> dict[str, ContentStoreItem]:
        """
        Load a nodes_content JSON file.
        """
        if not self._persistence_service.exists(path):
            raise PersistenceError(
                f"Content artefact not found: {path}"
            )

        logger.debug(
            "Loading content store from %s",
            path,
        )

        return self._persistence_service.load_nodes_content(path)

    def _merge_content_store(
        self,
        merged: dict[str, ContentStoreItem],
        incoming: dict[str, ContentStoreItem],
    ) -> None:
        """
        Merge one content store into the accumulated store.

        Raises:
            DuplicateIdsError:
                If duplicate UUIDs are encountered.
        """
        duplicates = merged.keys() & incoming.keys()

        if duplicates:
            duplicate_list = ", ".join(sorted(duplicates))

            raise DuplicateIdsError(
                "Duplicate CONTENT UUIDs detected while merging transcript "
                f"parts: {duplicate_list}"
            )

        merged.update(incoming)