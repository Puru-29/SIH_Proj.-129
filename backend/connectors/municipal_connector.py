from __future__ import annotations

from typing import Any

from connectors.base_connector import LocalDepartmentConnector


class MunicipalConnector(LocalDepartmentConnector):
    department = "Municipal Department"
    system_name = "Local Municipal Property Adapter"
    record_id_field = "property_id"
    mapping_key = "municipal"

    def get_record(
        self,
        citizen_id: str | int,
        record_type: str,
        purpose: str | None = None,
    ) -> dict[str, Any]:
        return self._remember_record(
            citizen_id,
            {
                "owner_name": f"Citizen {citizen_id}",
                "property_id": f"MUN-{citizen_id}-10482",
                "assessment_status": "VERIFIED",
            },
        )
