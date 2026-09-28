import uuid

from sqlalchemy import create_engine, inspect, event
from sqlalchemy.orm import Session, configure_mappers
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models import (
    ApplicationEvent,
    AuditLog,
    DataShareConsent,
    Department,
    DigitalPlatform,
    InteroperabilityTransaction,
    Role,
    Service,
    ServiceApplication,
    TransactionEvent,
    User,
    Workflow,
    WorkflowStep,
)
from app.models.application import ApplicationStatus
from app.models.consent import ConsentStatus
from app.models.platform import PlatformStatus
from app.models.user import UserRole


def make_engine():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, _record):
        cursor = connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return engine


def test_database_metadata_contains_relational_domain_tables_and_indexes():
    configure_mappers()
    required_tables = {
        "users",
        "auth_sessions",
        "roles",
        "departments",
        "services",
        "service_applications",
        "application_events",
        "government_records",
        "documents",
        "data_share_consents",
        "interoperability_transactions",
        "transaction_events",
        "data_mappings",
        "notifications",
        "audit_logs",
        "interoperability_exceptions",
        "connected_systems",
        "workflows",
        "workflow_steps",
    }
    assert required_tables <= set(Base.metadata.tables)

    engine = make_engine()
    Base.metadata.create_all(engine)
    inspector = inspect(engine)
    assert "workflow" not in {column["name"] for column in inspector.get_columns("service_applications")}
    assert {"citizen_id", "service_id", "department_id"} <= {
        column["name"] for column in inspector.get_columns("service_applications")
    }
    assert {
        "requested_at", "completed_at", "error_code", "error_message"
    } <= {column["name"] for column in inspector.get_columns("interoperability_transactions")}
    assert any(
        index["column_names"] == ["citizen_id"]
        for index in inspector.get_indexes("service_applications")
    )
    assert {
        "refresh_token_hash",
        "expires_at",
        "revoked_at",
        "last_used_at",
    } <= {column["name"] for column in inspector.get_columns("auth_sessions")}


def test_application_workflow_consent_and_transaction_events_are_relational():
    engine = make_engine()
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        role = Role(key="citizen", name="Citizen")
        department = Department(name="Revenue", code="REV")
        db.add_all([role, department])
        db.flush()

        source = DigitalPlatform(
            name="Revenue Records",
            slug="revenue-records",
            department_id=department.id,
            status=PlatformStatus.ACTIVE,
        )
        destination = DigitalPlatform(
            name="GovFlow Gateway",
            slug="govflow-gateway",
            department_id=department.id,
            status=PlatformStatus.ACTIVE,
        )
        db.add_all([source, destination])
        db.flush()

        user = User(
            full_name="Test Citizen",
            email="citizen@example.test",
            role=UserRole.CITIZEN,
            role_id=role.id,
            hashed_password="not-a-real-password",
        )
        service = Service(
            name="Income Certificate",
            code="INCOME",
            department_id=department.id,
            platform_id=destination.id,
        )
        db.add_all([user, service])
        db.flush()

        application = ServiceApplication(
            reference_id="APP-TEST-1",
            citizen_id=user.id,
            service_id=service.id,
            department_id=department.id,
            status=ApplicationStatus.SUBMITTED,
        )
        consent = DataShareConsent(
            purpose="Income verification",
            requested_data="Annual income",
            status=ConsentStatus.GRANTED,
            citizen_id=user.id,
            source_platform_id=source.id,
            target_platform_id=destination.id,
            source_department_id=department.id,
            requesting_department_id=department.id,
        )
        db.add_all([application, consent])
        db.flush()
        workflow = Workflow(
            service_id=service.id,
            application_id=application.id,
            name="Income certificate workflow",
        )
        workflow.steps.append(
            WorkflowStep(step_key="income-check", name="Income check", sequence=1)
        )
        transaction = InteroperabilityTransaction(
            application_id=application.id,
            citizen_id=user.id,
            consent_id=consent.id,
            source_system_id=source.id,
            destination_system_id=destination.id,
            transaction_type="record_request",
            status="completed",
            requesting_department="Revenue",
            source_department="Revenue",
            data_requested="Annual income",
            purpose="Income verification",
            consent_status="VERIFIED",
            request_status="SUCCESS",
            validation_status="PASSED",
            mapping_status="PASSED",
            response_status="SUCCESS",
        )
        db.add_all(
            [
                workflow,
                transaction,
                ApplicationEvent(
                    application_id=application.id,
                    event_type="submitted",
                    status="submitted",
                ),
            ]
        )
        db.flush()
        db.add(
            TransactionEvent(
                transaction_id=transaction.id,
                event_type="completed",
                status="success",
            )
        )
        db.commit()

        db.refresh(application)
        db.refresh(transaction)
        assert isinstance(user.public_id, uuid.UUID)
        assert isinstance(application.public_id, uuid.UUID)
        assert application.department_id == department.id
        assert application.workflow[0]["key"] == "income-check"
        assert transaction.events[0].event_type == "completed"
