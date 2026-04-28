"""
Chatbot Schemas
===============
Pydantic models for the chat endpoint request/response.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Single-turn chat request."""
    message: str = Field(..., min_length=1, max_length=2000, description="User message")
    session_id: Optional[str] = Field(None, description="Session ID (omit to start a new session)")
    user_id: Optional[str] = Field(None, description="Stable user UUID (from localStorage) for profile memory")
    assessment_context: Optional[Dict[str, Any]] = Field(
        None,
        description="Completed assessment result sent by the frontend on the first chat message "
                    "after a wizard assessment. Shape: {condition, completedAt, result: {probability, "
                    "risk_level, interpretation, top_factors, protective_factors, recommendations}}",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "message": "Check my diabetes risk",
                "session_id": None,
                "user_id": None,
                "assessment_context": None,
            }
        }


class AssessmentResultSummary(BaseModel):
    """Condensed risk result included in the chat response when an assessment completes."""
    condition: str = Field(..., description="Assessed condition (diabetes / cvd / hypertension)")
    risk_percentage: float = Field(..., description="Estimated risk as a percentage")
    risk_category: str = Field(..., description="Risk level (Low / Moderate / High / Very High)")
    prediction: int = Field(..., description="Binary prediction (0 = No, 1 = Yes)")


class ChatResponse(BaseModel):
    """Single-turn chat response."""
    session_id: str = Field(..., description="Session ID — pass this back in subsequent requests")
    reply: str = Field(..., description="Bot reply text (may contain Markdown)")
    assessment_complete: bool = Field(False, description="True when an assessment just completed")
    result: Optional[AssessmentResultSummary] = Field(
        None, description="Assessment result summary (present only when assessment_complete=True)"
    )
    profile_updated: bool = Field(False, description="True when user profile was updated")

    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "abc-123",
                "reply": "Hi there! I can help you check your risk for diabetes, CVD, or hypertension.",
                "assessment_complete": False,
                "result": None,
            }
        }


class SessionInfoResponse(BaseModel):
    """Current session state (for debugging / introspection)."""
    session_id: str
    active_assessment: Optional[str]
    collected_metrics: List[str]
    turn_count: int
    last_active: str
