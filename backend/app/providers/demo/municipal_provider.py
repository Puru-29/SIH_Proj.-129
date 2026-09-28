from __future__ import annotations

from app.connectors.base_connector import BaseConnector


class MunicipalDemoProvider(BaseConnector):
    department = "Municipal Department"
    system_name = "Demo Municipal Property Registry"
    protocol = "REST"
    status = "connected"

    def get_record(self, citizen_id: str | int, record_type: str, purpose: str | None = None) -> dict:
        return {
            "citizen_id": str(citizen_id),
            "owner_name": f"Citizen {citizen_id}",
            "property_id": "MUN-PROP-10482",
            "assessment_status": "Verified",
            "record_type": "Property Record",
            "purpose": purpose or record_type,
            "date_of_issue": "2026-09-05",
        }

    def normalize(self, raw: dict, citizen_id: str | int) -> dict:
        return {
            "citizenId": str(citizen_id),
            "name": raw.get("owner_name") or f"Citizen {citizen_id}",
            "records": [
                {
                    "type": raw.get("record_type", "Property Record"),
                    "issuer": self.department,
                    "issuedDate": raw.get("date_of_issue"),
                    "verificationStatus": raw.get("assessment_status", "Verified").upper(),
                    "source": self.department,
                    "sourceType": "Demo Connected System",
                    "identifier": raw.get("property_id"),
                    "details": {
                        key: value
                        for key, value in raw.items()
                        if key not in {"citizen_id", "owner_name", "date_of_issue", "purpose"}
                    },
                }
            ],
        }
