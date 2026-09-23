from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.service import Service
from app.schemas.service import ServiceCreate, ServiceRead
from app.services.service_config import SERVICE_NAMES, get_service_config

router = APIRouter(prefix="/services", tags=["Government Services"])


@router.get("", response_model=list[ServiceRead])
def list_services(
    db: Annotated[Session, Depends(get_db)],
    department_id: int | None = Query(None, description="Filter by department ID"),
    platform_id: int | None = Query(None, description="Filter by platform ID"),
    is_active: bool | None = Query(None, description="Filter by active status"),
):
    """List all interoperable public services available across mesh nodes."""
    query = db.query(Service).filter(Service.name.in_(SERVICE_NAMES))
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
    return get_service_config(svc)


@router.post("", response_model=ServiceRead, status_code=status.HTTP_201_CREATED)
def create_service(payload: ServiceCreate, db: Annotated[Session, Depends(get_db)]):
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
    db.commit()
    db.refresh(svc)
    return svc
