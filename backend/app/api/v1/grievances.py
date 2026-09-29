from typing import Annotated, Any

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_user_role_key, require_role
from app.database import get_db
from app.models.grievance import Grievance
from app.models.user import User
from app.schemas.grievance import GrievanceCreate
from app.services.audit_service import record_audit

router = APIRouter(prefix="/grievances", tags=["Citizen Grievances"])


def serialize_grievance(grievance: Grievance) -> dict[str, Any]:
    return {
        "id": str(grievance.id),
        "category": grievance.category,
        "relatedApplication": grievance.related_application or "",
        "department": grievance.department or "",
        "description": grievance.description,
        "priority": grievance.priority,
        "status": grievance.status,
    }


@router.get("", response_model=list[dict[str, Any]])
def list_grievances(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role("citizen"))],
):
    grievances = (
        db.query(Grievance)
        .filter(Grievance.citizen_id == current_user.id)
        .order_by(Grievance.created_at.desc(), Grievance.id.desc())
        .all()
    )
    return [serialize_grievance(grievance) for grievance in grievances]


@router.post("", response_model=dict[str, Any], status_code=status.HTTP_201_CREATED)
def create_grievance(
    payload: GrievanceCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role("citizen"))],
):
    grievance = Grievance(
        citizen_id=current_user.id,
        category=payload.category,
        related_application=payload.related_application,
        department=payload.department,
        description=payload.description,
        priority=payload.priority,
        status="Submitted",
    )
    db.add(grievance)
    db.flush()
    record_audit(
        db,
        action="GRIEVANCE_SUBMITTED",
        resource_type="grievance",
        resource_id=grievance.id,
        actor_id=current_user.id,
        actor_role=get_user_role_key(current_user),
        role_id=current_user.role_id,
        metadata={"category": grievance.category, "priority": grievance.priority},
    )
    db.commit()
    db.refresh(grievance)
    return serialize_grievance(grievance)
