"""
BioNexus India V2 — Authentication Service

Core authentication functionality:
  - Password hashing (bcrypt)
  - JWT access/refresh token creation and validation
  - FastAPI dependencies for auth and RBAC

Usage in routes:
    # Require any authenticated user
    @router.get("/profile")
    async def profile(user: User = Depends(get_current_user)):
        ...

    # Require specific role(s)
    @router.post("/admin-action")
    async def admin_action(user: User = Depends(require_role("admin"))):
        ...

    # Optional auth (works for both public and authenticated)
    @router.get("/datasets")
    async def list_datasets(user: User | None = Depends(get_optional_user)):
        ...
"""

import logging
from datetime import datetime, timedelta
from typing import Optional

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from database import get_session
from database.models import User

logger = logging.getLogger(__name__)

# --- OAuth2 scheme (extracts token from Authorization header) ---
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=True)
oauth2_scheme_optional = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)


def hash_password(password: str) -> str:
    """Hash a plaintext password using bcrypt directly."""
    password_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password_bytes, salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against its bcrypt hash."""
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8"),
    )


def create_access_token(user_id: str, role: str) -> str:
    """
    Create a short-lived JWT access token.

    Contains: sub (user_id), role, type, exp
    Expires in: settings.access_token_expire_minutes (default 30min)
    """
    expire = datetime.utcnow() + timedelta(
        minutes=settings.access_token_expire_minutes
    )
    payload = {
        "sub": str(user_id),
        "role": role,
        "type": "access",
        "exp": expire,
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_refresh_token(user_id: str) -> str:
    """
    Create a long-lived JWT refresh token.

    Contains: sub (user_id), type, exp
    Expires in: settings.refresh_token_expire_days (default 7 days)
    """
    expire = datetime.utcnow() + timedelta(
        days=settings.refresh_token_expire_days
    )
    payload = {
        "sub": str(user_id),
        "type": "refresh",
        "exp": expire,
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict:
    """
    Decode and validate a JWT token.

    Raises HTTPException 401 if token is invalid or expired.
    """
    try:
        payload = jwt.decode(
            token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
        )
        return payload
    except JWTError as e:
        logger.warning(f"JWT decode error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_session),
) -> User:
    """
    FastAPI dependency: returns the currently authenticated user.

    Extracts the JWT from the Authorization header, decodes it,
    and fetches the corresponding User from the database.

    Raises 401 if:
      - Token is missing, invalid, or expired
      - Token is not an access token
      - User doesn't exist or is inactive
    """
    payload = decode_token(token)

    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type — use an access token",
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    result = await session.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated",
        )

    return user


async def get_optional_user(
    token: Optional[str] = Depends(oauth2_scheme_optional),
    session: AsyncSession = Depends(get_session),
) -> Optional[User]:
    """
    FastAPI dependency: returns the current user if authenticated, None otherwise.

    Use this for endpoints that work both publicly and authenticated,
    showing different levels of detail.
    """
    if token is None:
        return None

    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            return None

        user_id = payload.get("sub")
        if not user_id:
            return None

        result = await session.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()

        if user and user.is_active:
            return user
        return None

    except HTTPException:
        return None


def require_role(*allowed_roles: str):
    """
    FastAPI dependency factory: restricts access to specific roles.

    Usage:
        @router.post("/admin-only")
        async def admin_action(user: User = Depends(require_role("admin"))):
            ...

        @router.put("/institution-or-admin")
        async def action(user: User = Depends(require_role("institution", "admin"))):
            ...
    """

    async def role_checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required role(s): {', '.join(allowed_roles)}",
            )
        return user

    return role_checker
