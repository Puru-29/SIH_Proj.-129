from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.api.deps import get_user_role_key, require_role
from app.models.department import Department
from app.models.platform import DigitalPlatform
from app.models.service import Service
from app.models.user import User
from app.schemas.service import ServiceCreate, ServiceRead
from app.services.service_config import SERVICE_NAMES, get_service_config
from app.services.workflow_engine import workflow_engine
from app.services.audit_service import record_audit

router = APIRouter(prefix="/services", tags=["Government Services"])


@router.get("", response_model=list[ServiceRead])
def list_services(
    db: Annotated[Session, Depends(get_db)],
    department_id: int | None = Query(None, description="Filter by department ID"),
    platform_id: int | None = Query(None, description="Filter by platform ID"),
    is_active: bool | None = Query(None, description="Filter by active status"),
):
    """List all interoperable public services available across mesh nodes."""
    query = db.query(Service)
    if department_id is not None:
        query = query.filter(Service.department_id == department_id)
    if platform_id is not None:
        query = query.filter(Service.platform_id == platform_id)
    if is_active is not None:
        query = query.filter(Service.is_active == is_active)
    return query.order_by(Service.name).all()


@router.get("/{service_id}", response_model=ServiceRead)
def get_service(service_id: int, db: Annotated[Session, Depends(get_db)]):
    """Get single service details by ID."""
    svc = db.query(Service).filter(Service.id == service_id).first()
    if not svc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service not found")
    return svc


@router.get("/{service_id}/form-schema")
def get_service_form_schema(service_id: int, db: Annotated[Session, Depends(get_db)]):
    """Return the configurable citizen form and workflow for one service."""
    svc = db.query(Service).filter(Service.id == service_id, Service.is_active.is_(True)).first()
    if not svc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service not found")
    config = get_service_config(svc)
    definition = workflow_engine.ensure_definition(db, svc)
    if definition is not None:
        config["workflow"] = [step.name for step in definition.steps]
    return config


@router.get("/{service_id}/application-sources")
def get_service_application_sources(
    service_id: int,
    db: Annotated[Session, Depends(get_db)],
    _citizen: Annotated[User, Depends(require_role("citizen"))],
):
    """Return only platform IDs needed by this service's citizen data requests."""
    service = (
        db.query(Service)
        .filter(Service.id == service_id, Service.is_active.is_(True))
        .first()
    )
    if service is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service not found")

    definition = workflow_engine.ensure_definition(db, service)
    if definition is None:
        return []

    departments = [
        (
            department,
            "".join(
                character
                for character in department.name.casefold()
                if character.isalnum()
            ),
        )
        for department in db.query(Department).all()
    ]
    sources: list[dict[str, int | str]] = []
    seen_departments: set[int] = set()
    for step in definition.steps:
        if step.step_type != "DATA_REQUEST" or not step.department:
            continue
        step_department = "".join(
            character for character in step.department.casefold() if character.isalnum()
        )
        department = next(
            (
                item
                for item, compact_name in departments
                if compact_name
                and (compact_name in step_department or step_department in compact_name)
            ),
            None,
        )
        if department is None or department.id in seen_departments:
            continue
        platform = (
            db.query(DigitalPlatform)
            .filter(DigitalPlatform.department_id == department.id)
            .order_by(DigitalPlatform.name)
            .first()
        )
        if platform is None:
            continue
        sources.append(
            {
                "department": step.department,
                "department_id": department.id,
                "platform_id": platform.id,
            }
        )
        seen_departments.add(department.id)
    return sources


@router.post("", response_model=ServiceRead, status_code=status.HTTP_201_CREATED)
def create_service(
    payload: ServiceCreate,
    db: Annotated[Session, Depends(get_db)],
    _admin: Annotated[User, Depends(require_role("system_admin"))],
):
    """Register a new citizen service."""
    existing = db.query(Service).filter(Service.code == payload.code).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Service with code '{payload.code}' already exists.",
        )

    svc = Service(
        name=payload.name,
        code=payload.code,
        description=payload.description,
        is_active=payload.is_active,
        department_id=payload.department_id,
        platform_id=payload.platform_id,
    )
    db.add(svc)
    db.flush()
    record_audit(
        db,
        action="SERVICE_CREATED",
        resource_type="service",
        resource_id=svc.id,
        actor_id=_admin.id,
        actor_role=get_user_role_key(_admin),
        role_id=_admin.role_id,
        department_id=svc.department_id,
        metadata={"code": svc.code, "platform_id": svc.platform_id},
    )
    db.commit()
    db.refresh(svc)
    return svc
