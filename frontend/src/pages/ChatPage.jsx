import { useState, useRef, useEffect, useCallback, useMemo } from 'react';
import {
  Send, RotateCcw, Stethoscope, Sparkles,
  Activity, HeartPulse, Salad, Brain, Moon,
} from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import TopBar from '../components/layout/TopBar';
import FloatingNav from '../components/layout/FloatingNav';
import useChat from '../hooks/useChat';
import { readLocal } from '../utils/assessmentHistory';

/* ── Read most-recent assessment from per-user cache (≤30 min old) ── */
function useRecentAssessment() {
  const [ctx, setCtx] = useState(() => {
    try {
      const stored = readLocal();
      if (!stored.length) return null;
      const latest = stored[0];
      if (Date.now() - latest.completedAt > 30 * 60 * 1000) return null;
      return latest;
    } catch { return null; }
  });
  const dismiss = useCallback(() => setCtx(null), []);
  return [ctx, dismiss];
}

/* ── Categorised quick-start prompts ─────────────────────────────── */
const PROMPT_CATEGORIES = [
  {
    label: 'Risk',
    icon: Activity,
    color: 'var(--elan-tc-400)',
    bg: 'var(--elan-tc-50)',
    border: 'var(--elan-tc-200)',
    prompts: [
      'What are my biggest diabetes risk factors?',
      'How does my risk compare to people my age?',
    ],
  },
  {
    label: 'Heart',
    icon: HeartPulse,
    color: 'var(--elan-tc-500)',
    bg: 'var(--elan-tc-50)',
    border: 'var(--elan-tc-200)',
    prompts: [
      'How can I improve my heart health?',
      'Explain my blood pressure reading.',
    ],
  },
  {
    label: 'Lifestyle',
    icon: Salad,
    color: 'var(--elan-sg-500)',
    bg: 'var(--elan-sg-50)',
    border: 'var(--elan-sg-200)',
    prompts: [
      'Build me a 30-day plan to lower my risk.',
      'What lifestyle changes lower hypertension?',
    ],
  },
  {
    label: 'Mind',
    icon: Brain,
    color: 'var(--elan-am-400)',
    bg: 'var(--elan-am-50)',
    border: 'var(--elan-am-200)',
    prompts: [
      'How does stress affect my health markers?',
    ],
  },
  {
    label: 'Sleep',
    icon: Moon,
    color: 'var(--elan-primary-bg)',
    bg: 'var(--elan-ch-50)',
    border: 'var(--elan-ch-200)',
    prompts: [
      'How does sleep impact my cardiovascular risk?',
    ],
  },
];

function contextualHero(ctx) {
  if (!ctx) {
    return {
      title: 'How can I help?',
      subtitle:
        "Ask me about your assessments, risk factors, or what lifestyle changes will make the biggest difference.",
      featured: [
        'What are my biggest diabetes risk factors?',
        'How can I improve my heart health?',
        'Build me a 30-day plan to lower my risk.',
        'Explain how lifestyle affects blood pressure.',
      ],
    };
  }
  const label = ctx.condition === 'cvd' ? 'heart disease'
    : ctx.condition === 'hypertension' ? 'hypertension'
    : 'diabetes';
  return {
    title: 'Let’s unpack your result.',
    subtitle: `I have your latest ${label} assessment loaded. Ask me anything about it — or pick a quick start.`,
    featured: [
      `Explain my ${label} result in simple terms.`,
      `What's the single most impactful change I can make?`,
      `How does my risk compare to someone my age?`,
      `Create a 30-day plan to lower my risk.`,
    ],
  };
}

