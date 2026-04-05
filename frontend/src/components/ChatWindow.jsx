/**
 * ChatWindow
 * Main chat UI — scrollable message list + input bar.
 */

import { useEffect, useRef } from 'react';
import useChat from '../hooks/useChat';
import ChatMessage from './ChatMessage';
import ChatInput from './ChatInput';
import RiskResultCard from './RiskResultCard';
import styles from './ChatWindow.module.css';

const QUICK_STARTS = [
  'Check my diabetes risk',
  'How is my heart health?',
  'Assess my hypertension risk',
];

export default function ChatWindow({ userId = null, isReturningUser = false }) {
  const { messages, send, reset, isLoading, lastResult } = useChat(userId);
  const bottomRef = useRef(null);

  // Auto-scroll to latest message
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  const isEmpty = messages.length === 0;

  return (
    <div className={styles.root}>
      {/* ── Header ── */}
      <header className={styles.header}>
        <span className={styles.logo}>🩺</span>
        <div>
          <h1 className={styles.title}>Preventive Health Assistant</h1>
          <p className={styles.subtitle}>Powered by XGBoost · NHANES data</p>
        </div>
        {messages.length > 0 && (
          <button className={styles.resetBtn} onClick={reset} title="Start over">
            ↺ New chat
          </button>
        )}
      </header>

      {/* ── Message list ── */}
      <div className={styles.messages}>
        {isEmpty ? (
          <Welcome onQuickStart={send} isReturningUser={isReturningUser} />
        ) : (
          <>
            {messages.map((msg) => (
              <div key={msg.id} className={styles.msgRow}>
                <ChatMessage message={msg} />
                {/* Show result card inline after the assistant's result reply */}
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

function Welcome({ onQuickStart, isReturningUser }) {
  return (
    <div className={styles.welcome}>
      <div className={styles.welcomeEmoji}>🩺</div>
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
      <div className={styles.quickStarts}>
        {QUICK_STARTS.map((q) => (
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
      <span />
      <span />
      <span />
    </div>
  );
}
