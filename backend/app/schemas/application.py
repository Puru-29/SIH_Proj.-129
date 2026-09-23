from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.application import ApplicationStatus


class WorkflowStage(BaseModel):
    """Represents a stage in an application workflow."""
    key: str
    label: str
    status: str  # pending, in_progress, completed, recovered, failed
    detail: str | None = None
    attempts: int = 0
    started_at: str | None = None
    completed_at: str | None = None
    error: str | None = None


class ApplicationCreate(BaseModel):
    reference_id: str | None = None
    citizen_id: int
    service_id: int
    remarks: str | None = None
    location: str | None = None
    form_data: dict | None = None
    consent: bool = False


class ApplicationUpdate(BaseModel):
    status: ApplicationStatus | None = None
    remarks: str | None = None


class ApplicationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    reference_id: str
    status: ApplicationStatus
    remarks: str | None
    citizen_id: int
    service_id: int
    location: str | None = None
    form_data: dict | None = None
    workflow: list[dict] | None = None
    created_at: datetime
    updated_at: datetime


class WorkflowStageUpdate(BaseModel):
    """Request to update a single workflow stage."""
    stage_key: str
    status: str
    detail: str | None = None
    completed_at: str | None = None
    error: str | None = None


class CitizenProfileInput(BaseModel):
    full_name: str
    email: str
    phone: str | None = None
    aadhaar_last4: str | None = None
    city: str | None = "New Delhi"
    district: str | None = "Central"
    pincode: str | None = "110001"


class FullApplicationSubmissionRequest(BaseModel):
    citizen: CitizenProfileInput
    service_id: int
    claimed_income: float = 240000.0
    claimed_land_acres: float = 1.5
    applicant_remarks: str | None = None
    document_title: str | None = "Citizen Identity & Scheme Record"
    doc_type: str | None = "Aadhaar / Land Record / Certificate"
    document_text: str | None = None
    image_base64: str | None = None
    dpdp_consent_granted: bool = True
    data_share_purpose: str = "Cross-Department Interoperability & Scheme Eligibility Verification"
    source_platform_id: int | None = None
    target_platform_id: int | None = None
    preferred_tabular_engine: str = "xgboost"


class FullApplicationSubmissionResponse(BaseModel):
    application: dict
    reference_id: str
    consent_id: int | None = None
    document_id: int | None = None
    verification_result: dict | None = None
    message: str

