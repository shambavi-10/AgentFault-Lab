from api.schemas.experiment import ExperimentExecutionResponse


_execution_results: dict[
    str, list[ExperimentExecutionResponse]
] = {}


def get_execution_results_store() -> dict[
    str, list[ExperimentExecutionResponse]
]:
    """Return the execution history store."""

    return _execution_results