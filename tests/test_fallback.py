
from agentfault.fallback import execute_with_fallback
from agentfault.models import ToolResult
from agentfault.tracing import ExecutionTrace
import pytest

# ==================================================
# BASIC FALLBACK TESTS
# ==================================================

def test_primary_success_does_not_call_fallback():
    calls = {"fallback": 0}

    def primary():
        return ToolResult(
            status="success",
            data={"customer": "Alice"}
        )

    def fallback():
        calls["fallback"] += 1
        return ToolResult(
            status="success",
            data={"customer": "Backup Alice"}
        )

    result = execute_with_fallback(primary, fallback)

    assert result.status == "success"
    assert result.data == {"customer": "Alice"}
    assert calls["fallback"] == 0


def test_retryable_primary_failure_uses_fallback():
    def primary():
        return ToolResult(
            status="failure",
            error="Primary API timed out",
            error_type="timeout",
            retryable=True
        )

    def fallback():
        return ToolResult(
            status="success",
            data={"customer": "Backup Alice"}
        )

    result = execute_with_fallback(primary, fallback)

    assert result.status == "success"
    assert result.data == {"customer": "Backup Alice"}


def test_non_retryable_failure_skips_fallback():
    calls = {"fallback": 0}

    def primary():
        return ToolResult(
            status="failure",
            error="Customer not found",
            error_type="customer_not_found",
            retryable=False
        )

    def fallback():
        calls["fallback"] += 1
        return ToolResult(
            status="success",
            data={"customer": "Backup Alice"}
        )

    result = execute_with_fallback(primary, fallback)

    assert result.status == "failure"
    assert result.error == "Customer not found"
    assert calls["fallback"] == 0


def test_both_tools_fail():
    def primary():
        return ToolResult(
            status="failure",
            error="Primary timed out",
            error_type="timeout",
            retryable=True
        )

    def fallback():
        return ToolResult(
            status="failure",
            error="Backup connection failed",
            error_type="connection_error",
            retryable=True
        )

    result = execute_with_fallback(primary, fallback)

    assert result.status == "failure"
    assert result.error == "Backup connection failed"
    assert result.error_type == "connection_error"


def test_fallback_execution_is_traced():
    trace = ExecutionTrace()

    def primary():
        return ToolResult(
            status="failure",
            error="Primary timed out",
            error_type="timeout",
            retryable=True
        )

    def fallback():
        return ToolResult(
            status="success",
            data={"customer": "Backup Alice"}
        )

    execute_with_fallback(primary, fallback, trace=trace)

    event_types = [
        event["event_type"]
        for event in trace.get_events()
    ]

    assert "fallback_execution_started" in event_types
    assert "primary_tool_failed" in event_types
    assert "fallback_tool_started" in event_types
    assert "fallback_tool_succeeded" in event_types
    assert "fallback_execution_completed" in event_types


# ==================================================
# EXCEPTION HANDLING TESTS
# ==================================================

def test_primary_timeout_exception_uses_fallback():
    def primary():
        raise TimeoutError("Primary API timed out")

    def fallback():
        return ToolResult(
            status="success",
            data={"customer": "Backup Alice"}
        )

    result = execute_with_fallback(primary, fallback)

    assert result.status == "success"
    assert result.data == {"customer": "Backup Alice"}


def test_primary_connection_exception_uses_fallback():
    def primary():
        raise ConnectionError("Primary connection lost")

    def fallback():
        return ToolResult(
            status="success",
            data={"customer": "Backup Alice"}
        )

    result = execute_with_fallback(primary, fallback)

    assert result.status == "success"
    assert result.data == {"customer": "Backup Alice"}


def test_fallback_timeout_exception_returns_failure():
    def primary():
        raise TimeoutError("Primary API timed out")

    def fallback():
        raise TimeoutError("Backup API timed out")

    result = execute_with_fallback(primary, fallback)

    assert result.status == "failure"
    assert result.error == "Backup API timed out"
    assert result.error_type == "timeout"
    assert result.retryable is True


# ==================================================
# MULTIPLE FALLBACK CHAIN TESTS
# ==================================================

def test_fallback_chain_uses_next_tool_after_retryable_failure():
    calls = []

    def primary():
        calls.append("primary")
        return ToolResult(
            status="failure",
            error="Primary timeout",
            error_type="timeout",
            retryable=True
        )

    def backup1():
        calls.append("backup1")
        return ToolResult(
            status="failure",
            error="Backup 1 unavailable",
            error_type="connection_error",
            retryable=True
        )

    def backup2():
        calls.append("backup2")
        return ToolResult(
            status="success",
            data={"customer": "Alice"}
        )

    result = execute_with_fallback(
        primary,
        fallback_tools=[backup1, backup2]
    )

    assert result.status == "success"
    assert result.data == {"customer": "Alice"}
    assert calls == ["primary", "backup1", "backup2"]


