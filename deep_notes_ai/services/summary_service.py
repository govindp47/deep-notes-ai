"""
deep_notes_ai/services/summary_service.py

SummaryService — orchestrate batched revision-summary generation.

Identical pattern to ContentService except:
- Input to LLM is list[StructuredContentPayload] using nodes_content[id].content.
- Populates nodes_content[uuid].summary (not .content).
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
    ContentPayload,
    ContentStoreItem,
    RetryExhaustedError,
    StructuredContentPayload,
    SummaryGenerationError,
    ContentSummaryBatch,
)
from deep_notes_ai.services.partition_service import PartitionService
from deep_notes_ai.services.retry_service import RetryService
from deep_notes_ai.services.validation_service import ValidationService

if TYPE_CHECKING:
    from deep_notes_ai.services.progress_service import ProgressService

logger = logging.getLogger(__name__)


def _is_llm_retryable(exc: Exception) -> bool:
    """
    Retryable predicate for summary generation.

    Same rules as ContentService.
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


class SummaryService:
    """
    Orchestrate batched revision-summary generation across all transcript partitions.

    Identical algorithm to ContentService, with these differences:
    - Input payload items are StructuredContentPayload (uses .content from nodes_content).
    - Populates nodes_content[uuid].summary (not .content).
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
        with .summary populated for each UUID.

        Args:
            content_points: The full numbered points list.
            payload:         List of ContentPayload objects (one per CONTENT node).
            nodes_content:   Existing UUID → ContentStoreItem mapping (not mutated).

        Returns:
            New dict with .summary populated for all UUIDs in payload.

        Raises:
            SummaryGenerationError: if generation fails even after fallback.
        """
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
                result = dict(nodes_content)
                self._process_partitions(
                    payload=payload,
                    result=result,
                    n_partitions=fallback_partitions,
                )
            except (BatchCountMismatchError, RetryExhaustedError) as exc:
                raise SummaryGenerationError(
                    f"Summary generation failed even with fallback partitions "
                    f"({fallback_partitions}): {exc}"
                ) from exc
        except RetryExhaustedError as exc:
            raise SummaryGenerationError(
                f"Summary generation failed after retries: {exc}"
            ) from exc

        return result

    def _process_partitions(
        self,
        payload: list[ContentPayload],
        result: dict[str, ContentStoreItem],
        n_partitions: int,
        node_name: str = "generate_summaries",
        stage: str = "Generating Summaries",
    ) -> None:
        """
        Process all partitions, populating result[uuid].summary in place.

        Raises:
            BatchCountMismatchError: if item count is wrong.
            RetryExhaustedError:     if retries exhausted on a partition.
        """
        partitioned_payloads = self._partition_service.partition_payloads_by_content(payload, result, n_partitions)

        logger.info("Processing %d partition(s) for summary generation.", len(partitioned_payloads))

        for partition_index, partition_payload in enumerate(partitioned_payloads, start=1):
            if not partition_payload:
                logger.debug("Partition %d: no CONTENT nodes, skipping.", partition_index)
                continue

            # Build temp-ID mapping: N1 → real UUID
            temp_id_map: dict[str, str] = {
                f"N{i}": item.id
                for i, item in enumerate(partition_payload, start=1)
            }
            uuid_to_temp: dict[str, str] = {v: k for k, v in temp_id_map.items()}
            expected_temp_ids: set[str] = set(temp_id_map.keys())

            # Build StructuredContentPayload list for LLM input.
            temp_summary_payload = [
                asdict(StructuredContentPayload(
                    id=uuid_to_temp[item.id],
                    hierarchy_path=item.hierarchy_path,
                    structured_content=result.get(
                        item.id, ContentStoreItem()
                    ).content,
                ))
                for item in partition_payload
            ]

            llm_input = json.dumps(temp_summary_payload, indent=2)

            def _invoke(
                llm_input: str = llm_input,
                expected_ids: set[str] = expected_temp_ids,
            ) -> ContentSummaryBatch:
                response: ContentSummaryBatch = self._llm_chain.invoke(llm_input)
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

            # Map N-IDs back to real UUIDs and store summary.
            for item in response.items:
                real_uuid = temp_id_map[item.id]
                existing = result.get(real_uuid, ContentStoreItem())
                result[real_uuid] = ContentStoreItem(
                    content=existing.content,
                    summary=item.summary,
                )
                logger.debug("Stored summary for uuid=%s", real_uuid)

            if self._progress_service is not None:
                self._progress_service.emit_progress(
                    node_name=node_name,
                    stage=stage,
                    message=f"Partition {partition_index} / {len(partitioned_payloads)}",
                    current=partition_index,
                    total=len(partitioned_payloads),
                )
