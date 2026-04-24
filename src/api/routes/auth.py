"""
Élan — JWT Authentication Routes
=================================
POST   /api/v1/auth/register          — create account
POST   /api/v1/auth/login             — get JWT
GET    /api/v1/auth/me                — current user info
PUT    /api/v1/auth/profile           — update name / dob / gender / height / weight
PUT    /api/v1/auth/change-password   — change password (requires current password)
DELETE /api/v1/auth/account           — delete account (requires password confirmation)
"""

import os
import uuid
from datetime import datetime, timedelta, timezone

import bcrypt as _bcrypt_lib
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from pydantic import BaseModel, Field

from src.api.db.users_db import (
    create_user,
    delete_user,
    get_user_by_email,
    get_user_by_id,
    update_user,
)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

# ── Config ───────────────────────────────────────────────────────────
SECRET_KEY = os.getenv("ELAN_SECRET_KEY", "elan-dev-secret-change-in-production-32chars")
ALGORITHM  = "HS256"
TOKEN_TTL  = timedelta(days=7)

oauth2 = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


# ── Password helpers ─────────────────────────────────────────────────
def _hash(password: str) -> str:
    return _bcrypt_lib.hashpw(password.encode(), _bcrypt_lib.gensalt()).decode()


def _verify(plain: str, hashed: str) -> bool:
    return _bcrypt_lib.checkpw(plain.encode(), hashed.encode())


# ── JWT helpers ──────────────────────────────────────────────────────
def _make_token(user_id: str) -> str:
    payload = {"sub": user_id, "exp": datetime.now(timezone.utc) + TOKEN_TTL}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def _decode_token(token: str) -> str:
    try:
        data = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return data["sub"]
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token.")


# ── Dependency ───────────────────────────────────────────────────────
def current_user(token: str = Depends(oauth2)) -> dict:
    user_id = _decode_token(token)
    user = get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=401, detail="User not found.")
    return user


# ── Schemas ───────────────────────────────────────────────────────────
class RegisterRequest(BaseModel):
    name:     str = Field(..., min_length=1)
    email:    str
    password: str = Field(..., min_length=8)


class UserOut(BaseModel):
    id:         str
    name:       str
    email:      str
    dob:        str = ""
    gender:     str = ""
    height:     str = ""
    weight:     str = ""
    created_at: str


class TokenResponse(BaseModel):
    access_token: str
    token_type:   str = "bearer"
    user:         UserOut


class ProfileUpdateRequest(BaseModel):
    name:   str | None = None
    dob:    str | None = None
    gender: str | None = None
    height: str | None = None
    weight: str | None = None


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password:     str = Field(..., min_length=8)


class DeleteAccountRequest(BaseModel):
    password: str


def _user_out(u: dict) -> UserOut:
    return UserOut(
        id=u["id"], name=u["name"], email=u["email"],
        dob=u.get("dob", ""), gender=u.get("gender", ""),
        height=u.get("height", ""), weight=u.get("weight", ""),
        created_at=u["created_at"],
    )


# ── Routes ───────────────────────────────────────────────────────────

@router.post("/register", response_model=TokenResponse, status_code=201)
def register(req: RegisterRequest):
    if get_user_by_email(req.email):
        raise HTTPException(status_code=409, detail="An account with this email already exists.")

    user_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    try:
        user = create_user(
            user_id=user_id,
            name=req.name,
            email=req.email,
            password_hash=_hash(req.password),
            created_at=now,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))

    return TokenResponse(access_token=_make_token(user_id), user=_user_out(user))


@router.post("/login", response_model=TokenResponse)
def login(form: OAuth2PasswordRequestForm = Depends()):
    user = get_user_by_email(form.username)   # OAuth2 uses 'username' for email
    if not user or not _verify(form.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Incorrect email or password.")
    return TokenResponse(access_token=_make_token(user["id"]), user=_user_out(user))


@router.get("/me", response_model=UserOut)
def me(user: dict = Depends(current_user)):
    return _user_out(user)


@router.put("/profile", response_model=UserOut)
def update_profile(req: ProfileUpdateRequest, user: dict = Depends(current_user)):
    updates = req.model_dump(exclude_none=True)
    if not updates:
        return _user_out(user)
    updated = update_user(user["id"], **updates)
    return _user_out(updated)


@router.put("/change-password", status_code=204)
def change_password(req: ChangePasswordRequest, user: dict = Depends(current_user)):
    if not _verify(req.current_password, user["password_hash"]):
        raise HTTPException(status_code=400, detail="Current password is incorrect.")
    update_user(user["id"], password_hash=_hash(req.new_password))


@router.delete("/account", status_code=204)
def delete_account(req: DeleteAccountRequest, user: dict = Depends(current_user)):
    if not _verify(req.password, user["password_hash"]):
        raise HTTPException(status_code=400, detail="Password confirmation failed.")
    delete_user(user["id"])
