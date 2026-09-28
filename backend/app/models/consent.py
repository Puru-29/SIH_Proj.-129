from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.model_base import PublicUUIDMixin, TimestampMixin


class ConsentStatus(str, PyEnum):
    PENDING = "pending"
    GRANTED = "granted"
    ACTIVE = "active"
    DENIED = "denied"
    REVOKED = "revoked"
    EXPIRED = "expired"


class DataShareConsent(PublicUUIDMixin, TimestampMixin, Base):
    __tablename__ = "data_share_consents"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    purpose: Mapped[str] = mapped_column(String(255))
    status: Mapped[ConsentStatus] = mapped_column(Enum(ConsentStatus), default=ConsentStatus.GRANTED)
    source_platform_id: Mapped[int] = mapped_column(
        ForeignKey("connected_systems.id", ondelete="RESTRICT"), index=True
    )
    target_platform_id: Mapped[int] = mapped_column(
        ForeignKey("connected_systems.id", ondelete="RESTRICT"), index=True
    )
    citizen_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    application_id: Mapped[int | None] = mapped_column(
        ForeignKey("service_applications.id", ondelete="SET NULL"), nullable=True, index=True
    )
    requesting_department_id: Mapped[int] = mapped_column(
        ForeignKey("departments.id", ondelete="RESTRICT"), index=True
    )
    source_department_id: Mapped[int] = mapped_column(
        ForeignKey("departments.id", ondelete="RESTRICT"), index=True
    )
    requested_data: Mapped[str] = mapped_column(Text, nullable=False, default="")
    granted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    citizen = relationship("User", back_populates="consents")
    source_platform = relationship("ConnectedSystem", foreign_keys=[source_platform_id])
    target_platform = relationship("ConnectedSystem", foreign_keys=[target_platform_id])
    application = relationship("ServiceApplication", back_populates="consents")
    requesting_department = relationship("Department", foreign_keys=[requesting_department_id])
    source_department = relationship("Department", foreign_keys=[source_department_id])
    data_items = relationship(
        "ConsentDataItem", back_populates="consent", cascade="all, delete-orphan"
    )
    transactions = relationship("InteroperabilityTransaction", back_populates="consent")


class ConsentDataItem(TimestampMixin, Base):
    __tablename__ = "consent_data_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    consent_id: Mapped[int] = mapped_column(
        ForeignKey("data_share_consents.id", ondelete="CASCADE"), index=True
    )
    data_key: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    classification: Mapped[str | None] = mapped_column(String(40), nullable=True)

    consent = relationship("DataShareConsent", back_populates="data_items")
