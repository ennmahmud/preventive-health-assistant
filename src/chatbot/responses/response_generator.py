"""
Response Generator
==================
Plain-language response templates for the health chatbot.

All responses are intentionally brief and conversational.
Medical results always include a disclaimer.
"""

from typing import Any, Dict, List, Optional

_DISCLAIMER = (
    "_Disclaimer: This is a screening tool, not medical advice. "
    "Always consult a qualified healthcare professional._"
)


# ── Risk narrative helpers ────────────────────────────────────────────────────

_RISK_EMOJI = {
    "Low": "🟢",
    "Moderate": "🟡",
    "High": "🟠",
    "Very High": "🔴",
}

_CONDITION_NAMES = {
    "diabetes": "diabetes",
    "cvd": "cardiovascular disease (CVD)",
    "hypertension": "hypertension",
}

_PLAIN_FACTOR_NAMES: Dict[str, str] = {
    "hba1c":                  "blood sugar (HbA1c)",
    "fasting_glucose":        "fasting blood sugar",
    "bmi":                    "body weight (BMI)",
    "age":                    "age",
    "total_cholesterol":      "total cholesterol",
    "hdl_cholesterol":        "HDL (good cholesterol)",
    "systolic_bp":            "blood pressure",
    "sedentary_minutes":      "sedentary time",
    "vigorous_rec_minutes":   "vigorous exercise",
    "moderate_rec_minutes":   "moderate exercise",
    "walk_minutes":           "daily walking",
    "smoking_status":         "smoking history",
    "smoked_100":             "smoking history",
    "alcohol_use":            "alcohol intake",
    "diet_quality":           "diet quality",
    "salt_intake":            "salt intake",
    "sleep_hours":            "sleep",
    "stress_level":           "stress level",
    "family_diabetes":        "family history of diabetes",
    "family_cvd":             "family history of heart disease",
    "family_htn":             "family history of hypertension",
    "waist_circumference":    "waist circumference",
    "sugar_intake":           "sugar intake",
    "diabetes":               "diabetes diagnosis",
    "self_reported_hbp":      "high blood pressure history",
    "self_reported_hchol":    "high cholesterol history",
}

_RISK_NARRATIVES: Dict[str, Dict[str, str]] = {
    "diabetes": {
        "Low":      "Your lifestyle profile suggests a low risk of developing type 2 diabetes. Keep up your healthy habits.",
        "Moderate": "Some risk factors are present. Small diet and activity changes can meaningfully lower your risk.",
        "High":     "Several risk factors are elevated. Talk to your doctor about blood sugar monitoring and lifestyle changes.",
        "Very High":"Multiple significant risk factors detected. Please consult a healthcare professional soon.",
    },
    "cvd": {
        "Low":      "Your cardiovascular risk looks low based on your lifestyle profile. Stay active and keep monitoring.",
        "Moderate": "Some cardiovascular risk factors are present. Focus on diet, exercise, and stress management.",
        "High":     "Your heart disease risk is elevated. A consultation with your doctor is strongly recommended.",
        "Very High":"Multiple serious risk factors detected. Please seek medical advice as soon as possible.",
    },
    "hypertension": {
        "Low":      "Your risk of developing high blood pressure appears low. Maintaining your current habits is key.",
        "Moderate": "Some factors increase your hypertension risk. Reducing salt, managing stress, and staying active will help.",
        "High":     "Your hypertension risk is elevated. A blood pressure check and lifestyle review with your doctor is advised.",
        "Very High":"You have multiple significant risk factors for hypertension. Please see a healthcare professional soon.",
    },
}

_FIELD_PROMPTS: Dict[str, str] = {
    "age":               "How old are you?",
    "gender":            "What is your biological sex? (male / female)",
    "bmi":               "Do you know your BMI? If not, tell me your height (cm) and weight (kg) and I'll work it out.",
    "hba1c":             "What was your most recent HbA1c result? (e.g. 5.7%)",
    "fasting_glucose":   "What is your fasting blood glucose level? (mg/dL)",
    "total_cholesterol": "What is your total cholesterol level? (mg/dL)",
    "systolic_bp":       "What is your systolic blood pressure — the top number? (e.g. 130 mmHg)",
    "smoking_status":    "Do you smoke? (never / former / current)",
    "diabetes":          "Have you been diagnosed with diabetes? (yes / no)",
    "family_diabetes":   "Does anyone in your immediate family have diabetes? (yes / no)",
    "waist_circumference": "What is your waist circumference? (cm)",
}

