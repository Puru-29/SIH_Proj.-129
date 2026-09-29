from datetime import datetime, timezone
import fitz
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
    Department,
    GovernmentRecord,
    GovernmentRecordValue,
    Service,
    ServiceApplication,
    User,
)
from app.models.application import ApplicationStatus
from app.models.platform import ConnectedSystem, PlatformStatus
from app.models.user import UserRole


def _pdf(content: str) -> bytes:
    document = fitz.open()
    page = document.new_page()
    page.insert_textbox((50, 50, 550, 750), content)
    return document.tobytes()


@pytest.fixture
def verification_client(monkeypatch, tmp_path):
    monkeypatch.setattr("app.api.v1.documents.BASE_DIR", tmp_path)
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    sessions = sessionmaker(autoflush=False, bind=engine, expire_on_commit=False)
    with sessions() as db:
        department = Department(name="Revenue", code="REV")
        other_department = Department(name="Education", code="EDU")
        db.add_all([department, other_department])
        db.flush()
        citizen = User(
            full_name="Ada Citizen",
            email="document-citizen@example.test",
            role=UserRole.CITIZEN,
            hashed_password="unused",
        )
        officer = User(
            full_name="Revenue Officer",
            email="document-officer@example.test",
            role=UserRole.OFFICER,
            department_id=department.id,
            hashed_password="unused",
        )
        other_officer = User(
            full_name="Education Officer",
            email="other-officer@example.test",
            role=UserRole.OFFICER,
            department_id=other_department.id,
            hashed_password="unused",
        )
        db.add_all([citizen, officer, other_officer])
        db.flush()
        source = ConnectedSystem(
            name="Revenue Source",
            slug="revenue-source",
            department_id=department.id,
            status=PlatformStatus.ACTIVE,
        )
        db.add(source)
        db.flush()
        service = Service(
            name="Income Certificate",
            code="INC",
            department_id=department.id,
            platform_id=source.id,
        )
        db.add(service)
        db.flush()
        application = ServiceApplication(
            reference_id="DOC-APP-1001",
            status=ApplicationStatus.UNDER_REVIEW,
            citizen_id=citizen.id,
            service_id=service.id,
            department_id=department.id,
            form_data={},
        )
        db.add(application)
        db.flush()
        source_record = GovernmentRecord(
            citizen_id=citizen.id,
            department_id=department.id,
            connected_system_id=source.id,
            application_id=application.id,
            record_type="Income Certificate",
            source_record_id="INC-0001",
            status="VERIFIED",
            verified_at=datetime.now(timezone.utc),
        )
        db.add(source_record)
        db.flush()
        db.add_all(
            [
                GovernmentRecordValue(
                    record_id=source_record.id,
                    field_key="certificate_number",
                    field_value="INC-0001",
                ),
                GovernmentRecordValue(
                    record_id=source_record.id,
                    field_key="full_name",
                    field_value="Ada Citizen",
                ),
                GovernmentRecordValue(
                    record_id=source_record.id,
                    field_key="annual_income",
                    field_value="120000",
                ),
            ]
        )
        db.commit()
        ids = {
            "citizen": citizen.id,
            "officer": officer.id,
            "other_officer": other_officer.id,
            "application": application.id,
        }

    active_user = {"user": None}

    def override_get_db():
        with sessions() as db:
            yield db

    app.dependency_overrides[get_db] = override_get_db

    def current_user():
        with sessions() as db:
            return (
                db.query(User)
                .options(joinedload(User.role_record))
                .filter(User.id == active_user["user"])
                .one()
            )

    app.dependency_overrides[require_authenticated_user] = current_user
    app.state.document_test_sessions = sessions
    app.state.document_test_user = active_user
    try:
        with TestClient(app) as client:
            yield client, ids
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(require_authenticated_user, None)
        del app.state.document_test_sessions
        del app.state.document_test_user
        engine.dispose()


def test_pdf_upload_extracts_fields_matches_source_and_waits_for_review(
    verification_client,
):
    client, ids = verification_client
    client.app.state.document_test_user["user"] = ids["citizen"]
    pdf = _pdf(
        "GOVERNMENT OF MAHARASHTRA\n"
        "REVENUE DEPARTMENT\n"
        "INCOME CERTIFICATE\n"
        "Applicant: Ada Citizen\n"
        "Annual Income: Rs 120,000\n"
        "Certificate No: INC-0001\n"
        "Issue Date: 05/09/2026\n"
        "Issued by: Revenue Department"
    )
    response = client.post(
        "/api/v1/documents/upload-and-verify",
        data={"application_id": str(ids["application"])},
        files={"file": ("income.pdf", pdf, "application/pdf")},
    )
    assert response.status_code == 201, response.text
    body = response.json()
    result = body["verification_result"]
    assert body["document"]["is_verified"] is False
    assert result["verification_status"] == "PENDING_REVIEW"
    assert result["source_match_status"] == "MATCHED"
    assert result["extracted_fields"]["certificate_number"] == "INC-0001"
    assert result["extracted_fields"]["name"] == "Ada Citizen"
    assert result["extracted_fields"]["income"] == 120000
    assert result["extracted_fields"]["issue_date"] == "2026-09-05"
    assert result["pipeline_steps"][-1]["step"] == "HUMAN_REVIEW"
    assert "fraud probability" in result["pipeline_steps"][-2]["confidence_scope"]


