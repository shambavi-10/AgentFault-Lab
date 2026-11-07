import time
from threading import Thread
from agentfault.circuit_breaker import CircuitBreaker, CircuitState
from unittest.mock import Mock

import pytest

def test_circuit_starts_closed():
    breaker = CircuitBreaker()
    assert breaker.state == CircuitState.CLOSED
    assert breaker.failure_count == 0


def test_circuit_opens_after_failure_threshold():
    breaker = CircuitBreaker(failure_threshold=2)
    breaker.record_failure()
    assert breaker.state == CircuitState.CLOSED

    breaker.record_failure()
    assert breaker.state == CircuitState.OPEN


def test_open_circuit_blocks_requests():
    breaker = CircuitBreaker(failure_threshold=1)
    breaker.record_failure()

    allowed, is_probe = breaker.acquire_permission()

    assert allowed is False
    assert is_probe is False


def test_open_circuit_allows_probe_after_timeout():
    breaker = CircuitBreaker(
        failure_threshold=1,
        recovery_timeout=0.05
    )
    breaker.record_failure()
    time.sleep(0.06)

    allowed, is_probe = breaker.acquire_permission()

    assert allowed is True
    assert is_probe is True
    assert breaker.state == CircuitState.HALF_OPEN


def test_successful_probe_closes_circuit():
    breaker = CircuitBreaker(
        failure_threshold=1,
        recovery_timeout=0
    )
    breaker.record_failure()

    allowed, is_probe = breaker.acquire_permission()
    assert allowed is True
    assert is_probe is True

    breaker.record_success(is_probe=True)

    assert breaker.state == CircuitState.CLOSED
    assert breaker.failure_count == 0


def test_failed_probe_reopens_circuit():
    breaker = CircuitBreaker(
        failure_threshold=1,
        recovery_timeout=0
    )
    breaker.record_failure()

    allowed, is_probe = breaker.acquire_permission()
    assert allowed is True
    assert is_probe is True

    breaker.record_failure(is_probe=True)

    assert breaker.state == CircuitState.OPEN
    assert breaker.failure_count == 2


def test_only_one_concurrent_recovery_probe_is_allowed():
    breaker = CircuitBreaker(
        failure_threshold=1,
        recovery_timeout=0
    )
    breaker.record_failure()

    results = []

    def request_permission():
        results.append(breaker.acquire_permission())

    threads = [Thread(target=request_permission) for _ in range(10)]

    for thread in threads:
        thread.start()

    for thread in threads:
        thread.join()

    allowed_probes = [
        result for result in results if result == (True, True)
    ]

    assert len(allowed_probes) == 1
    assert breaker.state == CircuitState.HALF_OPEN

def test_invalid_failure_threshold():
    with pytest.raises(
        ValueError,
        match="Failure threshold must be at least 1"
    ):
        CircuitBreaker(failure_threshold=0)


def test_negative_recovery_timeout():
    with pytest.raises(
        ValueError,
        match="Recovery timeout cannot be negative"
    ):
        CircuitBreaker(recovery_timeout=-1)


def test_zero_recovery_timeout_is_valid():
    breaker = CircuitBreaker(recovery_timeout=0)

    assert breaker.recovery_timeout == 0


def test_half_open_circuit_blocks_additional_probes():
    breaker = CircuitBreaker(
        failure_threshold=1,
        recovery_timeout=0
    )

    breaker.record_failure()

    first_permission = breaker.acquire_permission()
    second_permission = breaker.acquire_permission()

    assert first_permission == (True, True)
    assert second_permission == (False, False)
    assert breaker.state == CircuitState.HALF_OPEN


def test_unrelated_success_does_not_close_half_open_circuit():
    breaker = CircuitBreaker(
        failure_threshold=1,
        recovery_timeout=0
    )

    breaker.record_failure()
    breaker.acquire_permission()

    breaker.record_success(is_probe=False)

    assert breaker.state == CircuitState.HALF_OPEN
    assert breaker.failure_count == 1


def test_unrelated_failure_does_not_reopen_half_open_circuit():
    breaker = CircuitBreaker(
        failure_threshold=1,
        recovery_timeout=0
    )

    breaker.record_failure()
    breaker.acquire_permission()

    breaker.record_failure(is_probe=False)

    assert breaker.state == CircuitState.HALF_OPEN
    assert breaker.failure_count == 1


def test_failure_is_ignored_when_circuit_is_already_open():
    breaker = CircuitBreaker(
        failure_threshold=1,
        recovery_timeout=100
    )

    breaker.record_failure()
    original_failure_time = breaker.last_failure_time

    breaker.record_failure()

    assert breaker.state == CircuitState.OPEN
    assert breaker.failure_count == 1
    assert breaker.last_failure_time == original_failure_time


def test_success_in_closed_state_resets_failure_count():
    breaker = CircuitBreaker(failure_threshold=3)

    breaker.record_failure()
    breaker.record_failure()

    breaker.record_success()

    assert breaker.state == CircuitState.CLOSED
    assert breaker.failure_count == 0


def test_allow_request_returns_permission():
    breaker = CircuitBreaker()

    assert breaker.allow_request() is True

    breaker.record_failure()
    breaker.record_failure()
    breaker.record_failure()

    assert breaker.allow_request() is False


def test_tracing_records_circuit_open_transition():
    trace = Mock()
    breaker = CircuitBreaker(
        failure_threshold=1,
        trace=trace
    )

    breaker.record_failure()

    trace.record.assert_called_once_with(
        "circuit_breaker_opened",
        message="Failure threshold reached. Circuit opened."
    )


def test_tracing_records_half_open_transition():
    trace = Mock()
    breaker = CircuitBreaker(
        failure_threshold=1,
        recovery_timeout=0,
        trace=trace
    )

    breaker.record_failure()
    trace.record.reset_mock()

    allowed, is_probe = breaker.acquire_permission()

    assert allowed is True
    assert is_probe is True

    trace.record.assert_called_once_with(
        "circuit_breaker_half_open",
        message="Recovery timeout elapsed. Recovery probe allowed."
    )


def test_tracing_records_successful_recovery():
    trace = Mock()
    breaker = CircuitBreaker(
        failure_threshold=1,
        recovery_timeout=0,
        trace=trace
    )

    breaker.record_failure()
    breaker.acquire_permission()
    trace.record.reset_mock()

    breaker.record_success(is_probe=True)

    trace.record.assert_called_once_with(
        "circuit_breaker_closed",
        message="Recovery probe succeeded. Circuit closed."
    )


def test_tracing_records_failed_recovery():
    trace = Mock()
    breaker = CircuitBreaker(
        failure_threshold=1,
        recovery_timeout=0,
        trace=trace
    )

    breaker.record_failure()
    breaker.acquire_permission()
    trace.record.reset_mock()

    breaker.record_failure(is_probe=True)

    trace.record.assert_called_once_with(
        "circuit_breaker_opened",
        message="Recovery probe failed. Circuit reopened."
    )


def test_unexpected_state_denies_permission():
    breaker = CircuitBreaker()

    # Defensive test for an unexpected internal state.
    breaker.state = "unexpected"

    assert breaker.acquire_permission() == (False, False)

def test_half_open_state_allows_probe_when_none_is_in_progress():
    breaker = CircuitBreaker()

    # Simulate a half-open circuit with no active recovery probe.
    breaker.state = CircuitState.HALF_OPEN
    breaker._probe_in_progress = False

    allowed, is_probe = breaker.acquire_permission()

    assert allowed is True
    assert is_probe is True
    assert breaker._probe_in_progress is True