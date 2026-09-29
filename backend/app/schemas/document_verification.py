from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.document import DocumentRead


class DocumentVerificationResultRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    document_id: int
    file_sha256: str
    extracted_fields: dict[str, Any]
    extraction_text: str
    pipeline_steps: list[dict[str, Any]]
    verification_status: str
    confidence: float
    source_match_status: str
    source_match: dict[str, Any]
    duplicate_status: str
    tampering_indicators: list[str]
    reviewed_by: int | None
    reviewed_at: datetime | None
    review_note: str | None
    created_at: datetime


class DocumentWithVerificationResponse(BaseModel):
    document: DocumentRead
    verification_result: DocumentVerificationResultRead


class DocumentReviewRequest(BaseModel):
    decision: Literal["VERIFIED", "REJECTED"]
    note: str = Field(min_length=5, max_length=2000)
