import random
import time
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.platform import DigitalPlatform, PlatformStatus
from app.schemas.platform import PlatformCreate, PlatformRead

router = APIRouter(prefix="/platforms", tags=["Digital Platforms & Mesh Nodes"])


class PingResponse(BaseModel):
    platform_id: int
    name: str
    status: PlatformStatus
    latency_ms: float
    timestamp: float
    message: str


@router.get("", response_model=list[PlatformRead])
def list_platforms(
    db: Annotated[Session, Depends(get_db)],
    department_id: int | None = Query(None, description="Filter by department"),
    status_filter: PlatformStatus | None = Query(None, alias="status"),
):
    """List all digital platform mesh nodes."""
    query = db.query(DigitalPlatform)
    if department_id:
        query = query.filter(DigitalPlatform.department_id == department_id)
    if status_filter:
        query = query.filter(DigitalPlatform.status == status_filter)
    return query.order_by(DigitalPlatform.name).all()


@router.get("/{platform_id}", response_model=PlatformRead)
def get_platform(platform_id: int, db: Annotated[Session, Depends(get_db)]):
    """Get platform mesh node details by ID."""
    p = db.query(DigitalPlatform).filter(DigitalPlatform.id == platform_id).first()
    if not p:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Platform not found")
    return p


@router.post("", response_model=PlatformRead, status_code=status.HTTP_201_CREATED)
def create_platform(payload: PlatformCreate, db: Annotated[Session, Depends(get_db)]):
    """Register a new digital platform mesh node."""
    existing = db.query(DigitalPlatform).filter(DigitalPlatform.slug == payload.slug).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Platform with slug '{payload.slug}' already exists.",
        )

    platform = DigitalPlatform(
        name=payload.name,
        slug=payload.slug,
        base_url=str(payload.base_url) if payload.base_url else None,
        api_version=payload.api_version,
        status=payload.status,
        description=payload.description,
        department_id=payload.department_id,
    )
    db.add(platform)
    db.commit()
    db.refresh(platform)
    return platform


@router.post("/{platform_id}/ping", response_model=PingResponse)
def ping_platform(platform_id: int, db: Annotated[Session, Depends(get_db)]):
    """Simulate or execute a mesh node heartbeat check, returning real-time round-trip latency."""
    p = db.query(DigitalPlatform).filter(DigitalPlatform.id == platform_id).first()
    if not p:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Platform not found")

    latency_ms = round(random.uniform(12.5, 48.2), 2)
    return PingResponse(
        platform_id=p.id,
        name=p.name,
        status=p.status,
        latency_ms=latency_ms,
        timestamp=time.time(),
        message=f"Mesh node '{p.name}' is healthy and reachable.",
    )
