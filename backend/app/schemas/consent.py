from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.consent import ConsentStatus


class ConsentCreate(BaseModel):
    purpose: str
    source_platform_id: int
    target_platform_id: int
    citizen_id: int
    expires_at: datetime | None = None


class ConsentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    purpose: str
    status: ConsentStatus
    source_platform_id: int
    target_platform_id: int
    citizen_id: int
    created_at: datetime
    expires_at: datetime | None
