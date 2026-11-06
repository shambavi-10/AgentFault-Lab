
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from agentfault.database.models.tenant import TenantModel


class TenantRepository:
    """Handles tenant creation and retrieval."""

    def create(
        self,
        session: Session,
        name: str,
    ) -> TenantModel:
        """Create and persist a new tenant."""

        if not isinstance(name, str) or not name.strip():
            raise ValueError("Tenant name cannot be empty")

        tenant = TenantModel(name=name.strip())

        try:
            session.add(tenant)
            session.commit()
            session.refresh(tenant)
            return tenant
        except Exception:
            session.rollback()
            raise

    def get_by_id(
        self,
        session: Session,
        tenant_id: str | uuid.UUID,
    ) -> TenantModel | None:
        """Retrieve a tenant using its UUID."""

        try:
            tenant_uuid = (
                tenant_id
                if isinstance(tenant_id, uuid.UUID)
                else uuid.UUID(tenant_id)
            )
        except (ValueError, TypeError, AttributeError) as exc:
            raise ValueError(f"Invalid tenant UUID: {tenant_id}") from exc

        return session.scalar(
            select(TenantModel).where(
                TenantModel.tenant_id == tenant_uuid
            )
        )

    def list_all(
        self,
        session: Session,
    ) -> list[TenantModel]:
        """Return all registered tenants."""

        return list(
            session.scalars(
                select(TenantModel).order_by(TenantModel.created_at.desc())
            ).all()
        )
