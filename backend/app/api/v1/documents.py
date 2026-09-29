import json
import logging
from pathlib import Path
from typing import Annotated
from uuid import uuid4
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, joinedload

from app.config import BASE_DIR
from app.database import get_db
from app.api.deps import (
    ensure_department_access,
    ensure_resource_access,
    get_user_role_key,
    require_authenticated_user,
    require_role,
)
from app.models.application import ServiceApplication
from app.models.application_event import ApplicationEvent
from app.models.document import Document
from app.models.document_verification_result import DocumentVerificationResult
from app.models.user import User
from app.schemas.document import DocumentRead
from app.schemas.document_verification import (
    DocumentReviewRequest,
    DocumentVerificationResultRead,
    DocumentWithVerificationResponse,
)
from app.services.audit_service import record_audit
from app.services.document_verification_service import (
    MAX_FILE_SIZE_BYTES,
    DocumentInputError,
    document_verification_service,
)
from app.services.notification_service import notification_service

router = APIRouter(prefix="/documents", tags=["Document Management & AI Verification"])
logger = logging.getLogger(__name__)


@router.get("", response_model=list[DocumentRead])
def list_documents(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[
        User,
        Depends(
            require_role(
                "citizen",
                "department_officer",
                "interoperability_admin",
                "system_admin",
            )
        ),
    ],
    owner_id: int | None = Query(None),
    application_id: int | None = Query(None),
    doc_type: str | None = Query(None),
):
    """List uploaded citizen documents."""
    query = db.query(Document)
    role_key = get_user_role_key(current_user)
    if role_key == "citizen":
        if owner_id is not None and owner_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Citizens may only view their own documents.",
            )
        query = query.filter(Document.owner_id == current_user.id)
    elif role_key == "department_officer":
        if current_user.department_id is None:
            return []
        query = query.filter(
            Document.application.has(
                ServiceApplication.department_id == current_user.department_id
            )
        )
    if owner_id is not None and role_key != "citizen":
        query = query.filter(Document.owner_id == owner_id)
    if application_id is not None:
        query = query.filter(Document.application_id == application_id)
    if doc_type:
        query = query.filter(Document.doc_type.ilike(f"%{doc_type}%"))
    return query.order_by(Document.created_at.desc()).all()


@router.get("/verifications", response_model=list[DocumentWithVerificationResponse])
def list_document_verifications(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[
        User,
        Depends(
            require_role(
                "citizen",
                "department_officer",
                "interoperability_admin",
                "system_admin",
            )
        ),
    ],
    application_id: int | None = Query(None),
    verification_status: str | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
):
    query = (
        db.query(DocumentVerificationResult)
        .join(DocumentVerificationResult.document)
        .options(
            joinedload(DocumentVerificationResult.document).joinedload(
                Document.application
            )
        )
    )
    role_key = get_user_role_key(current_user)
    if role_key == "citizen":
        query = query.filter(Document.owner_id == current_user.id)
    elif role_key == "department_officer":
        if current_user.department_id is None:
            return []
        query = query.filter(
            Document.application.has(
                ServiceApplication.department_id == current_user.department_id
            )
        )
    if application_id is not None:
        query = query.filter(Document.application_id == application_id)
    if verification_status:
        query = query.filter(
            DocumentVerificationResult.verification_status == verification_status.upper()
        )
    results = (
        query.order_by(
            DocumentVerificationResult.created_at.desc(),
            DocumentVerificationResult.id.desc(),
        )
        .limit(limit)
        .all()
    )
    return [_serialize_verification(result) for result in results]


