from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from app.database import SessionLocal
from app.models.audit import AuditLog
from app.models.consent import ConsentStatus, DataShareConsent
from app.models.platform import DigitalPlatform


class ConsentService:
    def create_consent(self, *, citizen_id: int, source_department: str, requesting_department: str, purpose: str) -> DataShareConsent:
        db = SessionLocal()
        try:
            source = db.query(DigitalPlatform).filter(
                DigitalPlatform.department.has(name=source_department)
            ).first()
            target = db.query(DigitalPlatform).filter(
                DigitalPlatform.department.has(name=requesting_department)
            ).first()
            if source is None or target is None:
                raise ValueError("Consent source and requesting department systems must be registered.")
            consent = DataShareConsent(
                purpose=purpose,
                status=ConsentStatus.PENDING,
                source_platform_id=source.id,
                target_platform_id=target.id,
                citizen_id=citizen_id,
                source_department_id=source.department_id,
                requesting_department_id=target.department_id,
                requested_data=purpose,
                expires_at=datetime.now(timezone.utc) + timedelta(days=30),
            )
            db.add(consent)
            db.commit()
            db.refresh(consent)
            db.add(AuditLog(
                action='CONSENT_REQUESTED',
                entity_type='consent',
                entity_id=str(consent.id),
                details=f"{requesting_department} requested consent to access {purpose} from {source_department}.",
                actor_id=citizen_id,
            ))
            db.commit()
            return consent
        finally:
            db.close()

    def approve_consent(self, consent_id: int) -> DataShareConsent:
        db = SessionLocal()
        try:
            consent = db.query(DataShareConsent).filter(DataShareConsent.id == consent_id).first()
            if not consent:
                raise ValueError('Consent not found')
            consent.status = ConsentStatus.GRANTED
            db.add(AuditLog(
                action='CONSENT_APPROVED',
                entity_type='consent',
                entity_id=str(consent.id),
                details='Citizen approved the consent request for data access.',
                actor_id=consent.citizen_id,
            ))
            db.commit()
            db.refresh(consent)
            return consent
        finally:
            db.close()

    def deny_consent(self, consent_id: int) -> DataShareConsent:
        db = SessionLocal()
        try:
            consent = db.query(DataShareConsent).filter(DataShareConsent.id == consent_id).first()
            if not consent:
                raise ValueError('Consent not found')
            consent.status = ConsentStatus.REVOKED
            db.add(AuditLog(
                action='CONSENT_DENIED',
                entity_type='consent',
                entity_id=str(consent.id),
                details='Citizen denied the consent request for data access.',
                actor_id=consent.citizen_id,
            ))
            db.commit()
            db.refresh(consent)
            return consent
        finally:
            db.close()


consent_service = ConsentService()
