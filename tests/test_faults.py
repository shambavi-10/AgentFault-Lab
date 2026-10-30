
from agentfault.faults import simulated_tool, validate_result


def test_normal_tool_call():
    result = simulated_tool("none")

    assert result.status == "success"
    assert result.data == {"amount": 100}
    assert validate_result(result) is True


def test_timeout():
    result = simulated_tool("timeout")

    assert result.status == "failure"
    assert result.error_type == "timeout"
    assert validate_result(result) is False


def test_rate_limit():
    result = simulated_tool("rate_limit")

    assert result.status == "failure"
    assert result.error_type == "rate_limit"
    assert validate_result(result) is False


def test_malformed_response():
    result = simulated_tool("malformed")

    assert result.status == "success"
    assert validate_result(result) is False


def test_unknown_fault():
    try:
        simulated_tool("unknown")
        assert False, "Expected ValueError"
    except ValueError as error:
        assert "Unknown fault" in str(error)
