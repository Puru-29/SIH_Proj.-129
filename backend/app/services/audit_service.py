from __future__ import annotations

from datetime import datetime, timezone

from app.database import SessionLocal
from app.models.audit import AuditLog


class AuditService:
    def log(self, *, action: str, entity_type: str, entity_id: str, details: str, actor_id: int | None = None) -> AuditLog:
        db = SessionLocal()
        try:
            entry = AuditLog(
                action=action,
                entity_type=entity_type,
                entity_id=entity_id,
                details=details,
                actor_id=actor_id,
            )
            db.add(entry)
            db.commit()
            db.refresh(entry)
            return entry
        finally:
            db.close()


audit_service = AuditService()
