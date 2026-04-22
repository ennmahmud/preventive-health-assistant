# Claude Health AI Service — Wraps the Anthropic Claude API to power intelligent, contextual explanations.

import logging
import os
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Plain-English factor names (shared with frontend)
_FACTOR_NAMES: Dict[str, str] = {
    "hba1c": "blood sugar (HbA1c)",
    "fasting_glucose": "fasting blood sugar",
    "bmi": "body weight (BMI)",
    "age": "age",
    "total_cholesterol": "total cholesterol",
    "hdl_cholesterol": "HDL (good cholesterol)",
    "systolic_bp": "blood pressure",
    "sedentary_minutes": "sedentary time",
    "vigorous_rec_minutes": "vigorous exercise",
    "moderate_rec_minutes": "moderate exercise",
    "walk_minutes": "daily walking",
    "smoking_status": "smoking history",
    "smoked_100": "smoking history",
    "alcohol_use": "alcohol intake",
    "diet_quality": "diet quality",
    "salt_intake": "salt intake",
    "sleep_hours": "sleep duration",
    "stress_level": "stress level",
    "family_diabetes": "family history of diabetes",
    "family_cvd": "family history of heart disease",
    "family_htn": "family history of hypertension",
    "waist_circumference": "waist circumference",
    "sugar_intake": "sugar intake",
    "diabetes": "diabetes diagnosis",
    "self_reported_hbp": "blood pressure history",
    "self_reported_hchol": "cholesterol history",
    "gender": "sex",
    "race_ethnicity": "ethnicity",
    "income_ratio": "socioeconomic status",
    "education": "education level",
    "diabetes_indicator": "diabetes risk marker",
}

_CONDITION_NAMES = {
    "diabetes": "Type 2 Diabetes",
    "cvd": "Cardiovascular Disease (CVD)",
    "hypertension": "Hypertension (High Blood Pressure)",
}


def _plain_name(feature: str) -> str:
    return _FACTOR_NAMES.get(feature, feature.replace("_", " "))


