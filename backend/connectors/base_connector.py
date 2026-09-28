from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseConnector(ABC):
    """Interface to a department source system; responses retain its native schema."""

    department: str
    system_name: str
    record_id_field: str
    mapping_key: str

    @abstractmethod
    def get_record(
        self,
        citizen_id: str | int,
        record_type: str,
        purpose: str | None = None,
    ) -> dict[str, Any]:
        """Fetch one native source-system record."""
        raise NotImplementedError

    @abstractmethod
    def verify_record(
        self, citizen_id: str | int, record: dict[str, Any]
    ) -> bool:
        """Verify that a previously retrieved record belongs to this request."""
        raise NotImplementedError

    @abstractmethod
    def health_check(self) -> dict[str, Any]:
        """Report connector availability and its execution mode."""
        raise NotImplementedError


class LocalDepartmentConnector(BaseConnector):
    """Shared safeguards for local adapters; replace source access for authorized APIs."""

    execution_mode = "local"

    def __init__(self) -> None:
        self._issued_records: set[tuple[str, str]] = set()

    def _remember_record(
        self, citizen_id: str | int, record: dict[str, Any]
    ) -> dict[str, Any]:
        record_id = record.get(self.record_id_field)
        if record_id is not None and str(record_id).strip():
            self._issued_records.add((str(citizen_id), str(record_id)))
        return record

    def verify_record(self, citizen_id: str | int, record: dict[str, Any]) -> bool:
        record_id = record.get(self.record_id_field)
        return (
            record_id is not None
            and (str(citizen_id), str(record_id)) in self._issued_records
        )

    def health_check(self) -> dict[str, Any]:
        return {
            "status": "healthy",
            "mode": self.execution_mode,
            "system": self.system_name,
        }
