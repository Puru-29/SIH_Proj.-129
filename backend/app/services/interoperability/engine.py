from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Callable

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.config import settings
from connectors.education_connector import EducationConnector
from connectors.employment_connector import EmploymentConnector
from connectors.municipal_connector import MunicipalConnector
from connectors.revenue_connector import RevenueConnector
from connectors.transport_connector import TransportConnector
from connectors.welfare_connector import WelfareConnector
from app.models.application import ApplicationStatus, ServiceApplication
from app.models.application_event import ApplicationEvent
from app.models.consent import ConsentStatus, DataShareConsent
from app.models.government_record import GovernmentRecord, GovernmentRecordValue
from app.models.interoperability_exception import ExceptionStatus
from app.models.platform import ConnectedSystem, PlatformStatus
from app.models.service import Service
from app.models.transaction import InteroperabilityTransaction
from app.models.transaction_event import TransactionEvent
from app.models.user import User
from app.services.interoperability.exception_service import (
    ExceptionService,
    exception_type,
)
from app.services.interoperability.mapping_service import MappingService
from app.services.interoperability.normalization_service import NormalizationService
from app.services.interoperability.transaction_service import TransactionService
from app.services.interoperability.validation_service import (
    InteroperabilityValidationError,
    ValidationService,
)
from app.services.notification_service import notification_service
from app.services.audit_service import record_audit
from app.services.workflow_engine import workflow_engine

logger = logging.getLogger(__name__)

SourceFetcher = Callable[[Any, int, str, str], dict[str, Any]]


