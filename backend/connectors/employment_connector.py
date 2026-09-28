from __future__ import annotations

from typing import Any

from connectors.base_connector import LocalDepartmentConnector


class EmploymentConnector(LocalDepartmentConnector):
    department = "Employment Department"
    system_name = "Local Employment Records Adapter"
    record_id_field = "employment_id"
    mapping_key = "employment"

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
                "date_of_birth": "2003-05-10",
                "employment_id": f"EMP-{citizen_id}-001",
                "employer_name": "Local Employment Registry Sample Employer",
                "employment_status": "ACTIVE",
                "occupation": "Sample occupation",
            },
        )
