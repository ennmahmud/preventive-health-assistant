"""
Conversation Manager
====================
Orchestrates multi-turn chatbot conversations.

Flow for an assessment:
  1. User signals intent (assess_diabetes / cvd / hypertension)
  2. Bot asks for required fields one-by-one (age, gender first)
  3. User provides values (extracted by entity extractor)
  4. When enough data collected → run prediction → return result
  5. User may ask for explanation or recommendations

Required fields per assessment type:
  All:            age, gender
  Diabetes:       + at least one of (bmi, hba1c, fasting_glucose)
  CVD:            + at least one of (total_cholesterol, systolic_bp)
  Hypertension:   + bmi (optional but helpful; age+gender alone is sufficient)
"""

import sys
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from src.chatbot.intents.classifier import classify_intent, Intent
from src.chatbot.intents.entities import extract_entities
from src.chatbot.handlers.session import Session, session_store
from src.chatbot.responses.response_generator import ResponseGenerator

logger = logging.getLogger(__name__)


# ── Required / nice-to-have fields per condition ─────────────────────────────

_REQUIRED: Dict[str, List[str]] = {
    "diabetes":     ["age", "gender"],
    "cvd":          ["age", "gender"],
    "hypertension": ["age", "gender"],
}

# One of these must be present before running prediction
_MINIMUM_USEFUL: Dict[str, List[str]] = {
    "diabetes":     ["bmi", "hba1c", "fasting_glucose", "waist_circumference"],
    "cvd":          ["total_cholesterol", "systolic_bp", "bmi", "hba1c"],
    "hypertension": [],  # age+gender is enough — model is robust
}

# The next field to ask for (in order) if still missing
_COLLECT_ORDER: Dict[str, List[str]] = {
    "diabetes": ["age", "gender", "bmi", "hba1c", "fasting_glucose", "smoking_status", "family_diabetes"],
    "cvd":      ["age", "gender", "total_cholesterol", "systolic_bp", "bmi", "smoking_status", "diabetes"],
    "hypertension": ["age", "gender", "bmi", "smoking_status", "diabetes"],
}

# Human-readable prompt for each missing field
_FIELD_PROMPTS: Dict[str, str] = {
    "age":               "How old are you? (e.g. 45)",
    "gender":            "What is your biological sex? (male / female)",
    "bmi":               "Do you know your BMI? If not, I can estimate it — what is your height (cm) and weight (kg)?",
    "hba1c":             "Do you have a recent HbA1c result? (e.g. 5.7%)",
    "fasting_glucose":   "Do you know your fasting blood glucose? (mg/dL)",
    "total_cholesterol": "Do you know your total cholesterol level? (mg/dL)",
    "systolic_bp":       "What is your systolic blood pressure? (the top number, e.g. 130 mmHg)",
    "smoking_status":    "Do you smoke? (never / former / current)",
    "diabetes":          "Have you been diagnosed with diabetes? (yes / no)",
    "family_diabetes":   "Does anyone in your immediate family have diabetes? (yes / no)",
    "waist_circumference": "What is your waist circumference? (cm)",
}


