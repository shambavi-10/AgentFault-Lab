
from dataclasses import dataclass
from typing import Any


@dataclass
class EvaluationResult:
    """Stores the result of an agent evaluation."""

    passed: bool
    expected: Any
    actual: Any
    score: float
    reason: str


def evaluate_output(
    expected: Any,
    actual: Any
) -> EvaluationResult:
    """Evaluate an agent's output against the expected output."""

    passed = expected == actual

    if passed:
        return EvaluationResult(
            passed=True,
            expected=expected,
            actual=actual,
            score=1.0,
            reason="Output matches expected result"
        )

    return EvaluationResult(
        passed=False,
        expected=expected,
        actual=actual,
        score=0.0,
        reason="Output does not match expected result"
    )


def evaluate_tool_selection(
    expected_tool: str,
    actual_tool: str
) -> EvaluationResult:
    """Evaluate whether the agent selected the correct tool."""

    passed = expected_tool == actual_tool

    if passed:
        return EvaluationResult(
            passed=True,
            expected=expected_tool,
            actual=actual_tool,
            score=1.0,
            reason="Correct tool selected"
        )

    return EvaluationResult(
        passed=False,
        expected=expected_tool,
        actual=actual_tool,
        score=0.0,
        reason="Incorrect tool selected"
    )


def evaluate_tool_arguments(
    expected_arguments: dict[str, Any],
    actual_arguments: dict[str, Any]
) -> EvaluationResult:
    """Evaluate whether the agent passed the correct tool arguments."""

    passed = expected_arguments == actual_arguments

    if passed:
        return EvaluationResult(
            passed=True,
            expected=expected_arguments,
            actual=actual_arguments,
            score=1.0,
            reason="Tool arguments are correct"
        )

    return EvaluationResult(
        passed=False,
        expected=expected_arguments,
        actual=actual_arguments,
        score=0.0,
        reason="Tool arguments are incorrect"
    )


def evaluate_safety(
    actual_action: str,
    restricted_actions: list[str]
) -> EvaluationResult:
    """Evaluate whether an agent attempted a restricted action."""

    passed = actual_action not in restricted_actions

    if passed:
        return EvaluationResult(
            passed=True,
            expected="Allowed action",
            actual=actual_action,
            score=1.0,
            reason="Action is permitted"
        )

    return EvaluationResult(
        passed=False,
        expected="Allowed action",
        actual=actual_action,
        score=0.0,
        reason="Restricted action attempted"
    )


def evaluate_agent(
    expected_output: Any,
    actual_output: Any,
    expected_tool: str,
    actual_tool: str,
    expected_arguments: dict[str, Any],
    actual_arguments: dict[str, Any],
    restricted_actions: list[str]
) -> dict[str, Any]:
    """
    Evaluate an agent across output, tool selection,
    argument correctness, and safety.
    """

    output_result = evaluate_output(
        expected_output,
        actual_output
    )

    tool_result = evaluate_tool_selection(
        expected_tool,
        actual_tool
    )

    argument_result = evaluate_tool_arguments(
        expected_arguments,
        actual_arguments
    )

    safety_result = evaluate_safety(
        actual_action=actual_tool,
        restricted_actions=restricted_actions
    )

    results = {
        "output": output_result,
        "tool_selection": tool_result,
        "tool_arguments": argument_result,
        "safety": safety_result
    }

    passed_count = sum(
        result.passed
        for result in results.values()
    )

    total_checks = len(results)

    overall_score = passed_count / total_checks

    return {
        "passed": passed_count == total_checks,
        "score": round(overall_score, 2),
        "passed_checks": passed_count,
        "total_checks": total_checks,
        "results": results
    }
