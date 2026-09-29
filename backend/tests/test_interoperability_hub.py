from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import joinedload, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import require_authenticated_user
from app.database import Base, get_db
from app.main import app
from app.models import (
    AuditLog,
    DataMapping,
    DataMappingRule,
    Department,
    DigitalPlatform,
    InteroperabilityException,
    InteroperabilityTransaction,
    Service,
    ServiceApplication,
    TransactionEvent,
    User,
)
from app.models.application import ApplicationStatus
from app.models.consent import ConsentStatus, DataShareConsent
from app.models.interoperability_exception import ExceptionStatus
from app.models.platform import PlatformStatus
from app.models.notification import Notification
from app.models.user import UserRole
from app.services.audit_service import record_audit
from app.services.interoperability.exception_service import exception_type
from app.services.interoperability_service import interoperability_service
from app.services.notification_service import notification_service


@pytest.fixture
def hub_client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    sessions = sessionmaker(autoflush=False, bind=engine, expire_on_commit=False)
    with sessions() as db:
        revenue = Department(name="Revenue", code="REV")
        education = Department(name="Education", code="EDU")
        db.add_all([revenue, education])
        db.flush()

        source_system = DigitalPlatform(
            name="Revenue Registry",
            slug="revenue-registry",
            department_id=revenue.id,
            status=PlatformStatus.ACTIVE,
        )
        destination_system = DigitalPlatform(
            name="Education Registry",
            slug="education-registry",
            department_id=education.id,
            status=PlatformStatus.ACTIVE,
        )
        citizen = User(
            full_name="Test Citizen",
            email="hub-test@example.test",
            role=UserRole.CITIZEN,
            hashed_password="unused",
        )
        officer = User(
            full_name="Test Administrator",
            email="hub-admin@example.test",
            role=UserRole.ADMIN,
            hashed_password="unused",
        )
        db.add_all([source_system, destination_system, citizen, officer])
        db.flush()
        officer.role_record = None

        service = Service(
            name="Scholarship",
            code="HUB-SCHOLARSHIP",
            department_id=education.id,
            platform_id=destination_system.id,
        )
        db.add(service)
        db.flush()

        application = ServiceApplication(
            reference_id="HUB-APP-1001",
            status=ApplicationStatus.UNDER_REVIEW,
            citizen_id=citizen.id,
            service_id=service.id,
            department_id=education.id,
        )
        db.add(application)
        db.flush()

        consent = DataShareConsent(
            purpose="Income record Scholarship verification",
            status=ConsentStatus.GRANTED,
            source_platform_id=source_system.id,
            target_platform_id=destination_system.id,
            citizen_id=citizen.id,
            application_id=application.id,
            source_department_id=revenue.id,
            requesting_department_id=education.id,
            requested_data="Income record",
            granted_at=datetime.now(timezone.utc) - timedelta(minutes=1),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        )
        db.add(consent)
        db.flush()

        requested_at = datetime.now(timezone.utc) - timedelta(seconds=2)
        completed_at = requested_at + timedelta(milliseconds=850)
        transaction = InteroperabilityTransaction(
            transaction_id="TXN-HUB-1001",
            application_id=application.id,
            citizen_id=citizen.id,
            consent_id=consent.id,
            source_system_id=source_system.id,
            destination_system_id=destination_system.id,
            transaction_type="government_record_request",
            status="COMPLETED",
            requested_at=requested_at,
            completed_at=completed_at,
            requesting_department=education.name,
            source_department=revenue.name,
            data_requested="Income record",
            purpose="Scholarship verification",
            consent_status="GRANTED",
            request_status="SUCCESS",
            validation_status="PASSED",
            mapping_status="PASSED",
            response_status="SUCCESS",
        )
        db.add(transaction)
        db.flush()
        timeline_states = (
            "CREATED",
            "CONSENT_GRANTED",
            "DATA_REQUESTED",
            "DATA_RECEIVED",
            "DATA_VALIDATED",
            "DATA_NORMALIZED",
            "APPLICATION_UPDATED",
            "COMPLETED",
        )
        db.add_all(
            TransactionEvent(
                transaction_id=transaction.id,
                event_type=state.lower(),
                status=state,
                detail=f"Persisted {state} event",
                occurred_at=requested_at + timedelta(milliseconds=index * 100),
            )
            for index, state in enumerate(timeline_states)
        )
        mapping = DataMapping(
            source_system_id=source_system.id,
            target_system_id=destination_system.id,
            name="Revenue to Education",
            source="Revenue Registry",
            target="Education Registry",
            status="active",
            version=2,
        )
        db.add(mapping)
        db.flush()
        db.add_all(
            [
                DataMappingRule(
                    mapping_id=mapping.id,
                    source_field="full_name",
                    target_field="name",
                    is_required=True,
                ),
                DataMappingRule(
                    mapping_id=mapping.id,
                    source_field="dob",
                    target_field="date_of_birth",
                    is_required=True,
                ),
                DataMappingRule(
                    mapping_id=mapping.id,
                    source_field="income_certificate_no",
                    target_field="identifier",
                    is_required=True,
                ),
                DataMappingRule(
                    mapping_id=mapping.id,
                    source_field="annual_income",
                    target_field="annual_income",
                    is_required=False,
                ),
            ]
        )
        db.add(
            InteroperabilityException(
                application_id=application.reference_id,
                service_application_id=application.id,
                transaction_id=transaction.id,
                system=source_system.name,
                category="CONNECTOR_FAILURE",
                message="Example stored exception",
                severity="medium",
                status=ExceptionStatus.OPEN,
            )
        )
        record_audit(
            db,
            action="DATA_RECEIVED",
            resource_type="interoperability_transaction",
            resource_id=transaction.transaction_id,
            actor_id=officer.id,
            actor_role="system_admin",
            department_id=education.id,
            transaction=transaction,
            metadata={"status": "DATA_RECEIVED"},
        )
        db.commit()
        authenticated_user = officer

    def override_get_db():
        with sessions() as db:
            yield db

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[require_authenticated_user] = lambda: authenticated_user
    app.state.test_sessions = sessions
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(require_authenticated_user, None)
        del app.state.test_sessions
        engine.dispose()


