
import os

from fastapi import Depends
from sqlalchemy.orm import Session

from agentfault.database.session import get_db
from agentfault.services.execution_analytics_service import (
    ExecutionAnalyticsService,
)
from agentfault.services.execution_reliability_service import (
    ExecutionReliabilityService,
)


def get_execution_analytics_service(
    db: Session = Depends(get_db),
) -> ExecutionAnalyticsService:
    """Provide the database-backed execution analytics service."""

    tenant_id = os.getenv("DEFAULT_TENANT_ID")

    if not tenant_id:
        raise RuntimeError(
            "DEFAULT_TENANT_ID is not configured. Check your .env file."
        )

    return ExecutionAnalyticsService(
        session=db,
        tenant_id=tenant_id,
    )


def get_execution_reliability_service(
    db: Session = Depends(get_db),
) -> ExecutionReliabilityService:
    """Provide the database-backed execution reliability service."""

    tenant_id = os.getenv("DEFAULT_TENANT_ID")

    if not tenant_id:
        raise RuntimeError(
            "DEFAULT_TENANT_ID is not configured. Check your .env file."
        )

    return ExecutionReliabilityService(
        session=db,
        tenant_id=tenant_id,
    )
