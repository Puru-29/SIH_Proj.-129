from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class AuditLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    timestamp: datetime
    actor_id: int | None
    actor_role: str | None
    department_id: int | None
    action: str
    resource_type: str
    resource_id: str
    transaction_id: str | None
    result: str
    metadata: dict[str, Any]
    details: str | None
    actor_name: str | None = None
