/* useAssessment — state machine for the structured Assessment Wizard. */

import { useState, useCallback } from 'react';
import { runStructuredAssessment, getAssessmentQuestions } from '../utils/api';

// Demographic answers paired with each demo so CohortComparison can render
const DEMO_ANSWERS = {
  diabetes:     { age: 54, gender: 'male' },
  cvd:          { age: 57, gender: 'male' },
  hypertension: { age: 49, gender: 'female' },
};

// Pre-built high-risk demo results — used to showcase explainability
const DEMO_RESULTS = {
  diabetes: {
    risk: { risk_category: 'Very High', risk_probability: 0.81 },
    explanation: {
      top_risk_factors: [
        { feature: 'hba1c', shap_value: 0.62, feature_value: 8.2 },
        { feature: 'fasting_glucose', shap_value: 0.48, feature_value: 145 },
        { feature: 'bmi', shap_value: 0.41, feature_value: 33.5 },
        { feature: 'family_diabetes', shap_value: 0.35, feature_value: 1 },
        { feature: 'sedentary_minutes', shap_value: 0.28, feature_value: 480 },
        { feature: 'sugar_intake', shap_value: 0.22, feature_value: 4 },
        { feature: 'age', shap_value: 0.18, feature_value: 54 },
      ],
      top_protective_factors: [
        { feature: 'diet_quality', shap_value: -0.09, feature_value: 3 },
        { feature: 'sleep_hours', shap_value: -0.06, feature_value: 7 },
      ],
    },
    recommendations: [
      { priority: 'high', category: 'blood_sugar', recommendation: 'Your HbA1c of 8.2% and fasting glucose of 145 mg/dL are significantly elevated. Consult your doctor about medication review and a structured diabetes management plan immediately.' },
      { priority: 'high', category: 'weight', recommendation: 'A BMI of 33.5 places you in the obese range. Even a 5–10% weight reduction can dramatically improve insulin sensitivity and blood sugar control.' },
      { priority: 'high', category: 'activity', recommendation: 'You are sedentary for 8+ hours daily. Aim for 30 minutes of brisk walking after meals — this is one of the most effective ways to lower post-meal blood sugar.' },
      { priority: 'medium', category: 'diet', recommendation: 'Significantly reduce refined carbohydrates, sugary drinks, and processed foods. A low-glycaemic-index diet can lower HbA1c by 0.5–1.5% within 3 months.' },
      { priority: 'medium', category: 'family_history', recommendation: 'With a family history of diabetes, genetic predisposition amplifies lifestyle risks. Regular 3-monthly HbA1c monitoring is strongly advised.' },
      { priority: 'medium', category: 'medical', recommendation: 'Ask your doctor about a referral to a diabetes prevention or management programme. Early structured intervention can prevent progression.' },
      { priority: 'low', category: 'sleep', recommendation: 'Maintaining 7–8 hours of consistent sleep supports hormonal balance and reduces cortisol-driven blood sugar spikes.' },
    ],
  },
  cvd: {
    risk: { risk_category: 'Very High', risk_probability: 0.76 },
    explanation: {
      top_risk_factors: [
        { feature: 'smoking_status', shap_value: 0.58, feature_value: 1 },
        { feature: 'total_cholesterol', shap_value: 0.45, feature_value: 260 },
        { feature: 'family_cvd', shap_value: 0.40, feature_value: 1 },
        { feature: 'systolic_bp', shap_value: 0.36, feature_value: 155 },
        { feature: 'bmi', shap_value: 0.30, feature_value: 31.2 },
        { feature: 'stress_level', shap_value: 0.24, feature_value: 5 },
        { feature: 'sedentary_minutes', shap_value: 0.19, feature_value: 420 },
      ],
      top_protective_factors: [
        { feature: 'hdl_cholesterol', shap_value: -0.11, feature_value: 38 },
        { feature: 'alcohol_use', shap_value: -0.07, feature_value: 1 },
      ],
    },
    recommendations: [
      { priority: 'high', category: 'smoking', recommendation: 'Smoking is your single largest cardiovascular risk factor. Quitting reduces heart disease risk by 50% within 1 year. Ask your GP about cessation support or varenicline therapy.' },
      { priority: 'high', category: 'cholesterol', recommendation: 'Total cholesterol of 260 mg/dL is high. Discuss statins with your doctor — they reduce cardiovascular events by 25–35% in high-risk individuals.' },
      { priority: 'high', category: 'blood_pressure', recommendation: 'A systolic BP of 155 mmHg significantly strains your heart and arteries. A combination of medication review, low-sodium diet, and exercise is essential.' },
      { priority: 'medium', category: 'family_history', recommendation: 'With a first-degree relative who had heart disease, your inherited risk is substantial. Annual lipid panels and BP checks are critical.' },
      { priority: 'medium', category: 'stress', recommendation: 'Chronic high stress elevates cortisol and adrenaline, directly raising BP and clotting risk. Consider mindfulness-based stress reduction or structured therapy.' },
      { priority: 'medium', category: 'activity', recommendation: 'Regular aerobic exercise (150 min/week) reduces cardiovascular mortality by 35%. Start with 20-minute daily walks and build gradually.' },
      { priority: 'low', category: 'diet', recommendation: 'Adopt a Mediterranean-style diet rich in oily fish, olive oil, nuts, and vegetables. This reduces cardiovascular events by ~30%.' },
    ],
  },
  hypertension: {
    risk: { risk_category: 'High', risk_probability: 0.68 },
    explanation: {
      top_risk_factors: [
        { feature: 'salt_intake', shap_value: 0.52, feature_value: 5 },
        { feature: 'bmi', shap_value: 0.44, feature_value: 30.8 },
        { feature: 'stress_level', shap_value: 0.38, feature_value: 4 },
        { feature: 'family_htn', shap_value: 0.34, feature_value: 1 },
        { feature: 'sedentary_minutes', shap_value: 0.26, feature_value: 390 },
        { feature: 'age', shap_value: 0.21, feature_value: 49 },
        { feature: 'alcohol_use', shap_value: 0.17, feature_value: 3 },
      ],
      top_protective_factors: [
        { feature: 'sleep_hours', shap_value: -0.10, feature_value: 7.5 },
        { feature: 'diet_quality', shap_value: -0.08, feature_value: 3 },
      ],
    },
    recommendations: [
      { priority: 'high', category: 'salt_intake', recommendation: 'Very high salt intake (>5g/day) is your strongest modifiable risk factor. Reducing to under 5g/day can lower systolic BP by 5–8 mmHg within weeks.' },
      { priority: 'high', category: 'weight', recommendation: 'Losing 5–10 kg can reduce systolic blood pressure by 5–10 mmHg. Even moderate weight loss significantly lowers hypertension risk.' },
      { priority: 'high', category: 'medical', recommendation: 'Get your blood pressure checked now. If readings are consistently above 130/80 mmHg, discuss treatment options with your doctor.' },
      { priority: 'medium', category: 'stress', recommendation: 'High stress activates the renin-angiotensin system, raising BP. Structured relaxation techniques, breathing exercises, or yoga can reduce systolic BP by 3–5 mmHg.' },
      { priority: 'medium', category: 'activity', recommendation: 'Regular moderate exercise (brisk walking, cycling) reduces systolic BP by 5–8 mmHg. Aim for at least 30 minutes on most days.' },
      { priority: 'medium', category: 'alcohol', recommendation: 'Alcohol directly raises blood pressure. Limiting to ≤14 units/week and having alcohol-free days can noticeably lower your BP.' },
      { priority: 'low', category: 'family_history', recommendation: 'With a family history of hypertension, annual home BP monitoring is strongly recommended. Early detection allows lifestyle intervention before medication is needed.' },
    ],
  },
};

