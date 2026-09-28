from datetime import datetime
import random
import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import or_
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
from app.models.consent import DataShareConsent
from app.models.document import Document
from app.models.government_record import GovernmentRecord
from app.models.interoperability_exception import InteroperabilityException
from app.models.service import Service
from app.models.transaction import InteroperabilityTransaction
from app.models.transaction_event import TransactionEvent
from app.models.user import User
from app.models.workflow import Workflow
from app.schemas.application import ApplicationCreate, ApplicationUpdate, WorkflowStageUpdate
from app.services.service_config import validate_form_data
from app.services.workflow_engine import WorkflowEngineError, workflow_engine

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
    assigned_officer_id: int | None = None
    assigned_officer_name: str | None = None
    current_workflow_step: dict | None = None
    sla_due_at: datetime | None = None
    location: str | None = None
    form_data: dict | None = None
    workflow: list[dict] | None = None
    created_at: datetime
    updated_at: datetime
    document_count: int = 0


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
        "assigned_officer_id": app.assigned_officer_id,
        "assigned_officer_name": (
            app.assigned_officer.full_name if app.assigned_officer else None
        ),
        "current_workflow_step": app.current_workflow_step,
        "sla_due_at": app.workflow_run.sla_due_at if app.workflow_run else None,
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
    assigned_to_me: bool = Query(False),
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
            joinedload(ServiceApplication.assigned_officer),
            joinedload(ServiceApplication.workflow_run).joinedload(Workflow.steps),
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
    if assigned_to_me:
        if role_key != "department_officer":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only department officers can filter their assigned applications.",
            )
        query = query.filter(
            ServiceApplication.assigned_officer_id == current_user.id
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
    run = app.workflow_run
    step = next(
        (item for item in run.steps if item.step_key == payload.stage_key),
        None,
    ) if run else None
    role_key = get_user_role_key(current_user)
    if role_key == "department_officer":
        officer_department = current_user.department_record
        if (
            step is None
            or step.department is None
            or officer_department is None
            or not workflow_engine._same_department(
                workflow_engine._compact(officer_department.name),
                workflow_engine._compact(step.department),
            )
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This workflow step is not assigned to your department.",
            )
        if app.assigned_officer_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Assign this application to yourself before acting on its workflow.",
            )
    else:
        ensure_resource_access(
            current_user, citizen_id=app.citizen_id, department_id=app.department_id
        )

    try:
        workflow_engine.transition_step(
            db,
            app,
            payload.stage_key,
            next_status=payload.status,
            actor_id=current_user.id,
            detail=payload.detail,
            error=payload.error,
            next_step=payload.next_step,
        )
    except WorkflowEngineError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    db.refresh(app)
    return app.workflow


@router.post("/{application_id}/assign-to-me", response_model=EnrichedApplicationRead)
def assign_application_to_me(
    application_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role("department_officer"))],
):
    app = (
        db.query(ServiceApplication)
        .filter(ServiceApplication.id == application_id)
        .with_for_update()
        .first()
    )
    if app is None:
        raise HTTPException(status_code=404, detail="Application not found.")
    ensure_resource_access(
        current_user, citizen_id=app.citizen_id, department_id=app.department_id
    )
    if app.assigned_officer_id not in (None, current_user.id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This application is already assigned to another officer.",
        )
    if app.assigned_officer_id is None:
        app.assigned_officer_id = current_user.id
        db.add(
            ApplicationEvent(
                application_id=app.id,
                actor_id=current_user.id,
                event_type="application_assigned",
                status=app.status.value,
                note=f"Assigned to {current_user.full_name}.",
            )
        )
        db.add(
            AuditLog(
                action="APPLICATION_ASSIGNED",
                entity_type="service_application",
                entity_id=str(app.id),
                details=f"Application assigned to {current_user.full_name}.",
                actor_id=current_user.id,
            )
        )
        db.commit()
        db.refresh(app)
    return enrich_application(app)


