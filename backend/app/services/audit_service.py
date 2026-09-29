from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session, joinedload

from app.models.audit import AuditLog
from app.models.transaction import InteroperabilityTransaction
from app.models.user import User, UserRole


def record_audit(
    db: Session,
    *,
    action: str,
    resource_type: str,
    resource_id: str | int,
    actor_id: int | None = None,
    actor_role: str | None = None,
    department_id: int | None = None,
    role_id: Any | None = None,
    transaction: InteroperabilityTransaction | None = None,
    result: str = "success",
    metadata: dict[str, Any] | None = None,
    details: str | None = None,
) -> AuditLog:
    """Stage an immutable audit event in the same transaction as the operation."""
    if actor_id is not None and actor_role is None:
        actor = (
            db.query(User)
            .options(joinedload(User.role_record))
            .filter(User.id == actor_id)
            .first()
        )
        if actor is not None:
            actor_role = actor_role or (
                actor.role_record.key
                if actor.role_record
                else {
                    UserRole.CITIZEN: "citizen",
                    UserRole.OFFICER: "department_officer",
                    UserRole.ADMIN: "system_admin",
                    UserRole.DEVELOPER: "interoperability_admin",
                    UserRole.OPERATOR: "interoperability_admin",
                    UserRole.AUDITOR: "auditor",
                }.get(actor.role, "unknown")
            )
            department_id = (
                department_id
                if department_id is not None
                else actor.department_id
            )
            role_id = role_id or actor.role_id
    entry = AuditLog(
        action=action,
        entity_type=resource_type,
        entity_id=str(resource_id),
        resource=resource_type,
        resource_id=str(resource_id),
        actor_id=actor_id,
        actor_role=actor_role,
        department_id=department_id,
        role_id=role_id,
        transaction_id=transaction.public_id if transaction else None,
        result=result,
        event_metadata=metadata or {},
        details=details,
    )
    db.add(entry)
    return entry