@router.post(
    "/upload-and-verify",
    response_model=DocumentWithVerificationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_and_verify(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[
        User,
        Depends(
            require_role(
                "citizen",
                "department_officer",
                "interoperability_admin",
                "system_admin",
            )
        ),
    ],
    file: Annotated[UploadFile, File()],
    application_id: Annotated[int, Form()],
    doc_type: Annotated[str | None, Form()] = None,
):
    application = (
        db.query(ServiceApplication)
        .options(joinedload(ServiceApplication.citizen))
        .filter(ServiceApplication.id == application_id)
        .first()
    )
    if application is None:
        raise HTTPException(status_code=404, detail="Application not found.")
    ensure_resource_access(
        current_user,
        citizen_id=application.citizen_id,
        department_id=application.department_id,
    )

    content = await file.read(MAX_FILE_SIZE_BYTES + 1)
    safe_filename = Path((file.filename or "document").replace("\\", "/")).name
    try:
        processed = document_verification_service.process(
            db,
            content=content,
            filename=safe_filename,
            content_type=file.content_type,
            type_hint=doc_type,
            citizen_id=application.citizen_id,
        )
    except DocumentInputError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    extension = safe_filename.rsplit(".", 1)[-1].lower()
    stored_name = f"{uuid4().hex}.{extension}"
    storage_directory = BASE_DIR / "storage" / "documents"
    destination = storage_directory / stored_name
    try:
        storage_directory.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(content)
    except OSError as exc:
        logger.exception("Unable to persist uploaded document.")
        raise HTTPException(
            status_code=500, detail="The document could not be stored."
        ) from exc

    document = Document(
        title=safe_filename[:200],
        doc_type=processed["document_type"],
        file_path=str(Path("storage") / "documents" / stored_name),
        mime_type=processed["mime_type"],
        owner_id=application.citizen_id,
        application_id=application.id,
        is_verified=False,
        verification_score=processed["confidence"],
        fraud_risk_level=None,
        extracted_text=processed["extraction_text"],
        extracted_entities=json.dumps(processed["extracted_fields"], ensure_ascii=False),
    )
    result = DocumentVerificationResult(
        file_sha256=processed["file_sha256"],
        extracted_fields=processed["extracted_fields"],
        extraction_text=processed["extraction_text"],
        pipeline_steps=processed["pipeline_steps"],
        verification_status="PENDING_REVIEW",
        confidence=processed["confidence"],
        source_match_status=processed["source_match"]["status"],
        source_match=processed["source_match"],
        duplicate_status=processed["duplicate_status"],
        tampering_indicators=processed["tampering_indicators"],
    )
    document.verification_result = result
    db.add(document)
    try:
        db.flush()
        for step in result.pipeline_steps:
            if step["step"] == "DUPLICATE_DETECTION":
                step["status"] = result.duplicate_status
        db.add(
            ApplicationEvent(
                application_id=application.id,
                actor_id=current_user.id,
                event_type="DOCUMENT_VERIFICATION_REQUESTED",
                status=result.verification_status,
                note=f"Document #{document.id} uploaded for human review.",
            )
        )
        record_audit(
            db,
            action="DOCUMENT_VERIFICATION_REQUESTED",
            resource_type="document_verification_result",
            resource_id=result.id,
            actor_id=current_user.id,
            department_id=application.department_id,
            metadata={
                "application_id": application.id,
                "document_id": document.id,
                "source_match_status": result.source_match_status,
                "duplicate_status": result.duplicate_status,
            },
        )
        notification_service.create_event(
            db,
            event_type="APPLICATION_UPDATED",
            citizen_id=application.citizen_id,
            department_id=application.department_id,
            application_id=application.id,
            title="Document verification requested",
            message=(
                f"{document.title} was received for application "
                f"{application.reference_id} and requires officer review."
            ),
        )
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        try:
            destination.unlink(missing_ok=True)
        except OSError:
            logger.exception("Unable to remove an uncommitted uploaded document.")
        logger.exception("Unable to persist document verification.")
        raise HTTPException(
            status_code=500,
            detail="The document verification result could not be saved.",
        ) from exc
    db.refresh(document)
    db.refresh(result)
    return _serialize_verification(result)


@router.get(
    "/verifications/{verification_id}",
    response_model=DocumentWithVerificationResponse,
)
def get_document_verification(
    verification_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_authenticated_user)],
):
    result = (
        db.query(DocumentVerificationResult)
        .options(
            joinedload(DocumentVerificationResult.document).joinedload(
                Document.application
            )
        )
        .filter(DocumentVerificationResult.id == verification_id)
        .first()
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Verification result not found.")
    ensure_resource_access(
        current_user,
        citizen_id=result.document.owner_id,
        department_id=(
            result.document.application.department_id
            if result.document.application
            else None
        ),
    )
    return _serialize_verification(result)


@router.post(
    "/verifications/{verification_id}/review",
    response_model=DocumentWithVerificationResponse,
)
def review_document_verification(
    verification_id: int,
    payload: DocumentReviewRequest,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[
        User, Depends(require_role("department_officer", "system_admin"))
    ],
):
    result = (
        db.query(DocumentVerificationResult)
        .options(
            joinedload(DocumentVerificationResult.document).joinedload(
                Document.application
            )
        )
        .filter(DocumentVerificationResult.id == verification_id)
        .with_for_update()
        .first()
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Verification result not found.")
    application = result.document.application
    if application is None:
        raise HTTPException(
            status_code=409,
            detail="A linked application is required for officer review.",
        )
    ensure_department_access(current_user, application.department_id)
    if result.verification_status != "PENDING_REVIEW":
        raise HTTPException(
            status_code=409,
            detail="This document verification has already been reviewed.",
        )

    result.verification_status = payload.decision
    result.reviewed_by = current_user.id
    result.reviewed_at = datetime.now(timezone.utc)
    result.review_note = payload.note.strip()
    result.document.is_verified = payload.decision == "VERIFIED"

    application_data = dict(application.form_data or {})
    reviewed_documents = list(application_data.get("document_verifications", []))
    reviewed_documents.append(
        {
            "verification_id": result.id,
            "document_id": result.document_id,
            "status": result.verification_status,
            "source_match_status": result.source_match_status,
            "reviewed_at": result.reviewed_at.isoformat(),
        }
    )
    application_data["document_verifications"] = reviewed_documents
    application.form_data = application_data
    db.add(
        ApplicationEvent(
            application_id=application.id,
            actor_id=current_user.id,
            event_type="DOCUMENT_VERIFICATION_REVIEWED",
            status=result.verification_status,
            note=f"Document #{result.document_id}: {result.review_note}",
        )
    )
    record_audit(
        db,
        action=(
            "DOCUMENT_VERIFIED"
            if payload.decision == "VERIFIED"
            else "DOCUMENT_VERIFICATION_REJECTED"
        ),
        resource_type="document_verification_result",
        resource_id=result.id,
        actor_id=current_user.id,
        department_id=application.department_id,
        result="success" if payload.decision == "VERIFIED" else "rejected",
        metadata={
            "application_id": application.id,
            "document_id": result.document_id,
            "source_match_status": result.source_match_status,
            "duplicate_status": result.duplicate_status,
            "review_note": result.review_note,
        },
    )
    notification_service.create_event(
        db,
        event_type="APPLICATION_UPDATED",
        citizen_id=application.citizen_id,
        department_id=application.department_id,
        application_id=application.id,
        title="Document review completed",
        message=(
            f"{result.document.title} was marked {result.verification_status} "
            f"by a department officer."
        ),
    )
    db.commit()
    db.refresh(result)
    return _serialize_verification(result)


@router.get("/{document_id}", response_model=DocumentRead)
def get_document(
    document_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_authenticated_user)],
):
    """Get document details by ID."""
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    ensure_resource_access(
        current_user,
        citizen_id=doc.owner_id,
        department_id=doc.application.department_id if doc.application else None,
    )
    return doc


