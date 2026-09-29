"""PostgreSQL-backed scholarship flow; requires a disposable GovFlow test database."""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import fitz
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app
from app.core.security import hash_password
from app.models.audit import AuditLog
from app.models.application import ApplicationStatus
from app.models.application import ServiceApplication
from app.models.consent import ConsentStatus, DataShareConsent
from app.models.department import Department
from app.models.document_verification_result import DocumentVerificationResult
from app.models.government_record import GovernmentRecord, GovernmentRecordValue
from app.models.interoperability_exception import (
    ExceptionStatus,
    InteroperabilityException,
)
from app.models.notification import Notification
from app.models.platform import ConnectedSystem, PlatformStatus
from app.models.role import Role
from app.models.service import Service
from app.models.transaction import InteroperabilityTransaction
from app.models.transaction_event import TransactionEvent
from app.models.user import User, UserRole
from app.services.interoperability_service import interoperability_service
from app.services.workflow_engine import workflow_engine


@pytest.fixture
def postgres_scholarship_flow(monkeypatch, tmp_path):
    database_url = os.getenv("GOVFLOW_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("Set GOVFLOW_TEST_DATABASE_URL to an isolated test database.")

    engine = create_engine(
        database_url,
        pool_pre_ping=True,
        connect_args=(
            {"check_same_thread": False}
            if database_url.startswith("sqlite")
            else {"connect_timeout": 5}
        ),
    )
    connection = engine.connect()
    if engine.dialect.name == "sqlite":
        Base.metadata.create_all(connection)
        connection.commit()
    elif engine.dialect.name != "postgresql":
        pytest.skip("The scholarship integration tests require PostgreSQL or SQLite.")
    transaction = connection.begin()
    sessions = sessionmaker(
        bind=connection,
        autoflush=False,
        expire_on_commit=False,
        join_transaction_mode="create_savepoint",
    )
    client: TestClient | None = None

    try:
        missing_tables = set(Base.metadata.tables) - set(inspect(connection).get_table_names())
        if engine.dialect.name == "postgresql" and missing_tables:
            pytest.skip(
                "Apply database migrations before running the PostgreSQL flow test."
            )

        db = sessions()
        try:
            for key, name in (
                ("citizen", "Citizen"),
                ("department_officer", "Department Officer"),
            ):
                if db.query(Role).filter_by(key=key).first() is None:
                    db.add(Role(key=key, name=name))
            db.flush()

            unique = uuid4().hex[:10]
            revenue = Department(name=f"Revenue {unique}", code=f"REV{unique[:6]}")
            education = Department(name=f"Education {unique}", code=f"EDU{unique[:6]}")
            welfare = Department(
                name=f"Social Welfare {unique}", code=f"SW{unique[:6]}"
            )
            db.add_all([revenue, education, welfare])
            db.flush()

            revenue_system = ConnectedSystem(
                name=f"Revenue Registry {unique}",
                slug=f"revenue-{unique}",
                department_id=revenue.id,
                status=PlatformStatus.ACTIVE,
                max_retries=0,
            )
            education_system = ConnectedSystem(
                name=f"Higher & Technical Education Registry {unique}",
                slug=f"education-{unique}",
                department_id=education.id,
                status=PlatformStatus.ACTIVE,
                max_retries=0,
            )
            welfare_system = ConnectedSystem(
                name=f"Social Welfare Gateway {unique}",
                slug=f"welfare-{unique}",
                department_id=welfare.id,
                status=PlatformStatus.ACTIVE,
            )
            db.add_all([revenue_system, education_system, welfare_system])
            db.flush()

            service = Service(
                name=f"Post-Matric Scholarship {unique}",
                code=f"POST_MATRIC_{unique.upper()}",
                description="Post-Matric Scholarship integration test service.",
                department_id=welfare.id,
                platform_id=welfare_system.id,
            )
            db.add(service)
            db.flush()

            officer = User(
                full_name="Integration Test Officer",
                email=f"officer-{unique}@example.com",
                role=UserRole.OFFICER,
                role_id=db.query(Role).filter_by(key="department_officer").one().id,
                department_id=welfare.id,
                hashed_password=hash_password("OfficerPass123"),
                is_active=True,
            )
            db.add(officer)
            db.commit()
            service_id = service.id
            revenue_system_id = revenue_system.id
            education_system_id = education_system.id
            welfare_id = welfare.id
            officer_email = officer.email
        finally:
            db.close()

        def override_db():
            with sessions() as request_db:
                yield request_db

        app.dependency_overrides[get_db] = override_db
        monkeypatch.setattr("app.api.v1.documents.BASE_DIR", tmp_path)
        monkeypatch.setattr(
            "app.services.interoperability.engine.settings.data_mode", "demo"
        )
        client = TestClient(app)

        citizen_response = client.post(
            "/api/v1/auth/signup",
            json={
                "full_name": "Integration Test Citizen",
                "email": f"citizen-{unique}@example.com",
                "phone": "8123456789",
                "aadhaar_last4": "1234",
                "password": "CitizenPass123",
            },
        )
        assert citizen_response.status_code == 201, citizen_response.text
        citizen = citizen_response.json()["user"]
        citizen_login = client.post(
            "/api/v1/auth/login",
            json={
                "email": f"citizen-{unique}@example.com",
                "password": "CitizenPass123",
            },
        )
        assert citizen_login.status_code == 200, citizen_login.text
        citizen_token = citizen_login.json()["access_token"]

        officer_login = client.post(
            "/api/v1/auth/login",
            json={"email": officer_email, "password": "OfficerPass123"},
        )
        assert officer_login.status_code == 200, officer_login.text

        def authorize(token: str) -> None:
            client.headers.update({"Authorization": "bearer" + chr(32) + token})

        authorize(citizen_token)
        services_response = client.get("/api/v1/services")
        assert services_response.status_code == 200, services_response.text
        assert any(
            item["id"] == service_id for item in services_response.json()
        )
        form_schema_response = client.get(f"/api/v1/services/{service_id}/form-schema")
        assert form_schema_response.status_code == 200, form_schema_response.text
        form_schema = form_schema_response.json()
        form_data = _valid_form_data(form_schema["fields"], citizen)
        application_response = client.post(
            "/api/v1/applications",
            json={
                "citizen_id": citizen["id"],
                "service_id": service_id,
                "form_data": form_data,
                "verified_records": {},
                "consent": True,
            },
        )
        assert application_response.status_code == 201, application_response.text
        application = application_response.json()

        with sessions() as request_db:
            application_row = request_db.get(ServiceApplication, application["id"])
            assert application_row is not None
            definition = workflow_engine.latest_definition(request_db, service_id)
            assert definition is not None
            assert set(definition.required_records) == {"Revenue", "Education"}
            assert set(definition.required_consents) == {
                "Student enrolment and academic record",
                "Verified household income record",
            }

        yield {
            "client": client,
            "sessions": sessions,
            "citizen": citizen,
            "citizen_token": citizen_token,
            "officer_token": officer_login.json()["access_token"],
            "application": application,
            "service_id": service_id,
            "revenue_system_id": revenue_system_id,
            "education_system_id": education_system_id,
            "welfare_id": welfare_id,
            "revenue_calls": [],
            "education_calls": [],
        }
    finally:
        if client is not None:
            client.close()
        app.dependency_overrides.pop(get_db, None)
        connection.rollback()
        connection.close()
        engine.dispose()


def _valid_form_data(fields, citizen) -> dict:
    values = {}
    for field in fields:
        if field.get("visible_if") and values.get(field["visible_if"]["field"]) != field[
            "visible_if"
        ]["equals"]:
            continue
        field_id = field["id"]
        if field_id == "full_name":
            value = citizen["full_name"]
        elif field_id == "email":
            value = citizen["email"]
        elif field_id == "mobile":
            value = "8123456789"
        elif field_id == "aadhaar_last4":
            value = "1234"
        elif field_id == "date_of_birth":
            value = "2003-05-10"
        elif field_id in {"address", "district", "taluka", "village_city", "state"}:
            value = "Integration Test Value"
        elif field_id == "pin_code":
            value = "411001"
        elif field["type"] == "checkbox":
            value = True
        elif field["type"] == "select":
            value = field["options"][0]
        elif field["type"] == "number":
            value = 100
        elif field["type"] == "date":
            value = "2026-01-01"
        else:
            value = f"Test {field_id}"
        values[field_id] = value
    return values


def _pdf(content: str) -> bytes:
    document = fitz.open()
    page = document.new_page()
    page.insert_textbox((50, 50, 550, 750), content)
    return document.tobytes()


def _seed_source_responses(
    flow,
    monkeypatch,
    *,
    revenue_dob="10/05/2003",
    education_dob="10/05/2003",
):
    engine = interoperability_service.engine
    revenue_connector = next(
        connector for connector in engine.connectors if connector.mapping_key == "revenue"
    )
    education_connector = next(
        connector for connector in engine.connectors if connector.mapping_key == "education"
    )

    def revenue_record(citizen_id, record_type, purpose=None):
        flow["revenue_calls"].append((citizen_id, record_type, purpose))
        return revenue_connector._remember_record(
            citizen_id,
            {
                "full_name": flow["citizen"]["full_name"],
                "dob": revenue_dob,
                "income_certificate_no": f"INC-{citizen_id}-TEST",
                "annual_income": 240000,
            },
        )

    def education_record(citizen_id, record_type, purpose=None):
        flow["education_calls"].append((citizen_id, record_type, purpose))
        return education_connector._remember_record(
            citizen_id,
            {
                "student_name": flow["citizen"]["full_name"],
                "date_of_birth": education_dob,
                "student_id": f"EDU-{citizen_id}-TEST",
                "institution": "Integration Test Institution",
            },
        )

    monkeypatch.setattr(revenue_connector, "get_record", revenue_record)
    monkeypatch.setattr(education_connector, "get_record", education_record)


def _create_and_grant_consents(flow) -> dict[str, int]:
    client = flow["client"]
    application_id = flow["application"]["id"]
    citizen_id = flow["citizen"]["id"]
    with flow["sessions"]() as db:
        app_row = db.get(ServiceApplication, application_id)
        assert app_row is not None
        service = db.get(Service, flow["service_id"])
        assert service is not None
        revenue_system = db.get(ConnectedSystem, flow["revenue_system_id"])
        education_system = db.get(ConnectedSystem, flow["education_system_id"])
        assert revenue_system is not None and education_system is not None
        specs = (
            (
                "income",
                revenue_system.id,
                "Verified household income record",
                "Income Certificate",
            ),
            (
                "education",
                education_system.id,
                "Student enrolment and academic record",
                "Student Verification",
            ),
        )
        target_system_id = service.platform_id
    ids = {}
    for key, source_system_id, consent_scope, requested_data in specs:
        response = client.post(
            "/api/v1/consents",
            json={
                "citizen_id": citizen_id,
                "application_id": application_id,
                "purpose": (
                    "Post-Matric Scholarship eligibility verification"
                    f" | {consent_scope} | Data requested: {requested_data}"
                ),
                "source_platform_id": source_system_id,
                "target_platform_id": target_system_id,
                "requested_data": consent_scope,
                "requested_fields": [requested_data],
            },
        )
        assert response.status_code == 201, response.text
        consent_id = response.json()["id"]
        granted = client.post(f"/api/v1/consents/{consent_id}/approve")
        assert granted.status_code == 200, granted.text
        assert granted.json()["status"] == "granted"
        ids[key] = consent_id
    workflow_response = client.get(
        f"/api/v1/applications/{application_id}/workflow"
    )
    assert workflow_response.status_code == 200, workflow_response.text
    workflow_steps = {step["key"]: step for step in workflow_response.json()}
    assert workflow_steps["consent"]["status"] == "completed"
    assert workflow_steps["income_request"]["status"] == "in_progress"
    return ids


def _request_data(flow, *, consent_id: int, source: str, data: str, purpose: str):
    app = flow["application"]
    return flow["client"].post(
        "/api/v1/interoperability/request",
        json={
            "citizen_id": flow["citizen"]["id"],
            "service_id": flow["service_id"],
            "application_id": app["id"],
            "consent_id": consent_id,
            "requesting_department": "Social Welfare",
            "source_department": source,
            "data_requested": data,
            "purpose": purpose,
        },
    )


def test_complete_scholarship_flow_is_persisted_in_postgresql(
    postgres_scholarship_flow, monkeypatch
):
    flow = postgres_scholarship_flow
    with flow["sessions"]() as db:
        assert (
            db.query(GovernmentRecord)
            .filter_by(citizen_id=flow["citizen"]["id"])
            .count()
            == 0
        )
    _seed_source_responses(flow, monkeypatch)
    consent_ids = _create_and_grant_consents(flow)
    with flow["sessions"]() as db:
        persisted_consent = db.get(DataShareConsent, consent_ids["income"])
        assert persisted_consent is not None
        assert persisted_consent.citizen_id == flow["citizen"]["id"]
        assert persisted_consent.status == ConsentStatus.GRANTED

    revenue_result = _request_data(
        flow,
        consent_id=consent_ids["income"],
        source="Revenue",
        data="Income Certificate",
        purpose="Post-Matric Scholarship eligibility verification | Verified household income record | Data requested: Income Certificate",
    )
    assert revenue_result.status_code == 200, revenue_result.text
    assert revenue_result.json()["status"] == "success", revenue_result.json()

    education_result = _request_data(
        flow,
        consent_id=consent_ids["education"],
        source="Education",
        data="Student Verification",
        purpose="Post-Matric Scholarship eligibility verification | Student enrolment and academic record | Data requested: Student Verification",
    )
    assert education_result.status_code == 200, education_result.text
    assert education_result.json()["status"] == "success", education_result.json()
    assert len(flow["revenue_calls"]) == 1
    assert len(flow["education_calls"]) == 1

    application_id = flow["application"]["id"]
    document_response = flow["client"].post(
        "/api/v1/documents/upload-and-verify",
        data={
            "application_id": application_id,
            "doc_type": "Income Certificate",
        },
        files={
            "file": (
                "income-certificate.pdf",
                _pdf(
                    "Income Certificate\n"
                    "Certificate Number: INC-TEST-123\n"
                    "Name: Integration Test Citizen\n"
                    "Issue Date: 2025-01-01\n"
                    "Issuer: Revenue Department\n"
                    "Income: 240000"
                ),
                "application/pdf",
            )
        },
    )
    assert document_response.status_code == 201, document_response.text
    document_result = document_response.json()["verification_result"]
    assert document_result["verification_status"] == "PENDING_REVIEW"

    with flow["sessions"]() as db:
        application = db.get(ServiceApplication, application_id)
        transactions = (
            db.query(InteroperabilityTransaction)
            .filter_by(application_id=application_id)
            .order_by(InteroperabilityTransaction.created_at)
            .all()
        )
        records = (
            db.query(GovernmentRecord)
            .filter_by(application_id=application_id, status="VERIFIED")
            .all()
        )
        assert application is not None
        assert application.status == ApplicationStatus.UNDER_REVIEW
        assert {record.department.name for record in records} == {
            db.get(Department, record.department_id).name for record in records
        }
        assert len(records) == 2
        assert {row.connected_system_id for row in records} == {
            flow["revenue_system_id"],
            flow["education_system_id"],
        }
        values_by_source = {
            row.connected_system_id: {
                value.field_key: value.field_value for value in row.values
            }
            for row in records
        }
        assert (
            values_by_source[flow["revenue_system_id"]]["date_of_birth"]
            == "2003-05-10"
        )
        assert values_by_source[flow["revenue_system_id"]]["annual_income"] == "240000"
        assert values_by_source[flow["education_system_id"]]["identifier"].startswith(
            "EDU-"
        )
        assert len(transactions) == 2
        for transaction in transactions:
            assert transaction.status == "COMPLETED"
            states = [
                item.status
                for item in db.query(TransactionEvent)
                .filter_by(transaction_id=transaction.id)
                .order_by(TransactionEvent.occurred_at)
                .all()
            ]
            assert {
                "CREATED",
                "CONSENT_GRANTED",
                "DATA_REQUESTED",
                "DATA_RECEIVED",
                "DATA_VALIDATED",
                "DATA_NORMALIZED",
                "APPLICATION_UPDATED",
                "COMPLETED",
            } <= set(states)
        assert db.query(AuditLog).filter(AuditLog.transaction_id.is_not(None)).count() >= 10
        assert (
            db.query(Notification)
            .filter_by(
                recipient_id=flow["citizen"]["id"],
                application_id=application_id,
                event_type="APPLICATION_CREATED",
            )
            .count()
            == 1
        )
        assert db.query(GovernmentRecordValue).count() >= 2

    flow["client"].headers.update(
        {"Authorization": f"Bearer {flow['officer_token']}"}
    )
    assigned = flow["client"].post(f"/api/v1/applications/{application_id}/assign-to-me")
    assert assigned.status_code == 200, assigned.text
    reviewed_document = flow["client"].post(
        f"/api/v1/documents/verifications/{document_result['id']}/review",
        json={
            "decision": "VERIFIED",
            "note": "Integration test officer confirmed the uploaded document.",
        },
    )
    assert reviewed_document.status_code == 200, reviewed_document.text
    assert (
        reviewed_document.json()["verification_result"]["verification_status"]
        == "VERIFIED"
    )
    with flow["sessions"]() as db:
        verified_document = db.get(
            DocumentVerificationResult, document_result["id"]
        )
        assert verified_document is not None
        assert verified_document.verification_status == "VERIFIED"
        assert verified_document.reviewed_by is not None
        assert verified_document.document.is_verified is True
        assert (
            db.query(AuditLog)
            .filter(
                AuditLog.action == "DOCUMENT_VERIFIED",
                AuditLog.resource_id == str(document_result["id"]),
            )
            .count()
            == 1
        )
    officer_applications = flow["client"].get("/api/v1/applications")
    assert officer_applications.status_code == 200, officer_applications.text
    assert any(item["id"] == application_id for item in officer_applications.json())
    workspace = flow["client"].get(
        f"/api/v1/applications/{application_id}/workspace"
    )
    if workspace.status_code == 404:
        workspace = flow["client"].get(f"/api/v1/applications/{application_id}")
    assert workspace.status_code == 200, workspace.text
    details = workspace.json()
    assert details["citizen"]["id"] == flow["citizen"]["id"]
    assert details["application_information"]["id"] == application_id
    assert len(details.get("verified_records", [])) == 2
    assert len(details.get("transactions", [])) == 2
    assert len(details.get("consents", [])) == 2
    assert details.get("transaction_events")
    assert details.get("workflow")
    assert details.get("exceptions") == []
    assert details.get("audit_events")

    workflow_response = flow["client"].get(
        f"/api/v1/applications/{application_id}/workflow"
    )
    assert workflow_response.status_code == 200, workflow_response.text
    steps = {step["key"]: step for step in workflow_response.json()}
    for step_key, next_step in (
        ("documents", None),
        ("document_verification", None),
        ("data_validation", None),
        ("officer_review", "approval"),
        ("approval", None),
    ):
        step = steps[step_key]
        if step["status"] == "completed":
            continue
        if step["status"] == "pending":
            started = flow["client"].patch(
                f"/api/v1/applications/{application_id}/workflow",
                json={"stage_key": step_key, "status": "in_progress"},
            )
            assert started.status_code == 200, started.text
        completed = flow["client"].patch(
            f"/api/v1/applications/{application_id}/workflow",
            json={
                "stage_key": step_key,
                "status": "completed",
                **({"next_step": next_step} if next_step else {}),
            },
        )
        assert completed.status_code == 200, completed.text
    with flow["sessions"]() as db:
        persisted = db.get(ServiceApplication, application_id)
        assert persisted is not None
        assert persisted.status == ApplicationStatus.APPROVED
        assert (
            db.query(AuditLog)
            .filter(
                AuditLog.action == "APPLICATION_APPROVED",
                AuditLog.resource_id == str(application_id),
            )
            .count()
            == 1
        )
        assert (
            db.query(Notification)
            .filter_by(
                recipient_id=flow["citizen"]["id"],
                application_id=application_id,
                event_type="APPLICATION_APPROVED",
            )
            .count()
            == 1
        )
    flow["client"].headers.update(
        {"Authorization": "bearer" + chr(32) + flow["citizen_token"]}
    )
    citizen_notifications = flow["client"].get("/api/v1/notifications")
    assert citizen_notifications.status_code == 200, citizen_notifications.text
    assert any(
        item["event_type"] == "APPLICATION_APPROVED"
        and item["application_id"] == application_id
        for item in citizen_notifications.json()
    )


def test_revenue_connector_failure_creates_retryable_persisted_exception(
    postgres_scholarship_flow, monkeypatch
):
    flow = postgres_scholarship_flow
    _seed_source_responses(flow, monkeypatch)
    consent_ids = _create_and_grant_consents(flow)
    revenue = next(
        connector
        for connector in interoperability_service.engine.connectors
        if connector.mapping_key == "revenue"
    )
    calls = []

    def fail_then_succeed(citizen_id, _record_type, _purpose=None):
        calls.append("attempt")
        if len(calls) == 1:
            raise ConnectionError("test source unavailable")
        return revenue._remember_record(
            citizen_id,
            {
                "full_name": flow["citizen"]["full_name"],
                "dob": "10/05/2003",
                "income_certificate_no": f"INC-{citizen_id}-RETRY",
                "annual_income": 240000,
            },
        )

    monkeypatch.setattr(revenue, "get_record", fail_then_succeed)
    result = _request_data(
        flow,
        consent_id=consent_ids["income"],
        source="Revenue",
        data="Income Certificate",
        purpose="Post-Matric Scholarship eligibility verification | Verified household income record | Data requested: Income Certificate",
    )
    assert result.status_code == 200, result.text
    assert result.json()["status"] == "failure"
    assert calls
    with flow["sessions"]() as db:
        exception = db.query(InteroperabilityException).one()
        assert exception.category == "SOURCE_SYSTEM_UNAVAILABLE"
        assert exception.status == ExceptionStatus.OPEN
        transaction = db.get(InteroperabilityTransaction, exception.transaction_id)
        assert transaction is not None and transaction.status == "FAILED"
        exception_id = exception.id

    flow["client"].headers.update(
        {"Authorization": "bearer" + chr(32) + flow["officer_token"]}
    )
    assignment = flow["client"].post(
        f"/api/v1/applications/{flow['application']['id']}/assign-to-me"
    )
    assert assignment.status_code == 200, assignment.text
    retried = flow["client"].post(f"/api/v1/exceptions/{exception_id}/retry")
    assert retried.status_code == 200, retried.text
    assert retried.json()["status"] == "success"
    assert len(calls) == 2
    with flow["sessions"]() as db:
        exception = db.get(InteroperabilityException, exception_id)
        assert exception is not None
        assert exception.status == ExceptionStatus.RESOLVED
        assert exception.retry_count == 1
        assert (
            db.query(InteroperabilityTransaction)
            .filter_by(id=exception.transaction_id, status="COMPLETED")
            .count()
            == 1
        )


def test_invalid_revenue_data_is_persisted_as_validation_exception(
    postgres_scholarship_flow, monkeypatch
):
    flow = postgres_scholarship_flow
    _seed_source_responses(flow, monkeypatch)
    consent_ids = _create_and_grant_consents(flow)
    revenue = next(
        connector
        for connector in interoperability_service.engine.connectors
        if connector.mapping_key == "revenue"
    )

    def invalid_record(citizen_id, _record_type, _purpose=None):
        return revenue._remember_record(
            citizen_id,
            {
                "full_name": flow["citizen"]["full_name"],
                "dob": "not-a-date",
                "income_certificate_no": f"INC-{citizen_id}-INVALID",
                "annual_income": 240000,
            },
        )

    monkeypatch.setattr(revenue, "get_record", invalid_record)
    response = _request_data(
        flow,
        consent_id=consent_ids["income"],
        source="Revenue",
        data="Income Certificate",
        purpose="Post-Matric Scholarship eligibility verification | Verified household income record | Data requested: Income Certificate",
    )
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "failure"
    with flow["sessions"]() as db:
        exception = db.query(InteroperabilityException).one()
        assert exception.category == "MALFORMED_DATA"
        assert exception.status == ExceptionStatus.OPEN
        transaction = db.get(InteroperabilityTransaction, exception.transaction_id)
        assert transaction is not None
        assert transaction.validation_status == "PASSED"
        assert transaction.mapping_status == "FAILED"
        assert db.query(GovernmentRecord).filter_by(application_id=flow["application"]["id"]).count() == 0


def test_conflicting_dob_between_revenue_and_education_is_flagged(
    postgres_scholarship_flow, monkeypatch
):
    flow = postgres_scholarship_flow
    _seed_source_responses(
        flow,
        monkeypatch,
        revenue_dob="10/05/2003",
        education_dob="10/05/2004",
    )
    consent_ids = _create_and_grant_consents(flow)
    for consent_key, source, data in (
        ("income", "Revenue", "Income Certificate"),
        ("education", "Education", "Student Verification"),
    ):
        response = _request_data(
            flow,
            consent_id=consent_ids[consent_key],
            source=source,
            data=data,
            purpose=(
                "Post-Matric Scholarship eligibility verification | "
                f"{'Verified household income record' if consent_key == 'income' else 'Student enrolment and academic record'} "
                f"| Data requested: {data}"
            ),
        )
        assert response.status_code == 200, response.text
    with flow["sessions"]() as db:
        exception = (
            db.query(InteroperabilityException)
            .filter_by(category="DATA_CONFLICT")
            .one()
        )
        assert exception.status == ExceptionStatus.OPEN
        records = (
            db.query(GovernmentRecord)
            .filter_by(citizen_id=flow["citizen"]["id"])
            .all()
        )
        assert len(records) == 2
        assert {record.status for record in records} == {"CONFLICT"}
        conflict_rows = (
            db.query(GovernmentRecordValue)
            .filter(
                GovernmentRecordValue.record_id.in_([record.id for record in records]),
                GovernmentRecordValue.field_key == "date_of_birth",
            )
            .all()
        )
        assert {value.field_value for value in conflict_rows} == {
            "2003-05-10",
            "2004-05-10",
        }


def test_expired_consent_prevents_connector_request_and_persists_exception(
    postgres_scholarship_flow, monkeypatch
):
    flow = postgres_scholarship_flow
    _seed_source_responses(flow, monkeypatch)
    consent_ids = _create_and_grant_consents(flow)
    with flow["sessions"]() as db:
        consent = db.get(DataShareConsent, consent_ids["income"])
        assert consent is not None
        consent.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        db.commit()
    response = _request_data(
        flow,
        consent_id=consent_ids["income"],
        source="Revenue",
        data="Income Certificate",
        purpose="Post-Matric Scholarship eligibility verification | Verified household income record | Data requested: Income Certificate",
    )
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "failure"
    assert flow["revenue_calls"] == []
    with flow["sessions"]() as db:
        exception = (
            db.query(InteroperabilityException)
            .filter_by(category="CONSENT_EXPIRED")
            .one()
        )
        assert exception.status == ExceptionStatus.OPEN
        transaction = db.get(InteroperabilityTransaction, exception.transaction_id)
        assert transaction is not None and transaction.status == "FAILED"