/* ── Markdown styles injected once ──────────────────────────────── */
const MD_STYLES = `
  .elan-md { color: var(--elan-ch-800); }
  .elan-md p { margin: 0 0 0.65em; line-height: 1.65; }
  .elan-md p:last-child { margin-bottom: 0; }
  .elan-md strong { font-weight: 700; color: var(--elan-ch-700); }
  .elan-md em { font-style: italic; color: var(--elan-ch-700); }
  .elan-md ul, .elan-md ol { margin: 0.5em 0 0.7em 0; padding-left: 1.2em; }
  .elan-md li { margin-bottom: 0.35em; line-height: 1.6; }
  .elan-md li::marker { color: var(--elan-ch-500); }
  .elan-md code {
    font-family: var(--elan-mono); font-size: 0.85em;
    background: var(--elan-ch-100); color: var(--elan-ch-700);
    padding: 1px 6px; border-radius: var(--r-xs);
    border: 1px solid var(--elan-ch-200);
  }
  .elan-md pre {
    background: var(--elan-ch-50); border: 1px solid var(--elan-ch-200);
    border-radius: var(--r-md); padding: 12px 14px; overflow-x: auto;
    margin: 0.5em 0;
  }
  .elan-md pre code { background: transparent; border: none; padding: 0; }
  .elan-md h1, .elan-md h2, .elan-md h3 {
    font-family: var(--elan-serif); font-weight: 600;
    color: var(--elan-ch-800);
    margin: 0.8em 0 0.35em; line-height: 1.25;
    letter-spacing: -0.01em;
  }
  .elan-md h1 { font-size: 1.2rem; }
  .elan-md h2 { font-size: 1.08rem; }
  .elan-md h3 { font-size: 0.98rem; }
  .elan-md blockquote {
    border-left: 3px solid var(--elan-primary-bg);
    padding: 4px 0 4px 14px;
    margin: 0.6em 0;
    color: var(--elan-ch-600);
    font-style: italic;
  }
  .elan-md a {
    color: var(--elan-primary-bg);
    border-bottom: 1px solid rgba(242,237,227,0.30);
    transition: border-color var(--t-fast);
  }
  .elan-md a:hover { border-bottom-color: var(--elan-primary-bg); }
  .elan-md hr {
    border: none; border-top: 1px solid var(--elan-border);
    margin: 1em 0;
  }
  .elan-md table {
    border-collapse: collapse; margin: 0.5em 0;
    width: 100%; font-size: 0.88em;
  }
  .elan-md th, .elan-md td {
    border: 1px solid var(--elan-border);
    padding: 6px 10px; text-align: left;
  }
  .elan-md th {
    background: var(--elan-ch-100);
    font-weight: 600; color: var(--elan-ch-700);
  }
`;

/* ── Bot avatar ──────────────────────────────────────────────────── */
function BotAvatar({ size = 28, pulse = false }) {
  return (
    <div style={{
      width: size, height: size, borderRadius: '50%',
      background: 'var(--elan-primary-bg)',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      flexShrink: 0,
      boxShadow: pulse ? 'var(--shadow-xs), var(--glow-cream)' : 'var(--shadow-xs)',
      position: 'relative',
    }}>
      <svg width={size * 0.55} height={size * 0.55} viewBox="0 0 52 52" fill="none">
        <polyline
          points="8,26 17,26 20,14 24,38 27,26 44,26"
          stroke="var(--elan-primary-text)"
          strokeWidth="3"
          strokeLinecap="round"
          strokeLinejoin="round"
          fill="none"
        />
      </svg>
      {pulse && (
        <span style={{
          position: 'absolute', bottom: -1, right: -1,
          width: 8, height: 8, borderRadius: '50%',
          background: 'var(--elan-sg-500)',
          border: '1.5px solid var(--elan-bg)',
          boxShadow: '0 0 0 0 rgba(107,174,101,0.6)',
          animation: 'elan-pulse-glow 2s ease-out infinite',
        }} />
      )}
    </div>
  );
}

