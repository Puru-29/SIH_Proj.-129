from pydantic import BaseModel, Field
from typing import Any


# ==========================================
# 1. EasyOCR Schemas
# ==========================================

class OCRWord(BaseModel):
    text: str
    confidence: float
    bbox: list[list[float]] = Field(default_factory=list, description="4 coordinates [[x1,y1],[x2,y1],[x2,y2],[x1,y2]]")
    normalized_bbox: list[int] = Field(default_factory=list, description="[x1, y1, x2, y2] scaled 0-1000")


class OCRRequest(BaseModel):
    image_base64: str | None = Field(default=None, description="Base64 encoded document image")
    image_url: str | None = Field(default=None, description="Direct URL to document image")
    file_path: str | None = Field(default=None, description="Local file path to document")
    languages: list[str] = Field(default_factory=lambda: ["en", "hi"], description="List of OCR languages (e.g. ['en', 'hi', 'mr'])")


class OCRResponse(BaseModel):
    success: bool
    extracted_text: str
    words: list[OCRWord] = Field(default_factory=list)
    word_count: int = 0
    average_confidence: float = 0.0
    processing_time_ms: float = 0.0
    engine: str = "easyocr"


# ==========================================
# 2. LayoutLMv3 Schemas
# ==========================================

class LayoutField(BaseModel):
    label: str
    text: str
    confidence: float
    bbox: list[int] = Field(default_factory=lambda: [0, 0, 0, 0])


class LayoutLMRequest(BaseModel):
    image_base64: str | None = None
    ocr_text: str | None = None
    normalized_boxes: list[list[int]] | None = None
    doc_type_hint: str | None = None


class LayoutLMResponse(BaseModel):
    success: bool
    document_type: str
    type_confidence: float
    layout_authenticity_score: float
    fields: list[LayoutField] = Field(default_factory=list)
    is_tampered_or_anomalous: bool = False
    processing_time_ms: float = 0.0
    engine: str = "layoutlmv3"


# ==========================================
# 3. spaCy NER Schemas
# ==========================================

class ExtractedEntity(BaseModel):
    text: str
    label: str
    start: int
    end: int
    confidence: float = 1.0


class GovernmentIDs(BaseModel):
    aadhaar: list[str] = Field(default_factory=list)
    pan: list[str] = Field(default_factory=list)
    voter_id: list[str] = Field(default_factory=list)
    ration_card: list[str] = Field(default_factory=list)
    ifsc: list[str] = Field(default_factory=list)


class NERRequest(BaseModel):
    text: str = Field(..., description="Document text or citizen application text to extract entities from")


class NERResponse(BaseModel):
    success: bool
    entities: list[ExtractedEntity] = Field(default_factory=list)
    government_ids: GovernmentIDs = Field(default_factory=GovernmentIDs)
    entity_counts: dict[str, int] = Field(default_factory=dict)
    processing_time_ms: float = 0.0
    engine: str = "spacy"


class ConsentPurposeRequest(BaseModel):
    text: str = Field(..., description="Consent purpose text to tag and classify")


class ConsentPurposeTag(BaseModel):
    tag: str
    confidence: float
    matched_keywords: list[str] = Field(default_factory=list)


class ConsentPurposeResponse(BaseModel):
    success: bool
    purpose_tags: list[ConsentPurposeTag] = Field(default_factory=list)
    entities: list[ExtractedEntity] = Field(default_factory=list)
    government_ids: GovernmentIDs = Field(default_factory=GovernmentIDs)
    classification: "DistilBertClassifyResponse"
    processing_time_ms: float = 0.0
    engine: str = "spacy+distilbert-consent-purpose"


# ==========================================
# 4. DistilBERT Schemas
# ==========================================

class CategoryScore(BaseModel):
    category: str
    score: float


class DistilBertClassifyRequest(BaseModel):
    text: str = Field(..., description="Text content or remarks from citizen application")
    compare_with_policy: str | None = Field(default=None, description="Optional policy or scheme description to check semantic match")


class DistilBertClassifyResponse(BaseModel):
    success: bool
    top_category: str
    confidence: float
    category_scores: list[CategoryScore] = Field(default_factory=list)
    sentiment: str = "NEUTRAL"
    urgency_score: float = 0.5
    semantic_similarity: float | None = None
    processing_time_ms: float = 0.0
    engine: str = "distilbert"


# ==========================================
# 5. XGBoost / LightGBM Schemas
# ==========================================

