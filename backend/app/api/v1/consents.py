from datetime import datetime, timezone
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models.audit import AuditLog
from app.models.consent import ConsentStatus, DataShareConsent
from app.models.platform import DigitalPlatform
from app.models.user import User
from app.schemas.consent import ConsentCreate, ConsentRead

router = APIRouter(prefix="/consents", tags=["Citizen Consent Management (DPDP Act)"])


class EnrichedConsentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    purpose: str
    status: ConsentStatus
    source_platform_id: int
    source_platform_name: str | None = None
    target_platform_id: int
    target_platform_name: str | None = None
    citizen_id: int
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
        "source_platform_name": c.source_platform.name if c.source_platform else None,
        "target_platform_id": c.target_platform_id,
        "target_platform_name": c.target_platform.name if c.target_platform else None,
        "citizen_id": c.citizen_id,
        "citizen_name": c.citizen.full_name if c.citizen else None,
        "citizen_aadhaar_last4": c.citizen.aadhaar_last4 if c.citizen else None,
        "created_at": c.created_at,
        "expires_at": c.expires_at,
    }


@router.get("", response_model=list[EnrichedConsentRead])
def list_consents(
    db: Annotated[Session, Depends(get_db)],
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

    if citizen_id:
        query = query.filter(DataShareConsent.citizen_id == citizen_id)
    if status_filter:
        query = query.filter(DataShareConsent.status == status_filter)

    consents = query.order_by(DataShareConsent.created_at.desc()).all()
    return [enrich_consent(c) for c in consents]


@router.get("/{consent_id}", response_model=EnrichedConsentRead)
def get_consent(consent_id: int, db: Annotated[Session, Depends(get_db)]):
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
    return enrich_consent(c)


@router.post("", response_model=EnrichedConsentRead, status_code=status.HTTP_201_CREATED)
def create_consent(payload: ConsentCreate, db: Annotated[Session, Depends(get_db)]):
    """Grant new citizen data share consent between two mesh nodes."""
    citizen = db.query(User).filter(User.id == payload.citizen_id).first()
    if not citizen:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Citizen not found")

    src = db.query(DigitalPlatform).filter(DigitalPlatform.id == payload.source_platform_id).first()
    tgt = db.query(DigitalPlatform).filter(DigitalPlatform.id == payload.target_platform_id).first()
    if not src or not tgt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Source or target platform not found"
        )

    consent = DataShareConsent(
        purpose=payload.purpose,
        status=ConsentStatus.GRANTED,
        source_platform_id=payload.source_platform_id,
        target_platform_id=payload.target_platform_id,
        citizen_id=payload.citizen_id,
        expires_at=payload.expires_at,
    )
    db.add(consent)
    db.flush()

    audit = AuditLog(
        action="CONSENT_GRANTED",
        entity_type="data_share_consent",
        entity_id=str(consent.id),
        details=f"Consent #{consent.id} granted for '{payload.purpose}' from {src.name} to {tgt.name}",
        actor_id=citizen.id,
    )
    db.add(audit)
    db.commit()
    db.refresh(consent)

    return enrich_consent(consent)


@router.post("/{consent_id}/revoke", response_model=EnrichedConsentRead)
def revoke_consent(consent_id: int, db: Annotated[Session, Depends(get_db)]):
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

    consent.status = ConsentStatus.REVOKED

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