/* ── Bubble ─────────────────────────────────────────────────────── */
function Bubble({ msg, showAvatar = true }) {
  const isUser = msg.role === 'user';

  if (isUser) {
    return (
      <div style={{
        display: 'flex', justifyContent: 'flex-end',
        marginBottom: 12,
        animation: 'elan-slide-up 0.28s var(--ease-out) both',
      }}>
        <div style={{
          maxWidth: '78%',
          padding: '11px 16px',
          borderRadius: '20px 20px 6px 20px',
          background: 'var(--elan-primary-bg)',
          color: 'var(--elan-primary-text)',
          fontSize: '0.9rem',
          lineHeight: 1.55,
          fontWeight: 500,
          whiteSpace: 'pre-wrap',
          boxShadow: 'var(--shadow-xs)',
        }}>
          {msg.content}
        </div>
      </div>
    );
  }

  return (
    <div style={{
      display: 'flex', justifyContent: 'flex-start',
      marginBottom: 14, gap: 10, alignItems: 'flex-start',
      animation: 'elan-slide-up 0.32s var(--ease-out) both',
    }}>
      {showAvatar ? <BotAvatar size={28} /> : <div style={{ width: 28, flexShrink: 0 }} />}
      <div style={{
        maxWidth: 'calc(100% - 50px)',
        padding: '12px 16px',
        borderRadius: '4px 18px 18px 18px',
        background: 'var(--elan-surface-2)',
        border: '1px solid var(--elan-border)',
        boxShadow: 'var(--shadow-xs)',
        fontSize: '0.92rem',
      }}>
        <div className="elan-md">
          <ReactMarkdown>{msg.content}</ReactMarkdown>
        </div>
      </div>
    </div>
  );
}

/* ── Typing indicator — 3 dots + subtle shimmer line ──────────── */
function TypingDots() {
  return (
    <div style={{
      display: 'flex', justifyContent: 'flex-start',
      marginBottom: 14, gap: 10, alignItems: 'flex-start',
      animation: 'elan-fade-in 0.2s var(--ease-out) both',
    }}>
      <BotAvatar size={28} pulse />
      <div style={{
        padding: '14px 18px',
        borderRadius: '4px 18px 18px 18px',
        background: 'var(--elan-surface-2)',
        border: '1px solid var(--elan-border)',
        boxShadow: 'var(--shadow-xs)',
        display: 'flex', flexDirection: 'column', gap: 8,
        minWidth: 110,
      }}>
        <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
          {[0, 1, 2].map(i => (
            <span key={i} style={{
              width: 7, height: 7, borderRadius: '50%',
              background: 'var(--elan-ch-500)', display: 'inline-block',
              animation: `elan-bounce 1.2s ease-in-out ${i * 0.18}s infinite`,
            }} />
          ))}
          <span style={{
            fontSize: '0.7rem', color: 'var(--elan-ch-500)',
            fontWeight: 600, letterSpacing: '0.04em',
            marginLeft: 6, textTransform: 'uppercase',
          }}>
            Thinking
          </span>
        </div>
      </div>
    </div>
  );
}

/* ── Risk level → gradient + glow ───────────────────────────────── */
const RISK_COLOR = {
  low: { color: 'var(--elan-sg-500)', glow: 'var(--glow-sage)' },
  moderate: { color: 'var(--elan-am-400)', glow: 'var(--glow-amber)' },
  high: { color: 'var(--elan-tc-400)', glow: 'var(--glow-terra)' },
  very_high: { color: 'var(--elan-tc-700)', glow: 'var(--glow-terra)' },
};

