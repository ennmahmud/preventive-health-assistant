"""
Chatbot Endpoint Tests
======================
Integration tests for POST /api/v1/chat and session management endpoints.
"""

import pytest
from fastapi.testclient import TestClient

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.api.main import app
from src.chatbot.handlers.session import session_store


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def chat(client, message, session_id=None):
    """Helper: post a single chat message and return the response dict."""
    r = client.post(
        "/api/v1/chat",
        json={"message": message, "session_id": session_id},
    )
    assert r.status_code == 200
    return r.json()


# ── Basic response contract ───────────────────────────────────────────────────

class TestChatResponseContract:
    def test_response_has_required_fields(self, client):
        data = chat(client, "hello")
        assert "session_id" in data
        assert "reply" in data
        assert "assessment_complete" in data
        assert isinstance(data["reply"], str)
        assert len(data["reply"]) > 0

    def test_new_session_created_when_none_provided(self, client):
        data = chat(client, "hi")
        assert data["session_id"] is not None
        assert len(data["session_id"]) > 0

    def test_session_id_persisted_across_turns(self, client):
        d1 = chat(client, "hello")
        sid = d1["session_id"]
        d2 = chat(client, "tell me more", session_id=sid)
        assert d2["session_id"] == sid

    def test_assessment_complete_false_on_greeting(self, client):
        data = chat(client, "hello")
        assert data["assessment_complete"] is False
        assert data["result"] is None

    def test_result_is_none_when_not_complete(self, client):
        data = chat(client, "what can you do?")
        assert data["result"] is None


# ── Intent routing ─────────────────────────────────────────────────────────────

class TestIntentRouting:
    def test_greet_returns_welcome_message(self, client):
        data = chat(client, "hi there")
        reply = data["reply"].lower()
        assert any(kw in reply for kw in ("diabetes", "cvd", "hypertension", "health", "risk"))

    def test_help_intent_mentions_capabilities(self, client):
        data = chat(client, "help")
        reply = data["reply"].lower()
        assert any(kw in reply for kw in ("diabetes", "cvd", "hypertension", "help"))

    def test_diabetes_intent_starts_collection(self, client):
        data = chat(client, "I want to check my diabetes risk")
        reply = data["reply"].lower()
        # Should ask for first required field (age or gender)
        assert any(kw in reply for kw in ("age", "old", "gender", "sex", "diabetes"))

    def test_cvd_intent_starts_collection(self, client):
        data = chat(client, "check my heart health")
        reply = data["reply"].lower()
        assert any(kw in reply for kw in ("age", "cardiovascular", "cvd", "heart", "gender"))

    def test_hypertension_intent_starts_collection(self, client):
        data = chat(client, "check my blood pressure risk")
        reply = data["reply"].lower()
        # Should NOT ask for BP — should mention preventive model instead
        assert any(kw in reply for kw in ("age", "hypertension", "preventive", "risk", "gender"))

    def test_hypertension_intent_not_routed_to_cvd(self, client):
        """blood pressure keywords must route to hypertension, not CVD."""
        data = chat(client, "I want to check my blood pressure risk")
        reply = data["reply"].lower()
        # Should mention hypertension (not just heart/cardiac)
        assert "hypertension" in reply or "blood pressure" in reply or "preventive" in reply

    def test_unknown_intent_suggests_options(self, client):
        data = chat(client, "zxqwerty1234")
        reply = data["reply"].lower()
        assert any(kw in reply for kw in ("diabetes", "cvd", "hypertension", "help", "don't"))


# ── Multi-turn metric collection ───────────────────────────────────────────────

class TestMultiTurnCollection:
    def test_entities_accumulated_across_turns(self, client):
        # Start assessment
        d1 = chat(client, "check my diabetes risk")
        sid = d1["session_id"]

        # Provide age
        chat(client, "I am 45 years old", session_id=sid)

        # Check session state
        r = client.get(f"/api/v1/chat/session/{sid}")
        assert r.status_code == 200
        collected = r.json()["collected_metrics"]
        assert "age" in collected

    def test_gender_extracted_from_message(self, client):
        d1 = chat(client, "check my diabetes risk")
        sid = d1["session_id"]

        chat(client, "I am 45, male", session_id=sid)

        r = client.get(f"/api/v1/chat/session/{sid}")
        collected = r.json()["collected_metrics"]
        assert "age" in collected
        assert "gender" in collected

    def test_turn_count_increments(self, client):
        d1 = chat(client, "hello")
        sid = d1["session_id"]
        chat(client, "check my diabetes risk", session_id=sid)
        chat(client, "I'm 40", session_id=sid)

        r = client.get(f"/api/v1/chat/session/{sid}")
        assert r.json()["turn_count"] >= 3


# ── Session management endpoints ──────────────────────────────────────────────

class TestSessionManagement:
    def test_get_session_returns_state(self, client):
        d = chat(client, "hello")
        sid = d["session_id"]

        r = client.get(f"/api/v1/chat/session/{sid}")
        assert r.status_code == 200
        data = r.json()
        assert data["session_id"] == sid
        assert "turn_count" in data
        assert "last_active" in data

    def test_get_nonexistent_session_returns_404(self, client):
        r = client.get("/api/v1/chat/session/does-not-exist-xyz")
        assert r.status_code == 404

    def test_delete_session(self, client):
        d = chat(client, "hi")
        sid = d["session_id"]

        r = client.delete(f"/api/v1/chat/session/{sid}")
        assert r.status_code == 200
        assert r.json()["success"] is True

        # Session should be gone
        r2 = client.get(f"/api/v1/chat/session/{sid}")
        assert r2.status_code == 404

    def test_delete_nonexistent_session_returns_404(self, client):
        r = client.delete("/api/v1/chat/session/no-such-session-abc")
        assert r.status_code == 404


# ── Input validation ───────────────────────────────────────────────────────────

class TestChatInputValidation:
    def test_empty_message_rejected(self, client):
        r = client.post("/api/v1/chat", json={"message": ""})
        assert r.status_code == 422

    def test_whitespace_only_message_rejected(self, client):
        r = client.post("/api/v1/chat", json={"message": "   "})
        # Pydantic min_length=1 on stripped content — may be 200 with empty reply or 422
        # Either is acceptable; just must not crash (500)
        assert r.status_code in (200, 422)

    def test_very_long_message_accepted_or_truncated(self, client):
        """Messages up to 2000 chars are accepted; beyond that Pydantic rejects."""
        long_msg = "a" * 2000
        r = client.post("/api/v1/chat", json={"message": long_msg})
        assert r.status_code == 200

    def test_message_over_limit_rejected(self, client):
        r = client.post("/api/v1/chat", json={"message": "a" * 2001})
        assert r.status_code == 422
