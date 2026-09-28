from datetime import datetime, timezone
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.api.deps import ensure_resource_access, get_user_role_key, require_role
from app.api.deps import require_authenticated_user
from app.models.audit import AuditLog
from app.models.application import ServiceApplication
from app.models.consent import ConsentStatus, DataShareConsent
from app.models.platform import DigitalPlatform
from app.models.user import User
from app.schemas.consent import ConsentCreate

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
    citizen_name: str | None = None
    citizen_aadhaar_last4: str | None = None
    created_at: datetime
    expires_at: datetime | None


def enrich_consent(c: DataShareConsent) -> dict[str, Any]:
    return {
        "id": c.id,
        "purpose": c.purpose,
        "status": c.status,
        "source_platform_id": c.source_platform_id,
        "source_department_id": c.source_department_id,
        "source_platform_name": c.source_platform.name if c.source_platform else None,
        "target_platform_id": c.target_platform_id,
        "requesting_department_id": c.requesting_department_id,
        "target_platform_name": c.target_platform.name if c.target_platform else None,
        "citizen_id": c.citizen_id,
        "application_id": c.application_id,
        "requested_data": c.requested_data,
        "citizen_name": c.citizen.full_name if c.citizen else None,
        "citizen_aadhaar_last4": c.citizen.aadhaar_last4 if c.citizen else None,
        "created_at": c.created_at,
        "expires_at": c.expires_at,
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
    """List data share consents for DPDP audit compliance."""
    query = (
        db.query(DataShareConsent)
        .options(
            joinedload(DataShareConsent.citizen),
            joinedload(DataShareConsent.source_platform),
            joinedload(DataShareConsent.target_platform),
        )
    )
    role_key = get_user_role_key(current_user)
    if role_key == "citizen":
        if citizen_id is not None and citizen_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Citizens may only view their own consents.")
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
    if status_filter:
        query = query.filter(DataShareConsent.status == status_filter)

    consents = query.order_by(DataShareConsent.created_at.desc()).all()
    return [enrich_consent(c) for c in consents]


@router.get("/{consent_id}", response_model=EnrichedConsentRead)
def get_consent(
    consent_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_authenticated_user)],
):
    """Get consent details by ID."""
    c = (
        db.query(DataShareConsent)
        .options(
            joinedload(DataShareConsent.citizen),
            joinedload(DataShareConsent.source_platform),
            joinedload(DataShareConsent.target_platform),
        )
        .filter(DataShareConsent.id == consent_id)
        .first()
    )
    if not c:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Consent not found")
    scoped_department_id = c.requesting_department_id
    if (
        get_user_role_key(current_user) == "department_officer"
        and current_user.department_id == c.source_department_id
    ):
        scoped_department_id = c.source_department_id
    ensure_resource_access(
        current_user,
        citizen_id=c.citizen_id,
        department_id=scoped_department_id,
    )
    return enrich_consent(c)


