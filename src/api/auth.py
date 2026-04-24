"""
API Key Authentication
======================
Simple Bearer-token auth for all /api/v1/ endpoints.

Set the API_KEY environment variable to enable protection.
If API_KEY is not set the server starts in open (dev) mode and logs a warning.

Usage in routes:
    from src.api.auth import require_api_key
    router = APIRouter(dependencies=[Depends(require_api_key)])
"""

import logging
import os
from typing import Optional

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

logger = logging.getLogger(__name__)

_bearer = HTTPBearer(auto_error=False)

_API_KEY: Optional[str] = os.getenv("API_KEY") or None
_JWT_SECRET = os.getenv("ELAN_SECRET_KEY", "elan-dev-secret-change-in-production-32chars")
_ALGORITHM = "HS256"

if not _API_KEY:
    logger.warning(
        "API_KEY env var not set — server running in open (unauthenticated) mode. "
        "Set API_KEY=<secret> before deploying to production."
    )


def _is_valid_jwt(token: str) -> bool:
    try:
        jwt.decode(token, _JWT_SECRET, algorithms=[_ALGORITHM])
        return True
    except JWTError:
        return False


async def require_api_key(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(_bearer),
) -> None:
    """Accept either the raw API key or a valid Élan JWT as the Bearer credential."""
    if not _API_KEY:
        return  # Dev mode — allow all

    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    if token == _API_KEY or _is_valid_jwt(token):
        return

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing API key.",
        headers={"WWW-Authenticate": "Bearer"},
    )
