"""
Profile Routes
==============
User health profile CRUD endpoints.

GET    /api/v1/profile/{user_id}       — fetch profile
POST   /api/v1/profile                 — create/update profile
DELETE /api/v1/profile/{user_id}       — delete (GDPR)
GET    /api/v1/profile/{user_id}/history — assessment history
"""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from src.api.auth import require_api_key

router = APIRouter(
    prefix="/api/v1/profile",
    tags=["Profile"],
    dependencies=[Depends(require_api_key)],
)
logger = logging.getLogger(__name__)


class ProfileUpdateRequest(BaseModel):
    user_id: str
    age: Optional[int] = None
    biological_sex: Optional[str] = None
    height_cm: Optional[float] = None
    weight_kg: Optional[float] = None
    activity_level: Optional[str] = None
    smoking_status: Optional[str] = None
    diet_quality: Optional[str] = None
    sleep_hours: Optional[str] = None
    alcohol_weekly: Optional[str] = None
    stress_level: Optional[int] = None
    salt_intake: Optional[str] = None
    sugar_intake: Optional[str] = None
    family_diabetes: Optional[bool] = None
    family_cvd: Optional[bool] = None
    family_htn: Optional[bool] = None


@router.get("/{user_id}")
async def get_profile(user_id: str):
    """Fetch a user's health profile."""
    try:
        from src.profile.profile_service import profile_service
        profile = profile_service.get_profile(user_id)
        if not profile:
            raise HTTPException(status_code=404, detail="Profile not found")
        return {"success": True, "profile": profile.model_dump()}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_profile error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("")
async def upsert_profile(request: ProfileUpdateRequest):
    """Create or update a user's health profile."""
    try:
        from src.profile.profile_service import profile_service
        answers = request.model_dump(exclude_none=True)
        profile = profile_service.update_profile_from_answers(
            request.user_id, answers
        )
        return {"success": True, "profile": profile.model_dump()}
    except Exception as e:
        logger.error("upsert_profile error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{user_id}")
async def delete_profile(user_id: str):
    """Delete a user's health profile (GDPR right to erasure)."""
    try:
        from src.profile.profile_service import profile_service
        ok = profile_service.delete_profile(user_id)
        if not ok:
            raise HTTPException(status_code=404, detail="Profile not found")
        return {"success": True, "message": "Profile deleted"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("delete_profile error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{user_id}/history")
async def get_history(user_id: str, limit: int = 10):
    """Retrieve a user's past assessment results."""
    try:
        from src.profile.profile_service import profile_service
        history = profile_service.get_assessment_history(user_id, limit)
        return {
            "success": True,
            "user_id": user_id,
            "history": [
                {
                    "result_id": r.result_id,
                    "condition": r.condition,
                    "risk_probability": r.risk_probability,
                    "risk_category": r.risk_category,
                    "created_at": r.created_at.isoformat(),
                }
                for r in history
            ],
        }
    except Exception as e:
        logger.error("get_history error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
