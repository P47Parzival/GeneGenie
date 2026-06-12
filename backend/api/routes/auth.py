"""
BioNexus India V2 — Authentication Routes

POST /auth/register  — create user account
POST /auth/login     — authenticate and get tokens
POST /auth/refresh   — exchange refresh token for new access token
GET  /auth/me        — get current user profile
PUT  /auth/me        — update profile
"""

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.schemas import (
    RegisterRequest,
    LoginRequest,
    TokenResponse,
    RefreshRequest,
    UserResponse,
    UserUpdateRequest,
    ErrorResponse,
)
from config import settings
from database import get_session
from database.models import User
from services.auth_service import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
    get_current_user,
)
from services.audit_service import audit_service
from services.notification_service import notification_service, NotificationEvent

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])

VALID_ROLES = {"researcher", "institution", "admin"}


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    responses={400: {"model": ErrorResponse}},
    summary="Register a new user",
)
async def register(
    body: RegisterRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    """Create a new user account and return auth tokens."""

    # Validate role
    if body.role not in VALID_ROLES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid role: '{body.role}'. Must be one of: {', '.join(VALID_ROLES)}",
        )

    # Check for existing email
    existing = await session.execute(
        select(User).where(User.email == body.email.lower())
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail="An account with this email already exists",
        )

    # Create user
    user = User(
        id=uuid.uuid4(),
        email=body.email.lower(),
        hashed_password=hash_password(body.password),
        full_name=body.full_name,
        role=body.role,
        is_active=True,
    )
    session.add(user)
    await session.flush()

    # Audit log
    await audit_service.log(
        session=session,
        actor_id=user.id,
        action="user.register",
        resource_type="user",
        resource_id=user.id,
        details={"role": body.role, "email": body.email.lower()},
        ip_address=request.client.host if request.client else None,
    )

    # Generate tokens
    access_token = create_access_token(str(user.id), user.role)
    refresh_token = create_refresh_token(str(user.id))

    # Notification (async)
    notification_service.dispatch(
        NotificationEvent.USER_REGISTERED,
        user.email,
        {"full_name": user.full_name, "role": user.role},
    )

    logger.info(f"User registered: {user.email} (role={user.role})")

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.access_token_expire_minutes * 60,
        user=UserResponse.model_validate(user),
    )


@router.post(
    "/login",
    response_model=TokenResponse,
    responses={401: {"model": ErrorResponse}},
    summary="Login and get tokens",
)
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: AsyncSession = Depends(get_session),
):
    """Authenticate with email and password, receive JWT tokens."""

    # Find user
    result = await session.execute(
        select(User).where(User.email == form_data.username.lower())
    )
    user = result.scalar_one_or_none()

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated",
        )

    # Audit log
    await audit_service.log(
        session=session,
        actor_id=user.id,
        action="user.login",
        resource_type="user",
        resource_id=user.id,
        ip_address=request.client.host if request.client else None,
    )

    # Generate tokens
    access_token = create_access_token(str(user.id), user.role)
    refresh_token = create_refresh_token(str(user.id))

    logger.info(f"User logged in: {user.email}")

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.access_token_expire_minutes * 60,
        user=UserResponse.model_validate(user),
    )


@router.post(
    "/refresh",
    response_model=TokenResponse,
    responses={401: {"model": ErrorResponse}},
    summary="Refresh access token",
)
async def refresh_token(
    body: RefreshRequest,
    session: AsyncSession = Depends(get_session),
):
    """Exchange a valid refresh token for a new access token."""

    payload = decode_token(body.refresh_token)

    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type — provide a refresh token",
        )

    user_id = payload.get("sub")
    result = await session.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    # Issue new tokens
    access_token = create_access_token(str(user.id), user.role)
    new_refresh_token = create_refresh_token(str(user.id))

    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
        expires_in=settings.access_token_expire_minutes * 60,
        user=UserResponse.model_validate(user),
    )


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user profile",
)
async def get_profile(user: User = Depends(get_current_user)):
    """Return the authenticated user's profile."""
    return UserResponse.model_validate(user)


@router.put(
    "/me",
    response_model=UserResponse,
    summary="Update current user profile",
)
async def update_profile(
    body: UserUpdateRequest,
    request: Request,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Update the authenticated user's profile."""

    if body.full_name is not None:
        user.full_name = body.full_name
    if body.email is not None:
        # Check uniqueness
        existing = await session.execute(
            select(User).where(User.email == body.email.lower(), User.id != user.id)
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Email already in use")
        user.email = body.email.lower()

    await audit_service.log(
        session=session,
        actor_id=user.id,
        action="user.update_profile",
        resource_type="user",
        resource_id=user.id,
        details=body.model_dump(exclude_none=True),
        ip_address=request.client.host if request.client else None,
    )

    return UserResponse.model_validate(user)
