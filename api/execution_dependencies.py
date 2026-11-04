from api.schemas.experiment import ExperimentExecutionResponse


_execution_results: dict[str, ExperimentExecutionResponse] = {}


def get_execution_results_store() -> dict[str, ExperimentExecutionResponse]:
    """Return the in-memory store for the latest experiment results."""

    return _execution_results