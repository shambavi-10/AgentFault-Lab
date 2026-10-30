
from agentfault.faults import simulated_tool
from agentfault.models import ToolResult
from agentfault.retry import run_with_retry


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
