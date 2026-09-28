from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.database import SessionLocal
from app.models.notification import Notification
from sqlalchemy.orm import Session


class NotificationService:
    def create_notification(
        self,
        *,
        citizen_id: int,
        title: str,
        message: str,
        kind: str = "Application",
        db: Session | None = None,
        application_id: int | None = None,
        transaction_id: int | None = None,
    ) -> dict[str, Any]:
        owns_session = db is None
        session = db or SessionLocal()
        try:
            notification = Notification(
                recipient_id=citizen_id,
                application_id=application_id,
                transaction_id=transaction_id,
                notification_type=kind,
                title=title,
                message=message,
                status="unread",
            )
            session.add(notification)
            if owns_session:
                session.commit()
                session.refresh(notification)
            else:
                session.flush()
            return {
                "id": notification.id,
                "citizen_id": citizen_id,
                "title": title,
                "message": message,
                "kind": kind,
                "created_at": (
                    notification.created_at.isoformat()
                    if notification.created_at
                    else datetime.now(timezone.utc).isoformat()
                ),
                "read": False,
            }
        finally:
            if owns_session:
                session.close()


notification_service = NotificationService()