@router.get("/{document_id}/file")
def get_document_file(
    document_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_authenticated_user)],
):
    document = (
        db.query(Document)
        .options(joinedload(Document.application))
        .filter(Document.id == document_id)
        .first()
    )
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found.")
    ensure_resource_access(
        current_user,
        citizen_id=document.owner_id,
        department_id=(
            document.application.department_id if document.application else None
        ),
    )
    storage_root = (BASE_DIR / "storage" / "documents").resolve()
    path = (BASE_DIR / document.file_path).resolve()
    if storage_root not in path.parents or not path.is_file():
        raise HTTPException(status_code=404, detail="Stored document file not found.")
    record_audit(
        db,
        action="DOCUMENT_ACCESSED",
        resource_type="document",
        resource_id=document.id,
        actor_id=current_user.id,
        department_id=(
            document.application.department_id if document.application else None
        ),
        metadata={"mime_type": document.mime_type},
    )
    db.commit()
    return FileResponse(
        path,
        media_type=document.mime_type,
        filename=document.title,
        content_disposition_type="attachment",
    )


def _serialize_verification(
    result: DocumentVerificationResult,
) -> DocumentWithVerificationResponse:
    return DocumentWithVerificationResponse(
        document=DocumentRead.model_validate(result.document),
        verification_result=DocumentVerificationResultRead.model_validate(result),
    )
