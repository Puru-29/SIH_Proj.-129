import json
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.document import Document
from app.models.user import User
from app.schemas.document import DocumentCreate, DocumentRead
from app.ml.pipeline import verification_pipeline

router = APIRouter(prefix="/documents", tags=["Document Management & AI Verification"])


class UploadAndVerifyRequest(BaseModel):
    title: str
    doc_type: str
    owner_id: int
    application_id: int | None = None
    image_base64: str | None = None
    document_text: str | None = None
    citizen_full_name: str | None = None
    citizen_aadhaar_last4: str | None = None
    claimed_income: float | None = None
    mesh_income: float | None = None
    claimed_land_acres: float | None = None
    mesh_land_acres: float | None = None
    applicant_remarks: str | None = None


class DocumentWithVerificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    document: DocumentRead
    ai_pipeline_result: dict


@router.get("", response_model=list[DocumentRead])
def list_documents(
    db: Annotated[Session, Depends(get_db)],
    owner_id: int | None = Query(None),
    application_id: int | None = Query(None),
    doc_type: str | None = Query(None),
):
    """List uploaded citizen documents."""
    query = db.query(Document)
    if owner_id:
        query = query.filter(Document.owner_id == owner_id)
    if application_id:
        query = query.filter(Document.application_id == application_id)
    if doc_type:
        query = query.filter(Document.doc_type.ilike(f"%{doc_type}%"))
    return query.order_by(Document.created_at.desc()).all()


@router.get("/{document_id}", response_model=DocumentRead)
def get_document(document_id: int, db: Annotated[Session, Depends(get_db)]):
    """Get document details by ID."""
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return doc


@router.post("/upload-and-verify", response_model=DocumentWithVerificationResponse)
def upload_and_verify(payload: UploadAndVerifyRequest, db: Annotated[Session, Depends(get_db)]):
    """
    Submits a document (base64 image or text payload) and runs it through the
    multi-model AI pipeline (EasyOCR, LayoutLMv3, spaCy NER, Anomaly Detection & Tabular Risk),
    saving the authenticated result in the database.
    """
    owner = db.query(User).filter(User.id == payload.owner_id).first()
    if not owner:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document owner user not found")

    # Run AI verification pipeline
    verification_res = verification_pipeline.verify_document(
        image_base64=payload.image_base64,
        document_text=payload.document_text,
        citizen_full_name=payload.citizen_full_name or owner.full_name,
        citizen_aadhaar_last4=payload.citizen_aadhaar_last4 or owner.aadhaar_last4,
        claimed_income=payload.claimed_income,
        mesh_income=payload.mesh_income,
        claimed_land_acres=payload.claimed_land_acres,
        mesh_land_acres=payload.mesh_land_acres,
        applicant_remarks=payload.applicant_remarks,
    )

    overall_verdict = verification_res.get("overall_verdict", "EVALUATED")
    confidence_score = float(verification_res.get("confidence_score", 0.95))
    risk_level = str(verification_res.get("risk_level", "LOW"))
    extracted_identities = verification_res.get("extracted_identities", {})

    doc = Document(
        title=payload.title,
        doc_type=payload.doc_type,
        file_path="virtual://" + payload.title.lower().replace(" ", "_"),
        mime_type="image/jpeg" if payload.image_base64 else "text/plain",
        owner_id=payload.owner_id,
        application_id=payload.application_id,
        is_verified=(overall_verdict in ["APPROVED", "VERIFIED"]),
        verification_score=confidence_score,
        fraud_risk_level=risk_level,
        extracted_text=payload.document_text,
        extracted_entities=json.dumps(extracted_identities) if extracted_identities else None,
    )

    db.add(doc)
    db.commit()
    db.refresh(doc)

    return DocumentWithVerificationResponse(
        document=DocumentRead.model_validate(doc),
        ai_pipeline_result=verification_res,
    )
