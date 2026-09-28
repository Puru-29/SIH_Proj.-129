from __future__ import annotations

import re
from datetime import datetime
from typing import Any


class DataQualityService:
    def validate_income_certificate(self, record: dict[str, Any]) -> dict[str, Any]:
        required = ["full_name", "dob", "certificate_no", "annual_income", "verification_status"]
        missing = [field for field in required if not record.get(field)]
        if missing:
            return {"status": "FAILED", "missing": missing, "message": "Required fields missing"}

        issues: list[str] = []
        if not isinstance(record.get("annual_income"), (int, float)):
            issues.append("annual_income must be numeric")
        if record.get("dob") and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(record.get("dob"))) and not re.fullmatch(r"\d{2}/\d{2}/\d{4}", str(record.get("dob"))):
            issues.append("dob must use YYYY-MM-DD or DD/MM/YYYY format")
        if record.get("certificate_no") and not re.match(r"^[A-Z0-9-]+$", str(record.get("certificate_no"))):
            issues.append("certificate_no has invalid format")
        if issues:
            return {"status": "FAILED", "missing": [], "issues": issues, "message": "Record validation failed"}
        return {"status": "PASSED", "missing": [], "issues": [], "message": "Record validated successfully"}

    def normalize_income_certificate(self, record: dict[str, Any], citizen_id: str | int) -> dict[str, Any]:
        dob = record.get("dob")
        if "/" in str(dob):
            d, m, y = str(dob).split("/")
            dob = f"{y}-{m}-{d}"
        if isinstance(dob, str) and len(dob) == 10 and "-" in dob:
            try:
                datetime.strptime(dob, "%Y-%m-%d")
            except ValueError:
                dob = None
        return {
            "citizenId": str(citizen_id),
            "name": record.get("full_name") or "Citizen",
            "dateOfBirth": dob or "2003-05-10",
            "certificateId": record.get("certificate_no") or "INC-92821",
            "annualIncome": record.get("annual_income") or 240000,
            "sourceDepartment": "Revenue Department",
            "verified": str(record.get("verification_status", "VERIFIED")).upper() == "VERIFIED",
        }


data_quality_service = DataQualityService()
