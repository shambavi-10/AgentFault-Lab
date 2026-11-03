
import pytest

from agentfault.circuit_breaker import CircuitBreaker, CircuitState
from agentfault.models import ToolResult
from agentfault.safe_execution import (
    safe_tool_call,
    safe_tool_call_with_circuit_breaker
)


# Existing safe execution tests

def test_successful_tool_call():
    def fake_tool():
        return ToolResult(
            status="success",
            data={"amount": 100}
        )

    result = safe_tool_call(fake_tool)

    assert result.status == "success"
    assert result.data == {"amount": 100}


def test_timeout_exception():
    def fake_tool():
        raise TimeoutError("Request timed out")

    result = safe_tool_call(fake_tool)

    assert result.status == "failure"
    assert result.error == "Request timed out"
    assert result.error_type == "timeout"
    assert result.retryable is True


def test_connection_error():
    def fake_tool():
        raise ConnectionError("Connection lost")

    result = safe_tool_call(fake_tool)

    assert result.status == "failure"
    assert result.error == "Connection lost"
    assert result.error_type == "connection_error"
    assert result.retryable is True


def test_unexpected_exception():
    def fake_tool():
        raise ValueError("Invalid input")

    result = safe_tool_call(fake_tool)

    assert result.status == "failure"
    assert result.error == "Invalid input"
    assert result.error_type == "ValueError"
    assert result.retryable is False


def test_invalid_response_type():
    def fake_tool():
        return "Invalid response"

    result = safe_tool_call(fake_tool)

    assert result.status == "failure"
    assert result.error_type == "invalid_response"
    assert result.retryable is False


# New circuit breaker integration tests

def test_circuit_breaker_allows_successful_tool_call():
    breaker = CircuitBreaker()

    def fake_tool():
        return ToolResult(
            status="success",
            data={"amount": 100}
        )

    result = safe_tool_call_with_circuit_breaker(
        fake_tool,
        breaker
    )

    assert result.status == "success"
    assert breaker.state == CircuitState.CLOSED
    assert breaker.failure_count == 0


def test_circuit_breaker_opens_after_failures():
    breaker = CircuitBreaker(failure_threshold=2)

    def failing_tool():
        return ToolResult(
            status="failure",
            error="Service unavailable",
            error_type="timeout",
            retryable=True
        )

    safe_tool_call_with_circuit_breaker(failing_tool, breaker)
    result = safe_tool_call_with_circuit_breaker(failing_tool, breaker)

    assert result.status == "failure"
    assert breaker.state == CircuitState.OPEN
    assert breaker.failure_count == 2


def test_circuit_breaker_blocks_tool_execution():
    breaker = CircuitBreaker(failure_threshold=1)
    breaker.record_failure()

    call_count = 0

    def fake_tool():
        nonlocal call_count
        call_count += 1

        return ToolResult(
            status="success",
            data={"amount": 100}
        )

    result = safe_tool_call_with_circuit_breaker(
        fake_tool,
        breaker
    )

    assert result.status == "failure"
    assert result.error_type == "circuit_open"
    assert result.retryable is False
    assert call_count == 0


def test_circuit_breaker_recovers_after_successful_probe():
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

    result = safe_tool_call_with_circuit_breaker(
        successful_tool,
        breaker
    )

    assert result.status == "success"
    assert breaker.state == CircuitState.CLOSED
    assert breaker.failure_count == 0
