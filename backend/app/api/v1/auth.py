from datetime import datetime, timedelta, timezone
import hmac
from typing import Annotated, Literal
from uuid import UUID, uuid4

from fastapi import (
    APIRouter,
    Cookie,
    Depends,
    HTTPException,
    Query,
    Request,
    Response,
    status,
)
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_current_user, get_user_role_key, oauth2_scheme, require_role
from app.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_access_token,
    hash_password,
    hash_token,
    verify_password,
)
from app.database import get_db
from app.models.auth_session import AuthSession
from app.models.department import Department
from app.models.role import Role
from app.models.user import User, UserRole
from app.schemas.user import UserCreate, UserRead
from app.services.audit_service import record_audit

router = APIRouter(prefix="/auth", tags=["Authentication & Identity"])
REFRESH_COOKIE_NAME = "govflow_refresh_token"
REFRESH_COOKIE_PATH = "/api/v1/auth"


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserRead


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class ManagedUserCreate(UserCreate):
    role: Literal[
        "citizen",
        "department_officer",
        "interoperability_admin",
        "system_admin",
    ]
    department_id: int | None = None


class StaffAccountRequest(UserCreate):
    role: Literal["department_officer", "interoperability_admin"]
    department_id: int | None = None


class StaffAccountRequestResponse(BaseModel):
    message: str


class ManagedUserUpdate(BaseModel):
    role: Literal[
        "citizen",
        "department_officer",
        "interoperability_admin",
        "system_admin",
    ] | None = None
    department_id: int | None = None
    is_active: bool | None = None


def _set_refresh_cookie(response: Response, refresh_token: str) -> None:
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=refresh_token,
        max_age=settings.refresh_token_expire_days * 24 * 60 * 60,
        httponly=True,
        secure=(
            settings.auth_cookie_secure
            if settings.auth_cookie_secure is not None
            else not settings.debug
        ),
        samesite=settings.auth_cookie_samesite,
        path=REFRESH_COOKIE_PATH,
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(
        key=REFRESH_COOKIE_NAME,
        path=REFRESH_COOKIE_PATH,
        secure=(
            settings.auth_cookie_secure
            if settings.auth_cookie_secure is not None
            else not settings.debug
        ),
        httponly=True,
        samesite=settings.auth_cookie_samesite,
    )


def _validate_browser_origin(request: Request) -> None:
    origin = request.headers.get("origin")
    if origin and origin not in settings.cors_origins:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This origin is not allowed to use authentication cookies.",
        )


def _role_record(db: Session, role_key: str) -> Role:
    role = db.query(Role).filter(Role.key == role_key).one_or_none()
    if role is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Role registry is not initialized; apply the database migrations.",
        )
    return role


def _legacy_role(role_key: str) -> UserRole:
    return {
        "citizen": UserRole.CITIZEN,
        "department_officer": UserRole.OFFICER,
        "interoperability_admin": UserRole.OPERATOR,
        "system_admin": UserRole.ADMIN,
    }[role_key]


def _check_department(
    db: Session, role_key: str, department_id: int | None
) -> Department | None:
    if role_key == "department_officer":
        if department_id is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="A department officer must be assigned to a department.",
            )
    elif department_id is not None and role_key == "citizen":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Citizens cannot be assigned to a department.",
        )
    if department_id is None:
        return None
    department = db.query(Department).filter(Department.id == department_id).first()
    if department is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Select an existing department.",
        )
    return department


def _create_auth_session(
    user: User, db: Session, *, audit_action: str = "LOGIN"
) -> tuple[str, str]:
    now = datetime.now(timezone.utc)
    session_id = uuid4()
    role_key = get_user_role_key(user)
    claims = {
        "sub": str(user.id),
        "email": user.email,
        "role": role_key,
        "sid": str(session_id),
    }
    access_token = create_access_token(claims)
    refresh_token = create_refresh_token(claims)
    db.add(
        AuthSession(
            id=session_id,
            user_id=user.id,
            refresh_token_hash=hash_token(refresh_token),
            expires_at=now + timedelta(days=settings.refresh_token_expire_days),
        )
    )
    record_audit(
        db,
        action=audit_action,
        actor_id=user.id,
        actor_role=get_user_role_key(user),
        role_id=user.role_id,
        department_id=user.department_id,
        resource_type="auth_session",
        resource_id=str(session_id),
        metadata={"session_id": str(session_id)},
    )
    db.commit()
    return access_token, refresh_token


