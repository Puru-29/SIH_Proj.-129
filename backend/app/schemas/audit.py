from datetime import datetime
from pydantic import BaseModel, ConfigDict


class AuditLogCreate(BaseModel):
    action: str
    entity_type: str
    entity_id: str
    details: str | None = None
    actor_id: int | None = None


class AuditLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    action: str
    entity_type: str
    entity_id: str
    details: str | None
    actor_id: int | None
    created_at: datetime
