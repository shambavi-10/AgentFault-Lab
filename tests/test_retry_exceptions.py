from agentfault.models import ToolResult
from agentfault.retry import run_with_retry


def test_retry_recovers_from_timeout_exception():

    calls = {"count": 0}
    delays = []

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
        base_delay=1,
        jitter=False,
        sleep_fn=lambda seconds: delays.append(seconds)
    )

    assert result.status == "success"
    assert calls["count"] == 2
    assert delays == [1]


def test_unexpected_exception_does_not_retry():

    calls = {"count": 0}
    delays = []

    def fake_tool():
        calls["count"] += 1
        raise ValueError("Invalid input")

    result = run_with_retry(
        fake_tool,
        max_attempts=3,
        sleep_fn=lambda seconds: delays.append(seconds)
    )

    assert result.status == "failure"
    assert result.error == "Invalid input"
    assert result.error_type == "ValueError"
    assert result.retryable is False
    assert calls["count"] == 1
    assert delays == []