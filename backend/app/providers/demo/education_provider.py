from __future__ import annotations

from app.connectors.base_connector import BaseConnector


class EducationDemoProvider(BaseConnector):
    department = "Higher & Technical Education"
    system_name = "SAMARTH Education Registry"
    protocol = "REST"
    status = "connected"

    def get_record(self, citizen_id: str | int, record_type: str, purpose: str | None = None) -> dict:
        fallback_name = f"Citizen {citizen_id}"
        return {
            "student_name": fallback_name,
            "date_of_birth": "10/05/2003",
            "student_id": "EDU-12091",
            "record_type": "Education Record",
            "date_of_issue": "2026-08-12",
            "citizen_id": str(citizen_id),
            "department": self.department,
            "purpose": purpose or "Academic verification",
        }

    def normalize(self, raw: dict, citizen_id: str | int) -> dict:
        dob = raw.get("date_of_birth")
        if "/" in str(dob):
            parts = str(dob).split("/")
            dob = f"{parts[2]}-{parts[1]}-{parts[0]}"
        return {
            "citizenId": str(citizen_id),
            "name": raw.get("student_name") or f"Citizen {citizen_id}",
            "dateOfBirth": dob or "2003-05-10",
            "records": [
                {
                    "type": "Education Record",
                    "issuer": self.department,
                    "issuedDate": raw.get("date_of_issue") or "2026-08-12",
                    "verificationStatus": "VERIFIED",
                    "source": self.department,
                    "sourceType": "Demo Connected System",
                    "identifier": raw.get("student_id") or "EDU-12091",
                }
            ],
        }
