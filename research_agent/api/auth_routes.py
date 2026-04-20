"""Auth endpoints — signup, signin, me."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db import get_session
from db.models import User
from services.auth import (
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    name: str | None = Field(default=None, max_length=120)


class SigninRequest(BaseModel):
    email: EmailStr
    password: str


class UserPublic(BaseModel):
    id: str
    email: EmailStr
    name: str | None = None


class AuthResponse(BaseModel):
    token: str
    user: UserPublic


@router.post("/signup", response_model=AuthResponse, status_code=201)
async def signup(
    payload: SignupRequest,
    db: AsyncSession = Depends(get_session),
) -> AuthResponse:
    email = payload.email.lower().strip()

    existing = await db.execute(select(User).where(User.email == email))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists",
        )

    user = User(
        email=email,
        name=payload.name.strip() if payload.name else None,
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    token = create_access_token(subject=user.id)
    return AuthResponse(token=token, user=UserPublic(**user.to_public()))


@router.post("/signin", response_model=AuthResponse)
async def signin(
    payload: SigninRequest,
    db: AsyncSession = Depends(get_session),
) -> AuthResponse:
    email = payload.email.lower().strip()
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    token = create_access_token(subject=user.id)
    return AuthResponse(token=token, user=UserPublic(**user.to_public()))


@router.get("/me", response_model=UserPublic)
async def me(current: User = Depends(get_current_user)) -> UserPublic:
    return UserPublic(**current.to_public())
