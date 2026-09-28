"""add managed roles and revocable authentication sessions

Revision ID: 44a21c4b9d20
Revises: c658ed35c11a
Create Date: 2026-09-28
"""
from typing import Sequence, Union
import uuid

from alembic import op
import sqlalchemy as sa


revision: str = "44a21c4b9d20"
down_revision: Union[str, Sequence[str], None] = "c658ed35c11a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

DEPARTMENT_OFFICER_ROLE_ID = uuid.UUID("44a21c4b-9d20-4c00-8000-000000000001")
INTEROPERABILITY_ADMIN_ROLE_ID = uuid.UUID("44a21c4b-9d20-4c00-8000-000000000002")
SYSTEM_ADMIN_ROLE_ID = uuid.UUID("44a21c4b-9d20-4c00-8000-000000000003")


def upgrade() -> None:
    op.create_table(
        "auth_sessions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("refresh_token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_auth_sessions_user_id", "auth_sessions", ["user_id"])
    op.create_index("ix_auth_sessions_expires_at", "auth_sessions", ["expires_at"])

    role_table = sa.table(
        "roles",
        sa.column("id", sa.Uuid()),
        sa.column("key", sa.String()),
        sa.column("name", sa.String()),
        sa.column("description", sa.String()),
    )
    op.bulk_insert(
        role_table,
        [
            {
                "id": DEPARTMENT_OFFICER_ROLE_ID,
                "key": "department_officer",
                "name": "Department Officer",
                "description": "Processes resources assigned to one government department.",
            },
            {
                "id": INTEROPERABILITY_ADMIN_ROLE_ID,
                "key": "interoperability_admin",
                "name": "Interoperability Administrator",
                "description": "Manages interoperability connectors, mappings, workflows and transactions.",
            },
            {
                "id": SYSTEM_ADMIN_ROLE_ID,
                "key": "system_admin",
                "name": "System Administrator",
                "description": "Manages users, roles, departments and system configuration.",
            },
        ],
    )
    op.execute(
        sa.text(
            "UPDATE users SET role_id = :role_id WHERE role = 'OFFICER'"
        ).bindparams(
            sa.bindparam(
                "role_id", type_=sa.Uuid(), value=DEPARTMENT_OFFICER_ROLE_ID
            )
        )
    )
    op.execute(
        sa.text(
            "UPDATE users SET role_id = :role_id "
            "WHERE role IN ('DEVELOPER', 'OPERATOR')"
        ).bindparams(
            sa.bindparam(
                "role_id", type_=sa.Uuid(), value=INTEROPERABILITY_ADMIN_ROLE_ID
            )
        )
    )
    op.execute(
        sa.text(
            "UPDATE users SET role_id = :role_id WHERE role = 'ADMIN'"
        ).bindparams(
            sa.bindparam("role_id", type_=sa.Uuid(), value=SYSTEM_ADMIN_ROLE_ID)
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text("UPDATE users SET role_id = :role_id WHERE role = 'OFFICER'").bindparams(
            sa.bindparam(
                "role_id",
                type_=sa.Uuid(),
                value=uuid.UUID("27d7f037-208e-4e9f-8df9-28c73cc44002"),
            )
        )
    )
    op.execute(
        sa.text(
            "UPDATE users SET role_id = :role_id "
            "WHERE role IN ('DEVELOPER', 'OPERATOR')"
        ).bindparams(
            sa.bindparam(
                "role_id",
                type_=sa.Uuid(),
                value=uuid.UUID("27d7f037-208e-4e9f-8df9-28c73cc44004"),
            )
        )
    )
    op.execute(
        sa.text("UPDATE users SET role_id = :role_id WHERE role = 'ADMIN'").bindparams(
            sa.bindparam(
                "role_id",
                type_=sa.Uuid(),
                value=uuid.UUID("27d7f037-208e-4e9f-8df9-28c73cc44003"),
            )
        )
    )
    op.execute("DELETE FROM roles WHERE key IN ('department_officer', 'interoperability_admin', 'system_admin')")
    op.drop_index("ix_auth_sessions_expires_at", table_name="auth_sessions")
    op.drop_index("ix_auth_sessions_user_id", table_name="auth_sessions")
    op.drop_table("auth_sessions")
