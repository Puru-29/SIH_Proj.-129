from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.api.deps import require_authenticated_user
import app.services.interoperability_service as interoperability_module
from app.models.consent import ConsentStatus, DataShareConsent
from app.models.service import Service
from app.models.application import ServiceApplication
from app.models.transaction import InteroperabilityTransaction
from app.providers.demo.municipal_provider import MunicipalDemoProvider
from app.providers.demo.revenue_provider import RevenueDemoProvider
from app.services.interoperability_service import InteroperabilityService
from app.models.user import User, UserRole

client = TestClient(app)


def test_integrations_registry_endpoint_returns_demo_sources(monkeypatch):
    monkeypatch.setattr(interoperability_module.settings, "data_mode", "demo")
    monkeypatch.setitem(
        app.dependency_overrides,
        require_authenticated_user,
        lambda: User(
            id=1,
            full_name="Test Interoperability Administrator",
            email="interop@example.com",
            role=UserRole.OPERATOR,
            hashed_password="unused",
            is_active=True,
        ),
    )
    response = client.get('/api/v1/integrations')
    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload, list)
    assert len(payload) >= 3
    first = payload[0]
    assert 'department' in first
    assert 'systemName' in first or 'name' in first
    assert 'status' in first


def test_service_catalog_seeds_requested_service_owners():
    services = client.get('/api/v1/services').json()
    departments = client.get('/api/v1/departments').json()
    department_names = {department['id']: department['name'] for department in departments}
    by_name = {service['name']: service for service in services}

    assert department_names[by_name['Post-Matric Scholarship']['department_id']] == 'Social Welfare Department'
    assert 'transport' in department_names[by_name['Driving Licence']['department_id']].casefold()
    assert department_names[by_name['Property Verification']['department_id']] == 'Municipal Department'

    service_names = (
        "Income Certificate",
        "Post-Matric Scholarship",
        "Driving Licence",
        "Property Verification",
    )
    schemas = {
        name: client.get(f"/api/v1/services/{by_name[name]['id']}/form-schema").json()
        for name in service_names
    }
    schema_fields = {
        name: {field["id"] for field in schema["fields"]}
        for name, schema in schemas.items()
    }
    assert "family_income" in schema_fields["Income Certificate"]
    assert "institution" in schema_fields["Post-Matric Scholarship"]
    assert "driving_category" in schema_fields["Driving Licence"]
    assert "property_id" in schema_fields["Property Verification"]
    assert len({tuple(schema["workflow"]) for schema in schemas.values()}) == 4


def test_every_service_card_has_a_distinct_backend_form_and_workflow():
    services = client.get("/api/v1/services").json()
    by_name = {service["name"]: service for service in services}
    card_to_backend = {
        "Income Certificate": "Income Certificate",
        "Domicile Certificate": "Residence Certificate",
        "Caste Certificate": "Caste Certificate",
        "Land Record Verification": "Land Record Verification",
        "Scholarship": "Post-Matric Scholarship",
        "Student Verification": "Student Verification",
        "Education Certificate": "Education Certificate",
        "Driving Licence": "Driving Licence",
        "Vehicle Registration": "Vehicle Registration",
        "Licence Verification": "Licence Verification",
        "Pension": "Senior Citizen Pension",
        "Welfare Scheme": "Direct Benefit Subsidy",
        "Scholarship Assistance": "Scholarship Assistance",
        "Birth Certificate": "Birth Certificate",
        "Death Certificate": "Death Certificate",
        "Property Verification": "Property Verification",
        "Employment Registration": "Employment Registration",
        "Skill Verification": "Skill Verification",
        "Employment Certificate": "Employment Certificate",
    }
    distinguishing_fields = {
        "Income Certificate": "family_income",
        "Domicile Certificate": "residing_since",
        "Caste Certificate": "family_category",
        "Land Record Verification": "land_record_type",
        "Scholarship": "institution",
        "Student Verification": "student_id",
        "Education Certificate": "certificate_type",
        "Driving Licence": "driving_category",
        "Vehicle Registration": "chassis_number",
        "Licence Verification": "licence_number",
        "Pension": "pension_status",
        "Welfare Scheme": "subsidy_type",
        "Scholarship Assistance": "institution",
        "Birth Certificate": "child_name",
        "Death Certificate": "deceased_name",
        "Property Verification": "property_id",
        "Employment Registration": "highest_qualification",
        "Skill Verification": "skill_name",
        "Employment Certificate": "employment_status",
    }
    missing = set(card_to_backend.values()) - set(by_name)
    assert not missing, f"Missing backend service entries: {sorted(missing)}"

    schemas = {
        card_name: client.get(f"/api/v1/services/{by_name[backend_name]['id']}/form-schema").json()
        for card_name, backend_name in card_to_backend.items()
    }
    for name, schema in schemas.items():
        assert schema["fields"], f"{name} has no form fields"
        assert len(schema["workflow"]) >= 3, f"{name} has no configured application workflow"
        field_map = {field["id"]: field for field in schema["fields"]}
        distinguishing_field = distinguishing_fields[name]
        assert distinguishing_field in field_map, (
            f"{name} is missing service-specific field {distinguishing_field}"
        )
        if name in {"Licence Verification", "Birth Certificate"}:
            assert field_map["date_of_birth"]["type"] == "date"

    workflows = {tuple(schema["workflow"]) for schema in schemas.values()}
    assert len(workflows) == len(schemas), "Each service card must have its own workflow."


