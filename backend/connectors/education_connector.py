from __future__ import annotations

from typing import Any

from connectors.base_connector import LocalDepartmentConnector


class EducationConnector(LocalDepartmentConnector):
    department = "Higher & Technical Education"
    system_name = "Local Education Registry Adapter"
    record_id_field = "student_id"
    mapping_key = "education"

    def get_record(
        self,
        citizen_id: str | int,
        record_type: str,
        purpose: str | None = None,
    ) -> dict[str, Any]:
        return self._remember_record(
            citizen_id,
            {
                "student_name": f"Citizen {citizen_id}",
                "date_of_birth": "10/05/2003",
                "student_id": f"EDU-{citizen_id}-12091",
                "institution": "Local Education Registry Sample Institution",
            },
        )
