from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import String, cast, or_
from sqlalchemy.orm import Session, joinedload

from app.api.deps import ensure_resource_access, get_user_role_key, require_role
from app.database import get_db
from app.models.application import ServiceApplication
from app.models.interoperability_exception import (
    ExceptionStatus,
    InteroperabilityException,
)
from app.models.platform import ConnectedSystem, PlatformStatus
from app.services.interoperability.mapping_service import MappingService
from app.models.transaction import InteroperabilityTransaction
from app.models.user import User
from app.api.deps import require_authenticated_user
from app.services.interoperability_service import interoperability_service
from app.services.audit_service import record_audit
from app.services.system_health_service import check_integration_health

router = APIRouter(
    tags=["Interoperability & Demo Connectors"],
    dependencies=[Depends(require_authenticated_user)],
)
unversioned_health_router = APIRouter(
    tags=["Interoperability & Demo Connectors"],
    dependencies=[Depends(require_authenticated_user)],
)


class InteroperabilityRequest(BaseModel):
    citizen_id: int
    service_id: int
    application_id: int
    consent_id: int
    requesting_department: str = "Social Welfare"
    source_department: str = "Revenue & Land Records"
    data_requested: str = "Income Certificate"
    purpose: str = "Scholarship eligibility"


class TestMappingRequest(BaseModel):
    source_system: str = "REVENUE"
    sample_data: dict[str, Any]


mapping_service = MappingService()


@router.get("/integrations", response_model=list[dict])
def list_integrations(
    db: Annotated[Session, Depends(get_db)],
    _admin: Annotated[
        User,
        Depends(require_role(
            "department_officer", "interoperability_admin", "system_admin", "auditor"
        )),
    ],
):
    systems = (
        db.query(ConnectedSystem)
        .options(joinedload(ConnectedSystem.department))
        .order_by(ConnectedSystem.name)
        .all()
    )
    transactions = (
        db.query(InteroperabilityTransaction)
        .options(
            joinedload(InteroperabilityTransaction.source_system),
            joinedload(InteroperabilityTransaction.destination_system),
        )
        .all()
    )
    transactions_by_system: dict[int, list[InteroperabilityTransaction]] = {}
    for transaction in transactions:
        transactions_by_system.setdefault(transaction.source_system_id, []).append(transaction)
        if transaction.destination_system_id != transaction.source_system_id:
            transactions_by_system.setdefault(transaction.destination_system_id, []).append(transaction)
    health_by_system = {
        system.id: check_integration_health(db, system) for system in systems
    }
    db.commit()
    return [
        _integration_payload(
            system,
            transactions_by_system.get(system.id, []),
            health_by_system[system.id],
        )
        for system in systems
    ]


@router.get("/integrations/{integration_id}", response_model=dict)
def get_integration(
    integration_id: str,
    db: Annotated[Session, Depends(get_db)],
    _admin: Annotated[
        User,
        Depends(require_role(
            "department_officer", "interoperability_admin", "system_admin", "auditor"
        )),
    ],
):
    system = _get_connected_system(db, integration_id)
    health = check_integration_health(db, system)
    db.commit()
    return _integration_payload(system, _system_transactions(db, system.id), health)


@router.get("/integrations/{integration_id}/health", response_model=dict)
@unversioned_health_router.get(
    "/integrations/{integration_id}/health", response_model=dict
)
def health_for_integration(
    integration_id: str,
    db: Annotated[Session, Depends(get_db)],
    _admin: Annotated[
        User,
        Depends(require_role(
            "department_officer", "interoperability_admin", "system_admin", "auditor"
        )),
    ],
):
    system = _get_connected_system(db, integration_id)
    health = check_integration_health(db, system)
    db.commit()
    return _integration_payload(system, _system_transactions(db, system.id), health)


