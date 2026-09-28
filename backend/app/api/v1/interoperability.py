from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import String, cast, or_
from sqlalchemy.orm import Session

from app.api.deps import ensure_resource_access, get_user_role_key, require_role
from app.database import get_db
from app.models.application import ServiceApplication
from app.models.interoperability_exception import ExceptionStatus, InteroperabilityException
from app.models.transaction import InteroperabilityTransaction
from app.models.user import User
from app.api.deps import require_authenticated_user
from app.services.interoperability_service import interoperability_service

router = APIRouter(
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


@router.get("/integrations", response_model=list[dict])
def list_integrations(
    _admin: Annotated[
        User, Depends(require_role("interoperability_admin", "system_admin"))
    ],
):
    """Return the connected government systems available in demo mode."""
    return interoperability_service.get_demo_integrations()


@router.get("/integrations/{integration_id}", response_model=dict)
def get_integration(
    integration_id: str,
    _admin: Annotated[
        User, Depends(require_role("interoperability_admin", "system_admin"))
    ],
):
    integrations = interoperability_service.get_demo_integrations()
    for item in integrations:
        if item["id"] == integration_id:
            return item
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Integration not found")


@router.get("/integrations/{integration_id}/health", response_model=dict)
def health_for_integration(
    integration_id: str,
    _admin: Annotated[
        User, Depends(require_role("interoperability_admin", "system_admin"))
    ],
):
    integrations = interoperability_service.get_demo_integrations()
    for item in integrations:
        if item["id"] == integration_id:
            return {"status": "ok", "health": item["health"], "department": item["department"], "systemName": item["systemName"]}
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Integration not found")


@router.post("/interoperability/request", response_model=dict)
def request_interoperability(
    payload: InteroperabilityRequest,
    current_user: Annotated[User, Depends(require_authenticated_user)],
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
    rows = query.order_by(InteroperabilityTransaction.created_at.desc()).limit(100).all()
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
            )
        ),
    ],
):
    query = db.query(InteroperabilityTransaction).filter(
        InteroperabilityTransaction.transaction_id == transaction_id
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


def _transaction_payload(row: InteroperabilityTransaction) -> dict[str, Any]:
    created_at = row.created_at.isoformat() if row.created_at else None
    completed_at = row.completed_at.isoformat() if row.completed_at else None
    return {
        "transactionId": row.transaction_id,
        "requestingDepartment": row.requesting_department,
        "sourceDepartment": row.source_department,
        "dataRequested": row.data_requested,
        "consent": row.consent_status,
        "authentication": "VERIFIED",
        "apiStatus": row.request_status,
        "validation": row.validation_status,
        "mapping": row.mapping_status,
        "response": row.response_status,
        "audit": "RECORDED",
        "result": row.response_status,
        "status": row.response_status,
        "applicationId": row.application_id,
        "consentId": row.consent_id,
        "timestamp": created_at,
        "createdAt": created_at,
        "completedAt": completed_at,
    }


@router.get("/exceptions", response_model=list[dict])
@router.get("/interoperability/exceptions", response_model=list[dict])
def list_exceptions(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[
        User,
        Depends(
            require_role(
                "department_officer", "interoperability_admin", "system_admin"
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
    return [{
        "id": row.id,
        "applicationId": row.application_id,
        "system": row.system,
        "category": row.category,
        "message": row.message,
        "severity": row.severity,
        "status": row.status.value,
        "details": row.details,
        "createdAt": row.created_at.isoformat(),
        "updatedAt": row.updated_at.isoformat() if row.updated_at else None,
        "resolvedAt": row.resolved_at.isoformat() if row.resolved_at else None,
    } for row in rows]


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
    db.commit()
    db.refresh(exception)
    return {
        "id": exception.id,
        "applicationId": exception.application_id,
        "system": exception.system,
        "category": exception.category,
        "message": exception.message,
        "severity": exception.severity,
        "status": exception.status.value,
        "details": exception.details,
        "createdAt": exception.created_at.isoformat(),
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
    if "status" in payload:
        try:
            row.status = ExceptionStatus(payload["status"])
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unsupported exception status: {payload['status']}") from exc
    if "message" in payload:
        row.message = payload["message"]
    if "details" in payload:
        row.details = payload["details"]
    if "notes" in payload:
        row.notes = payload["notes"]
    db.commit()
    db.refresh(row)
    return {
        "id": row.id,
        "applicationId": row.application_id,
        "system": row.system,
        "category": row.category,
        "message": row.message,
        "severity": row.severity,
        "status": row.status.value,
        "details": row.details,
        "updatedAt": row.updated_at.isoformat() if row.updated_at else None,
    }
