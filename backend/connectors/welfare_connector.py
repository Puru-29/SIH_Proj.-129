from __future__ import annotations

from typing import Any

from connectors.base_connector import LocalDepartmentConnector


class WelfareConnector(LocalDepartmentConnector):
    department = "Social Welfare Department"
    system_name = "Local Welfare Eligibility Adapter"
    record_id_field = "eligibility_id"
    mapping_key = "welfare"

    def get_record(
        self,
        citizen_id: str | int,
        record_type: str,
        purpose: str | None = None,
    ) -> dict[str, Any]:
        return self._remember_record(
            citizen_id,
            {
                "applicant_name": f"Citizen {citizen_id}",
                "eligibility_id": f"WEL-{citizen_id}-001",
                "scheme_name": record_type,
                "eligibility_status": "ELIGIBLE",
            },
        )
