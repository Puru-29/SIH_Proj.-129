import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

import app.models
from app.database import Base
from app.models.application import ApplicationStatus, ServiceApplication
from app.models.department import Department
from app.models.platform import ConnectedSystem, PlatformStatus
from app.models.service import Service
from app.models.user import User, UserRole
from app.schemas.workflow import WorkflowDefinitionCreate
from app.services.workflow_engine import (
    SCHOLARSHIP_WORKFLOW,
    WorkflowEngine,
    WorkflowEngineError,
)


def _db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return Session(engine)


def _configured_service(db: Session, *, name: str = "General Service") -> Service:
    department = Department(name="Social Welfare", code="SW")
    db.add(department)
    db.flush()
    platform = ConnectedSystem(
        name="Social Welfare Gateway",
        slug="social-welfare-gateway",
        status=PlatformStatus.ACTIVE,
        department_id=department.id,
    )
    db.add(platform)
    db.flush()
    service = Service(
        name=name,
        code="GENERAL",
        department_id=department.id,
        platform_id=platform.id,
    )
    db.add(service)
    db.commit()
    return service


def test_scholarship_definition_uses_supported_steps_and_configured_transitions():
    definition = WorkflowDefinitionCreate.model_validate(
        {**SCHOLARSHIP_WORKFLOW, "service_id": 18}
    )

    assert {step.type.value for step in definition.steps} == {
        "CONSENT",
        "DATA_REQUEST",
        "DOCUMENT_UPLOAD",
        "DOCUMENT_VERIFICATION",
        "DATA_VALIDATION",
        "OFFICER_REVIEW",
        "APPROVAL",
        "REJECTION",
        "NOTIFICATION",
        "COMPLETION",
    }
    assert definition.transitions["officer_review"] == ["approval", "rejection"]
    assert definition.sla_hours is not None


def test_workflow_definition_rejects_unknown_transition_targets():
    config = {
        "service_id": 1,
        "name": "Invalid",
        "steps": [
            {
                "step_id": "review",
                "name": "Review",
                "type": "OFFICER_REVIEW",
                "order": 0,
                "next_steps": ["missing"],
            }
        ],
    }
    with pytest.raises(ValueError, match="defined steps"):
        WorkflowDefinitionCreate.model_validate(config)


def test_workflow_run_routes_branch_and_executes_notification():
    db = _db_session()
    try:
        service = _configured_service(db)
        department = db.get(Department, service.department_id)
        assert department is not None
        citizen = User(
            full_name="Test Citizen",
            email="workflow-citizen@example.test",
            role=UserRole.CITIZEN,
            hashed_password="unused",
            is_active=True,
        )
        db.add(citizen)
        db.flush()
        application = ServiceApplication(
            reference_id="APP-WORKFLOW-1",
            citizen_id=citizen.id,
            service_id=service.id,
            department_id=department.id,
            status=ApplicationStatus.SUBMITTED,
        )
        db.add(application)
        db.flush()
        engine = WorkflowEngine()
        definition = engine.ensure_definition(db, service)
        assert definition is not None
        run = engine.create_run(db, application, definition)
        db.commit()

        assert run.steps[0].step_type == "OFFICER_REVIEW"
        assert run.steps[0].status == "in_progress"

        with pytest.raises(WorkflowEngineError, match="Select one configured next_step"):
            engine.transition_step(
                db,
                application,
                "officer_review",
                next_status="completed",
                actor_id=citizen.id,
            )
        assert run.steps[0].status == "in_progress"

        engine.transition_step(
            db,
            application,
            "officer_review",
            next_status="completed",
            actor_id=citizen.id,
            next_step="approval",
        )
        engine.transition_step(
            db,
            application,
            "approval",
            next_status="completed",
            actor_id=citizen.id,
        )
        assert application.status == ApplicationStatus.APPROVED
        assert next(step for step in run.steps if step.step_key == "notification").status == "completed"
        completion = next(step for step in run.steps if step.step_key == "completion")
        assert completion.status == "in_progress"

        engine.transition_step(
            db,
            application,
            "completion",
            next_status="completed",
            actor_id=citizen.id,
        )
        assert run.status == "completed"
        assert db.query(app.models.Notification).filter_by(application_id=application.id).count() == 1
    finally:
        db.close()