def test_interoperability_hub_endpoints_return_database_records(hub_client):
    integrations = hub_client.get("/api/v1/integrations")
    assert integrations.status_code == 200
    source_metrics = next(
        system for system in integrations.json() if system["slug"] == "revenue-registry"
    )
    assert source_metrics["connectionStatus"] == "connected"
    assert source_metrics["healthStatus"] == "active"
    assert source_metrics["responseTimeMs"] is not None
    assert source_metrics["responseTimeMs"] >= 0
    assert source_metrics["transactionResponseTimeMs"] == 850
    assert source_metrics["lastSuccessfulRequestAt"]
    assert source_metrics["status"] == "healthy"
    assert source_metrics["failureCount"] == 0
    assert source_metrics["transactionCount"] == 1
    assert source_metrics["failedTransactionCount"] == 0

    health = hub_client.get(
        f"/api/v1/integrations/{source_metrics['id']}/health"
    )
    assert health.status_code == 200
    assert health.json()["slug"] == "revenue-registry"
    assert health.json()["status"] == "healthy"
    assert health.json()["response_time"] >= 0
    unversioned_health = hub_client.get(
        f"/api/integrations/{source_metrics['id']}/health"
    )
    assert unversioned_health.status_code == 200
    assert unversioned_health.json()["status"] == "healthy"

    transactions = hub_client.get("/api/v1/interoperability/transactions")
    assert transactions.status_code == 200
    assert transactions.json()[0]["applicationReference"] == "HUB-APP-1001"

    detail = hub_client.get(
        "/api/v1/interoperability/transactions/TXN-HUB-1001"
    )
    assert detail.status_code == 200
    assert [step["label"] for step in detail.json()["timeline"]] == [
        "REQUEST CREATED",
        "CONSENT VERIFIED",
        "DATA REQUESTED",
        "DATA RECEIVED",
        "DATA VALIDATED",
        "DATA NORMALIZED",
        "APPLICATION UPDATED",
        "COMPLETED",
    ]
    assert all(step["status"] == "completed" for step in detail.json()["timeline"])

    mappings = hub_client.get("/api/v1/data-mappings")
    assert mappings.status_code == 200
    assert mappings.json()[0]["name"] == "Revenue to Education"

    exceptions = hub_client.get("/api/v1/exceptions")
    assert exceptions.status_code == 200
    assert exceptions.json()[0]["message"] == "Example stored exception"
    exception = exceptions.json()[0]
    assert exception["exceptionId"] == exception["id"]
    assert exception["transactionId"] == "TXN-HUB-1001"
    assert exception["sourceSystem"] == "Revenue Registry"
    assert exception["type"] == "CONNECTOR_FAILURE"
    assert exception["status"] == "OPEN"
    assert exception["retryCount"] == 0


