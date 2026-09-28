from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class VerificationStatus(str, Enum):
    VERIFIED = "VERIFIED"
    UNVERIFIED = "UNVERIFIED"
    CONFLICT = "CONFLICT"


class Citizen(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    date_of_birth: date
    identifier: str
    source_system: str
    verification_status: VerificationStatus


class GovernmentRecord(BaseModel):
    model_config = ConfigDict(extra="allow")

    record_id: str
    record_type: str
    citizen: Citizen
    source_system: str
    verification_status: VerificationStatus
    values: dict[str, Any] = Field(default_factory=dict)
    schema_version: str = "1"
    verified_at: datetime | None = None


class Document(BaseModel):
    model_config = ConfigDict(extra="forbid")

    document_id: str
    document_type: str
    issuer: str
    issued_at: date | None = None
    verification_status: VerificationStatus
    source_system: str


class Application(BaseModel):
    model_config = ConfigDict(extra="forbid")

    application_id: str
    service_id: int
    citizen_identifier: str
    status: str
    submitted_at: datetime | None = None
    attributes: dict[str, Any] = Field(default_factory=dict)


class VerifiedRecord(BaseModel):
    model_config = ConfigDict(extra="allow")

    citizen: Citizen
    government_record: GovernmentRecord
    verification_status: VerificationStatus
    verified_at: datetime | None = None
    conflicts: dict[str, list[dict[str, Any]]] = Field(default_factory=dict)