def _token_response(user: User, access_token: str) -> TokenResponse:
    return TokenResponse(
        access_token=access_token,
        expires_in=settings.access_token_expire_minutes * 60,
        user=UserRead.model_validate(user),
    )


def _authenticate(db: Session, email: str, password: str) -> User:
    user = (
        db.query(User)
        .options(joinedload(User.role_record))
        .filter(User.email == email.strip().lower())
        .first()
    )
    if user is None or not verify_password(password, user.hashed_password):
        attempt_id = uuid4()
        record_audit(
            db,
            action="LOGIN",
            actor_id=user.id if user else None,
            actor_role=get_user_role_key(user) if user else None,
            role_id=user.role_id if user else None,
            department_id=user.department_id if user else None,
            resource_type="auth_session",
            resource_id=str(attempt_id),
            result="failure",
            metadata={"attempt_id": str(attempt_id), "reason": "invalid_credentials"},
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        attempt_id = uuid4()
        record_audit(
            db,
            action="LOGIN",
            actor_id=user.id,
            actor_role=get_user_role_key(user),
            role_id=user.role_id,
            department_id=user.department_id,
            resource_type="auth_session",
            resource_id=str(attempt_id),
            result="failure",
            metadata={"attempt_id": str(attempt_id), "reason": "account_deactivated"},
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated.",
        )
    return user


def _start_session(
    user: User,
    db: Session,
    response: Response,
    *,
    audit_action: str = "LOGIN",
) -> TokenResponse:
    access_token, refresh_token = _create_auth_session(
        user, db, audit_action=audit_action
    )
    _set_refresh_cookie(response, refresh_token)
    return _token_response(user, access_token)


@router.post(
    "/staff-requests",
    response_model=StaffAccountRequestResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def request_staff_account(
    payload: StaffAccountRequest,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
):
    _validate_browser_origin(request)
    department = _check_department(db, payload.role, payload.department_id)
    message = "Your staff account request was received. A system administrator must approve it."

    if db.query(User).filter(User.email == payload.email).first():
        return {"message": message}
    if payload.phone and db.query(User).filter(User.phone == payload.phone).first():
        return {"message": message}

    user = User(
        full_name=payload.full_name,
        email=payload.email,
        phone=payload.phone,
        role=_legacy_role(payload.role),
        role_id=_role_record(db, payload.role).id,
        department=department.name if department else None,
        department_id=department.id if department else None,
        hashed_password=hash_password(payload.password),
        is_active=False,
        staff_request_pending=True,
    )
    db.add(user)
    db.flush()
    record_audit(
        db,
        action="STAFF_ACCOUNT_REQUESTED",
        resource_type="user",
        resource_id=user.id,
        result="pending",
        metadata={"role": payload.role, "department_id": user.department_id},
    )
    db.commit()
    return {"message": message}


@router.post("/signup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def signup(
    payload: UserCreate,
    request: Request,
    response: Response,
    db: Annotated[Session, Depends(get_db)],
):
    """Register a citizen account; privileged accounts are provisioned by system admins."""
    _validate_browser_origin(request)
    if db.query(User).filter(User.email == payload.email.lower()).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )
    if payload.phone and db.query(User).filter(User.phone == payload.phone).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this phone number already exists.",
        )

    user = User(
        full_name=payload.full_name,
        email=payload.email.lower(),
        phone=payload.phone,
        aadhaar_last4=payload.aadhaar_last4,
        role=UserRole.CITIZEN,
        role_id=_role_record(db, "citizen").id,
        hashed_password=hash_password(payload.password),
        is_active=True,
    )
    db.add(user)
    db.flush()
    db.refresh(user)
    return _start_session(user, db, response, audit_action="ACCOUNT_REGISTERED")


@router.post("/login", response_model=TokenResponse)
def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: Annotated[Session, Depends(get_db)],
):
    _validate_browser_origin(request)
    user = _authenticate(db, payload.email, payload.password)
    return _start_session(user, db, response)


@router.post("/oauth/token", response_model=TokenResponse)
def oauth_login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    request: Request,
    response: Response,
    db: Annotated[Session, Depends(get_db)],
):
    _validate_browser_origin(request)
    user = _authenticate(db, form_data.username, form_data.password)
    return _start_session(user, db, response)


