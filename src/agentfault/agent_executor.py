
from dataclasses import dataclass
from time import perf_counter

from agentfault.agent_config import AgentConfig
from agentfault.faults import validate_result
from agentfault.models import ToolResult
from agentfault.retry import run_with_retry
from agentfault.scenario_runner import ScenarioRunner
from agentfault.scenarios import FailureScenario
from agentfault.tracing import ExecutionTrace
from agentfault.stochastic_runner import StochasticToolRunner
from agentfault.stochastic_scenario_runner import StochasticScenarioRunner
from collections.abc import Callable, Sequence

from agentfault.reliability_config import ReliabilityConfig
from agentfault.reliability_engine import ReliabilityEngine

@dataclass
class AgentExecution:
    agent_name: str
    scenario_name: str
    result: ToolResult
    trace: ExecutionTrace
    execution_time_ms: float
    retry_count: int
    valid_business_result: bool
    scheduled_backoff_seconds: float

    # Unified reliability metrics
    fallback_count: int = 0
    fallback_used: bool = False
    circuit_breaker_enabled: bool = False


def execute_scenario(
    config: AgentConfig,
    scenario: FailureScenario
) -> AgentExecution:

    runner = ScenarioRunner(scenario)
    trace = ExecutionTrace()
    scheduled_delays = []

    start_time = perf_counter()

    result = run_with_retry(
        tool_call=runner.run,
        max_attempts=config.max_attempts,
        retry_strategy=config.retry_strategy,
        base_delay=config.base_delay,
        max_delay=config.max_delay,
        jitter=config.jitter,
        sleep_fn=lambda delay: scheduled_delays.append(delay),
        trace=trace
    )

    execution_time_ms = (perf_counter() - start_time) * 1000

    retry_count = trace.count_events("retry_scheduled")
    valid_business_result = validate_result(result)

    return AgentExecution(
        agent_name=config.name,
        scenario_name=scenario.name,
        result=result,
        trace=trace,
        execution_time_ms=execution_time_ms,
        retry_count=retry_count,
        valid_business_result=valid_business_result,
        scheduled_backoff_seconds=sum(scheduled_delays)
    )


def execute_stochastic(
    config: AgentConfig,
    timeout_probability: float = 0.1,
    rate_limit_probability: float = 0.1,
    seed: int | None = None
) -> AgentExecution:

    runner = StochasticToolRunner(
        timeout_probability=timeout_probability,
        rate_limit_probability=rate_limit_probability,
        seed=seed
    )

    trace = ExecutionTrace()
    scheduled_delays = []

    start_time = perf_counter()

    result = run_with_retry(
        tool_call=runner.run,
        max_attempts=config.max_attempts,
        retry_strategy=config.retry_strategy,
        base_delay=config.base_delay,
        max_delay=config.max_delay,
        jitter=config.jitter,
        sleep_fn=lambda delay: scheduled_delays.append(delay),
        trace=trace
    )

    execution_time_ms = (perf_counter() - start_time) * 1000

    retry_count = trace.count_events("retry_scheduled")
    valid_business_result = validate_result(result)

    return AgentExecution(
        agent_name=config.name,
        scenario_name="Stochastic Failure Simulation",
        result=result,
        trace=trace,
        execution_time_ms=execution_time_ms,
        retry_count=retry_count,
        valid_business_result=valid_business_result,
        scheduled_backoff_seconds=sum(scheduled_delays)
    )


def execute_stochastic_sequence(
    config: AgentConfig,
    outcomes: list[str]
) -> AgentExecution:

    runner = StochasticScenarioRunner(outcomes)
    trace = ExecutionTrace()
    scheduled_delays = []

    start_time = perf_counter()

    result = run_with_retry(
        tool_call=runner.run,
        max_attempts=config.max_attempts,
        retry_strategy=config.retry_strategy,
        base_delay=config.base_delay,
        max_delay=config.max_delay,
        jitter=config.jitter,
        sleep_fn=lambda delay: scheduled_delays.append(delay),
        trace=trace
    )

    execution_time_ms = (perf_counter() - start_time) * 1000

    retry_count = trace.count_events("retry_scheduled")
    valid_business_result = validate_result(result)

    return AgentExecution(
        agent_name=config.name,
        scenario_name="Stochastic Sequence Simulation",
        result=result,
        trace=trace,
        execution_time_ms=execution_time_ms,
        retry_count=retry_count,
        valid_business_result=valid_business_result,
        scheduled_backoff_seconds=sum(scheduled_delays)
    )


def execute_scenario_with_reliability(
    config: AgentConfig,
    scenario: FailureScenario,
    reliability_config: ReliabilityConfig | None = None,
    fallback_tools: Sequence[Callable[[], ToolResult]] | None = None,
) -> AgentExecution:
    """Execute a scenario through the unified reliability engine.

    Existing AgentConfig retry settings are used by default.
    A ReliabilityConfig can override them and enable additional
    reliability mechanisms.
    """

    runner = ScenarioRunner(scenario)

    if reliability_config is None:
        reliability_config = ReliabilityConfig(
            max_attempts=config.max_attempts,
            retry_strategy=config.retry_strategy,
            base_delay=config.base_delay,
            max_delay=config.max_delay,
            jitter=config.jitter,
        )

    engine = ReliabilityEngine(
        config=reliability_config
    )

    execution = engine.execute(
        primary_tool=runner.run,
        fallback_tools=fallback_tools,
    )

    valid_business_result = validate_result(
        execution.result
    )

    return AgentExecution(
        agent_name=config.name,
        scenario_name=scenario.name,
        result=execution.result,
        trace=execution.trace,
        execution_time_ms=execution.execution_time_ms,
        retry_count=execution.retry_count,
        valid_business_result=valid_business_result,
        scheduled_backoff_seconds=(
            execution.scheduled_backoff_seconds
        ),
        fallback_count=execution.fallback_count,
        fallback_used=execution.fallback_used,
        circuit_breaker_enabled=(
            execution.circuit_breaker_enabled
        ),
    )
