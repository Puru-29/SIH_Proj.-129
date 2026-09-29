"""persist connector health probe results

Revision ID: 20260929_healthchecks
Revises: 20260929_docverify
Create Date: 2026-09-29
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260929_healthchecks"
down_revision: Union[str, Sequence[str], None] = "20260929_docverify"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "integration_health_checks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "system_id",
            sa.Integer(),
            sa.ForeignKey("connected_systems.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("response_time_ms", sa.Float(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "checked_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_integration_health_checks_system_id",
        "integration_health_checks",
        ["system_id"],
    )
    op.create_index(
        "ix_integration_health_checks_checked_at",
        "integration_health_checks",
        ["checked_at"],
    )
    op.create_index(
        "ix_integration_health_system_checked",
        "integration_health_checks",
        ["system_id", "checked_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_integration_health_system_checked",
        table_name="integration_health_checks",
    )
    op.drop_index(
        "ix_integration_health_checks_checked_at",
        table_name="integration_health_checks",
    )
    op.drop_index(
        "ix_integration_health_checks_system_id",
        table_name="integration_health_checks",
    )
    op.drop_table("integration_health_checks")
