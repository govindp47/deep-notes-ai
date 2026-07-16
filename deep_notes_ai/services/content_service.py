"""
deep_notes_ai/services/content_service.py

ContentService — orchestrate batched structured-content generation.
"""
from __future__ import annotations

import json
import logging
from dataclasses import asdict
from typing import TYPE_CHECKING

from langchain_core.runnables import Runnable

from deep_notes_ai.domain.algorithms import filter_payload_by_range
from deep_notes_ai.domain.models import (
    BatchCountMismatchError,
    ContentGenerationError,
    ContentPayload,
    ContentStoreItem,
    RetryExhaustedError,
    StructuredContentBatch,
)
from deep_notes_ai.services.partition_service import PartitionService
from deep_notes_ai.services.retry_service import RetryService
from deep_notes_ai.services.validation_service import ValidationService

if TYPE_CHECKING:
    from deep_notes_ai.services.progress_service import ProgressService

logger = logging.getLogger(__name__)


def _is_llm_retryable(exc: Exception) -> bool:
    """
    Retryable predicate for content generation.

    DuplicateIdsError and IncorrectIdsError are retryable (LLM non-determinism).
    BatchCountMismatchError is NOT retryable (caller handles repartition).
    LLMCallError with is_transient=True is retryable.
    All other exceptions are non-retryable.
    """
    from deep_notes_ai.domain.models import (
        DuplicateIdsError,
        IncorrectIdsError,
        LLMCallError,
    )
    if isinstance(exc, (DuplicateIdsError, IncorrectIdsError)):
        return True
    if isinstance(exc, LLMCallError):
        return getattr(exc, "is_transient", False)
    return False


class ContentService:
    """
    Orchestrate batched structured-content generation across all transcript partitions.

    Internal algorithm:
    1. Compute partition ranges for initial_partitions.
    2. For each partition:
       a. Filter payload to items in range.
       b. Build temp-ID mapping (N1..Nk → real UUID).
       c. Build temp ContentPayload list with N-IDs.
       d. Call retry_service.invoke(lambda: llm_chain.invoke(...), is_retryable).
       e. Call validation_service.validate_batch(response, expected_ids).
       f. Map N-IDs back to real UUIDs, populate nodes_content[uuid].content.
    3. If BatchCountMismatchError: restart with fallback_partitions.
    4. Return updated nodes_content.
    """

    def __init__(
        self,
        llm_chain: Runnable,
        partition_service: PartitionService,
        validation_service: ValidationService,
        retry_service: RetryService,
        progress_service: "ProgressService | None" = None,
    ) -> None:
        self._llm_chain = llm_chain
        self._partition_service = partition_service
        self._validation_service = validation_service
        self._retry_service = retry_service
        self._progress_service = progress_service

    def generate(
        self,
        payload: list[ContentPayload],
        nodes_content: dict[str, ContentStoreItem],
        initial_partitions: int,
        fallback_partitions: int,
    ) -> dict[str, ContentStoreItem]:
        """
        Process all partitions and return the updated nodes_content dict
        with .content populated for each UUID.

        Args:
            content_points: The full numbered points list.
            payload:         List of ContentPayload objects (one per CONTENT node).
            nodes_content:   Existing UUID → ContentStoreItem mapping (not mutated).

        Returns:
            New dict with .content populated for all UUIDs in payload.

        Raises:
            ContentGenerationError: if generation fails even after fallback.
        """
        # Work on a copy so we never mutate the caller's dict.
        result = dict(nodes_content)

        try:
            self._process_partitions(
                payload=payload,
                result=result,
                n_partitions=initial_partitions,
            )
        except BatchCountMismatchError as first_mismatch:
            logger.warning(
                "BatchCountMismatchError with %d partitions, retrying with %d: %s",
                initial_partitions,
                fallback_partitions,
                first_mismatch,
            )
            try:
                # Reset result to the original state before retry.
                result = dict(nodes_content)
                self._process_partitions(
                    payload=payload,
                    result=result,
                    n_partitions=fallback_partitions,
                )
            except (BatchCountMismatchError, RetryExhaustedError) as exc:
                raise ContentGenerationError(
                    f"Content generation failed even with fallback partitions "
                    f"({fallback_partitions}): {exc}"
                ) from exc
        except RetryExhaustedError as exc:
            raise ContentGenerationError(
                f"Content generation failed after retries: {exc}"
            ) from exc

        return result

    def _process_partitions(
        self,
        payload: list[ContentPayload],
        result: dict[str, ContentStoreItem],
        n_partitions: int,
        node_name: str = "generate_content",
        stage: str = "Generating Structured Content",
    ) -> None:
        """
        Process all partitions, populating result[uuid].content in place.

        Raises:
            BatchCountMismatchError: if item count is wrong (caller handles repartition).
            RetryExhaustedError:     if retries exhausted on a partition.
        """
        partitioned_payloads = self._partition_service.partition_payloads_by_transcript(payload, n_partitions)

        logger.info("Processing %d partition(s) for content generation.", len(partitioned_payloads))

        for partition_index, partition_payload in enumerate(partitioned_payloads, start=1):
            if not partition_payload:
                logger.debug("Partition %d: no CONTENT nodes, skipping.", partition_index)
                continue

            # Build temp-ID mapping: N1 → real UUID
            temp_id_map: dict[str, str] = {
                f"N{i}": item.id
                for i, item in enumerate(partition_payload, start=1)
            }
            # Invert: real UUID → temp ID (for building LLM input)
            uuid_to_temp: dict[str, str] = {v: k for k, v in temp_id_map.items()}
            expected_temp_ids: set[str] = set(temp_id_map.keys())

            # Build temp payload list for LLM input (N-IDs, not UUIDs).
            temp_payload = [
                asdict(ContentPayload(
                    id=uuid_to_temp[item.id],
                    hierarchy_path=item.hierarchy_path,
                    range=item.range,
                    content_points_list=item.content_points_list,
                ))
                for item in partition_payload
            ]

            llm_input = json.dumps(temp_payload, indent=2)

            def _invoke(
                llm_input: str = llm_input,
                expected_ids: set[str] = expected_temp_ids,
            ) -> StructuredContentBatch:
                response: StructuredContentBatch = self._llm_chain.invoke(llm_input)
                self._validation_service.validate_batch(
                    response=response,
                    expected_ids=expected_ids,
                )
                return response

            logger.info(
                "Partition %d/%d: invoking LLM for %d CONTENT node(s).",
                partition_index, len(partitioned_payloads), len(partition_payload),
            )

            response = self._retry_service.invoke(
                fn=_invoke,
                is_retryable=_is_llm_retryable,
            )

            # Map N-IDs back to real UUIDs and store content.
            for item in response.items:
                real_uuid = temp_id_map[item.id]
                result[real_uuid] = ContentStoreItem(
                    content=item.markdown,
                    summary=result.get(real_uuid, ContentStoreItem()).summary,
                )
                logger.debug("Stored content for uuid=%s", real_uuid)

            if self._progress_service is not None:
                self._progress_service.emit_progress(
                    node_name=node_name,
                    stage=stage,
                    message=f"Partition {partition_index} / {len(partitioned_payloads)}",
                    current=partition_index,
                    total=len(partitioned_payloads),
                )
