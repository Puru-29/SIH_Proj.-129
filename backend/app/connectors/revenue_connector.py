from __future__ import annotations

from app.connectors.base_connector import BaseConnector


class RevenueConnector(BaseConnector):
    department = "Revenue Department"
    system_name = "DEMO CONNECTOR - Revenue Certificate System"
    protocol = "REST"
    status = "demo"

    def get_record(self, citizen_id: str | int, record_type: str, purpose: str | None = None) -> dict:
        fallback_name = f"Citizen {citizen_id}"
        return {
            "full_name": fallback_name,
            "dob": "10/05/2003",
            "certificate_no": "INC-92821",
            "annual_income": 240000,
            "verification_status": "VERIFIED",
            "citizen_id": str(citizen_id),
            "record_type": record_type,
            "purpose": purpose or "Scholarship eligibility",
        }

    def normalize(self, raw: dict, citizen_id: str | int) -> dict:
        dob = raw.get("dob")
        if "/" in str(dob):
            d, m, y = str(dob).split("/")
            dob = f"{y}-{m}-{d}"
        return {
            "citizenId": str(citizen_id) if str(citizen_id) else "CIT-MH-2026-10482",
            "name": raw.get("full_name") or f"Citizen {citizen_id}",
            "dateOfBirth": dob or "2003-05-10",
            "certificateId": raw.get("certificate_no") or "INC-92821",
            "annualIncome": raw.get("annual_income") or 240000,
            "sourceDepartment": self.department,
            "verified": str(raw.get("verification_status", "VERIFIED")).upper() == "VERIFIED",
        }
