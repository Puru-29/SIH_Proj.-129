"""add assigned officer to service applications

Revision ID: 20260930_assignment
Revises: 20260929_workflows
Create Date: 2026-09-30
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260930_assignment"
down_revision: Union[str, Sequence[str], None] = "20260929_workflows"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("service_applications") as batch_op:
        batch_op.add_column(sa.Column("assigned_officer_id", sa.Integer(), nullable=True))
        batch_op.create_index(
            "ix_service_applications_assigned_officer_id",
            ["assigned_officer_id"],
        )
        batch_op.create_foreign_key(
            "fk_service_applications_assigned_officer_id_users",
            "users",
            ["assigned_officer_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    with op.batch_alter_table("service_applications") as batch_op:
        batch_op.drop_constraint(
            "fk_service_applications_assigned_officer_id_users",
            type_="foreignkey",
        )
        batch_op.drop_index("ix_service_applications_assigned_officer_id")
        batch_op.drop_column("assigned_officer_id")
