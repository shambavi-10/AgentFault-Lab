
from agentfault.models import ToolResult
from agentfault.reliability_config import ReliabilityConfig
from agentfault.reliability_engine import ReliabilityEngine


def success_result():
    return ToolResult(
        status="success",
        data={"message": "Operation completed"}
    )


def timeout_result():
    return ToolResult(
        status="failure",
        error="Service timed out",
        error_type="timeout",
        retryable=True
    )


def permanent_failure():
    return ToolResult(
        status="failure",
        error="Invalid request",
        error_type="validation_error",
        retryable=False
    )


def test_primary_tool_success():
    config = ReliabilityConfig()

    engine = ReliabilityEngine(config)

    execution = engine.execute(
        primary_tool=success_result
    )

    assert execution.result.status == "success"
    assert execution.fallback_used is False
    assert execution.retry_count == 0
    assert execution.fallback_count == 0


def test_primary_tool_retries_and_recovers():
    config = ReliabilityConfig(
        max_attempts=3,
        retry_strategy="fixed",
        base_delay=0
    )

    engine = ReliabilityEngine(config)

    calls = []

    def primary_tool():
        calls.append(1)

        if len(calls) < 3:
            return timeout_result()

        return success_result()

    execution = engine.execute(primary_tool)

    assert execution.result.status == "success"
    assert len(calls) == 3
    assert execution.retry_count == 2


def test_fallback_recovers_after_primary_failure():
    config = ReliabilityConfig(
        max_attempts=1,
        retry_strategy="none",
        enable_fallback=True
    )

    engine = ReliabilityEngine(config)

    execution = engine.execute(
        primary_tool=timeout_result,
        fallback_tools=[success_result]
    )

    assert execution.result.status == "success"
    assert execution.fallback_used is True
    assert execution.fallback_count == 1


def test_fallback_chain_tries_next_tool():
    config = ReliabilityConfig(
        max_attempts=1,
        retry_strategy="none"
    )

    engine = ReliabilityEngine(config)

    execution = engine.execute(
        primary_tool=timeout_result,
        fallback_tools=[
            timeout_result,
            success_result
        ]
    )

    assert execution.result.status == "success"
    assert execution.fallback_used is True
    assert execution.fallback_count == 2


def test_non_retryable_fallback_failure_stops_chain():
    config = ReliabilityConfig(
        max_attempts=1,
        retry_strategy="none"
    )

    engine = ReliabilityEngine(config)

    execution = engine.execute(
        primary_tool=timeout_result,
        fallback_tools=[
            permanent_failure,
            success_result
        ]
    )

    assert execution.result.status == "failure"
    assert execution.result.error_type == "validation_error"
    assert execution.fallback_count == 1
    assert execution.fallback_used is False


def test_circuit_breaker_blocks_retry_and_fallback_recovers():
    config = ReliabilityConfig(
        max_attempts=2,
        retry_strategy="fixed",
        base_delay=0,
        enable_circuit_breaker=True,
        failure_threshold=1,
        recovery_timeout=1000
    )

    engine = ReliabilityEngine(config)

    primary_calls = []

    def primary_tool():
        primary_calls.append(1)
        return timeout_result()

    execution = engine.execute(
        primary_tool=primary_tool,
        fallback_tools=[success_result]
    )

    assert execution.result.status == "success"
    assert len(primary_calls) == 1
    assert execution.fallback_used is True
    assert execution.circuit_breaker_enabled is True
    assert execution.trace.count_events(
        "circuit_breaker_blocked"
    ) == 1


def test_execution_records_unified_trace():
    config = ReliabilityConfig()

    engine = ReliabilityEngine(config)

    execution = engine.execute(success_result)

    assert execution.trace.count_events(
        "reliability_execution_started"
    ) == 1

    assert execution.trace.count_events(
        "reliability_execution_completed"
    ) == 1


def test_fallback_is_rejected_when_disabled():
    config = ReliabilityConfig(
        enable_fallback=False
    )

    engine = ReliabilityEngine(config)

    try:
        engine.execute(
            primary_tool=timeout_result,
            fallback_tools=[success_result]
        )
    except ValueError as error:
        assert "Fallback tools supplied" in str(error)
    else:
        raise AssertionError("Expected ValueError")