class ConversationManager:
    """
    Turn-by-turn conversation handler.

    Call `handle_message(session_id, message)` for each user turn.
    Returns a plain-text bot reply.
    """

    def __init__(self):
        self._response_gen = ResponseGenerator()

    # ── Public API ────────────────────────────────────────────────────────────

    def handle_message(self, session_id: Optional[str], message: str) -> Dict[str, Any]:
        """
        Process one user message and return a response dict:

        {
          "session_id": str,
          "reply":      str,        # text to display to the user
          "assessment_complete": bool,
          "result":     dict | None # prediction result if just completed
        }
        """
        session = session_store.get_or_create(session_id)
        session.add_message("user", message)

        # Always try to extract entities, even during intent routing
        entities = extract_entities(message)
        if entities:
            session.update_metrics(entities)
            logger.debug("Entities extracted: %s", entities)

        # Classify intent
        intent = classify_intent(message)
        logger.info("Session %s | Intent: %s (%.2f) | Entities: %s",
                    session.session_id, intent.name, intent.confidence, list(entities.keys()))

        reply, result = self._route(session, intent, message, entities)

        session.add_message("assistant", reply)

        return {
            "session_id": session.session_id,
            "reply": reply,
            "assessment_complete": result is not None,
            "result": result,
        }

    # ── Routing ───────────────────────────────────────────────────────────────

    def _route(
        self,
        session: Session,
        intent: Intent,
        message: str,
        entities: Dict[str, Any],
    ) -> Tuple[str, Optional[Dict]]:
        """Return (reply_text, result_dict_or_None)."""

        name = intent.name

        # ── Greet ──
        if name == "greet":
            return self._response_gen.greeting(), None

        # ── Help ──
        if name == "help":
            return self._response_gen.help_message(), None

        # ── Starting a specific assessment ──
        if name in ("assess_diabetes", "assess_cvd", "assess_hypertension"):
            condition = name.replace("assess_", "")
            # Low-confidence match (keyword only, no explicit "check/assess/risk" trigger)
            # while a session is already active → treat as metric provision, not a new assessment.
            if session.active_assessment and intent.confidence < 0.90:
                return self._collect_or_predict(session), None
            session.clear_metrics()           # resets active_assessment — must come first
            session.active_assessment = condition
            if entities:
                session.update_metrics(entities)
            first_q = self._collect_or_predict(session)
            intro = self._response_gen.condition_intro(condition)
            return f"{intro}\n\n{first_q}", None

        # ── Unknown assessment type — ask ──
        if name == "assess_unknown":
            session.active_assessment = None
            return self._response_gen.ask_condition(), None

        # ── User is providing a value mid-flow ──
        if name == "provide_metric" or (entities and session.active_assessment):
            if session.active_assessment:
                return self._collect_or_predict(session), None
            return self._response_gen.no_active_assessment(), None

        # ── Follow-up on last result ──
        if name == "ask_about_result":
            if session.last_result:
                return self._response_gen.explain_result(
                    session.last_assessment_type, session.last_result
                ), None
            return self._response_gen.no_previous_result(), None

        # ── Recommendations ──
        if name == "ask_for_recommendation":
            if session.last_result:
                return self._response_gen.recommendations_summary(
                    session.last_assessment_type, session.last_result
                ), None
            return self._response_gen.no_previous_result(), None

        # ── If we have an active assessment, keep collecting ──
        if session.active_assessment:
            return self._collect_or_predict(session), None

        return self._response_gen.unknown_intent(), None

    # ── Data collection / prediction ─────────────────────────────────────────

    def _collect_or_predict(self, session: Session) -> str:
        """
        Either ask for the next missing field or run the prediction
        if we have enough data.
        """
        condition = session.active_assessment
        if not condition:
            return self._response_gen.ask_condition()

        # Derive BMI from height+weight if both are present but bmi is missing
        m = session.metrics
        if "bmi" not in m and "height" in m and "weight" in m:
            h, w = m["height"], m["weight"]
            if h > 0:
                calculated = round(w / ((h / 100) ** 2), 1)
                if 10.0 <= calculated <= 80.0:
                    session.update_metrics({"bmi": calculated})

        # Check all required fields
        missing_required = [
            f for f in _REQUIRED[condition] if f not in session.metrics
        ]
        if missing_required:
            return self._response_gen.ask_for_field(condition, missing_required[0])

        # Check that at least one useful field is present (beyond age+gender)
        min_useful = _MINIMUM_USEFUL[condition]
        if min_useful and not any(f in session.metrics for f in min_useful):
            # Ask for the first one
            next_field = min_useful[0]
            return self._response_gen.ask_for_field(condition, next_field)

        # We have enough — run prediction
        return self._run_prediction(session)

    def _run_prediction(self, session: Session) -> str:
        """Call the appropriate prediction service and format a reply."""
        condition = session.active_assessment
        metrics = dict(session.metrics)

        try:
            result = self._call_service(condition, metrics)
            session.store_result(condition, result)

            reply = self._response_gen.assessment_result(condition, result)
            # Offer to go deeper
            reply += "\n\n" + self._response_gen.offer_followup()
            return reply

        except Exception as e:
            logger.error("Prediction failed for %s: %s", condition, e, exc_info=True)
            return self._response_gen.prediction_error(condition)

    def _call_service(self, condition: str, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Delegate to the correct prediction service."""
        if condition == "diabetes":
            from src.api.services.prediction_service import prediction_service
            result = prediction_service.predict(metrics, include_explanation=True)
            result["recommendations"] = prediction_service.generate_recommendations(metrics, result)
            return result

        if condition == "cvd":
            from src.api.services.cvd_prediction_service import cvd_prediction_service
            result = cvd_prediction_service.predict(metrics, include_explanation=True)
            result["recommendations"] = cvd_prediction_service.generate_recommendations(metrics, result)
            return result

        if condition == "hypertension":
            from src.api.services.hypertension_prediction_service import hypertension_prediction_service
            result = hypertension_prediction_service.predict(metrics, include_explanation=True)
            result["recommendations"] = hypertension_prediction_service.generate_recommendations(metrics, result)
            return result

        raise ValueError(f"Unknown condition: {condition}")
