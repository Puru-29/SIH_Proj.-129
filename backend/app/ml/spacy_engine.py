import re
import time
import logging
from typing import Any

logger = logging.getLogger(__name__)

try:
    import spacy
    SPACY_AVAILABLE = True
except ImportError:
    SPACY_AVAILABLE = False

try:
    from rapidfuzz import fuzz
    RAPIDFUZZ_AVAILABLE = True
except ImportError:
    RAPIDFUZZ_AVAILABLE = False


class SpaCyNEREngine:
    """
    spaCy Named Entity Recognition Engine for Indian Government documents.
    Extracts structured identities (Aadhaar, PAN, Voter ID, IFSC), applicant names,
    dates of birth, addresses, and issuing departments.
    """

    # Government ID Regular Expression Patterns
    AADHAAR_PATTERN = re.compile(r"\b[2-9]{1}[0-9]{3}\s?[0-9]{4}\s?[0-9]{4}\b")
    PAN_PATTERN = re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]{1}\b")
    VOTER_PATTERN = re.compile(r"\b[A-Z]{3}[0-9]{7}\b")
    IFSC_PATTERN = re.compile(r"\b[A-Z]{4}0[A-Z0-9]{6}\b")
    RATION_PATTERN = re.compile(r"\b(?:RC\s?)?[0-9]{12}\b")
    DATE_PATTERN = re.compile(r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b")
    CONSENT_PURPOSE_KEYWORDS = {
        "identity": ["aadhaar", "identity", "kyc", "verify", "verification", "pan", "voter"],
        "financial": ["income", "bank", "account", "payment", "tax", "credit", "financial", "loan"],
        "health": ["health", "medical", "hospital", "diagnosis", "treatment", "patient", "medicine"],
        "welfare": ["benefit", "subsidy", "pension", "scholarship", "welfare", "ration", "eligibility"],
        "location": ["location", "address", "gps", "geolocation", "residence", "district"],
        "communications": ["email", "sms", "contact", "notification", "phone", "call"],
        "analytics": ["analytics", "research", "statistics", "improve", "insights", "model"],
    }

    def __init__(self, model_name: str = "en_core_web_sm"):
        self.model_name = model_name
        self._nlp: Any = None
        self._is_initialized = False

    @property
    def is_ready(self) -> bool:
        return SPACY_AVAILABLE

    def _load_spacy(self) -> Any:
        if not SPACY_AVAILABLE:
            return None

        if self._nlp is None:
            try:
                logger.info(f"Loading spaCy model: {self.model_name}")
                self._nlp = spacy.load(self.model_name)
                self._is_initialized = True
            except Exception as e:
                logger.warning(f"Could not load {self.model_name}: {e}. Creating blank English pipeline.")
                try:
                    self._nlp = spacy.blank("en")
                    self._is_initialized = True
                except Exception as blank_err:
                    logger.error(f"Failed to create blank spacy pipeline: {blank_err}")
                    self._nlp = None
        return self._nlp

    def extract_government_ids(self, text: str) -> dict[str, list[str]]:
        """Extracts Aadhaar, PAN, Voter ID, Ration Card, and IFSC using regex rules."""
        aadhaar_matches = [m.group(0).strip() for m in self.AADHAAR_PATTERN.finditer(text)]
        pan_matches = [m.group(0).strip() for m in self.PAN_PATTERN.finditer(text)]
        voter_matches = [m.group(0).strip() for m in self.VOTER_PATTERN.finditer(text)]
        ifsc_matches = [m.group(0).strip() for m in self.IFSC_PATTERN.finditer(text)]
        ration_matches = [m.group(0).strip() for m in self.RATION_PATTERN.finditer(text)]

        return {
            "aadhaar": list(set(aadhaar_matches)),
            "pan": list(set(pan_matches)),
            "voter_id": list(set(voter_matches)),
            "ration_card": list(set(ration_matches)),
            "ifsc": list(set(ifsc_matches)),
        }

    def extract_entities(self, text: str) -> dict[str, Any]:
        """
        Extracts both spaCy NLP entities (PERSON, ORG, GPE, DATE, MONEY)
        and Indian government specific identification numbers.
        """
        start_time = time.perf_counter()
        entities_list: list[dict[str, Any]] = []
        entity_counts: dict[str, int] = {}

        nlp = self._load_spacy()

        if nlp is not None and text.strip():
            doc = nlp(text)
            for ent in doc.ents:
                entities_list.append({
                    "text": ent.text.strip(),
                    "label": ent.label_,
                    "start": ent.start_char,
                    "end": ent.end_char,
                    "confidence": 0.95,
                })
                entity_counts[ent.label_] = entity_counts.get(ent.label_, 0) + 1

        # Fallback entity extraction if spaCy NER didn't find all key fields
        if not any(e["label"] == "PERSON" for e in entities_list):
            name_match = re.search(r"(?:Name|Applicant Name|Shri|Smt)[\s:]+([A-Za-z\s]+)", text, re.IGNORECASE)
            if name_match:
                extracted_name = name_match.group(1).split("\n")[0].strip()
                if extracted_name:
                    entities_list.append({
                        "text": extracted_name,
                        "label": "PERSON",
                        "start": name_match.start(1),
                        "end": name_match.end(1),
                        "confidence": 0.92,
                    })
                    entity_counts["PERSON"] = entity_counts.get("PERSON", 0) + 1

        # Fallback dates
        for d in self.DATE_PATTERN.finditer(text):
            date_str = d.group(0)
            if not any(e["text"] == date_str for e in entities_list):
                entities_list.append({
                    "text": date_str,
                    "label": "DATE",
                    "start": d.start(),
                    "end": d.end(),
                    "confidence": 0.95,
                })
                entity_counts["DATE"] = entity_counts.get("DATE", 0) + 1

        # Extract Government IDs
        gov_ids = self.extract_government_ids(text)
        for cat, ids in gov_ids.items():
            if ids:
                entity_counts[cat.upper()] = len(ids)

        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)

        return {
            "success": True,
            "entities": entities_list,
            "government_ids": gov_ids,
            "entity_counts": entity_counts,
            "processing_time_ms": elapsed_ms,
            "engine": "spacy",
        }

    def verify_citizen_profile(
        self,
        extracted_entities: list[dict[str, Any]],
        government_ids: dict[str, list[str]],
        citizen_full_name: str | None = None,
        citizen_aadhaar_last4: str | None = None,
    ) -> dict[str, Any]:
        """
        Cross-validates extracted document entities against the citizen's registered profile.
        """
        name_matched = False
        name_score = 0.0

        if citizen_full_name:
            # Check all PERSON entities extracted
            extracted_names = [e["text"] for e in extracted_entities if e.get("label") == "PERSON"]
            for ename in extracted_names:
                if RAPIDFUZZ_AVAILABLE:
                    score = fuzz.token_sort_ratio(ename.lower(), citizen_full_name.lower()) / 100.0
                else:
                    score = 1.0 if ename.lower() in citizen_full_name.lower() or citizen_full_name.lower() in ename.lower() else 0.5
                if score > name_score:
                    name_score = score
            name_matched = name_score >= 0.75

        aadhaar_matched = False
        if citizen_aadhaar_last4 and government_ids.get("aadhaar"):
            for a_num in government_ids["aadhaar"]:
                clean_num = a_num.replace(" ", "")
                if clean_num.endswith(citizen_aadhaar_last4):
                    aadhaar_matched = True
                    break

        return {
            "name_matched": name_matched,
            "name_match_score": round(name_score, 4),
            "aadhaar_last4_matched": aadhaar_matched,
            "is_fully_verified": (name_matched if citizen_full_name else True) and (aadhaar_matched if citizen_aadhaar_last4 else True),
        }

    def extract_consent_purpose(self, text: str) -> dict[str, Any]:
        """Extract entities and keyword-backed tags from a consent purpose statement."""
        start_time = time.perf_counter()
        entity_result = self.extract_entities(text)
        normalized_text = text.lower()
        purpose_tags: list[dict[str, Any]] = []

        for category, keywords in self.CONSENT_PURPOSE_KEYWORDS.items():
            matched_keywords = [keyword for keyword in keywords if keyword in normalized_text]
            if matched_keywords:
                purpose_tags.append({
                    "tag": category,
                    "confidence": round(min(0.99, 0.55 + len(matched_keywords) * 0.12), 4),
                    "matched_keywords": matched_keywords,
                })

        purpose_tags.sort(key=lambda item: item["confidence"], reverse=True)
        return {
            "success": True,
            "purpose_tags": purpose_tags,
            "entities": entity_result["entities"],
            "government_ids": entity_result["government_ids"],
            "processing_time_ms": round((time.perf_counter() - start_time) * 1000, 2),
            "engine": "spacy-consent-purpose",
        }


# Singleton instance
spacy_ner_engine = SpaCyNEREngine()