export default function useAssessment(userId, profile) {
  const [step, setStep] = useState(0);
  const [condition, setCondition] = useState(null);
  const [questions, setQuestions] = useState({ steps: [] });
  const [answers, setAnswers] = useState({});
  const [result, setResult] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  // Pre-populate answers from stored profile
  const getInitialAnswers = useCallback((prof) => {
    if (!prof) return {};
    const a = {};
    if (prof.age) a.age = prof.age;
    if (prof.biological_sex) a.biological_sex = prof.biological_sex;
    if (prof.height_cm) a.height_cm = prof.height_cm;
    if (prof.weight_kg) a.weight_kg = prof.weight_kg;
    if (prof.bmi) a.bmi = prof.bmi;
    if (prof.activity_level) a.activity_level = prof.activity_level;
    if (prof.smoking_status) a.smoking_status = prof.smoking_status;
    if (prof.diet_quality) a.diet_quality = prof.diet_quality;
    if (prof.sleep_hours) a.sleep_hours = prof.sleep_hours;
    if (prof.alcohol_weekly) a.alcohol_weekly = prof.alcohol_weekly;
    if (prof.stress_level) a.stress_level = prof.stress_level;
    if (prof.salt_intake) a.salt_intake = prof.salt_intake;
    if (prof.sugar_intake) a.sugar_intake = prof.sugar_intake;
    if (prof.family_diabetes != null) a.family_diabetes = prof.family_diabetes;
    if (prof.family_cvd != null) a.family_cvd = prof.family_cvd;
    if (prof.family_htn != null) a.family_htn = prof.family_htn;
    return a;
  }, []);

  const selectCondition = useCallback(async (cond) => {
    setCondition(cond);
    setIsLoading(true);
    setError(null);
    try {
      const data = await getAssessmentQuestions(cond);
      setQuestions(data);
      setAnswers(getInitialAnswers(profile));
      setStep(1);
    } catch (e) {
      setError('Failed to load questions. Please try again.');
    } finally {
      setIsLoading(false);
    }
  }, [profile, getInitialAnswers]);

  const updateAnswers = useCallback((newAnswers) => {
    setAnswers((prev) => ({ ...prev, ...newAnswers }));
  }, []);

  const nextStep = useCallback(() => {
    const totalSteps = questions.steps?.length || 3;
    if (step < totalSteps) {
      setStep((s) => s + 1);
    }
  }, [step, questions]);

  const prevStep = useCallback(() => {
    if (step > 1) setStep((s) => s - 1);
    else if (step === 1) { setStep(0); setCondition(null); }
  }, [step]);

  const submit = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await runStructuredAssessment({
        condition,
        answers,
        user_id: userId,
        include_explanation: true,
        include_recommendations: true,
      });
      setResult(data);
      setStep((questions.steps?.length || 3) + 1); // results step
    } catch (e) {
      setError(e.message || 'Assessment failed. Please try again.');
    } finally {
      setIsLoading(false);
    }
  }, [condition, answers, userId, questions]);

  const reset = useCallback(() => {
    setStep(0);
    setCondition(null);
    setAnswers({});
    setResult(null);
    setError(null);
    setQuestions({ steps: [] });
  }, []);

  // Skip the wizard entirely and show a pre-built high-risk result
  const loadDemo = useCallback((cond) => {
    const demo = DEMO_RESULTS[cond];
    if (!demo) return;
    setCondition(cond);
    setResult(demo);
    setAnswers(DEMO_ANSWERS[cond] || {});
    setQuestions({ steps: [[], [], []] }); // 3 dummy steps so totalSteps = 3
    setStep(4); // results step = totalSteps + 1
    setError(null);
  }, []);

  return {
    step,
    condition,
    questions,
    answers,
    result,
    isLoading,
    error,
    selectCondition,
    updateAnswers,
    nextStep,
    prevStep,
    submit,
    reset,
    loadDemo,
  };
}