def test_interoperability_request_requires_authenticated_citizen():
    response = client.post(
        '/api/v1/interoperability/request',
        json={
            'citizen_id': 1,
            'service_id': 1,
            'application_id': 1,
            'consent_id': 1,
            'requesting_department': 'Social Welfare',
            'source_department': 'Revenue & Land Records',
            'data_requested': 'Income Certificate',
            'purpose': 'Scholarship eligibility',
        },
    )
    assert response.status_code == 401


def test_interoperability_rejects_missing_consent_before_provider_fetch(monkeypatch):
    monkeypatch.setattr(interoperability_module.settings, "data_mode", "demo")
    service = InteroperabilityService()
    application = SimpleNamespace(id=12, citizen_id=4, service_id=8)
    monkeypatch.setattr(service, '_ensure_application', lambda _: application)

    class Query:
        def filter(self, *_args):
            return self

        def first(self):
            return None

    class Session:
        def query(self, *_args):
            return Query()

        def close(self):
            pass

    monkeypatch.setattr(interoperability_module, 'SessionLocal', lambda: Session())
    fetched = []
    monkeypatch.setattr(service, 'fetch_record', lambda *args: fetched.append(args))

    with pytest.raises(ValueError, match="consent"):
        service.request_interoperability(
            citizen_id=4,
            service_id=8,
            application_id=12,
            consent_id=999,
            requesting_department="Social Welfare",
            source_department="Revenue",
            data_requested="Income Certificate",
            purpose="Scholarship eligibility",
        )

    assert fetched == []


@pytest.mark.parametrize(
    ("status", "expires_at", "message"),
    [
        (ConsentStatus.DENIED, datetime.now(timezone.utc) + timedelta(hours=1), "not active"),
        (ConsentStatus.GRANTED, datetime.now(timezone.utc) - timedelta(seconds=1), "expired"),
    ],
)
def test_interoperability_rejects_denied_or_expired_consent(
    monkeypatch,
    status,
    expires_at,
    message,
):
    monkeypatch.setattr(interoperability_module.settings, "data_mode", "demo")
    service = InteroperabilityService()
    application = SimpleNamespace(id=12, citizen_id=4, service_id=8)
    consent = SimpleNamespace(
        id=44,
        citizen_id=4,
        purpose="Property verification | Data requested: Property assessment and ownership record",
        status=status,
        expires_at=expires_at,
    )

    class Query:
        def filter(self, *_args):
            return self

        def first(self):
            return consent

    class Session:
        def query(self, *_args):
            return Query()

        def close(self):
            pass

    monkeypatch.setattr(service, "_ensure_application", lambda _: application)
    monkeypatch.setattr(interoperability_module, "SessionLocal", lambda: Session())
    fetched = []
    monkeypatch.setattr(service, "fetch_record", lambda *args: fetched.append(args))

    with pytest.raises(ValueError, match=message):
        service.request_interoperability(
            citizen_id=4,
            service_id=8,
            application_id=12,
            consent_id=44,
            requesting_department="Municipal",
            source_department="Municipal",
            data_requested="Property assessment and ownership record",
            purpose=consent.purpose,
        )

    assert fetched == []


