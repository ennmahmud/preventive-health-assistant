"""
Chatbot Unit Tests
==================
Unit tests for the intent classifier, entity extractor, and session store.
"""

import time
import pytest

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.chatbot.intents.classifier import classify_intent, Intent
from src.chatbot.intents.entities import extract_entities
from src.chatbot.handlers.session import Session, SessionStore


# ═══════════════════════════════════════════════════════════════
# INTENT CLASSIFIER
# ═══════════════════════════════════════════════════════════════

class TestIntentClassifier:

    # ── Greet ──
    def test_hi_is_greet(self):
        assert classify_intent("hi").name == "greet"

    def test_hello_is_greet(self):
        assert classify_intent("Hello there!").name == "greet"

    def test_good_morning_is_greet(self):
        assert classify_intent("Good morning").name == "greet"

    # ── Diabetes ──
    def test_check_diabetes_risk(self):
        assert classify_intent("check my diabetes risk").name == "assess_diabetes"

    def test_blood_sugar_is_diabetes(self):
        assert classify_intent("assess my blood sugar").name == "assess_diabetes"

    def test_hba1c_is_diabetes(self):
        assert classify_intent("what is my HbA1c risk?").name == "assess_diabetes"

    def test_a1c_is_diabetes(self):
        assert classify_intent("my a1c is elevated").name == "assess_diabetes"

    # ── CVD ──
    def test_heart_disease_is_cvd(self):
        assert classify_intent("check my heart disease risk").name == "assess_cvd"

    def test_cardiovascular_is_cvd(self):
        assert classify_intent("assess cardiovascular risk").name == "assess_cvd"

    def test_cholesterol_is_cvd(self):
        assert classify_intent("my cholesterol is high, am I at risk?").name == "assess_cvd"

    def test_stroke_is_cvd(self):
        assert classify_intent("stroke risk assessment").name == "assess_cvd"

    # ── Hypertension (critical routing checks) ──
    def test_blood_pressure_is_hypertension_not_cvd(self):
        intent = classify_intent("check my blood pressure risk")
        assert intent.name == "assess_hypertension", (
            f"Expected assess_hypertension, got {intent.name}. "
            "blood pressure keywords must route to hypertension."
        )

    def test_hypertension_explicit(self):
        assert classify_intent("hypertension risk check").name == "assess_hypertension"

    def test_htn_abbreviation(self):
        assert classify_intent("I want to check for htn").name == "assess_hypertension"

    def test_systolic_is_hypertension(self):
        assert classify_intent("my systolic is high").name == "assess_hypertension"

    def test_high_blood_pressure_is_hypertension(self):
        intent = classify_intent("am I at risk for high blood pressure?")
        assert intent.name == "assess_hypertension"

    # ── Generic assess (no condition specified) ──
    def test_generic_health_check_is_unknown_assess(self):
        assert classify_intent("check my health").name == "assess_unknown"

    def test_what_is_my_risk_is_ask_about_result(self):
        # "what is my risk?" asks about an existing result, not to start a new assessment
        assert classify_intent("what is my risk?").name == "ask_about_result"

    # ── Result / recommendation ──
    def test_what_does_that_mean(self):
        assert classify_intent("what does that mean?").name == "ask_about_result"

    def test_explain_result(self):
        assert classify_intent("can you explain my result?").name == "ask_about_result"

    def test_what_should_i_do(self):
        assert classify_intent("what should I do?").name == "ask_for_recommendation"

    def test_how_can_i_improve(self):
        assert classify_intent("how can I improve my health?").name == "ask_for_recommendation"

    # ── Provide metric ──
    def test_plain_number_is_provide_metric(self):
        assert classify_intent("42").name == "provide_metric"

    def test_number_with_unit_is_provide_metric(self):
        assert classify_intent("28.5 kg").name == "provide_metric"

    def test_my_bmi_is_provide_metric(self):
        assert classify_intent("my bmi is 28").name == "provide_metric"

    # ── Help ──
    def test_help_intent(self):
        assert classify_intent("help").name == "help"

    def test_what_can_you_do(self):
        assert classify_intent("what can you do?").name == "help"

    # ── Confidence ──
    def test_confident_assess_when_trigger_present(self):
        intent = classify_intent("check my diabetes risk")
        assert intent.confidence >= 0.85

    def test_lower_confidence_without_trigger(self):
        intent = classify_intent("diabetes")
        assert intent.confidence < 0.85

    # ── No false positives ──
    def test_random_text_is_unknown(self):
        assert classify_intent("xyzzy frobnicator 12345").name == "unknown"


