from agentfault.models import ToolResult


def simulated_tool(fault: str = "none") -> ToolResult:
    """Simulate a business tool with different failure scenarios."""

    if fault == "timeout":
        return ToolResult(
            status="failure",
            error="The tool timed out",
            error_type="timeout",
            retryable=True
        )

    if fault == "rate_limit":
        return ToolResult(
            status="failure",
            error="HTTP 429: rate limit exceeded",
            error_type="rate_limit",
            retryable=True
        )

    if fault == "service_unavailable":
        return ToolResult(
            status="failure",
            error="Service temporarily unavailable",
            error_type="service_unavailable",
            retryable=True
        )

    if fault == "permission_denied":
        return ToolResult(
            status="failure",
            error="Permission denied",
            error_type="permission_denied",
            retryable=False
        )

    if fault == "malformed":
        return ToolResult(
            status="success",
            data={"amount": "not-a-number"}
        )

    if fault == "none":
        return ToolResult(
            status="success",
            data={"amount": 100}
        )

    raise ValueError(f"Unknown fault type: {fault}")


def validate_result(result: ToolResult) -> bool:
    """Check whether the tool returned valid business data."""

    if result.status != "success" or result.data is None:
        return False

    amount = result.data.get("amount")

    return (
        isinstance(amount, (int, float))
        and not isinstance(amount, bool)
    )
def should_retry(result: ToolResult) -> bool:
    """Determine whether a failed tool call should be retried."""

    if result.status == "success":
        return False

    return result.retryable