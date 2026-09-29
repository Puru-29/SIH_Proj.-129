from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_db
from app.core.security import hash_password
from app.database import Base
from app.main import app
from app.models.application import ApplicationStatus, ServiceApplication
from app.models.audit import AuditLog
from app.models.department import Department
from app.models.document import Document
from app.models.platform import DigitalPlatform, PlatformStatus
from app.models.role import Role
from app.models.service import Service
from app.models.user import User, UserRole


@pytest.fixture
def auth_client():
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

    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    with session_factory() as db:
        roles = {
            key: Role(key=key, name=name)
            for key, name in (
                ("citizen", "Citizen"),
                ("department_officer", "Department Officer"),
                ("interoperability_admin", "Interoperability Administrator"),
                ("system_admin", "System Administrator"),
            )
        }
        revenue = Department(name="Revenue", code="REV")
        education = Department(name="Education", code="EDU")
        db.add_all([*roles.values(), revenue, education])
        db.flush()
        gateway = DigitalPlatform(
            name="Revenue Gateway",
            slug="revenue-gateway-test",
            department_id=revenue.id,
            status=PlatformStatus.ACTIVE,
        )
        education_gateway = DigitalPlatform(
            name="Education Gateway",
            slug="education-gateway-test",
            department_id=education.id,
            status=PlatformStatus.ACTIVE,
        )
        db.add_all([gateway, education_gateway])
        db.flush()
        revenue_service = Service(
            name="Revenue Service",
            code="REV-TEST",
            department_id=revenue.id,
            platform_id=gateway.id,
        )
        education_service = Service(
            name="Education Service",
            code="EDU-TEST",
            department_id=education.id,
            platform_id=education_gateway.id,
        )
        db.add_all([revenue_service, education_service])
        admin = User(
            full_name="System Admin",
            email="admin@example.com",
            role=UserRole.ADMIN,
            role_id=roles["system_admin"].id,
            hashed_password=hash_password("AdminPass123!"),
            is_active=True,
        )
        citizen = User(
            full_name="Test Citizen",
            email="citizen@example.com",
            role=UserRole.CITIZEN,
            role_id=roles["citizen"].id,
            hashed_password=hash_password("CitizenPass123!"),
            is_active=True,
        )
        other_citizen = User(
            full_name="Other Citizen",
            email="other@example.com",
            role=UserRole.CITIZEN,
            role_id=roles["citizen"].id,
            hashed_password=hash_password("OtherPass123!"),
            is_active=True,
        )
        db.add_all([admin, citizen, other_citizen])
        db.flush()
        own_application = ServiceApplication(
            reference_id="APP-REVENUE-1",
            citizen_id=other_citizen.id,
            service_id=revenue_service.id,
            department_id=revenue.id,
            status=ApplicationStatus.SUBMITTED,
        )
        restricted_application = ServiceApplication(
            reference_id="APP-EDUCATION-1",
            citizen_id=other_citizen.id,
            service_id=education_service.id,
            department_id=education.id,
            status=ApplicationStatus.SUBMITTED,
        )
        other_document = Document(
            title="Other citizen document",
            doc_type="identity",
            file_path="virtual://other",
            owner_id=other_citizen.id,
        )
        citizen_document = Document(
            title="Citizen's document",
            doc_type="identity",
            file_path="virtual://citizen",
            owner_id=citizen.id,
        )
        db.add_all(
            [own_application, restricted_application, other_document, citizen_document]
        )
        db.add(
            AuditLog(
                action="AUTH_FIXTURE",
                entity_type="test",
                entity_id="auth-fixture",
                details="Authentication access test.",
                actor_id=admin.id,
                occurred_at=datetime.now(timezone.utc),
            )
        )
        db.commit()
        department_id = revenue.id
        own_application_id = own_application.id
        restricted_application_id = restricted_application.id
        document_id = other_document.id
        citizen_document_id = citizen_document.id

    def override_get_db():
        with session_factory() as db:
            yield db

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        yield (
            client,
            department_id,
            own_application_id,
            restricted_application_id,
            document_id,
            citizen_document_id,
        )
    app.dependency_overrides.pop(get_db, None)
    engine.dispose()


