from __future__ import annotations

import base64
import hashlib
import io
import re
from datetime import datetime
from typing import Any

import fitz
from PIL import Image, UnidentifiedImageError
from sqlalchemy.orm import Session

from app.ml.easyocr_engine import easyocr_engine
from app.models.document_verification_result import DocumentVerificationResult
from app.services.interoperability_service import interoperability_service

MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024
MAX_PDF_PAGES = 10


class DocumentInputError(ValueError):
    pass


class DocumentVerificationService:
    def process(
        self,
        db: Session,
        *,
        content: bytes,
        filename: str,
        content_type: str | None,
        type_hint: str | None,
        citizen_id: int,
    ) -> dict[str, Any]:
        extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        if extension not in {"pdf", "jpg", "jpeg", "png"}:
            raise DocumentInputError("Upload a PDF, JPG, or PNG document.")
        if not content or len(content) > MAX_FILE_SIZE_BYTES:
            raise DocumentInputError("Document must be between 1 byte and 10 MB.")

        expected_mime = {
            "pdf": "application/pdf",
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
            "png": "image/png",
        }[extension]
        if content_type and content_type.lower() not in {
            expected_mime,
            "image/jpg" if extension in {"jpg", "jpeg"} else expected_mime,
            "application/octet-stream",
        }:
            raise DocumentInputError("The file type does not match its extension.")

        file_sha256 = hashlib.sha256(content).hexdigest()
        extracted_text, extraction_signal, file_steps = self._extract_text(
            content, extension
        )
        extracted_fields, format_findings = self._extract_fields(extracted_text)
        document_type = self._detect_document_type(
            extracted_text, type_hint
        )
        duplicate_status = (
            "DUPLICATE"
            if db.query(DocumentVerificationResult)
            .filter(DocumentVerificationResult.file_sha256 == file_sha256)
            .first()
            else "UNIQUE"
        )

        source_match = {"status": "NOT_CHECKED"}
        certificate_number = extracted_fields.get("certificate_number")
        if certificate_number:
            source_match = interoperability_service.engine.match_document_record(
                db,
                citizen_id=citizen_id,
                certificate_number=certificate_number,
                extracted_fields=extracted_fields,
            )

        confidence = round(
            extraction_signal
            * (
                0.6
                + 0.4
                * sum(
                    extracted_fields.get(field) is not None
                    for field in ("name", "certificate_number", "issue_date", "issuer", "income")
                )
                / 5
            ),
            3,
        )
        indicators = list(format_findings)
        if duplicate_status == "DUPLICATE":
            indicators.append(
                "Identical file content was previously uploaded; review for reuse."
            )
        if source_match["status"] == "MISMATCHED":
            indicators.append(
                "Extracted values differ from the matched source record; review the documents."
            )
        pipeline_steps = [
            {"step": "FILE_INTEGRITY_VALIDATION", "status": "COMPLETED"},
            {
                "step": "DOCUMENT_TYPE_DETECTION",
                "status": "COMPLETED" if document_type != "Unknown" else "NEEDS_REVIEW",
                "document_type": document_type,
            },
            *file_steps,
            {
                "step": "FIELD_EXTRACTION",
                "status": "COMPLETED" if extracted_fields else "NEEDS_REVIEW",
                "fields_found": sorted(extracted_fields),
            },
            {
                "step": "FORMAT_VALIDATION",
                "status": "NEEDS_REVIEW" if format_findings else "COMPLETED",
                "findings": format_findings,
            },
            {
                "step": "SOURCE_RECORD_MATCHING",
                "status": source_match["status"],
            },
            {"step": "DUPLICATE_DETECTION", "status": duplicate_status},
            {
                "step": "TAMPERING_INDICATORS",
                "status": "REVIEW_ONLY",
                "indicators": indicators,
            },
            {
                "step": "CONFIDENCE_ASSESSMENT",
                "status": "COMPLETED",
                "confidence_scope": "Extraction signal only; not authenticity or fraud probability.",
            },
            {"step": "HUMAN_REVIEW", "status": "REQUIRED"},
        ]
        return {
            "file_sha256": file_sha256,
            "mime_type": expected_mime,
            "document_type": document_type,
            "extraction_text": extracted_text,
            "extracted_fields": extracted_fields,
            "source_match": source_match,
            "duplicate_status": duplicate_status,
            "confidence": confidence,
            "tampering_indicators": indicators,
            "pipeline_steps": pipeline_steps,
        }

    @staticmethod
    def _extract_text(
        content: bytes, extension: str
    ) -> tuple[str, float, list[dict[str, Any]]]:
        steps: list[dict[str, Any]] = []
        text_parts: list[str] = []
        ocr_confidences: list[float] = []
        if extension == "pdf":
            try:
                pdf = fitz.open(stream=content, filetype="pdf")
            except (fitz.FileDataError, RuntimeError) as exc:
                raise DocumentInputError("The PDF is damaged or cannot be read.") from exc
            if pdf.is_encrypted:
                raise DocumentInputError("Password-protected PDFs are not supported.")
            if not 1 <= pdf.page_count <= MAX_PDF_PAGES:
                raise DocumentInputError(
                    f"PDFs must contain between 1 and {MAX_PDF_PAGES} pages."
                )
            for page_number, page in enumerate(pdf, start=1):
                page_text = page.get_text("text").strip()
                if page_text:
                    text_parts.append(page_text)
                    continue
                png_bytes = page.get_pixmap(matrix=fitz.Matrix(2, 2)).tobytes("png")
                ocr_text, ocr_confidence = DocumentVerificationService._ocr(png_bytes)
                if ocr_text:
                    text_parts.append(ocr_text)
                if ocr_confidence is not None:
                    ocr_confidences.append(ocr_confidence)
                steps.append(
                    {
                        "step": "OCR_TEXT_EXTRACTION",
                        "page": page_number,
                        "status": "COMPLETED" if ocr_text else "NEEDS_REVIEW",
                    }
                )
            pdf.close()
        else:
            try:
                image = Image.open(io.BytesIO(content))
                actual_format = image.format
                expected_format = "JPEG" if extension in {"jpg", "jpeg"} else "PNG"
                if actual_format != expected_format:
                    raise DocumentInputError("The image content does not match its extension.")
                image.verify()
                image = Image.open(io.BytesIO(content)).convert("RGB")
            except DocumentInputError:
                raise
            except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
                raise DocumentInputError("The image is damaged or cannot be read.") from exc
            png_output = io.BytesIO()
            image.save(png_output, format="PNG")
            ocr_text, ocr_confidence = DocumentVerificationService._ocr(
                png_output.getvalue()
            )
            if ocr_text:
                text_parts.append(ocr_text)
            if ocr_confidence is not None:
                ocr_confidences.append(ocr_confidence)
            steps.append(
                {
                    "step": "OCR_TEXT_EXTRACTION",
                    "status": "COMPLETED" if ocr_text else "NEEDS_REVIEW",
                }
            )
        text = "\n".join(text_parts).strip()
        steps.append(
            {
                "step": "OCR_TEXT_EXTRACTION",
                "status": "COMPLETED" if text else "NEEDS_REVIEW",
            }
        )
        extraction_signal = (
            sum(ocr_confidences) / len(ocr_confidences)
            if ocr_confidences
            else 0.8 if text else 0.0
        )
        return text, extraction_signal, steps

    @staticmethod
    def _ocr(image_bytes: bytes) -> tuple[str, float | None]:
        image_base64 = base64.b64encode(image_bytes).decode("ascii")
        result = easyocr_engine.extract_text(
            image_input=f"data:image/png;base64,{image_base64}",
            allow_fallback=False,
        )
        if not result["success"]:
            return "", None
        return result["extracted_text"], float(result["average_confidence"])

    @staticmethod
    def _detect_document_type(text: str, hint: str | None) -> str:
        content = text.casefold()
        types = (
            (("income certificate", "annual family income"), "Income Certificate"),
            (("caste certificate", "caste certificate"), "Caste Certificate"),
            (("7/12 extract", "7/12", "land record"), "Land Record"),
            (("aadhaar", "uidai"), "Aadhaar"),
            (("permanent account number", "pan card"), "PAN"),
            (("driving licence", "driver license", "driving license"), "Driving License"),
        )
        for markers, label in types:
            if any(marker in content for marker in markers):
                return label
        return hint.strip()[:80] if hint and hint.strip() else "Unknown"

    @staticmethod
    def _extract_fields(text: str) -> tuple[dict[str, Any], list[str]]:
        fields: dict[str, Any] = {}
        findings: list[str] = []
        patterns = {
            "name": r"(?im)^\s*(?:applicant(?:\s+name)?|name)\s*[:\-]\s*(.{2,100})$",
            "certificate_number": (
                r"(?im)^\s*(?:income\s+)?certificate\s*(?:no\.?|number|#)\s*[:\-]?\s*"
                r"([A-Z0-9][A-Z0-9/\-]{2,79})\s*$"
            ),
            "issue_date": r"(?im)^\s*(?:issue|issued|date\s+of\s+issue)\s*date?\s*[:\-]\s*(.{3,40})$",
            "income": r"(?im)^\s*(?:annual\s+family\s+income|annual\s+income|income)\s*[:\-]\s*(?:INR|Rs\.?|₹)?\s*([\d,]+(?:\.\d{1,2})?)",
        }
        for field, pattern in patterns.items():
            match = re.search(pattern, text)
            if match:
                value = match.group(1).strip()
                if field == "certificate_number":
                    fields[field] = value.upper()
                elif field == "income":
                    fields[field] = float(value.replace(",", ""))
                elif field == "issue_date":
                    normalized_date = DocumentVerificationService._normalize_date(value)
                    if normalized_date:
                        fields[field] = normalized_date
                    else:
                        findings.append("The issue date could not be parsed.")
                else:
                    fields[field] = value
        issuer = next(
            (
                line.strip()
                for line in text.splitlines()
                if re.search(r"\b(government|department|authority|revenue|issuer)\b", line, re.I)
            ),
            None,
        )
        if issuer:
            fields["issuer"] = issuer[:200]
        if "certificate_number" not in fields:
            findings.append("Certificate number was not extracted.")
        if "name" not in fields:
            findings.append("Applicant name was not extracted.")
        return fields, findings

    @staticmethod
    def _normalize_date(value: str) -> str | None:
        for date_format in (
            "%d/%m/%Y",
            "%d-%m-%Y",
            "%Y-%m-%d",
            "%d/%m/%y",
            "%d-%m-%y",
        ):
            try:
                return datetime.strptime(value.strip(), date_format).date().isoformat()
            except ValueError:
                continue
        return None


document_verification_service = DocumentVerificationService()
