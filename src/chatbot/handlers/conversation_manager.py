"""
Conversation Manager
====================
Orchestrates multi-turn chatbot consultations using lifestyle-based questions.

A normal person doesn't know their HbA1c, cholesterol, or systolic BP.
This manager collects lifestyle and medical history information through
plain-English questions, maps the answers to model features via the
LifestyleFeatureMapper, and runs the prediction when enough is known.

Flow:
  1. User signals intent → bot introduces the assessment
  2. For returning users: profile is loaded → pre-populate known answers
  3. Bot asks lifestyle questions (activity, diet, family history, etc.)
  4. User answers (free text or structured choices)
  5. When minimum data is collected → run prediction → return result
  6. User can ask for explanation or recommendations
  7. Results and lifestyle profile are persisted for future sessions
"""

import logging
import sys
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from src.chatbot.intents.classifier import classify_intent, Intent
from src.chatbot.intents.entities import extract_entities
from src.chatbot.handlers.session import Session, session_store
from src.chatbot.responses.response_generator import ResponseGenerator
from src.chatbot.questions.question_bank import QuestionDef
from src.chatbot.questions.question_flow import question_flow
from src.lifestyle.answer_normalizer import answer_normalizer
from src.lifestyle.feature_mapper import lifestyle_mapper

logger = logging.getLogger(__name__)


