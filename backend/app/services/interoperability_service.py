from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from app.config import settings
from app.database import SessionLocal
from app.models.application import ApplicationStatus, ServiceApplication
from app.models.application_event import ApplicationEvent
from app.models.audit import AuditLog
from app.models.consent import ConsentStatus, DataShareConsent
from app.models.service import Service
from app.models.transaction import InteroperabilityTransaction
from app.models.transaction_event import TransactionEvent
from app.models.user import User
from app.models.workflow import WorkflowStep
from app.providers.demo.education_provider import EducationDemoProvider
from app.providers.demo.municipal_provider import MunicipalDemoProvider
from app.providers.demo.revenue_provider import RevenueDemoProvider
from app.providers.demo.transport_provider import TransportDemoProvider
from app.services.data_quality_service import data_quality_service
from app.services.notification_service import notification_service


class InteroperabilityService:
    def __init__(self):
        self.providers = {
            "Revenue & Land Records": RevenueDemoProvider(),
            "Revenue Department": RevenueDemoProvider(),
            "Revenue": RevenueDemoProvider(),
            "Higher & Technical Education": EducationDemoProvider(),
            "Education": EducationDemoProvider(),
            "Municipal": MunicipalDemoProvider(),
            "Municipal Department": MunicipalDemoProvider(),
            "Transport": TransportDemoProvider(),
            "Transport Department": TransportDemoProvider(),
            "Transport & Motor Vehicles": TransportDemoProvider(),
        }

    def get_demo_integrations(self) -> list[dict[str, Any]]:
        if settings.data_mode != "demo":
            return []
        return [
            {
                "id": "revenue-demo",
                "department": "Revenue & Land Records",
                "systemName": "DEMO CONNECTOR - Revenue Certificate System",
                "integrationType": "REST API",
                "protocol": "REST",
                "status": "CONNECTED",
                "lastSync": "2 minutes ago",
                "health": "Operational",
                "dataTypes": ["Income Certificate", "Domicile", "Land Records"],
                "version": "v1",
            },
            {
                "id": "education-demo",
                "department": "Higher & Technical Education",
                "systemName": "SAMARTH Education Registry",
                "integrationType": "REST API",
                "protocol": "REST",
                "status": "CONNECTED",
                "lastSync": "4 minutes ago",
                "health": "Operational",
                "dataTypes": ["Education Record", "Student Verification", "Scholarship Records"],
                "version": "v1",
            },
            {
                "id": "welfare-demo",
                "department": "Social Welfare Department",
                "systemName": "DEMO CONNECTOR - Welfare Eligibility System",
                "integrationType": "REST API",
                "protocol": "REST",
                "status": "CONNECTED",
                "lastSync": "7 minutes ago",
                "health": "Operational",
                "dataTypes": ["Pension", "Scholarship", "Support Eligibility"],
                "version": "v1",
            },
            {
                "id": "municipal-property-demo",
                "department": "Municipal Department",
                "systemName": "Demo Municipal Property Registry",
                "integrationType": "REST API",
                "protocol": "REST",
                "status": "CONNECTED",
                "lastSync": "2 minutes ago",
                "health": "Operational",
                "dataTypes": ["Property Record", "Municipal Assessment"],
                "version": "v1",
            },
            {
                "id": "transport-licensing-demo",
                "department": "Transport & Motor Vehicles",
                "systemName": "Sarathi RTO Services",
                "integrationType": "REST API",
                "protocol": "REST",
                "status": "CONNECTED",
                "lastSync": "2 minutes ago",
                "health": "Operational",
                "dataTypes": ["Driving Licence", "Licence Status", "Vehicle Class"],
                "version": "v1",
            },
        ]

    def fetch_record(self, department: str, citizen_id: str | int, record_type: str, purpose: str | None = None) -> dict[str, Any]:
        provider = self.providers.get(department)
        if not provider:
            raise ValueError(f"No demo provider configured for department: {department}")

        raw = provider.get_record(citizen_id, record_type, purpose)
        normalized = provider.normalize(raw, citizen_id)
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.id == int(citizen_id)).first()
            if user and user.full_name:
                normalized["name"] = user.full_name
                raw["full_name"] = user.full_name
                if "student_name" in raw:
                    raw["student_name"] = user.full_name
        finally:
            db.close()

        return {
            "source": department,
            "record_type": record_type,
            "raw": raw,
            "normalized": normalized,
            "validation": {"status": "passed", "message": "Data validated and normalized via GovFlow common model"},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def _ensure_application(self, application_id: int) -> ServiceApplication:
        db = SessionLocal()
        try:
            app = db.query(ServiceApplication).filter(ServiceApplication.id == application_id).first()
            if app is None:
                raise ValueError("Application not found.")
            return app
        finally:
            db.close()

    def request_interoperability(
        self,
        *,
        citizen_id: str | int,
        service_id: int,
        application_id: int,
        consent_id: int,
        requesting_department: str,
        source_department: str,
        data_requested: str,
        purpose: str,
    ) -> dict[str, Any]:
        if settings.data_mode != "demo":
            raise ValueError(
                "No production government connector is configured; demo connector execution is disabled."
            )
        citizen_id_int = int(citizen_id)
        application = self._ensure_application(application_id)

        db = SessionLocal()
        try:
            if application.citizen_id != citizen_id_int or application.service_id != service_id:
                raise ValueError("Application does not belong to this citizen and service.")

            consent = (
                db.query(DataShareConsent)
                .filter(
                    DataShareConsent.id == consent_id,
                    DataShareConsent.citizen_id == citizen_id_int,
                )
                .first()
            )
            if consent is None:
                raise ValueError("A matching citizen consent is required before data exchange.")
            if consent.status not in {ConsentStatus.GRANTED, ConsentStatus.ACTIVE}:
                raise ValueError("The consent is not active.")
            if consent.purpose.strip() != purpose.strip():
                raise ValueError("Consent purpose does not match this data request.")
            data_scope = f"Data requested: {data_requested}".casefold()
            if data_scope not in consent.purpose.casefold():
                raise ValueError("Consent does not include the requested data scope.")

            expires_at = consent.expires_at
            if expires_at is not None:
                if expires_at.tzinfo is None:
                    expires_at = expires_at.replace(tzinfo=timezone.utc)
                if expires_at <= datetime.now(timezone.utc):
                    raise ValueError("The consent has expired.")

            service = db.query(Service).filter(Service.id == service_id).first()
            if service is None or service.platform_id != consent.target_platform_id:
                raise ValueError("Consent does not authorize access for this service.")
            source_name = consent.source_platform.department.name if consent.source_platform else ""
            target_name = service.department.name if service.department else ""
            normalize = lambda value: "".join(character for character in value.casefold() if character.isalnum())
            if normalize(source_department) not in normalize(source_name):
                raise ValueError("Consent source department does not match this data request.")
            if normalize(requesting_department) not in normalize(target_name):
                raise ValueError("Requesting department does not match the service department.")

            consent_record_id = consent.id
            db.add(AuditLog(
                action="CONSENT_VERIFIED",
                entity_type="data_share_consent",
                entity_id=str(consent_record_id),
                details=f"Consent #{consent_record_id} verified for {requesting_department} to request {data_requested} from {source_department}.",
                actor_id=citizen_id_int,
            ))
            db.commit()
        finally:
            db.close()

        fetched = self.fetch_record(source_department, citizen_id_int, data_requested, purpose)
        is_income_record = "income" in data_requested.casefold()
        if is_income_record:
            validation = data_quality_service.validate_income_certificate(fetched["raw"])
            normalized = data_quality_service.normalize_income_certificate(fetched["raw"], citizen_id_int)
        else:
            validation = fetched["validation"]
            normalized = fetched["normalized"]
        if str(validation.get("status", "")).upper() not in {"PASSED", "SUCCESS"}:
            raise ValueError(f"{data_requested} failed source data validation.")
        transaction_id = f"TXN-{uuid.uuid4().hex[:10].upper()}"

        db = SessionLocal()
        try:
            transaction = InteroperabilityTransaction(
                transaction_id=transaction_id,
                application_id=application.id,
                citizen_id=citizen_id_int,
                consent_id=consent_record_id,
                source_system_id=consent.source_platform_id,
                destination_system_id=consent.target_platform_id,
                transaction_type="government_record_request",
                status="completed",
                requesting_department=requesting_department,
                source_department=source_department,
                data_requested=data_requested,
                purpose=purpose,
                consent_status="VERIFIED",
                request_status="SUCCESS",
                validation_status=str(validation["status"]).upper(),
                mapping_status="PASSED",
                response_status="SUCCESS",
                completed_at=datetime.now(timezone.utc),
            )
            db.add(transaction)
            db.flush()
            lifecycle = [
                ("request_received", "completed", "Interoperability request received."),
                ("consent_verified", "completed", "Citizen consent and requested scope verified."),
                ("source_response_received", "completed", "Source system returned a record."),
                ("data_validated", "completed", "Source record validated and normalized."),
                ("transaction_completed", "completed", "Normalized response delivered to destination."),
            ]
            db.add_all(
                TransactionEvent(
                    transaction_id=transaction.id,
                    event_type=event_type,
                    status=event_status,
                    detail=detail,
                )
                for event_type, event_status, detail in lifecycle
            )
            app = db.query(ServiceApplication).filter(ServiceApplication.id == application.id).first()
            if app:
                app.status = ApplicationStatus.UNDER_REVIEW
                app.remarks = f"{data_requested} retrieved from {source_department} through GovFlow interoperability and validated."
                workflow_steps = app.workflow_run.steps if app.workflow_run else []
                completed_at = datetime.now(timezone.utc)
                source_key = "".join(character for character in source_department.casefold() if character.isalnum())
                request_key = "".join(character for character in data_requested.casefold() if character.isalnum())
                for stage in workflow_steps:
                    label = "".join(character for character in stage.name.casefold() if character.isalnum())
                    relevant = "consent" in label or source_key in label or request_key in label
                    if relevant and stage.status != "completed":
                        stage.status = "completed"
                        stage.detail = f"{data_requested} verified using consent from {source_department}."
                        stage.completed_at = completed_at
                        stage.attempts = max(1, stage.attempts)
                for stage in workflow_steps:
                    if stage.status == "pending":
                        stage.status = "in_progress"
                        stage.started_at = completed_at
                        break
                db.add(
                    ApplicationEvent(
                        application_id=app.id,
                        actor_id=citizen_id_int,
                        event_type="interoperability_completed",
                        status=app.status.value,
                        note=f"{data_requested} received and validated from {source_department}.",
                    )
                )
                db.commit()
            db.add(AuditLog(
                action="INTEROPERABILITY_TRANSACTION_COMPLETED",
                entity_type="interoperability_transaction",
                entity_id=transaction_id,
                details=f"{requesting_department} received {data_requested} from {source_department} after verifying consent #{consent_record_id}.",
                actor_id=citizen_id_int,
            ))
            db.add(AuditLog(
                action="INTEROPERABILITY_DATA_RECEIVED",
                entity_type='application',
                entity_id=str(application.id),
                details=f"{requesting_department} requested {data_requested} from {source_department}. Consent granted. Data retrieved and normalized.",
                actor_id=citizen_id_int,
            ))
            db.add(AuditLog(
                action='DATA_VALIDATION_PASSED',
                entity_type='government_record',
                entity_id=transaction_id,
                details=f"{data_requested} passed data validation and normalization.",
                actor_id=citizen_id_int,
            ))
            db.commit()
            notification = notification_service.create_notification(
                citizen_id=citizen_id_int,
                title=f"{data_requested} retrieved",
                message=f"Your {data_requested} was securely retrieved from {source_department} with your permission.",
                kind='Application',
            )
            db.add(AuditLog(
                action='NOTIFICATION_SENT',
                entity_type='notification',
                entity_id=notification['id'],
                details='Citizen notification sent after approval.',
                actor_id=citizen_id_int,
            ))
            db.commit()
        finally:
            db.close()

        response = {
            "status": "success",
            "message": "Interoperability request processed successfully.",
            "transactionId": transaction_id,
            "requestingDepartment": requesting_department,
            "sourceDepartment": source_department,
            "dataRequested": data_requested,
            "consentStatus": "GRANTED",
            "requestStatus": "SUCCESS",
            "validationStatus": validation["status"],
            "mappingStatus": "PASSED",
            "responseStatus": "SUCCESS",
            "createdAt": datetime.now(timezone.utc).isoformat(),
            "completedAt": datetime.now(timezone.utc).isoformat(),
            "applicationId": application.id,
            "consentId": consent_record_id,
            "data": normalized,
            "record": {
                "source": source_department,
                "sourceType": "DEMO CONNECTOR",
                "status": "VERIFIED",
                "identifier": (
                    fetched["raw"].get("certificate_no")
                    or fetched["raw"].get("income_certificate_no")
                    or fetched["raw"].get("land_parcel_id")
                    or fetched["raw"].get("property_id")
                    or fetched["raw"].get("student_id")
                    or "GOV-RECORD"
                ),
                "timestamp": fetched['timestamp'],
            },
            "notification": notification,
            "demoMode": settings.data_mode,
        }
        return response


interoperability_service = InteroperabilityService()
