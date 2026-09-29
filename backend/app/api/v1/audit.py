from datetime import date, datetime, time, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import String, cast, or_
from sqlalchemy.orm import Session

from app.api.deps import get_user_role_key, require_role
from app.database import get_db
from app.models.audit import AuditLog
from app.models.transaction import InteroperabilityTransaction
from app.models.user import User
from app.schemas.audit import AuditLogRead

router = APIRouter(prefix="/audit-logs", tags=["Audit Trail & Mesh Governance"])


def _audit_payload(
    row: AuditLog, actor_name: str | None, transaction_id: str | None
) -> AuditLogRead:
    return AuditLogRead(
        id=row.id,
        timestamp=row.occurred_at,
        actor_id=row.actor_id,
        actor_role=row.actor_role,
        department_id=row.department_id,
        action=row.action,
        resource_type=row.resource
        if row.resource and row.resource != "unknown"
        else row.entity_type,
        resource_id=row.resource_id or row.entity_id,
        transaction_id=transaction_id
        or (str(row.transaction_id) if row.transaction_id else None),
        result=row.result,
        metadata=row.event_metadata or {},
        details=row.details,
        actor_name=actor_name,
    )


@router.get("", response_model=list[AuditLogRead])
def list_audit_logs(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[
        User,
        Depends(
            require_role(
                "department_officer",
                "interoperability_admin",
                "system_admin",
                "auditor",
            )
        ),
    ],
    log_date: date | None = Query(None, alias="date"),
    actor: int | None = Query(None, ge=1),
    department: int | None = Query(None, ge=1),
    action: str | None = Query(None, min_length=1, max_length=120),
    transaction: str | None = Query(None, min_length=1, max_length=100),
    resource: str | None = Query(None, min_length=1, max_length=160),
    result: str | None = Query(None, min_length=1, max_length=32),
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """Return append-only audit entries, scoped to the caller's department."""
    role = get_user_role_key(current_user)
    query = db.query(AuditLog)
    if role == "department_officer":
        if current_user.department_id is None:
            return []
        query = query.filter(AuditLog.department_id == current_user.department_id)
    if actor is not None:
        query = query.filter(AuditLog.actor_id == actor)
    if department is not None:
        query = query.filter(AuditLog.department_id == department)
    if action:
        query = query.filter(AuditLog.action.ilike(action.strip()))
    if result:
        query = query.filter(AuditLog.result.ilike(result.strip()))
    if log_date:
        start = datetime.combine(log_date, time.min, tzinfo=timezone.utc)
        query = query.filter(
            AuditLog.occurred_at >= start,
            AuditLog.occurred_at < start + timedelta(days=1),
        )
    if start_date:
        query = query.filter(
            AuditLog.occurred_at
            >= datetime.combine(start_date, time.min, tzinfo=timezone.utc)
        )
    if end_date:
        query = query.filter(
            AuditLog.occurred_at
            < datetime.combine(end_date + timedelta(days=1), time.min, tzinfo=timezone.utc)
        )
    if resource:
        search = f"%{resource.strip()}%"
        query = query.filter(
            or_(
                AuditLog.resource.ilike(search),
                AuditLog.entity_type.ilike(search),
                AuditLog.resource_id.ilike(search),
                AuditLog.entity_id.ilike(search),
            )
        )
    if transaction:
        matching = (
            db.query(InteroperabilityTransaction.public_id)
            .filter(
                or_(
                    InteroperabilityTransaction.transaction_id == transaction,
                    cast(InteroperabilityTransaction.id, String) == transaction,
                    cast(InteroperabilityTransaction.public_id, String) == transaction,
                )
            )
            .first()
        )
        if matching is None:
            return []
        query = query.filter(AuditLog.transaction_id == matching[0])

    rows = (
        query.order_by(AuditLog.occurred_at.desc(), AuditLog.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    actor_ids = {row.actor_id for row in rows if row.actor_id is not None}
    transaction_public_ids = {
        row.transaction_id for row in rows if row.transaction_id is not None
    }
    names = (
        {
            user.id: user.full_name
            for user in db.query(User).filter(User.id.in_(actor_ids)).all()
        }
        if actor_ids
        else {}
    )
    transaction_ids = (
        {
            transaction.public_id: transaction.transaction_id
            for transaction in db.query(InteroperabilityTransaction)
            .filter(InteroperabilityTransaction.public_id.in_(transaction_public_ids))
            .all()
        }
        if transaction_public_ids
        else {}
    )
    return [
        _audit_payload(
            row,
            names.get(row.actor_id),
            transaction_ids.get(row.transaction_id),
        )
        for row in rows
    ]
