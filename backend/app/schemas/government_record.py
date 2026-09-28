from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class GovernmentRecord(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    citizenId: str
    name: str
    dateOfBirth: str
    certificateId: str | None = None
    annualIncome: float | None = None
    sourceDepartment: str
    verified: bool = True
