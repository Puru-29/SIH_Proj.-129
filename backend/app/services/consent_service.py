from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models.consent import ConsentDataItem, ConsentStatus, DataShareConsent
from app.models.platform import DigitalPlatform
from app.services.notification_service import notification_service
from app.services.audit_service import record_audit
from app.models.application import ServiceApplication
from app.services.workflow_engine import workflow_engine


class ConsentService:
    GRANT_DURATION = timedelta(hours=24)

    def create_request(
        self,
        db: Session,
        *,
        citizen_id: int,
        source_platform: DigitalPlatform,
        target_platform: DigitalPlatform,
        purpose: str,
        requested_data: str,
        requested_fields: list[str],
        application_id: int | None = None,
    ) -> DataShareConsent:
        if not purpose.strip() or not requested_data.strip():
            raise ValueError("Purpose and requested data must not be blank.")
        unique_fields = dict.fromkeys(
            field.strip() for field in requested_fields if field.strip()
        )
        if not unique_fields:
            raise ValueError("At least one requested data field is required.")
        if any(len(self._field_key(field)) > 120 for field in unique_fields):
            raise ValueError("Requested data field keys must be 120 characters or fewer.")
        if any(len(field) > 255 for field in unique_fields):
            raise ValueError("Requested data field descriptions must be 255 characters or fewer.")

        consent = DataShareConsent(
            purpose=purpose.strip(),
            status=ConsentStatus.PENDING,
            source_platform_id=source_platform.id,
            target_platform_id=target_platform.id,
            citizen_id=citizen_id,
            application_id=application_id,
            source_department_id=source_platform.department_id,
            requesting_department_id=target_platform.department_id,
            requested_data=requested_data.strip(),
        )
        db.add(consent)
        db.flush()

        db.add_all(
            ConsentDataItem(
                consent_id=consent.id,
                data_key=self._field_key(field),
                description=field,
            )
            for field in unique_fields
        )
        record_audit(
            db,
            action="CONSENT_REQUESTED",
            resource_type="data_share_consent",
            resource_id=consent.id,
            actor_id=citizen_id,
            actor_role="citizen",
            department_id=getattr(consent, "requesting_department_id", None),
            metadata={
                "application_id": application_id,
                "source_department_id": source_platform.department_id,
                "requesting_department_id": target_platform.department_id,
            },
        )
        notification_service.create_event(
            db,
            event_type="CONSENT_REQUIRED",
            citizen_id=citizen_id,
            department_id=target_platform.department_id,
            application_id=application_id,
            title="Data-sharing consent requested",
            message=(
                f"{target_platform.department.name} requests {requested_data} "
                f"from {source_platform.department.name} for {purpose}. "
                "Review and approve or reject this request."
            ),
        )
        db.commit()
        db.refresh(consent)
        return consent

    def approve(self, db: Session, consent_id: int, *, citizen_id: int) -> DataShareConsent:
        consent = self._get_for_decision(db, consent_id, citizen_id)
        if consent.status != ConsentStatus.PENDING:
            raise ValueError("Only pending consent requests can be approved.")
        now = datetime.now(timezone.utc)
        consent.status = ConsentStatus.GRANTED
        consent.granted_at = now
        consent.expires_at = now + self.GRANT_DURATION
        consent.revoked_at = None
        self._audit(
            db,
            consent,
            action="CONSENT_GRANTED",
            details="Citizen approved this data-sharing request.",
            actor_id=citizen_id,
        )
        notification_service.create_event(
            db,
            event_type="CONSENT_GRANTED",
            citizen_id=citizen_id,
            department_id=consent.requesting_department_id,
            application_id=consent.application_id,
            title="Data-sharing consent granted",
            message=(
                f"Your consent to share {consent.requested_data} for "
                f"{consent.purpose} is now active."
            ),
        )
        db.flush()
        if consent.application_id is not None:
            application = (
                db.query(ServiceApplication)
                .filter(ServiceApplication.id == consent.application_id)
                .first()
            )
            if application is not None and application.workflow_run is not None:
                consent_step = next(
                    (
                        step
                        for step in application.workflow_run.steps
                        if step.step_type == "CONSENT"
                        and step.status == "in_progress"
                    ),
                    None,
                )
                requirements = application.workflow_run.required_consents or []
                if consent_step is not None and workflow_engine._consent_requirements_met(
                    db, citizen_id, requirements
                ):
                    workflow_engine.transition_step(
                        db,
                        application,
                        consent_step.step_key,
                        next_status="completed",
                        actor_id=citizen_id,
                        detail="All required consent requests were approved by the citizen.",
                    )
        db.commit()
        db.refresh(consent)
        return consent

    def reject(self, db: Session, consent_id: int, *, citizen_id: int) -> DataShareConsent:
        consent = self._get_for_decision(db, consent_id, citizen_id)
        if consent.status != ConsentStatus.PENDING:
            raise ValueError("Only pending consent requests can be rejected.")
        consent.status = ConsentStatus.DENIED
        self._audit(
            db,
            consent,
            action="CONSENT_REJECTED",
            details="Citizen rejected this data-sharing request.",
            actor_id=citizen_id,
        )
        db.commit()
        db.refresh(consent)
        return consent

    def revoke(self, db: Session, consent_id: int, *, citizen_id: int) -> DataShareConsent:
        consent = self._get_for_decision(db, consent_id, citizen_id)
        if consent.status not in {
            ConsentStatus.PENDING,
            ConsentStatus.GRANTED,
            ConsentStatus.ACTIVE,
        }:
            raise ValueError("This consent is no longer revocable.")
        consent.status = ConsentStatus.REVOKED
        consent.revoked_at = datetime.now(timezone.utc)
        self._audit(
            db,
            consent,
            action="CONSENT_REVOKED",
            details="Citizen revoked this data-sharing request.",
            actor_id=citizen_id,
        )
        db.commit()
        db.refresh(consent)
        return consent

    @staticmethod
    def _get_for_decision(
        db: Session, consent_id: int, citizen_id: int
    ) -> DataShareConsent:
        consent = (
            db.query(DataShareConsent)
            .filter(
                DataShareConsent.id == consent_id,
                DataShareConsent.citizen_id == citizen_id,
            )
            .with_for_update()
            .first()
        )
        if consent is None:
            raise LookupError("Consent not found.")
        return consent

    @staticmethod
    def _audit(
        db: Session,
        consent: DataShareConsent,
        *,
        action: str,
        details: str,
        actor_id: int,
    ) -> None:
        record_audit(
            db,
            action=action,
            resource_type="data_share_consent",
            resource_id=consent.id,
            actor_id=actor_id,
            actor_role="citizen",
            department_id=getattr(consent, "requesting_department_id", None),
            metadata={"consent_status": consent.status.value},
            details=details,
        )

    @staticmethod
    def _field_key(field: str) -> str:
        return "_".join(field.strip().casefold().split())


consent_service = ConsentService()
