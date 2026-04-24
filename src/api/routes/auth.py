"""
Élan — JWT Authentication Routes
POST /api/v1/auth/register
POST /api/v1/auth/login
"""
import os
import uuid
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from jose import JWTError, jwt
import bcrypt as _bcrypt_lib

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

# ── Config ───────────────────────────────────────────────────────────
SECRET_KEY  = os.getenv("ELAN_SECRET_KEY", "elan-dev-secret-change-in-production-32chars")
ALGORITHM   = "HS256"
TOKEN_TTL   = timedelta(days=7)

oauth2 = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

# ── In-memory user store (replace with DB in production) ─────────────
_users: dict[str, dict] = {}   # email → user record

# ── Helpers ──────────────────────────────────────────────────────────
def _hash(password: str) -> str:
    return _bcrypt_lib.hashpw(password.encode(), _bcrypt_lib.gensalt()).decode()

def _verify(plain: str, hashed: str) -> bool:
    return _bcrypt_lib.checkpw(plain.encode(), hashed.encode())

def _make_token(user_id: str) -> str:
    payload = {
        "sub": user_id,
        "exp": datetime.now(timezone.utc) + TOKEN_TTL,
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def _decode_token(token: str) -> str:
    try:
        data = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return data["sub"]
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

# ── Schemas ───────────────────────────────────────────────────────────
class RegisterRequest(BaseModel):
    name: str
    email: str
    password: str

class UserOut(BaseModel):
    id: str
    name: str
    email: str
    created_at: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut

# ── Routes ───────────────────────────────────────────────────────────
@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(req: RegisterRequest):
    if req.email in _users:
        raise HTTPException(status_code=409, detail="An account with this email already exists.")
    if len(req.password) < 8:
        raise HTTPException(status_code=422, detail="Password must be at least 8 characters.")

    user_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    _users[req.email] = {
        "id": user_id,
        "name": req.name,
        "email": req.email,
        "password_hash": _hash(req.password),
        "created_at": now,
    }
    token = _make_token(user_id)
    out = UserOut(id=user_id, name=req.name, email=req.email, created_at=now)
    return TokenResponse(access_token=token, user=out)


@router.post("/login", response_model=TokenResponse)
def login(form: OAuth2PasswordRequestForm = Depends()):
    user = _users.get(form.username)   # OAuth2 uses 'username' field
    if not user or not _verify(form.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Incorrect email or password.")
    token = _make_token(user["id"])
    out = UserOut(id=user["id"], name=user["name"], email=user["email"], created_at=user["created_at"])
    return TokenResponse(access_token=token, user=out)


# ── Dependency for protected routes ──────────────────────────────────
def current_user(token: str = Depends(oauth2)) -> dict:
    user_id = _decode_token(token)
    for u in _users.values():
        if u["id"] == user_id:
            return u
    raise HTTPException(status_code=401, detail="User not found.")
