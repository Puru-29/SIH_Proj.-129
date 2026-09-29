from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, joinedload

from app.api.deps import require_role
from app.database import get_db
from app.models.platform import ConnectedSystem
from app.models.user import User
from app.services.system_health_service import check_system_health

router = APIRouter(prefix="/system", tags=["System"])


@router.get("/health", response_model=dict)
def get_system_health(
    db: Annotated[Session, Depends(get_db)],
    _user: Annotated[
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
):
    systems = (
        db.query(ConnectedSystem)
        .options(joinedload(ConnectedSystem.department))
        .order_by(ConnectedSystem.name)
        .all()
    )
    return check_system_health(db, systems)
