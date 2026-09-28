from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseConnector(ABC):
    department: str
    system_name: str
    protocol: str = "REST"
    status: str = "connected"

    @abstractmethod
    def get_record(self, citizen_id: str | int, record_type: str, purpose: str | None = None) -> dict[str, Any]:
        raise NotImplementedError

    def validate_response(self, raw: dict[str, Any]) -> dict[str, Any]:
        return raw

    def normalize(self, raw: dict[str, Any], citizen_id: str | int) -> dict[str, Any]:
        return {
            "citizenId": str(citizen_id),
            "name": raw.get("full_name") or raw.get("student_name") or raw.get("name") or "Unknown Citizen",
            "dateOfBirth": raw.get("dob") or raw.get("date_of_birth") or "1970-01-01",
            "records": [
                {
                    "type": raw.get("record_type") or raw.get("document_type") or "Record",
                    "issuer": self.department,
                    "issuedDate": raw.get("issued_date") or raw.get("date_of_issue") or "2026-09-25",
                    "verificationStatus": "VERIFIED",
                    "source": self.department,
                    "sourceType": "Demo Connected System",
                }
            ],
        }
