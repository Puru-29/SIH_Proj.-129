from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.model_base import TimestampMixin


class Grievance(TimestampMixin, Base):
    __tablename__ = "grievances"

    id: Mapped[int] = mapped_column(primary_key=True)
    citizen_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    category: Mapped[str] = mapped_column(String(120), nullable=False)
    related_application: Mapped[str | None] = mapped_column(String(80), nullable=True)
    department: Mapped[str | None] = mapped_column(String(160), nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    priority: Mapped[str] = mapped_column(String(24), default="Normal", nullable=False)
    status: Mapped[str] = mapped_column(String(24), default="Submitted", nullable=False)

    citizen = relationship("User")
