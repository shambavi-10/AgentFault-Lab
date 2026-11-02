from agentfault.tracing import ExecutionTrace
from agentfault.models import ToolResult
from agentfault.retry import run_with_retry

def test_trace_has_unique_execution_id():
    first = ExecutionTrace()
    second = ExecutionTrace()

    assert first.execution_id != second.execution_id


def test_record_event():
    trace = ExecutionTrace()

    event = trace.record(
        event_type="execution_started",
        message="Execution started"
    )

    assert event.event_type == "execution_started"
    assert event.execution_id == trace.execution_id
    assert len(trace.events) == 1


def test_record_multiple_events():
    trace = ExecutionTrace()

    trace.record("execution_started")
    trace.record("tool_call_started", attempt=1)
    trace.record("tool_call_failed", attempt=1)

    assert len(trace.events) == 3


def test_get_events():
    trace = ExecutionTrace()

    trace.record(
        event_type="tool_call_failed",
        attempt=1,
        status="failure",
        error_type="timeout"
    )

    events = trace.get_events()

    assert len(events) == 1
    assert events[0]["event_type"] == "tool_call_failed"
    assert events[0]["error_type"] == "timeout"


def test_count_events():
    trace = ExecutionTrace()

    trace.record("tool_call_started", attempt=1)
    trace.record("tool_call_failed", attempt=1)
    trace.record("tool_call_started", attempt=2)
    trace.record("tool_call_succeeded", attempt=2)

    assert trace.count_events("tool_call_started") == 2
    assert trace.count_events("tool_call_failed") == 1
    assert trace.count_events("tool_call_succeeded") == 1

def test_retry_engine_records_successful_execution():
    trace = ExecutionTrace()

    def fake_tool():
        return ToolResult(
            status="success",
            data={"amount": 100}
        )

    result = run_with_retry(
        fake_tool,
        trace=trace
    )

    event_types = [
        event["event_type"]
        for event in trace.get_events()
    ]

    assert result.status == "success"
    assert "execution_started" in event_types
    assert "tool_call_started" in event_types
    assert "tool_call_succeeded" in event_types
    assert "execution_completed" in event_types


def test_retry_engine_records_failed_attempt():
    trace = ExecutionTrace()
    calls = {"count": 0}

    def fake_tool():
        calls["count"] += 1

        if calls["count"] == 1:
            raise TimeoutError("Temporary timeout")

        return ToolResult(
            status="success",
            data={"amount": 100}
        )

    result = run_with_retry(
        fake_tool,
        max_attempts=3,
        jitter=False,
        sleep_fn=lambda seconds: None,
        trace=trace
    )

    event_types = [
        event["event_type"]
        for event in trace.get_events()
    ]

    assert result.status == "success"
    assert "tool_call_failed" in event_types
    assert "retry_scheduled" in event_types
    assert "tool_call_succeeded" in event_types