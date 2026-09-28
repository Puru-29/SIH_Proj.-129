from datetime import datetime
import uuid

from sqlalchemy import DateTime, ForeignKey, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.model_base import TimestampMixin


class GovernmentRecord(TimestampMixin, Base):
    __tablename__ = "government_records"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    citizen_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    department_id: Mapped[int] = mapped_column(
        ForeignKey("departments.id", ondelete="RESTRICT"), index=True
    )
    connected_system_id: Mapped[int] = mapped_column(
        ForeignKey("connected_systems.id", ondelete="RESTRICT"), index=True
    )
    application_id: Mapped[int | None] = mapped_column(
        ForeignKey("service_applications.id", ondelete="SET NULL"), nullable=True, index=True
    )
    record_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    source_record_id: Mapped[str] = mapped_column(String(160), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    schema_version: Mapped[str] = mapped_column(String(40), default="1", nullable=False)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    citizen = relationship("User")
    department = relationship("Department")
    connected_system = relationship("ConnectedSystem")
    application = relationship("ServiceApplication", back_populates="government_records")
    values = relationship(
        "GovernmentRecordValue", back_populates="record", cascade="all, delete-orphan"
    )


class GovernmentRecordValue(TimestampMixin, Base):
    __tablename__ = "government_record_values"

    id: Mapped[int] = mapped_column(primary_key=True)
    record_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("government_records.id", ondelete="CASCADE"),
        index=True,
    )
    field_key: Mapped[str] = mapped_column(String(120), nullable=False)
    field_value: Mapped[str] = mapped_column(String(4000), nullable=False)
    data_type: Mapped[str] = mapped_column(String(32), default="string", nullable=False)
    classification: Mapped[str | None] = mapped_column(String(40), nullable=True)

    record = relationship("GovernmentRecord", back_populates="values")
