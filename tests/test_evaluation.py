
from agentfault.evaluation import (
    evaluate_output,
    evaluate_tool_selection,
    evaluate_tool_arguments,
    evaluate_agent,
    evaluate_safety
)


# --------------------------------------------------
# OUTPUT EVALUATION TESTS
# --------------------------------------------------

def test_evaluate_correct_output():
    result = evaluate_output(
        expected=150000,
        actual=150000
    )

    assert result.passed is True
    assert result.score == 1.0
    assert result.reason == "Output matches expected result"


def test_evaluate_incorrect_output():
    result = evaluate_output(
        expected=150000,
        actual=140000
    )

    assert result.passed is False
    assert result.score == 0.0
    assert result.reason == "Output does not match expected result"


def test_evaluate_string_output():
    result = evaluate_output(
        expected="success",
        actual="success"
    )

    assert result.passed is True


def test_evaluate_dictionary_output():
    result = evaluate_output(
        expected={"status": "success"},
        actual={"status": "success"}
    )

    assert result.passed is True


def test_evaluate_different_data_types():
    result = evaluate_output(
        expected=100,
        actual="100"
    )

    assert result.passed is False


# --------------------------------------------------
# TOOL SELECTION EVALUATION TESTS
# --------------------------------------------------

def test_correct_tool_selection():
    result = evaluate_tool_selection(
        expected_tool="calculator",
        actual_tool="calculator"
    )

    assert result.passed is True
    assert result.score == 1.0
    assert result.reason == "Correct tool selected"


def test_incorrect_tool_selection():
    result = evaluate_tool_selection(
        expected_tool="calculator",
        actual_tool="email_sender"
    )

    assert result.passed is False
    assert result.score == 0.0
    assert result.reason == "Incorrect tool selected"


# --------------------------------------------------
# TOOL ARGUMENT EVALUATION TESTS
# --------------------------------------------------

def test_correct_tool_arguments():
    result = evaluate_tool_arguments(
        expected_arguments={
            "quantity": 3,
            "price": 50000
        },
        actual_arguments={
            "quantity": 3,
            "price": 50000
        }
    )

    assert result.passed is True
    assert result.score == 1.0
    assert result.reason == "Tool arguments are correct"


def test_incorrect_tool_arguments():
    result = evaluate_tool_arguments(
        expected_arguments={
            "quantity": 3,
            "price": 50000
        },
        actual_arguments={
            "quantity": 3,
            "price": 40000
        }
    )

    assert result.passed is False
    assert result.score == 0.0


def test_tool_arguments_with_different_key_order():
    result = evaluate_tool_arguments(
        expected_arguments={
            "quantity": 3,
            "price": 50000
        },
        actual_arguments={
            "price": 50000,
            "quantity": 3
        }
    )

    assert result.passed is True


# --------------------------------------------------
# UNIFIED AGENT EVALUATION TESTS
# --------------------------------------------------

def test_evaluate_agent_all_checks_pass():
    result = evaluate_agent(
        expected_output=150000,
        actual_output=150000,
        expected_tool="calculator",
        actual_tool="calculator",
        expected_arguments={"quantity": 3, "price": 50000},
        actual_arguments={"quantity": 3, "price": 50000},
        restricted_actions=["file_deleter", "payment_processor"]
    )

    assert result["passed"] is True
    assert result["score"] == 1.0
    assert result["passed_checks"] == 4
    assert result["total_checks"] == 4


def test_evaluate_agent_partial_success():
    result = evaluate_agent(
        expected_output=150000,
        actual_output=140000,
        expected_tool="calculator",
        actual_tool="calculator",
        expected_arguments={"quantity": 3, "price": 50000},
        actual_arguments={"quantity": 3, "price": 50000},
        restricted_actions=["file_deleter", "payment_processor"]
    )

    assert result["passed"] is False
    assert result["score"] == 0.75
    assert result["passed_checks"] == 3
    assert result["total_checks"] == 4


def test_evaluate_agent_all_checks_fail():
    result = evaluate_agent(
        expected_output=150000,
        actual_output=100000,
        expected_tool="calculator",
        actual_tool="email_sender",
        expected_arguments={"quantity": 3, "price": 50000},
        actual_arguments={"quantity": 2, "price": 50000},
        restricted_actions=["file_deleter", "payment_processor"]
    )

    assert result["passed"] is False
    assert result["score"] == 0.25
    assert result["passed_checks"] == 1
    assert result["total_checks"] == 4


# --------------------------------------------------
# SAFETY EVALUATION TESTS
# --------------------------------------------------

def test_allowed_action_passes_safety():
    result = evaluate_safety(
        actual_action="calculator",
        restricted_actions=["file_deleter", "payment_processor"]
    )

    assert result.passed is True
    assert result.score == 1.0


def test_restricted_action_fails_safety():
    result = evaluate_safety(
        actual_action="file_deleter",
        restricted_actions=["file_deleter", "payment_processor"]
    )

    assert result.passed is False
    assert result.score == 0.0
    assert result.reason == "Restricted action attempted"


def test_empty_restricted_actions():
    result = evaluate_safety(
        actual_action="calculator",
        restricted_actions=[]
    )

    assert result.passed is True


# --------------------------------------------------
# SAFETY INTEGRATION TEST
# --------------------------------------------------

def test_evaluate_agent_restricted_tool():
    result = evaluate_agent(
        expected_output=150000,
        actual_output=150000,
        expected_tool="calculator",
        actual_tool="file_deleter",
        expected_arguments={"quantity": 3, "price": 50000},
        actual_arguments={"quantity": 3, "price": 50000},
        restricted_actions=["file_deleter", "payment_processor"]
    )

    assert result["passed"] is False
    assert result["score"] == 0.50
    assert result["passed_checks"] == 2
    assert result["total_checks"] == 4

    assert result["results"]["safety"].passed is False
    assert result["results"]["safety"].reason == "Restricted action attempted"

