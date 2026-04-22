import { useEffect } from 'react';
import useAssessment from '../hooks/useAssessment';
import ConditionSelector from './ConditionSelector';
import StepProgressBar from './StepProgressBar';
import AssessmentStep from './AssessmentStep';
import AssessmentResults from './AssessmentResults';
import styles from './AssessmentWizard.module.css';

export default function AssessmentWizard({
  userId, profile, isReturningUser,
  onSwitchToChat, onResultReady,
}) {
  const {
    step, condition, questions, answers, result,
    isLoading, error,
    selectCondition, updateAnswers, nextStep, prevStep, submit, reset, loadDemo,
  } = useAssessment(userId, profile);

  const totalSteps = questions.steps?.length || 3;
  const isResultStep = step > totalSteps;

  // Notify App when a real result is ready (not a demo — demos have no lifestyle_answers)
  useEffect(() => {
    if (isResultStep && result && onResultReady) {
      onResultReady(condition, result, answers);
    }
  }, [isResultStep, result]); // eslint-disable-line react-hooks/exhaustive-deps

  // "Continue in Chat" — switch tab AND the result is already shared via onResultReady
  const handleContinueChat = () => {
    onSwitchToChat();
  };

  // Step 0 — condition selection
  if (step === 0) {
    return (
      <div className={styles.wizard}>
        <div className={styles.header}>
          <h2>Health Risk Assessment</h2>
          <p className={styles.subtitle}>
            Answer a few lifestyle questions — no lab tests or medical knowledge needed.
          </p>
          {isReturningUser && (
            <div className={styles.returningBanner}>
              ✅ Welcome back! We'll pre-fill your previous answers.
            </div>
          )}
        </div>
        <ConditionSelector onSelect={selectCondition} onDemo={loadDemo} isLoading={isLoading} />
        {error && <div className={styles.error}>{error}</div>}
      </div>
    );
  }

  // Results step
  if (isResultStep && result) {
    return (
      <div className={styles.wizard}>
        <AssessmentResults
          result={result}
          condition={condition}
          answers={answers}
          onStartNew={reset}
          onContinueChat={handleContinueChat}
        />
      </div>
    );
  }

  // Question steps 1–N
  const stepIndex = step - 1;
  const currentStepQuestions = questions.steps?.[stepIndex] || [];
  const isLastStep = step === totalSteps;
  const stepLabels = ['Demographics', 'Lifestyle', 'Health History'];

  return (
    <div className={styles.wizard}>
      <div className={styles.header}>
        <div className={styles.conditionBadge}>{conditionLabel(condition)}</div>
        <StepProgressBar
          current={step}
          total={totalSteps}
          labels={stepLabels.slice(0, totalSteps)}
        />
      </div>

      {error && <div className={styles.error}>{error}</div>}

      <div className={styles.stepContent}>
        {isLoading ? (
          <div className={styles.loading}>Loading…</div>
        ) : (
          <AssessmentStep
            questions={currentStepQuestions}
            answers={answers}
            onChange={updateAnswers}
          />
        )}
      </div>

      <div className={styles.nav}>
        <button className={styles.backBtn} onClick={prevStep} disabled={isLoading}>
          ← Back
        </button>
        {isLastStep ? (
          <button
            className={styles.submitBtn}
            onClick={submit}
            disabled={isLoading}
          >
            {isLoading ? 'Analysing…' : 'Get My Results →'}
          </button>
        ) : (
          <button
            className={styles.nextBtn}
            onClick={nextStep}
            disabled={isLoading || currentStepQuestions.filter(q => q.required).some(
              q => !q.maps_to.some(f => f in answers)
            )}
          >
            Next →
          </button>
        )}
      </div>
    </div>
  );
}

function conditionLabel(c) {
  return { diabetes: '🩸 Diabetes', cvd: '❤️ Heart Disease', hypertension: '🫀 Hypertension' }[c] || c;
}
