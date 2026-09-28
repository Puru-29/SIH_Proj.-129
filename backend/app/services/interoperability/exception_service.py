from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.models.interoperability_exception import (
    ExceptionStatus,
    InteroperabilityException,
)


class ExceptionService:
    def create(
        self,
        db: Session,
        *,
        application_id: int,
        transaction_id: int,
        system_id: int,
        category: str,
        message: str,
        details: dict[str, Any] | None = None,
        severity: str = "medium",
    ) -> InteroperabilityException:
        exception = InteroperabilityException(
            application_id=str(application_id),
            service_application_id=application_id,
            transaction_id=transaction_id,
            connected_system_id=system_id,
            system="GovFlow Interoperability Engine",
            category=category,
            message=message[:255],
            severity=severity,
            status=ExceptionStatus.OPEN,
            details=details or {},
        )
        db.add(exception)
        return exception
