from datetime import datetime, timezone
import random
import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.api.deps import (
    ensure_resource_access,
    get_user_role_key,
    require_authenticated_user,
    require_role,
)
from app.models.application import ApplicationStatus, ServiceApplication
from app.models.application_event import ApplicationEvent
from app.models.audit import AuditLog
from app.models.service import Service
from app.models.user import User
from app.models.workflow import Workflow, WorkflowStep
from app.schemas.application import ApplicationCreate, ApplicationUpdate, WorkflowStageUpdate
from app.services.service_config import get_workflow_stages, validate_form_data

router = APIRouter(prefix="/applications", tags=["Service Applications"])


class EnrichedApplicationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    reference_id: str
    status: ApplicationStatus
    remarks: str | None
    citizen_id: int
    citizen_name: str | None = None
    citizen_email: str | None = None
    citizen_phone: str | None = None
    citizen_aadhaar_last4: str | None = None
    service_id: int
    service_name: str | None = None
    service_code: str | None = None
    department_name: str | None = None
    location: str | None = None
    form_data: dict | None = None
    workflow: list[dict] | None = None
    created_at: datetime
    updated_at: datetime
    document_count: int = 0


def get_default_workflow_stages() -> list[dict]:
    """Get default workflow stages for applications."""
    now_iso = datetime.now(timezone.utc).isoformat()
    return [
        {"key": "submitted", "label": "Application Submitted", "status": "completed", "detail": "Application form submitted via citizen portal", "attempts": 1, "started_at": now_iso, "completed_at": now_iso, "error": None},
        {"key": "auth", "label": "Authentication", "status": "pending", "detail": "Aadhaar eKYC verification", "attempts": 0, "started_at": None, "completed_at": None, "error": None},
        {"key": "consent", "label": "Consent Capture", "status": "pending", "detail": "Data share consent collection", "attempts": 0, "started_at": None, "completed_at": None, "error": None},
        {"key": "income", "label": "Income Verification", "status": "pending", "detail": "Cross-check income against tax records", "attempts": 0, "started_at": None, "completed_at": None, "error": None},
        {"key": "education", "label": "Education Verification", "status": "pending", "detail": "Verify institutional enrollment and marks", "attempts": 0, "started_at": None, "completed_at": None, "error": None},
        {"key": "bank", "label": "Bank Verification", "status": "pending", "detail": "Verify bank account details", "attempts": 0, "started_at": None, "completed_at": None, "error": None},
        {"key": "eligibility", "label": "Eligibility Check", "status": "pending", "detail": "Determine scholarship eligibility", "attempts": 0, "started_at": None, "completed_at": None, "error": None},
        {"key": "approval", "label": "Final Approval", "status": "pending", "detail": "Government approval officer review", "attempts": 0, "started_at": None, "completed_at": None, "error": None},
        {"key": "completed", "label": "Application Completed", "status": "pending", "detail": "Scholarship disbursement and notifications", "attempts": 0, "started_at": None, "completed_at": None, "error": None},
    ]


def enrich_application(app: ServiceApplication) -> dict[str, Any]:
    """Enrich application with related data."""
    return {
        "id": app.id,
        "reference_id": app.reference_id,
        "status": app.status,
        "remarks": app.remarks,
        "citizen_id": app.citizen_id,
        "citizen_name": app.citizen.full_name if app.citizen else None,
        "citizen_email": app.citizen.email if app.citizen else None,
        "citizen_phone": app.citizen.phone if app.citizen else None,
        "citizen_aadhaar_last4": app.citizen.aadhaar_last4 if app.citizen else None,
        "service_id": app.service_id,
        "service_name": app.service.name if app.service else None,
        "service_code": app.service.code if app.service else None,
        "department_name": (app.service.department.name if app.service and app.service.department else None),
        "location": app.location,
        "form_data": app.form_data,
        "workflow": app.workflow,
        "created_at": app.created_at,
        "updated_at": app.updated_at,
        "document_count": len(app.documents) if app.documents else 0,
    }