# ═══════════════════════════════════════════════════════════════
# ENTITY EXTRACTOR
# ═══════════════════════════════════════════════════════════════

class TestEntityExtractor:

    # ── Age ──
    def test_age_explicit(self):
        assert extract_entities("my age is 45")["age"] == 45

    def test_age_natural(self):
        assert extract_entities("I am 45 years old")["age"] == 45

    def test_age_short(self):
        assert extract_entities("I'm 30")["age"] == 30

    def test_age_out_of_range_ignored(self):
        entities = extract_entities("I am 150 years old")
        assert "age" not in entities

    # ── Gender ──
    def test_male(self):
        assert extract_entities("I am male")["gender"] == "male"

    def test_female(self):
        assert extract_entities("I'm a woman")["gender"] == "female"

    def test_he_is_male(self):
        assert extract_entities("he is 45")["gender"] == "male"

    # ── BMI ──
    def test_bmi_simple(self):
        assert extract_entities("my bmi is 28.5")["bmi"] == 28.5

    def test_bmi_with_colon(self):
        assert extract_entities("BMI: 30")["bmi"] == 30.0

    # ── Weight / height ──
    def test_weight_kg(self):
        assert extract_entities("I weigh 80 kg")["weight"] == 80.0

    def test_height_cm(self):
        assert extract_entities("I am 175 cm tall")["height"] == 175.0

    # ── Cholesterol ──
    def test_total_cholesterol(self):
        assert extract_entities("my cholesterol is 210")["total_cholesterol"] == 210.0

    def test_hdl(self):
        assert extract_entities("HDL 55 mg")["hdl_cholesterol"] == 55.0

    def test_hdl_does_not_also_set_total(self):
        entities = extract_entities("my HDL is 55")
        assert entities.get("hdl_cholesterol") == 55.0
        # total_cholesterol should not be set to the same HDL number
        assert entities.get("total_cholesterol") != 55.0

    # ── HbA1c / Glucose ──
    def test_hba1c(self):
        assert extract_entities("HbA1c of 6.2%")["hba1c"] == 6.2

    def test_a1c(self):
        assert extract_entities("my a1c is 5.9")["hba1c"] == 5.9

    def test_fasting_glucose(self):
        assert extract_entities("fasting glucose 105 mg")["fasting_glucose"] == 105.0

    # ── Blood pressure ──
    def test_bp_pair(self):
        entities = extract_entities("bp is 130/85")
        assert entities["systolic_bp"] == 130.0
        assert entities["diastolic_bp"] == 85.0

    def test_blood_pressure_pair(self):
        entities = extract_entities("blood pressure 120/80")
        assert entities["systolic_bp"] == 120.0
        assert entities["diastolic_bp"] == 80.0

    def test_systolic_standalone(self):
        assert extract_entities("systolic is 135")["systolic_bp"] == 135.0

    def test_diastolic_standalone(self):
        assert extract_entities("diastolic 88")["diastolic_bp"] == 88.0

    # ── Smoking ──
    def test_current_smoker(self):
        assert extract_entities("I smoke")["smoking_status"] == "current"

    def test_former_smoker(self):
        assert extract_entities("I used to smoke")["smoking_status"] == "former"

    def test_never_smoker(self):
        assert extract_entities("I don't smoke")["smoking_status"] == "never"

    def test_non_smoker(self):
        assert extract_entities("non smoker")["smoking_status"] == "never"

    # ── Diabetes ──
    def test_has_diabetes(self):
        assert extract_entities("I have diabetes")["diabetes"] is True

    def test_no_diabetes(self):
        assert extract_entities("no diabetes")["diabetes"] is False

    def test_type2_diabetes(self):
        assert extract_entities("I have type 2 diabetes")["diabetes"] is True

    # ── Waist / sedentary ──
    def test_waist_circumference(self):
        assert extract_entities("waist 92 cm")["waist_circumference"] == 92.0

    def test_sedentary_minutes(self):
        assert extract_entities("sedentary 480 min")["sedentary_minutes"] == 480

    # ── Multiple entities in one message ──
    def test_multiple_entities(self):
        msg = "I'm 45, male, my BMI is 28.5 and I smoke"
        entities = extract_entities(msg)
        assert entities["age"] == 45
        assert entities["gender"] == "male"
        assert entities["bmi"] == 28.5
        assert entities["smoking_status"] == "current"

    # ── Empty ──
    def test_empty_message_returns_empty_dict(self):
        assert extract_entities("") == {}

    def test_no_health_content_returns_empty_dict(self):
        assert extract_entities("the weather is nice today") == {}


