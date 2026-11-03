import time
from threading import Thread

from agentfault.circuit_breaker import CircuitBreaker, CircuitState


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
