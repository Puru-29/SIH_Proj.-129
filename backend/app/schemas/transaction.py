from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, ConfigDict


class TransactionRecord(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    transactionId: str
    requestingDepartment: str
    sourceDepartment: str
    dataRequested: str
    consentStatus: str
    requestStatus: str
    validationStatus: str
    mappingStatus: str
    responseStatus: str
    createdAt: datetime
    completedAt: datetime | None = None