@router.post("/refresh", response_model=TokenResponse)
def refresh(
    request: Request,
    response: Response,
    db: Annotated[Session, Depends(get_db)],
    refresh_token: Annotated[str | None, Cookie(alias=REFRESH_COOKIE_NAME)] = None,
):
    _validate_browser_origin(request)
    invalid = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Refresh session is invalid or expired.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    claims = decode_access_token(refresh_token) if refresh_token else None
    if (
        refresh_token is None
        or not claims
        or claims.get("type") != "refresh"
    ):
        raise invalid
    try:
        session_id = UUID(claims["sid"])
        user_id = int(claims["sub"])
    except (KeyError, TypeError, ValueError):
        raise invalid from None

    auth_session = db.query(AuthSession).filter(AuthSession.id == session_id).first()
    now = datetime.now(timezone.utc)
    if (
        auth_session is None
        or auth_session.user_id != user_id
        or auth_session.revoked_at is not None
        or (
            auth_session.expires_at.replace(tzinfo=timezone.utc)
            if auth_session.expires_at.tzinfo is None
            else auth_session.expires_at
        )
        <= now
    ):
        raise invalid
    if not hmac.compare_digest(
        auth_session.refresh_token_hash, hash_token(refresh_token)
    ):
        auth_session.revoked_at = now
        db.commit()
        _clear_refresh_cookie(response)
        raise invalid

    user = (
        db.query(User)
        .options(joinedload(User.role_record))
        .filter(User.id == user_id)
        .first()
    )
    if user is None or not user.is_active:
        auth_session.revoked_at = now
        db.commit()
        _clear_refresh_cookie(response)
        raise invalid

    access_token, rotated_refresh_token = _create_rotated_tokens(
        user, session_id, auth_session, db
    )
    _set_refresh_cookie(response, rotated_refresh_token)
    return _token_response(user, access_token)


def _create_rotated_tokens(
    user: User,
    session_id: UUID,
    auth_session: AuthSession,
    db: Session,
) -> tuple[str, str]:
    now = datetime.now(timezone.utc)
    claims = {
        "sub": str(user.id),
        "email": user.email,
        "role": get_user_role_key(user),
        "sid": str(session_id),
    }
    access_token = create_access_token(claims)
    refresh_token = create_refresh_token(claims)
    auth_session.refresh_token_hash = hash_token(refresh_token)
    auth_session.last_used_at = now
    auth_session.expires_at = now + timedelta(days=settings.refresh_token_expire_days)
    record_audit(
        db,
        action="TOKEN_REFRESHED",
        resource_type="auth_session",
        resource_id=session_id,
        actor_id=user.id,
        actor_role=get_user_role_key(user),
        role_id=user.role_id,
        department_id=user.department_id,
        metadata={"session_id": str(session_id)},
    )
    db.commit()
    return access_token, refresh_token


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    request: Request,
    response: Response,
    db: Annotated[Session, Depends(get_db)],
    access_token: Annotated[str | None, Depends(oauth2_scheme)],
    refresh_token: Annotated[str | None, Cookie(alias=REFRESH_COOKIE_NAME)] = None,
):
    _validate_browser_origin(request)
    now = datetime.now(timezone.utc)
    claims = decode_access_token(access_token) if access_token else None
    refresh_claims = decode_access_token(refresh_token) if refresh_token else None
    session_id: UUID | None = None
    user_id: int | None = None
    if claims and claims.get("type") == "access":
        try:
            session_id = UUID(claims["sid"])
            user_id = int(claims["sub"])
        except (KeyError, TypeError, ValueError):
            session_id = None
    if session_id is None and refresh_claims and refresh_claims.get("type") == "refresh":
        try:
            session_id = UUID(refresh_claims["sid"])
            user_id = int(refresh_claims["sub"])
        except (KeyError, TypeError, ValueError):
            session_id = None

    if session_id is not None and user_id is not None:
        auth_session = (
            db.query(AuthSession)
            .filter(AuthSession.id == session_id, AuthSession.user_id == user_id)
            .first()
        )
        if (
            auth_session is not None
            and auth_session.revoked_at is None
            and (
                not refresh_token
                or (claims is not None and claims.get("type") == "access")
                or (
                    refresh_claims is not None
                    and hmac.compare_digest(
                        auth_session.refresh_token_hash, hash_token(refresh_token)
                    )
                )
            )
        ):
            auth_session.revoked_at = now
            user = (
                db.query(User)
                .options(joinedload(User.role_record))
                .filter(User.id == user_id)
                .first()
            )
            record_audit(
                db,
                action="LOGOUT",
                resource_type="auth_session",
                resource_id=session_id,
                actor_id=user_id,
                actor_role=get_user_role_key(user) if user else None,
                role_id=user.role_id if user else None,
                department_id=user.department_id if user else None,
                metadata={"session_id": str(session_id)},
            )
            db.commit()
    _clear_refresh_cookie(response)
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@router.get("/me", response_model=UserRead)
def get_current_user_profile(
    current_user: Annotated[User, Depends(get_current_user)],
):
    return UserRead.model_validate(current_user)


