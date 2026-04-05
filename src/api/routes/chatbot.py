"""
Chatbot Routes
==============
Conversational health assessment endpoints.

Endpoints:
  POST /api/v1/chat          — send a message, get a reply
  GET  /api/v1/chat/session/{session_id}  — inspect session state
  DELETE /api/v1/chat/session/{session_id} — clear a session
"""

import sys
import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from src.api.schemas.chatbot import (
    ChatRequest,
    ChatResponse,
    AssessmentResultSummary,
    SessionInfoResponse,
)
from src.chatbot.handlers.conversation_manager import ConversationManager
from src.chatbot.handlers.session import session_store

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/chat", tags=["Chatbot"])

# Single shared conversation manager (stateless — all state lives in sessions)
_conversation_manager = ConversationManager()


# ── Main chat endpoint ────────────────────────────────────────────────────────

@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Send a message to the health chatbot and receive a reply.

    - **session_id**: pass `null` to start a new session; include it on subsequent turns
    - **message**: natural language (e.g. *"Check my diabetes risk"*, *"I'm 45, male"*, *"What should I do?"*)

    The bot will guide you through data collection and run a risk prediction when
    enough information has been gathered.
    """
    try:
        outcome = _conversation_manager.handle_message(
            session_id=request.session_id,
            message=request.message,
        )
    except Exception as e:
        logger.error("Chat handler error: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Chat processing failed: {str(e)}")

    # Build optional result summary
    result_summary = None
    if outcome["assessment_complete"] and outcome.get("result"):
        raw = outcome["result"]
        condition = _infer_condition(request.session_id or outcome["session_id"])
        risk = raw.get("risk", {})
        if risk:
            result_summary = AssessmentResultSummary(
                condition=condition or "unknown",
                risk_percentage=risk.get("risk_percentage", 0.0),
                risk_category=risk.get("risk_category", "Unknown"),
                prediction=risk.get("prediction", 0),
            )

    return ChatResponse(
        session_id=outcome["session_id"],
        reply=outcome["reply"],
        assessment_complete=outcome["assessment_complete"],
        result=result_summary,
    )


# ── Session management endpoints ──────────────────────────────────────────────

@router.get("/session/{session_id}", response_model=SessionInfoResponse)
async def get_session(session_id: str):
    """Retrieve current state of a chat session (useful for debugging)."""
    session = session_store.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found or expired.")
    return SessionInfoResponse(**session.to_dict())


@router.delete("/session/{session_id}")
async def delete_session(session_id: str):
    """Clear a chat session (e.g. to start fresh)."""
    session = session_store.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found or expired.")
    session_store.delete(session_id)
    return {"success": True, "message": "Session cleared."}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _infer_condition(session_id: str) -> str:
    """Look up the active (or last) condition from the session."""
    session = session_store.get(session_id)
    if not session:
        return "unknown"
    return session.last_assessment_type or session.active_assessment or "unknown"
