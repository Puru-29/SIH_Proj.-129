from __future__ import annotations

from app.connectors.base_connector import BaseConnector


class RevenueDemoProvider(BaseConnector):
    department = "Revenue & Land Records"
    system_name = "Revenue Certificate System"
    protocol = "REST"
    status = "connected"

    def get_record(self, citizen_id: str | int, record_type: str, purpose: str | None = None) -> dict:
        fallback_name = f"Citizen {citizen_id}"
        request_text = f"{record_type} {purpose or ''}".casefold()
        if any(term in request_text for term in ("land", "property", "survey")):
            resolved_type = "Land Record"
            details = {
                "survey_number": "SUR-2048-17",
                "land_parcel_id": "LAND-77421",
                "ownership_status": "Verified",
            }
        elif any(term in request_text for term in ("address", "residence", "domicile")):
            resolved_type = "Address Record"
            details = {
                "address": "Demo residential address, Pune, Maharashtra",
                "pin_code": "411001",
                "residency_status": "Verified",
            }
        else:
            resolved_type = "Income Certificate"
            details = {
                "income_certificate_no": "INC-92821",
                "certificate_no": "INC-92821",
                "annual_income": 240000,
                "income_category": "Eligible",
                "verification_status": "VERIFIED",
            }
        return {
            "full_name": f"{fallback_name}",
            "dob": "2003-05-10",
            **details,
            "record_type": resolved_type,
            "date_of_issue": "2026-09-05",
            "citizen_id": str(citizen_id),
            "department": self.department,
            "purpose": purpose or "Eligibility check",
        }

    def normalize(self, raw: dict, citizen_id: str | int) -> dict:
        record_type = raw.get("record_type") or "Government Record"
        identifier = (
            raw.get("income_certificate_no")
            or raw.get("land_parcel_id")
            or raw.get("survey_number")
            or raw.get("pin_code")
            or "REV-92821"
        )
        return {
            "citizenId": str(citizen_id),
            "name": raw.get("full_name") or f"Citizen {citizen_id}",
            "dateOfBirth": raw.get("dob") or "2003-05-10",
            "records": [
                {
                    "type": record_type,
                    "issuer": self.department,
                    "issuedDate": raw.get("date_of_issue") or "2026-09-05",
                    "verificationStatus": "VERIFIED",
                    "source": self.department,
                    "sourceType": "Demo Connected System",
                    "identifier": identifier,
                    "details": {
                        key: value for key, value in raw.items()
                        if key not in {"citizen_id", "full_name", "dob", "date_of_issue", "department", "purpose"}
                    },
                }
            ],
        }
