from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.department import Department
from app.schemas.department import DepartmentCreate, DepartmentRead

router = APIRouter(prefix="/departments", tags=["Departments"])


@router.get("", response_model=list[DepartmentRead])
def list_departments(
    db: Annotated[Session, Depends(get_db)],
    state: str | None = Query(None, description="Filter by state"),
    search: str | None = Query(None, description="Search by name or code"),
):
    """List all registered government departments."""
    query = db.query(Department)
    if state:
        query = query.filter(Department.state.ilike(f"%{state}%"))
    if search:
        query = query.filter(
            (Department.name.ilike(f"%{search}%")) | (Department.code.ilike(f"%{search}%"))
        )
    return query.order_by(Department.name).all()


@router.get("/{department_id}", response_model=DepartmentRead)
def get_department(department_id: int, db: Annotated[Session, Depends(get_db)]):
    """Get single department details by ID."""
    dept = db.query(Department).filter(Department.id == department_id).first()
    if not dept:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Department not found")
    return dept


@router.post("", response_model=DepartmentRead, status_code=status.HTTP_201_CREATED)
def create_department(payload: DepartmentCreate, db: Annotated[Session, Depends(get_db)]):
    """Register a new department in the inter-governmental mesh."""
    existing = db.query(Department).filter(Department.code == payload.code).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Department with code '{payload.code}' already exists.",
        )

    dept = Department(
        name=payload.name,
        code=payload.code,
        description=payload.description,
        state=payload.state,
    )
    db.add(dept)
    db.commit()
    db.refresh(dept)
    return dept