def test_registration_login_refresh_logout_and_role_escalation_rejection(auth_client):
    client, *_ = auth_client
    rejected_privilege = client.post(
        "/api/v1/auth/signup",
        json={
            "full_name": "Injected Admin",
            "email": "injected@example.com",
            "password": "SafePass123!",
            "role": "system_admin",
        },
    )
    assert rejected_privilege.status_code == 422

    registered = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "New Citizen",
            "email": "NEW.CITIZEN@example.com",
            "password": "SafePass123!",
        },
    )
    assert registered.status_code == 201
    assert registered.json()["expires_in"] == 15 * 60
    assert registered.json()["user"]["role"] == "citizen"
    assert registered.cookies.get("govflow_refresh_token")
    assert "httponly" in registered.headers["set-cookie"].lower()
    access_token = registered.json()["access_token"]
    assert client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {access_token}"}
    ).json()["email"] == "new.citizen@example.com"

    blocked_login = client.post(
        "/api/v1/auth/login",
        headers={"Origin": "https://untrusted.example"},
        json={"email": "new.citizen@example.com", "password": "SafePass123!"},
    )
    assert blocked_login.status_code == 403

    old_refresh = registered.cookies["govflow_refresh_token"]
    client.cookies.set(
        "govflow_refresh_token",
        old_refresh,
        path="/api/v1/auth",
    )
    blocked_refresh = client.post(
        "/api/v1/auth/refresh",
        headers={"Origin": "https://untrusted.example"},
    )
    assert blocked_refresh.status_code == 403
    refreshed = client.post(
        "/api/v1/auth/refresh",
    )
    assert refreshed.status_code == 200
    new_access_token = refreshed.json()["access_token"]
    assert new_access_token != access_token

    client.cookies.set(
        "govflow_refresh_token",
        old_refresh,
        path="/api/v1/auth",
    )
    replayed = client.post("/api/v1/auth/refresh")
    assert replayed.status_code == 401
    assert client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {new_access_token}"}
    ).status_code == 401

    relogin = client.post(
        "/api/v1/auth/login",
        json={"email": "new.citizen@example.com", "password": "SafePass123!"},
    )
    assert relogin.status_code == 200
    new_access_token = relogin.json()["access_token"]
    logged_out = client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {new_access_token}"},
    )
    assert logged_out.status_code == 204
    assert client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {new_access_token}"}
    ).status_code == 401
    assert client.post("/api/v1/auth/refresh").status_code == 401

    invalid_login = client.post(
        "/api/v1/auth/login",
        json={"email": "new.citizen@example.com", "password": "Incorrect123!"},
    )
    assert invalid_login.status_code == 401
    valid_login = client.post(
        "/api/v1/auth/login",
        json={"email": "new.citizen@example.com", "password": "SafePass123!"},
    )
    assert valid_login.status_code == 200


def test_backend_role_and_department_ownership_enforcement(auth_client):
    (
        client,
        department_id,
        own_application_id,
        restricted_application_id,
        document_id,
        citizen_document_id,
    ) = auth_client
    unauthenticated = client.get("/api/v1/applications")
    assert unauthenticated.status_code == 401

    citizen_login = client.post(
        "/api/v1/auth/login",
        json={"email": "citizen@example.com", "password": "CitizenPass123!"},
    )
    citizen_token = citizen_login.json()["access_token"]
    citizen_headers = {"Authorization": f"Bearer {citizen_token}"}
    assert client.get("/api/v1/auth/users", headers=citizen_headers).status_code == 403
    assert client.get("/api/v1/platforms", headers=citizen_headers).status_code == 403
    assert client.get("/api/v1/audit-logs", headers=citizen_headers).status_code == 403
    assert client.get(
        f"/api/v1/documents/{document_id}", headers=citizen_headers
    ).status_code == 403
    assert client.get(
        f"/api/v1/documents/{citizen_document_id}", headers=citizen_headers
    ).status_code == 200
    assert client.get(
        "/api/v1/applications?citizen_id=3", headers=citizen_headers
    ).status_code == 403

    admin_login = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "AdminPass123!"},
    )
    admin_headers = {
        "Authorization": f"Bearer {admin_login.json()['access_token']}"
    }
    assert client.get("/api/v1/auth/users", headers=admin_headers).status_code == 200
    assert client.get("/api/v1/audit-logs", headers=admin_headers).status_code == 200
    citizen_login_audit = client.get(
        "/api/v1/audit-logs?action=LOGIN&actor=2",
        headers=admin_headers,
    )
    assert citizen_login_audit.status_code == 200
    assert any(
        row["actor_role"] == "citizen" and row["result"] == "success"
        for row in citizen_login_audit.json()
    )
    created_officer = client.post(
        "/api/v1/auth/users",
        headers=admin_headers,
        json={
            "full_name": "Revenue Officer",
            "email": "officer@example.com",
            "password": "OfficerPass123!",
            "role": "department_officer",
            "department_id": department_id,
        },
    )
    assert created_officer.status_code == 201
    assert created_officer.json()["role"] == "department_officer"
    created_audit = client.get(
        "/api/v1/audit-logs?action=USER_CREATED",
        headers=admin_headers,
    )
    assert created_audit.status_code == 200
    assert created_audit.json()[0]["actor_id"] == 1
    officer_login = client.post(
        "/api/v1/auth/login",
        json={"email": "officer@example.com", "password": "OfficerPass123!"},
    )
    officer_headers = {
        "Authorization": f"Bearer {officer_login.json()['access_token']}"
    }
    assert client.get(
        f"/api/v1/applications/{own_application_id}",
        headers=officer_headers,
    ).status_code == 200
    assert client.get(
        f"/api/v1/applications/{restricted_application_id}",
        headers=officer_headers,
    ).status_code == 403
    deactivated = client.patch(
        f"/api/v1/auth/users/{created_officer.json()['id']}",
        headers=admin_headers,
        json={"is_active": False},
    )
    assert deactivated.status_code == 200
    assert client.get(
        f"/api/v1/applications/{own_application_id}",
        headers=officer_headers,
    ).status_code == 401


