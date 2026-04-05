"""
Profile Service
===============
Orchestrates ProfileStore (SQLite) + ProfileRAGStore (ChromaDB).
All API routes and the ConversationManager use this — never the stores directly.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from src.profile.models import UserProfile, AssessmentResult
from src.profile.store import ProfileStore
from src.profile.rag_store import ProfileRAGStore, ProfileContext

logger = logging.getLogger(__name__)


# Lifestyle answer key → UserProfile field
_ANSWER_TO_PROFILE: Dict[str, str] = {
    "age": "age",
    "gender": "biological_sex",
    "height": "height_cm",
    "weight": "weight_kg",
    "bmi": "bmi",
    "activity_level": "activity_level",
    "smoking_status": "smoking_status",
    "diet_quality": "diet_quality",
    "sleep_hours": "sleep_hours",
    "alcohol_weekly": "alcohol_weekly",
    "stress_level": "stress_level",
    "salt_intake": "salt_intake",
    "sugar_intake": "sugar_intake",
    "family_diabetes": "family_diabetes",
    "family_cvd": "family_cvd",
    "family_htn": "family_htn",
    "prediabetes_flag": "prediabetes_flag",
}


class ProfileService:
    def __init__(self, store: Optional[ProfileStore] = None, rag: Optional[ProfileRAGStore] = None):
        self._store = store or ProfileStore()
        self._rag = rag

    # ── Profile CRUD ──────────────────────────────────────────────────────────

    def get_profile(self, user_id: str) -> Optional[UserProfile]:
        try:
            return self._store.get_profile(user_id)
        except Exception as e:
            logger.error("get_profile failed: %s", e)
            return None

    def get_or_create_profile(self, user_id: str) -> UserProfile:
        profile = self.get_profile(user_id)
        if not profile:
            profile = UserProfile(user_id=user_id)
            self._store.upsert_profile(profile)
        return profile

    def delete_profile(self, user_id: str) -> bool:
        try:
            ok = self._store.delete_profile(user_id)
            if ok and self._rag:
                self._rag.delete_profile(user_id)
            return ok
        except Exception as e:
            logger.error("delete_profile failed: %s", e)
            return False

    # ── Profile Updates ───────────────────────────────────────────────────────

    def update_profile_from_answers(
        self, user_id: str, answers: Dict[str, Any]
    ) -> UserProfile:
        """Merge lifestyle answers into the stored profile."""
        profile = self.get_or_create_profile(user_id)

        for answer_key, profile_field in _ANSWER_TO_PROFILE.items():
            val = answers.get(answer_key)
            if val is not None:
                setattr(profile, profile_field, val)

        # Derive BMI if we have height + weight
        if profile.height_cm and profile.weight_kg and not profile.bmi:
            h = float(profile.height_cm)
            w = float(profile.weight_kg)
            if h > 0:
                derived = round(w / ((h / 100) ** 2), 1)
                if 10.0 <= derived <= 80.0:
                    profile.bmi = derived

        profile.updated_at = datetime.utcnow()
        saved = self._store.upsert_profile(profile)

        # Re-index in ChromaDB
        if self._rag:
            try:
                doc_id = self._rag.index_profile(saved)
                if doc_id:
                    saved.chroma_doc_id = doc_id
                    self._store.upsert_profile(saved)
            except Exception as e:
                logger.warning("RAG index failed: %s", e)

        return saved

    def update_profile_from_result(
        self, user_id: str, condition: str, result: Dict[str, Any]
    ) -> UserProfile:
        """Store risk result against the user's profile."""
        profile = self.get_or_create_profile(user_id)

        risk = result.get("risk", {})
        prob = risk.get("risk_probability")
        if prob is not None:
            if condition == "diabetes":
                profile.last_diabetes_risk = float(prob)
            elif condition == "cvd":
                profile.last_cvd_risk = float(prob)
            elif condition == "hypertension":
                profile.last_htn_risk = float(prob)

        profile.last_assessment_date = datetime.utcnow()
        profile.assessments_completed = (profile.assessments_completed or 0) + 1
        profile.updated_at = datetime.utcnow()

        saved = self._store.upsert_profile(profile)

        if self._rag:
            try:
                doc_id = self._rag.index_profile(saved)
                if doc_id:
                    saved.chroma_doc_id = doc_id
                    self._store.upsert_profile(saved)
            except Exception as e:
                logger.warning("RAG index after result failed: %s", e)

        return saved

    # ── RAG Context ───────────────────────────────────────────────────────────

    def get_rag_context(
        self, user_id: str, condition: Optional[str] = None
    ) -> Optional["ProfileContext"]:
        """
        Returns a ProfileContext for a returning user, with pre-populated fields
        and a welcome message. Returns None for new users.
        """
        profile = self.get_profile(user_id)
        if not profile:
            return None

        # Build pre-populated fields from profile
        pre_pop: Dict[str, Any] = {}
        if profile.age:
            pre_pop["age"] = profile.age
        if profile.biological_sex:
            pre_pop["gender"] = profile.biological_sex
        if profile.bmi:
            pre_pop["bmi"] = profile.bmi
        elif profile.height_cm and profile.weight_kg:
            pre_pop["height"] = profile.height_cm
            pre_pop["weight"] = profile.weight_kg
        if profile.activity_level:
            pre_pop["activity_level"] = profile.activity_level
        if profile.smoking_status:
            pre_pop["smoking_status"] = profile.smoking_status
        if profile.diet_quality:
            pre_pop["diet_quality"] = profile.diet_quality
        if profile.sleep_hours:
            pre_pop["sleep_hours"] = profile.sleep_hours
        if profile.alcohol_weekly:
            pre_pop["alcohol_weekly"] = profile.alcohol_weekly
        if profile.stress_level:
            pre_pop["stress_level"] = profile.stress_level
        if profile.salt_intake:
            pre_pop["salt_intake"] = profile.salt_intake
        if profile.sugar_intake:
            pre_pop["sugar_intake"] = profile.sugar_intake
        if profile.family_diabetes is not None:
            pre_pop["family_diabetes"] = profile.family_diabetes
        if profile.family_cvd is not None:
            pre_pop["family_cvd"] = profile.family_cvd
        if profile.family_htn is not None:
            pre_pop["family_htn"] = profile.family_htn

        # Risk summary
        risk_parts = []
        if profile.last_diabetes_risk is not None:
            risk_parts.append(f"diabetes {profile.last_diabetes_risk*100:.0f}%")
        if profile.last_cvd_risk is not None:
            risk_parts.append(f"CVD {profile.last_cvd_risk*100:.0f}%")
        if profile.last_htn_risk is not None:
            risk_parts.append(f"hypertension {profile.last_htn_risk*100:.0f}%")
        risk_summary = ("Previous risk scores: " + ", ".join(risk_parts)) if risk_parts else None

        # Welcome message
        parts = []
        if profile.age:
            parts.append(f"age {profile.age}")
        if profile.biological_sex:
            parts.append(profile.biological_sex)
        if len(pre_pop) >= 3:
            greeting = (
                f"Welcome back! I already have your profile on record "
                f"({', '.join(parts[:2]) if parts else 'returning user'}) — "
                "I'll skip questions you've already answered."
            )
        else:
            greeting = "Welcome back! I have some of your information from last time."

        return ProfileContext(
            pre_populated_fields=pre_pop,
            welcome_message=greeting,
            questions_to_skip=[],
            last_risk_summary=risk_summary,
        )

    # ── Assessment History ────────────────────────────────────────────────────

    def save_assessment(
        self,
        user_id: str,
        session_id: Optional[str],
        condition: str,
        answers: Dict[str, Any],
        result: Dict[str, Any],
    ) -> None:
        try:
            risk = result.get("risk", {})
            ar = AssessmentResult(
                user_id=user_id,
                session_id=session_id,
                condition=condition,
                risk_probability=risk.get("risk_probability", 0.0),
                risk_category=risk.get("risk_category", "Unknown"),
                raw_result=result,
                lifestyle_inputs=answers,
            )
            self._store.save_assessment(ar)
        except Exception as e:
            logger.error("save_assessment failed: %s", e)

    def get_assessment_history(
        self, user_id: str, limit: int = 10
    ) -> List[AssessmentResult]:
        try:
            return self._store.get_assessment_history(user_id, limit)
        except Exception as e:
            logger.error("get_assessment_history failed: %s", e)
            return []


# Singleton — RAG disabled (profile context served from SQLite; ChromaDB/
# sentence-transformers init is synchronous and blocks the event loop on
# first request, causing 30-second hangs.  All retrieval paths already use
# SQLite directly via get_rag_context(), so no functionality is lost.)
profile_service = ProfileService(store=ProfileStore(), rag=None)
