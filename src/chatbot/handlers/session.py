"""
Session Store
=============
In-memory session management for chatbot conversations.

Each session tracks:
  - Collected health metrics (built up across multiple turns)
  - Active assessment type (diabetes / cvd / hypertension)
  - Conversation history (list of {role, content} dicts)
  - Last assessment result (for follow-up questions)
  - Session metadata (created_at, last_active)
"""

import random
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional


# Sessions expire after 30 minutes of inactivity
_SESSION_TTL_MINUTES = 30

# Conversation history caps
_MAX_HISTORY_TURNS = 100       # max messages stored per session
_MAX_MESSAGE_CHARS = 4_000     # truncate single messages beyond this length

# Probabilistic cleanup: run on ~5% of get_or_create calls
_CLEANUP_PROBABILITY = 0.05


class Session:
    """Single user conversation session."""

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.created_at: datetime = datetime.utcnow()
        self.last_active: datetime = datetime.utcnow()

        # Which condition we're currently collecting data for
        self.active_assessment: Optional[str] = None  # "diabetes" | "cvd" | "hypertension"

        # Collected metrics accumulated from user messages
        self.metrics: Dict[str, Any] = {}

        # Full conversation history
        self.history: List[Dict[str, str]] = []

        # Last prediction result (for result / recommendation follow-ups)
        self.last_result: Optional[Dict[str, Any]] = None
        self.last_assessment_type: Optional[str] = None

    # ── Metrics ──────────────────────────────────────────────────────────────

    def update_metrics(self, new_metrics: Dict[str, Any]) -> None:
        """Merge new extracted metric values into the session."""
        self.metrics.update({k: v for k, v in new_metrics.items() if v is not None})
        self.touch()

    def clear_metrics(self) -> None:
        """Reset collected metrics (e.g. after a completed assessment)."""
        self.metrics = {}
        self.active_assessment = None
        self.touch()

    # ── History ──────────────────────────────────────────────────────────────

    def add_message(self, role: str, content: str) -> None:
        """Append a message to conversation history (capped to avoid unbounded memory)."""
        # Truncate oversized messages before storing
        if len(content) > _MAX_MESSAGE_CHARS:
            content = content[:_MAX_MESSAGE_CHARS] + "… [truncated]"
        self.history.append({"role": role, "content": content, "timestamp": datetime.utcnow().isoformat()})
        # Drop oldest entries if history exceeds the cap
        if len(self.history) > _MAX_HISTORY_TURNS:
            self.history = self.history[-_MAX_HISTORY_TURNS:]
        self.touch()

    # ── Result ───────────────────────────────────────────────────────────────

    def store_result(self, assessment_type: str, result: Dict[str, Any]) -> None:
        self.last_result = result
        self.last_assessment_type = assessment_type
        self.touch()

    # ── Helpers ───────────────────────────────────────────────────────────────

    def touch(self) -> None:
        self.last_active = datetime.utcnow()

    def is_expired(self) -> bool:
        return datetime.utcnow() - self.last_active > timedelta(minutes=_SESSION_TTL_MINUTES)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "active_assessment": self.active_assessment,
            "collected_metrics": list(self.metrics.keys()),
            "turn_count": len(self.history),
            "last_active": self.last_active.isoformat(),
        }


class SessionStore:
    """Thread-safe in-memory store for all active sessions."""

    def __init__(self):
        self._sessions: Dict[str, Session] = {}

    def get_or_create(self, session_id: Optional[str] = None) -> Session:
        """Return existing session or create a new one.

        Probabilistically prunes expired sessions on each call so the store
        never grows without bound even without an external scheduler.
        """
        # ~5% of calls trigger a full sweep of expired sessions
        if random.random() < _CLEANUP_PROBABILITY:
            self.cleanup_expired()

        if session_id and session_id in self._sessions:
            session = self._sessions[session_id]
            if not session.is_expired():
                return session
            # Expired — replace with a fresh session under the same ID
        sid = session_id or str(uuid.uuid4())
        session = Session(sid)
        self._sessions[sid] = session
        return session

    def get(self, session_id: str) -> Optional[Session]:
        """Return session if it exists and is not expired."""
        session = self._sessions.get(session_id)
        if session and not session.is_expired():
            return session
        return None

    def delete(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)

    def cleanup_expired(self) -> int:
        """Remove expired sessions. Returns count removed."""
        expired = [sid for sid, s in self._sessions.items() if s.is_expired()]
        for sid in expired:
            del self._sessions[sid]
        return len(expired)

    @property
    def active_count(self) -> int:
        return sum(1 for s in self._sessions.values() if not s.is_expired())


# Global singleton
session_store = SessionStore()
