from dataclasses import dataclass
from dataclasses import asdict

from agentfault.benchmark_analytics import BenchmarkAnalytics
from agentfault.experiment_executor import ExperimentExecution


@dataclass
class ScenarioReport:
    """Stores report information for an individual scenario."""

    scenario_name: str
    expected_status: str
    actual_status: str
    passed: bool
    execution_time_ms: float
    retry_count: int
    fallback_count: int


@dataclass
class BenchmarkReport:
    """Stores a complete benchmark report."""

    experiment_id: str
    experiment_name: str
    experiment_status: str

    total_scenarios: int
    passed_scenarios: int
    failed_scenarios: int

    success_rate: float
    failure_rate: float

    average_latency_ms: float
    minimum_latency_ms: float
    maximum_latency_ms: float

    p50_latency_ms: float
    p90_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float

    total_retries: int
    average_retries: float

    total_fallbacks: int
    fallback_usage_rate: float

    scenario_reports: list[ScenarioReport]

def generate_benchmark_report(
    execution: ExperimentExecution,
    analytics: BenchmarkAnalytics,
) -> BenchmarkReport:
    """Generate a complete benchmark report."""

    if execution.experiment_id != analytics.experiment_id:
        raise ValueError(
            "Execution and analytics experiment IDs do not match"
        )

    if execution.experiment_name != analytics.experiment_name:
        raise ValueError(
            "Execution and analytics experiment names do not match"
        )

    if len(execution.scenario_results) != execution.total_scenarios:
        raise ValueError(
            "Scenario count does not match execution results"
        )

    scenario_reports = []

    for result in execution.scenario_results:
        scenario_report = ScenarioReport(
            scenario_name=result.scenario_name,
            expected_status=result.expected_status,
            actual_status=result.result.status,
            passed=result.passed,
            execution_time_ms=round(result.execution_time_ms, 4),
            retry_count=result.retry_count,
            fallback_count=result.fallback_count,
        )

        scenario_reports.append(scenario_report)

    return BenchmarkReport(
        experiment_id=analytics.experiment_id,
        experiment_name=analytics.experiment_name,
        experiment_status=execution.status,

        total_scenarios=analytics.total_scenarios,
        passed_scenarios=analytics.passed_scenarios,
        failed_scenarios=analytics.failed_scenarios,

        success_rate=analytics.success_rate,
        failure_rate=analytics.failure_rate,

        average_latency_ms=analytics.average_latency_ms,
        minimum_latency_ms=analytics.minimum_latency_ms,
        maximum_latency_ms=analytics.maximum_latency_ms,

        p50_latency_ms=analytics.p50_latency_ms,
        p90_latency_ms=analytics.p90_latency_ms,
        p95_latency_ms=analytics.p95_latency_ms,
        p99_latency_ms=analytics.p99_latency_ms,

        total_retries=analytics.total_retries,
        average_retries=analytics.average_retries,

        total_fallbacks=analytics.total_fallbacks,
        fallback_usage_rate=analytics.fallback_usage_rate,

        scenario_reports=scenario_reports,
    )

def format_benchmark_report(report: BenchmarkReport) -> str:
    """Format a benchmark report as a human-readable text summary."""

    lines = [
        "=" * 60,
        "AGENTFAULT LAB - BENCHMARK REPORT",
        "=" * 60,
        "",
        "EXPERIMENT DETAILS",
        "-" * 60,
        f"Experiment Name: {report.experiment_name}",
        f"Experiment ID:   {report.experiment_id}",
        f"Status:          {report.experiment_status}",
        "",
        "OVERALL RESULTS",
        "-" * 60,
        f"Total Scenarios:  {report.total_scenarios}",
        f"Passed Scenarios: {report.passed_scenarios}",
        f"Failed Scenarios: {report.failed_scenarios}",
        f"Success Rate:     {report.success_rate * 100:.2f}%",
        f"Failure Rate:     {report.failure_rate * 100:.2f}%",
        "",
        "PERFORMANCE ANALYTICS",
        "-" * 60,
        f"Average Latency: {report.average_latency_ms:.4f} ms",
        f"Minimum Latency: {report.minimum_latency_ms:.4f} ms",
        f"Maximum Latency: {report.maximum_latency_ms:.4f} ms",
        f"P50 Latency:     {report.p50_latency_ms:.4f} ms",
        f"P90 Latency:     {report.p90_latency_ms:.4f} ms",
        f"P95 Latency:     {report.p95_latency_ms:.4f} ms",
        f"P99 Latency:     {report.p99_latency_ms:.4f} ms",
        "",
        "RELIABILITY ANALYTICS",
        "-" * 60,
        f"Total Retries:        {report.total_retries}",
        f"Average Retries:      {report.average_retries:.4f}",
        f"Total Fallbacks:      {report.total_fallbacks}",
        f"Fallback Usage Rate:  {report.fallback_usage_rate * 100:.2f}%",
        "",
        "SCENARIO DETAILS",
        "-" * 60,
    ]

    for scenario in report.scenario_reports:
        status = "PASSED" if scenario.passed else "FAILED"

        lines.extend([
            f"Scenario: {scenario.scenario_name}",
            f"  Expected Status: {scenario.expected_status}",
            f"  Actual Status:   {scenario.actual_status}",
            f"  Result:          {status}",
            f"  Latency:         {scenario.execution_time_ms:.4f} ms",
            f"  Retries:         {scenario.retry_count}",
            f"  Fallbacks:       {scenario.fallback_count}",
            "",
        ])

    lines.append("=" * 60)
    lines.append("END OF BENCHMARK REPORT")
    lines.append("=" * 60)

    return "\n".join(lines)

def export_benchmark_report_json(
    report: BenchmarkReport,
) -> dict:
    """Convert a benchmark report into a JSON-compatible dictionary."""

    return asdict(report)