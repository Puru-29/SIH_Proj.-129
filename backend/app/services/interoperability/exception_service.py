from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.models.interoperability_exception import (
    ExceptionStatus,
    InteroperabilityException,
)
from app.models.transaction import InteroperabilityTransaction
from app.services.audit_service import record_audit


EXCEPTION_TYPES = {
    "SOURCE_SYSTEM_UNAVAILABLE",
    "TIMEOUT",
    "INVALID_RESPONSE",
    "MALFORMED_DATA",
    "MISSING_REQUIRED_FIELD",
    "CONSENT_EXPIRED",
    "CITIZEN_NOT_FOUND",
    "VALIDATION_FAILURE",
    "DATA_CONFLICT",
    "CONNECTOR_FAILURE",
}


def exception_type(category: str, message: str = "") -> str:
    normalized = category.upper()
    if normalized in EXCEPTION_TYPES:
        return normalized
    text = message.casefold()
    if "consent" in text and "expir" in text:
        return "CONSENT_EXPIRED"
    if "citizen" in text and ("not found" in text or "unknown" in text):
        return "CITIZEN_NOT_FOUND"
    return {
        "CONNECTOR_UNAVAILABLE": "SOURCE_SYSTEM_UNAVAILABLE",
        "SOURCE_UNAVAILABLE": "SOURCE_SYSTEM_UNAVAILABLE",
        "TIMEOUT_ERROR": "TIMEOUT",
        "SOURCE_RESPONSE": "INVALID_RESPONSE",
        "MALFORMED_RESPONSE": "MALFORMED_DATA",
        "MISSING_FIELDS": "MISSING_REQUIRED_FIELD",
        "SOURCE_VERIFICATION": "VALIDATION_FAILURE",
        "VALIDATION": "VALIDATION_FAILURE",
        "CONSENT": "VALIDATION_FAILURE",
        "SOURCE_CONNECTOR": "CONNECTOR_FAILURE",
        "CONNECTOR_NOT_FOUND": "CONNECTOR_FAILURE",
        "NORMALIZATION": "MALFORMED_DATA",
    }.get(normalized, "CONNECTOR_FAILURE")


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
        transaction = db.get(InteroperabilityTransaction, transaction_id)
        exception = InteroperabilityException(
            application_id=str(application_id),
            service_application_id=application_id,
            transaction_id=transaction_id,
            connected_system_id=system_id,
            system=(
                transaction.source_system.name
                if transaction and transaction.source_system
                else "Unknown source system"
            ),
            category=exception_type(category, message),
            message=message,
            severity=severity,
            status=ExceptionStatus.OPEN,
            retry_count=0,
            details=details or {},
        )
        db.add(exception)
        db.flush()
        application = transaction.application if transaction else None
        record_audit(
            db,
            action="EXCEPTION_CREATED",
            resource_type="interoperability_exception",
            resource_id=exception.id,
            actor_id=transaction.citizen_id if transaction else None,
            actor_role="citizen" if transaction else "system",
            department_id=application.department_id if application else None,
            transaction=transaction,
            metadata={"category": category, "severity": severity},
        )
        return exception
