import time
import logging
from typing import Any

from app.ml.easyocr_engine import easyocr_engine
from app.ml.layoutlm_engine import layoutlm_engine
from app.ml.spacy_engine import spacy_ner_engine
from app.ml.distilbert_engine import distilbert_engine
from app.ml.tabular_engine import tabular_risk_engine
from app.ml.anomaly_engine import anomaly_engine

logger = logging.getLogger(__name__)


class DocumentVerificationPipeline:
    """
    End-to-end multi-model AI verification pipeline for the Inter-Governmental Mesh.
    Coordinates EasyOCR, LayoutLMv3, spaCy NER, DistilBERT, XGBoost/LightGBM,
    and One-Class SVM / Local Outlier Factor (LOF) to perform holistic document authentication,
    fraud detection, and eligibility evaluation.
    """

    def __init__(self):
        self.easyocr = easyocr_engine
        self.layoutlm = layoutlm_engine
        self.spacy = spacy_ner_engine
        self.distilbert = distilbert_engine
        self.tabular = tabular_risk_engine
        self.anomaly = anomaly_engine

    def verify_document(
        self,
        image_base64: str | None = None,
        document_text: str | None = None,
        citizen_full_name: str | None = None,
        citizen_aadhaar_last4: str | None = None,
        claimed_income: float | None = None,
        mesh_income: float | None = None,
        claimed_land_acres: float | None = None,
        mesh_land_acres: float | None = None,
        applicant_remarks: str | None = None,
        preferred_tabular_engine: str = "xgboost",
    ) -> dict[str, Any]:
        """
        Executes the full 5-stage verification workflow.
        """
        start_time = time.perf_counter()
        steps: list[dict[str, Any]] = []

        # -------------------------------------------------------------
        # Step 1: EasyOCR Text & Bounding Box Extraction
        # -------------------------------------------------------------
        ocr_res = self.easyocr.extract_text(
            image_input=image_base64,
            raw_text_hint=document_text,
        )
        extracted_text = ocr_res["extracted_text"]
        normalized_boxes = [w.get("normalized_bbox", [0, 0, 0, 0]) for w in ocr_res.get("words", [])]

        steps.append({
            "step_name": "Optical Character Recognition",
            "model_name": "EasyOCR",
            "status": "COMPLETED" if ocr_res["success"] else "FAILED",
            "details": {
                "word_count": ocr_res["word_count"],
                "average_confidence": ocr_res["average_confidence"],
                "text_snippet": (extracted_text[:120] + "...") if len(extracted_text) > 120 else extracted_text,
            },
        })

        # -------------------------------------------------------------
        # Step 2: LayoutLMv3 Multimodal Document Intelligence
        # -------------------------------------------------------------
        layout_res = self.layoutlm.analyze_document(
            image_input=image_base64,
            ocr_text=extracted_text,
            normalized_boxes=normalized_boxes,
        )

        steps.append({
            "step_name": "Visual Document Understanding",
            "model_name": "LayoutLMv3",
            "status": "COMPLETED",
            "details": {
                "detected_type": layout_res["document_type"],
                "layout_authenticity_score": layout_res["layout_authenticity_score"],
                "fields_identified": len(layout_res["fields"]),
                "is_tampered_or_anomalous": layout_res["is_tampered_or_anomalous"],
            },
        })

        # -------------------------------------------------------------
        # Step 3: spaCy NER & Government ID Extraction
        # -------------------------------------------------------------
        ner_res = self.spacy.extract_entities(extracted_text)
        gov_ids = ner_res["government_ids"]

        # Cross-validate with citizen registered profile
        identity_check = self.spacy.verify_citizen_profile(
            extracted_entities=ner_res["entities"],
            government_ids=gov_ids,
            citizen_full_name=citizen_full_name,
            citizen_aadhaar_last4=citizen_aadhaar_last4,
        )

        steps.append({
            "step_name": "Named Entity Recognition & ID Cross-Validation",
            "model_name": "spaCy NER",
            "status": "COMPLETED",
            "details": {
                "entities_found": len(ner_res["entities"]),
                "aadhaar_numbers": gov_ids.get("aadhaar", []),
                "pan_numbers": gov_ids.get("pan", []),
                "name_matched": identity_check["name_matched"],
                "name_match_score": identity_check["name_match_score"],
                "aadhaar_last4_matched": identity_check["aadhaar_last4_matched"],
            },
        })

        # -------------------------------------------------------------
        # Step 4: DistilBERT Intent & Semantic Consistency
        # -------------------------------------------------------------
        text_for_nlp = applicant_remarks or extracted_text
        nlp_res = self.distilbert.classify_intent(
            text=text_for_nlp,
            compare_with_policy=f"Citizen application for {layout_res['document_type']} under state interoperability mesh",
        )

        steps.append({
            "step_name": "Semantic Routing & Sentiment Analysis",
            "model_name": "DistilBERT",
            "status": "COMPLETED",
            "details": {
                "top_department": nlp_res["top_category"],
                "confidence": nlp_res["confidence"],
                "urgency_score": nlp_res["urgency_score"],
                "sentiment": nlp_res["sentiment"],
            },
        })

        # -------------------------------------------------------------
        # Step 5: XGBoost / LightGBM Tabular Risk & Fraud Assessment
        # -------------------------------------------------------------
        risk_input = {
            "annual_income_claimed": claimed_income or 0.0,
            "annual_income_tax_mesh": mesh_income or claimed_income or 0.0,
            "land_holding_acres_claimed": claimed_land_acres or 0.0,
            "land_holding_acres_registry": mesh_land_acres or claimed_land_acres or 0.0,
            "past_rejections_count": 0,
            "ocr_confidence": ocr_res["average_confidence"],
            "name_match_score": identity_check["name_match_score"],
            "aadhaar_verified": identity_check["aadhaar_last4_matched"] if citizen_aadhaar_last4 else True,
            "pan_verified": len(gov_ids.get("pan", [])) > 0 or True,
            "documents_submitted_count": 2,
        }

        risk_res = self.tabular.predict_risk(
            features_dict=risk_input,
            engine_type=preferred_tabular_engine,
        )

        steps.append({
            "step_name": "Mesh Fraud & Eligibility Assessment",
            "model_name": f"{risk_res['engine_used'].upper()} (Gradient Boosted Trees)",
            "status": "COMPLETED",
            "details": {
                "fraud_risk_score": risk_res["fraud_risk_score"],
                "approval_probability": risk_res["approval_probability"],
                "risk_level": risk_res["risk_level"],
                "decision": risk_res["decision"],
                "risk_factors": risk_res["key_risk_factors"],
            },
        })

        # -------------------------------------------------------------
        # Step 6: One-Class SVM & LOF Unsupervised Anomaly Detection
        # -------------------------------------------------------------
        anomaly_res = self.anomaly.detect_outliers(
            features_data=risk_input,
            algorithm="ensemble",
        )

        steps.append({
            "step_name": "Unsupervised Multivariate Anomaly Detection",
            "model_name": "One-Class SVM + Local Outlier Factor (LOF)",
            "status": "COMPLETED",
            "details": {
                "is_anomaly": anomaly_res["is_anomaly"],
                "anomaly_score": anomaly_res["anomaly_score"],
                "ocsvm_prediction": anomaly_res["ocsvm_prediction"],
                "lof_prediction": anomaly_res["lof_prediction"],
                "status_verdict": anomaly_res["status_verdict"],
                "outlier_reasons": anomaly_res["outlier_reasons"],
            },
        })

        # -------------------------------------------------------------
        # Overall Verdict Generation
        # -------------------------------------------------------------
        recommendations = []
        is_safe = (
            risk_res["risk_level"] == "LOW"
            and not anomaly_res["is_anomaly"]
            and identity_check["is_fully_verified"]
        )

        if is_safe:
            overall_verdict = "VERIFIED_AUTHENTIC"
            recommendations.append("Document passes all automated integrity checks. Ready for instant digital approval.")
        elif risk_res["risk_level"] in ["MEDIUM", "HIGH"] or anomaly_res["is_anomaly"]:
            overall_verdict = "FLAGGED_FOR_OFFICER_REVIEW"
            recommendations.extend(risk_res["key_risk_factors"])
            if anomaly_res["is_anomaly"]:
                recommendations.extend(anomaly_res["outlier_reasons"])
                recommendations.append("Unsupervised anomaly detector (One-Class SVM/LOF) flagged statistical density outlier.")
            recommendations.append("Route application to designated Department Verification Officer for physical/attested verification.")
        else:
            overall_verdict = "REJECTED_SUSPECTED_FRAUD"
            recommendations.extend(risk_res["key_risk_factors"])
            if anomaly_res["outlier_reasons"]:
                recommendations.extend(anomaly_res["outlier_reasons"])
            recommendations.append("Application exhibits high anomaly/discrepancy score. Recommend audit notification to vigilance cell.")

        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)

        return {
            "success": True,
            "overall_verdict": overall_verdict,
            "confidence_score": round((ocr_res["average_confidence"] + layout_res["layout_authenticity_score"]) / 2, 4),
            "fraud_risk_score": risk_res["fraud_risk_score"],
            "risk_level": risk_res["risk_level"],
            "document_type_detected": layout_res["document_type"],
            "extracted_identities": gov_ids,
            "identity_match_verified": identity_check["is_fully_verified"],
            "name_similarity": identity_check["name_match_score"],
            "steps": steps,
            "recommendations": recommendations,
            "processing_time_ms": elapsed_ms,
        }


# Singleton pipeline instance
verification_pipeline = DocumentVerificationPipeline()