class RiskAssessmentRequest(BaseModel):
    annual_income_claimed: float = Field(default=0.0, description="Claimed annual income in INR")
    annual_income_tax_mesh: float = Field(default=0.0, description="Income record from Tax/Revenue database mesh")
    land_holding_acres_claimed: float = Field(default=0.0, description="Claimed land holding in acres")
    land_holding_acres_registry: float = Field(default=0.0, description="Land holding from Land Registry 7/12 mesh")
    past_rejections_count: int = Field(default=0, description="Previous application rejection count")
    ocr_confidence: float = Field(default=0.95, description="Average OCR detection confidence")
    name_match_score: float = Field(default=1.0, description="Similarity between Aadhaar/ID name and citizen profile")
    aadhaar_verified: bool = Field(default=True, description="Whether Aadhaar last 4 or full ID was matched")
    pan_verified: bool = Field(default=True, description="Whether PAN format & record was matched")
    documents_submitted_count: int = Field(default=2, description="Total documents attached")
    engine: str = Field(default="xgboost", description="Either 'xgboost' or 'lightgbm'")


class RiskAssessmentResponse(BaseModel):
    success: bool
    engine_used: str
    fraud_risk_score: float = Field(..., description="Calculated fraud risk (0.0=safe, 1.0=critical fraud)")
    approval_probability: float = Field(..., description="Predicted likelihood of legitimate approval (0.0 to 1.0)")
    risk_level: str = Field(..., description="LOW | MEDIUM | HIGH | CRITICAL")
    decision: str = Field(..., description="AUTO_APPROVE | OFFICER_REVIEW | REJECT | FLAGGED_FOR_AUDIT")
    key_risk_factors: list[str] = Field(default_factory=list)
    feature_importance: dict[str, float] = Field(default_factory=dict)
    processing_time_ms: float = 0.0


# ==========================================
# 6. Unified Verification Pipeline Schemas
# ==========================================

class FullVerificationRequest(BaseModel):
    citizen_id: int | None = None
    service_id: int | None = None
    application_reference: str | None = None
    image_base64: str | None = None
    document_text: str | None = None
    citizen_full_name: str | None = None
    citizen_aadhaar_last4: str | None = None
    claimed_income: float | None = None
    mesh_income: float | None = None
    claimed_land_acres: float | None = None
    mesh_land_acres: float | None = None
    applicant_remarks: str | None = None
    preferred_tabular_engine: str = Field(default="xgboost", description="Choice of 'xgboost' or 'lightgbm'")


class PipelineStepSummary(BaseModel):
    step_name: str
    model_name: str
    status: str
    details: dict[str, Any] = Field(default_factory=dict)


class FullVerificationResponse(BaseModel):
    success: bool
    overall_verdict: str
    confidence_score: float
    fraud_risk_score: float
    risk_level: str
    document_type_detected: str
    extracted_identities: GovernmentIDs = Field(default_factory=GovernmentIDs)
    identity_match_verified: bool = False
    name_similarity: float = 0.0
    steps: list[PipelineStepSummary] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    processing_time_ms: float = 0.0


# ==========================================
# 7. Model Status & Health Schemas
# ==========================================

class EngineStatusItem(BaseModel):
    name: str
    type: str
    ready: bool
    device: str = "cpu"
    version: str = "1.0.0"
    mode: str = "active"


class MLSystemStatusResponse(BaseModel):
    status: str
    total_engines: int
    ready_count: int
    engines: dict[str, EngineStatusItem]


# ==========================================
# 8. One-Class SVM & LOF Anomaly Detection
# ==========================================

class AnomalyDetectionRequest(BaseModel):
    annual_income_claimed: float = Field(default=100000.0, description="Claimed annual income in INR")
    annual_income_tax_mesh: float = Field(default=100000.0, description="Income from tax mesh in INR")
    land_holding_acres_claimed: float = Field(default=2.0, description="Claimed land holding in acres")
    land_holding_acres_registry: float = Field(default=2.0, description="Land holding from 7/12 registry in acres")
    ocr_confidence: float = Field(default=0.95, description="Document OCR extraction confidence")
    name_match_score: float = Field(default=1.0, description="Name match similarity with citizen registry")
    past_rejections_count: int = Field(default=0, description="Number of past rejected applications")
    algorithm: str = Field(default="ensemble", description="Choice of 'one_class_svm', 'lof', or 'ensemble'")


class AnomalyDetectionResponse(BaseModel):
    success: bool
    algorithm_used: str
    is_anomaly: bool
    anomaly_score: float = Field(..., description="Normalized anomaly probability (0.0=normal, 1.0=severe outlier)")
    ocsvm_prediction: str = Field(..., description="One-Class SVM verdict: INLIER | OUTLIER")
    ocsvm_distance: float
    lof_prediction: str = Field(..., description="Local Outlier Factor verdict: INLIER | OUTLIER")
    lof_score: float = Field(..., description="LOF density ratio score (>1.5 indicates local outlier)")
    status_verdict: str = Field(..., description="NORMAL_INLIER | SUSPICIOUS_OUTLIER | HIGH_RISK_ANOMALY")
    outlier_reasons: list[str] = Field(default_factory=list)
    processing_time_ms: float = 0.0
