/* ChatWindow */

import { useEffect, useRef } from 'react';
import useChat from '../hooks/useChat';
import ChatMessage from './ChatMessage';
import ChatInput from './ChatInput';
import RiskResultCard from './RiskResultCard';
import styles from './ChatWindow.module.css';

const CONDITION_LABELS = {
  diabetes: '🩸 Diabetes',
  cvd: '❤️ Heart Disease',
  hypertension: '🫀 Hypertension',
};

const RISK_COLORS = {
  'Low': '#16a34a',
  'Moderate': '#ca8a04',
  'High': '#ea580c',
  'Very High': '#dc2626',
};

const CONTEXT_QUICK_STARTS = (condition) => [
  'Explain my result in detail',
  'What lifestyle changes should I make?',
  'How quickly can I reduce my risk?',
  `What causes ${condition === 'cvd' ? 'heart disease' : condition}?`,
];

const DEFAULT_QUICK_STARTS = [
  'Check my diabetes risk',
  'How is my heart health?',
  'Assess my hypertension risk',
];

export default function ChatWindow({
  userId = null,
  isReturningUser = false,
  assessmentContext = null,
  onClearAssessmentContext,
}) {
  const { messages, send, reset, isLoading, lastResult } = useChat(userId, assessmentContext);
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  const isEmpty = messages.length === 0;
  const condition = assessmentContext?.condition;
  const riskCategory = assessmentContext?.result?.risk?.risk_category;
  const riskPct = assessmentContext?.result?.risk?.risk_percentage
    ?? (assessmentContext?.result?.risk?.risk_probability ?? 0) * 100;

  return (
    <div className={styles.root}>
      {/* ── Header ── */}
      <header className={styles.header}>
        <span className={styles.logo}>🩺</span>
        <div>
          <h1 className={styles.title}>Health AI Assistant</h1>
          <p className={styles.subtitle}>XGBoost models · NHANES data · Claude explanations</p>
        </div>
        {messages.length > 0 && (
          <button className={styles.resetBtn} onClick={reset} title="Start over">
            ↺ New chat
          </button>
        )}
      </header>

      {/* ── Assessment context banner ── */}
      {assessmentContext && (
        <div
          className={styles.contextBanner}
          style={{ borderColor: RISK_COLORS[riskCategory] || '#5b8dee' }}
        >
          <div className={styles.contextLeft}>
            <span className={styles.contextLabel}>Assessment loaded:</span>
            <span className={styles.contextCondition}>
              {CONDITION_LABELS[condition] || condition}
            </span>
            <span
              className={styles.contextRisk}
              style={{ color: RISK_COLORS[riskCategory] || '#5b8dee' }}
            >
              {riskCategory} · {riskPct?.toFixed(1)}%
            </span>
          </div>
          <button
            className={styles.contextClear}
            onClick={onClearAssessmentContext}
            title="Remove assessment context"
          >
            ✕
          </button>
        </div>
      )}

      {/* ── Message list ── */}
      <div className={styles.messages}>
        {isEmpty ? (
          <Welcome
            onQuickStart={send}
            isReturningUser={isReturningUser}
            assessmentContext={assessmentContext}
            condition={condition}
            riskCategory={riskCategory}
            riskPct={riskPct}
          />
        ) : (
          <>
            {messages.map((msg) => (
              <div key={msg.id} className={styles.msgRow}>
                <ChatMessage message={msg} />
                {msg.role === 'assistant' && msg.assessmentComplete && msg.result && (
                  <div className={styles.cardRow}>
                    <RiskResultCard result={msg.result} />
                  </div>
                )}
              </div>
            ))}
            {isLoading && <TypingIndicator />}
            <div ref={bottomRef} />
          </>
        )}
      </div>

      {/* ── Input bar ── */}
      <ChatInput onSend={send} disabled={isLoading} />
    </div>
  );
}

// ── Sub-components ─────────────────────────────────────────────────────────

function Welcome({ onQuickStart, isReturningUser, assessmentContext, condition, riskCategory, riskPct }) {
  const hasContext = !!assessmentContext;
  const quickStarts = hasContext ? CONTEXT_QUICK_STARTS(condition) : DEFAULT_QUICK_STARTS;

  return (
    <div className={styles.welcome}>
      <div className={styles.welcomeEmoji}>🩺</div>

      {hasContext ? (
        <>
          <h2>Ready to explain your results</h2>
          <div
            className={styles.contextCard}
            style={{ borderColor: RISK_COLORS[riskCategory] || '#5b8dee' }}
          >
            <div className={styles.contextCardTitle}>
              {CONDITION_LABELS[condition] || condition} Assessment
            </div>
            <div
              className={styles.contextCardRisk}
              style={{ color: RISK_COLORS[riskCategory] || '#5b8dee' }}
            >
              {riskCategory} Risk · {riskPct?.toFixed(1)}%
            </div>
            <p className={styles.contextCardHint}>
              I have your full result including risk factors and SHAP explanations.
              Ask me anything about it.
            </p>
          </div>
        </>
      ) : (
        <>
          <h2>{isReturningUser ? 'Welcome back!' : 'How can I help you today?'}</h2>
          {isReturningUser && (
            <div className={styles.returningBanner}>
              ✅ Your profile is loaded — I&apos;ll skip questions you&apos;ve already answered.
            </div>
          )}
          <p>
            I assess your risk for <strong>diabetes</strong>,{' '}
            <strong>cardiovascular disease</strong>, and{' '}
            <strong>hypertension</strong> using lifestyle questions — no lab tests needed.
          </p>
        </>
      )}

      <div className={styles.quickStarts}>
        {quickStarts.map((q) => (
          <button key={q} className={styles.quickBtn} onClick={() => onQuickStart(q)}>
            {q}
          </button>
        ))}
      </div>

      <p className={styles.disclaimer}>
        For informational purposes only · Not a substitute for medical advice
      </p>
    </div>
  );
}

function TypingIndicator() {
  return (
    <div className={styles.typing}>
      <span /><span /><span />
    </div>
  );
}