def test_fallback_chain_returns_last_failure():
    def primary():
        return ToolResult(
            status="failure",
            error="Primary timeout",
            error_type="timeout",
            retryable=True
        )

    def backup1():
        return ToolResult(
            status="failure",
            error="Backup 1 failed",
            error_type="connection_error",
            retryable=True
        )

    def backup2():
        return ToolResult(
            status="failure",
            error="Backup 2 failed",
            error_type="timeout",
            retryable=True
        )

    result = execute_with_fallback(
        primary,
        fallback_tools=[backup1, backup2]
    )

    assert result.status == "failure"
    assert result.error == "Backup 2 failed"


def test_fallback_chain_stops_on_non_retryable_failure():
    calls = []

    def primary():
        return ToolResult(
            status="failure",
            error="Primary timeout",
            error_type="timeout",
            retryable=True
        )

    def backup1():
        calls.append("backup1")
        return ToolResult(
            status="failure",
            error="Customer not found",
            error_type="customer_not_found",
            retryable=False
        )

    def backup2():
        calls.append("backup2")
        return ToolResult(
            status="success",
            data={"customer": "Alice"}
        )

    result = execute_with_fallback(
        primary,
        fallback_tools=[backup1, backup2]
    )

    assert result.status == "failure"
    assert result.error == "Customer not found"
    assert calls == ["backup1"]


def test_fallback_chain_traces_each_attempt():
    trace = ExecutionTrace()

    def primary():
        return ToolResult(
            status="failure",
            error="Primary timeout",
            error_type="timeout",
            retryable=True
        )

    def backup1():
        return ToolResult(
            status="failure",
            error="Backup 1 failed",
            error_type="connection_error",
            retryable=True
        )

    def backup2():
        return ToolResult(
            status="success",
            data={"customer": "Alice"}
        )

    execute_with_fallback(
        primary,
        fallback_tools=[backup1, backup2],
        trace=trace
    )

    events = trace.get_events()

    fallback_started = [
        event for event in events
        if event["event_type"] == "fallback_tool_started"
    ]

    fallback_succeeded = [
        event for event in events
        if event["event_type"] == "fallback_tool_succeeded"
    ]

    assert len(fallback_started) == 2
    assert len(fallback_succeeded) == 1
    assert fallback_succeeded[0]["attempt"] == 2


# ==================================================
# ADDITIONAL COVERAGE TESTS
# ==================================================

def test_both_fallback_arguments_raise_error():
    def primary():
        return ToolResult(status="success")

    def fallback():
        return ToolResult(status="success")

    with pytest.raises(
        ValueError,
        match="Provide fallback_tool or fallback_tools, not both",
    ):
        execute_with_fallback(
            primary,
            fallback_tool=fallback,
            fallback_tools=[fallback],
        )


def test_primary_success_is_traced():
    trace = ExecutionTrace()

    def primary():
        return ToolResult(
            status="success",
            data={"result": "primary"},
        )

    result = execute_with_fallback(
        primary,
        trace=trace,
    )

    assert result.status == "success"

    event_types = [
        event["event_type"]
        for event in trace.get_events()
    ]

    assert "fallback_execution_started" in event_types
    assert "primary_tool_started" in event_types
    assert "primary_tool_succeeded" in event_types
    assert "fallback_execution_completed" in event_types


def test_non_retryable_primary_failure_is_traced():
    trace = ExecutionTrace()

    def primary():
        return ToolResult(
            status="failure",
            error="Invalid request",
            error_type="validation_error",
            retryable=False,
        )

    result = execute_with_fallback(
        primary,
        fallback_tools=[],
        trace=trace,
    )

    assert result.status == "failure"
    assert result.error == "Invalid request"

    event_types = [
        event["event_type"]
        for event in trace.get_events()
    ]

    assert "primary_tool_failed" in event_types
    assert "fallback_skipped" in event_types
    assert "fallback_execution_completed" in event_types

    assert "fallback_tool_started" not in event_types


def test_non_retryable_fallback_failure_is_traced():
    trace = ExecutionTrace()

    def primary():
        return ToolResult(
            status="failure",
            error="Primary timeout",
            error_type="timeout",
            retryable=True,
        )

    def fallback():
        return ToolResult(
            status="failure",
            error="Invalid backup request",
            error_type="validation_error",
            retryable=False,
        )

    result = execute_with_fallback(
        primary,
        fallback_tools=[fallback],
        trace=trace,
    )

    assert result.status == "failure"
    assert result.error == "Invalid backup request"

    event_types = [
        event["event_type"]
        for event in trace.get_events()
    ]

    assert "fallback_tool_started" in event_types
    assert "fallback_tool_failed" in event_types
    assert "fallback_execution_completed" in event_types


def test_empty_fallback_chain_is_traced():
    trace = ExecutionTrace()

    def primary():
        return ToolResult(
            status="failure",
            error="Primary timeout",
            error_type="timeout",
            retryable=True,
        )

    result = execute_with_fallback(
        primary,
        fallback_tools=[],
        trace=trace,
    )

    assert result.status == "failure"
    assert result.error == "Primary timeout"

    events = trace.get_events()

    completed_events = [
        event for event in events
        if event["event_type"] == "fallback_execution_completed"
    ]

    assert len(completed_events) == 1
    assert completed_events[0]["message"] == "All available tools failed."
