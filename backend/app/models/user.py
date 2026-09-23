from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import DateTime, Enum, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class UserRole(str, PyEnum):
    CITIZEN = "citizen"
    OFFICER = "officer"
    ADMIN = "admin"
    DEVELOPER = "developer"
    OPERATOR = "operator"
    AUDITOR = "auditor"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    full_name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    phone: Mapped[str | None] = mapped_column(String(15), unique=True, nullable=True)
    department: Mapped[str | None] = mapped_column(String(200), nullable=True)
    aadhaar_last4: Mapped[str | None] = mapped_column(String(4), nullable=True)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.CITIZEN)
    hashed_password: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    applications = relationship("ServiceApplication", back_populates="citizen")
    consents = relationship("DataShareConsent", back_populates="citizen")
    documents = relationship("Document", back_populates="owner")
