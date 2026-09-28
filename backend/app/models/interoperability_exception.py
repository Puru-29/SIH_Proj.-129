from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import DateTime, Enum, ForeignKey, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.model_base import PublicUUIDMixin, TimestampMixin


class ExceptionStatus(str, PyEnum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    ESCALATED = "escalated"


class InteroperabilityException(PublicUUIDMixin, TimestampMixin, Base):
    __tablename__ = "interoperability_exceptions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    application_id: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    service_application_id: Mapped[int | None] = mapped_column(
        ForeignKey("service_applications.id", ondelete="SET NULL"), nullable=True, index=True
    )
    transaction_id: Mapped[int | None] = mapped_column(
        ForeignKey("interoperability_transactions.id", ondelete="SET NULL"), nullable=True, index=True
    )
    connected_system_id: Mapped[int | None] = mapped_column(
        ForeignKey("connected_systems.id", ondelete="SET NULL"), nullable=True, index=True
    )
    system: Mapped[str] = mapped_column(String(120), index=True)
    category: Mapped[str] = mapped_column(String(80), index=True)
    message: Mapped[str] = mapped_column(String(255))
    severity: Mapped[str] = mapped_column(String(40), default="medium")
    status: Mapped[ExceptionStatus] = mapped_column(Enum(ExceptionStatus), default=ExceptionStatus.OPEN)
    details: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
