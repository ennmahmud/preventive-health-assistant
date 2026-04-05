"""
Intent Classifier
=================
Rule-based intent classification for health chatbot messages.

Intents:
  greet               — hello / hi / hey
  assess_diabetes     — wants diabetes risk check
  assess_cvd          — wants CVD / heart risk check
  assess_hypertension — wants hypertension / blood pressure risk check
  provide_metric      — user is supplying a health value mid-conversation
  ask_about_result    — questions about a previous result
  ask_for_recommendation — wants advice / what should I do
  help                — what can you do / help
  unknown             — nothing matched
"""

import re
from dataclasses import dataclass
from typing import Tuple


@dataclass
class Intent:
    name: str
    confidence: float  # 0.0 – 1.0


# ── Keyword banks ────────────────────────────────────────────────────────────

_GREET_PATTERNS = re.compile(
    r"\b(hi|hello|hey|howdy|good (morning|afternoon|evening)|greetings|sup|what'?s up)\b",
    re.IGNORECASE,
)

_DIABETES_PATTERNS = re.compile(
    r"\b(diabet(es|ic)?|blood\s*sugar|glucose|hba1c|insulin|a1c)\b",
    re.IGNORECASE,
)

_CVD_PATTERNS = re.compile(
    # Note: blood pressure / BP keywords intentionally excluded — they belong to hypertension
    r"\b(cardio(vascular)?|heart\s*(disease|attack|risk|health)|cvd|coronary|stroke|cholesterol"
    r"|framingham|cardiac|myocardial)\b",
    re.IGNORECASE,
)

_HYPERTENSION_PATTERNS = re.compile(
    # Owns all BP-related keywords; checked BEFORE CVD in classify_intent
    r"\b(hypertension|high\s*blood\s*pressure|blood\s*pressure|bp\b|systolic|diastolic|htn)\b",
    re.IGNORECASE,
)

_ASSESS_TRIGGER = re.compile(
    r"\b(check|assess|test|screen|evaluat|calculat|predict|risk|chance|likelihood|how (likely|at risk)"
    r"|am i (at risk|likely)|what('?s| is) my)\b",
    re.IGNORECASE,
)

_PROVIDE_METRIC_PATTERNS = re.compile(
    r"\b(i('?m| am)|my|mine|it'?s|its|the)\b.{0,40}"
    r"\b(age|bmi|weight|height|cholesterol|glucose|hba1c|a1c|blood pressure|bp|bmi|smoker|smoke"
    r"|diabetes|diabetic|sedentary|waist|hdl|triglyceride|systolic|diastolic)\b",
    re.IGNORECASE,
)

_RESULT_PATTERNS = re.compile(
    r"\b(what does (it|that|this|the result) mean|explain|interpret|understand|tell me more"
    r"|what is (my|the) (risk|score|result|probability|chance))\b",
    re.IGNORECASE,
)

_RECOMMENDATION_PATTERNS = re.compile(
    r"\b(what (should|can|do) i|how (can|do) i|advice|recommend|suggest|tip|improve|lower|reduce"
    r"|prevent|lifestyle|what (to|should) do|help me)\b",
    re.IGNORECASE,
)

_HELP_PATTERNS = re.compile(
    r"\b(help|what can you (do|help)|commands|options|menu|features|capabilities|how (do|does) (this|it) work)\b",
    re.IGNORECASE,
)


# ── Classifier ───────────────────────────────────────────────────────────────

def classify_intent(message: str) -> Intent:
    """
    Classify the intent of a user message.

    Returns the best-matching Intent with a confidence score.
    Order matters: more specific patterns are checked first.
    """
    msg = message.strip()

    # --- Greet (only if short / no assessment trigger) ---
    if _GREET_PATTERNS.search(msg) and not _ASSESS_TRIGGER.search(msg):
        return Intent("greet", 0.90)

    # --- Condition-specific assessment intents ---
    has_assess = bool(_ASSESS_TRIGGER.search(msg))

    if _DIABETES_PATTERNS.search(msg):
        return Intent("assess_diabetes", 0.90 if has_assess else 0.70)

    # Hypertension checked before CVD: BP keywords (blood pressure, systolic, etc.)
    # belong to hypertension and must not be captured by the CVD branch.
    if _HYPERTENSION_PATTERNS.search(msg):
        return Intent("assess_hypertension", 0.90 if has_assess else 0.70)

    if _CVD_PATTERNS.search(msg):
        return Intent("assess_cvd", 0.90 if has_assess else 0.70)

    # --- Generic "check my health" → ask which condition ---
    if has_assess:
        return Intent("assess_unknown", 0.60)

    # --- Result / explanation ---
    if _RESULT_PATTERNS.search(msg):
        return Intent("ask_about_result", 0.85)

    # --- Recommendations ---
    if _RECOMMENDATION_PATTERNS.search(msg):
        return Intent("ask_for_recommendation", 0.85)

    # --- Providing a metric mid-conversation ---
    if _PROVIDE_METRIC_PATTERNS.search(msg):
        return Intent("provide_metric", 0.75)

    # --- Plain number/value — likely a metric response ---
    if re.match(r"^\s*[\d.]+\s*(%|mg|kg|cm|mmhg|mm hg)?\s*$", msg, re.IGNORECASE):
        return Intent("provide_metric", 0.80)

    # --- Help ---
    if _HELP_PATTERNS.search(msg):
        return Intent("help", 0.90)

    return Intent("unknown", 0.50)