@router.get("", response_model=list[EnrichedApplicationRead])
def list_applications(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[
        User,
        Depends(
            require_role(
                "citizen",
                "department_officer",
                "interoperability_admin",
                "system_admin",
            )
        ),
    ],
    status_filter: ApplicationStatus | None = Query(None, alias="status"),
    citizen_id: int | None = Query(None),
    service_id: int | None = Query(None),
    search: str | None = Query(None, description="Search by reference ID or applicant name"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """List service applications with filtering and pagination."""
    query = (
        db.query(ServiceApplication)
        .options(
            joinedload(ServiceApplication.citizen),
            joinedload(ServiceApplication.service).joinedload(Service.department),
            joinedload(ServiceApplication.documents),
        )
    )

    if status_filter:
        query = query.filter(ServiceApplication.status == status_filter)
    role_key = get_user_role_key(current_user)
    if role_key == "citizen":
        if citizen_id is not None and citizen_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Citizens may only view their own applications.",
            )
        query = query.filter(ServiceApplication.citizen_id == current_user.id)
    elif role_key == "department_officer":
        if current_user.department_id is None:
            return []
        query = query.filter(
            ServiceApplication.department_id == current_user.department_id
        )
    if citizen_id is not None and role_key != "citizen":
        query = query.filter(ServiceApplication.citizen_id == citizen_id)
    if service_id:
        query = query.filter(ServiceApplication.service_id == service_id)
    if search:
        query = query.join(ServiceApplication.citizen).filter(
            (ServiceApplication.reference_id.ilike(f"%{search}%"))
            | (User.full_name.ilike(f"%{search}%"))
            | (User.email.ilike(f"%{search}%"))
        )

    apps = query.order_by(ServiceApplication.created_at.desc()).offset(offset).limit(limit).all()
    return [enrich_application(a) for a in apps]


@router.get("/track/{reference_id}", response_model=EnrichedApplicationRead)
def track_application(
    reference_id: str,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_authenticated_user)],
):
    """Look up an application after enforcing citizen or department ownership."""
    app = (
        db.query(ServiceApplication)
        .options(
            joinedload(ServiceApplication.citizen),
            joinedload(ServiceApplication.service).joinedload(Service.department),
            joinedload(ServiceApplication.documents),
        )
        .filter(ServiceApplication.reference_id == reference_id)
        .first()
    )
    if not app:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application with reference '{reference_id}' not found.",
        )
    ensure_resource_access(
        current_user, citizen_id=app.citizen_id, department_id=app.department_id
    )
    return enrich_application(app)


@router.get("/{application_id}", response_model=EnrichedApplicationRead)
def get_application(
    application_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_authenticated_user)],
):
    """Get full details of an application by ID."""
    app = (
        db.query(ServiceApplication)
        .options(
            joinedload(ServiceApplication.citizen),
            joinedload(ServiceApplication.service).joinedload(Service.department),
            joinedload(ServiceApplication.documents),
        )
        .filter(ServiceApplication.id == application_id)
        .first()
    )
    if not app:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")
    ensure_resource_access(
        current_user, citizen_id=app.citizen_id, department_id=app.department_id
    )
    return enrich_application(app)


@router.get("/{application_id}/workflow", response_model=list[dict])
def get_application_workflow(
    application_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_authenticated_user)],
):
    """Get workflow stages for an application."""
    app = db.query(ServiceApplication).filter(ServiceApplication.id == application_id).first()
    if not app:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")
    ensure_resource_access(
        current_user, citizen_id=app.citizen_id, department_id=app.department_id
    )

    return app.workflow


@router.patch("/{application_id}/workflow", response_model=list[dict])
def update_application_workflow(
    application_id: int,
    payload: WorkflowStageUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[
        User,
        Depends(
            require_role(
                "department_officer", "interoperability_admin", "system_admin"
            )
        ),
    ],
):
    """Update a specific workflow stage in an application."""
    app = db.query(ServiceApplication).filter(ServiceApplication.id == application_id).first()
    if not app:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")
    ensure_resource_access(
        current_user, citizen_id=app.citizen_id, department_id=app.department_id
    )

    if not app.workflow_run:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No workflow found for this application")

    stage = next(
        (step for step in app.workflow_run.steps if step.step_key == payload.stage_key), None
    )
    if not stage:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Stage '{payload.stage_key}' not found in workflow",
        )

    # Update stage
    stage.status = payload.status
    if payload.detail:
        stage.detail = payload.detail
    if payload.status == "completed":
        stage.completed_at = (
            datetime.fromisoformat(payload.completed_at)
            if payload.completed_at
            else datetime.now(timezone.utc)
        )
    elif payload.completed_at:
        stage.completed_at = datetime.fromisoformat(payload.completed_at)
    if payload.error:
        stage.error_message = payload.error
    stage.attempts += 1

    db.add(
        ApplicationEvent(
            application_id=app.id,
            event_type="workflow_step_updated",
            status=payload.status,
            note=payload.detail or payload.error,
        )
    )
    db.commit()
    db.refresh(app)

    return app.workflow


