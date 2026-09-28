from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class WorkflowStepType(str, Enum):
    DATA_REQUEST = "DATA_REQUEST"
    CONSENT = "CONSENT"
    DOCUMENT_UPLOAD = "DOCUMENT_UPLOAD"
    DOCUMENT_VERIFICATION = "DOCUMENT_VERIFICATION"
    DATA_VALIDATION = "DATA_VALIDATION"
    OFFICER_REVIEW = "OFFICER_REVIEW"
    APPROVAL = "APPROVAL"
    REJECTION = "REJECTION"
    NOTIFICATION = "NOTIFICATION"
    COMPLETION = "COMPLETION"


class WorkflowStepDefinition(BaseModel):
    step_id: str = Field(min_length=1, max_length=80, pattern=r"^[a-zA-Z0-9_-]+$")
    name: str = Field(min_length=1, max_length=160)
    department: str | None = Field(default=None, max_length=160)
    type: WorkflowStepType
    order: int = Field(ge=0)
    required: bool = True
    action: dict[str, Any] = Field(default_factory=dict)
    next_steps: list[str] = Field(default_factory=list)


class WorkflowDefinitionCreate(BaseModel):
    service_id: int
    name: str = Field(min_length=1, max_length=160)
    steps: list[WorkflowStepDefinition] = Field(min_length=1)
    required_records: list[str] = Field(default_factory=list)
    required_consents: list[str] = Field(default_factory=list)
    departments: list[str] = Field(default_factory=list)
    transitions: dict[str, list[str]] = Field(default_factory=dict)
    sla_hours: int | None = Field(default=None, ge=1, le=8760)

    @model_validator(mode="after")
    def validate_graph(self) -> WorkflowDefinitionCreate:
        step_ids = [step.step_id for step in self.steps]
        if len(step_ids) != len(set(step_ids)):
            raise ValueError("Workflow step_id values must be unique.")
        if len({step.order for step in self.steps}) != len(self.steps):
            raise ValueError("Workflow step order values must be unique.")
        known = set(step_ids)
        edges = {
            source: targets
            for source, targets in self.transitions.items()
        }
        for step in self.steps:
            edges.setdefault(step.step_id, step.next_steps)
        for source, targets in edges.items():
            if source not in known or any(target not in known for target in targets):
                raise ValueError("Workflow transitions must reference defined steps.")
        return self


class WorkflowStepRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    step_id: str
    name: str
    department: str | None
    type: WorkflowStepType
    order: int
    required: bool
    action: dict[str, Any]
    next_steps: list[str]
    status: str
    attempts: int
    detail: str | None


class WorkflowRead(BaseModel):
    id: int
    workflow_id: int
    service_id: int
    application_id: int | None
    name: str
    version: int
    status: str
    steps: list[WorkflowStepRead]
    required_records: list[str]
    required_consents: list[str]
    departments: list[str]
    transitions: dict[str, list[str]]
    sla_hours: int | None
    sla_due_at: datetime | None
