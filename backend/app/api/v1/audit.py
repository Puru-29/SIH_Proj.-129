from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.audit import AuditLog
from app.models.user import User
from app.schemas.audit import AuditLogCreate, AuditLogRead

router = APIRouter(prefix="/audit-logs", tags=["Audit Trail & Mesh Governance"])


class EnrichedAuditLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    action: str
    entity_type: str
    entity_id: str
    details: str | None
    actor_id: int | None
    actor_name: str | None = None
    created_at: datetime


@router.get("", response_model=list[EnrichedAuditLogRead])
def list_audit_logs(
    db: Annotated[Session, Depends(get_db)],
    action: str | None = Query(None, description="Filter by action code"),
    entity_type: str | None = Query(None, description="Filter by entity type"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """Retrieve immutable audit trail entries across inter-departmental mesh exchanges."""
    query = db.query(AuditLog)
    if action:
        query = query.filter(AuditLog.action.ilike(f"%{action}%"))
    if entity_type:
        query = query.filter(AuditLog.entity_type == entity_type)

    logs = query.order_by(AuditLog.created_at.desc()).offset(offset).limit(limit).all()

    # Pre-fetch actors for fast enrichment
    actor_ids = {l.actor_id for l in logs if l.actor_id}
    users = {u.id: u.full_name for u in db.query(User).filter(User.id.in_(actor_ids)).all()} if actor_ids else {}

    results: list[EnrichedAuditLogRead] = []
    for l in logs:
        results.append(
            EnrichedAuditLogRead(
                id=l.id,
                action=l.action,
                entity_type=l.entity_type,
                entity_id=l.entity_id,
                details=l.details,
                actor_id=l.actor_id,
                actor_name=users.get(l.actor_id, "System Automated" if not l.actor_id else f"User #{l.actor_id}"),
                created_at=l.created_at,
            )
        )
    return results


@router.post("", response_model=AuditLogRead, status_code=status.HTTP_201_CREATED)
def create_audit_log(payload: AuditLogCreate, db: Annotated[Session, Depends(get_db)]):
    """Record an audit log entry in the mesh journal."""
    log = AuditLog(
        action=payload.action,
        entity_type=payload.entity_type,
        entity_id=payload.entity_id,
        details=payload.details,
        actor_id=payload.actor_id,
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log
