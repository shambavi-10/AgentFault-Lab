
from dataclasses import dataclass
from time import perf_counter

from agentfault.agent_config import AgentConfig
from agentfault.faults import validate_result
from agentfault.models import ToolResult
from agentfault.retry import run_with_retry
from agentfault.scenario_runner import ScenarioRunner
from agentfault.scenarios import FailureScenario
from agentfault.tracing import ExecutionTrace


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
