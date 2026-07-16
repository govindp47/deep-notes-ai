"""
tests/unit/services/test_retry_service.py

Unit tests for RetryService.

Uses unittest.mock.Mock for callables and predicates.
"""
import pytest
from unittest.mock import Mock, call

from deep_notes_ai.domain.models import RetryExhaustedError
from deep_notes_ai.services.retry_service import RetryService


# ---------------------------------------------------------------------------
# test_succeeds_on_first_attempt
# ---------------------------------------------------------------------------

def test_succeeds_on_first_attempt() -> None:
    service = RetryService(max_retries=3)
    fn = Mock(return_value="success")
    is_retryable = Mock(return_value=True)

    result = service.invoke(fn, is_retryable)

    assert result == "success"
    fn.assert_called_once()
    is_retryable.assert_not_called()


# ---------------------------------------------------------------------------
# test_retries_on_retryable_error
# ---------------------------------------------------------------------------

def test_retries_on_retryable_error() -> None:
    service = RetryService(max_retries=3)
    err = ValueError("transient")
    fn = Mock(side_effect=[err, "success"])
    is_retryable = Mock(return_value=True)

    result = service.invoke(fn, is_retryable)

    assert result == "success"
    assert fn.call_count == 2
    is_retryable.assert_called_once_with(err)


# ---------------------------------------------------------------------------
# test_succeeds_on_second_attempt_after_failure
# ---------------------------------------------------------------------------

def test_succeeds_on_second_attempt_after_failure() -> None:
    service = RetryService(max_retries=3)
    err = RuntimeError("oops")
    fn = Mock(side_effect=[err, err, "ok"])
    is_retryable = Mock(return_value=True)

    result = service.invoke(fn, is_retryable)

    assert result == "ok"
    assert fn.call_count == 3
    assert is_retryable.call_count == 2


# ---------------------------------------------------------------------------
# test_raises_retry_exhausted_after_max_retries
# ---------------------------------------------------------------------------

def test_raises_retry_exhausted_after_max_retries() -> None:
    service = RetryService(max_retries=2)
    err = ValueError("keep failing")
    fn = Mock(side_effect=err)
    is_retryable = Mock(return_value=True)

    with pytest.raises(RetryExhaustedError) as exc_info:
        service.invoke(fn, is_retryable)

    assert exc_info.value.attempts == 2
    assert exc_info.value.last_error is err
    assert fn.call_count == 2


# ---------------------------------------------------------------------------
# test_non_retryable_error_propagates_immediately
# ---------------------------------------------------------------------------

def test_non_retryable_error_propagates_immediately() -> None:
    service = RetryService(max_retries=5)
    err = PermissionError("auth failed")
    fn = Mock(side_effect=err)
    is_retryable = Mock(return_value=False)

    with pytest.raises(PermissionError) as exc_info:
        service.invoke(fn, is_retryable)

    assert exc_info.value is err
    fn.assert_called_once()
    is_retryable.assert_called_once_with(err)


# ---------------------------------------------------------------------------
# test_correct_number_of_attempts
# ---------------------------------------------------------------------------

def test_correct_number_of_attempts() -> None:
    max_retries = 4
    service = RetryService(max_retries=max_retries)
    err = ValueError("still failing")
    fn = Mock(side_effect=err)
    is_retryable = Mock(return_value=True)

    with pytest.raises(RetryExhaustedError):
        service.invoke(fn, is_retryable)

    assert fn.call_count == max_retries
    assert is_retryable.call_count == max_retries


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

def test_max_retries_one_succeeds_immediately() -> None:
    service = RetryService(max_retries=1)
    fn = Mock(return_value=42)
    is_retryable = Mock(return_value=True)

    result = service.invoke(fn, is_retryable)
    assert result == 42
    fn.assert_called_once()


def test_max_retries_one_raises_retry_exhausted() -> None:
    service = RetryService(max_retries=1)
    err = ValueError("fail")
    fn = Mock(side_effect=err)
    is_retryable = Mock(return_value=True)

    with pytest.raises(RetryExhaustedError) as exc_info:
        service.invoke(fn, is_retryable)

    assert exc_info.value.attempts == 1


def test_invalid_max_retries_raises() -> None:
    with pytest.raises(ValueError):
        RetryService(max_retries=0)
