from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr, field_validator
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User, UserRole
from app.models.department import Department
from app.schemas.user import UserCreate, UserRead
from app.core.security import hash_password, verify_password, create_access_token
from app.api.deps import require_authenticated_user

router = APIRouter(prefix="/auth", tags=["Authentication & Identity"])


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserRead


class LoginRequest(BaseModel):
    email: EmailStr
    password: str

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        if not 8 <= len(value) <= 16:
            raise ValueError("Password must be between 8 and 16 characters.")
        return value


@router.post("/signup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def signup(payload: UserCreate, db: Annotated[Session, Depends(get_db)]):
    """Register a new citizen or government user and return a JWT access token."""
    staff_roles = {
        UserRole.ADMIN,
        UserRole.OFFICER,
        UserRole.DEVELOPER,
        UserRole.OPERATOR,
        UserRole.AUDITOR,
    }
    platform_roles = staff_roles - {UserRole.OFFICER}

    if payload.role == UserRole.CITIZEN:
        if payload.department is not None:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Citizens cannot select a department.")
    elif payload.role in platform_roles:
        if payload.department != "GovFlow Platform":
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="This role must use GovFlow Platform.")
    elif payload.role == UserRole.OFFICER:
        if not payload.department or not db.query(Department).filter(Department.name == payload.department).first():
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Select one existing department for a Department Officer.")

    existing_user = db.query(User).filter(User.email == payload.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email already exists.",
        )

    if payload.phone:
        existing_phone = db.query(User).filter(User.phone == payload.phone).first()
        if existing_phone:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="An account with this phone number already exists.",
            )

    user = User(
        full_name=payload.full_name,
        email=payload.email,
        phone=payload.phone,
        department=payload.department,
        aadhaar_last4=payload.aadhaar_last4,
        role=payload.role,
        hashed_password=hash_password(payload.password),
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    access_token = create_access_token(
        data={"sub": str(user.id), "email": user.email, "role": user.role.value}
    )
    return TokenResponse(access_token=access_token, user=UserRead.model_validate(user))


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Annotated[Session, Depends(get_db)]):
    """Authenticate user with email and password and return a JWT access token."""
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated.",
        )

    access_token = create_access_token(
        data={"sub": str(user.id), "email": user.email, "role": user.role.value}
    )
    return TokenResponse(access_token=access_token, user=UserRead.model_validate(user))


@router.post("/oauth/token", response_model=TokenResponse)
def oauth_login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[Session, Depends(get_db)],
):
    """OAuth2 compatible token endpoint for swagger docs."""
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(
        data={"sub": str(user.id), "email": user.email, "role": user.role.value}
    )
    return TokenResponse(access_token=access_token, user=UserRead.model_validate(user))


@router.get("/me", response_model=UserRead)
def get_current_user_profile(
    current_user: Annotated[User, Depends(require_authenticated_user)],
):
    """Fetch profile of currently authenticated user."""
    return UserRead.model_validate(current_user)