class ConversationManager:
    """
    Turn-by-turn conversation handler.

    Call `handle_message(session_id, message, user_id)` for each turn.
    Returns a response dict.
    """

    def __init__(self):
        self._response_gen = ResponseGenerator()

    # ── Public API ────────────────────────────────────────────────────────────

    def handle_message(
        self,
        session_id: Optional[str],
        message: str,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Process one user message and return:
        {
          "session_id": str,
          "reply": str,
          "assessment_complete": bool,
          "result": dict | None,
          "profile_updated": bool,
        }
        """
        session = session_store.get_or_create(session_id)
        session.add_message("user", message)

        # Attach user_id if provided (first time or reconnect)
        if user_id and not session.user_id:
            session.user_id = user_id
            # Inject profile context for returning users
            self._inject_profile_context(session)

        # Extract clinical entities (age, gender, BMI, explicit lab values)
        entities = extract_entities(message)
        if entities:
            session.update_metrics(entities)
            # Also lift demographic entities into lifestyle_answers
            for k in ("age", "gender", "height", "weight", "bmi",
                      "smoking_status", "family_diabetes"):
                if k in entities:
                    session.lifestyle_answers[k] = entities[k]

        # Extract lifestyle signals from free text
        lifestyle = answer_normalizer.normalize_all_lifestyle(message)
        if lifestyle:
            session.update_lifestyle(lifestyle)

        # Handle yes/no for the current question
        if session.active_assessment:
            self._handle_yes_no_for_current_question(session, message)

        # Classify intent
        intent = classify_intent(message)
        logger.info(
            "Session %s | UserID %s | Intent: %s (%.2f) | Entities: %s | Lifestyle: %s",
            session.session_id, session.user_id,
            intent.name, intent.confidence,
            list(entities.keys()), list(lifestyle.keys()),
        )

        reply, result = self._route(session, intent, message, entities)
        session.add_message("assistant", reply)

        profile_updated = False
        if result and session.user_id:
            self._persist_result(session, result)
            profile_updated = True

        return {
            "session_id": session.session_id,
            "reply": reply,
            "assessment_complete": result is not None,
            "result": result,
            "profile_updated": profile_updated,
        }

    # ── Profile injection ─────────────────────────────────────────────────────

    def _inject_profile_context(self, session: Session) -> None:
        """Load the user's stored profile into the session."""
        try:
            from src.profile.profile_service import profile_service
            ctx = profile_service.get_rag_context(session.user_id)
            if not ctx:
                return
            # Pre-populate lifestyle answers from profile
            if ctx.pre_populated_fields:
                session.profile_context = {
                    "welcome_message": ctx.welcome_message,
                    "last_risk_summary": ctx.last_risk_summary,
                }
                session.update_lifestyle(ctx.pre_populated_fields)
                # Also merge into clinical metrics (age, gender, bmi)
                for k in ("age", "gender", "bmi", "height", "weight"):
                    if k in ctx.pre_populated_fields:
                        session.metrics[k] = ctx.pre_populated_fields[k]
        except Exception as e:
            logger.warning("Profile context injection failed: %s", e)

    # ── Routing ───────────────────────────────────────────────────────────────

    def _route(
        self,
        session: Session,
        intent: Intent,
        message: str,
        entities: Dict[str, Any],
    ) -> Tuple[str, Optional[Dict]]:
        name = intent.name

        if name == "greet":
            # Personalise greeting for returning users
            if session.profile_context:
                wm = session.profile_context.get("welcome_message", "")
                rs = session.profile_context.get("last_risk_summary")
                reply = self._response_gen.greeting()
                if wm:
                    reply = wm + "\n\n" + reply
                if rs:
                    reply += f"\n\n_{rs}_"
                return reply, None
            return self._response_gen.greeting(), None

        if name == "help":
            return self._response_gen.help_message(), None

        # Starting a specific assessment
        if name in ("assess_diabetes", "assess_cvd", "assess_hypertension"):
            condition = name.replace("assess_", "")
            # Low-confidence keyword match during active session → treat as metric answer
            if session.active_assessment and intent.confidence < 0.90:
                return self._collect_or_predict(session), None
            # Start fresh assessment
            session.clear_metrics()
            session.active_assessment = condition
            # Re-inject profile context (cleared by clear_metrics)
            if session.user_id:
                self._inject_profile_context(session)
            # Merge any entities just extracted
            if entities:
                session.update_metrics(entities)
                for k in ("age", "gender", "height", "weight", "bmi"):
                    if k in entities:
                        session.lifestyle_answers[k] = entities[k]
            first_q = self._collect_or_predict(session)
            intro = self._response_gen.condition_intro(condition)
            # Add returning-user note if applicable
            if session.profile_context:
                wm = session.profile_context.get("welcome_message", "")
                if wm and "Welcome back" in wm:
                    intro = wm + "\n\n" + intro
            return f"{intro}\n\n{first_q}", None

        if name == "assess_unknown":
            session.active_assessment = None
            return self._response_gen.ask_condition(), None

        if name == "provide_metric" or (
            (entities or lifestyle_answers_changed(session, message)) and session.active_assessment
        ):
            if session.active_assessment:
                return self._collect_or_predict(session), None
            return self._response_gen.no_active_assessment(), None

        if name == "ask_about_result":
            if session.last_result:
                return self._response_gen.explain_result(
                    session.last_assessment_type, session.last_result
                ), None
            return self._response_gen.no_previous_result(), None

        if name == "ask_for_recommendation":
            if session.last_result:
                return self._response_gen.recommendations_summary(
                    session.last_assessment_type, session.last_result
                ), None
            return self._response_gen.no_previous_result(), None

        if session.active_assessment:
            return self._collect_or_predict(session), None

        return self._response_gen.unknown_intent(), None

    # ── Question collection and prediction ───────────────────────────────────

    def _collect_or_predict(self, session: Session) -> str:
        """Ask the next lifestyle question or run prediction when ready."""
        condition = session.active_assessment
        if not condition:
            return self._response_gen.ask_condition()

        # Load profile for skip-logic
        profile = None
        if session.user_id:
            try:
                from src.profile.profile_service import profile_service
                profile = profile_service.get_profile(session.user_id)
            except Exception:
                pass

        # All answers known so far (lifestyle + some clinical from entities)
        all_answers = {**session.lifestyle_answers, **session.metrics}

        # Check if ready to predict
        if question_flow.is_ready_to_predict(condition, all_answers, profile):
            return self._run_prediction(session, profile)

        # Get next question to ask
        next_q = question_flow.get_next_question(condition, all_answers, profile)
        if not next_q:
            # No more questions but minimum not met — try anyway
            return self._run_prediction(session, profile)

        # Track which question is "current" (for yes/no detection)
        session.asked_question_ids.append(next_q.id)
        return self._response_gen.ask_lifestyle_question(next_q)

    def _handle_yes_no_for_current_question(
        self, session: Session, message: str
    ) -> None:
        """
        If the last question asked was a yes_no type and the user just
        answered yes/no, parse it and store the answer.
        """
        if not session.asked_question_ids:
            return
        last_qid = session.asked_question_ids[-1]

        from src.chatbot.questions.question_bank import CONDITION_QUESTIONS
        condition = session.active_assessment
        questions = CONDITION_QUESTIONS.get(condition, [])
        current_q = next((q for q in questions if q.id == last_qid), None)
        if not current_q or current_q.response_type not in ("yes_no", "choice"):
            return

        # Try to match option
        answer_key = self._match_option(message, current_q)
        if answer_key and current_q.maps_to:
            for field in current_q.maps_to:
                # Resolve yes/no to bool for flag fields
                val: Any = answer_key
                if answer_key == "yes":
                    val = True
                elif answer_key == "no":
                    val = False
                elif answer_key == "unknown":
                    val = None
                if val is not None:
                    session.lifestyle_answers[field] = val

    def _match_option(self, message: str, question: QuestionDef) -> Optional[str]:
        """Match a user's free text answer to one of the question's option_keys."""
        if not question.option_keys or not question.options:
            return None
        msg = message.lower().strip()
        for i, (option, key) in enumerate(zip(question.options, question.option_keys)):
            if (
                option.lower() in msg
                or key.lower() in msg
                or (len(msg) <= 3 and str(i + 1) in msg)
            ):
                return key
        # Generic yes/no fallback
        yn = answer_normalizer.normalize_yes_no(message)
        if yn in (question.option_keys or []):
            return yn
        return None

    def _run_prediction(self, session: Session, profile: Any) -> str:
        """Map lifestyle answers to features, call prediction service, return reply."""
        condition = session.active_assessment
        all_answers = {**session.lifestyle_answers, **session.metrics}

        try:
            features = self._map_features(condition, all_answers, profile)
            result = self._call_service(condition, features)
            session.store_result(condition, result)

            reply = self._response_gen.assessment_result(condition, result)
            reply += "\n\n" + self._response_gen.offer_followup()
            return reply

        except Exception as e:
            logger.error("Prediction failed for %s: %s", condition, e, exc_info=True)
            return self._response_gen.prediction_error(condition)

    def _map_features(
        self, condition: str, answers: Dict[str, Any], profile: Any
    ) -> Dict[str, Any]:
        """Translate lifestyle answers to model-ready feature dict."""
        if condition == "diabetes":
            return lifestyle_mapper.map_for_diabetes(answers, profile)
        if condition == "cvd":
            return lifestyle_mapper.map_for_cvd(answers, profile)
        if condition == "hypertension":
            return lifestyle_mapper.map_for_hypertension(answers, profile)
        raise ValueError(f"Unknown condition: {condition}")

    def _call_service(self, condition: str, features: Dict[str, Any]) -> Dict[str, Any]:
        """Delegate to the correct prediction service."""
        if condition == "diabetes":
            from src.api.services.prediction_service import prediction_service
            result = prediction_service.predict(features, include_explanation=True)
            result["recommendations"] = prediction_service.generate_recommendations(features, result)
            return result

        if condition == "cvd":
            from src.api.services.cvd_prediction_service import cvd_prediction_service
            result = cvd_prediction_service.predict(features, include_explanation=True)
            result["recommendations"] = cvd_prediction_service.generate_recommendations(features, result)
            return result

        if condition == "hypertension":
            from src.api.services.hypertension_prediction_service import hypertension_prediction_service
            result = hypertension_prediction_service.predict(features, include_explanation=True)
            result["recommendations"] = hypertension_prediction_service.generate_recommendations(features, result)
            return result

        raise ValueError(f"Unknown condition: {condition}")

    def _persist_result(self, session: Session, result: Dict[str, Any]) -> None:
        """Save result and update profile for logged-in users."""
        if not session.user_id or not session.last_assessment_type:
            return
        try:
            from src.profile.profile_service import profile_service
            answers = {**session.lifestyle_answers, **session.metrics}
            profile_service.update_profile_from_answers(session.user_id, answers)
            profile_service.update_profile_from_result(
                session.user_id, session.last_assessment_type, result
            )
            profile_service.save_assessment(
                session.user_id,
                session.session_id,
                session.last_assessment_type,
                answers,
                result,
            )
        except Exception as e:
            logger.error("Profile persist failed: %s", e)


# ── Helpers ───────────────────────────────────────────────────────────────────

def lifestyle_answers_changed(session: Session, message: str) -> bool:
    """True if new lifestyle info was likely provided."""
    keywords = [
        "active", "sedentary", "exercise", "walk", "sit", "diet", "eat", "food",
        "smoke", "stress", "sleep", "drink", "salt", "family", "diabetes", "heart",
        "healthy", "junk", "processed", "never", "rarely", "daily", "weekly",
    ]
    msg = message.lower()
    return any(kw in msg for kw in keywords)
