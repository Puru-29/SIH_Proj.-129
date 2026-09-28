from __future__ import annotations

from typing import Any

from connectors.base_connector import LocalDepartmentConnector


class TransportConnector(LocalDepartmentConnector):
    department = "Transport & Motor Vehicles"
    system_name = "Local Transport Records Adapter"
    record_id_field = "licenseNumber"
    mapping_key = "transport"

    def get_record(
        self,
        citizen_id: str | int,
        record_type: str,
        purpose: str | None = None,
    ) -> dict[str, Any]:
        return self._remember_record(
            citizen_id,
            {
                "applicantName": f"Citizen {citizen_id}",
                "birthDate": "2003-05-10",
                "licenseNumber": f"MH-12-{citizen_id}-009821",
            },
        )
