from datetime import datetime
import uuid

from sqlalchemy import DateTime, JSON, String, Text, Uuid, event, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.model_base import PublicUUIDMixin


class AuditLog(PublicUUIDMixin, Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    action: Mapped[str] = mapped_column(String(120), index=True)
    entity_type: Mapped[str] = mapped_column(String(80))
    entity_id: Mapped[str] = mapped_column(String(80), index=True)
    details: Mapped[str | None] = mapped_column(Text, nullable=True)
    actor_id: Mapped[int | None] = mapped_column(nullable=True, index=True)
    role_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), nullable=True, index=True
    )
    actor_role: Mapped[str | None] = mapped_column(String(32), nullable=True)
    department_id: Mapped[int | None] = mapped_column(nullable=True, index=True)
    resource: Mapped[str] = mapped_column(
        String(80), nullable=False, default="unknown", index=True
    )
    resource_id: Mapped[str] = mapped_column(String(80), nullable=False, default="")
    result: Mapped[str] = mapped_column(
        String(32), nullable=False, default="success", index=True
    )
    event_metadata: Mapped[dict] = mapped_column(
        "metadata",
        JSON,
        nullable=False,
        default=dict,
        server_default=text("'{}'"),
    )
    transaction_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), nullable=True, index=True
    )
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )


@event.listens_for(AuditLog, "before_update")
@event.listens_for(AuditLog, "before_delete")
def _prevent_audit_mutation(*_args: object) -> None:
    raise ValueError("Audit records are append-only and cannot be changed or deleted.")
