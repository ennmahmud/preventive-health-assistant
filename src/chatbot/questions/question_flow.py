"""
Question Flow Manager
=====================
Determines which question to ask next during a consultation,
respecting skip logic and profile pre-population.
"""

from typing import Any, Dict, List, Optional, TYPE_CHECKING

from src.chatbot.questions.question_bank import (
    QuestionDef,
    CONDITION_QUESTIONS,
    MINIMUM_REQUIRED,
    STRONGLY_RECOMMENDED,
)

if TYPE_CHECKING:
    from src.profile.models import UserProfile


class QuestionFlow:
    """Manages question ordering and skip logic for a consultation."""

    def get_next_question(
        self,
        condition: str,
        answered: Dict[str, Any],
        profile: Optional["UserProfile"] = None,
    ) -> Optional[QuestionDef]:
        """
        Returns the next unanswered required question, then recommended,
        then optional. Returns None when ready to predict.
        """
        questions = CONDITION_QUESTIONS.get(condition, [])
        profile_fields = self._profile_to_dict(profile) if profile else {}

        # Already-known fields: answered this session OR in stored profile
        known = {**profile_fields, **answered}

        for q in questions:
            # Skip if all skip_if_profile_has fields are present in known context
            if q.skip_if_profile_has and all(f in known for f in q.skip_if_profile_has):
                continue
            # Skip if this question's maps_to fields are already known
            if q.maps_to and all(f in known for f in q.maps_to):
                continue
            # Skip optional questions if we already have minimum + recommended
            if not q.required and self.is_ready_to_predict(condition, answered, profile):
                continue
            return q

        return None  # all questions answered or skipped

    def is_ready_to_predict(
        self,
        condition: str,
        answered: Dict[str, Any],
        profile: Optional["UserProfile"] = None,
    ) -> bool:
        """
        True when minimum required fields are present AND at least one
        strongly-recommended field is answered.
        """
        known = {**self._profile_to_dict(profile), **answered}

        # Must have all minimum required fields
        for f in MINIMUM_REQUIRED.get(condition, []):
            if f not in known:
                return False

        # Must have at least one strongly-recommended field for a meaningful result
        recommended = STRONGLY_RECOMMENDED.get(condition, [])
        if recommended and not any(f in known for f in recommended):
            return False

        return True

    def get_wizard_steps(
        self,
        condition: str,
        profile: Optional["UserProfile"] = None,
    ) -> List[List[QuestionDef]]:
        """
        Returns questions grouped into wizard steps:
          Step 0: demographics (layer 0)
          Step 1: shared lifestyle (layer 1)
          Step 2: condition-specific (layer 2)
        """
        questions = CONDITION_QUESTIONS.get(condition, [])
        profile_fields = self._profile_to_dict(profile) if profile else {}
        steps: List[List[QuestionDef]] = [[], [], []]

        for q in questions:
            # Skip pre-populated from profile
            if q.skip_if_profile_has and all(f in profile_fields for f in q.skip_if_profile_has):
                continue
            idx = min(q.layer, 2)
            steps[idx].append(q)

        # Remove empty steps
        return [s for s in steps if s]

    @staticmethod
    def _profile_to_dict(profile: Optional["UserProfile"]) -> Dict[str, Any]:
        """Flatten a UserProfile into a dict of known fields."""
        if not profile:
            return {}
        result: Dict[str, Any] = {}
        fields_map = {
            "age": profile.age,
            "gender": profile.biological_sex,
            "bmi": profile.bmi,
            "activity_level": profile.activity_level,
            "smoking_status": profile.smoking_status,
            "diet_quality": profile.diet_quality,
            "sleep_hours": profile.sleep_hours,
            "alcohol_weekly": profile.alcohol_weekly,
            "stress_level": profile.stress_level,
            "salt_intake": profile.salt_intake,
            "sugar_intake": profile.sugar_intake,
            "family_diabetes": profile.family_diabetes,
            "family_cvd": profile.family_cvd,
            "family_htn": profile.family_htn,
            "diabetes": None,  # not stored at profile level
        }
        for k, v in fields_map.items():
            if v is not None:
                result[k] = v
        return result


question_flow = QuestionFlow()
