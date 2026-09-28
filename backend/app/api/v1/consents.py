from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any, Callable

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session, joinedload

from app.api.deps import (
    ensure_resource_access,
    get_user_role_key,
    require_authenticated_user,
    require_role,
)
from app.models.application import ServiceApplication
from app.database import get_db
from app.models.consent import ConsentStatus, DataShareConsent
from app.models.platform import DigitalPlatform
from app.models.user import User
from app.schemas.consent import ConsentDataItemRead
from app.schemas.consent import ConsentCreate
from app.services.consent_service import consent_service

router = APIRouter(prefix="/consents", tags=["Citizen Consent Management (DPDP Act)"])


class EnrichedConsentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    purpose: str
    status: ConsentStatus
    source_platform_id: int
    source_department_id: int | None = None
    source_platform_name: str | None = None
    target_platform_id: int
    requesting_department_id: int | None = None
    target_platform_name: str | None = None
    citizen_id: int
    application_id: int | None = None
    requested_data: str
    data_items: list[ConsentDataItemRead]
    citizen_name: str | None = None
    citizen_aadhaar_last4: str | None = None
    created_at: datetime
    granted_at: datetime | None = None
    expires_at: datetime | None = None
    revoked_at: datetime | None = None


def enrich_consent(consent: DataShareConsent) -> dict[str, Any]:
    return {
        "id": consent.id,
        "purpose": consent.purpose,
        "status": consent.status,
        "source_platform_id": consent.source_platform_id,
        "source_department_id": consent.source_department_id,
        "source_platform_name": (
            consent.source_platform.name if consent.source_platform else None
        ),
        "target_platform_id": consent.target_platform_id,
        "requesting_department_id": consent.requesting_department_id,
        "target_platform_name": (
            consent.target_platform.name if consent.target_platform else None
        ),
        "citizen_id": consent.citizen_id,
        "application_id": consent.application_id,
        "requested_data": consent.requested_data,
        "data_items": consent.data_items,
        "citizen_name": consent.citizen.full_name if consent.citizen else None,
        "citizen_aadhaar_last4": (
            consent.citizen.aadhaar_last4 if consent.citizen else None
        ),
        "created_at": consent.created_at,
        "granted_at": consent.granted_at,
        "expires_at": consent.expires_at,
        "revoked_at": consent.revoked_at,
    }


@router.get("", response_model=list[EnrichedConsentRead])
def list_consents(
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
    citizen_id: int | None = Query(None),
    status_filter: ConsentStatus | None = Query(None, alias="status"),
):
    query = db.query(DataShareConsent).options(
        joinedload(DataShareConsent.citizen),
        joinedload(DataShareConsent.source_platform),
        joinedload(DataShareConsent.target_platform),
        joinedload(DataShareConsent.data_items),
    )
    role_key = get_user_role_key(current_user)
    if role_key == "citizen":
        if citizen_id is not None and citizen_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Citizens may only view their own consents.",
            )
        citizen_id = current_user.id
    elif role_key == "department_officer":
        if current_user.department_id is None:
            return []
        query = query.filter(
            (DataShareConsent.requesting_department_id == current_user.department_id)
            | (DataShareConsent.source_department_id == current_user.department_id)
        )
    if citizen_id is not None:
        query = query.filter(DataShareConsent.citizen_id == citizen_id)
    if status_filter is not None:
        query = query.filter(DataShareConsent.status == status_filter)
    return [
        enrich_consent(consent)
        for consent in query.order_by(DataShareConsent.created_at.desc()).all()
    ]


@router.get("/{consent_id}", response_model=EnrichedConsentRead)
def get_consent(
    consent_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_authenticated_user)],
):
    consent = (
        db.query(DataShareConsent)
        .options(
            joinedload(DataShareConsent.citizen),
            joinedload(DataShareConsent.source_platform),
            joinedload(DataShareConsent.target_platform),
            joinedload(DataShareConsent.data_items),
        )
        .filter(DataShareConsent.id == consent_id)
        .first()
    )
    if consent is None:
        raise HTTPException(status_code=404, detail="Consent not found.")
    department_id = consent.requesting_department_id
    if (
        get_user_role_key(current_user) == "department_officer"
        and current_user.department_id == consent.source_department_id
    ):
        department_id = consent.source_department_id
    ensure_resource_access(
        current_user,
        citizen_id=consent.citizen_id,
        department_id=department_id,
    )
    return enrich_consent(consent)


@router.post("", response_model=EnrichedConsentRead, status_code=status.HTTP_201_CREATED)
def create_consent(
    payload: ConsentCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_authenticated_user)],
):
    if get_user_role_key(current_user) != "citizen" or current_user.id != payload.citizen_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the signed-in citizen may request data sharing.",
        )
    source = (
        db.query(DigitalPlatform)
        .filter(DigitalPlatform.id == payload.source_platform_id)
        .first()
    )
    target = (
        db.query(DigitalPlatform)
        .filter(DigitalPlatform.id == payload.target_platform_id)
        .first()
    )
    if source is None or target is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Source or target platform not found.",
        )
    if payload.application_id is not None:
        application_exists = (
            db.query(ServiceApplication.id)
            .filter(
                ServiceApplication.id == payload.application_id,
                ServiceApplication.citizen_id == current_user.id,
            )
            .first()
        )
        if application_exists is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Application not found for the signed-in citizen.",
            )
    try:
        consent = consent_service.create_request(
            db,
            citizen_id=current_user.id,
            source_platform=source,
            target_platform=target,
            purpose=payload.purpose,
            requested_data=payload.requested_data,
            requested_fields=payload.requested_fields,
            application_id=payload.application_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    return enrich_consent(consent)


def _decide_consent(
    consent_id: int,
    db: Session,
    current_user: User,
    action: Callable[..., DataShareConsent],
) -> dict[str, Any]:
    if get_user_role_key(current_user) != "citizen":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the citizen may decide their consent request.",
        )
    try:
        consent = action(db, consent_id, citizen_id=current_user.id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return enrich_consent(consent)


@router.post("/{consent_id}/approve", response_model=EnrichedConsentRead)
def approve_consent(
    consent_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_authenticated_user)],
):
    return _decide_consent(
        consent_id,
        db,
        current_user,
        consent_service.approve,
    )


@router.post("/{consent_id}/reject", response_model=EnrichedConsentRead)
def reject_consent(
    consent_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_authenticated_user)],
):
    return _decide_consent(
        consent_id,
        db,
        current_user,
        consent_service.reject,
    )


@router.post("/{consent_id}/revoke", response_model=EnrichedConsentRead)
def revoke_consent(
    consent_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_authenticated_user)],
):
    return _decide_consent(
        consent_id,
        db,
        current_user,
        consent_service.revoke,
    )
