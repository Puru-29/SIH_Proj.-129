from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class DocumentVerificationResult(Base):
    __tablename__ = "document_verification_results"

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), unique=True, index=True
    )
    file_sha256: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    extracted_fields: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    extraction_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    pipeline_steps: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    verification_status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="PENDING_REVIEW", index=True
    )
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    source_match_status: Mapped[str] = mapped_column(
        String(24), nullable=False, default="NOT_CHECKED", index=True
    )
    source_match: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    duplicate_status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="UNIQUE", index=True
    )
    tampering_indicators: Mapped[list] = mapped_column(
        JSON, nullable=False, default=list
    )
    reviewed_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    review_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    document = relationship("Document", back_populates="verification_result")
    reviewer = relationship("User")
