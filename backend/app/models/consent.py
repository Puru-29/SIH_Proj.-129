from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import DateTime, Enum, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ConsentStatus(str, PyEnum):
    GRANTED = "granted"
    REVOKED = "revoked"
    EXPIRED = "expired"


class DataShareConsent(Base):
    __tablename__ = "data_share_consents"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    purpose: Mapped[str] = mapped_column(String(255))
    status: Mapped[ConsentStatus] = mapped_column(Enum(ConsentStatus), default=ConsentStatus.GRANTED)
    source_platform_id: Mapped[int] = mapped_column(ForeignKey("digital_platforms.id"))
    target_platform_id: Mapped[int] = mapped_column(ForeignKey("digital_platforms.id"))
    citizen_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    citizen = relationship("User", back_populates="consents")
    source_platform = relationship("DigitalPlatform", foreign_keys=[source_platform_id])
    target_platform = relationship("DigitalPlatform", foreign_keys=[target_platform_id])
