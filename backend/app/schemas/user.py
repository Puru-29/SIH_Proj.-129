from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, field_validator, model_validator

from app.models.user import UserRole


class UserCreate(BaseModel):
    full_name: str
    email: EmailStr
    phone: str | None = None
    aadhaar_last4: str | None = None
    password: str

    model_config = ConfigDict(extra="forbid")

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, value: str) -> str:
        normalized = " ".join(value.split())
        if len(normalized) < 3 or not all(character.isalpha() or character in " .'-" for character in normalized):
            raise ValueError("Full name must contain letters and spaces only.")
        return normalized

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> str:
        return str(value).lower()

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: str | None) -> str | None:
        if value is not None and (not value.isdigit() or len(value) != 10 or value[0] not in "6789"):
            raise ValueError("Mobile number must be a valid 10-digit Indian number.")
        return value

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        if not 8 <= len(value) <= 16:
            raise ValueError("Password must be between 8 and 16 characters.")
        return value

class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    email: EmailStr
    phone: str | None
    department: str | None
    aadhaar_last4: str | None
    role: str
    is_active: bool
    created_at: datetime

    @model_validator(mode="before")
    @classmethod
    def canonical_role(cls, value):
        role_map = {
            UserRole.CITIZEN: "citizen",
            UserRole.OFFICER: "department_officer",
            UserRole.ADMIN: "system_admin",
            UserRole.DEVELOPER: "interoperability_admin",
            UserRole.OPERATOR: "interoperability_admin",
            UserRole.AUDITOR: "auditor",
        }
        role_record = getattr(value, "role_record", None)
        if hasattr(value, "role"):
            return {
                "id": value.id,
                "full_name": value.full_name,
                "email": value.email,
                "phone": value.phone,
                "department": value.department,
                "aadhaar_last4": value.aadhaar_last4,
                "role": role_record.key if role_record is not None else role_map[value.role],
                "is_active": value.is_active,
                "created_at": value.created_at,
            }
        if isinstance(value, dict):
            value = value.copy()
            role = value.get("role")
            if isinstance(role, UserRole):
                value["role"] = role_map[role]
        return value
