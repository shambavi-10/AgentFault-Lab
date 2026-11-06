
import os

from fastapi import Depends
from sqlalchemy.orm import Session

from agentfault.database.session import get_db
from agentfault.experiment_manager import ExperimentManager
from agentfault.services.experiment_service import ExperimentService


def get_experiment_manager(
    db: Session = Depends(get_db),
) -> ExperimentManager | ExperimentService:
    """Provide the database-backed experiment service."""

    tenant_id = os.getenv("DEFAULT_TENANT_ID")

    if not tenant_id:
        raise RuntimeError(
            "DEFAULT_TENANT_ID is not configured. Check your .env file."
        )

    return ExperimentService(
        session=db,
        tenant_id=tenant_id,
    )
