from __future__ import annotations

from app.connectors.base_connector import BaseConnector


class WelfareConnector(BaseConnector):
    department = "Social Welfare Department"
    system_name = "DEMO CONNECTOR - Welfare Eligibility System"
    protocol = "REST"
    status = "demo"

    def get_record(self, citizen_id: str | int, record_type: str, purpose: str | None = None) -> dict:
        return {
            "citizen_id": str(citizen_id),
            "record_type": record_type,
            "eligibility_status": "ELIGIBLE",
            "purpose": purpose or "Scholarship eligibility",
        }
