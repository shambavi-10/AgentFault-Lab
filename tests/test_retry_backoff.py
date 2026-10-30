from agentfault.models import ToolResult
from agentfault.retry import run_with_retry


def test_retry_waits_between_attempts():

    delays = []
    calls = {"count": 0}

    def fake_sleep(seconds):
        delays.append(seconds)

    def fake_tool():
        calls["count"] += 1

        if calls["count"] < 3:
            return ToolResult(
                status="failure",
                error="Timeout",
                error_type="timeout",
                retryable=True
            )

        return ToolResult(
            status="success",
            data={"amount": 100}
        )

    result = run_with_retry(
        fake_tool,
        max_attempts=3,
        base_delay=1,
        jitter=False,
        sleep_fn=fake_sleep
    )

    assert result.status == "success"
    assert calls["count"] == 3
    assert delays == [1, 2]


def test_no_sleep_after_permanent_failure():

    delays = []

    def fake_sleep(seconds):
        delays.append(seconds)

    def fake_tool():
        return ToolResult(
            status="failure",
            error="Permission denied",
            error_type="permission_denied",
            retryable=False
        )

    result = run_with_retry(
        fake_tool,
        sleep_fn=fake_sleep
    )

    assert result.status == "failure"
    assert delays == []


def test_no_sleep_after_final_attempt():

    delays = []

    def fake_sleep(seconds):
        delays.append(seconds)

    def fake_tool():
        return ToolResult(
            status="failure",
            error="Timeout",
            error_type="timeout",
            retryable=True
        )

    result = run_with_retry(
        fake_tool,
        max_attempts=3,
        jitter=False,
        sleep_fn=fake_sleep
    )

    assert result.status == "failure"
    assert delays == [1, 2]