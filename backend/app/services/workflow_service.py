from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


class WorkflowService:
    def __init__(self):
        self.transitions = [
            'CONSENT_PENDING',
            'CONSENT_GRANTED',
            'DATA_REQUESTED',
            'DATA_RECEIVED',
            'DATA_VALIDATED',
            'DATA_NORMALIZED',
            'APPLICATION_UPDATED',
            'COMPLETED',
        ]

    def build_workflow(self, application_id: int | str) -> list[dict[str, Any]]:
        now = datetime.now(timezone.utc).isoformat()
        return [
            {"state": "CONSENT_PENDING", "timestamp": now, "status": "PENDING"},
            {"state": "CONSENT_GRANTED", "timestamp": now, "status": "PENDING"},
            {"state": "DATA_REQUESTED", "timestamp": now, "status": "PENDING"},
            {"state": "DATA_RECEIVED", "timestamp": now, "status": "PENDING"},
            {"state": "DATA_VALIDATED", "timestamp": now, "status": "PENDING"},
            {"state": "DATA_NORMALIZED", "timestamp": now, "status": "PENDING"},
            {"state": "APPLICATION_UPDATED", "timestamp": now, "status": "PENDING"},
            {"state": "COMPLETED", "timestamp": now, "status": "PENDING"},
        ]

    def advance(self, workflow: list[dict[str, Any]], state: str) -> list[dict[str, Any]]:
        now = datetime.now(timezone.utc).isoformat()
        for step in workflow:
            if step["state"] == state:
                step["status"] = "DONE"
                step["timestamp"] = now
        for idx, step in enumerate(workflow):
            if step["state"] == state:
                for later in workflow[idx + 1:]:
                    later["status"] = "PENDING"
                break
        return workflow


workflow_service = WorkflowService()