@router.post("/interoperability/request", response_model=dict)
def request_interoperability(
    payload: InteroperabilityRequest,
    current_user: Annotated[User, Depends(require_authenticated_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """Execute a demo cross-department governmental data exchange and return normalized output."""
    if get_user_role_key(current_user) != "citizen" or payload.citizen_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the signed-in citizen may authorize this data request.")
    try:
        return interoperability_service.request_interoperability(
            citizen_id=payload.citizen_id,
            service_id=payload.service_id,
            application_id=payload.application_id,
            consent_id=payload.consent_id,
            requesting_department=payload.requesting_department,
            source_department=payload.source_department,
            data_requested=payload.data_requested,
            purpose=payload.purpose,
            authenticated_user=current_user,
            db=db,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/interoperability/data-mapping/test", response_model=dict)
def test_mapping(
    payload: TestMappingRequest,
    _admin: Annotated[
        User, Depends(require_role("interoperability_admin", "system_admin"))
    ],
):
    """Validate source-to-common-model mapping for a dataset."""
    sample = payload.sample_data
    dob = sample.get("dob")
    if isinstance(dob, str) and "/" in dob:
        day, month, year = dob.split("/")
        dob = f"{year}-{month}-{day}"
    normalized = {
        "name": sample.get("full_name"),
        "dateOfBirth": dob,
        "annualIncome": sample.get("annual_income"),
        "recordId": sample.get("income_certificate_no") or sample.get("certificate_no"),
        "sourceSystem": payload.source_system,
    }
    return {"normalized": normalized, "status": "mapped", "confidence": 96}


@router.get("/data-mappings", response_model=list[dict])
@router.get("/data-mapping", response_model=list[dict])
@router.get("/interoperability/mappings", response_model=list[dict])
def list_mapping_configurations(
    db: Annotated[Session, Depends(get_db)],
    _admin: Annotated[
        User,
        Depends(
            require_role(
                "department_officer", "interoperability_admin", "system_admin", "auditor"
            )
        ),
    ],
):
    """Inspect persisted source-to-GovFlow mapping configurations."""
    mappings = mapping_service.list_mappings(db)
    return [
        {
            "id": mapping.id,
            "name": mapping.name,
            "source": mapping.source,
            "target": mapping.target,
            "sourceSystemId": mapping.source_system_id,
            "sourceSystem": mapping.source_system.name if mapping.source_system else None,
            "targetSystemId": mapping.target_system_id,
            "targetSystem": mapping.target_system.name if mapping.target_system else None,
            "sourceSchemaVersion": mapping.source_schema_version,
            "targetSchemaVersion": mapping.target_schema_version,
            "version": mapping.version,
            "status": mapping.status,
            "rules": [
                {
                    "sourceField": rule.source_field,
                    "targetField": rule.target_field,
                    "transformation": rule.transformation,
                    "required": rule.is_required,
                }
                for rule in mapping.rules
            ],
        }
        for mapping in mappings
    ]


@router.get("/interoperability/conflicts", response_model=list[dict])
def list_mapping_conflicts(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[
        User,
        Depends(
            require_role(
                "department_officer", "interoperability_admin", "system_admin"
            )
        ),
    ],
    limit: int = Query(100, ge=1, le=500),
):
    """Inspect persisted data conflicts and the values returned by each source."""
    query = db.query(InteroperabilityException).filter(
        InteroperabilityException.category == "DATA_CONFLICT"
    )
    if get_user_role_key(current_user) == "department_officer":
        if current_user.department_id is None:
            return []
        query = query.join(
            ServiceApplication,
            ServiceApplication.id == InteroperabilityException.service_application_id,
        ).filter(ServiceApplication.department_id == current_user.department_id)
    conflicts = (
        query.order_by(InteroperabilityException.created_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": conflict.id,
            "applicationId": conflict.application_id,
            "transactionId": conflict.transaction_id,
            "fieldNames": (conflict.details or {}).get("fields", []),
            "conflictingValues": (conflict.details or {}).get("conflictingValues", {}),
            "message": conflict.message,
            "severity": conflict.severity,
            "status": _status_value(conflict.status),
            "createdAt": conflict.created_at.isoformat(),
        }
        for conflict in conflicts
    ]


@router.get("/interoperability/transactions", response_model=list[dict])
def list_transactions(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[
        User,
        Depends(
            require_role(
                "citizen",
                "department_officer",
                "interoperability_admin",
                "system_admin",
                "auditor",
            )
        ),
    ],
):
    query = db.query(InteroperabilityTransaction)
    role_key = get_user_role_key(current_user)
    if role_key == "citizen":
        query = query.filter(InteroperabilityTransaction.citizen_id == current_user.id)
    elif role_key == "department_officer":
        if current_user.department_id is None:
            return []
        query = query.join(
            ServiceApplication,
            ServiceApplication.id == InteroperabilityTransaction.application_id,
        ).filter(ServiceApplication.department_id == current_user.department_id)
    rows = (
        query.options(
            joinedload(InteroperabilityTransaction.source_system),
            joinedload(InteroperabilityTransaction.destination_system),
            joinedload(InteroperabilityTransaction.application),
            joinedload(InteroperabilityTransaction.events),
        )
        .order_by(InteroperabilityTransaction.requested_at.desc())
        .limit(200)
        .all()
    )
    return [_transaction_payload(row) for row in rows]


@router.get("/interoperability/transactions/{transaction_id}", response_model=dict)
def get_transaction(
    transaction_id: str,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[
        User,
        Depends(
            require_role(
                "citizen",
                "department_officer",
                "interoperability_admin",
                "system_admin",
                "auditor",
            )
        ),
    ],
):
    query = db.query(InteroperabilityTransaction).options(
        joinedload(InteroperabilityTransaction.source_system),
        joinedload(InteroperabilityTransaction.destination_system),
        joinedload(InteroperabilityTransaction.application),
        joinedload(InteroperabilityTransaction.events),
    ).filter(
        or_(
            InteroperabilityTransaction.transaction_id == transaction_id,
            cast(InteroperabilityTransaction.id, String) == transaction_id,
        )
    )
    role_key = get_user_role_key(current_user)
    if role_key == "citizen":
        query = query.filter(InteroperabilityTransaction.citizen_id == current_user.id)
    elif role_key == "department_officer":
        if current_user.department_id is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")
        query = query.join(
            ServiceApplication,
            ServiceApplication.id == InteroperabilityTransaction.application_id,
        ).filter(ServiceApplication.department_id == current_user.department_id)
    row = query.first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")
    return _transaction_payload(row)


def _get_connected_system(db: Session, integration_id: str) -> ConnectedSystem:
    query = db.query(ConnectedSystem).options(joinedload(ConnectedSystem.department))
    if integration_id.isdecimal():
        query = query.filter(ConnectedSystem.id == int(integration_id))
    else:
        query = query.filter(ConnectedSystem.slug == integration_id)
    system = query.first()
    if system is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Connected system not found.",
        )
    return system


def _system_transactions(
    db: Session, system_id: int
) -> list[InteroperabilityTransaction]:
    return (
        db.query(InteroperabilityTransaction)
        .options(
            joinedload(InteroperabilityTransaction.source_system),
            joinedload(InteroperabilityTransaction.destination_system),
            joinedload(InteroperabilityTransaction.application),
            joinedload(InteroperabilityTransaction.events),
        )
        .filter(
            or_(
                InteroperabilityTransaction.source_system_id == system_id,
                InteroperabilityTransaction.destination_system_id == system_id,
            )
        )
        .all()
    )


def _integration_payload(
    system: ConnectedSystem,
    transactions: list[InteroperabilityTransaction],
    health_check: dict[str, Any],
) -> dict[str, Any]:
    failed_statuses = {"FAILED", "CONFLICT"}
    failures = sum(
        1 for transaction in transactions if transaction.status.upper() in failed_statuses
    )
    durations = [
        (transaction.completed_at - transaction.requested_at).total_seconds() * 1000
        for transaction in transactions
        if transaction.completed_at is not None
        and transaction.requested_at is not None
        and transaction.status.upper() in {"COMPLETED", "FAILED", "CONFLICT"}
    ]
    stored_status = (
        system.status.value
        if isinstance(system.status, PlatformStatus)
        else str(system.status)
    )
    actual_health = health_check["status"]
    connected = actual_health == "healthy"
    return {
        "id": system.id,
        "slug": system.slug,
        "name": system.name,
        "systemName": system.name,
        "department": system.department.name if system.department else None,
        "status": actual_health,
        "connectionStatus": "connected" if connected else "disconnected",
        "healthStatus": "active" if connected else actual_health,
        "responseTimeMs": health_check["response_time"],
        "transactionResponseTimeMs": (
            round(sum(durations) / len(durations), 2) if durations else None
        ),
        "lastSuccessfulRequestAt": health_check["last_successful_request"],
        "lastFailureAt": health_check["last_failure"],
        "lastFailureMessage": health_check["last_failure_message"],
        "failureCount": health_check["failure_count"],
        "system_name": health_check["system_name"],
        "connectorMode": health_check["connector_mode"],
        "status": actual_health,
        "response_time": health_check["response_time"],
        "last_successful_request": health_check["last_successful_request"],
        "last_failure": health_check["last_failure"],
        "failure_count": health_check["failure_count"],
        "transactionCount": len(transactions),
        "failedTransactionCount": failures,
        "platformStatus": stored_status,
        "isActive": system.is_active,
        "integrationType": system.integration_type,
        "apiVersion": system.api_version,
    }


def _transaction_payload(row: InteroperabilityTransaction) -> dict[str, Any]:
    created_at = row.requested_at.isoformat() if row.requested_at else None
    completed_at = row.completed_at.isoformat() if row.completed_at else None
    ordered_events = sorted(
        row.events,
        key=lambda item: item.occurred_at or row.requested_at,
    )
    timeline_steps = (
        ("REQUEST_CREATED", "REQUEST CREATED", {"CREATED"}),
        ("CONSENT_VERIFIED", "CONSENT VERIFIED", {"CONSENT_GRANTED"}),
        ("DATA_REQUESTED", "DATA REQUESTED", {"DATA_REQUESTED"}),
        ("DATA_RECEIVED", "DATA RECEIVED", {"DATA_RECEIVED"}),
        ("DATA_VALIDATED", "DATA VALIDATED", {"DATA_VALIDATED"}),
        ("DATA_NORMALIZED", "DATA NORMALIZED", {"DATA_NORMALIZED"}),
        ("APPLICATION_UPDATED", "APPLICATION UPDATED", {"APPLICATION_UPDATED"}),
        ("COMPLETED", "COMPLETED", {"COMPLETED"}),
    )
    event_timeline = []
    for key, label, matched_statuses in timeline_steps:
        event = next(
            (
                item
                for item in ordered_events
                if item.status.upper() in matched_statuses
            ),
            None,
        )
        event_timeline.append(
            {
                "key": key,
                "label": label,
                "status": "completed" if event else "pending",
                "occurredAt": event.occurred_at.isoformat()
                if event and event.occurred_at
                else None,
                "detail": event.detail if event else None,
            }
        )
    return {
        "transactionId": row.transaction_id,
        "source": (
            row.source_system.name if row.source_system else row.source_department
        ),
        "destination": (
            row.destination_system.name if row.destination_system else row.requesting_department
        ),
        "sourceDepartment": row.source_department,
        "requestingDepartment": row.requesting_department,
        "dataRequested": row.data_requested,
        "dataType": row.data_requested,
        "transactionType": row.transaction_type,
        "consent": row.consent_status,
        "apiStatus": row.request_status,
        "validation": row.validation_status,
        "mapping": row.mapping_status,
        "response": row.response_status,
        "result": row.response_status,
        "status": row.status,
        "transactionStatus": row.status,
        "applicationId": row.application_id,
        "applicationReference": (
            row.application.reference_id if row.application else None
        ),
        "consentId": row.consent_id,
        "startedAt": created_at,
        "timestamp": created_at,
        "createdAt": created_at,
        "completedAt": completed_at,
        "errorCode": row.error_code,
        "errorMessage": row.error_message,
        "timeline": event_timeline,
        "events": [
            {
                "state": event.status,
                "type": event.event_type,
                "detail": event.detail,
                "occurredAt": event.occurred_at.isoformat() if event.occurred_at else None,
            }
            for event in ordered_events
        ],
    }


@router.get("/exceptions", response_model=list[dict])
@router.get("/interoperability/exceptions", response_model=list[dict])
def list_exceptions(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[
        User,
        Depends(
            require_role(
                "department_officer", "interoperability_admin", "system_admin", "auditor"
            )
        ),
    ],
    limit: int = Query(20, ge=1, le=100),
):
    query = db.query(InteroperabilityException)
    if get_user_role_key(current_user) == "department_officer":
        if current_user.department_id is None:
            return []
        query = query.join(
            ServiceApplication,
            or_(
                InteroperabilityException.application_id
                == cast(ServiceApplication.id, String),
                InteroperabilityException.application_id
                == ServiceApplication.reference_id,
            ),
        ).filter(ServiceApplication.department_id == current_user.department_id)
    rows = query.order_by(InteroperabilityException.created_at.desc()).limit(limit).all()
    return [_exception_payload(db, row) for row in rows]


@router.post("/exceptions/{exception_id}/retry", response_model=dict)
@router.post("/interoperability/exceptions/{exception_id}/retry", response_model=dict)
def retry_exception(
    exception_id: int,
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
    exception = db.get(InteroperabilityException, exception_id)
    if exception is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Exception not found"
        )
    transaction = db.get(InteroperabilityTransaction, exception.transaction_id)
    application = (
        db.get(ServiceApplication, transaction.application_id)
        if transaction is not None
        else None
    )
    if transaction is None or application is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Exception is not linked to a retryable application transaction.",
        )
    if get_user_role_key(current_user) == "department_officer":
        if current_user.department_id is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Exception not found"
            )
        ensure_resource_access(
            current_user,
            citizen_id=transaction.citizen_id,
            department_id=application.department_id,
        )
    if exception.status == ExceptionStatus.RETRYING:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This exception is already being retried.",
        )
    if exception.status not in {
        ExceptionStatus.OPEN,
        ExceptionStatus.ESCALATED,
    }:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only open or escalated exceptions can be retried.",
        )
    try:
        return interoperability_service.engine.retry_exception(
            db, exception, actor=current_user
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        ) from exc


