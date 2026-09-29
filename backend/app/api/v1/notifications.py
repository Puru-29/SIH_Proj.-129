from datetime import datetime, timezone
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_user_role_key, require_authenticated_user, require_role
from app.database import get_db
from app.models.notification import Notification
from app.models.user import User
from app.services.audit_service import record_audit
from app.services.notification_service import notification_service

router = APIRouter(prefix="/notifications", tags=["Notifications"])

NOTIFICATION_ROLES = (
    "citizen",
    "department_officer",
    "interoperability_admin",
    "system_admin",
    "auditor",
)


@router.get("", response_model=list[dict[str, Any]])
def list_notifications(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role(*NOTIFICATION_ROLES))],
    limit: int = Query(100, ge=1, le=500),
):
    rows = (
        db.query(Notification)
        .filter(Notification.recipient_id == current_user.id)
        .order_by(Notification.created_at.desc(), Notification.id.desc())
        .limit(limit)
        .all()
    )
    return [notification_service.serialize(db, row) for row in rows]


@router.patch("/{notification_id}/read", response_model=dict[str, Any])
def mark_notification_read(
    notification_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[
        User, Depends(require_role(*NOTIFICATION_ROLES))
    ],
):
    notification = (
        db.query(Notification)
        .filter(
            Notification.id == notification_id,
            Notification.recipient_id == current_user.id,
        )
        .with_for_update()
        .first()
    )
    if notification is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found."
        )
    if notification.status != "read":
        notification.status = "read"
        notification.read_at = datetime.now(timezone.utc)
        record_audit(
            db,
            action="NOTIFICATION_READ",
            resource_type="notification",
            resource_id=notification.id,
            actor_id=current_user.id,
            actor_role=get_user_role_key(current_user),
            role_id=current_user.role_id,
            metadata={"event_type": notification.event_type},
        )
        db.commit()
        db.refresh(notification)
    return notification_service.serialize(db, notification)
