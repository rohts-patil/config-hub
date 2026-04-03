from __future__ import annotations

"""Auth router — register, login, me."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.schemas.schemas import (
    GoogleAuthRequest,
    TokenResponse,
    UserLogin,
    UserOut,
    UserRegister,
)
from app.services.auth import (
    build_unusable_password_hash,
    hash_password,
    verify_password,
    create_access_token,
    get_current_user,
    verify_google_id_token,
)
from app.services.invites import accept_pending_org_invites, normalize_email

router = APIRouter(prefix="/api/v1/auth", tags=["Auth"])


@router.post(
    "/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED
)
async def register(body: UserRegister, db: AsyncSession = Depends(get_db)):
    normalized_email = normalize_email(body.email)
    # Check if user exists
    result = await db.execute(
        select(User).where(func.lower(User.email) == normalized_email)
    )
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        email=normalized_email,
        name=body.name,
        password_hash=hash_password(body.password),
    )
    db.add(user)
    await db.flush()
    await accept_pending_org_invites(db, user)
    token = create_access_token(user.id)
    return TokenResponse(access_token=token)


@router.post("/login", response_model=TokenResponse)
async def login(body: UserLogin, db: AsyncSession = Depends(get_db)):
    normalized_email = normalize_email(body.email)
    result = await db.execute(
        select(User).where(func.lower(User.email) == normalized_email)
    )
    user = result.scalar_one_or_none()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    await accept_pending_org_invites(db, user)
    token = create_access_token(user.id)
    return TokenResponse(access_token=token)


@router.post("/google", response_model=TokenResponse)
async def google_login(body: GoogleAuthRequest, db: AsyncSession = Depends(get_db)):
    identity = await verify_google_id_token(body.credential)
    normalized_email = normalize_email(identity.email)

    result = await db.execute(select(User).where(User.google_sub == identity.sub))
    user = result.scalar_one_or_none()

    if user is None:
        result = await db.execute(
            select(User).where(func.lower(User.email) == normalized_email)
        )
        user = result.scalar_one_or_none()

        if user is None:
            user = User(
                email=normalized_email,
                name=identity.name,
                password_hash=build_unusable_password_hash(),
                google_sub=identity.sub,
            )
            db.add(user)
        else:
            if user.google_sub and user.google_sub != identity.sub:
                raise HTTPException(
                    status_code=409,
                    detail="This email is already linked to a different Google account",
                )
            if not user.google_sub:
                user.google_sub = identity.sub

    await db.flush()
    await accept_pending_org_invites(db, user)
    token = create_access_token(user.id)
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserOut)
async def me(current_user: User = Depends(get_current_user)):
    return current_user
