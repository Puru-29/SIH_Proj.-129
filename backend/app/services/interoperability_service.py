from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.config import settings
from app.database import SessionLocal
from sqlalchemy.orm import Session
from app.providers.demo.education_provider import EducationDemoProvider
from app.providers.demo.municipal_provider import MunicipalDemoProvider
from app.providers.demo.revenue_provider import RevenueDemoProvider
from app.providers.demo.transport_provider import TransportDemoProvider
from app.models.user import User
from app.services.interoperability.engine import InteroperabilityEngine


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
        self.engine = InteroperabilityEngine()

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

    def fetch_record(
        self,
        department: str,
        citizen_id: str | int,
        record_type: str,
        purpose: str | None = None,
    ) -> dict[str, Any]:
        provider = self.providers.get(department)
        if provider is None:
            compact_department = self._compact(department)
            provider = next(
                (
                    configured
                    for alias, configured in self.providers.items()
                    if compact_department in self._compact(alias)
                    or self._compact(alias) in compact_department
                ),
                None,
            )
        if provider is None:
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
            "validation": {
                "status": "passed",
                "message": "Data validated and normalized via GovFlow common model",
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def _fetch_selected_connector(
        self, connector: Any, citizen_id: int, record_type: str, purpose: str
    ) -> dict[str, Any]:
        return self.fetch_record(
            connector.department, citizen_id, record_type, purpose
        )["raw"]

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
        authenticated_user: User | None = None,
        db: Session | None = None,
    ) -> dict[str, Any]:
        owns_session = db is None
        session = db or SessionLocal()
        try:
            return self.engine.process(
                session,
                citizen_id=int(citizen_id),
                service_id=service_id,
                application_id=application_id,
                consent_id=consent_id,
                requesting_department=requesting_department,
                source_department=source_department,
                data_requested=data_requested,
                purpose=purpose,
                authenticated_user=authenticated_user,
            )
        finally:
            if owns_session:
                session.close()

    @staticmethod
    def _compact(value: str) -> str:
        return "".join(character for character in value.casefold() if character.isalnum())


interoperability_service = InteroperabilityService()