@router.post("", response_model=EnrichedConsentRead, status_code=status.HTTP_201_CREATED)
def create_consent(
    payload: ConsentCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_authenticated_user)],
):
    """Record a citizen's decision for data sharing between two mesh nodes."""
    if get_user_role_key(current_user) != "citizen" or current_user.id != payload.citizen_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the signed-in citizen may record consent.",
        )
    if payload.status not in {ConsentStatus.PENDING, ConsentStatus.GRANTED, ConsentStatus.DENIED}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A citizen may only record a pending, granted, or denied consent decision.",
        )
    citizen = db.query(User).filter(User.id == payload.citizen_id).first()
    if not citizen:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Citizen not found")
    if payload.application_id is not None:
        application = (
            db.query(ServiceApplication)
            .filter(
                ServiceApplication.id == payload.application_id,
                ServiceApplication.citizen_id == current_user.id,
            )
            .first()
        )
        if application is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Application not found for the signed-in citizen.",
            )

    src = db.query(DigitalPlatform).filter(DigitalPlatform.id == payload.source_platform_id).first()
    tgt = db.query(DigitalPlatform).filter(DigitalPlatform.id == payload.target_platform_id).first()
    if not src or not tgt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Source or target platform not found"
        )

    consent = DataShareConsent(
        purpose=payload.purpose,
        status=payload.status,
        source_platform_id=payload.source_platform_id,
        target_platform_id=payload.target_platform_id,
        citizen_id=payload.citizen_id,
        application_id=payload.application_id,
        source_department_id=src.department_id,
        requesting_department_id=tgt.department_id,
        requested_data=payload.requested_data or payload.purpose,
        granted_at=datetime.now(timezone.utc) if payload.status == ConsentStatus.GRANTED else None,
        expires_at=payload.expires_at,
    )
    db.add(consent)
    db.flush()

    audit = AuditLog(
        action="CONSENT_GRANTED" if consent.status == ConsentStatus.GRANTED else "CONSENT_DENIED" if consent.status == ConsentStatus.DENIED else "CONSENT_REQUESTED",
        entity_type="data_share_consent",
        entity_id=str(consent.id),
        details=f"Consent #{consent.id} {consent.status.value} for '{payload.purpose}' from {src.name} to {tgt.name}",
        actor_id=citizen.id,
    )
    db.add(audit)
    db.commit()
    db.refresh(consent)

    return enrich_consent(consent)


@router.post("/{consent_id}/revoke", response_model=EnrichedConsentRead)
def revoke_consent(
    consent_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_authenticated_user)],
):
    """Revoke an active citizen data share consent immediately."""
    consent = (
        db.query(DataShareConsent)
        .options(
            joinedload(DataShareConsent.citizen),
            joinedload(DataShareConsent.source_platform),
            joinedload(DataShareConsent.target_platform),
        )
        .filter(DataShareConsent.id == consent_id)
        .first()
    )
    if not consent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Consent not found")
    if get_user_role_key(current_user) != "citizen" or consent.citizen_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Citizens may only revoke their own consents.")

    consent.status = ConsentStatus.REVOKED
    consent.revoked_at = datetime.now(timezone.utc)

    audit = AuditLog(
        action="CONSENT_REVOKED",
        entity_type="data_share_consent",
        entity_id=str(consent.id),
        details=f"Consent #{consent.id} ('{consent.purpose}') revoked by citizen",
        actor_id=consent.citizen_id,
    )
    db.add(audit)
    db.commit()
    db.refresh(consent)

    return enrich_consent(consent)


@router.post("/{consent_id}/status", response_model=EnrichedConsentRead)
def update_consent_status(
    consent_id: int,
    payload: dict,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_authenticated_user)],
):
    """Update the lifecycle state of a consent record."""
    consent = (
        db.query(DataShareConsent)
        .options(
            joinedload(DataShareConsent.citizen),
            joinedload(DataShareConsent.source_platform),
            joinedload(DataShareConsent.target_platform),
        )
        .filter(DataShareConsent.id == consent_id)
        .first()
    )
    if not consent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Consent not found")
    if get_user_role_key(current_user) != "citizen" or consent.citizen_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Citizens may only update their own consents.")

    new_status = payload.get("status")
    if not new_status:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="status is required")
    try:
        next_status = ConsentStatus(new_status)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unsupported consent status: {new_status}") from exc
    if next_status in {ConsentStatus.ACTIVE, ConsentStatus.EXPIRED}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Consent lifecycle state cannot be set directly.")
    if consent.status in {ConsentStatus.REVOKED, ConsentStatus.EXPIRED} and next_status != consent.status:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Revoked or expired consent cannot be changed.")
    consent.status = next_status
    if next_status == ConsentStatus.GRANTED:
        consent.granted_at = datetime.now(timezone.utc)
    elif next_status == ConsentStatus.REVOKED:
        consent.revoked_at = datetime.now(timezone.utc)

    db.add(AuditLog(
        action="CONSENT_STATUS_UPDATED",
        entity_type="data_share_consent",
        entity_id=str(consent.id),
        details=f"Consent #{consent.id} moved to {consent.status.value}",
        actor_id=consent.citizen_id,
    ))
    db.commit()
    db.refresh(consent)
    return enrich_consent(consent)