@router.get("/{application_id}/workspace")
def get_application_workspace(
    application_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_authenticated_user)],
):
    app = (
        db.query(ServiceApplication)
        .options(
            joinedload(ServiceApplication.citizen),
            joinedload(ServiceApplication.service).joinedload(Service.department),
            joinedload(ServiceApplication.assigned_officer),
            joinedload(ServiceApplication.workflow_run).joinedload(Workflow.steps),
            joinedload(ServiceApplication.documents),
        )
        .filter(ServiceApplication.id == application_id)
        .first()
    )
    if app is None:
        raise HTTPException(status_code=404, detail="Application not found.")
    ensure_resource_access(
        current_user, citizen_id=app.citizen_id, department_id=app.department_id
    )

    records = (
        db.query(GovernmentRecord)
        .options(joinedload(GovernmentRecord.department), joinedload(GovernmentRecord.values))
        .filter(GovernmentRecord.application_id == app.id)
        .order_by(GovernmentRecord.created_at.desc())
        .all()
    )
    consent_query = db.query(DataShareConsent).filter(
        DataShareConsent.citizen_id == app.citizen_id
    )
    consent_filters = [DataShareConsent.application_id == app.id]
    if app.service is not None:
        consent_filters.append(
            (DataShareConsent.application_id.is_(None))
            & (DataShareConsent.target_platform_id == app.service.platform_id)
        )
    consents = (
        consent_query.options(joinedload(DataShareConsent.source_platform))
        .filter(or_(*consent_filters))
        .order_by(DataShareConsent.created_at.desc())
        .all()
    )
    transactions = (
        db.query(InteroperabilityTransaction)
        .filter(InteroperabilityTransaction.application_id == app.id)
        .order_by(InteroperabilityTransaction.created_at.desc())
        .all()
    )
    transaction_events = (
        db.query(TransactionEvent)
        .filter(
            TransactionEvent.transaction_id.in_(
                [transaction.id for transaction in transactions]
            )
        )
        .order_by(TransactionEvent.occurred_at.desc())
        .all()
        if transactions
        else []
    )
    exceptions = (
        db.query(InteroperabilityException)
        .filter(
            or_(
                InteroperabilityException.service_application_id == app.id,
                InteroperabilityException.application_id.in_(
                    [str(app.id), app.reference_id]
                ),
            )
        )
        .order_by(InteroperabilityException.created_at.desc())
        .all()
    )
    application_events = (
        db.query(ApplicationEvent)
        .filter(ApplicationEvent.application_id == app.id)
        .order_by(ApplicationEvent.occurred_at.desc())
        .all()
    )
    related_ids = {
        str(app.id),
        app.reference_id,
        *(str(record.id) for record in records),
        *(str(document.id) for document in app.documents),
        *(str(consent.id) for consent in consents),
        *(str(transaction.id) for transaction in transactions),
        *(transaction.transaction_id for transaction in transactions),
    }
    transaction_public_ids = [transaction.public_id for transaction in transactions]
    audit_query = db.query(AuditLog).filter(
        or_(
            AuditLog.entity_id.in_(related_ids),
            AuditLog.resource_id.in_(related_ids),
            AuditLog.transaction_id.in_(transaction_public_ids)
            if transaction_public_ids
            else AuditLog.id == -1,
        )
    )
    audit_logs = audit_query.order_by(AuditLog.occurred_at.desc()).limit(200).all()

    return {
        "application": enrich_application(app),
        "citizen": {
            "id": app.citizen.id,
            "full_name": app.citizen.full_name,
            "email": app.citizen.email,
            "phone": app.citizen.phone,
            "aadhaar_last4": app.citizen.aadhaar_last4,
        },
        "application_information": {
            "id": app.id,
            "reference_id": app.reference_id,
            "status": app.status.value,
            "service_id": app.service_id,
            "service_name": app.service.name if app.service else None,
            "department_name": (
                app.service.department.name
                if app.service and app.service.department
                else None
            ),
            "submitted_at": app.created_at.isoformat() if app.created_at else None,
            "form_data": app.form_data or {},
            "sla_due_at": (
                app.workflow_run.sla_due_at.isoformat()
                if app.workflow_run and app.workflow_run.sla_due_at
                else None
            ),
            "assigned_officer_id": app.assigned_officer_id,
            "assigned_officer_name": (
                app.assigned_officer.full_name if app.assigned_officer else None
            ),
        },
        "verified_records": [
            {
                "id": str(record.id),
                "record_type": record.record_type,
                "status": record.status,
                "department": record.department.name if record.department else None,
                "source_record_id": record.source_record_id,
                "verified_at": record.verified_at.isoformat() if record.verified_at else None,
                "values": {
                    value.field_key: value.field_value for value in record.values
                },
            }
            for record in records
        ],
        "documents": [
            {
                "id": document.id,
                "title": document.title,
                "doc_type": document.doc_type,
                "is_verified": document.is_verified,
                "verification_score": document.verification_score,
                "fraud_risk_level": document.fraud_risk_level,
                "created_at": document.created_at.isoformat()
                if document.created_at
                else None,
            }
            for document in app.documents
        ],
        "consents": [
            {
                "id": consent.id,
                "purpose": consent.purpose,
                "requested_data": consent.requested_data,
                "status": consent.status.value,
                "source_department": (
                    consent.source_platform.department.name
                    if consent.source_platform and consent.source_platform.department
                    else None
                ),
                "granted_at": consent.granted_at.isoformat()
                if consent.granted_at
                else None,
                "expires_at": consent.expires_at.isoformat()
                if consent.expires_at
                else None,
                "revoked_at": consent.revoked_at.isoformat()
                if consent.revoked_at
                else None,
            }
            for consent in consents
        ],
        "transactions": [
            {
                "transaction_id": transaction.transaction_id,
                "status": transaction.status,
                "source_department": transaction.source_department,
                "requesting_department": transaction.requesting_department,
                "data_requested": transaction.data_requested,
                "requested_at": transaction.requested_at.isoformat()
                if transaction.requested_at
                else None,
                "completed_at": transaction.completed_at.isoformat()
                if transaction.completed_at
                else None,
                "error_message": transaction.error_message,
            }
            for transaction in transactions
        ],
        "transaction_events": [
            {
                "id": str(event.id),
                "transaction_id": event.transaction_id,
                "event_type": event.event_type,
                "status": event.status,
                "detail": event.detail,
                "error_code": event.error_code,
                "error_message": event.error_message,
                "occurred_at": event.occurred_at.isoformat()
                if event.occurred_at
                else None,
            }
            for event in transaction_events
        ],
        "workflow": app.workflow,
        "exceptions": [
            {
                "id": exception.id,
                "system": exception.system,
                "category": exception.category,
                "message": exception.message,
                "severity": exception.severity,
                "status": exception.status.value,
                "details": exception.details,
                "created_at": exception.created_at.isoformat()
                if exception.created_at
                else None,
            }
            for exception in exceptions
        ],
        "audit_events": [
            {
                "id": str(event.id),
                "action": event.event_type,
                "entity_type": "application_event",
                "details": event.note,
                "actor_id": event.actor_id,
                "created_at": event.occurred_at.isoformat()
                if event.occurred_at
                else None,
            }
            for event in application_events
        ]
        + [
            {
                "id": audit.id,
                "action": audit.action,
                "entity_type": audit.entity_type,
                "details": audit.details,
                "actor_id": audit.actor_id,
                "created_at": audit.occurred_at.isoformat()
                if audit.occurred_at
                else None,
            }
            for audit in audit_logs
        ],
    }


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

        workflow_definition = workflow_engine.ensure_definition(db, svc)
        if workflow_definition is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="No workflow definition is configured for this service.",
            )

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
        workflow_engine.create_run(db, app, workflow_definition)
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
    if payload.status in {ApplicationStatus.APPROVED, ApplicationStatus.REJECTED}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Applications must be approved or rejected through their configured workflow.",
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
