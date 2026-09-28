from __future__ import annotations

from typing import Any

from connectors.base_connector import LocalDepartmentConnector


class RevenueConnector(LocalDepartmentConnector):
    department = "Revenue & Land Records"
    system_name = "Local Revenue Records Adapter"
    record_id_field = "income_certificate_no"
    mapping_key = "revenue"

    def get_record(
        self,
        citizen_id: str | int,
        record_type: str,
        purpose: str | None = None,
    ) -> dict[str, Any]:
        return self._remember_record(
            citizen_id,
            {
                "full_name": f"Citizen {citizen_id}",
                "dob": "10/05/2003",
                "income_certificate_no": f"INC-{citizen_id}-92821",
                "annual_income": 240000,
            },
        )