def test_staff_account_request_requires_admin_approval(auth_client):
    client, department_id, *_ = auth_client
    request_payload = {
        "full_name": "Pending Officer",
        "email": "pending.officer@example.com",
        "password": "OfficerPass123!",
        "role": "department_officer",
        "department_id": department_id,
    }

    requested = client.post("/api/v1/auth/staff-requests", json=request_payload)
    assert requested.status_code == 202
    assert "administrator must approve" in requested.json()["message"]

    blocked_login = client.post(
        "/api/v1/auth/login",
        json={"email": request_payload["email"], "password": request_payload["password"]},
    )
    assert blocked_login.status_code == 403

    admin_login = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "AdminPass123!"},
    )
    admin_headers = {
        "Authorization": f"Bearer {admin_login.json()['access_token']}"
    }
    users = client.get("/api/v1/auth/users", headers=admin_headers)
    assert users.status_code == 200
    pending_user = next(user for user in users.json() if user["email"] == request_payload["email"])
    pending_user_id = pending_user["id"]
    assert pending_user["is_active"] is False
    assert pending_user["staff_request_pending"] is True

    approved = client.patch(
        f"/api/v1/auth/users/{pending_user_id}",
        headers=admin_headers,
        json={"is_active": True},
    )
    assert approved.status_code == 200
    assert approved.json()["is_active"] is True
    assert approved.json()["staff_request_pending"] is False

    successful_login = client.post(
        "/api/v1/auth/login",
        json={"email": request_payload["email"], "password": request_payload["password"]},
    )
    assert successful_login.status_code == 200


def test_staff_account_request_cannot_request_admin_role(auth_client):
    client, *_ = auth_client
    response = client.post(
        "/api/v1/auth/staff-requests",
        json={
            "full_name": "Unapproved Admin",
            "email": "request.admin@example.com",
            "password": "AdminPass123!",
            "role": "system_admin",
        },
    )
    assert response.status_code == 422


def test_citizen_application_sources_do_not_require_platform_admin_access(auth_client):
    client, department_id, *_ = auth_client
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "citizen@example.com", "password": "CitizenPass123!"},
    )
    assert login.status_code == 200
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    services = client.get("/api/v1/services", headers=headers)
    assert services.status_code == 200
    service = next(
        item for item in services.json() if item["name"] == "Revenue Service"
    )
    service_id = service["id"]

    admin_platforms = client.get("/api/v1/platforms", headers=headers)
    assert admin_platforms.status_code == 403

    admin_login = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "AdminPass123!"},
    )
    admin_headers = {
        "Authorization": f"Bearer {admin_login.json()['access_token']}"
    }
    platforms = client.get("/api/v1/platforms", headers=admin_headers)
    assert platforms.status_code == 200
    revenue_platform = next(
        item for item in platforms.json() if item["department_id"] == department_id
    )
    workflow = client.post(
        "/api/v1/workflows",
        headers=admin_headers,
        json={
            "service_id": service_id,
            "name": "Revenue data request",
            "steps": [
                {
                    "step_id": "income_request",
                    "name": "Verify income",
                    "department": "Revenue",
                    "type": "DATA_REQUEST",
                    "order": 0,
                    "action": {},
                }
            ],
        },
    )
    assert workflow.status_code == 201

    application_sources = client.get(
        f"/api/v1/services/{service_id}/application-sources",
        headers=headers,
    )
    assert application_sources.status_code == 200
    assert application_sources.json() == [
        {
            "department": "Revenue",
            "department_id": department_id,
            "platform_id": revenue_platform["id"],
        }
    ]


def test_citizens_can_create_and_list_only_their_own_grievances(auth_client):
    client, *_ = auth_client
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "citizen@example.com", "password": "CitizenPass123!"},
    )
    assert login.status_code == 200
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    created = client.post(
        "/api/v1/grievances",
        headers=headers,
        json={
            "category": "Application delay",
            "relatedApplication": "APP-REVENUE-1",
            "department": "Revenue",
            "description": "Please provide an update on my application.",
            "priority": "High",
        },
    )
    assert created.status_code == 201
    assert created.json()["id"]
    assert created.json()["relatedApplication"] == "APP-REVENUE-1"
    assert created.json()["status"] == "Submitted"

    listed = client.get("/api/v1/grievances", headers=headers)
    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()] == [created.json()["id"]]

    unauthenticated = client.get("/api/v1/grievances")
    assert unauthenticated.status_code == 401
    invalid = client.post(
        "/api/v1/grievances",
        headers=headers,
        json={"category": " ", "description": " "},
    )
    assert invalid.status_code == 422
