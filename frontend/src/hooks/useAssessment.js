/**
 * useAssessment — state machine for the structured Assessment Wizard.
 *
 * Steps:
 *   0 — condition selection
 *   1 — demographics (age, sex, height/weight)
 *   2 — shared lifestyle
 *   3 — condition-specific questions
 *   4 — results display
 */

import { useState, useCallback } from 'react';
import { runStructuredAssessment, getAssessmentQuestions } from '../utils/api';

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
  };
}
