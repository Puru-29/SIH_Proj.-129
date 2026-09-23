from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, field_validator

from app.models.user import UserRole


class UserCreate(BaseModel):
    full_name: str
    email: EmailStr
    phone: str | None = None
    department: str | None = None
    aadhaar_last4: str | None = None
    role: UserRole = UserRole.CITIZEN
    password: str

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, value: str) -> str:
        normalized = " ".join(value.split())
        if len(normalized) < 3 or not all(character.isalpha() or character in " .'-" for character in normalized):
            raise ValueError("Full name must contain letters and spaces only.")
        return normalized

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

    @field_validator("department")
    @classmethod
    def validate_department(cls, value: str | None) -> str | None:
        if value is not None:
            normalized = " ".join(value.split())
            if not normalized:
                raise ValueError("Department cannot be empty.")
            return normalized
        return value


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    email: EmailStr
    phone: str | None
    department: str | None
    aadhaar_last4: str | None
    role: UserRole
    is_active: bool
    created_at: datetime
