from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.models.application import ServiceApplication
from app.models.consent import ConsentStatus, DataShareConsent
from app.models.platform import ConnectedSystem
from app.models.service import Service
from app.models.user import User


class InteroperabilityValidationError(ValueError):
    def __init__(self, message: str, *, category: str = "VALIDATION"):
        super().__init__(message)
        self.category = category


class ValidationService:
    def validate_authenticated_user(self, user: User | None, citizen_id: int) -> User:
        if user is None or not user.is_active or user.id != citizen_id:
            raise InteroperabilityValidationError(
                "The authenticated user is not authorized for this request.",
                category="AUTHENTICATION",
            )
        return user

    def validate_application(
        self,
        application: ServiceApplication | None,
        *,
        citizen_id: int,
        service_id: int,
    ) -> ServiceApplication:
        if application is None:
            raise InteroperabilityValidationError("Application not found.", category="APPLICATION")
        if application.citizen_id != citizen_id or application.service_id != service_id:
            raise InteroperabilityValidationError(
                "Application does not belong to this citizen and service.",
                category="APPLICATION",
            )
        return application

    def validate_consent(
        self,
        consent: DataShareConsent | None,
        *,
        citizen_id: int,
        application_id: int,
        service: Service | None,
        data_requested: str,
        purpose: str,
        source_department: str,
        requesting_department: str,
        source_system: ConnectedSystem | None,
    ) -> ConsentStatus:
        if consent is None or consent.citizen_id != citizen_id:
            raise InteroperabilityValidationError(
                "A matching citizen consent is required before data exchange.",
                category="CONSENT",
            )
        if consent.application_id is not None and consent.application_id != application_id:
            raise InteroperabilityValidationError(
                "Consent does not authorize access for this application.",
                category="CONSENT",
            )
        if consent.status not in {ConsentStatus.PENDING, ConsentStatus.GRANTED}:
            raise InteroperabilityValidationError(
                "The consent is not approved for this data request.", category="CONSENT"
            )
        if consent.revoked_at is not None:
            raise InteroperabilityValidationError(
                "The consent has been revoked.", category="CONSENT"
            )

        normalized_purpose = consent.purpose.strip().casefold()
        requested_scope = f"data requested: {data_requested}".casefold()
        if purpose.strip().casefold() not in normalized_purpose:
            raise InteroperabilityValidationError(
                "Consent purpose does not match this data request.", category="CONSENT"
            )
        if requested_scope not in normalized_purpose and data_requested.casefold() not in normalized_purpose:
            raise InteroperabilityValidationError(
                "Consent does not include the requested data scope.", category="CONSENT"
            )

        expires_at = consent.expires_at
        if consent.status == ConsentStatus.GRANTED and (
            consent.granted_at is None or expires_at is None
        ):
            raise InteroperabilityValidationError(
                "Approved consent must have grant and expiration timestamps.",
                category="CONSENT",
            )
        if expires_at is not None:
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            if expires_at <= datetime.now(timezone.utc):
                raise InteroperabilityValidationError(
                    "The consent has expired.", category="CONSENT"
                )

        if consent.data_items:
            requested_key = "_".join(data_requested.strip().casefold().split())
            permitted = any(
                item.data_key.casefold() == requested_key
                or item.description.strip().casefold() == data_requested.strip().casefold()
                for item in consent.data_items
            )
            if not permitted:
                raise InteroperabilityValidationError(
                    "Consent does not authorize the requested data fields.",
                    category="CONSENT",
                )

        if service is None or service.platform_id != consent.target_platform_id:
            raise InteroperabilityValidationError(
                "Consent does not authorize access for this service.", category="CONSENT"
            )
        if not self._same_department(
            source_department,
            source_system.department.name if source_system and source_system.department else "",
        ):
            raise InteroperabilityValidationError(
                "Consent source department does not match this data request.",
                category="CONSENT",
            )
        service_department = service.department.name if service.department else ""
        if not self._same_department(requesting_department, service_department):
            raise InteroperabilityValidationError(
                "Requesting department does not match the service department.",
                category="CONSENT",
            )
        return consent.status

    def validate_source_response(self, raw: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(raw, dict) or not raw:
            raise InteroperabilityValidationError(
                "The source system returned an empty or invalid response.",
                category="SOURCE_RESPONSE",
            )
        if not any(value is not None and value != "" for value in raw.values()):
            raise InteroperabilityValidationError(
                "The source system response contains no usable data.",
                category="SOURCE_RESPONSE",
            )
        return raw

    @staticmethod
    def _same_department(left: str, right: str) -> bool:
        compact = lambda value: "".join(character for character in value.casefold() if character.isalnum())
        left_key = compact(left)
        right_key = compact(right)
        return bool(left_key and right_key and (left_key in right_key or right_key in left_key))
