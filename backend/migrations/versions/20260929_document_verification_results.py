"""persist assisted document verification outcomes

Revision ID: 20260929_docverify
Revises: 20260930_notifications
Create Date: 2026-09-29
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260929_docverify"
down_revision: Union[str, Sequence[str], None] = "20260930_notifications"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "document_verification_results",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "document_id",
            sa.Integer(),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("file_sha256", sa.String(length=64), nullable=False),
        sa.Column("extracted_fields", sa.JSON(), nullable=False),
        sa.Column("extraction_text", sa.Text(), nullable=False),
        sa.Column("pipeline_steps", sa.JSON(), nullable=False),
        sa.Column("verification_status", sa.String(length=32), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("source_match_status", sa.String(length=24), nullable=False),
        sa.Column("source_match", sa.JSON(), nullable=False),
        sa.Column("duplicate_status", sa.String(length=16), nullable=False),
        sa.Column("tampering_indicators", sa.JSON(), nullable=False),
        sa.Column(
            "reviewed_by",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("review_note", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    for column in (
        "document_id",
        "file_sha256",
        "verification_status",
        "source_match_status",
        "duplicate_status",
        "reviewed_by",
        "created_at",
    ):
        op.create_index(
            f"ix_document_verification_results_{column}",
            "document_verification_results",
            [column],
            unique=column == "document_id",
        )


def downgrade() -> None:
    for column in (
        "document_id",
        "file_sha256",
        "verification_status",
        "source_match_status",
        "duplicate_status",
        "reviewed_by",
        "created_at",
    ):
        op.drop_index(
            f"ix_document_verification_results_{column}",
            table_name="document_verification_results",
        )
    op.drop_table("document_verification_results")
