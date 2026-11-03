
from agentfault.circuit_breaker import CircuitBreaker, CircuitState
from agentfault.faults import simulated_tool
from agentfault.models import ToolResult
from agentfault.retry import run_with_retry


# Existing retry tests

def test_retry_stops_after_success():
    responses = [
        ToolResult(
            status="failure",
            error="Timeout",
            error_type="timeout",
            retryable=True
        ),
        ToolResult(
            status="failure",
            error="Timeout",
            error_type="timeout",
            retryable=True
        ),
        ToolResult(
            status="success",
            data={"amount": 100}
        )
    ]

    calls = {"count": 0}

    def fake_tool():
        result = responses[calls["count"]]
        calls["count"] += 1
        return result

    result = run_with_retry(fake_tool)

    assert result.status == "success"
    assert calls["count"] == 3


def test_retry_stops_on_permanent_failure():
    result = run_with_retry(
        lambda: simulated_tool("permission_denied")
    )

    assert result.status == "failure"
    assert result.retryable is False


def test_retry_stops_after_max_attempts():
    calls = {"count": 0}

    def always_fails():
        calls["count"] += 1

        return ToolResult(
            status="failure",
            error="Timeout",
            error_type="timeout",
            retryable=True
        )

    result = run_with_retry(always_fails, max_attempts=3)

    assert result.status == "failure"
    assert calls["count"] == 3


def test_success_does_not_retry():
    calls = {"count": 0}

    def successful_tool():
        calls["count"] += 1
        return simulated_tool("none")

    result = run_with_retry(successful_tool)

    assert result.status == "success"
    assert calls["count"] == 1


def test_invalid_max_attempts():
    try:
        run_with_retry(
            lambda: simulated_tool("none"),
            max_attempts=0
        )
        assert False, "Expected ValueError"

    except ValueError:
        pass


# New circuit breaker integration tests

def test_retry_engine_stops_when_circuit_opens():
    breaker = CircuitBreaker(failure_threshold=1)
    calls = {"count": 0}

    def failing_tool():
        calls["count"] += 1

        return ToolResult(
            status="failure",
            error="Timeout",
            error_type="timeout",
            retryable=True
        )

    result = run_with_retry(
        failing_tool,
        max_attempts=3,
        circuit_breaker=breaker,
        sleep_fn=lambda _: None
    )

    assert result.status == "failure"
    assert result.error_type == "circuit_open"
    assert calls["count"] == 1
    assert breaker.state == CircuitState.OPEN


def test_retry_engine_works_with_closed_circuit():
    breaker = CircuitBreaker()
    calls = {"count": 0}

    def successful_tool():
        calls["count"] += 1

        return ToolResult(
            status="success",
            data={"amount": 100}
        )

    result = run_with_retry(
        successful_tool,
        circuit_breaker=breaker
    )

    assert result.status == "success"
    assert calls["count"] == 1
    assert breaker.state == CircuitState.CLOSED


def test_retry_engine_recovers_after_circuit_timeout():
    breaker = CircuitBreaker(
        failure_threshold=1,
        recovery_timeout=0
    )

    breaker.record_failure()

    def successful_tool():
        return ToolResult(
            status="success",
            data={"amount": 100}
        )

    result = run_with_retry(
        successful_tool,
        max_attempts=3,
        circuit_breaker=breaker,
        sleep_fn=lambda _: None
    )

    assert result.status == "success"
    assert breaker.state == CircuitState.CLOSED
    assert breaker.failure_count == 0


def test_retry_engine_works_without_circuit_breaker():
    calls = {"count": 0}

    def successful_tool():
        calls["count"] += 1

        return ToolResult(
            status="success",
            data={"amount": 100}
        )

    result = run_with_retry(successful_tool)

    assert result.status == "success"
    assert calls["count"] == 1
