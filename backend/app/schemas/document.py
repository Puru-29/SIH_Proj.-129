from datetime import datetime
from pydantic import BaseModel, ConfigDict


class DocumentCreate(BaseModel):
    title: str
    doc_type: str
    file_path: str
    mime_type: str = "application/pdf"
    owner_id: int
    application_id: int | None = None


class DocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    doc_type: str
    file_path: str
    mime_type: str
    owner_id: int
    application_id: int | None
    is_verified: bool = False
    verification_score: float | None = None
    fraud_risk_level: str | None = None
    extracted_text: str | None = None
    extracted_entities: str | None = None
    created_at: datetime