class InteroperabilityEngine:
    def __init__(
        self,
        *,
        transaction_service: TransactionService | None = None,
        validation_service: ValidationService | None = None,
        mapping_service: MappingService | None = None,
        normalization_service: NormalizationService | None = None,
        exception_service: ExceptionService | None = None,
        source_fetcher: SourceFetcher | None = None,
    ):
        self.transactions = transaction_service or TransactionService()
        self.validation = validation_service or ValidationService()
        self.mapping = mapping_service or MappingService()
        self.normalization = normalization_service or NormalizationService()
        self.exceptions = exception_service or ExceptionService()
        self.source_fetcher = source_fetcher or self._fetch_from_connector
        self.connectors = (
            RevenueConnector(),
            EducationConnector(),
            WelfareConnector(),
            TransportConnector(),
            MunicipalConnector(),
            EmploymentConnector(),
        )

    def process(
        self,
        db: Session,
        *,
        citizen_id: int,
        service_id: int,
        application_id: int,
        consent_id: int,
        requesting_department: str,
        source_department: str,
        data_requested: str,
        purpose: str,
        authenticated_user: User | None = None,
    ) -> dict[str, Any]:
        if settings.data_mode != "demo":
            raise ValueError(
                "No production government connector is configured; demo connector execution is disabled."
            )
        if authenticated_user is not None:
            self.validation.validate_authenticated_user(authenticated_user, citizen_id)

        application = db.query(ServiceApplication).filter(
            ServiceApplication.id == application_id
        ).first()
        application = self.validation.validate_application(
            application, citizen_id=citizen_id, service_id=service_id
        )
        consent = (
            db.query(DataShareConsent)
            .filter(
                DataShareConsent.id == consent_id,
                DataShareConsent.citizen_id == citizen_id,
            )
            .first()
        )
        service = db.query(Service).filter(Service.id == service_id).first()
        if consent is None:
            raise InteroperabilityValidationError(
                "A matching citizen consent is required before data exchange.",
                category="CONSENT",
            )
        if service is None:
            raise InteroperabilityValidationError(
                "Service not found.", category="APPLICATION"
            )
        source_system = consent.source_platform
        transaction = self.transactions.create(
            db,
            application_id=application_id,
            citizen_id=citizen_id,
            consent_id=consent_id,
            source_system_id=consent.source_platform_id,
            destination_system_id=consent.target_platform_id,
            requesting_department=requesting_department,
            source_department=source_department,
            data_requested=data_requested,
            purpose=purpose,
        )
        transaction_id = transaction.transaction_id
        try:
            consent_status = self.validation.validate_consent(
                consent,
                citizen_id=citizen_id,
                application_id=application_id,
                service=service,
                data_requested=data_requested,
                purpose=purpose,
                source_department=source_department,
                requesting_department=requesting_department,
                source_system=source_system,
            )
        except InteroperabilityValidationError as exc:
            self._fail(
                db,
                transaction,
                citizen_id=citizen_id,
                message=str(exc),
                category=exc.category,
            )
            return self._result(transaction, message=str(exc))
        if source_system is None:
            self._fail(
                db,
                transaction,
                citizen_id=citizen_id,
                message="The consent source system is not registered.",
                category="SOURCE_SYSTEM_UNAVAILABLE",
            )
            return self._result(
                transaction, message="The consent source system is not registered."
            )

        if consent_status == ConsentStatus.PENDING:
            transaction.consent_status = "PENDING"
            self.transactions.transition(
                db,
                transaction,
                "CONSENT_PENDING",
                "Interoperability request is waiting for citizen consent.",
            )
            return self._result(
                transaction,
                message="Interoperability request is waiting for citizen consent.",
            )

        transaction.consent_status = "GRANTED"
        self.transactions.transition(
            db, transaction, "CONSENT_GRANTED", "Citizen consent and requested scope verified."
        )
        self._audit(
            db,
            transaction,
            action="INTEROPERABILITY_CONSENT_VERIFIED",
            actor_id=citizen_id,
            details=f"Consent #{consent_id} verified for {data_requested}.",
        )
        db.commit()

        db.refresh(consent)
        try:
            refreshed_status = self.validation.validate_consent(
                consent,
                citizen_id=citizen_id,
                application_id=application_id,
                service=service,
                data_requested=data_requested,
                purpose=purpose,
                source_department=source_department,
                requesting_department=requesting_department,
                source_system=source_system,
            )
            if refreshed_status != ConsentStatus.GRANTED:
                raise InteroperabilityValidationError(
                    "Explicit citizen approval is required before requesting source data.",
                    category="CONSENT",
                )
        except InteroperabilityValidationError as exc:
            self._fail(
                db,
                transaction,
                citizen_id=citizen_id,
                message=str(exc),
                category="CONSENT",
            )
            return self._result(transaction, message="Consent validation failed.")

        transaction.request_status = "IN_PROGRESS"
        self.transactions.transition(
            db,
            transaction,
            "DATA_REQUESTED",
            f"Requested {data_requested} from {source_system.name}.",
        )

        try:
            connector = self._select_connector(source_system, source_department)
            raw = self._request_source_data(
                db,
                connector,
                source_system,
                citizen_id,
                data_requested,
                purpose,
                transaction,
            )
        except Exception as exc:
            logger.exception(
                "Source connector failed for interoperability transaction %s", transaction_id
            )
            category = (
                "TIMEOUT"
                if isinstance(exc, TimeoutError)
                else "SOURCE_SYSTEM_UNAVAILABLE"
                if isinstance(exc, ConnectionError)
                else getattr(exc, "category", "CONNECTOR_FAILURE")
            )
            self._fail(
                db,
                transaction,
                citizen_id=citizen_id,
                message=f"Source system request failed: {exc}",
                category=category,
            )
            return self._result(transaction, message="Source system request failed.")

        self.transactions.transition(
            db,
            transaction,
            "DATA_RECEIVED",
            f"Source system {source_system.name} returned a response.",
        )
        transaction.request_status = "SUCCESS"
        try:
            raw = self.validation.validate_source_response(raw)
            if not connector.verify_record(citizen_id, raw):
                raise InteroperabilityValidationError(
                    "Citizen was not found or verified by the source system.",
                    category="CITIZEN_NOT_FOUND",
                )
        except (InteroperabilityValidationError, ValueError, TypeError) as exc:
            self._fail(
                db,
                transaction,
                citizen_id=citizen_id,
                message=str(exc),
                category="SOURCE_RESPONSE",
            )
            return self._result(transaction, message="Source response validation failed.")

        transaction.validation_status = "PASSED"
        self.transactions.transition(
            db, transaction, "DATA_VALIDATED", "Source response passed validation."
        )
        try:
            common_record = self.mapping.map_to_common_model(
                db,
                raw=raw,
                citizen_id=citizen_id,
                source_system=source_system,
                target_system_id=consent.target_platform_id,
                requested_type=data_requested,
                connector_key=connector.mapping_key,
            )
            mapping_missing = common_record.get("missing_required_fields", [])
            if mapping_missing:
                raise InteroperabilityValidationError(
                    "Source response is missing required fields: "
                    + ", ".join(mapping_missing),
                    category="MISSING_REQUIRED_FIELD",
                )
            common_record["verification_status"] = "VERIFIED"
            normalized = self.normalization.normalize(common_record)
            missing = self._missing_common_fields(normalized)
            if missing:
                raise InteroperabilityValidationError(
                    f"Source response is missing required common-model fields: {', '.join(missing)}",
                    category="MISSING_FIELDS",
                )
        except (InteroperabilityValidationError, TypeError, ValueError) as exc:
            self._fail(
                db,
                transaction,
                citizen_id=citizen_id,
                message=str(exc),
                category=getattr(exc, "category", "NORMALIZATION"),
            )
            return self._result(transaction, message="Source data could not be normalized.")

        transaction.mapping_status = "PASSED"
        transaction.response_status = "RECEIVED"
        self.transactions.transition(
            db,
            transaction,
            "DATA_NORMALIZED",
            "Source fields mapped to and normalized as the GovFlow Common Data Model.",
        )
        conflict_values = self._detect_conflicts(
            db,
            citizen_id=citizen_id,
            normalized=normalized,
        )
        for field_name, evidence in normalized.get("mapping_conflicts", {}).items():
            conflict_values[field_name] = [
                {
                    "source_system": normalized["source_system"],
                    "record_id": normalized["identifier"],
                    "source_field": item["source_field"],
                    "value": self._serialize(item["value"]),
                }
                for item in evidence
            ]
        conflicts = sorted(conflict_values)
        record = self._store_record(
            db,
            application=application,
            source_system=source_system,
            citizen_id=citizen_id,
            normalized=normalized,
            conflicts=conflicts,
        )
        db.flush()

        if conflicts:
            transaction.response_status = "CONFLICT"
            self.transactions.transition(
                db,
                transaction,
                "CONFLICT",
                "The source record conflicts with a previously stored government record.",
                event_data={"conflictingValues": conflict_values},
            )
            self.exceptions.create(
                db,
                application_id=application_id,
                transaction_id=transaction.id,
                system_id=source_system.id,
                category="DATA_CONFLICT",
                message="Government record contains values that conflict with a stored record.",
                details={
                    "fields": conflicts,
                    "conflictingValues": conflict_values,
                    "recordId": str(record.id),
                },
                severity="high",
            )
            notification_service.create_event(
                db,
                event_type="DATA_CONFLICT",
                citizen_id=citizen_id,
                department_id=application.department_id,
                application_id=application.id,
                transaction_id=transaction.id,
                title=f"{data_requested} needs review",
                message=(
                    f"Conflicting {data_requested} data was received from "
                    f"{source_department} and flagged for review."
                ),
            )
            notification_service.create_event(
                db,
                event_type="APPLICATION_UPDATED",
                citizen_id=citizen_id,
                department_id=application.department_id,
                application_id=application.id,
                transaction_id=transaction.id,
                title="Application requires review",
                message=(
                    f"Application {application.reference_id} was updated to "
                    "require review of conflicting source data."
                ),
            )
            self._update_application(
                db,
                application,
                citizen_id=citizen_id,
                data_requested=data_requested,
                source_department=source_department,
                outcome="conflict",
            )
            self._record_non_transition_event(
                db, transaction, "application_updated", "Application updated for conflict review."
            )
            self._finish(
                db,
                transaction,
                citizen_id=citizen_id,
                message=f"Conflicting {data_requested} data was received from {source_department} and flagged for review.",
            )
            return self._result(
                transaction,
                message="Interoperability completed with a data conflict.",
                normalized=normalized,
                record=record,
            )

        self._update_application(
            db,
            application,
            citizen_id=citizen_id,
            data_requested=data_requested,
            source_department=source_department,
            outcome="completed",
        )
        transaction.response_status = "SUCCESS"
        self.transactions.transition(
            db,
            transaction,
            "APPLICATION_UPDATED",
            "Application state updated with the verified government record.",
        )
        self.transactions.transition(
            db, transaction, "COMPLETED", "Interoperability transaction completed successfully."
        )
        workflow_engine.sync_completed_data_request(
            db,
            application,
            source_department=source_department,
            actor_id=citizen_id,
        )
        self._audit(
            db,
            transaction,
            action="INTEROPERABILITY_TRANSACTION_COMPLETED",
            actor_id=citizen_id,
            details=f"{data_requested} was retrieved, validated, normalized, and stored.",
        )
        notification_service.create_event(
            db,
            event_type="APPLICATION_UPDATED",
            citizen_id=citizen_id,
            department_id=application.department_id,
            application_id=application.id,
            transaction_id=transaction.id,
            title="Application updated",
            message=(
                f"Application {application.reference_id} was updated with "
                f"verified {data_requested} data."
            ),
        )
        notification = self._notify(
            db,
            transaction,
            citizen_id=citizen_id,
            title=f"{data_requested} retrieved",
            message=f"Your {data_requested} was securely retrieved from {source_department} with your permission.",
            event_type="DATA_VERIFIED",
        )
        db.commit()
        result = self._result(
            transaction,
            message="Interoperability request processed successfully.",
            normalized=normalized,
            record=record,
        )
        result["notification"] = notification
        return result

    @staticmethod
    def match_document_record(
        db: Session,
        *,
        citizen_id: int,
        certificate_number: str,
        extracted_fields: dict[str, Any],
    ) -> dict[str, Any]:
        """Compare extracted certificate fields with a persisted verified source record."""
        records = (
            db.query(GovernmentRecord)
            .join(GovernmentRecordValue)
            .filter(
                GovernmentRecord.citizen_id == citizen_id,
                func.lower(GovernmentRecord.source_record_id)
                == certificate_number.strip().lower(),
                GovernmentRecord.status == "VERIFIED",
                GovernmentRecordValue.field_key.in_(
                    ("income_certificate_no", "certificate_no", "certificate_number")
                ),
                func.lower(GovernmentRecordValue.field_value)
                == certificate_number.strip().lower(),
            )
            .options(
                joinedload(GovernmentRecord.values),
                joinedload(GovernmentRecord.connected_system),
            )
            .distinct()
            .all()
        )
        if not records:
            return {
                "status": "NOT_FOUND",
                "record_id": None,
                "source_system": None,
                "matched_fields": [],
                "mismatched_fields": [],
                "source_fields": {},
            }

        record = records[0]
        source_fields = {
            item.field_key: item.field_value for item in record.values
        }
        aliases = {
            "name": ("name", "full_name"),
            "income": ("income", "annual_income"),
            "issue_date": ("issue_date", "issued_at"),
        }
        matched_fields = ["certificate_number"]
        mismatched_fields = []
        for extracted_key, source_keys in aliases.items():
            extracted_value = extracted_fields.get(extracted_key)
            source_value = next(
                (source_fields[key] for key in source_keys if key in source_fields),
                None,
            )
            if extracted_value is None or source_value is None:
                continue
            if extracted_key == "income":
                try:
                    matches = float(extracted_value) == float(source_value)
                except (TypeError, ValueError):
                    matches = False
            else:
                matches = " ".join(str(extracted_value).casefold().split()) == (
                    " ".join(str(source_value).casefold().split())
                )
            (matched_fields if matches else mismatched_fields).append(extracted_key)

        return {
            "status": "MISMATCHED" if mismatched_fields else "MATCHED",
            "record_id": str(record.id),
            "source_record_id": record.source_record_id,
            "source_system": (
                record.connected_system.name if record.connected_system else None
            ),
            "matched_fields": matched_fields,
            "mismatched_fields": mismatched_fields,
            "source_fields": source_fields,
        }

    def retry_exception(
        self,
        db: Session,
        exception: Any,
        *,
        actor: User,
    ) -> dict[str, Any]:
        transaction = db.get(InteroperabilityTransaction, exception.transaction_id)
        if transaction is None:
            raise ValueError("The exception has no linked interoperability transaction.")
        transaction_id = transaction.id
        exception_model = type(exception)
        exception_id = exception.id

        application = db.get(ServiceApplication, transaction.application_id)
        consent = db.get(DataShareConsent, transaction.consent_id)
        service = db.get(Service, application.service_id) if application else None
        source_system = db.get(ConnectedSystem, transaction.source_system_id)
        citizen = db.get(User, transaction.citizen_id)
        claimed = (
            db.query(exception_model)
            .filter(
                exception_model.id == exception_id,
                exception_model.status.in_(
                    [ExceptionStatus.OPEN, ExceptionStatus.ESCALATED]
                ),
            )
            .update(
                {
                    exception_model.status: ExceptionStatus.RETRYING,
                    exception_model.retry_count: exception_model.retry_count + 1,
                    exception_model.resolved_at: None,
                },
                synchronize_session=False,
            )
        )
        if claimed != 1:
            db.rollback()
            raise ValueError("Only open or escalated exceptions can be retried.")
        db.refresh(exception)
        db.flush()
        self.transactions.transition(
            db,
            transaction,
            "RETRYING",
            f"Officer {actor.id} started retry {exception.retry_count}.",
            event_data={"attempt": exception.retry_count, "exceptionId": exception.id},
        )

        try:
            if settings.data_mode != "demo":
                raise InteroperabilityValidationError(
                    "No production government connector is configured.",
                    category="CONNECTOR_FAILURE",
                )
            if application is None or citizen is None or service is None:
                raise InteroperabilityValidationError(
                    "The application, citizen, or service for this request no longer exists.",
                    category="CITIZEN_NOT_FOUND"
                    if citizen is None
                    else "VALIDATION_FAILURE",
                )
            if consent is None or source_system is None:
                raise InteroperabilityValidationError(
                    "The consent or source system for this request no longer exists.",
                    category="CONSENT_EXPIRED"
                    if consent is None
                    else "SOURCE_SYSTEM_UNAVAILABLE",
                )
            consent_status = self.validation.validate_consent(
                consent,
                citizen_id=transaction.citizen_id,
                application_id=transaction.application_id,
                service=service,
                data_requested=transaction.data_requested,
                purpose=transaction.purpose,
                source_department=transaction.source_department,
                requesting_department=transaction.requesting_department,
                source_system=source_system,
            )
            if consent_status != ConsentStatus.GRANTED:
                raise InteroperabilityValidationError(
                    "Active granted consent is required before retrying the source request.",
                    category="CONSENT_EXPIRED",
                )
            connector = self._select_connector(
                source_system, transaction.source_department
            )
            transaction.request_status = "IN_PROGRESS"
            transaction.response_status = "PENDING"
            transaction.validation_status = "PENDING"
            transaction.mapping_status = "PENDING"
            self.transactions.transition(
                db,
                transaction,
                "DATA_REQUESTED",
                f"Retry requested {transaction.data_requested} from {source_system.name}.",
                event_data={"attempt": exception.retry_count},
            )
            raw = self._request_source_data(
                db,
                connector,
                source_system,
                transaction.citizen_id,
                transaction.data_requested,
                transaction.purpose,
                transaction,
            )
            raw = self.validation.validate_source_response(raw)
            self.transactions.transition(
                db,
                transaction,
                "DATA_RECEIVED",
                f"Source system {source_system.name} returned a retry response.",
                event_data={"attempt": exception.retry_count},
            )
            if not connector.verify_record(transaction.citizen_id, raw):
                raise InteroperabilityValidationError(
                    "The source system could not verify the returned citizen record.",
                    category="CITIZEN_NOT_FOUND",
                )
            transaction.request_status = "SUCCESS"
            transaction.validation_status = "PASSED"
            self.transactions.transition(
                db,
                transaction,
                "DATA_VALIDATED",
                "Retried source response passed validation.",
                event_data={"attempt": exception.retry_count},
            )
            common_record = self.mapping.map_to_common_model(
                db,
                raw=raw,
                citizen_id=transaction.citizen_id,
                source_system=source_system,
                target_system_id=transaction.destination_system_id,
                requested_type=transaction.data_requested,
                connector_key=connector.mapping_key,
            )
            mapping_missing = common_record.get("missing_required_fields", [])
            if mapping_missing:
                raise InteroperabilityValidationError(
                    "Source response is missing required fields: "
                    + ", ".join(mapping_missing),
                    category="MISSING_REQUIRED_FIELD",
                )
            common_record["verification_status"] = "VERIFIED"
            normalized = self.normalization.normalize(common_record)
            missing = self._missing_common_fields(normalized)
            if missing:
                raise InteroperabilityValidationError(
                    f"Source response is missing required fields: {', '.join(missing)}",
                    category="MISSING_REQUIRED_FIELD",
                )
            transaction.mapping_status = "PASSED"
            transaction.response_status = "RECEIVED"
            self.transactions.transition(
                db,
                transaction,
                "DATA_NORMALIZED",
                "Retried source fields were mapped and normalized.",
                event_data={"attempt": exception.retry_count},
            )
            conflict_values = self._detect_conflicts(
                db,
                citizen_id=transaction.citizen_id,
                normalized=normalized,
            )
            conflicts = sorted(conflict_values)
            record = self._store_record(
                db,
                application=application,
                source_system=source_system,
                citizen_id=transaction.citizen_id,
                normalized=normalized,
                conflicts=conflicts,
            )
            if conflicts:
                transaction.response_status = "CONFLICT"
                self.transactions.transition(
                    db,
                    transaction,
                    "CONFLICT",
                    "Retried source data still conflicts with an existing government record.",
                    event_data={"conflictingValues": conflict_values},
                )
                self._update_application(
                    db,
                    application,
                    citizen_id=transaction.citizen_id,
                    data_requested=transaction.data_requested,
                    source_department=transaction.source_department,
                    outcome="conflict",
                )
                exception.category = "DATA_CONFLICT"
                exception.message = (
                    "Retried source data still conflicts with an existing government record."
                )
                exception.status = ExceptionStatus.OPEN
                notification_service.create_event(
                    db,
                    event_type="DATA_CONFLICT",
                    citizen_id=transaction.citizen_id,
                    department_id=application.department_id,
                    application_id=application.id,
                    transaction_id=transaction.id,
                    title=f"{transaction.data_requested} needs review",
                    message=exception.message,
                )
                notification_service.create_event(
                    db,
                    event_type="APPLICATION_UPDATED",
                    citizen_id=transaction.citizen_id,
                    department_id=application.department_id,
                    application_id=application.id,
                    transaction_id=transaction.id,
                    title="Application requires review",
                    message=(
                        f"Application {application.reference_id} was updated to "
                        "require review of conflicting source data."
                    ),
                )
                self._audit_retry(
                    db, exception, transaction, actor, result="failure"
                )
                db.commit()
                return {
                    **self._result(
                        transaction,
                        message=exception.message,
                        normalized=normalized,
                        record=record,
                    ),
                    "exception": self._exception_result(exception, transaction),
                }

            self._update_application(
                db,
                application,
                citizen_id=transaction.citizen_id,
                data_requested=transaction.data_requested,
                source_department=transaction.source_department,
                outcome="completed",
            )
            transaction.response_status = "SUCCESS"
            self.transactions.transition(
                db,
                transaction,
                "APPLICATION_UPDATED",
                "Application updated with verified data from the retried request.",
                event_data={"attempt": exception.retry_count},
            )
            self.transactions.transition(
                db,
                transaction,
                "COMPLETED",
                "Interoperability retry completed successfully.",
                event_data={"attempt": exception.retry_count},
            )
            workflow_engine.sync_completed_data_request(
                db,
                application,
                source_department=transaction.source_department,
                actor_id=actor.id,
            )
            exception.status = ExceptionStatus.RESOLVED
            exception.resolved_at = datetime.now(timezone.utc)
            exception.message = "Connector retry succeeded."
            notification_service.create_event(
                db,
                event_type="DATA_VERIFIED",
                citizen_id=transaction.citizen_id,
                department_id=application.department_id,
                application_id=application.id,
                transaction_id=transaction.id,
                title=f"{transaction.data_requested} verified",
                message=(
                    f"Retried data from {transaction.source_department} was "
                    f"verified for application {application.reference_id}."
                ),
            )
            notification_service.create_event(
                db,
                event_type="APPLICATION_UPDATED",
                citizen_id=transaction.citizen_id,
                department_id=application.department_id,
                application_id=application.id,
                transaction_id=transaction.id,
                title="Application updated",
                message=(
                    f"Application {application.reference_id} was updated with "
                    f"verified {transaction.data_requested} data."
                ),
            )
            self._audit_retry(db, exception, transaction, actor, result="success")
            db.commit()
            return {
                **self._result(
                    transaction,
                    message="Connector retry completed successfully.",
                    normalized=normalized,
                    record=record,
                ),
                "exception": self._exception_result(exception, transaction),
            }
        except Exception as exc:
            db.rollback()
            exception = db.get(exception_model, exception_id)
            transaction = db.get(InteroperabilityTransaction, transaction_id)
            if exception is None or transaction is None:
                raise
            category = getattr(exc, "category", None)
            if category is None:
                category = (
                    "MALFORMED_DATA"
                    if isinstance(exc, (TypeError, ValueError, KeyError))
                    else "TIMEOUT"
                    if isinstance(exc, TimeoutError)
                    else "CONNECTOR_FAILURE"
                )
            mapped_type = exception_type(category, str(exc))
            exception.category = mapped_type
            exception.message = str(exc) or mapped_type
            exception.status = ExceptionStatus.OPEN
            exception.resolved_at = None
            transaction.request_status = "FAILED"
            transaction.response_status = "FAILED"
            transaction.validation_status = (
                "FAILED"
                if mapped_type
                in {"INVALID_RESPONSE", "MALFORMED_DATA", "MISSING_REQUIRED_FIELD", "VALIDATION_FAILURE"}
                else transaction.validation_status
            )
            self.transactions.transition(
                db,
                transaction,
                "FAILED",
                exception.message,
                error_code=mapped_type,
                error_message=exception.message,
                event_data={"attempt": exception.retry_count},
            )
            self._audit_retry(db, exception, transaction, actor, result="failure")
            notification_service.create_event(
                db,
                event_type="EXCEPTION_OCCURRED",
                citizen_id=transaction.citizen_id,
                department_id=transaction.application.department_id
                if transaction.application
                else actor.department_id,
                application_id=transaction.application_id,
                transaction_id=transaction.id,
                title="Government data request still needs attention",
                message=exception.message,
            )
            db.commit()
            return {
                "status": "failure",
                "transactionStatus": transaction.status,
                "message": exception.message,
                "transactionId": transaction.transaction_id,
                "exception": self._exception_result(exception, transaction),
            }

    @staticmethod
    def _audit_retry(
        db: Session,
        exception: Any,
        transaction: InteroperabilityTransaction,
        actor: User,
        *,
        result: str,
    ) -> None:
        record_audit(
            db,
            action="EXCEPTION_RETRIED",
            resource_type="interoperability_exception",
            resource_id=exception.id,
            actor_id=actor.id,
            role_id=actor.role_id,
            department_id=(
                transaction.application.department_id
                if transaction.application
                else actor.department_id
            ),
            transaction=transaction,
            result=result,
            metadata={
                "retry_count": exception.retry_count,
                "exception_type": exception.category,
                "transaction_status": transaction.status,
            },
            details=exception.message,
        )

    @staticmethod
    def _exception_result(
        exception: Any, transaction: InteroperabilityTransaction
    ) -> dict[str, Any]:
        return {
            "id": exception.id,
            "exceptionId": exception.id,
            "transactionId": transaction.transaction_id,
            "applicationId": exception.application_id,
            "sourceSystem": exception.system,
            "system": exception.system,
            "type": exception.category,
            "category": exception.category,
            "message": exception.message,
            "severity": exception.severity,
            "status": exception.status.value
            if isinstance(exception.status, ExceptionStatus)
            else str(exception.status).upper(),
            "retryCount": exception.retry_count,
            "details": exception.details,
            "createdAt": exception.created_at.isoformat()
            if exception.created_at
            else None,
            "updatedAt": exception.updated_at.isoformat()
            if exception.updated_at
            else None,
            "resolvedAt": exception.resolved_at.isoformat()
            if exception.resolved_at
            else None,
        }

    def _select_connector(self, source_system: ConnectedSystem, source_department: str) -> Any:
        stored_status = (
            source_system.status.value
            if isinstance(source_system.status, PlatformStatus)
            else str(source_system.status)
        )
        if not source_system.is_active or stored_status.lower() == PlatformStatus.OFFLINE.value:
            raise InteroperabilityValidationError(
                f"Source system {source_system.name} is unavailable.",
                category="CONNECTOR_UNAVAILABLE",
            )
        provider = self.connector_for_system(source_system, source_department)
        if provider is not None:
            connector_health = provider.health_check()
            if connector_health.get("status") != "healthy":
                raise InteroperabilityValidationError(
                    f"Source connector is unhealthy: {provider.system_name}.",
                    category="CONNECTOR_UNAVAILABLE",
                )
            return provider
        raise InteroperabilityValidationError(
            f"No source connector is configured for {source_department}.",
            category="CONNECTOR_NOT_FOUND",
        )

    def connector_for_system(
        self,
        source_system: ConnectedSystem,
        source_department: str | None = None,
    ) -> Any | None:
        keys = {
            self._compact(source_department or ""),
            self._compact(source_system.name),
            self._compact(source_system.slug),
            self._compact(
                source_system.department.name if source_system.department else ""
            ),
        }
        for provider in self.connectors:
            provider_keys = {
                self._compact(provider.department),
                self._compact(provider.system_name),
                self._compact(getattr(provider, "mapping_key", "")),
            }
            if any(
                key and (key in provider_key or provider_key in key)
                for key in keys
                for provider_key in provider_keys
            ):
                return provider
        return None

    def _request_source_data(
        self,
        db: Session,
        connector: Any,
        source_system: ConnectedSystem,
        citizen_id: int,
        data_requested: str,
        purpose: str,
        transaction: InteroperabilityTransaction,
    ) -> dict[str, Any]:
        attempts = max(0, min(source_system.max_retries, 5)) + 1
        for attempt in range(attempts):
            try:
                return self.source_fetcher(connector, citizen_id, data_requested, purpose)
            except (TimeoutError, ConnectionError):
                if attempt + 1 >= attempts:
                    raise
                self.transactions.transition(
                    db,
                    transaction,
                    "RETRYING",
                    f"Transient source connector failure; retrying attempt {attempt + 2} of {attempts}.",
                    event_data={"attempt": attempt + 2},
                )
        raise RuntimeError("Source connector retries exhausted.")

    @staticmethod
    def _fetch_from_connector(
        connector: Any, citizen_id: int, data_requested: str, purpose: str
    ) -> dict[str, Any]:
        return connector.get_record(citizen_id, data_requested, purpose)

    @staticmethod
    def _missing_common_fields(record: dict[str, Any]) -> list[str]:
        required = ("citizen_id", "record_type", "identifier", "source_system")
        return [field for field in required if record.get(field) in (None, "")]

    def _detect_conflicts(
        self,
        db: Session,
        *,
        citizen_id: int,
        normalized: dict[str, Any],
    ) -> dict[str, list[dict[str, str]]]:
        prior_records = (
            db.query(GovernmentRecord)
            .filter(GovernmentRecord.citizen_id == citizen_id)
            .all()
        )
        current_values = self._record_values(normalized)
        conflicts: dict[str, list[dict[str, str]]] = {}
        for prior in prior_records:
            for prior_value in prior.values:
                new_value = current_values.get(prior_value.field_key)
                if prior_value.field_key not in {"name", "date_of_birth"} or new_value is None:
                    continue
                if prior_value.field_value != self._serialize(new_value):
                    prior.status = "CONFLICT"
                    conflicts.setdefault(prior_value.field_key, []).append(
                        {
                            "source_system": prior.connected_system.name,
                            "record_id": prior.source_record_id,
                            "value": prior_value.field_value,
                        }
                    )
        for field_name, evidence in conflicts.items():
            evidence.append(
                {
                    "source_system": normalized["source_system"],
                    "record_id": normalized["identifier"],
                    "value": self._serialize(current_values[field_name]),
                }
            )
        return conflicts

    def _store_record(
        self,
        db: Session,
        *,
        application: ServiceApplication,
        source_system: ConnectedSystem,
        citizen_id: int,
        normalized: dict[str, Any],
        conflicts: list[str],
    ) -> GovernmentRecord:
        record = GovernmentRecord(
            citizen_id=citizen_id,
            department_id=source_system.department_id,
            connected_system_id=source_system.id,
            application_id=application.id,
            record_type=normalized["record_type"],
            source_record_id=normalized["identifier"],
            status=(
                "CONFLICT"
                if conflicts
                else normalized["verification_status"]
            ),
            schema_version="1",
            verified_at=(
                datetime.now(timezone.utc)
                if normalized["verification_status"] == "VERIFIED"
                else None
            ),
        )
        db.add(record)
        db.flush()
        for key, value in self._record_values(normalized).items():
            db.add(
                GovernmentRecordValue(
                    record_id=record.id,
                    field_key=key,
                    field_value=self._serialize(value),
                    data_type=self.normalization.value_type(value),
                    classification=(
                        "personal"
                        if key in {"citizen_id", "name", "date_of_birth"}
                        else None
                    ),
                )
            )
        self._audit(
            db,
            None,
            action="GOVERNMENT_RECORD_STORED",
            actor_id=citizen_id,
            details=f"Normalized {normalized['record_type']} stored from {source_system.name}.",
            entity_id=str(record.id),
            entity_type="government_record",
        )
        return record

    def _update_application(
        self,
        db: Session,
        application: ServiceApplication,
        *,
        citizen_id: int,
        data_requested: str,
        source_department: str,
        outcome: str,
    ) -> None:
        application.status = ApplicationStatus.UNDER_REVIEW
        if outcome == "conflict":
            application.remarks = (
                f"{data_requested} from {source_department} has conflicting values and requires review."
            )
        else:
            application.remarks = (
                f"{data_requested} retrieved from {source_department} through GovFlow interoperability and validated."
            )
        db.add(
            ApplicationEvent(
                application_id=application.id,
                actor_id=citizen_id,
                event_type=f"interoperability_{outcome}",
                status=application.status.value,
                note=application.remarks,
            )
        )

    def _fail(
        self,
        db: Session,
        transaction: InteroperabilityTransaction,
        *,
        citizen_id: int,
        message: str,
        category: str,
    ) -> None:
        transaction.request_status = "FAILED"
        transaction.response_status = "FAILED"
        if category == "CONSENT":
            transaction.consent_status = "FAILED"
        elif category in {
            "SOURCE_RESPONSE",
            "INVALID_RESPONSE",
            "CITIZEN_NOT_FOUND",
            "VALIDATION",
        }:
            transaction.validation_status = "FAILED"
        elif category in {
            "MISSING_REQUIRED_FIELD",
            "MALFORMED_DATA",
            "NORMALIZATION",
            "MISSING_FIELDS",
        }:
            transaction.mapping_status = "FAILED"
        self.exceptions.create(
            db,
            application_id=transaction.application_id,
            transaction_id=transaction.id,
            system_id=transaction.source_system_id,
            category=category,
            message=message,
            details={"transactionId": transaction.transaction_id},
            severity="high" if category in {"SOURCE_CONNECTOR", "SOURCE_RESPONSE"} else "medium",
        )
        self.transactions.transition(
            db,
            transaction,
            "FAILED",
            message,
            error_code=category,
            error_message=message,
        )
        self._audit(
            db,
            transaction,
            action="INTEROPERABILITY_TRANSACTION_FAILED",
            actor_id=citizen_id,
            details=message,
        )
        notification_service.create_event(
            db,
            event_type="EXCEPTION_OCCURRED",
            citizen_id=citizen_id,
            department_id=transaction.application.department_id
            if transaction.application
            else None,
            application_id=transaction.application_id,
            transaction_id=transaction.id,
            title="Government data request failed",
            message=message,
        )
        db.commit()

    def _finish(
        self,
        db: Session,
        transaction: InteroperabilityTransaction,
        *,
        citizen_id: int,
        message: str,
    ) -> None:
        self._audit(
            db,
            transaction,
            action="INTEROPERABILITY_TRANSACTION_CONFLICT",
            actor_id=citizen_id,
            details=message,
        )
        db.commit()

    @staticmethod
    def _notify(
        db: Session,
        transaction: InteroperabilityTransaction,
        *,
        citizen_id: int,
        title: str,
        message: str,
        event_type: str = "DATA_VERIFIED",
    ) -> Any:
        notification = notification_service.create_notification(
            db=db,
            citizen_id=citizen_id,
            application_id=transaction.application_id,
            transaction_id=transaction.id,
            title=title,
            message=message,
            kind="Application",
            event_type=event_type,
        )
        return notification

    @staticmethod
    def _audit(
        db: Session,
        transaction: InteroperabilityTransaction | None,
        *,
        action: str,
        actor_id: int,
        details: str,
        entity_id: str | None = None,
        entity_type: str = "interoperability_transaction",
    ) -> None:
        record_audit(
            db,
            action=action,
            resource_type=entity_type,
            resource_id=entity_id
            or (transaction.transaction_id if transaction else ""),
            actor_id=actor_id,
            department_id=transaction.application.department_id
            if transaction and transaction.application
            else None,
            transaction=transaction,
            result="failure"
            if action.endswith("_FAILED")
            else "conflict"
            if action.endswith("_CONFLICT")
            else "success",
            metadata={"detail": details},
            details=details,
        )

    @staticmethod
    def _record_non_transition_event(
        db: Session,
        transaction: InteroperabilityTransaction,
        event_type: str,
        detail: str,
    ) -> None:
        db.add(
            TransactionEvent(
                transaction_id=transaction.id,
                event_type=event_type,
                status=transaction.status,
                detail=detail,
                occurred_at=datetime.now(timezone.utc),
            )
        )

    @staticmethod
    def _record_values(normalized: dict[str, Any]) -> dict[str, Any]:
        values = {
            key: value
            for key, value in normalized.items()
            if key not in {
                "details",
                "source_department",
                "mapping_id",
                "mapping_version",
            }
            and value is not None
        }
        for key, value in normalized.get("details", {}).items():
            if value is not None:
                values[str(key)] = value
        return values

    @staticmethod
    def _serialize(value: Any) -> str:
        return value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, sort_keys=True)

    @staticmethod
    def _compact(value: str) -> str:
        return "".join(character for character in value.casefold() if character.isalnum())

    @staticmethod
    def _result(
        transaction: InteroperabilityTransaction,
        *,
        message: str,
        normalized: dict[str, Any] | None = None,
        record: GovernmentRecord | None = None,
    ) -> dict[str, Any]:
        is_success = transaction.status in {"COMPLETED", "CONFLICT"}
        result: dict[str, Any] = {
            "status": "success" if is_success else (
                "pending" if transaction.status == "CONSENT_PENDING" else "failure"
            ),
            "transactionStatus": transaction.status,
            "message": message,
            "transactionId": transaction.transaction_id,
            "requestingDepartment": transaction.requesting_department,
            "sourceDepartment": transaction.source_department,
            "dataRequested": transaction.data_requested,
            "consentStatus": transaction.consent_status,
            "requestStatus": transaction.request_status,
            "validationStatus": transaction.validation_status,
            "mappingStatus": transaction.mapping_status,
            "responseStatus": transaction.response_status,
            "applicationId": transaction.application_id,
            "consentId": transaction.consent_id,
            "createdAt": transaction.created_at.isoformat() if transaction.created_at else None,
            "completedAt": transaction.completed_at.isoformat() if transaction.completed_at else None,
        }
        if normalized is not None:
            result["data"] = normalized
        if record is not None:
            result["record"] = {
                "id": str(record.id),
                "source": transaction.source_department,
                "status": record.status,
                "identifier": record.source_record_id,
            }
        if transaction.error_message:
            result["error"] = transaction.error_message
        return result
