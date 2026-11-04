
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, replace

from agentfault.experiment import Experiment
from agentfault.experiment_executor import (
    ExperimentExecution,
    execute_experiment,
)
from agentfault.models import ToolResult
from agentfault.reliability_config import ReliabilityConfig
from agentfault.scenarios import FailureScenario


@dataclass
class StrategyComparison:
    """Stores the performance metrics of one reliability strategy."""

    strategy_name: str
    experiment_execution: ExperimentExecution
    success_rate: float
    average_execution_time_ms: float
    total_retries: int
    total_fallbacks: int
    passed_scenarios: int
    failed_scenarios: int


@dataclass
class ExperimentComparison:
    """Stores the comparison results of multiple strategies."""

    comparisons: list[StrategyComparison]
    best_strategy: str
    total_strategies: int


def compare_experiments(
    scenarios: Sequence[FailureScenario],
    strategies: Mapping[str, ReliabilityConfig],
    fallback_tools: Sequence[Callable[[], ToolResult]] | None = None,
) -> ExperimentComparison:
    """
    Execute the same scenarios under multiple reliability configurations
    and compare their performance.
    """

    if not scenarios:
        raise ValueError("At least one scenario is required")

    if not strategies:
        raise ValueError("At least one strategy is required")

    if any(not name.strip() for name in strategies):
        raise ValueError("Strategy names cannot be empty")

    comparisons = []

    for strategy_name, config in strategies.items():
        if not isinstance(config, ReliabilityConfig):
            raise TypeError(
                f"Strategy '{strategy_name}' must use ReliabilityConfig"
            )

        # Create fresh scenario objects for a fair comparison.
        fresh_scenarios = [
            FailureScenario(
                name=scenario.name,
                failure_sequence=list(scenario.failure_sequence),
                expected_status=scenario.expected_status,
            )
            for scenario in scenarios
        ]

        # Give each strategy its own configuration instance.
        independent_config = replace(config)

        experiment = Experiment(
            name=f"Comparison - {strategy_name}",
            scenarios=fresh_scenarios,
            reliability_config=independent_config,
        )

        # Pass fallback tools only when fallback is enabled.
        selected_fallback_tools = (
            fallback_tools if independent_config.enable_fallback else None
        )

        execution = execute_experiment(
            experiment,
            fallback_tools=selected_fallback_tools,
        )

        total_fallbacks = sum(
            result.fallback_count
            for result in execution.scenario_results
        )

        average_execution_time_ms = (
            execution.total_execution_time_ms
            / execution.total_scenarios
        )

        comparisons.append(
            StrategyComparison(
                strategy_name=strategy_name,
                experiment_execution=execution,
                success_rate=execution.success_rate,
                average_execution_time_ms=round(
                    average_execution_time_ms, 4
                ),
                total_retries=execution.total_retries,
                total_fallbacks=total_fallbacks,
                passed_scenarios=execution.passed_scenarios,
                failed_scenarios=execution.failed_scenarios,
            )
        )

    # Highest success rate wins.
    # Ties are resolved by lower average latency, then fewer retries.
    best_comparison = max(
        comparisons,
        key=lambda item: (
            item.success_rate,
            -item.average_execution_time_ms,
            -item.total_retries,
        ),
    )

    return ExperimentComparison(
        comparisons=comparisons,
        best_strategy=best_comparison.strategy_name,
        total_strategies=len(comparisons),
    )