@router.post("", response_model=EnrichedApplicationRead, status_code=status.HTTP_201_CREATED)
def create_application(
    payload: ApplicationCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role("citizen"))],
):
    """Submit a new service application to the inter-governmental mesh."""
    try:
        # Validate citizen and service exist
        if payload.citizen_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Applications can only be submitted for the signed-in citizen.",
            )
        citizen = current_user

        svc = db.query(Service).filter(Service.id == payload.service_id).first()
        if not svc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service not found")

        form_errors = validate_form_data(svc, payload.form_data or {}, payload.verified_records)
        if form_errors:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=form_errors)

        # Generate reference_id if empty or conflict
        ref_id = payload.reference_id or f"APP-2026-{random.randint(10000, 99999)}"
        existing = db.query(ServiceApplication).filter(ServiceApplication.reference_id == ref_id).first()
        if existing:
            ref_id = f"APP-2026-{uuid.uuid4().hex[:6].upper()}"

        workflow_stages = get_workflow_stages(svc)

        app = ServiceApplication(
            reference_id=ref_id,
            citizen_id=payload.citizen_id,
            service_id=payload.service_id,
            department_id=svc.department_id,
            status=ApplicationStatus.SUBMITTED,
            remarks=payload.remarks or "Application submitted via citizen mesh portal",
            location=payload.location,
            form_data={
                **(payload.form_data or {}),
                "_verified_records": payload.verified_records or {},
            },
        )
        db.add(app)
        db.flush()
        workflow = Workflow(
            service_id=svc.id,
            application_id=app.id,
            name=f"{svc.name} application workflow",
        )
        workflow.steps = [
            WorkflowStep(
                step_key=stage["key"],
                name=stage["label"],
                sequence=index,
                status=stage["status"],
                attempts=stage.get("attempts", 0),
                detail=stage.get("detail"),
                error_message=stage.get("error"),
                started_at=(
                    datetime.fromisoformat(stage["started_at"])
                    if stage.get("started_at")
                    else None
                ),
                completed_at=(
                    datetime.fromisoformat(stage["completed_at"])
                    if stage.get("completed_at")
                    else None
                ),
            )
            for index, stage in enumerate(workflow_stages)
        ]
        db.add(workflow)
        db.add(
            ApplicationEvent(
                application_id=app.id,
                actor_id=citizen.id,
                event_type="application_submitted",
                status=ApplicationStatus.SUBMITTED.value,
                note=f"Application created for {svc.name}.",
            )
        )

        # Log audit entry
        audit = AuditLog(
            action="APPLICATION_CREATED",
            entity_type="service_application",
            entity_id=str(app.id),
            details=f"Application {app.reference_id} created for {svc.name} by {citizen.full_name}",
            actor_id=citizen.id,
        )
        db.add(audit)
        db.commit()

        # Re-query to load all relationships
        app = db.query(ServiceApplication).filter(ServiceApplication.id == app.id).options(
            joinedload(ServiceApplication.citizen),
            joinedload(ServiceApplication.service).joinedload(Service.department),
            joinedload(ServiceApplication.documents),
        ).first()

        if app is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Application was saved but could not be reloaded.",
            )
        return enrich_application(app)
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.patch("/{application_id}/status", response_model=EnrichedApplicationRead)
def update_application_status(
    application_id: int,
    payload: ApplicationUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[
        User, Depends(require_role("department_officer", "system_admin"))
    ],
):
    """Update status (e.g. under_review, approved, rejected) and remarks of an application."""
    app = db.query(ServiceApplication).filter(ServiceApplication.id == application_id).first()
    if not app:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")
    ensure_resource_access(
        current_user, citizen_id=app.citizen_id, department_id=app.department_id
    )

    old_status = app.status
    if payload.status:
        app.status = payload.status
    if payload.remarks is not None:
        app.remarks = payload.remarks

    # Log audit
    audit = AuditLog(
        action="APPLICATION_STATUS_UPDATED",
        entity_type="service_application",
        entity_id=str(app.id),
        details=f"Status changed from {old_status} to {app.status}. Remarks: {payload.remarks}",
        actor_id=current_user.id,
    )
    db.add(audit)
    db.commit()
    db.refresh(app)

    return enrich_application(app)
