"""create citizen grievances

Revision ID: 20260929_grievances
Revises: 20260929_staff_requests
Create Date: 2026-09-29
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260929_grievances"
down_revision: Union[str, Sequence[str], None] = "20260929_staff_requests"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "grievances",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("citizen_id", sa.Integer(), nullable=False),
        sa.Column("category", sa.String(length=120), nullable=False),
        sa.Column("related_application", sa.String(length=80), nullable=True),
        sa.Column("department", sa.String(length=160), nullable=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("priority", sa.String(length=24), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["citizen_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_grievances_citizen_id", "grievances", ["citizen_id"])


def downgrade() -> None:
    op.drop_index("ix_grievances_citizen_id", table_name="grievances")
    op.drop_table("grievances")
