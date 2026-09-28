from __future__ import annotations

from app.connectors.base_connector import BaseConnector


class TransportDemoProvider(BaseConnector):
    department = "Transport & Motor Vehicles"
    system_name = "Sarathi RTO Services"
    protocol = "REST"
    status = "connected"

    def get_record(self, citizen_id: str | int, record_type: str, purpose: str | None = None) -> dict:
        return {
            "citizen_id": str(citizen_id),
            "license_number": "MH-12-2026-009821",
            "vehicle_class": "LMV",
            "license_status": "Valid",
            "record_type": "Driving Licence",
            "purpose": purpose or record_type,
            "date_of_issue": "2026-01-18",
        }

    def normalize(self, raw: dict, citizen_id: str | int) -> dict:
        return {
            "citizenId": str(citizen_id),
            "records": [
                {
                    "type": raw.get("record_type", "Driving Licence"),
                    "issuer": self.department,
                    "issuedDate": raw.get("date_of_issue"),
                    "verificationStatus": raw.get("license_status", "Verified").upper(),
                    "source": self.department,
                    "sourceType": "Demo Connected System",
                    "identifier": raw.get("license_number"),
                    "details": {
                        "vehicleClass": raw.get("vehicle_class"),
                        "licenseStatus": raw.get("license_status"),
                    },
                }
            ],
        }
