from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import DateTime, Enum, ForeignKey, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.model_base import PublicUUIDMixin, TimestampMixin


class ApplicationStatus(str, PyEnum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    REJECTED = "rejected"


class ServiceApplication(PublicUUIDMixin, TimestampMixin, Base):
    __tablename__ = "service_applications"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    reference_id: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    status: Mapped[ApplicationStatus] = mapped_column(
        Enum(ApplicationStatus), default=ApplicationStatus.DRAFT
    )
    remarks: Mapped[str | None] = mapped_column(Text, nullable=True)
    citizen_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    service_id: Mapped[int] = mapped_column(
        ForeignKey("services.id", ondelete="RESTRICT"), index=True
    )
    department_id: Mapped[int] = mapped_column(
        ForeignKey("departments.id", ondelete="RESTRICT"), index=True
    )
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    form_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    citizen = relationship("User", back_populates="applications")
    service = relationship("Service", back_populates="applications")
    department = relationship("Department", back_populates="applications")
    documents = relationship("Document", back_populates="application")
    events = relationship(
        "ApplicationEvent", back_populates="application", cascade="all, delete-orphan"
    )
    workflow_run = relationship(
        "Workflow",
        back_populates="application",
        uselist=False,
        cascade="all, delete-orphan",
    )
    government_records = relationship("GovernmentRecord", back_populates="application")
    transactions = relationship("InteroperabilityTransaction", back_populates="application")
    consents = relationship("DataShareConsent", back_populates="application")

    @property
    def workflow(self) -> list[dict]:
        if self.workflow_run is None:
            return []
        return [
            {
                "key": step.step_key,
                "label": step.name,
                "status": step.status,
                "detail": step.detail,
                "attempts": step.attempts,
                "started_at": step.started_at.isoformat() if step.started_at else None,
                "completed_at": step.completed_at.isoformat() if step.completed_at else None,
                "error": step.error_message,
            }
            for step in self.workflow_run.steps
        ]
