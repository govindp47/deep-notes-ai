"""
deep_notes_ai/services/retry_service.py

RetryService — generic retry loop for callable operations.
"""
from __future__ import annotations

import logging
from typing import Callable, TypeVar

from deep_notes_ai.domain.models import RetryExhaustedError

logger = logging.getLogger(__name__)

T = TypeVar("T")


class RetryService:
    """
    Generic retry loop.

    - Pure Python — no `tenacity` dependency.
    - `is_retryable` is a predicate function injected by the caller.
    - `fn` is a zero-argument callable (use `functools.partial` to bind args).
    """

    def __init__(self, max_retries: int) -> None:
        if max_retries < 1:
            raise ValueError("max_retries must be at least 1.")
        self._max_retries = max_retries

    def invoke(
        self,
        fn: Callable[[], T],
        is_retryable: Callable[[Exception], bool],
    ) -> T:
        """
        Calls fn() up to max_retries times.

        Args:
            fn:           Zero-argument callable to invoke.
            is_retryable: Predicate — returns True if the exception is
                          worth retrying.

        Returns:
            The return value of fn() on a successful call.

        Raises:
            Exception:          The original exception if is_retryable returns False.
            RetryExhaustedError: If all max_retries attempts fail.
        """
        last_error: Exception | None = None

        for attempt in range(1, self._max_retries + 1):
            try:
                return fn()
            except Exception as exc:
                if not is_retryable(exc):
                    logger.debug(
                        "Non-retryable error on attempt %d: %s",
                        attempt,
                        exc,
                    )
                    raise

                logger.warning(
                    "Retryable error on attempt %d/%d: %s",
                    attempt,
                    self._max_retries,
                    exc,
                )
                last_error = exc

        raise RetryExhaustedError(
            attempts=self._max_retries,
            last_error=last_error,  # type: ignore[arg-type]
        )
