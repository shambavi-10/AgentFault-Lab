from agentfault.agent_config import AgentConfig
from agentfault.benchmark import generate_benchmark_report
from agentfault.benchmark_runner import run_benchmark_suite
from agentfault.scenarios import FailureScenario


agents = [
    AgentConfig(
        name="Agent A - No Retry",
        max_attempts=1,
        retry_strategy="none"
    ),
    AgentConfig(
        name="Agent B - Fixed Retry",
        max_attempts=3,
        retry_strategy="fixed",
        base_delay=0.2
    ),
   
    AgentConfig(
        name="Agent C - Exponential Retry",
        max_attempts=3,
        retry_strategy="exponential",
        base_delay=0.2,
        jitter=False
    )
]


scenarios = [
    FailureScenario(
        name="Timeout Recovery",
        failure_sequence=["timeout", "none"]
    ),
    FailureScenario(
        name="Rate Limit Recovery",
        failure_sequence=["rate_limit", "none"]
    ),
    FailureScenario(
        name="Multiple Failures",
        failure_sequence=["timeout", "rate_limit", "none"]
    ),
    FailureScenario(
        name="Permanent Permission Failure",
        failure_sequence=["permission_denied"],
        expected_status="failure"
    ),
    FailureScenario(
        name="Normal Execution",
        failure_sequence=["none"]
    )
]


results = run_benchmark_suite(
    configs=agents,
    scenarios=scenarios
)

print("\nAUTOMATED AGENT BENCHMARK")
print("=" * 50)

print(generate_benchmark_report(results))