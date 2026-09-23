from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(200))
    doc_type: Mapped[str] = mapped_column(String(80))
    file_path: Mapped[str] = mapped_column(String(500))
    mime_type: Mapped[str] = mapped_column(String(80), default="application/pdf")
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    application_id: Mapped[int | None] = mapped_column(ForeignKey("service_applications.id"), nullable=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    verification_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    fraud_risk_level: Mapped[str | None] = mapped_column(String(30), nullable=True)
    extracted_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    extracted_entities: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    owner = relationship("User", back_populates="documents")
    application = relationship("ServiceApplication", back_populates="documents")