/* ── Assessment context card ─────────────────────────────────────── */
function ContextCard({ ctx, onDismiss }) {
  const condLabel = ctx.condition === 'cvd' ? 'Heart Disease'
    : ctx.condition === 'hypertension' ? 'Hypertension' : 'Diabetes';
  const pct = Math.round((ctx.result?.probability ?? 0) * 100);
  const level = ctx.result?.risk_level ?? 'low';
  const meta = RISK_COLOR[level] ?? RISK_COLOR.low;

  return (
    <div style={{
      margin: '0 0 14px',
      padding: '14px 16px',
      background: 'var(--elan-surface-2)',
      border: '1px solid var(--elan-border)',
      borderRadius: 'var(--r-lg)',
      boxShadow: `var(--shadow-xs), ${meta.glow}`,
      display: 'flex', alignItems: 'center', gap: 14,
      animation: 'elan-fade-in 0.3s var(--ease-out) both',
    }}>
      <div style={{
        width: 38, height: 38, borderRadius: 'var(--r-md)',
        background: `${meta.color}15`,
        border: `1px solid ${meta.color}40`,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        flexShrink: 0,
      }}>
        <Stethoscope size={17} color={meta.color} />
      </div>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{
          fontSize: '0.66rem', fontWeight: 700, textTransform: 'uppercase',
          letterSpacing: '0.08em', color: 'var(--elan-ch-500)',
        }}>
          Recent assessment loaded
        </div>
        <div style={{
          fontSize: '0.92rem', fontWeight: 600,
          color: 'var(--elan-ch-800)', marginTop: 2,
        }}>
          {condLabel} ·{' '}
          <span style={{
            color: meta.color,
            fontFamily: 'var(--elan-serif)',
            fontSize: '1.02rem',
          }}>
            {pct}%
          </span>
        </div>
      </div>
      <button onClick={onDismiss} style={{
        background: 'transparent', border: 'none',
        color: 'var(--elan-ch-400)',
        fontSize: '1.2rem', cursor: 'pointer',
        lineHeight: 1, flexShrink: 0,
        padding: 6, borderRadius: 'var(--r-xs)',
        transition: 'color var(--t-fast), background var(--t-fast)',
      }}
      onMouseEnter={e => {
        e.currentTarget.style.color = 'var(--elan-ch-800)';
        e.currentTarget.style.background = 'var(--elan-ch-100)';
      }}
      onMouseLeave={e => {
        e.currentTarget.style.color = 'var(--elan-ch-400)';
        e.currentTarget.style.background = 'transparent';
      }}
      aria-label="Dismiss context">×</button>
    </div>
  );
}

