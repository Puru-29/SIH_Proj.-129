from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy.orm import Session, joinedload

from app.models.application import ApplicationStatus, ServiceApplication
from app.models.application_event import ApplicationEvent
from app.models.audit import AuditLog
from app.models.consent import ConsentStatus, DataShareConsent
from app.models.document import Document
from app.models.government_record import GovernmentRecord
from app.models.notification import Notification
from app.models.service import Service
from app.models.transaction import InteroperabilityTransaction
from app.models.workflow import Workflow, WorkflowStep
from app.schemas.workflow import WorkflowDefinitionCreate


SCHOLARSHIP_WORKFLOW: dict[str, Any] = {
    "name": "Post-Matric Scholarship",
    "required_records": ["Revenue", "Education"],
    "required_consents": [
        "Student enrolment and academic record",
        "Verified household income record",
    ],
    "departments": ["Social Welfare", "Revenue", "Education"],
    "sla_hours": 120,
    "steps": [
        {
            "step_id": "consent",
            "name": "Consent confirmation",
            "department": "Social Welfare",
            "type": "CONSENT",
            "order": 0,
            "required": True,
            "action": {"required_consents": ["revenue_income", "education_enrollment"]},
            "next_steps": ["income_request"],
        },
        {
            "step_id": "income_request",
            "name": "Verify household income",
            "department": "Revenue",
            "type": "DATA_REQUEST",
            "order": 1,
            "required": True,
            "action": {"record": "income", "consent": "Verified household income record"},
            "next_steps": ["education_request"],
        },
        {
            "step_id": "education_request",
            "name": "Verify student enrollment",
            "department": "Education",
            "type": "DATA_REQUEST",
            "order": 2,
            "required": True,
            "action": {"record": "student_enrollment", "consent": "Student enrolment and academic record"},
            "next_steps": ["documents"],
        },
        {
            "step_id": "documents",
            "name": "Upload supporting documents",
            "department": "Social Welfare",
            "type": "DOCUMENT_UPLOAD",
            "order": 3,
            "required": True,
            "action": {"require_at_least_one_document": True},
            "next_steps": ["document_verification"],
        },
        {
            "step_id": "document_verification",
            "name": "Verify supporting documents",
            "department": "Social Welfare",
            "type": "DOCUMENT_VERIFICATION",
            "order": 4,
            "required": True,
            "action": {},
            "next_steps": ["data_validation"],
        },
        {
            "step_id": "data_validation",
            "name": "Validate eligibility data",
            "department": "Social Welfare",
            "type": "DATA_VALIDATION",
            "order": 5,
            "required": True,
            "action": {"required_records": ["Revenue", "Education"]},
            "next_steps": ["officer_review"],
        },
        {
            "step_id": "officer_review",
            "name": "Officer review",
            "department": "Social Welfare",
            "type": "OFFICER_REVIEW",
            "order": 6,
            "required": True,
            "action": {},
            "next_steps": ["approval", "rejection"],
        },
        {
            "step_id": "approval",
            "name": "Approve application",
            "department": "Social Welfare",
            "type": "APPROVAL",
            "order": 7,
            "required": False,
            "action": {},
            "next_steps": ["notification"],
        },
        {
            "step_id": "rejection",
            "name": "Reject application",
            "department": "Social Welfare",
            "type": "REJECTION",
            "order": 8,
            "required": False,
            "action": {},
            "next_steps": ["notification"],
        },
        {
            "step_id": "notification",
            "name": "Notify applicant of the decision",
            "department": "Social Welfare",
            "type": "NOTIFICATION",
            "order": 9,
            "required": True,
            "action": {
                "title": "Scholarship application decision",
                "message": "Your scholarship application has been reviewed.",
            },
            "next_steps": ["completion"],
        },
        {
            "step_id": "completion",
            "name": "Complete application workflow",
            "department": "Social Welfare",
            "type": "COMPLETION",
            "order": 10,
            "required": True,
            "action": {},
            "next_steps": [],
        },
    ],
    "transitions": {
        "consent": ["income_request"],
        "income_request": ["education_request"],
        "education_request": ["documents"],
        "documents": ["document_verification"],
        "document_verification": ["data_validation"],
        "data_validation": ["officer_review"],
        "officer_review": ["approval", "rejection"],
        "approval": ["notification"],
        "rejection": ["notification"],
        "notification": ["completion"],
        "completion": [],
    },
}


class WorkflowEngineError(ValueError):
    pass


