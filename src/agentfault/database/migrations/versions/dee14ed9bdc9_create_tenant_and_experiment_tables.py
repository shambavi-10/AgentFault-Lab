
"""create tenant and experiment tables

Revision ID: dee14ed9bdc9
Revises:
Create Date: 2026-11-06 09:48:40.305559

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "dee14ed9bdc9"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create tenant, experiment, and experiment scenario tables."""

    op.create_table(
        "tenants",
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("tenant_id"),
    )

    op.create_table(
        "experiments",
        sa.Column("experiment_id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column(
            "reliability_config",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('pending', 'running', 'completed', 'failed')",
            name="ck_experiments_status",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.tenant_id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("experiment_id"),
    )

    op.create_index(
        "ix_experiments_status",
        "experiments",
        ["status"],
        unique=False,
    )

    op.create_index(
        "ix_experiments_tenant_id",
        "experiments",
        ["tenant_id"],
        unique=False,
    )

    op.create_table(
        "experiment_scenarios",
        sa.Column("scenario_id", sa.UUID(), nullable=False),
        sa.Column("experiment_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column(
            "failure_sequence",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("expected_status", sa.String(length=20), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.CheckConstraint(
            "expected_status IN ('success', 'failure')",
            name="ck_experiment_scenarios_expected_status",
        ),
        sa.ForeignKeyConstraint(
            ["experiment_id"],
            ["experiments.experiment_id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("scenario_id"),
    )

    op.create_index(
        "ix_experiment_scenarios_experiment_id",
        "experiment_scenarios",
        ["experiment_id"],
        unique=False,
    )


def downgrade() -> None:
    """Remove experiment, scenario, and tenant tables."""

    op.drop_index(
        "ix_experiment_scenarios_experiment_id",
        table_name="experiment_scenarios",
    )
    op.drop_table("experiment_scenarios")

    op.drop_index(
        "ix_experiments_tenant_id",
        table_name="experiments",
    )
    op.drop_index(
        "ix_experiments_status",
        table_name="experiments",
    )
    op.drop_table("experiments")

    op.drop_table("tenants")
