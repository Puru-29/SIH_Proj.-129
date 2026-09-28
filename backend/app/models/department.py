from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.model_base import PublicUUIDMixin, TimestampMixin


class Department(PublicUUIDMixin, TimestampMixin, Base):
    __tablename__ = "departments"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(200), unique=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    state: Mapped[str] = mapped_column(String(80), default="Maharashtra")

    users = relationship("User", back_populates="department_record")
    platforms = relationship("ConnectedSystem", back_populates="department")
    services = relationship("Service", back_populates="department")
    applications = relationship("ServiceApplication", back_populates="department")
