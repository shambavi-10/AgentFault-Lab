
from agentfault.agent_config import AgentConfig
from agentfault.benchmark import generate_benchmark_report
from agentfault.benchmark_runner import run_benchmark_suite
from agentfault.scenarios import FailureScenario


# Configure agents with different retry strategies.
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


# Define controlled failure scenarios.
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


# Number of times to repeat the complete scenario set.
REPETITIONS = 10


# Execute the repeated benchmark.
results = run_benchmark_suite(
    configs=agents,
    scenarios=scenarios,
    repetitions=REPETITIONS
)


# Display benchmark information.
print("\nAUTOMATED AGENT BENCHMARK")
print("=" * 60)

print(f"Number of agents: {len(agents)}")
print(f"Number of scenarios: {len(scenarios)}")
print(f"Repetitions per scenario: {REPETITIONS}")
print(f"Executions per agent: {len(scenarios) * REPETITIONS}")
print(f"Total executions: {len(agents) * len(scenarios) * REPETITIONS}")

print("=" * 60)

print(generate_benchmark_report(results))
