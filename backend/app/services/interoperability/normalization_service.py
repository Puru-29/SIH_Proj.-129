from __future__ import annotations

from datetime import date, datetime
from typing import Any

from app.schemas.common_data_model import Citizen, VerificationStatus


class NormalizationService:
    def normalize(self, common_record: dict[str, Any]) -> dict[str, Any]:
        missing = common_record.get("missing_required_fields", [])
        if missing:
            raise ValueError(
                f"Source response is missing required common-model fields: {', '.join(missing)}"
            )

        date_of_birth = self._normalize_date(common_record.get("date_of_birth"))
        identifier = self._normalize_identifier(common_record.get("identifier"))
        citizen = Citizen(
            name=self._normalize_text(common_record.get("name")),
            date_of_birth=date_of_birth,
            identifier=identifier,
            source_system=self._normalize_text(common_record.get("source_system")),
            verification_status=VerificationStatus(
                common_record.get("verification_status", VerificationStatus.UNVERIFIED)
            ),
        )
        normalized = dict(common_record)
        normalized.update(citizen.model_dump(mode="json"))
        normalized["record_type"] = self._normalize_text(
            common_record.get("record_type", "Government Record")
        )
        normalized["details"] = {
            str(key): self._normalize_value(value)
            for key, value in common_record.get("details", {}).items()
            if value is not None
        }
        normalized.pop("missing_required_fields", None)
        normalized.pop("mapping_id", None)
        normalized.pop("mapping_version", None)
        return normalized

    def _normalize_value(self, value: Any) -> Any:
        if isinstance(value, datetime):
            return value.date().isoformat()
        if isinstance(value, date):
            return value.isoformat()
        if isinstance(value, str):
            value = value.strip()
            try:
                return self._normalize_date(value).isoformat()
            except ValueError:
                return value
        if isinstance(value, dict):
            return {str(key): self._normalize_value(item) for key, item in value.items()}
        if isinstance(value, (list, tuple)):
            return [self._normalize_value(item) for item in value]
        return value

    @staticmethod
    def _normalize_date(value: Any) -> date:
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value
        if not isinstance(value, str) or not value.strip():
            raise ValueError("date_of_birth is required.")
        value = value.strip()
        for pattern in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y"):
            try:
                return datetime.strptime(value, pattern).date()
            except ValueError:
                continue
        raise ValueError("date_of_birth must use an ISO or supported numeric date format.")

    @staticmethod
    def _normalize_identifier(value: Any) -> str:
        if value is None or not str(value).strip():
            raise ValueError("identifier is required.")
        return "".join(str(value).split()).upper()

    @staticmethod
    def _normalize_text(value: Any) -> str:
        if value is None or not str(value).strip():
            raise ValueError("A required common-model text field is missing.")
        return str(value).strip()

    @staticmethod
    def value_type(value: Any) -> str:
        if isinstance(value, bool):
            return "boolean"
        if isinstance(value, (int, float)):
            return "number"
        if isinstance(value, (list, dict)):
            return "json"
        return "string"
