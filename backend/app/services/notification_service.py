from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.database import SessionLocal
from app.models.audit import AuditLog


class NotificationService:
    def create_notification(self, *, citizen_id: int, title: str, message: str, kind: str = "Application") -> dict[str, Any]:
        return {
            "id": f"NOT-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
            "citizen_id": citizen_id,
            "title": title,
            "message": message,
            "kind": kind,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "read": False,
        }


notification_service = NotificationService()
