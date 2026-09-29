"""store actionable interoperability exceptions and retry state

Revision ID: 20260930_exceptions
Revises: 20260930_audit
Create Date: 2026-09-30
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260930_exceptions"
down_revision: Union[str, Sequence[str], None] = "20260930_audit"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table("interoperability_exceptions") as batch:
            batch.alter_column("id", new_column_name="exception_id")
            batch.alter_column("system", new_column_name="source_system")
            batch.alter_column("category", new_column_name="type")
            batch.alter_column(
                "message",
                existing_type=sa.String(length=255),
                type_=sa.Text(),
                existing_nullable=False,
            )
            batch.alter_column(
                "status",
                existing_type=sa.Enum(
                    "OPEN", "IN_PROGRESS", "RESOLVED", "ESCALATED",
                    name="exceptionstatus",
                ),
                type_=sa.String(length=20),
                existing_nullable=False,
            )
            batch.add_column(
                sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0")
            )
            batch.create_index(
                "ix_interoperability_exceptions_status",
                ["status"],
                unique=False,
            )
    else:
        op.alter_column(
            "interoperability_exceptions", "id", new_column_name="exception_id"
        )
        op.alter_column(
            "interoperability_exceptions", "system", new_column_name="source_system"
        )
        op.alter_column(
            "interoperability_exceptions", "category", new_column_name="type"
        )
        op.alter_column(
            "interoperability_exceptions",
            "message",
            type_=sa.Text(),
            existing_type=sa.String(length=255),
        )
        op.alter_column(
            "interoperability_exceptions",
            "status",
            type_=sa.String(length=20),
            postgresql_using="status::text",
        )
        op.add_column(
            "interoperability_exceptions",
            sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        )
        op.create_index(
            "ix_interoperability_exceptions_status",
            "interoperability_exceptions",
            ["status"],
        )

    op.execute(
        "UPDATE interoperability_exceptions "
        "SET status = 'RETRYING' WHERE status = 'IN_PROGRESS'"
    )
    for previous, current in {
        "CONNECTOR_UNAVAILABLE": "SOURCE_SYSTEM_UNAVAILABLE",
        "SOURCE_UNAVAILABLE": "SOURCE_SYSTEM_UNAVAILABLE",
        "TIMEOUT_ERROR": "TIMEOUT",
        "SOURCE_RESPONSE": "INVALID_RESPONSE",
        "MALFORMED_RESPONSE": "MALFORMED_DATA",
        "MISSING_FIELDS": "MISSING_REQUIRED_FIELD",
        "SOURCE_VERIFICATION": "VALIDATION_FAILURE",
        "VALIDATION": "VALIDATION_FAILURE",
        "SOURCE_CONNECTOR": "CONNECTOR_FAILURE",
        "CONNECTOR_NOT_FOUND": "CONNECTOR_FAILURE",
        "NORMALIZATION": "MALFORMED_DATA",
    }.items():
        op.execute(
            "UPDATE interoperability_exceptions SET type = "
            f"'{current}' WHERE type = '{previous}'"
        )
    op.execute(
        "UPDATE interoperability_exceptions SET type = "
        "'CONSENT_EXPIRED' WHERE type = 'CONSENT' "
        "AND lower(message) LIKE '%expir%'"
    )
    op.execute(
        "UPDATE interoperability_exceptions SET type = "
        "'VALIDATION_FAILURE' WHERE type = 'CONSENT'"
    )


def downgrade() -> None:
    bind = op.get_bind()
    op.execute(
        "UPDATE interoperability_exceptions SET status = 'IN_PROGRESS' "
        "WHERE status = 'RETRYING'"
    )
    op.execute(
        "UPDATE interoperability_exceptions SET status = 'OPEN' "
        "WHERE status = 'IGNORED'"
    )
    op.drop_index(
        "ix_interoperability_exceptions_status",
        table_name="interoperability_exceptions",
    )
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table("interoperability_exceptions") as batch:
            batch.drop_column("retry_count")
            batch.alter_column("type", new_column_name="category")
            batch.alter_column("source_system", new_column_name="system")
            batch.alter_column("exception_id", new_column_name="id")
            batch.alter_column(
                "message",
                existing_type=sa.Text(),
                type_=sa.String(length=255),
                existing_nullable=False,
            )
            batch.alter_column(
                "status",
                existing_type=sa.String(length=20),
                type_=sa.Enum(
                    "OPEN", "IN_PROGRESS", "RESOLVED", "ESCALATED",
                    name="exceptionstatus",
                ),
                existing_nullable=False,
            )
    else:
        op.alter_column(
            "interoperability_exceptions",
            "status",
            type_=sa.Enum(
                "OPEN", "IN_PROGRESS", "RESOLVED", "ESCALATED",
                name="exceptionstatus",
            ),
            postgresql_using="status::exceptionstatus",
        )
        op.drop_column("interoperability_exceptions", "retry_count")
        op.alter_column(
            "interoperability_exceptions", "type", new_column_name="category"
        )
        op.alter_column(
            "interoperability_exceptions", "source_system", new_column_name="system"
        )
        op.alter_column(
            "interoperability_exceptions", "exception_id", new_column_name="id"
        )
        op.alter_column(
            "interoperability_exceptions",
            "message",
            type_=sa.String(length=255),
            existing_type=sa.Text(),
        )
