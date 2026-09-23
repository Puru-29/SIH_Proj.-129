import sys
from pathlib import Path

# Add backend directory to sys.path
backend_path = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_path))

from fastapi.testclient import TestClient
from app.main import app
from app.ml import (
    easyocr_engine,
    layoutlm_engine,
    spacy_ner_engine,
    distilbert_engine,
    tabular_risk_engine,
    anomaly_engine,
    verification_pipeline,
)


def test_easyocr_engine():
    print("Testing EasyOCR engine...")
    res = easyocr_engine.extract_text(
        raw_text_hint="GOVERNMENT OF INDIA\nUnique Identification Authority of India\nName: Aarav Patil\nDOB: 15/08/1992\nAadhaar Number: 5432 1098 4321"
    )
    assert res["success"] is True
    assert "Aarav Patil" in res["extracted_text"]
    assert len(res["words"]) > 0
    assert res["engine"] == "easyocr"
    print("[PASS] EasyOCR engine passed.")


def test_layoutlmv3_engine():
    print("Testing LayoutLMv3 engine...")
    res = layoutlm_engine.analyze_document(
        ocr_text="GOVERNMENT OF INDIA\nUnique Identification Authority of India\nAadhaar Number: 5432 1098 4321\nName: Aarav Patil"
    )
    assert res["success"] is True
    assert res["document_type"] == "Aadhaar Card"
    assert res["layout_authenticity_score"] > 0.7
    assert res["engine"] == "layoutlmv3"
    print("[PASS] LayoutLMv3 engine passed.")


def test_spacy_ner_engine():
    print("Testing spaCy NER engine...")
    text = (
        "Applicant Shri Rajesh Sharma, DOB: 12/04/1985. "
        "Aadhaar: 9876 5432 1024, PAN: ABCDE1234F, IFSC: SBIN0001234. "
        "Resident of Pune, Maharashtra."
    )
    res = spacy_ner_engine.extract_entities(text)
    assert res["success"] is True
    assert len(res["government_ids"]["aadhaar"]) >= 1
    assert "ABCDE1234F" in res["government_ids"]["pan"]
    assert "SBIN0001234" in res["government_ids"]["ifsc"]

    # Test profile verification
    ver_check = spacy_ner_engine.verify_citizen_profile(
        extracted_entities=res["entities"],
        government_ids=res["government_ids"],
        citizen_full_name="Rajesh Sharma",
        citizen_aadhaar_last4="1024",
    )
    assert ver_check["name_matched"] is True
    assert ver_check["aadhaar_last4_matched"] is True
    assert ver_check["is_fully_verified"] is True
    print("[PASS] spaCy NER engine passed.")


def test_distilbert_engine():
    print("Testing DistilBERT engine...")
    text = "Need urgent mutation of land 7/12 record and farmer income certificate from tahsildar office."
    res = distilbert_engine.classify_intent(
        text=text,
        compare_with_policy="Citizen application for land revenue services and mutation extract.",
    )
    assert res["success"] is True
    assert res["top_category"] == "Revenue & Land Records"
    assert res["urgency_score"] >= 0.5
    assert res["engine"] == "distilbert"
    print("[PASS] DistilBERT engine passed.")


def test_tabular_risk_engine():
    print("Testing XGBoost / LightGBM tabular risk engine...")
    # Safe low-risk profile
    safe_data = {
        "annual_income_claimed": 120000.0,
        "annual_income_tax_mesh": 125000.0,
        "land_holding_acres_claimed": 2.5,
        "land_holding_acres_registry": 2.5,
        "past_rejections_count": 0,
        "ocr_confidence": 0.98,
        "name_match_score": 1.0,
        "aadhaar_verified": True,
        "pan_verified": True,
    }
    xgb_res = tabular_risk_engine.predict_risk(safe_data, engine_type="xgboost")
    assert xgb_res["success"] is True
    assert xgb_res["risk_level"] == "LOW"
    assert xgb_res["decision"] == "AUTO_APPROVE"
    assert xgb_res["approval_probability"] > 0.8

    # Fraudulent profile
    fraud_data = {
        "annual_income_claimed": 30000.0,
        "annual_income_tax_mesh": 850000.0,  # Huge mismatch
        "land_holding_acres_claimed": 5.0,
        "land_holding_acres_registry": 0.5,
        "past_rejections_count": 3,
        "ocr_confidence": 0.60,
        "name_match_score": 0.40,
        "aadhaar_verified": False,
        "pan_verified": False,
    }
    lgb_res = tabular_risk_engine.predict_risk(fraud_data, engine_type="lightgbm")
    assert lgb_res["success"] is True
    assert lgb_res["fraud_risk_score"] > 0.5
    assert lgb_res["risk_level"] in ["HIGH", "CRITICAL"]
    assert len(lgb_res["key_risk_factors"]) >= 2
    print("[PASS] Tabular risk engine (XGBoost/LightGBM) passed.")


def test_pipeline_integration():
    print("Testing Unified Verification Pipeline...")
    res = verification_pipeline.verify_document(
        document_text=(
            "GOVERNMENT OF INDIA\n"
            "Unique Identification Authority of India\n"
            "Name: Aarav Patil\n"
            "DOB: 15/08/1992\n"
            "Aadhaar Number: 5432 1098 4321\n"
            "Address: Shivajinagar, Pune, Maharashtra"
        ),
        citizen_full_name="Aarav Patil",
        citizen_aadhaar_last4="4321",
        claimed_income=250000.0,
        mesh_income=250000.0,
        applicant_remarks="Applying for state revenue concession under verified income certificate",
        preferred_tabular_engine="xgboost",
    )
    assert res["success"] is True
    assert res["overall_verdict"] == "VERIFIED_AUTHENTIC"
    assert res["document_type_detected"] == "Aadhaar Card"
    assert len(res["steps"]) == 6  # All 6 stages executed (including One-Class SVM & LOF)!
    print("[PASS] Unified multi-model pipeline passed.")