@router.post("/exceptions", response_model=dict)
@router.post("/interoperability/exceptions", response_model=dict)
def create_exception(
    payload: dict,
    db: Annotated[Session, Depends(get_db)],
    _admin: Annotated[
        User,
        Depends(
            require_role(
                "department_officer", "interoperability_admin", "system_admin"
            )
        ),
    ],
):
    if get_user_role_key(_admin) == "department_officer":
        application_id = str(payload.get("application_id") or "")
        application = (
            db.query(ServiceApplication)
            .filter(
                or_(
                    cast(ServiceApplication.id, String) == application_id,
                    ServiceApplication.reference_id == application_id,
                )
            )
            .first()
        )
        if application is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")
        ensure_resource_access(
            _admin,
            citizen_id=application.citizen_id,
            department_id=application.department_id,
        )
    exception = InteroperabilityException(
        application_id=str(payload.get("application_id") or ""),
        system=payload.get("system", "Unknown"),
        category=payload.get("category", "UNKNOWN"),
        message=payload.get("message", "Interoperability issue"),
        severity=payload.get("severity", "medium"),
        status=ExceptionStatus.OPEN,
        details=payload.get("details", {}),
    )
    db.add(exception)
    db.flush()
    application_id = payload.get("application_id")
    application = (
        db.query(ServiceApplication)
        .filter(
            or_(
                cast(ServiceApplication.id, String) == str(application_id),
                ServiceApplication.reference_id == str(application_id),
            )
        )
        .first()
        if application_id
        else None
    )
    record_audit(
        db,
        action="EXCEPTION_CREATED",
        resource_type="interoperability_exception",
        resource_id=exception.id,
        actor_id=_admin.id,
        actor_role=get_user_role_key(_admin),
        role_id=_admin.role_id,
        department_id=application.department_id
        if application
        else _admin.department_id,
        metadata={
            "category": exception.category,
            "severity": exception.severity,
            "application_id": exception.application_id,
        },
    )
    db.commit()
    db.refresh(exception)
    return {
        "id": exception.id,
        "exceptionId": exception.id,
        "applicationId": exception.application_id,
        "system": exception.system,
        "sourceSystem": exception.system,
        "category": exception.category,
        "type": exception.category,
        "message": exception.message,
        "severity": exception.severity,
        "status": _status_value(exception.status),
        "retryCount": exception.retry_count,
        "details": exception.details,
        "createdAt": exception.created_at.isoformat(),
        "updatedAt": exception.updated_at.isoformat() if exception.updated_at else None,
        "resolvedAt": exception.resolved_at.isoformat() if exception.resolved_at else None,
        "retryCount": exception.retry_count,
        "transactionId": _transaction_public_id(db, exception.transaction_id),
    }


