from agentfault.models import ToolResult
from agentfault.retry import run_with_retry


def test_no_retry_strategy():
    calls = []
    delays = []

    def tool():
        calls.append(1)
        return ToolResult(
            status="failure",
            error="Temporary timeout",
            error_type="timeout",
            retryable=True
        )

    result = run_with_retry(
        tool_call=tool,
        max_attempts=3,
        retry_strategy="none",
        sleep_fn=lambda delay: delays.append(delay)
    )

    assert result.status == "failure"
    assert len(calls) == 1
    assert delays == []


def test_fixed_retry_strategy():
    calls = []
    delays = []

    def tool():
        calls.append(1)

        if len(calls) < 3:
            return ToolResult(
                status="failure",
                error="Temporary timeout",
                error_type="timeout",
                retryable=True
            )

        return ToolResult(
            status="success",
            data={"amount": 100}
        )

    result = run_with_retry(
        tool_call=tool,
        max_attempts=3,
        retry_strategy="fixed",
        base_delay=0.5,
        max_delay=10,
        sleep_fn=lambda delay: delays.append(delay)
    )

    assert result.status == "success"
    assert len(calls) == 3
    assert delays == [0.5, 0.5]


def test_exponential_retry_strategy():
    calls = []
    delays = []

    def tool():
        calls.append(1)

        if len(calls) < 4:
            return ToolResult(
                status="failure",
                error="Temporary timeout",
                error_type="timeout",
                retryable=True
            )

        return ToolResult(
            status="success",
            data={"amount": 100}
        )

    result = run_with_retry(
        tool_call=tool,
        max_attempts=4,
        retry_strategy="exponential",
        base_delay=0.1,
        max_delay=10,
        jitter=False,
        sleep_fn=lambda delay: delays.append(delay)
    )

    assert result.status == "success"
    assert len(calls) == 4
    assert delays == [0.1, 0.2, 0.4]


def test_invalid_retry_strategy():
    def tool():
        return ToolResult(
            status="success",
            data={"amount": 100}
        )

    try:
        run_with_retry(
            tool_call=tool,
            retry_strategy="random"
        )
        assert False, "Expected ValueError"
    except ValueError:
        pass