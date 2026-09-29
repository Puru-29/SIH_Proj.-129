"""make audit entries self-contained and add structured metadata

Revision ID: 20260930_audit
Revises: 20260930_assignment
Create Date: 2026-09-30
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260930_audit"
down_revision: Union[str, Sequence[str], None] = "20260930_assignment"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    foreign_keys = sa.inspect(bind).get_foreign_keys("audit_logs")
    audit_references = [
        foreign_key
        for foreign_key in foreign_keys
        if foreign_key.get("constrained_columns")
        and foreign_key["constrained_columns"][0]
        in {"actor_id", "role_id", "department_id", "transaction_id"}
    ]
    if bind.dialect.name == "sqlite":
        naming = {
            "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s"
        }
        with op.batch_alter_table("audit_logs", naming_convention=naming) as batch:
            for foreign_key in audit_references:
                column = foreign_key["constrained_columns"][0]
                referred = foreign_key["referred_table"]
                batch.drop_constraint(
                    f"fk_audit_logs_{column}_{referred}", type_="foreignkey"
                )
    else:
        for foreign_key in audit_references:
            if foreign_key.get("name"):
                op.drop_constraint(
                    foreign_key["name"], "audit_logs", type_="foreignkey"
                )

    op.add_column(
        "audit_logs",
        sa.Column(
            "metadata",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'{}'"),
        ),
    )
    op.create_index("ix_audit_logs_result", "audit_logs", ["result"])
    op.create_index("ix_audit_logs_resource", "audit_logs", ["resource"])


def downgrade() -> None:
    op.drop_index("ix_audit_logs_resource", table_name="audit_logs")
    op.drop_index("ix_audit_logs_result", table_name="audit_logs")
    op.drop_column("audit_logs", "metadata")
    foreign_keys = (
        (
            "fk_audit_logs_actor_id_users",
            "users",
            ["actor_id"],
            ["id"],
        ),
        (
            "fk_audit_logs_role_id_roles",
            "roles",
            ["role_id"],
            ["id"],
        ),
        (
            "fk_audit_logs_department_id_departments",
            "departments",
            ["department_id"],
            ["id"],
        ),
        (
            "fk_audit_logs_transaction_id_interoperability_transactions",
            "interoperability_transactions",
            ["transaction_id"],
            ["public_id"],
        ),
    )
    if op.get_bind().dialect.name == "sqlite":
        with op.batch_alter_table("audit_logs") as batch:
            for name, table, columns, referred_columns in foreign_keys:
                batch.create_foreign_key(
                    name,
                    table,
                    columns,
                    referred_columns,
                    ondelete="SET NULL",
                )
    else:
        for name, table, columns, referred_columns in foreign_keys:
            op.create_foreign_key(
                name,
                "audit_logs",
                table,
                columns,
                referred_columns,
                ondelete="SET NULL",
            )
