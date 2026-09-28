from datetime import datetime
import uuid

from sqlalchemy import DateTime, ForeignKey, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.model_base import PublicUUIDMixin, TimestampMixin


class InteroperabilityTransaction(PublicUUIDMixin, TimestampMixin, Base):
    __tablename__ = "interoperability_transactions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    transaction_id: Mapped[str] = mapped_column(
        String(80), unique=True, index=True, default=lambda: str(uuid.uuid4())
    )
    application_id: Mapped[int] = mapped_column(
        ForeignKey("service_applications.id", ondelete="RESTRICT"), index=True
    )
    citizen_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    consent_id: Mapped[int] = mapped_column(
        ForeignKey("data_share_consents.id", ondelete="RESTRICT"), index=True
    )
    source_system_id: Mapped[int] = mapped_column(
        ForeignKey("connected_systems.id", ondelete="RESTRICT"), index=True
    )
    destination_system_id: Mapped[int] = mapped_column(
        ForeignKey("connected_systems.id", ondelete="RESTRICT"), index=True
    )
    transaction_type: Mapped[str] = mapped_column(
        String(80), nullable=False, default="data_exchange"
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="requested", index=True)
    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    requesting_department: Mapped[str] = mapped_column(String(200))
    source_department: Mapped[str] = mapped_column(String(200))
    data_requested: Mapped[str] = mapped_column(String(500))
    purpose: Mapped[str] = mapped_column(String(500))
    consent_status: Mapped[str] = mapped_column(String(40))
    request_status: Mapped[str] = mapped_column(String(40))
    validation_status: Mapped[str] = mapped_column(String(40))
    mapping_status: Mapped[str] = mapped_column(String(40))
    response_status: Mapped[str] = mapped_column(String(40))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    application = relationship("ServiceApplication", back_populates="transactions")
    consent = relationship("DataShareConsent", back_populates="transactions")
    source_system = relationship("ConnectedSystem", foreign_keys=[source_system_id])
    destination_system = relationship("ConnectedSystem", foreign_keys=[destination_system_id])
    events = relationship(
        "TransactionEvent", back_populates="transaction", cascade="all, delete-orphan"
    )
