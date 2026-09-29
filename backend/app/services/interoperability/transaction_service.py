from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
import uuid

from sqlalchemy.orm import Session

from app.models.transaction import InteroperabilityTransaction
from app.models.transaction_event import TransactionEvent
from app.services.audit_service import record_audit


TRANSACTION_STATES = {
    "CREATED",
    "CONSENT_PENDING",
    "CONSENT_GRANTED",
    "DATA_REQUESTED",
    "DATA_RECEIVED",
    "DATA_VALIDATED",
    "DATA_NORMALIZED",
    "APPLICATION_UPDATED",
    "COMPLETED",
    "FAILED",
    "CONFLICT",
    "RETRYING",
}


class TransactionService:
    def create(
        self,
        db: Session,
        *,
        application_id: int,
        citizen_id: int,
        consent_id: int,
        source_system_id: int,
        destination_system_id: int,
        requesting_department: str,
        source_department: str,
        data_requested: str,
        purpose: str,
    ) -> InteroperabilityTransaction:
        transaction = InteroperabilityTransaction(
            transaction_id=f"TXN-{uuid.uuid4().hex[:12].upper()}",
            application_id=application_id,
            citizen_id=citizen_id,
            consent_id=consent_id,
            source_system_id=source_system_id,
            destination_system_id=destination_system_id,
            transaction_type="government_record_request",
            status="CREATED",
            requesting_department=requesting_department,
            source_department=source_department,
            data_requested=data_requested,
            purpose=purpose,
            consent_status="PENDING",
            request_status="NOT_REQUESTED",
            validation_status="PENDING",
            mapping_status="PENDING",
            response_status="PENDING",
        )
        db.add(transaction)
        db.flush()
        self._event(db, transaction, "CREATED", "Interoperability request received.")
        record_audit(
            db,
            action="INTEROPERABILITY_REQUEST_CREATED",
            resource_type="interoperability_transaction",
            resource_id=transaction.transaction_id,
            actor_id=citizen_id,
            actor_role="citizen",
            department_id=transaction.application.department_id
            if transaction.application
            else None,
            transaction=transaction,
            metadata={"status": transaction.status},
        )
        db.commit()
        return transaction

    def transition(
        self,
        db: Session,
        transaction: InteroperabilityTransaction,
        state: str,
        detail: str,
        *,
        event_data: dict[str, Any] | None = None,
        error_code: str | None = None,
        error_message: str | None = None,
    ) -> None:
        if state not in TRANSACTION_STATES:
            raise ValueError(f"Unsupported interoperability state: {state}")
        transaction.status = state
        if state in {"COMPLETED", "FAILED", "CONFLICT"}:
            transaction.completed_at = datetime.now(timezone.utc)
        if error_code is not None:
            transaction.error_code = error_code
        if error_message is not None:
            transaction.error_message = error_message
        self._event(
            db,
            transaction,
            state,
            detail,
            event_data=event_data,
            error_code=error_code,
            error_message=error_message,
            occurred_at=datetime.now(timezone.utc),
        )
        audit_actions = {
            "DATA_REQUESTED": "DATA_REQUESTED",
            "DATA_RECEIVED": "DATA_RECEIVED",
            "DATA_VALIDATED": "DATA_VALIDATED",
            "DATA_NORMALIZED": "DATA_NORMALIZED",
            "APPLICATION_UPDATED": "APPLICATION_UPDATED",
            "CONFLICT": "DATA_CONFLICT",
            "RETRYING": "INTEROPERABILITY_RETRIED",
        }
        audit_action = audit_actions.get(state)
        if audit_action:
            record_audit(
                db,
                action=audit_action,
                resource_type="interoperability_transaction",
                resource_id=transaction.transaction_id,
                actor_id=transaction.citizen_id,
                actor_role="citizen",
                department_id=transaction.application.department_id
                if transaction.application
                else None,
                transaction=transaction,
                result="in_progress"
                if state == "RETRYING"
                else "conflict"
                if state == "CONFLICT"
                else "success",
                metadata={
                    "status": state,
                    "error_code": error_code,
                    **(
                        {"attempt": event_data["attempt"]}
                        if event_data and "attempt" in event_data
                        else {}
                    ),
                },
            )
        db.commit()

    @staticmethod
    def _event(
        db: Session,
        transaction: InteroperabilityTransaction,
        state: str,
        detail: str,
        *,
        event_data: dict[str, Any] | None = None,
        error_code: str | None = None,
        error_message: str | None = None,
        occurred_at: datetime | None = None,
    ) -> None:
        db.add(
            TransactionEvent(
                transaction_id=transaction.id,
                event_type=state.lower(),
                status=state,
                detail=detail,
                event_data=event_data,
                error_code=error_code,
                error_message=error_message,
                occurred_at=occurred_at or datetime.now(timezone.utc),
            )
        )
