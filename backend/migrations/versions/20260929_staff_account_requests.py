"""add pending staff account request state

Revision ID: 20260929_staff_requests
Revises: 20260929_healthchecks
Create Date: 2026-09-29
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260929_staff_requests"
down_revision: Union[str, Sequence[str], None] = "20260929_healthchecks"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "staff_request_pending",
            sa.Boolean(),
            server_default=sa.false(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "staff_request_pending")
