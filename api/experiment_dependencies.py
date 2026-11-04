
from functools import lru_cache

from agentfault.experiment_manager import ExperimentManager


@lru_cache
def get_experiment_manager() -> ExperimentManager:
    """Create and reuse the experiment manager."""

    return ExperimentManager()