def test_anomaly_detection_engine():
    print("Testing One-Class SVM & Local Outlier Factor (LOF) Anomaly Detection...")
    # 1. Normal inlier profile
    normal_profile = {
        "annual_income_claimed": 100000.0,
        "annual_income_tax_mesh": 105000.0,
        "land_holding_acres_claimed": 2.0,
        "land_holding_acres_registry": 2.0,
        "ocr_confidence": 0.95,
        "name_match_score": 1.0,
        "past_rejections_count": 0,
    }

    ocsvm_res = anomaly_engine.detect_outliers(normal_profile, algorithm="one_class_svm")
    assert ocsvm_res["success"] is True
    assert ocsvm_res["algorithm_used"] == "one_class_svm"
    assert "ocsvm_prediction" in ocsvm_res

    lof_res = anomaly_engine.detect_outliers(normal_profile, algorithm="lof")
    assert lof_res["success"] is True
    assert lof_res["algorithm_used"] == "lof"
    assert "lof_prediction" in lof_res

    # 2. Severe outlier / anomalous profile
    outlier_profile = {
        "annual_income_claimed": 20000.0,
        "annual_income_tax_mesh": 1200000.0,  # 60x difference
        "land_holding_acres_claimed": 10.0,
        "land_holding_acres_registry": 0.5,
        "ocr_confidence": 0.55,
        "name_match_score": 0.35,
        "past_rejections_count": 4,
    }
    ens_res = anomaly_engine.detect_outliers(outlier_profile, algorithm="ensemble")
    assert ens_res["success"] is True
    assert ens_res["is_anomaly"] is True
    assert ens_res["status_verdict"] in ["SUSPICIOUS_OUTLIER", "HIGH_RISK_ANOMALY"]
    assert len(ens_res["outlier_reasons"]) >= 2
    print("[PASS] One-Class SVM & Local Outlier Factor (LOF) engine passed.")


def test_fastapi_endpoints():
    print("Testing FastAPI API Endpoints...")
    client = TestClient(app)

    # Health check
    h_res = client.get("/health")
    assert h_res.status_code == 200

    # System ML status
    s_res = client.get("/api/v1/ml/status")
    assert s_res.status_code == 200
    s_data = s_res.json()
    assert s_data["status"] == "healthy"
    assert "easyocr" in s_data["engines"]
    assert "layoutlmv3" in s_data["engines"]
    assert "spacy_ner" in s_data["engines"]
    assert "distilbert" in s_data["engines"]
    assert "xgboost_lightgbm" in s_data["engines"]
    assert "one_class_svm_lof" in s_data["engines"]

    # NER endpoint
    ner_res = client.post("/api/v1/ml/ner/spacy", json={"text": "Applicant Aarav Patil, Aadhaar 5432 1098 4321, PAN ABCDE1234F"})
    assert ner_res.status_code == 200
    assert len(ner_res.json()["government_ids"]["aadhaar"]) >= 1

    # DistilBERT endpoint
    bert_res = client.post("/api/v1/ml/classify/distilbert", json={"text": "Applying for new driving license and RTO vehicle registration"})
    assert bert_res.status_code == 200
    assert bert_res.json()["top_category"] == "Transport & Motor Vehicles"

    # Risk Assessment endpoint (XGBoost)
    risk_res = client.post("/api/v1/ml/risk-assessment?engine=xgboost", json={
        "annual_income_claimed": 100000.0,
        "annual_income_tax_mesh": 100000.0,
        "ocr_confidence": 0.95,
        "name_match_score": 1.0,
        "aadhaar_verified": True,
        "pan_verified": True,
    })
    assert risk_res.status_code == 200
    assert risk_res.json()["decision"] == "AUTO_APPROVE"

    # Anomaly Detection endpoint (One-Class SVM & LOF)
    anom_res = client.post("/api/v1/ml/anomaly-detection", json={
        "annual_income_claimed": 25000.0,
        "annual_income_tax_mesh": 900000.0,
        "land_holding_acres_claimed": 8.0,
        "land_holding_acres_registry": 0.5,
        "ocr_confidence": 0.60,
        "name_match_score": 0.45,
        "past_rejections_count": 3,
        "algorithm": "ensemble",
    })
    assert anom_res.status_code == 200
    anom_data = anom_res.json()
    assert anom_data["success"] is True
    assert anom_data["is_anomaly"] is True

    # Full Verification endpoint
    full_res = client.post("/api/v1/ml/verify-document", json={
        "document_text": "GOVERNMENT OF INDIA\nAadhaar: 5432 1098 4321\nName: Aarav Patil",
        "citizen_full_name": "Aarav Patil",
        "citizen_aadhaar_last4": "4321",
        "claimed_income": 100000.0,
        "mesh_income": 100000.0,
        "preferred_tabular_engine": "xgboost",
    })
    assert full_res.status_code == 200
    assert full_res.json()["overall_verdict"] == "VERIFIED_AUTHENTIC"
    assert len(full_res.json()["steps"]) == 6
    print("[PASS] All FastAPI endpoints passed.")


if __name__ == "__main__":
    test_easyocr_engine()
    test_layoutlmv3_engine()
    test_spacy_ner_engine()
    test_distilbert_engine()
    test_tabular_risk_engine()
    test_anomaly_detection_engine()
    test_pipeline_integration()
    test_fastapi_endpoints()
    print("\n>>> ALL 8 TEST SUITES PASSED SUCCESSFULLY! <<<")