@router.get(
    "/users",
    response_model=list[UserRead],
    dependencies=[Depends(require_role("system_admin"))],
)
def list_users(
    db: Annotated[Session, Depends(get_db)],
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    return (
        db.query(User)
        .options(joinedload(User.role_record))
        .order_by(User.created_at.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )


@router.post(
    "/users",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
)
def create_managed_user(
    payload: ManagedUserCreate,
    db: Annotated[Session, Depends(get_db)],
    _admin: Annotated[User, Depends(require_role("system_admin"))],
):
    if db.query(User).filter(User.email == payload.email.lower()).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="An account with this email already exists.")
    if payload.phone and db.query(User).filter(User.phone == payload.phone).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="An account with this phone number already exists.")
    department = _check_department(db, payload.role, payload.department_id)
    user = User(
        full_name=payload.full_name,
        email=payload.email.lower(),
        phone=payload.phone,
        aadhaar_last4=payload.aadhaar_last4,
        role=_legacy_role(payload.role),
        role_id=_role_record(db, payload.role).id,
        department=department.name if department else None,
        department_id=department.id if department else None,
        hashed_password=hash_password(payload.password),
        is_active=True,
    )
    db.add(user)
    db.flush()
    record_audit(
        db,
        action="USER_CREATED",
        resource_type="user",
        resource_id=user.id,
        actor_id=_admin.id,
        actor_role=get_user_role_key(_admin),
        role_id=_admin.role_id,
        department_id=_admin.department_id,
        metadata={"role": payload.role, "department_id": user.department_id},
    )
    db.commit()
    db.refresh(user)
    return UserRead.model_validate(user)


@router.patch("/users/{user_id}", response_model=UserRead)
def update_managed_user(
    user_id: int,
    payload: ManagedUserUpdate,
    db: Annotated[Session, Depends(get_db)],
    _admin: Annotated[User, Depends(require_role("system_admin"))],
):
    user = (
        db.query(User)
        .options(joinedload(User.role_record))
        .filter(User.id == user_id)
        .first()
    )
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    old_role = get_user_role_key(user)
    old_department_id = user.department_id
    old_is_active = user.is_active
    next_role = payload.role or get_user_role_key(user)
    next_department_id = (
        payload.department_id
        if "department_id" in payload.model_fields_set
        else user.department_id
    )
    department = _check_department(db, next_role, next_department_id)
    user.role = _legacy_role(next_role)
    user.role_id = _role_record(db, next_role).id
    user.department_id = department.id if department else None
    user.department = department.name if department else None
    if payload.is_active is not None:
        user.is_active = payload.is_active
        if payload.is_active:
            user.staff_request_pending = False
        if not user.is_active:
            db.query(AuthSession).filter(
                AuthSession.user_id == user.id,
                AuthSession.revoked_at.is_(None),
            ).update({AuthSession.revoked_at: datetime.now(timezone.utc)})
    record_audit(
        db,
        action="USER_ACCESS_UPDATED",
        resource_type="user",
        resource_id=user.id,
        actor_id=_admin.id,
        actor_role=get_user_role_key(_admin),
        role_id=_admin.role_id,
        department_id=_admin.department_id,
        metadata={
            "old_role": old_role,
            "new_role": next_role,
            "old_department_id": old_department_id,
            "new_department_id": user.department_id,
            "old_is_active": old_is_active,
            "new_is_active": user.is_active,
        },
    )
    db.commit()
    db.refresh(user)
    return UserRead.model_validate(user)