_CONDITION_INTROS: Dict[str, str] = {
    "diabetes": (
        "Sure, let's check your diabetes risk. I'll need a few details — you can skip any you don't know."
    ),
    "cvd": (
        "Let's assess your cardiovascular disease risk. I'll ask a few questions — "
        "share what you know and I'll work with what's available."
    ),
    "hypertension": (
        "Let's look at your hypertension risk. I'll ask about your age, weight, and lifestyle — "
        "not your actual blood pressure reading. "
        "This is a **preventive** model: it predicts your risk of *developing* hypertension "
        "based on modifiable risk factors, so you can act before your BP rises."
    ),
}


class ResponseGenerator:
    """Generates natural-language responses for each conversation state."""

    # ── Greetings / misc ──────────────────────────────────────────────────────

    def greeting(self) -> str:
        return (
            "Hi there! I'm your Preventive Health Assistant. 👋\n\n"
            "I can assess your risk for:\n"
            "• **Diabetes** — based on your lifestyle, diet, and family history\n"
            "• **Cardiovascular disease (CVD)** — heart attack and stroke risk\n"
            "• **Hypertension** — your risk of developing high blood pressure\n\n"
            "I'll ask you plain questions — no lab tests or medical knowledge needed.\n\n"
            "What would you like to check? Or try the **Assessment** tab for a step-by-step form."
        )

    def help_message(self) -> str:
        return (
            "Here's what I can do:\n\n"
            "• **Diabetes risk check** — *\"Check my diabetes risk\"*\n"
            "• **CVD / heart risk check** — *\"Assess my heart health\"*\n"
            "• **Hypertension risk check** — *\"Check my blood pressure risk\"*\n\n"
            "During an assessment I'll ask for your age, gender, and a few health metrics. "
            "You can skip anything you don't know.\n\n"
            "After a result you can ask:\n"
            "• *\"What does that mean?\"* — for an explanation\n"
            "• *\"What should I do?\"* — for personalised recommendations"
        )

    def ask_condition(self) -> str:
        return (
            "I can help with risk checks for **diabetes**, **CVD (heart disease)**, or **hypertension**.\n"
            "Which one would you like to assess?"
        )

    def unknown_intent(self) -> str:
        return (
            "I'm not sure I understood that. I can help you check your risk for "
            "**diabetes**, **CVD**, or **hypertension**. "
            "Type *help* to see what I can do."
        )

    def no_active_assessment(self) -> str:
        return (
            "It looks like we haven't started an assessment yet. "
            "Would you like to check your risk for **diabetes**, **CVD**, or **hypertension**?"
        )

    def no_previous_result(self) -> str:
        return (
            "I don't have a previous result for this session. "
            "Would you like to start an assessment? "
            "I can check your risk for **diabetes**, **CVD**, or **hypertension**."
        )

    def prediction_error(self, condition: str) -> str:
        return (
            f"Sorry, I wasn't able to complete the {_CONDITION_NAMES.get(condition, condition)} "
            "assessment right now. The model may not be trained yet. "
            f"Please run the training script and try again."
        )

    # ── Data collection ───────────────────────────────────────────────────────

    def condition_intro(self, condition: str) -> str:
        return _CONDITION_INTROS.get(condition, f"Let's assess your {condition} risk.")

    def ask_for_field(self, condition: str, field: str) -> str:
        prompt = _FIELD_PROMPTS.get(field, f"Could you tell me your {field.replace('_', ' ')}?")
        return prompt

    def ask_lifestyle_question(self, question: Any) -> str:
        """Format a QuestionDef as a conversational prompt with option hints."""
        text = question.text
        # For choice/yes_no questions, append compact option hint if not already in text
        if question.response_type in ("choice", "yes_no") and question.options:
            if "\n•" not in text and "\n*" not in text:
                opts = " / ".join(f"*{o}*" for o in question.options)
                text = f"{text}\n\n({opts})"
        elif question.response_type == "scale":
            text = f"{text}\n\nReply with a number from 1 to 5."
        elif question.response_type == "numeric" and question.unit_hint:
            text = f"{text} ({question.unit_hint})"
        return text

    def welcome_back(self, welcome_message: str, risk_summary: Optional[str] = None) -> str:
        """Returning-user greeting injected before the condition intro."""
        msg = welcome_message
        if risk_summary:
            msg += f"\n\n_{risk_summary}_"
        return msg

    # ── Results ───────────────────────────────────────────────────────────────

    def assessment_result(self, condition: str, result: Dict[str, Any]) -> str:
        """Format a prediction result as a rich, proactive conversational reply."""
        risk = result.get("risk", {})
        category = risk.get("risk_category", "Unknown")
        pct = risk.get("risk_percentage", 0.0)
        emoji = _RISK_EMOJI.get(category, "⚪")
        cond_name = _CONDITION_NAMES.get(condition, condition)

        lines = [
            f"**{cond_name.capitalize()} Risk Assessment** {emoji}",
            "",
            f"Your estimated risk: **{pct:.1f}%** — **{category} Risk**",
            "",
        ]

        # Plain-language narrative for this risk level
        narrative = _RISK_NARRATIVES.get(condition, {}).get(category, "")
        if narrative:
            lines += [narrative, ""]

        # Explain what's driving the risk (translated to plain English)
        exp = result.get("explanation")
        if exp:
            top_risks = exp.get("top_risk_factors", [])
            top_protect = exp.get("top_protective_factors", [])

            if top_risks:
                names = [_PLAIN_FACTOR_NAMES.get(f["feature"], f["feature"].replace("_", " ")) for f in top_risks[:3]]
                lines.append(f"**What's increasing your risk:** {', '.join(names)}")

            if top_protect:
                names = [_PLAIN_FACTOR_NAMES.get(f["feature"], f["feature"].replace("_", " ")) for f in top_protect[:3]]
                lines.append(f"**What's protecting you:** {', '.join(names)}")

            lines.append("")

        # Top recommendation (highest priority first)
        recs = result.get("recommendations", [])
        if recs:
            high = [r for r in recs if r.get("priority") == "high"]
            top_rec = (high or recs)[0]
            lines += [
                f"**Top action:** {top_rec.get('recommendation', '')}",
                "",
            ]

        lines.append(_DISCLAIMER)
        return "\n".join(lines)

    def explain_result(self, condition: str, result: Dict[str, Any]) -> str:
        """Explain what the last result means."""
        risk = result.get("risk", {})
        category = risk.get("risk_category", "Unknown")
        pct = risk.get("risk_percentage", 0.0)
        cond_name = _CONDITION_NAMES.get(condition, condition)

        explanations = {
            "Low": (
                f"A **Low** risk ({pct:.1f}%) means your current profile suggests a relatively low chance "
                f"of developing {cond_name} in the near term. Keep up your healthy habits!"
            ),
            "Moderate": (
                f"A **Moderate** risk ({pct:.1f}%) means some risk factors are present. "
                f"With lifestyle adjustments you can likely reduce this risk. "
                "Consider speaking with your doctor at your next check-up."
            ),
            "High": (
                f"A **High** risk ({pct:.1f}%) indicates several risk factors that need attention. "
                "I strongly recommend scheduling an appointment with your GP or a specialist."
            ),
            "Very High": (
                f"A **Very High** risk ({pct:.1f}%) means you have multiple significant risk factors. "
                "Please seek medical advice soon — early intervention makes a big difference."
            ),
        }

        base = explanations.get(category, f"Your {cond_name} risk is {category} ({pct:.1f}%).")
        exp = result.get("explanation", {})
        if exp:
            summary = exp.get("summary", "")
            if summary:
                base += f"\n\n{summary}"

        return base + f"\n\n{_DISCLAIMER}"

    def recommendations_summary(self, condition: str, result: Dict[str, Any]) -> str:
        """Summarise recommendations from the last result."""
        recs = result.get("recommendations", [])
        if not recs:
            return (
                "I don't have specific recommendations stored for this result. "
                "For personalised advice, please consult a healthcare professional."
            )

        cond_name = _CONDITION_NAMES.get(condition, condition)
        lines = [f"**Recommendations to lower your {cond_name} risk:**", ""]

        high = [r for r in recs if r.get("priority") == "high"]
        medium = [r for r in recs if r.get("priority") == "medium"]
        low = [r for r in recs if r.get("priority") == "low"]

        for r in (high + medium + low)[:5]:
            priority_label = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(r.get("priority", "low"), "•")
            lines.append(f"{priority_label} **{r.get('category', '').capitalize()}:** {r.get('recommendation', '')}")

        lines.append("")
        lines.append(_DISCLAIMER)
        return "\n".join(lines)

    def offer_followup(self) -> str:
        return (
            "Want to dig deeper? Ask me:\n"
            "• *\"Explain my result\"* — full breakdown of what each factor means\n"
            "• *\"What should I do?\"* — all personalised recommendations\n"
            "• *\"Check my heart risk\"* / *\"Diabetes risk\"* / *\"Hypertension risk\"* — start another assessment"
        )
