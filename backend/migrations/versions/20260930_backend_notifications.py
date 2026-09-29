"""add notification event types for lifecycle delivery

Revision ID: 20260930_notifications
Revises: 20260930_exceptions
Create Date: 2026-09-30
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260930_notifications"
down_revision: Union[str, Sequence[str], None] = "20260930_exceptions"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "notifications",
        sa.Column(
            "event_type",
            sa.String(length=40),
            nullable=False,
            server_default="APPLICATION_UPDATED",
        ),
    )
    op.create_index(
        "ix_notifications_event_type", "notifications", ["event_type"], unique=False
    )
    op.execute(
        "UPDATE notifications SET event_type = CASE notification_type "
        "WHEN 'Consent' THEN 'CONSENT_REQUIRED' "
        "WHEN 'Application' THEN 'APPLICATION_UPDATED' "
        "ELSE 'APPLICATION_UPDATED' END"
    )


def downgrade() -> None:
    op.drop_index("ix_notifications_event_type", table_name="notifications")
    op.drop_column("notifications", "event_type")
