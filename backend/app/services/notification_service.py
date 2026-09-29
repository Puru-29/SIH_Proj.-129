from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session, joinedload

from app.models.application import ServiceApplication
from app.models.notification import Notification
from app.models.transaction import InteroperabilityTransaction
from app.models.user import User, UserRole
from app.services.audit_service import record_audit

NOTIFICATION_EVENTS = {
    "APPLICATION_CREATED",
    "CONSENT_REQUIRED",
    "CONSENT_GRANTED",
    "DATA_VERIFIED",
    "DATA_CONFLICT",
    "APPLICATION_UPDATED",
    "APPLICATION_APPROVED",
    "APPLICATION_REJECTED",
    "EXCEPTION_OCCURRED",
}


class NotificationService:
    def create_event(
        self,
        db: Session,
        *,
        event_type: str,
        title: str,
        message: str,
        citizen_id: int | None = None,
        department_id: int | None = None,
        application_id: int | None = None,
        transaction_id: int | None = None,
    ) -> list[dict[str, Any]]:
        if event_type not in NOTIFICATION_EVENTS:
            raise ValueError(f"Unsupported notification event: {event_type}")

        application = (
            db.get(ServiceApplication, application_id)
            if application_id is not None
            else None
        )
        transaction = (
            db.get(InteroperabilityTransaction, transaction_id)
            if transaction_id is not None
            else None
        )
        if application is not None:
            department_id = department_id or application.department_id

        recipient_ids: set[int] = set()
        if citizen_id is not None:
            recipient_ids.add(citizen_id)
        if department_id is not None:
            if application and application.assigned_officer_id is not None:
                recipient_ids.add(application.assigned_officer_id)
            for user in (
                db.query(User)
                .options(joinedload(User.role_record))
                .filter(User.is_active.is_(True), User.department_id == department_id)
                .all()
            ):
                if self._role_key(user) == "department_officer":
                    recipient_ids.add(user.id)
        for user in (
            db.query(User)
            .options(joinedload(User.role_record))
            .filter(User.is_active.is_(True))
            .all()
        ):
            if self._role_key(user) in {"system_admin", "interoperability_admin"}:
                recipient_ids.add(user.id)

        results = []
        for recipient_id in sorted(recipient_ids):
            notification = Notification(
                recipient_id=recipient_id,
                application_id=application_id,
                transaction_id=transaction_id,
                notification_type=self._category(event_type),
                event_type=event_type,
                title=title,
                message=message,
                status="unread",
            )
            db.add(notification)
            db.flush()
            record_audit(
                db,
                action="NOTIFICATION_SENT",
                resource_type="notification",
                resource_id=notification.id,
                department_id=department_id,
                transaction=transaction,
                metadata={
                    "recipient_id": recipient_id,
                    "event_type": event_type,
                    "application_id": application_id,
                },
            )
            results.append(self.serialize(db, notification))
        return results

    def create_notification(
        self,
        *,
        citizen_id: int,
        title: str,
        message: str,
        kind: str = "Application",
        db: Session,
        application_id: int | None = None,
        transaction_id: int | None = None,
        event_type: str = "DATA_VERIFIED",
    ) -> dict[str, Any]:
        created = self.create_event(
            db,
            event_type=event_type,
            title=title,
            message=message,
            citizen_id=citizen_id,
            application_id=application_id,
            transaction_id=transaction_id,
        )
        citizen_notification = next(
            (item for item in created if item["recipient_id"] == citizen_id), None
        )
        if citizen_notification is None:
            raise RuntimeError("The requested citizen notification was not persisted.")
        return citizen_notification

    @staticmethod
    def serialize(db: Session, notification: Notification) -> dict[str, Any]:
        application = (
            db.get(ServiceApplication, notification.application_id)
            if notification.application_id is not None
            else None
        )
        transaction = (
            db.get(InteroperabilityTransaction, notification.transaction_id)
            if notification.transaction_id is not None
            else None
        )
        created_at = notification.created_at
        if created_at is None:
            db.refresh(notification, attribute_names=["created_at"])
            created_at = notification.created_at
        return {
            "id": notification.id,
            "recipient_id": notification.recipient_id,
            "event_type": notification.event_type,
            "title": notification.title,
            "message": notification.message,
            "notification_type": notification.notification_type,
            "created_at": created_at.isoformat() if created_at else None,
            "read_at": notification.read_at.isoformat() if notification.read_at else None,
            "read": notification.status == "read",
            "application_id": notification.application_id,
            "application_reference": (
                application.reference_id if application is not None else None
            ),
            "transaction_id": (
                transaction.transaction_id if transaction is not None else None
            ),
        }

    @staticmethod
    def _role_key(user: User) -> str:
        if user.role_record is not None:
            return user.role_record.key
        return {
            UserRole.CITIZEN: "citizen",
            UserRole.OFFICER: "department_officer",
            UserRole.ADMIN: "system_admin",
            UserRole.DEVELOPER: "interoperability_admin",
            UserRole.OPERATOR: "interoperability_admin",
            UserRole.AUDITOR: "auditor",
        }.get(user.role, "unknown")

    @staticmethod
    def _category(event_type: str) -> str:
        if event_type in {"CONSENT_REQUIRED", "CONSENT_GRANTED"}:
            return "Consent"
        if event_type in {"DATA_VERIFIED", "DATA_CONFLICT", "EXCEPTION_OCCURRED"}:
            return "System"
        return "Application"


notification_service = NotificationService()