class WorkflowEngine:
    def latest_definition(self, db: Session, service_id: int) -> Workflow | None:
        return (
            db.query(Workflow)
            .options(joinedload(Workflow.steps))
            .filter(
                Workflow.service_id == service_id,
                Workflow.application_id.is_(None),
                Workflow.status == "active",
            )
            .order_by(Workflow.version.desc(), Workflow.id.desc())
            .first()
        )

    def ensure_definition(self, db: Session, service: Service) -> Workflow | None:
        definition = self.latest_definition(db, service.id)
        if definition is not None:
            return definition
        service_key = f"{service.code} {service.name}".casefold()
        if "post_matric" in service_key or "post-matric" in service_key:
            template = SCHOLARSHIP_WORKFLOW
        else:
            department = service.department.name if service.department else "Service Department"
            template = {
                "name": f"{service.name} workflow",
                "required_records": [],
                "required_consents": [],
                "departments": [department],
                "sla_hours": 120,
                "steps": [
                    {
                        "step_id": "officer_review",
                        "name": "Officer review",
                        "department": department,
                        "type": "OFFICER_REVIEW",
                        "order": 0,
                        "required": True,
                        "action": {},
                        "next_steps": ["approval", "rejection"],
                    },
                    {
                        "step_id": "approval",
                        "name": "Approve application",
                        "department": department,
                        "type": "APPROVAL",
                        "order": 1,
                        "required": False,
                        "action": {},
                        "next_steps": ["notification"],
                    },
                    {
                        "step_id": "rejection",
                        "name": "Reject application",
                        "department": department,
                        "type": "REJECTION",
                        "order": 2,
                        "required": False,
                        "action": {},
                        "next_steps": ["notification"],
                    },
                    {
                        "step_id": "notification",
                        "name": "Notify applicant",
                        "department": department,
                        "type": "NOTIFICATION",
                        "order": 3,
                        "required": True,
                        "action": {
                            "title": f"{service.name} application update",
                            "message": "Your application has been reviewed.",
                        },
                        "next_steps": ["completion"],
                    },
                    {
                        "step_id": "completion",
                        "name": "Complete application workflow",
                        "department": department,
                        "type": "COMPLETION",
                        "order": 4,
                        "required": True,
                        "action": {},
                        "next_steps": [],
                    },
                ],
                "transitions": {
                    "officer_review": ["approval", "rejection"],
                    "approval": ["notification"],
                    "rejection": ["notification"],
                    "notification": ["completion"],
                    "completion": [],
                },
            }
        payload = WorkflowDefinitionCreate.model_validate(
            {**template, "service_id": service.id}
        )
        return self.create_definition(db, payload)

    def create_definition(
        self,
        db: Session,
        payload: WorkflowDefinitionCreate,
    ) -> Workflow:
        service = db.query(Service).filter(Service.id == payload.service_id).first()
        if service is None:
            raise WorkflowEngineError("Service not found.")
        prior_definitions = (
            db.query(Workflow)
            .filter(
                Workflow.service_id == payload.service_id,
                Workflow.application_id.is_(None),
            )
            .all()
        )
        version = max((item.version for item in prior_definitions), default=0) + 1
        for previous in prior_definitions:
            previous.status = "inactive"

        transitions = {
            key: list(targets) for key, targets in payload.transitions.items()
        }
        for step in payload.steps:
            transitions.setdefault(step.step_id, list(step.next_steps))
        definition = Workflow(
            service_id=payload.service_id,
            name=payload.name,
            version=version,
            status="active",
            required_records=payload.required_records,
            required_consents=payload.required_consents,
            departments=payload.departments,
            transitions=transitions,
            sla_hours=payload.sla_hours,
        )
        definition.steps = [
            WorkflowStep(
                step_key=step.step_id,
                name=step.name,
                department=step.department,
                sequence=step.order,
                step_type=step.type.value,
                required=step.required,
                action=step.action,
                next_steps=transitions[step.step_id],
                status="configured",
            )
            for step in sorted(payload.steps, key=lambda item: item.order)
        ]
        db.add(definition)
        db.commit()
        db.refresh(definition)
        return definition

    def create_run(
        self,
        db: Session,
        application: ServiceApplication,
        definition: Workflow,
    ) -> Workflow:
        now = datetime.now(timezone.utc)
        workflow = Workflow(
            service_id=definition.service_id,
            application_id=application.id,
            name=definition.name,
            version=definition.version,
            status="active",
            required_records=list(definition.required_records or []),
            required_consents=list(definition.required_consents or []),
            departments=list(definition.departments or []),
            transitions=dict(definition.transitions or {}),
            sla_hours=definition.sla_hours,
            sla_due_at=(
                now + timedelta(hours=definition.sla_hours)
                if definition.sla_hours
                else None
            ),
        )
        workflow.steps = [
            WorkflowStep(
                step_key=step.step_key,
                name=step.name,
                department=step.department,
                sequence=step.sequence,
                step_type=step.step_type,
                required=step.required,
                action=dict(step.action or {}),
                next_steps=list(step.next_steps or []),
                status="in_progress" if index == 0 else "pending",
                attempts=1 if index == 0 else 0,
                detail="Workflow started." if index == 0 else None,
                started_at=now if index == 0 else None,
            )
            for index, step in enumerate(definition.steps)
        ]
        db.add(workflow)
        db.flush()
        application.workflow_run = workflow
        first_step = workflow.steps[0] if workflow.steps else None
        if (
            first_step is not None
            and first_step.step_type == "CONSENT"
            and self._consent_requirements_met(
                db, application.citizen_id, workflow.required_consents or []
            )
        ):
            first_step.status = "completed"
            first_step.completed_at = now
            first_step.detail = "All required consent requests are approved."
            self._activate_next_steps(workflow, first_step, now)
        return workflow

    def transition_step(
        self,
        db: Session,
        application: ServiceApplication,
        step_key: str,
        *,
        next_status: str,
        actor_id: int,
        detail: str | None = None,
        error: str | None = None,
        next_step: str | None = None,
    ) -> Workflow:
        run = application.workflow_run
        if run is None or run.application_id is None:
            raise WorkflowEngineError("No workflow run exists for this application.")
        step = next((item for item in run.steps if item.step_key == step_key), None)
        if step is None:
            raise WorkflowEngineError(f"Workflow step '{step_key}' was not found.")
        if step.status in {"completed", "failed", "skipped"}:
            raise WorkflowEngineError("A terminal workflow step cannot be changed.")
        allowed_statuses = {"in_progress", "completed", "failed", "skipped"}
        if next_status not in allowed_statuses:
            raise WorkflowEngineError("Unsupported workflow step status.")
        if step.status == "pending" and next_status != "in_progress":
            raise WorkflowEngineError("A pending step must be started before it can finish.")
        if next_status == "skipped" and step.required:
            raise WorkflowEngineError("A required workflow step cannot be skipped.")
        if next_status == "completed":
            self._validate_step_prerequisites(db, application, run, step)
            outgoing = set(
                (run.transitions or {}).get(step.step_key)
                or step.next_steps
                or []
            )
            if len(outgoing) > 1 and next_step not in outgoing:
                raise WorkflowEngineError(
                    "Select one configured next_step for this branching step."
                )
            if next_step is not None and next_step not in outgoing:
                raise WorkflowEngineError(
                    f"Step '{next_step}' is not a configured successor of '{step.step_key}'."
                )
            if step.step_type == "COMPLETION":
                self._validate_required_steps(run, completing=step.step_key)

        now = datetime.now(timezone.utc)
        step.status = next_status
        step.attempts += 1
        step.detail = detail or step.detail
        step.error_message = error
        if next_status == "in_progress":
            step.started_at = step.started_at or now
        if next_status in {"completed", "failed", "skipped"}:
            step.completed_at = now

        if next_status == "completed":
            if step.step_type == "APPROVAL":
                application.status = ApplicationStatus.APPROVED
            elif step.step_type == "REJECTION":
                application.status = ApplicationStatus.REJECTED
            self._activate_next_steps(run, step, now, selected=next_step)
            if step.step_type == "COMPLETION":
                run.status = "completed"
            for target in run.steps:
                if target.status == "in_progress" and target.step_type == "NOTIFICATION":
                    self._execute_notification(db, application, target, now)

        if next_status == "failed":
            run.status = "failed"
        db.add(
            ApplicationEvent(
                application_id=application.id,
                actor_id=actor_id,
                event_type="workflow_step_" + next_status,
                status=next_status,
                note=detail or error or step.name,
            )
        )
        db.add(
            AuditLog(
                action="WORKFLOW_STEP_" + next_status.upper(),
                entity_type="workflow_step",
                entity_id=str(step.id),
                details=f"{run.name}: {step.step_key} {next_status}.",
                actor_id=actor_id,
            )
        )
        db.commit()
        db.refresh(run)
        return run

    def sync_completed_data_request(
        self,
        db: Session,
        application: ServiceApplication,
        *,
        source_department: str,
        actor_id: int,
    ) -> None:
        run = application.workflow_run
        if run is None:
            return
        source = self._compact(source_department)
        for step in run.steps:
            if (
                step.step_type == "DATA_REQUEST"
                and step.status == "in_progress"
                and step.department
                and self._same_department(source, self._compact(step.department))
            ):
                self.transition_step(
                    db,
                    application,
                    step.step_key,
                    next_status="completed",
                    actor_id=actor_id,
                    detail=f"Verified data received from {source_department}.",
                )
                return

    @staticmethod
    def _validate_step_prerequisites(
        db: Session,
        application: ServiceApplication,
        workflow: Workflow,
        step: WorkflowStep,
    ) -> None:
        if step.step_type == "CONSENT":
            requirements = workflow.required_consents or []
            if not WorkflowEngine._consent_requirements_met(
                db, application.citizen_id, requirements
            ):
                unmatched = ", ".join(requirements)
                raise WorkflowEngineError(
                    "Required approved consents are missing or expired: "
                    + unmatched
                )
        elif step.step_type == "DATA_REQUEST":
            department = step.department or ""
            successful = (
                db.query(InteroperabilityTransaction)
                .filter(
                    InteroperabilityTransaction.application_id == application.id,
                    InteroperabilityTransaction.status == "COMPLETED",
                )
                .all()
            )
            if not any(
                WorkflowEngine._same_department(
                    WorkflowEngine._compact(transaction.source_department),
                    WorkflowEngine._compact(department),
                )
                for transaction in successful
            ):
                raise WorkflowEngineError(
                    f"No completed data request exists for {department}."
                )
        elif step.step_type == "DOCUMENT_UPLOAD":
            if (
                db.query(Document.id)
                .filter(Document.application_id == application.id)
                .first()
                is None
            ):
                raise WorkflowEngineError("At least one application document is required.")
        elif step.step_type == "DOCUMENT_VERIFICATION":
            if not application.documents or any(
                not document.is_verified for document in application.documents
            ):
                raise WorkflowEngineError(
                    "All uploaded application documents must be verified."
                )
        elif step.step_type == "DATA_VALIDATION":
            required = workflow.required_records or []
            records = (
                db.query(GovernmentRecord)
                .filter(
                    GovernmentRecord.application_id == application.id,
                    GovernmentRecord.status == "VERIFIED",
                )
                .all()
            )
            missing = [
                department
                for department in required
                if not any(
                    WorkflowEngine._same_department(
                        WorkflowEngine._compact(record.department.name if record.department else ""),
                        WorkflowEngine._compact(department),
                    )
                    for record in records
                )
            ]
            if missing:
                raise WorkflowEngineError(
                    "Required verified government records are missing: "
                    + ", ".join(missing)
                )

    @staticmethod
    def _consent_requirements_met(
        db: Session,
        citizen_id: int,
        requirements: list[str],
    ) -> bool:
        if not requirements:
            return True
        active_consents = (
            db.query(DataShareConsent)
            .filter(
                DataShareConsent.citizen_id == citizen_id,
                DataShareConsent.status == ConsentStatus.GRANTED,
            )
            .all()
        )
        now = datetime.now(timezone.utc)
        active_consents = [
            consent
            for consent in active_consents
            if consent.revoked_at is None
            and consent.expires_at is not None
            and WorkflowEngine._as_utc(consent.expires_at) > now
        ]
        return all(
            any(
                requirement.casefold() in consent.requested_data.casefold()
                or consent.requested_data.casefold() in requirement.casefold()
                for consent in active_consents
            )
            for requirement in requirements
        )

    @staticmethod
    def _as_utc(value: datetime) -> datetime:
        return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value

    @staticmethod
    def _compact(value: str) -> str:
        return "".join(character for character in value.casefold() if character.isalnum())

    @staticmethod
    def _same_department(left: str, right: str) -> bool:
        return bool(left and right and (left in right or right in left))

    @staticmethod
    def _activate_next_steps(
        workflow: Workflow,
        current: WorkflowStep,
        now: datetime,
        *,
        selected: str | None = None,
    ) -> None:
        allowed = set(
            (workflow.transitions or {}).get(current.step_key)
            or current.next_steps
            or []
        )
        if selected is not None:
            allowed = {selected}
        for next_step in workflow.steps:
            if next_step.step_key in allowed and next_step.status == "pending":
                next_step.status = "in_progress"
                next_step.started_at = now
                next_step.attempts += 1

    @staticmethod
    def _validate_required_steps(
        workflow: Workflow,
        *,
        completing: str,
    ) -> None:
        unfinished = [
            step.step_key
            for step in workflow.steps
            if step.required
            and step.step_type != "REJECTION"
            and step.step_key != completing
            and step.status not in {"completed", "skipped"}
        ]
        if unfinished:
            raise WorkflowEngineError(
                "Required workflow steps are incomplete: " + ", ".join(unfinished)
            )

    @staticmethod
    def _execute_notification(
        db: Session,
        application: ServiceApplication,
        step: WorkflowStep,
        now: datetime,
    ) -> None:
        action = step.action or {}
        db.add(
            Notification(
                recipient_id=application.citizen_id,
                application_id=application.id,
                notification_type="Workflow",
                title=action.get("title") or step.name,
                message=action.get("message") or step.detail or step.name,
                status="unread",
            )
        )
        step.status = "completed"
        step.completed_at = now
        step.detail = "Notification sent."
        WorkflowEngine._activate_next_steps(application.workflow_run, step, now)


workflow_engine = WorkflowEngine()