def test_system_health_executes_and_persists_connector_checks(hub_client, monkeypatch):
    system = next(
        item
        for item in hub_client.get("/api/v1/integrations").json()
        if item["slug"] == "revenue-registry"
    )
    with hub_client.app.state.test_sessions() as db:
        connected_system = db.query(DigitalPlatform).filter_by(id=system["id"]).one()
        connector = interoperability_service.engine.connector_for_system(
            connected_system
        )
        assert connector is not None

    monkeypatch.setattr(
        connector,
        "health_check",
        lambda: {"status": "offline", "message": "source is unreachable"},
    )
    response = hub_client.get("/api/system/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "degraded"
    failed_health = next(
        item for item in body["integrations"] if item["system_name"] == "Revenue Registry"
    )
    assert failed_health["status"] == "degraded"
    assert failed_health["last_failure"]
    assert failed_health["failure_count"] >= 1
    sessions = hub_client.app.state.test_sessions
    with sessions() as db:
        from app.models.integration_health_check import IntegrationHealthCheck

        assert (
            db.query(IntegrationHealthCheck)
            .filter(IntegrationHealthCheck.system_id == system["id"])
            .count()
            >= 2
        )


def test_education_gateway_resolves_by_connector_mapping_key():
    system = SimpleNamespace(
        name="Education Records Gateway",
        slug="education-records-mh",
        department=SimpleNamespace(name="Education Department"),
    )

    connector = interoperability_service.engine.connector_for_system(system)

    assert connector is not None
    assert connector.mapping_key == "education"


def test_notifications_are_persisted_scoped_and_linked_to_resources(hub_client):
    sessions = hub_client.app.state.test_sessions
    with sessions() as db:
        citizen = db.query(User).filter(User.email == "hub-test@example.test").one()
        application = (
            db.query(ServiceApplication)
            .filter(ServiceApplication.reference_id == "HUB-APP-1001")
            .one()
        )
        transaction = (
            db.query(InteroperabilityTransaction)
            .filter(InteroperabilityTransaction.transaction_id == "TXN-HUB-1001")
            .one()
        )
        officer = db.query(User).filter(User.email == "hub-admin@example.test").one()
        created = notification_service.create_event(
            db,
            event_type="DATA_VERIFIED",
            title="Record verified",
            message="Income data was verified.",
            citizen_id=citizen.id,
            application_id=application.id,
            transaction_id=transaction.id,
        )
        db.commit()
        citizen_notification = next(
            item for item in created if item["recipient_id"] == citizen.id
        )
        citizen_id = citizen.id
        notification_id = citizen_notification["id"]

    officer_notifications = hub_client.get("/api/v1/notifications")
    assert officer_notifications.status_code == 200
    assert all(item["recipient_id"] != citizen_id for item in officer_notifications.json())

    denied_read = hub_client.patch(
        f"/api/v1/notifications/{notification_id}/read"
    )
    assert denied_read.status_code == 404

    with sessions() as db:
        citizen = (
            db.query(User)
            .options(joinedload(User.role_record))
            .filter(User.id == citizen_id)
            .one()
        )
        assert citizen is not None
    hub_client.app.dependency_overrides[require_authenticated_user] = lambda: citizen
    try:
        citizen_notifications = hub_client.get("/api/v1/notifications")
        assert citizen_notifications.status_code == 200
        notification = next(
            item
            for item in citizen_notifications.json()
            if item["id"] == notification_id
        )
        assert notification["application_reference"] == "HUB-APP-1001"
        assert notification["transaction_id"] == "TXN-HUB-1001"
        assert notification["event_type"] == "DATA_VERIFIED"
        assert notification["read"] is False

        marked_read = hub_client.patch(
            f"/api/v1/notifications/{notification_id}/read"
        )
        assert marked_read.status_code == 200
        assert marked_read.json()["read"] is True
    finally:
        hub_client.app.dependency_overrides[require_authenticated_user] = lambda: officer

    with sessions() as db:
        persisted = db.get(Notification, notification_id)
        assert persisted is not None
        assert persisted.status == "read"
        assert persisted.read_at is not None
        assert (
            db.query(AuditLog)
            .filter(
                AuditLog.action == "NOTIFICATION_READ",
                AuditLog.resource_id == str(notification_id),
            )
            .count()
            == 1
        )
def test_exception_retry_reexecutes_connector_and_keeps_failures_open(
    hub_client, monkeypatch
):
    monkeypatch.setattr(
        "app.services.interoperability.engine.settings.data_mode", "demo"
    )

    def unavailable_connector(*_args):
        raise TimeoutError("Revenue connector timed out")

    monkeypatch.setattr(
        interoperability_service.engine, "source_fetcher", unavailable_connector
    )
    response = hub_client.post("/api/v1/exceptions/1/retry")
    assert response.status_code == 200
    result = response.json()
    assert result["status"] == "failure"
    assert result["exception"]["status"] == "OPEN"
    assert result["exception"]["retryCount"] == 1
    assert result["exception"]["type"] == "TIMEOUT"

    with hub_client.app.state.test_sessions() as db:
        transaction = (
            db.query(InteroperabilityTransaction)
            .filter(InteroperabilityTransaction.transaction_id == "TXN-HUB-1001")
            .one()
        )
        exception = db.query(InteroperabilityException).one()
        assert transaction.status == "FAILED"
        assert exception.status == "OPEN"
        assert exception.retry_count == 1
        assert exception.message == "Revenue connector timed out"
        assert (
            db.query(TransactionEvent)
            .filter(
                TransactionEvent.transaction_id == transaction.id,
                TransactionEvent.status == "FAILED",
            )
            .count()
            == 1
        )
        retry_audit = (
            db.query(AuditLog)
            .filter(AuditLog.action == "EXCEPTION_RETRIED")
            .one()
        )
        assert retry_audit.result == "failure"


def test_successful_exception_retry_updates_transaction_and_application(
    hub_client, monkeypatch
):
    monkeypatch.setattr(
        "app.services.interoperability.engine.settings.data_mode", "demo"
    )

    class RetryConnector:
        mapping_key = "revenue"

        @staticmethod
        def verify_record(_citizen_id, _record):
            return True

    engine = interoperability_service.engine
    monkeypatch.setattr(engine, "_select_connector", lambda *_args: RetryConnector())
    monkeypatch.setattr(
        engine,
        "source_fetcher",
        lambda *_args: {
            "full_name": "Test Citizen",
            "dob": "10/05/2003",
            "income_certificate_no": "INC-RETRY-1001",
            "annual_income": 240000,
        },
    )
    response = hub_client.post("/api/v1/exceptions/1/retry")
    assert response.status_code == 200
    result = response.json()
    assert result["status"] == "success"
    assert result["exception"]["status"] == "RESOLVED"
    assert result["exception"]["retryCount"] == 1
    assert result["transactionStatus"] == "COMPLETED"

    with hub_client.app.state.test_sessions() as db:
        transaction = (
            db.query(InteroperabilityTransaction)
            .filter(InteroperabilityTransaction.transaction_id == "TXN-HUB-1001")
            .one()
        )
        application = db.query(ServiceApplication).one()
        exception = db.query(InteroperabilityException).one()
        assert transaction.status == "COMPLETED"
        assert exception.status == "RESOLVED"
        assert exception.resolved_at is not None
        assert exception.retry_count == 1
        assert "retrieved" in application.remarks
        assert (
            db.query(TransactionEvent)
            .filter(
                TransactionEvent.transaction_id == transaction.id,
                TransactionEvent.status == "APPLICATION_UPDATED",
            )
            .count()
            == 2
        )
        retry_audit = (
            db.query(AuditLog)
            .filter(AuditLog.action == "EXCEPTION_RETRIED")
            .one()
        )
        assert retry_audit.result == "success"


@pytest.mark.parametrize(
    ("category", "message", "expected"),
    [
        ("CONNECTOR_UNAVAILABLE", "", "SOURCE_SYSTEM_UNAVAILABLE"),
        ("TIMEOUT_ERROR", "", "TIMEOUT"),
        ("SOURCE_RESPONSE", "", "INVALID_RESPONSE"),
        ("NORMALIZATION", "", "MALFORMED_DATA"),
        ("MISSING_FIELDS", "", "MISSING_REQUIRED_FIELD"),
        ("CONSENT", "The consent has expired.", "CONSENT_EXPIRED"),
        ("VALIDATION", "Citizen not found.", "CITIZEN_NOT_FOUND"),
        ("VALIDATION", "Source validation failed.", "VALIDATION_FAILURE"),
        ("DATA_CONFLICT", "", "DATA_CONFLICT"),
        ("SOURCE_CONNECTOR", "", "CONNECTOR_FAILURE"),
    ],
)
def test_exception_failures_use_supported_types(category, message, expected):
    assert exception_type(category, message) == expected


def test_expired_consent_is_persisted_as_an_interoperability_exception(
    hub_client, monkeypatch
):
    monkeypatch.setattr(
        "app.services.interoperability.engine.settings.data_mode", "demo"
    )
    with hub_client.app.state.test_sessions() as db:
        consent = db.query(DataShareConsent).one()
        consent.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        db.commit()

        application = db.query(ServiceApplication).one()
        citizen = db.query(User).filter(User.role == UserRole.CITIZEN).one()
        result = interoperability_service.engine.process(
            db,
            citizen_id=citizen.id,
            service_id=application.service_id,
            application_id=application.id,
            consent_id=consent.id,
            requesting_department="Education",
            source_department="Revenue",
            data_requested="Income record",
            purpose="Scholarship verification",
        )

        assert result["status"] == "failure"
        exception = (
            db.query(InteroperabilityException)
            .filter(InteroperabilityException.category == "CONSENT_EXPIRED")
            .one()
        )
        assert exception.status == "OPEN"
        assert exception.transaction_id is not None
        assert "expired" in exception.message.lower()


def test_audit_log_filters_return_immutable_database_records(hub_client):
    today = datetime.now(timezone.utc).date().isoformat()
    response = hub_client.get(
        "/api/v1/audit-logs",
        params={
            "date": today,
            "actor": 2,
            "department": 2,
            "action": "DATA_RECEIVED",
            "transaction": "TXN-HUB-1001",
            "resource": "interoperability_transaction",
            "result": "success",
        },
    )
    assert response.status_code == 200
    assert len(response.json()) == 1
    item = response.json()[0]
    assert item["action"] == "DATA_RECEIVED"
    assert item["actor_role"] == "system_admin"
    assert item["resource_type"] == "interoperability_transaction"
    assert item["resource_id"] == "TXN-HUB-1001"
    assert item["transaction_id"] == "TXN-HUB-1001"
    assert item["metadata"] == {"status": "DATA_RECEIVED"}
    assert item["timestamp"]

    assert hub_client.post("/api/v1/audit-logs", json={}).status_code == 405


def test_audit_log_rows_cannot_be_updated_or_deleted(hub_client):
    with hub_client.app.state.test_sessions() as db:
        audit = db.query(AuditLog).filter(AuditLog.action == "DATA_RECEIVED").first()
        audit.action = "TAMPERED"
        with pytest.raises(ValueError, match="append-only"):
            db.commit()
        db.rollback()

        audit = db.query(AuditLog).filter(AuditLog.action == "DATA_RECEIVED").first()
        db.delete(audit)
        with pytest.raises(ValueError, match="append-only"):
            db.commit()
