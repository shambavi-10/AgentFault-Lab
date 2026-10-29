
from typing import Any


def simulated_tool(fault: str = "none") -> dict[str, Any]:
    """Simulate a business tool with controllable failures."""

    if fault == "timeout":
        raise TimeoutError("The tool timed out")

    if fault == "rate_limit":
        raise RuntimeError("HTTP 429: rate limit exceeded")

    if fault == "malformed":
        return {"status": "success", "amount": "not-a-number"}

    if fault == "none":
        return {"status": "success", "amount": 100}

    raise ValueError(f"Unknown fault type: {fault}")


def validate_result(result: dict[str, Any]) -> bool:
    """Check whether the tool returned valid data."""

    if result.get("status") != "success":
        return False

    amount = result.get("amount")

    return (
        isinstance(amount, (int, float))
        and not isinstance(amount, bool)
    )
