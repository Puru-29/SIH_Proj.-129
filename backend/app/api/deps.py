from datetime import datetime, timezone
from typing import Annotated, Callable
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session, joinedload

from app.core.security import decode_access_token
from app.database import get_db
from app.models.auth_session import AuthSession
from app.models.user import User, UserRole

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/oauth/token", auto_error=False
)

LEGACY_ROLE_KEYS = {
    UserRole.CITIZEN: "citizen",
    UserRole.OFFICER: "department_officer",
    UserRole.ADMIN: "system_admin",
    UserRole.DEVELOPER: "interoperability_admin",
    UserRole.OPERATOR: "interoperability_admin",
    UserRole.AUDITOR: "auditor",
}


def get_user_role_key(user: User) -> str:
    if user.role_record is not None:
        return user.role_record.key
    return LEGACY_ROLE_KEYS.get(user.role, "unknown")


def get_current_user(
    token: Annotated[str | None, Depends(oauth2_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not token:
        raise unauthorized

    payload = decode_access_token(token)
    if not payload or payload.get("type") != "access":
        raise unauthorized
    try:
        user_id = int(payload["sub"])
        session_id = UUID(payload["sid"])
    except (KeyError, TypeError, ValueError):
        raise unauthorized from None

    now = datetime.now(timezone.utc)
    auth_session = db.query(AuthSession).filter(AuthSession.id == session_id).first()
    if (
        auth_session is None
        or auth_session.user_id != user_id
        or auth_session.revoked_at is not None
        or _as_utc(auth_session.expires_at) <= now
    ):
        raise unauthorized

    user = (
        db.query(User)
        .options(joinedload(User.role_record))
        .filter(User.id == user_id)
        .first()
    )
    if user is None or not user.is_active:
        raise unauthorized
    return user


def _as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


def require_authenticated_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    return current_user


def require_role(*allowed_roles: str | UserRole) -> Callable:
    role_keys = {
        role.value if isinstance(role, UserRole) else role
        for role in allowed_roles
    }

    def role_checker(
        user: Annotated[User, Depends(require_authenticated_user)],
    ) -> User:
        if get_user_role_key(user) not in role_keys:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action.",
            )
        return user

    return role_checker


def ensure_department_access(user: User, department_id: int) -> None:
    role_key = get_user_role_key(user)
    if role_key in {"system_admin", "interoperability_admin"}:
        return
    if role_key != "department_officer" or user.department_id != department_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This resource is outside your department.",
        )


def require_department(
    department_id: int,
    user: Annotated[User, Depends(get_current_user)],
) -> User:
    ensure_department_access(user, department_id)
    return user


def ensure_resource_access(
    user: User,
    *,
    citizen_id: int | None,
    department_id: int | None,
) -> None:
    role_key = get_user_role_key(user)
    if role_key == "citizen":
        if citizen_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Citizens may only access their own records.",
            )
        return
    if role_key == "department_officer":
        if department_id is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This resource is not assigned to a department.",
            )
        ensure_department_access(user, department_id)
        return
    if role_key not in {"system_admin", "interoperability_admin"}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this resource.",
        )