def test_upload_rejects_invalid_file_signature(verification_client):
    client, ids = verification_client
    client.app.state.document_test_user["user"] = ids["citizen"]
    response = client.post(
        "/api/v1/documents/upload-and-verify",
        data={"application_id": str(ids["application"])},
        files={"file": ("not-a-pdf.pdf", b"not a pdf", "application/pdf")},
    )
    assert response.status_code == 422


def test_duplicate_file_is_flagged_and_officer_review_updates_application(
    verification_client,
):
    client, ids = verification_client
    client.app.state.document_test_user["user"] = ids["citizen"]
    pdf = _pdf(
        "GOVERNMENT OF MAHARASHTRA\n"
        "INCOME CERTIFICATE\n"
        "Applicant: Ada Citizen\n"
        "Annual Income: 120000\n"
        "Certificate No: INC-0001"
    )
    first = client.post(
        "/api/v1/documents/upload-and-verify",
        data={"application_id": str(ids["application"])},
        files={"file": ("income.pdf", pdf, "application/pdf")},
    )
    second = client.post(
        "/api/v1/documents/upload-and-verify",
        data={"application_id": str(ids["application"])},
        files={"file": ("income.pdf", pdf, "application/pdf")},
    )
    assert first.status_code == 201
    assert second.status_code == 201
    second_result = second.json()["verification_result"]
    assert second_result["duplicate_status"] == "DUPLICATE"
    assert any("Identical file content" in item for item in second_result["tampering_indicators"])

    client.app.state.document_test_user["user"] = ids["other_officer"]
    forbidden = client.post(
        f"/api/v1/documents/verifications/{second_result['id']}/review",
        json={"decision": "VERIFIED", "note": "Checked original document"},
    )
    assert forbidden.status_code == 403

    client.app.state.document_test_user["user"] = ids["officer"]
    reviewed = client.post(
        f"/api/v1/documents/verifications/{second_result['id']}/review",
        json={"decision": "VERIFIED", "note": "Compared with the original record"},
    )
    assert reviewed.status_code == 200, reviewed.text
    reviewed_body = reviewed.json()
    assert reviewed_body["verification_result"]["verification_status"] == "VERIFIED"
    assert reviewed_body["verification_result"]["reviewed_by"] == ids["officer"]
    assert reviewed_body["document"]["is_verified"] is True

    sessions = client.app.state.document_test_sessions
    with sessions() as db:
        application = db.get(ServiceApplication, ids["application"])
        assert application is not None
        assert application.form_data["document_verifications"][-1]["status"] == "VERIFIED"
        assert (
            db.query(AuditLog)
            .filter(AuditLog.action == "DOCUMENT_VERIFIED")
            .count()
            == 1
        )


def test_citizen_cannot_upload_to_another_citizens_application(verification_client):
    client, ids = verification_client
    client.app.state.document_test_user["user"] = ids["other_officer"]
    response = client.post(
        "/api/v1/documents/upload-and-verify",
        data={"application_id": str(ids["application"])},
        files={"file": ("record.pdf", _pdf("Income Certificate"), "application/pdf")},
    )
    assert response.status_code == 403


def test_original_file_download_is_access_scoped_and_audited(verification_client):
    client, ids = verification_client
    client.app.state.document_test_user["user"] = ids["citizen"]
    pdf = _pdf("Income Certificate\nCertificate No: INC-0001")
    uploaded = client.post(
        "/api/v1/documents/upload-and-verify",
        data={"application_id": str(ids["application"])},
        files={"file": ("income.pdf", pdf, "application/pdf")},
    )
    assert uploaded.status_code == 201, uploaded.text
    document_id = uploaded.json()["document"]["id"]

    downloaded = client.get(f"/api/v1/documents/{document_id}/file")
    assert downloaded.status_code == 200
    assert downloaded.content == pdf
    assert downloaded.headers["content-type"] == "application/pdf"

    client.app.state.document_test_user["user"] = ids["other_officer"]
    forbidden = client.get(f"/api/v1/documents/{document_id}/file")
    assert forbidden.status_code == 403

    sessions = client.app.state.document_test_sessions
    with sessions() as db:
        assert (
            db.query(AuditLog)
            .filter(
                AuditLog.action == "DOCUMENT_ACCESSED",
                AuditLog.resource_id == document_id,
            )
            .count()
            == 1
        )
