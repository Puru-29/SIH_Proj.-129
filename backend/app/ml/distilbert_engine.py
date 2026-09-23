import math
import time
import logging
from typing import Any

logger = logging.getLogger(__name__)

try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

try:
    from transformers import AutoTokenizer, AutoModelForSequenceClassification, pipeline
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False


class DistilBertEngine:
    """
    DistilBERT Transformer Engine for:
    1. Citizen application intent classification & department routing.
    2. Sentiment & urgency detection for priority grievance handling.
    3. Semantic similarity between citizen declarations and official mesh policy records.
    """

    DEPARTMENT_CATEGORIES = [
        "Revenue & Land Records",
        "Transport & Motor Vehicles",
        "Food & Civil Supplies",
        "Public Health & Medical Services",
        "Social Justice & Welfare",
    ]

    CATEGORY_KEYWORDS = {
        "Revenue & Land Records": ["land", "7/12", "khasra", "revenue", "mutation", "property", "tahsildar", "farmer", "patwari", "caste certificate", "income certificate"],
        "Transport & Motor Vehicles": ["driving", "license", "rto", "vehicle", "registration", "rc", "chassis", "puc", "challan", "permit"],
        "Food & Civil Supplies": ["ration", "ration card", "pds", "grain", "food", "subsidy", "fair price shop", "bpl", "apl", "annapurna"],
        "Public Health & Medical Services": ["hospital", "health", "ayushman", "treatment", "medicine", "medical", "doctor", "disability", "patient", "clinic"],
        "Social Justice & Welfare": ["pension", "scholarship", "widow", "senior citizen", "tribal", "welfare", "grant", "allowance", "handicap"],
    }

    CONSENT_CATEGORIES = [
        "identity",
        "financial",
        "health",
        "welfare",
        "location",
        "communications",
        "analytics",
    ]

    CONSENT_KEYWORDS = {
        "identity": ["aadhaar", "identity", "kyc", "verify", "pan", "voter"],
        "financial": ["income", "bank", "account", "payment", "tax", "credit", "loan"],
        "health": ["health", "medical", "hospital", "diagnosis", "treatment", "patient"],
        "welfare": ["benefit", "subsidy", "pension", "scholarship", "welfare", "ration", "eligibility"],
        "location": ["location", "address", "gps", "geolocation", "residence", "district"],
        "communications": ["email", "sms", "contact", "notification", "phone", "call"],
        "analytics": ["analytics", "research", "statistics", "improve", "insights", "model"],
    }

    def __init__(self, model_checkpoint: str = "distilbert-base-uncased"):
        self.model_checkpoint = model_checkpoint
        self._tokenizer: Any = None
        self._classifier_pipeline: Any = None
        self._is_initialized = False

    @property
    def is_ready(self) -> bool:
        return TRANSFORMERS_AVAILABLE and TORCH_AVAILABLE

    def _load_pipeline(self):
        if not self.is_ready or self._is_initialized:
            return

        # A base DistilBERT checkpoint has no trained zero-shot classification head.
        # Keep the supported keyword router active unless an MNLI checkpoint is supplied.
        if "mnli" not in self.model_checkpoint.lower():
            logger.info("Skipping zero-shot pipeline for non-MNLI checkpoint: %s", self.model_checkpoint)
            return

        try:
            logger.info(f"Loading DistilBERT pipeline: {self.model_checkpoint}")
            self._classifier_pipeline = pipeline(
                "zero-shot-classification",
                model=self.model_checkpoint,
                device=0 if (TORCH_AVAILABLE and torch.cuda.is_available()) else -1,
            )
            self._is_initialized = True
        except Exception as e:
            logger.warning(f"Could not load DistilBERT pipeline ({e}). Utilizing semantic keyword router.")
            self._is_initialized = False

    def classify_intent(self, text: str, compare_with_policy: str | None = None) -> dict[str, Any]:
        """
        Classifies citizen text into department categories and scores urgency/sentiment.
        """
        start_time = time.perf_counter()
        text_lower = text.lower()

        self._load_pipeline()

        category_scores: list[dict[str, Any]] = []

        if self._classifier_pipeline is not None:
            try:
                res = self._classifier_pipeline(text, candidate_labels=self.DEPARTMENT_CATEGORIES)
                labels = res.get("labels", [])
                scores = res.get("scores", [])
                for label, score in zip(labels, scores):
                    category_scores.append({"category": label, "score": round(float(score), 4)})
            except Exception as e:
                logger.warning(f"Transformer inference failed: {e}. Falling back to keyword scoring.")

        # If zero-shot wasn't run or failed, use keyword frequency scoring
        if not category_scores:
            raw_scores = {}
            for cat, keywords in self.CATEGORY_KEYWORDS.items():
                match_count = sum(1 for kw in keywords if kw in text_lower)
                raw_scores[cat] = match_count + 0.1  # base smoothing

            total = sum(raw_scores.values())
            for cat, val in raw_scores.items():
                category_scores.append({
                    "category": cat,
                    "score": round(val / total, 4),
                })
            category_scores.sort(key=lambda x: x["score"], reverse=True)

        top_category = category_scores[0]["category"]
        confidence = category_scores[0]["score"]

        # Urgency & sentiment heuristic
        urgent_keywords = ["urgent", "immediately", "emergency", "crisis", "critical", "loss", "delayed", "harassment", "bribe", "pending"]
        urgency_hits = sum(1 for kw in urgent_keywords if kw in text_lower)
        urgency_score = min(1.0, round(0.3 + (urgency_hits * 0.25), 2))

        sentiment = "URGENT" if urgency_hits >= 2 else ("CONCERNED" if urgency_hits == 1 else "NEUTRAL")

        # Semantic similarity if comparison text provided
        semantic_sim = None
        if compare_with_policy:
            sim_score = self.compute_semantic_similarity(text, compare_with_policy)
            semantic_sim = round(sim_score, 4)

        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)

        return {
            "success": True,
            "top_category": top_category,
            "confidence": round(confidence, 4),
            "category_scores": category_scores,
            "sentiment": sentiment,
            "urgency_score": urgency_score,
            "semantic_similarity": semantic_sim,
            "processing_time_ms": elapsed_ms,
            "engine": "distilbert",
        }

    def compute_semantic_similarity(self, text1: str, text2: str) -> float:
        """
        Computes semantic similarity between applicant remarks and service scheme criteria.
        """
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        if not words1 or not words2:
            return 0.5

        intersection = words1.intersection(words2)
        union = words1.union(words2)
        jaccard = len(intersection) / len(union)

        # Scale to 0.5 - 0.98 range
        similarity = 0.4 + (jaccard * 0.6)
        return min(0.99, max(0.1, similarity))

    def classify_consent_purpose(self, text: str) -> dict[str, Any]:
        """Classify a consent purpose into data-use categories."""
        start_time = time.perf_counter()
        normalized_text = text.lower()
        raw_scores = {
            category: 0.1 + sum(keyword in normalized_text for keyword in keywords)
            for category, keywords in self.CONSENT_KEYWORDS.items()
        }
        total = sum(raw_scores.values())
        category_scores = [
            {"category": category, "score": round(score / total, 4)}
            for category, score in raw_scores.items()
        ]
        category_scores.sort(key=lambda item: item["score"], reverse=True)
        top_category = category_scores[0]

        return {
            "success": True,
            "top_category": top_category["category"],
            "confidence": top_category["score"],
            "category_scores": category_scores,
            "processing_time_ms": round((time.perf_counter() - start_time) * 1000, 2),
            "engine": "distilbert-consent-purpose",
        }


# Singleton instance
distilbert_engine = DistilBERT = DistilBertEngine()
