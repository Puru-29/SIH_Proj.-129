from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload

from app.api.deps import require_authenticated_user, require_role
from app.database import get_db
from app.models.user import User
from app.models.workflow import Workflow
from app.schemas.workflow import WorkflowDefinitionCreate
from app.services.workflow_engine import WorkflowEngineError, workflow_engine

router = APIRouter(prefix="/workflows", tags=["Configurable Workflows"])


def serialize_workflow(workflow: Workflow) -> dict[str, Any]:
    return {
        "id": workflow.id,
        "workflow_id": workflow.id,
        "service_id": workflow.service_id,
        "application_id": workflow.application_id,
        "name": workflow.name,
        "version": workflow.version,
        "status": workflow.status,
        "required_records": workflow.required_records or [],
        "required_consents": workflow.required_consents or [],
        "departments": workflow.departments or [],
        "transitions": workflow.transitions or {},
        "sla_hours": workflow.sla_hours,
        "sla_due_at": workflow.sla_due_at,
        "steps": [
            {
                "step_id": step.step_key,
                "name": step.name,
                "department": step.department,
                "type": step.step_type,
                "order": step.sequence,
                "required": step.required,
                "action": step.action or {},
                "next_steps": step.next_steps or [],
                "status": step.status,
                "attempts": step.attempts,
                "detail": step.detail,
            }
            for step in workflow.steps
        ],
    }


@router.get("")
def list_workflows(
    db: Annotated[Session, Depends(get_db)],
    _current_user: Annotated[User, Depends(require_authenticated_user)],
    service_id: int | None = Query(default=None),
):
    query = db.query(Workflow).options(joinedload(Workflow.steps)).filter(
        Workflow.application_id.is_(None)
    )
    if service_id is not None:
        query = query.filter(Workflow.service_id == service_id)
    return [
        serialize_workflow(workflow)
        for workflow in query.order_by(
            Workflow.service_id, Workflow.version.desc()
        ).all()
    ]


@router.get("/{workflow_id}")
def get_workflow(
    workflow_id: int,
    db: Annotated[Session, Depends(get_db)],
    _current_user: Annotated[User, Depends(require_authenticated_user)],
):
    workflow = (
        db.query(Workflow)
        .options(joinedload(Workflow.steps))
        .filter(Workflow.id == workflow_id, Workflow.application_id.is_(None))
        .first()
    )
    if workflow is None:
        raise HTTPException(status_code=404, detail="Workflow definition not found.")
    return serialize_workflow(workflow)


@router.post("", status_code=status.HTTP_201_CREATED)
def create_workflow(
    payload: WorkflowDefinitionCreate,
    db: Annotated[Session, Depends(get_db)],
    _admin: Annotated[
        User, Depends(require_role("interoperability_admin", "system_admin"))
    ],
):
    try:
        workflow = workflow_engine.create_definition(
            db, payload, actor_id=_admin.id
        )
    except WorkflowEngineError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return serialize_workflow(workflow)


@router.put("/{workflow_id}")
def revise_workflow(
    workflow_id: int,
    payload: WorkflowDefinitionCreate,
    db: Annotated[Session, Depends(get_db)],
    _admin: Annotated[
        User, Depends(require_role("interoperability_admin", "system_admin"))
    ],
):
    current = (
        db.query(Workflow)
        .filter(Workflow.id == workflow_id, Workflow.application_id.is_(None))
        .first()
    )
    if current is None:
        raise HTTPException(status_code=404, detail="Workflow definition not found.")
    if current.service_id != payload.service_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="A workflow revision must keep the same service_id.",
        )
    try:
        workflow = workflow_engine.create_definition(
            db, payload, actor_id=_admin.id, audit_action="WORKFLOW_REVISED"
        )
    except WorkflowEngineError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return serialize_workflow(workflow)