def test_revenue_provider_returns_service_specific_record_types():
    provider = RevenueDemoProvider()

    address = provider.get_record(4, "Verified residential address", "Driving licence address verification")
    land = provider.get_record(4, "Land title and survey record", "Property ownership cross-verification")
    income = provider.get_record(4, "Verified household income record", "Scholarship means-test")

    assert address["record_type"] == "Address Record"
    assert land["record_type"] == "Land Record"
    assert income["record_type"] == "Income Certificate"
    assert provider.normalize(address, 4)["records"][0]["type"] == "Address Record"


def test_municipal_provider_returns_property_record():
    provider = MunicipalDemoProvider()

    record = provider.get_record(4, "Property assessment and ownership record")
    normalized = provider.normalize(record, 4)

    assert normalized["records"][0]["type"] == "Property Record"
    assert normalized["records"][0]["source"] == "Municipal Department"


def test_interoperability_uses_persisted_consent_and_records_transaction(monkeypatch):
    monkeypatch.setattr(interoperability_module.settings, "data_mode", "demo")
    service = InteroperabilityService()
    application = SimpleNamespace(
        id=12,
        citizen_id=4,
        service_id=8,
        status=None,
        remarks="",
        workflow_run=SimpleNamespace(
            steps=[
                SimpleNamespace(
                    name="Municipal Property Verification",
                    status="pending",
                    detail="",
                    attempts=0,
                    started_at=None,
                    completed_at=None,
                )
            ]
        ),
    )
    consent = SimpleNamespace(
        id=44,
        citizen_id=4,
        purpose="Property verification | Data requested: Property assessment and ownership record",
        status=ConsentStatus.GRANTED,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        source_platform_id=3,
        source_platform=SimpleNamespace(department=SimpleNamespace(name="Municipal Department")),
        target_platform_id=4,
    )
    target_service = SimpleNamespace(
        platform_id=4,
        department=SimpleNamespace(name="Municipal Department"),
    )
    sessions = []

    class Query:
        def __init__(self, result):
            self.result = result

        def filter(self, *_args):
            return self

        def first(self):
            return self.result

    class Session:
        def __init__(self):
            self.added = []
            sessions.append(self)

        def query(self, model):
            if model is DataShareConsent:
                return Query(consent)
            if model is Service:
                return Query(target_service)
            if model is ServiceApplication:
                return Query(application)
            raise AssertionError(f"Unexpected query: {model}")

        def add(self, row):
            self.added.append(row)

        def add_all(self, rows):
            self.added.extend(rows)

        def flush(self):
            for row in self.added:
                if isinstance(row, InteroperabilityTransaction) and row.id is None:
                    row.id = 1

        def commit(self):
            pass

        def close(self):
            pass

    monkeypatch.setattr(service, "_ensure_application", lambda _: application)
    monkeypatch.setattr(interoperability_module, "SessionLocal", Session)
    monkeypatch.setattr(
        service,
        "fetch_record",
        lambda *_args: {
            "raw": {"property_id": "MUN-1"},
            "normalized": {"records": [{"type": "Property Record"}]},
            "validation": {"status": "passed"},
            "timestamp": "2026-09-25T10:00:00Z",
        },
    )
    monkeypatch.setattr(
        interoperability_module.notification_service,
        "create_notification",
        lambda **_kwargs: {"id": "notification-1"},
    )

    result = service.request_interoperability(
        citizen_id=4,
        service_id=8,
        application_id=12,
        consent_id=44,
        requesting_department="Municipal",
        source_department="Municipal",
        data_requested="Property assessment and ownership record",
        purpose="Property verification | Data requested: Property assessment and ownership record",
    )

    assert result["status"] == "success"
    assert result["consentId"] == 44
    assert any(isinstance(row, InteroperabilityTransaction) for session in sessions for row in session.added)
    assert application.workflow_run.steps[0].status == "completed"
