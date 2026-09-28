from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from typing import cast

import pytest
from sqlalchemy.orm import Session

from app.models.department import Department
from app.models.consent import ConsentDataItem, ConsentStatus
from app.models.platform import ConnectedSystem
from app.schemas.consent import ConsentCreate
from app.models.service import Service
from app.services.consent_service import ConsentService
from app.services import consent_service as consent_service_module
from app.services.interoperability.validation_service import (
    InteroperabilityValidationError,
    ValidationService,
)


def _valid_consent(**overrides):
    now = datetime.now(timezone.utc)
    values = {
        "citizen_id": 7,
        "application_id": 41,
        "status": ConsentStatus.GRANTED,
        "granted_at": now,
        "expires_at": now + timedelta(hours=1),
        "revoked_at": None,
        "purpose": "Scholarship | Data requested: student enrollment",
        "data_items": [
            SimpleNamespace(
                data_key="student_enrollment",
                description="student enrollment",
            )
        ],
        "target_platform_id": 5,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _validate(consent):
    return ValidationService().validate_consent(
        consent,
        citizen_id=7,
        application_id=41,
        service=Service(
            platform_id=5,
            department=Department(name="Education", code="EDU"),
        ),
        data_requested="student enrollment",
        purpose="Scholarship",
        source_department="Education",
        requesting_department="Education",
        source_system=ConnectedSystem(
            department=Department(name="Education", code="EDU")
        ),
    )


def test_only_pending_or_explicitly_granted_consent_passes_validation():
    assert _validate(_valid_consent(status=ConsentStatus.PENDING)) == ConsentStatus.PENDING
    assert _validate(_valid_consent()) == ConsentStatus.GRANTED


@pytest.mark.parametrize(
    "overrides",
    [
        {"status": ConsentStatus.DENIED},
        {"status": ConsentStatus.REVOKED},
        {"status": ConsentStatus.EXPIRED},
        {"revoked_at": datetime.now(timezone.utc)},
        {"expires_at": datetime.now(timezone.utc) - timedelta(seconds=1)},
        {"granted_at": None},
        {"expires_at": None},
        {
            "data_items": [
                SimpleNamespace(data_key="income", description="annual income")
            ]
        },
    ],
)
def test_invalid_or_out_of_scope_consent_is_rejected(overrides):
    with pytest.raises(InteroperabilityValidationError, match="consent|Consent"):
        _validate(_valid_consent(**overrides))


def test_consent_create_rejects_client_selected_status():
    with pytest.raises(ValueError):
        ConsentCreate.model_validate(
            {
                "purpose": "Scholarship",
                "source_platform_id": 1,
                "target_platform_id": 2,
                "citizen_id": 7,
                "requested_data": "student enrollment",
                "requested_fields": ["student enrollment"],
                "status": "granted",
            }
        )


class _ConsentQuery:
    def __init__(self, value):
        self.value = value

    def filter(self, *_args):
        return self

    def with_for_update(self):
        return self

    def first(self):
        return self.value


class _FakeSession:
    def __init__(self, consent=None):
        self.consent = consent
        self.added = []

    def query(self, _model):
        return _ConsentQuery(self.consent)

    def add(self, value):
        self.added.append(value)

    def add_all(self, values):
        self.added.extend(values)

    def flush(self):
        for value in self.added:
            if hasattr(value, "purpose") and getattr(value, "id", None) is None:
                value.id = 12

    def commit(self):
        pass

    def refresh(self, _value):
        pass


def test_approval_sets_grant_and_expiration_timestamps():
    consent = SimpleNamespace(
        id=12,
        citizen_id=7,
        status=ConsentStatus.PENDING,
        granted_at=None,
        expires_at=None,
        revoked_at=None,
    )
    service = ConsentService()

    approved = service.approve(
        cast(Session, _FakeSession(consent)), 12, citizen_id=7
    )

    assert approved.status == ConsentStatus.GRANTED
    assert approved.granted_at is not None
    assert approved.expires_at is not None
    assert approved.expires_at - approved.granted_at == timedelta(hours=24)


def test_request_stores_requested_fields_and_notifies_citizen(monkeypatch):
    notifications = []
    monkeypatch.setattr(
        consent_service_module.notification_service,
        "create_notification",
        lambda **kwargs: notifications.append(kwargs),
    )
    source = ConnectedSystem(
        id=1,
        name="Revenue",
        slug="revenue",
        department_id=10,
        department=Department(id=10, name="Revenue Department", code="REV"),
    )
    target = ConnectedSystem(
        id=2,
        name="Scholarships",
        slug="scholarships",
        department_id=20,
        department=Department(id=20, name="Education Department", code="EDU"),
    )

    db = _FakeSession()
    consent = ConsentService().create_request(
        db,
        citizen_id=7,
        source_platform=source,
        target_platform=target,
        purpose="Scholarship eligibility",
        requested_data="Income and identity",
        requested_fields=["annual income", "date of birth"],
    )

    assert consent.status == ConsentStatus.PENDING
    assert consent.granted_at is None
    assert consent.expires_at is None
    items = [item for item in db.added if isinstance(item, ConsentDataItem)]
    assert [item.data_key for item in items] == [
        "annual_income",
        "date_of_birth",
    ]
    assert notifications[0]["citizen_id"] == 7
    assert notifications[0]["application_id"] is None