/* ── Welcome screen ─────────────────────────────────────────────── */
function WelcomeScreen({ onSend, assessmentCtx, onDismissCtx }) {
  const hero = useMemo(() => contextualHero(assessmentCtx), [assessmentCtx]);
  const [activeCat, setActiveCat] = useState(null);

  const visibleCategoryPrompts = activeCat
    ? PROMPT_CATEGORIES.find(c => c.label === activeCat)?.prompts ?? []
    : null;

  return (
    <div style={{
      flex: 1, display: 'flex', flexDirection: 'column',
      alignItems: 'center', justifyContent: 'center',
      padding: '24px 20px 28px', gap: 0,
      animation: 'elan-fade-in 0.4s var(--ease-out) both',
    }}>
      {/* Brand mark with glow */}
      <div style={{
        width: 64, height: 64, borderRadius: 18,
        background: 'var(--elan-primary-bg)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        marginBottom: 18,
        boxShadow: 'var(--shadow-md), var(--glow-cream)',
        position: 'relative',
      }}>
        <svg width="32" height="32" viewBox="0 0 52 52" fill="none" aria-hidden="true">
          <polyline
            points="8,26 17,26 20,14 24,38 27,26 44,26"
            stroke="var(--elan-primary-text)" strokeWidth="3"
            strokeLinecap="round" strokeLinejoin="round" fill="none"
          />
        </svg>
        <div style={{
          position: 'absolute', top: -3, right: -3,
          width: 14, height: 14, borderRadius: '50%',
          background: 'var(--elan-sg-500)',
          border: '2px solid var(--elan-bg)',
          boxShadow: 'var(--glow-sage)',
        }} />
      </div>

      <div style={{
        display: 'inline-flex', alignItems: 'center', gap: 6,
        padding: '4px 12px',
        background: 'var(--elan-ch-100)',
        border: '1px solid var(--elan-border)',
        borderRadius: 'var(--r-pill)',
        marginBottom: 14,
      }}>
        <Sparkles size={11} color="var(--elan-am-400)" />
        <span style={{
          fontSize: '0.68rem', fontWeight: 600,
          color: 'var(--elan-ch-600)',
          letterSpacing: '0.04em', textTransform: 'uppercase',
        }}>
          Élan AI · Online
        </span>
      </div>

      <h2 style={{
        fontFamily: 'var(--elan-serif)', fontSize: '1.85rem',
        color: 'var(--elan-ch-800)', letterSpacing: '-0.025em',
        lineHeight: 1.15, textAlign: 'center', marginBottom: 8,
      }}>
        {hero.title}
      </h2>

      <p style={{
        fontSize: '0.9rem', color: 'var(--elan-ch-500)',
        textAlign: 'center', maxWidth: 360, lineHeight: 1.6, marginBottom: 22,
      }}>
        {hero.subtitle}
      </p>

      {assessmentCtx && (
        <div style={{ width: '100%', maxWidth: 440, marginBottom: 6 }}>
          <ContextCard ctx={assessmentCtx} onDismiss={onDismissCtx} />
        </div>
      )}

      {/* Featured prompts (first row, larger) */}
      <div style={{
        width: '100%', maxWidth: 480,
        display: 'grid', gridTemplateColumns: '1fr 1fr',
        gap: 8, marginBottom: 16,
      }}>
        {hero.featured.slice(0, 4).map((text, i) => (
          <button key={i} onClick={() => onSend(text)} style={{
            padding: '11px 14px', textAlign: 'left',
            background: 'var(--elan-surface-2)',
            border: '1px solid var(--elan-border)',
            borderRadius: 'var(--r-md)',
            fontSize: '0.82rem', color: 'var(--elan-ch-700)',
            cursor: 'pointer', lineHeight: 1.4,
            transition: 'all var(--t-fast)',
            fontFamily: 'inherit',
          }}
          onMouseEnter={e => {
            e.currentTarget.style.background = 'var(--elan-ch-100)';
            e.currentTarget.style.borderColor = 'rgba(242,237,227,0.18)';
            e.currentTarget.style.color = 'var(--elan-ch-800)';
            e.currentTarget.style.transform = 'translateY(-1px)';
          }}
          onMouseLeave={e => {
            e.currentTarget.style.background = 'var(--elan-surface-2)';
            e.currentTarget.style.borderColor = 'var(--elan-border)';
            e.currentTarget.style.color = 'var(--elan-ch-700)';
            e.currentTarget.style.transform = 'translateY(0)';
          }}
          >
            {text}
          </button>
        ))}
      </div>

      {/* Category chips */}
      <div style={{
        display: 'flex', flexWrap: 'wrap', gap: 6,
        justifyContent: 'center', maxWidth: 480, marginBottom: 12,
      }}>
        {PROMPT_CATEGORIES.map(({ label, icon: Icon, color, bg, border }) => {
          const active = activeCat === label;
          return (
            <button
              key={label}
              onClick={() => setActiveCat(active ? null : label)}
              style={{
                display: 'inline-flex', alignItems: 'center', gap: 6,
                padding: '6px 12px',
                background: active ? bg : 'transparent',
                border: `1px solid ${active ? border : 'var(--elan-border)'}`,
                borderRadius: 'var(--r-pill)',
                fontSize: '0.74rem', fontWeight: 600,
                color: active ? color : 'var(--elan-ch-500)',
                cursor: 'pointer',
                transition: 'all var(--t-fast)',
                fontFamily: 'inherit',
              }}
            >
              <Icon size={12} strokeWidth={2.2} />
              {label}
            </button>
          );
        })}
      </div>

      {/* Expanded prompt list under category */}
      {visibleCategoryPrompts && (
        <div style={{
          width: '100%', maxWidth: 480,
          display: 'flex', flexDirection: 'column', gap: 6,
          animation: 'elan-fade-in 0.25s var(--ease-out) both',
        }}>
          {visibleCategoryPrompts.map((text, i) => (
            <button key={i} onClick={() => onSend(text)} style={{
              padding: '9px 14px', textAlign: 'left',
              background: 'var(--elan-surface)',
              border: '1px solid var(--elan-border)',
              borderRadius: 'var(--r-md)',
              fontSize: '0.82rem', color: 'var(--elan-ch-700)',
              cursor: 'pointer', lineHeight: 1.4,
              transition: 'all var(--t-fast)',
              fontFamily: 'inherit',
            }}
            onMouseEnter={e => {
              e.currentTarget.style.background = 'var(--elan-surface-2)';
              e.currentTarget.style.color = 'var(--elan-ch-800)';
            }}
            onMouseLeave={e => {
              e.currentTarget.style.background = 'var(--elan-surface)';
              e.currentTarget.style.color = 'var(--elan-ch-700)';
            }}
            >
              {text}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

/* ── Main page ───────────────────────────────────────────────────── */
export default function ChatPage() {
  const [assessmentCtx, dismissCtx] = useRecentAssessment();
  const { messages, send, reset, isLoading } = useChat(null, assessmentCtx);

  const [input, setInput] = useState('');
  const [focused, setFocused] = useState(false);
  const bottomRef = useRef(null);
  const textareaRef = useRef(null);

  /* Scroll to bottom on new messages */
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  /* Auto-grow textarea */
  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = Math.min(el.scrollHeight, 140) + 'px';
  }, [input]);

  const handleSend = useCallback((text) => {
    const trimmed = (text ?? input).trim();
    if (!trimmed || isLoading) return;
    setInput('');
    send(trimmed);
  }, [input, isLoading, send]);

  const handleKey = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(); }
  };

  const handleReset = useCallback(async () => {
    await reset();
    setInput('');
  }, [reset]);

  const hasMessages = messages.length > 0;
  const canSend = input.trim() && !isLoading;

  return (
    <div style={{
      height: '100dvh', display: 'flex', flexDirection: 'column',
      background: 'var(--elan-bg)',
    }}>
      <TopBar />

      <div style={{
        flex: 1, overflowY: 'hidden',
        display: 'flex', flexDirection: 'column', alignItems: 'center',
      }}>
        <div style={{
          width: '100%', maxWidth: 720, flex: 1,
          display: 'flex', flexDirection: 'column',
          background: 'var(--elan-surface)',
          border: '1px solid var(--elan-border)',
          borderTop: 'none', borderBottom: 'none',
          overflow: 'hidden',
          boxShadow: 'var(--shadow-md)',
        }}>

          {/* Assistant identity strip — visible once chat starts */}
          {hasMessages && (
            <div style={{
              display: 'flex', alignItems: 'center',
              justifyContent: 'space-between',
              padding: '10px 18px',
              borderBottom: '1px solid var(--elan-sep)',
              background: 'var(--elan-surface-2)',
              flexShrink: 0,
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <BotAvatar size={28} pulse />
                <div style={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                  <span style={{
                    fontSize: '0.85rem', fontWeight: 700,
                    color: 'var(--elan-ch-800)',
                    fontFamily: 'var(--elan-serif)',
                    letterSpacing: '-0.01em',
                  }}>
                    Élan AI
                  </span>
                  <span style={{
                    fontSize: '0.66rem', color: 'var(--elan-sg-500)',
                    fontWeight: 600, letterSpacing: '0.04em',
                    textTransform: 'uppercase',
                  }}>
                    {isLoading ? 'Typing…' : 'Online'}
                  </span>
                </div>
              </div>
              <button onClick={handleReset} style={{
                display: 'flex', alignItems: 'center', gap: 6,
                background: 'transparent',
                border: '1px solid var(--elan-border)',
                borderRadius: 'var(--r-pill)',
                color: 'var(--elan-ch-500)', fontSize: '0.76rem',
                cursor: 'pointer', padding: '5px 11px',
                transition: 'all var(--t-fast)',
                fontFamily: 'inherit', fontWeight: 600,
              }}
              onMouseEnter={e => {
                e.currentTarget.style.color = 'var(--elan-ch-800)';
                e.currentTarget.style.borderColor = 'rgba(242,237,227,0.18)';
                e.currentTarget.style.background = 'var(--elan-ch-100)';
              }}
              onMouseLeave={e => {
                e.currentTarget.style.color = 'var(--elan-ch-500)';
                e.currentTarget.style.borderColor = 'var(--elan-border)';
                e.currentTarget.style.background = 'transparent';
              }}
              >
                <RotateCcw size={12} />
                New chat
              </button>
            </div>
          )}

          {/* Message area */}
          <div style={{
            flex: 1, overflowY: 'auto',
            display: 'flex', flexDirection: 'column',
          }}>
            {!hasMessages ? (
              <WelcomeScreen
                onSend={handleSend}
                assessmentCtx={assessmentCtx}
                onDismissCtx={dismissCtx}
              />
            ) : (
              <div style={{ padding: '20px 18px 12px', flex: 1 }}>
                {assessmentCtx && (
                  <ContextCard ctx={assessmentCtx} onDismiss={dismissCtx} />
                )}
                {messages.map((m, i) => {
                  const prev = messages[i - 1];
                  const showAvatar = !prev || prev.role !== m.role;
                  return <Bubble key={m.id ?? `${i}-${m.content?.slice(0, 24)}`} msg={m} showAvatar={showAvatar} />;
                })}
                {isLoading && <TypingDots />}
                <div ref={bottomRef} />
              </div>
            )}
            {!hasMessages && <div ref={bottomRef} />}
          </div>

          {/* Input bar */}
          <div style={{
            padding: '12px 16px 100px',
            background: 'var(--elan-surface)',
            borderTop: '1px solid var(--elan-sep)',
            flexShrink: 0,
          }}>
            <div style={{
              display: 'flex', alignItems: 'flex-end', gap: 10,
              background: 'var(--elan-surface-2)',
              border: `1.5px solid ${focused ? 'rgba(242,237,227,0.20)' : 'var(--elan-ch-200)'}`,
              borderRadius: 'var(--r-xl)',
              padding: '10px 12px',
              boxShadow: focused ? 'var(--shadow-sm), 0 0 0 4px rgba(242,237,227,0.05)' : 'var(--shadow-xs)',
              transition: 'border-color var(--t-base), box-shadow var(--t-base)',
            }}>
              <textarea
                ref={textareaRef}
                value={input}
                onChange={e => setInput(e.target.value)}
                onKeyDown={handleKey}
                onFocus={() => setFocused(true)}
                onBlur={() => setFocused(false)}
                placeholder={isLoading ? 'Élan is thinking…' : 'Ask about your health…'}
                rows={1}
                disabled={isLoading}
                style={{
                  flex: 1, resize: 'none', border: 'none',
                  background: 'transparent',
                  color: 'var(--elan-ch-800)',
                  fontSize: '0.9375rem',
                  lineHeight: 1.5, outline: 'none',
                  maxHeight: 140,
                  fontFamily: 'var(--elan-sans)',
                  padding: '4px 4px',
                }}
              />
              <button
                onClick={() => handleSend()}
                disabled={!canSend}
                aria-label="Send"
                style={{
                  width: 38, height: 38, borderRadius: '50%', flexShrink: 0,
                  background: canSend ? 'var(--elan-primary-bg)' : 'var(--elan-ch-200)',
                  color: canSend ? 'var(--elan-primary-text)' : 'var(--elan-ch-400)',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  transition: 'all var(--t-base)',
                  border: 'none',
                  cursor: canSend ? 'pointer' : 'default',
                  boxShadow: canSend ? 'var(--shadow-xs), var(--glow-cream)' : 'none',
                }}
                onMouseEnter={e => {
                  if (canSend) {
                    e.currentTarget.style.background = 'var(--elan-primary-bg-hover)';
                    e.currentTarget.style.transform = 'scale(1.05)';
                  }
                }}
                onMouseLeave={e => {
                  if (canSend) {
                    e.currentTarget.style.background = 'var(--elan-primary-bg)';
                    e.currentTarget.style.transform = 'scale(1)';
                  }
                }}
              >
                <Send size={15} strokeWidth={2.4} />
              </button>
            </div>
            {!hasMessages && (
              <div style={{
                fontSize: '0.66rem', color: 'var(--elan-ch-400)',
                textAlign: 'center', marginTop: 8,
                letterSpacing: '0.02em',
              }}>
                Élan can make mistakes — verify important health information with a clinician.
              </div>
            )}
          </div>

        </div>
      </div>

      <FloatingNav />

      <style>{MD_STYLES}</style>
    </div>
  );
}
