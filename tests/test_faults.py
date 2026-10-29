
import pytest

from agentfault.faults import simulated_tool, validate_result


def test_normal_tool_call():
    result = simulated_tool("none")

    assert result == {"status": "success", "amount": 100}
    assert validate_result(result) is True


def test_timeout():
    with pytest.raises(TimeoutError):
        simulated_tool("timeout")


def test_rate_limit():
    with pytest.raises(RuntimeError, match="429"):
        simulated_tool("rate_limit")


def test_malformed_response():
    result = simulated_tool("malformed")

    assert result["status"] == "success"
    assert validate_result(result) is False


def test_unknown_fault():
    with pytest.raises(ValueError, match="Unknown fault"):
        simulated_tool("unknown")
