from enum import Enum as PyEnum

from sqlalchemy import Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class PlatformStatus(str, PyEnum):
    ACTIVE = "active"
    DEGRADED = "degraded"
    OFFLINE = "offline"


class DigitalPlatform(Base):
    __tablename__ = "digital_platforms"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(200))
    slug: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    base_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    api_version: Mapped[str] = mapped_column(String(20), default="v1")
    status: Mapped[PlatformStatus] = mapped_column(Enum(PlatformStatus), default=PlatformStatus.ACTIVE)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    department_id: Mapped[int] = mapped_column(ForeignKey("departments.id"))

    department = relationship("Department", back_populates="platforms")
    services = relationship("Service", back_populates="platform")
