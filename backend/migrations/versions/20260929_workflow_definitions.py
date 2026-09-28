"""add configurable workflow definitions and step metadata

Revision ID: 20260929_workflows
Revises: 44a21c4b9d20
Create Date: 2026-09-29
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260929_workflows"
down_revision: Union[str, Sequence[str], None] = "44a21c4b9d20"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "workflows",
        sa.Column("required_records", sa.JSON(), nullable=False, server_default="[]"),
    )
    op.add_column(
        "workflows",
        sa.Column("required_consents", sa.JSON(), nullable=False, server_default="[]"),
    )
    op.add_column(
        "workflows",
        sa.Column("departments", sa.JSON(), nullable=False, server_default="[]"),
    )
    op.add_column(
        "workflows",
        sa.Column("transitions", sa.JSON(), nullable=False, server_default="{}"),
    )
    op.add_column("workflows", sa.Column("sla_hours", sa.Integer(), nullable=True))
    op.add_column(
        "workflows",
        sa.Column("sla_due_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "workflow_steps",
        sa.Column("department", sa.String(length=160), nullable=True),
    )
    op.add_column(
        "workflow_steps",
        sa.Column(
            "required",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
    )
    op.add_column(
        "workflow_steps",
        sa.Column("action", sa.JSON(), nullable=False, server_default="{}"),
    )
    op.add_column(
        "workflow_steps",
        sa.Column("next_steps", sa.JSON(), nullable=False, server_default="[]"),
    )


def downgrade() -> None:
    op.drop_column("workflow_steps", "next_steps")
    op.drop_column("workflow_steps", "action")
    op.drop_column("workflow_steps", "required")
    op.drop_column("workflow_steps", "department")
    op.drop_column("workflows", "sla_due_at")
    op.drop_column("workflows", "sla_hours")
    op.drop_column("workflows", "transitions")
    op.drop_column("workflows", "departments")
    op.drop_column("workflows", "required_consents")
    op.drop_column("workflows", "required_records")
