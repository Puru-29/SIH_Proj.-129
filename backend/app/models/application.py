from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import DateTime, Enum, ForeignKey, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ApplicationStatus(str, PyEnum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    REJECTED = "rejected"


class ServiceApplication(Base):
    __tablename__ = "service_applications"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    reference_id: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    status: Mapped[ApplicationStatus] = mapped_column(
        Enum(ApplicationStatus), default=ApplicationStatus.DRAFT
    )
    remarks: Mapped[str | None] = mapped_column(Text, nullable=True)
    citizen_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    service_id: Mapped[int] = mapped_column(ForeignKey("services.id"))
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    form_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    workflow: Mapped[list | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    citizen = relationship("User", back_populates="applications")
    service = relationship("Service", back_populates="applications")
    documents = relationship("Document", back_populates="application")
