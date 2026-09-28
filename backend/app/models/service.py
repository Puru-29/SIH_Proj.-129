from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.model_base import PublicUUIDMixin, TimestampMixin


class Service(PublicUUIDMixin, TimestampMixin, Base):
    __tablename__ = "services"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(200))
    code: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    department_id: Mapped[int] = mapped_column(
        ForeignKey("departments.id", ondelete="RESTRICT"), index=True
    )
    platform_id: Mapped[int] = mapped_column(
        ForeignKey("connected_systems.id", ondelete="RESTRICT"), index=True
    )

    department = relationship("Department", back_populates="services")
    platform = relationship("ConnectedSystem", back_populates="services")
    applications = relationship("ServiceApplication", back_populates="service")
    workflows = relationship("Workflow", back_populates="service")