# ═══════════════════════════════════════════════════════════════
# SESSION STORE
# ═══════════════════════════════════════════════════════════════

class TestSessionStore:

    def test_creates_new_session(self):
        store = SessionStore()
        session = store.get_or_create()
        assert session is not None
        assert session.session_id is not None

    def test_returns_existing_session(self):
        store = SessionStore()
        s1 = store.get_or_create()
        s2 = store.get_or_create(s1.session_id)
        assert s1.session_id == s2.session_id

    def test_get_returns_none_for_missing(self):
        store = SessionStore()
        assert store.get("nonexistent-id") is None

    def test_delete_removes_session(self):
        store = SessionStore()
        s = store.get_or_create()
        store.delete(s.session_id)
        assert store.get(s.session_id) is None

    def test_active_count(self):
        store = SessionStore()
        store.get_or_create()
        store.get_or_create()
        assert store.active_count >= 2

    def test_cleanup_expired_removes_old_sessions(self):
        from datetime import timedelta
        store = SessionStore()
        s = store.get_or_create()
        # Manually backdating last_active to simulate expiry
        s.last_active = s.last_active - timedelta(minutes=35)
        removed = store.cleanup_expired()
        assert removed >= 1
        assert store.get(s.session_id) is None


class TestSession:

    def test_update_metrics(self):
        s = Session("test-1")
        s.update_metrics({"age": 45, "gender": "male"})
        assert s.metrics["age"] == 45
        assert s.metrics["gender"] == "male"

    def test_metrics_merged_not_replaced(self):
        s = Session("test-2")
        s.update_metrics({"age": 45})
        s.update_metrics({"gender": "female"})
        assert "age" in s.metrics
        assert "gender" in s.metrics

    def test_clear_metrics(self):
        s = Session("test-3")
        s.update_metrics({"age": 45})
        s.active_assessment = "diabetes"
        s.clear_metrics()
        assert s.metrics == {}
        assert s.active_assessment is None

    def test_add_message_increments_history(self):
        s = Session("test-4")
        s.add_message("user", "hello")
        s.add_message("assistant", "hi there")
        assert len(s.history) == 2

    def test_message_truncated_if_too_long(self):
        s = Session("test-5")
        long_msg = "x" * 10_000
        s.add_message("user", long_msg)
        stored = s.history[0]["content"]
        assert len(stored) < 10_000
        assert "truncated" in stored

    def test_history_capped_at_100_turns(self):
        s = Session("test-6")
        for i in range(120):
            s.add_message("user", f"msg {i}")
        assert len(s.history) <= 100

    def test_store_result(self):
        s = Session("test-7")
        result = {"risk": {"risk_category": "Low", "risk_percentage": 12.0}}
        s.store_result("diabetes", result)
        assert s.last_assessment_type == "diabetes"
        assert s.last_result == result

    def test_is_expired_false_for_new_session(self):
        s = Session("test-8")
        assert s.is_expired() is False

    def test_is_expired_true_after_ttl(self):
        from datetime import timedelta
        s = Session("test-9")
        s.last_active = s.last_active - timedelta(minutes=35)
        assert s.is_expired() is True

    def test_to_dict(self):
        s = Session("test-10")
        s.update_metrics({"age": 45})
        s.active_assessment = "cvd"
        d = s.to_dict()
        assert d["session_id"] == "test-10"
        assert "age" in d["collected_metrics"]
        assert d["active_assessment"] == "cvd"
