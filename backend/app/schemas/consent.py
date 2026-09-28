from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.consent import ConsentStatus


class ConsentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    purpose: str = Field(min_length=1, max_length=255)
    source_platform_id: int
    target_platform_id: int
    citizen_id: int
    application_id: int | None = None
    requested_data: str = Field(min_length=1)
    requested_fields: list[str] = Field(min_length=1)


class ConsentDataItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    data_key: str
    description: str
    classification: str | None = None


class ConsentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    purpose: str
    status: ConsentStatus
    source_platform_id: int
    target_platform_id: int
    citizen_id: int
    application_id: int | None = None
    requested_data: str
    granted_at: datetime | None = None
    expires_at: datetime | None = None
    revoked_at: datetime | None = None
    created_at: datetime
    data_items: list[ConsentDataItemRead] = Field(default_factory=list)