@router.patch("/exceptions/{exception_id}", response_model=dict)
@router.patch("/interoperability/exceptions/{exception_id}", response_model=dict)
def update_exception(
    exception_id: int,
    payload: dict,
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
    row = db.query(InteroperabilityException).filter(InteroperabilityException.id == exception_id).first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exception not found")
    if get_user_role_key(current_user) == "department_officer":
        application = (
            db.query(ServiceApplication)
            .filter(
                or_(
                    cast(ServiceApplication.id, String) == row.application_id,
                    ServiceApplication.reference_id == row.application_id,
                )
            )
            .first()
        )
        if application is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exception not found")
        ensure_resource_access(
            current_user,
            citizen_id=application.citizen_id,
            department_id=application.department_id,
        )
    old_status = row.status
    if "status" in payload:
        if old_status == ExceptionStatus.RESOLVED:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A successfully resolved exception cannot be reopened.",
            )
        try:
            requested_status = ExceptionStatus(str(payload["status"]).upper())
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unsupported exception status: {payload['status']}") from exc
        if requested_status in {ExceptionStatus.RESOLVED, ExceptionStatus.RETRYING}:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Exceptions can only be resolved by a successful connector retry.",
            )
        row.status = requested_status
    if "message" in payload:
        row.message = payload["message"]
    if "details" in payload:
        row.details = payload["details"]
    if "notes" in payload:
        row.notes = payload["notes"]
    transaction = (
        db.query(InteroperabilityTransaction)
        .filter(InteroperabilityTransaction.id == row.transaction_id)
        .first()
        if row.transaction_id is not None
        else None
    )
    application = (
        db.query(ServiceApplication)
        .filter(ServiceApplication.id == row.service_application_id)
        .first()
        if row.service_application_id is not None
        else None
    )
    record_audit(
        db,
        action="EXCEPTION_UPDATED",
        resource_type="interoperability_exception",
        resource_id=row.id,
        actor_id=current_user.id,
        actor_role=get_user_role_key(current_user),
        role_id=current_user.role_id,
        department_id=application.department_id
        if application
        else current_user.department_id,
        transaction=transaction,
        metadata={
            "old_status": _status_value(old_status),
            "new_status": _status_value(row.status),
            "message_changed": "message" in payload,
            "notes_changed": "notes" in payload,
        },
    )
    db.commit()
    db.refresh(row)
    return {
        "id": row.id,
        "exceptionId": row.id,
        "applicationId": row.application_id,
        "system": row.system,
        "sourceSystem": row.system,
        "category": row.category,
        "type": row.category,
        "message": row.message,
        "severity": row.severity,
        "status": _status_value(row.status),
        "transactionId": _transaction_public_id(db, row.transaction_id),
        "retryCount": row.retry_count,
        "details": row.details,
        "updatedAt": row.updated_at.isoformat() if row.updated_at else None,
        "createdAt": row.created_at.isoformat() if row.created_at else None,
        "resolvedAt": row.resolved_at.isoformat() if row.resolved_at else None,
        "retryCount": row.retry_count,
        "transactionId": _transaction_public_id(db, row.transaction_id),
    }


def _exception_payload(
    db: Session, row: InteroperabilityException
) -> dict[str, Any]:
    return {
        "id": row.id,
        "exceptionId": row.id,
        "applicationId": row.application_id,
        "system": row.system,
        "sourceSystem": row.system,
        "category": row.category,
        "type": row.category,
        "message": row.message,
        "severity": row.severity,
        "status": _status_value(row.status),
        "transactionId": _transaction_public_id(db, row.transaction_id),
        "retryCount": row.retry_count,
        "details": row.details,
        "createdAt": row.created_at.isoformat() if row.created_at else None,
        "updatedAt": row.updated_at.isoformat() if row.updated_at else None,
        "resolvedAt": row.resolved_at.isoformat() if row.resolved_at else None,
    }


def _transaction_public_id(db: Session, transaction_id: int | None) -> str | None:
    if transaction_id is None:
        return None
    transaction = db.get(InteroperabilityTransaction, transaction_id)
    return transaction.transaction_id if transaction else None


def _status_value(value: ExceptionStatus | str) -> str:
    return value.value if isinstance(value, ExceptionStatus) else str(value).upper()