class ClaudeHealthService:
    """Intelligent health explanation and conversation service powered by Claude."""

    _SYSTEM_PROMPT = (
        "You are an expert preventive health coach embedded in a lifestyle risk "
        "assessment app. You explain medical risk assessments in plain English, "
        "offer actionable lifestyle advice, and always remind users to consult a "
        "healthcare professional for medical decisions. Be warm, concise, and "
        "evidence-based. Never diagnose or prescribe."
    )

    def __init__(self):
        self._available = False
        self._client = None
        self._model = "claude-3-haiku-20240307"
        try:
            import anthropic

            api_key = os.environ.get("ANTHROPIC_API_KEY")
            if api_key:
                self._client = anthropic.Anthropic(api_key=api_key)
                self._available = True
                logger.info("Claude Health Service initialised (model=%s)", self._model)
            else:
                logger.warning("ANTHROPIC_API_KEY not set — Claude features disabled")
        except ImportError:
            logger.warning("anthropic package not installed — Claude features disabled")

    # Explanation generation

    def explain_result(
        self,
        condition: str,
        result: Dict[str, Any],
        lifestyle_answers: Optional[Dict[str, Any]] = None,
        user_question: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> Optional[str]:
        """Generate a personalised explanation of a risk assessment result."""
        if not self._available:
            return None

        context = self._build_context(condition, result, lifestyle_answers)
        prompt = (
            f"{context}\n\n---\n"
            f"Explain this result in plain English. "
            f"Cover: what the risk level means, what's driving it, and 2-3 specific "
            f"actions the person can take. Keep it under 200 words."
        )
        if user_question:
            prompt += f'\n\nThe user specifically asked: "{user_question}"'

        messages = list(conversation_history or [])
        messages.append({"role": "user", "content": prompt})

        return self._call(messages, max_tokens=400)

    def answer_question(
        self,
        question: str,
        assessment_context: Optional[Dict[str, Any]] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        lifestyle_answers: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """Answer a free-form health question, optionally using assessment context."""
        if not self._available:
            return None

        messages = list(conversation_history or [])

        if assessment_context:
            condition = assessment_context.get("condition", "")
            result = assessment_context.get("result", {})
            context = self._build_context(condition, result, lifestyle_answers)
            prompt = f"{context}\n\n---\nUser question: {question}"
        else:
            prompt = question

        messages.append({"role": "user", "content": prompt})
        return self._call(messages, max_tokens=400)

    def generate_lifestyle_plan(
        self,
        condition: str,
        result: Dict[str, Any],
        lifestyle_answers: Optional[Dict[str, Any]] = None,
        focus_area: Optional[str] = None,
    ) -> Optional[str]:
        """Generate a personalised, actionable lifestyle improvement plan."""
        if not self._available:
            return None

        context = self._build_context(condition, result, lifestyle_answers)
        focus_clause = ""
        if focus_area:
            focus_clause = f"Focus especially on **{focus_area}**."

        prompt = f"""{context}

---
Create a personalised 4-week lifestyle improvement plan for this person.
{focus_clause}

Structure your response as:
## Your 4-Week Lifestyle Plan

**Week 1 — Foundation:** [2-3 specific, easy changes]
**Week 2 — Build:** [add 1-2 more habits]
**Week 3 — Momentum:** [reinforce + add challenge]
**Week 4 — Solidify:** [make it sustainable]

**Key targets to track:**
[3-4 measurable outcomes]

Keep each action specific, realistic, and linked to the risk factors identified."""

        return self._call([{"role": "user", "content": prompt}], max_tokens=700)

    def explain_trend(
        self,
        condition: str,
        previous_result: Dict[str, Any],
        current_result: Dict[str, Any],
        time_period: str = "since last check",
    ) -> Optional[str]:
        """Explain what changed between two assessment results and why it matters."""
        if not self._available:
            return None

        prev_risk = previous_result.get("risk", {})
        curr_risk = current_result.get("risk", {})
        prev_pct = prev_risk.get("risk_percentage", 0)
        curr_pct = curr_risk.get("risk_percentage", 0)
        delta = abs(curr_pct - prev_pct)
        direction = "improved (decreased)" if curr_pct < prev_pct else "increased"

        prompt = f"""A user re-assessed their {_CONDITION_NAMES.get(condition, condition)} risk.

Previous result: {prev_pct:.1f}% ({prev_risk.get('risk_category', '')})
Current result:  {curr_pct:.1f}% ({curr_risk.get('risk_category', '')})
Change: {direction} by {delta:.1f} percentage points over {time_period}

Explain:
1. What this change means clinically (is this meaningful? how long to see more?)
2. What likely drove this change (based on what we know about the condition)
3. What to do next to continue the trend (or reverse it if negative)

Be specific and encouraging. 3-4 short paragraphs."""

        return self._call([{"role": "user", "content": prompt}], max_tokens=400)

    # Internal helpers

    def _build_context(
        self,
        condition: str,
        result: Dict[str, Any],
        lifestyle_answers: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Build a structured context block for Claude from a risk result."""
        condition_name = _CONDITION_NAMES.get(condition, condition)
        risk = result.get("risk", {})
        parts = [
            f"Condition: {condition_name}",
            f"Risk: {risk.get('risk_percentage', 0):.1f}% — {risk.get('risk_category', 'Unknown')}",
        ]

        exp = result.get("explanation", {})
        if exp:
            top_risk = exp.get("top_risk_factors", [])
            top_protect = exp.get("top_protective_factors", [])
            if top_risk:
                names = [_plain_name(f["feature"]) for f in top_risk[:4]]
                parts.append(f"Top risk factors: {', '.join(names)}")
            if top_protect:
                names = [_plain_name(f["feature"]) for f in top_protect[:3]]
                parts.append(f"Protective factors: {', '.join(names)}")

        if lifestyle_answers:
            ls = self._format_lifestyle(lifestyle_answers)
            if ls:
                parts.append(f"Lifestyle: {ls}")

        return "\n".join(parts)

    def _format_lifestyle(self, answers: Dict[str, Any]) -> str:
        """Convert raw lifestyle answers into a readable summary."""
        parts = []
        mappings = [
            ("exercise_frequency", "exercise"),
            ("diet_quality", "diet"),
            ("smoking_status", "smoking"),
            ("alcohol_use", "alcohol"),
            ("sleep_hours", "sleep"),
            ("stress_level", "stress"),
            ("salt_intake", "salt intake"),
            ("sugar_intake", "sugar intake"),
        ]
        for key, label in mappings:
            val = answers.get(key)
            if val is not None:
                parts.append(f"{label}: {val}")
        return "; ".join(parts)

    def _call(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 300,
        system: Optional[str] = None,
    ) -> Optional[str]:
        """Make a Claude API call with error handling."""
        try:
            response = self._client.messages.create(
                model=self._model,
                max_tokens=max_tokens,
                system=system or self._SYSTEM_PROMPT,
                messages=messages,
            )
            return response.content[0].text.strip()
        except Exception as e:
            logger.error("Claude API call failed: %s", e)
            return None


# Module-level singleton
claude_service = ClaudeHealthService()
