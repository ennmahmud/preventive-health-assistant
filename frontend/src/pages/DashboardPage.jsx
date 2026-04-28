import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import TopBar from '../components/layout/TopBar';
import FloatingNav from '../components/layout/FloatingNav';
import RiskRing from '../components/health/RiskRing';
import RiskBadge from '../components/health/RiskBadge';
import ElanCard from '../components/ui/ElanCard';
import { fetchHistory, readLocal } from '../utils/assessmentHistory';
import { ArrowRight, Sparkles, Plus, Target, CheckCircle2 } from 'lucide-react';

/* Pretty-print backend recommendation categories */
const prettifyCategory = (c) =>
  !c ? 'General'
    : String(c).replace(/_/g, ' ').replace(/\b\w/g, (ch) => ch.toUpperCase());

const PRIORITY_ORDER = { high: 0, medium: 1, low: 2 };
const PRIORITY_COLORS = {
  high:   { bg: 'var(--elan-tc-50)',  border: 'var(--elan-tc-200)',  dot: 'var(--elan-tc-400)',  text: 'var(--elan-tc-700)'  },
  medium: { bg: 'var(--elan-am-50)',  border: 'var(--elan-am-200)',  dot: 'var(--elan-am-400)',  text: 'var(--elan-am-700)'  },
  low:    { bg: 'var(--elan-sg-50)',  border: 'var(--elan-sg-200)',  dot: 'var(--elan-sg-600)',  text: 'var(--elan-sg-700)'  },
};

const CONDITION_LABEL = { diabetes: 'Diabetes', cvd: 'Heart Disease', hypertension: 'Hypertension' };

const HEALTH_TIPS = [
  'Even a 10-minute walk after meals reduces blood glucose by up to 22%.',
  'Sleeping 7–9 hours nightly lowers cardiovascular risk by 30%.',
  'Replacing processed snacks with nuts can lower LDL cholesterol over 8 weeks.',
  'Stress management and mindfulness reduce hypertension risk measurably.',
  'Regular hydration (8 cups/day) supports healthy blood pressure.',
];

export default function DashboardPage() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [history, setHistory] = useState([]);

  useEffect(() => {
    // Show the per-user cache immediately, then refresh from the API in
    // the background so the dashboard stays accurate across devices.
    setHistory(readLocal(user?.id));
    if (user?.id) {
      fetchHistory(user.id).then(setHistory).catch(() => { /* keep cache */ });
    }
  }, [user?.id]);

  const latestByCondition = {};
  history.forEach(a => {
    if (!latestByCondition[a.condition]) latestByCondition[a.condition] = a;
  });

  /* Build a deduped, priority-ranked list of recommendations across the latest assessments */
  const suggestedActions = (() => {
    const seen = new Set();
    const flat = [];
    Object.entries(latestByCondition).forEach(([cond, a]) => {
      (a.result?.recommendations ?? []).forEach((r) => {
        const text = (r?.recommendation ?? '').trim();
        if (!text || seen.has(text.toLowerCase())) return;
        seen.add(text.toLowerCase());
        flat.push({
          condition: cond,
          category: r.category ?? 'general',
          priority: r.priority ?? 'medium',
          recommendation: text,
          rationale: r.rationale ?? '',
        });
      });
    });
    flat.sort((a, b) => (PRIORITY_ORDER[a.priority] ?? 1) - (PRIORITY_ORDER[b.priority] ?? 1));
    return flat.slice(0, 4);
  })();

  /* Track which suggested actions the user has marked done (this session) */
  const [completedActions, setCompletedActions] = useState(() => {
    try { return new Set(JSON.parse(localStorage.getItem('elan_done_actions') || '[]')); }
    catch { return new Set(); }
  });
  const toggleAction = (key) => {
    setCompletedActions((prev) => {
      const next = new Set(prev);
      next.has(key) ? next.delete(key) : next.add(key);
      try { localStorage.setItem('elan_done_actions', JSON.stringify([...next])); } catch { /* noop */ }
      return next;
    });
  };

  const CONDITIONS = [
    { key: 'diabetes',     label: 'Diabetes',      route: '/assess?c=diabetes' },
    { key: 'cvd',         label: 'Heart Disease',  route: '/assess?c=cvd' },
    { key: 'hypertension', label: 'Hypertension',  route: '/assess?c=hypertension' },
  ];

  const hour = new Date().getHours();
  const greeting = hour < 12 ? 'Good morning' : hour < 18 ? 'Good afternoon' : 'Good evening';
  const firstName = user?.name?.split(' ')[0] ?? 'there';
  const tip = HEALTH_TIPS[new Date().getDate() % HEALTH_TIPS.length];

  return (
    <div style={{ height: '100dvh', display: 'flex', flexDirection: 'column', overflow: 'hidden', background: 'var(--elan-bg)' }}>
      <TopBar />

      <div style={{ flex: 1, overflowY: 'auto', paddingBottom: 120 }}>
        <div className="elan-page-wrap">
        {/* Greeting */}
        <div style={{ marginBottom: 28 }}>
          <h1 style={{
            fontFamily: 'var(--elan-serif)', fontSize: '2rem',
            color: 'var(--elan-ch-800)', lineHeight: 1.15, letterSpacing: '-0.02em',
          }}>
            {greeting},<br />{firstName}.
          </h1>
          <p style={{ color: 'var(--elan-ch-400)', fontSize: '0.875rem', marginTop: 6 }}>
            Here's your health snapshot.
          </p>
        </div>

        {/* CTA for new users — appears prominently before risk rings */}
        {history.length === 0 && (
          <button
            onClick={() => navigate('/assess')}
            style={{
              display: 'flex', alignItems: 'center', justifyContent: 'space-between',
              width: '100%', marginBottom: 20, padding: '20px 22px',
              background: 'var(--elan-primary-bg)', borderRadius: 'var(--r-xl)',
              color: 'var(--elan-primary-text)', border: 'none', cursor: 'pointer',
              boxShadow: 'var(--shadow-lg), var(--glow-cream)',
              transition: 'transform var(--t-base) var(--ease-out), background var(--t-base)',
            }}
            onMouseEnter={e => {
              e.currentTarget.style.background = 'var(--elan-primary-bg-hover)';
              e.currentTarget.style.transform = 'translateY(-1px)';
            }}
            onMouseLeave={e => {
              e.currentTarget.style.background = 'var(--elan-primary-bg)';
              e.currentTarget.style.transform = 'translateY(0)';
            }}
          >
            <div style={{ textAlign: 'left' }}>
              <div style={{ fontFamily: 'var(--elan-serif)', fontSize: '1.15rem', lineHeight: 1.2, color: 'var(--elan-primary-text)' }}>
                Start your first assessment
              </div>
              <div style={{ fontSize: '0.8rem', color: 'var(--elan-primary-muted)', marginTop: 5 }}>
                Takes about 3 minutes · No lab results needed
              </div>
            </div>
            <div style={{
              width: 36, height: 36, borderRadius: '50%',
              background: 'rgba(20,17,13,0.10)',
              display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
              color: 'var(--elan-primary-text)',
            }}>
              <ArrowRight size={18} />
            </div>
          </button>
        )}

        {/* Risk rings */}
        <div style={{ display: 'flex', gap: 12, marginBottom: 24, overflowX: 'auto', paddingBottom: 4 }}>
          {CONDITIONS.map(({ key, label, route }) => {
            const a = latestByCondition[key];
            return (
              <ElanCard key={key} onClick={() => navigate(route)}
                style={{ padding: 20, minWidth: 140, flex: 1, textAlign: 'center', cursor: 'pointer' }}>
                {a ? (
                  <RiskRing
                    probability={a.result?.probability ?? 0}
                    risk_level={a.result?.risk_level ?? 'low'}
                    condition={label}
                    size={100}
                  />
                ) : (
                  <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 8 }}>
                    <div style={{
                      width: 64, height: 64, borderRadius: '50%',
                      background: 'var(--elan-ch-50)',
                      border: '2px solid var(--elan-ch-100)',
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                    }}>
                      <Plus size={20} color="var(--elan-ch-300)" strokeWidth={1.5} />
                    </div>
                    <div style={{ fontSize: '0.78rem', fontWeight: 600, color: 'var(--elan-ch-700)' }}>{label}</div>
                    <div style={{ fontSize: '0.68rem', color: 'var(--elan-ch-300)', fontWeight: 500 }}>Tap to assess</div>
                  </div>
                )}
              </ElanCard>
            );
          })}
        </div>

        {/* Recent assessments */}
        {history.length > 0 && (
          <section style={{ marginBottom: 24 }}>
            <h2 style={{ fontSize: '0.7rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.08em', color: 'var(--elan-ch-400)', marginBottom: 12 }}>
              Recent Assessments
            </h2>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {history.slice(0, 5).map((a, i) => (
                <ElanCard
                  key={i}
                  style={{ padding: '14px 18px' }}
                  onClick={() => navigate('/assess', { state: { condition: a.condition, result: a.result } })}
                >
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <div>
                      <div style={{ fontWeight: 600, fontSize: '0.9rem', color: 'var(--elan-ch-800)', textTransform: 'capitalize' }}>
                        {a.condition === 'cvd' ? 'Heart Disease' : a.condition}
                      </div>
                      <div style={{ fontSize: '0.75rem', color: 'var(--elan-ch-400)', marginTop: 2 }}>
                        {new Date(a.completedAt).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })}
                      </div>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                      <RiskBadge level={a.result?.risk_level ?? 'low'} />
                      <span style={{ fontSize: '0.88rem', fontFamily: 'var(--elan-serif)', color: 'var(--elan-ch-600)' }}>
                        {Math.round((a.result?.probability ?? 0) * 100)}%
                      </span>
                      <ArrowRight size={15} color="var(--elan-ch-300)" />
                    </div>
                  </div>
                </ElanCard>
              ))}
            </div>
          </section>
        )}

        {/* Suggested actions — pulled from latest assessment recommendations */}
        {suggestedActions.length > 0 && (
          <section style={{ marginBottom: 24 }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
              <h2 style={{ fontSize: '0.7rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.08em', color: 'var(--elan-ch-400)' }}>
                Suggested Actions
              </h2>
              <span style={{ fontSize: '0.7rem', color: 'var(--elan-ch-400)' }}>
                {[...completedActions].filter(k => suggestedActions.some(a => `${a.condition}::${a.recommendation}` === k)).length} / {suggestedActions.length} done
              </span>
            </div>
            <ElanCard style={{ padding: '6px 6px' }}>
              <div style={{ display: 'flex', flexDirection: 'column' }}>
                {suggestedActions.map((a, i) => {
                  const key = `${a.condition}::${a.recommendation}`;
                  const done = completedActions.has(key);
                  const s = PRIORITY_COLORS[a.priority] ?? PRIORITY_COLORS.medium;
                  return (
                    <button
                      key={key}
                      onClick={() => toggleAction(key)}
                      style={{
                        display: 'flex', alignItems: 'flex-start', gap: 12,
                        padding: '12px 14px', textAlign: 'left',
                        background: done ? 'var(--elan-ch-50)' : 'transparent',
                        border: 'none', borderTop: i === 0 ? 'none' : '1px solid var(--elan-sep)',
                        cursor: 'pointer', transition: 'background var(--t-fast)',
                      }}
                    >
                      <div style={{
                        width: 22, height: 22, borderRadius: '50%',
                        background: done ? 'var(--elan-sg-500)' : 'transparent',
                        border: done ? 'none' : `2px solid ${s.dot}`,
                        display: 'flex', alignItems: 'center', justifyContent: 'center',
                        flexShrink: 0, marginTop: 1,
                      }}>
                        {done && <CheckCircle2 size={20} color="#fff" strokeWidth={2.5} />}
                      </div>
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap', marginBottom: 3 }}>
                          <span style={{
                            fontSize: '0.62rem', fontWeight: 700, textTransform: 'uppercase',
                            letterSpacing: '0.06em', color: s.text,
                            background: s.bg, padding: '2px 6px', borderRadius: 'var(--r-xs)',
                            border: `1px solid ${s.border}`,
                          }}>{a.priority} · {prettifyCategory(a.category)}</span>
                          <span style={{ fontSize: '0.65rem', color: 'var(--elan-ch-400)' }}>
                            for {CONDITION_LABEL[a.condition] ?? a.condition}
                          </span>
                        </div>
                        <div style={{
                          fontSize: '0.875rem', fontWeight: 600,
                          color: done ? 'var(--elan-ch-400)' : 'var(--elan-ch-800)',
                          textDecoration: done ? 'line-through' : 'none',
                          lineHeight: 1.45,
                        }}>{a.recommendation}</div>
                        {a.rationale && !done && (
                          <div style={{ fontSize: '0.78rem', color: 'var(--elan-ch-500)', marginTop: 3, lineHeight: 1.5 }}>
                            {a.rationale}
                          </div>
                        )}
                      </div>
                    </button>
                  );
                })}
              </div>
            </ElanCard>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginTop: 8, color: 'var(--elan-ch-400)', fontSize: '0.72rem' }}>
              <Target size={12} />
              <span>Tap an action to mark it done · synced to your device</span>
            </div>
          </section>
        )}

        {/* Health tip */}
        <ElanCard style={{ padding: '16px 18px' }}>
          <div style={{ display: 'flex', gap: 12, alignItems: 'flex-start' }}>
            <Sparkles size={16} color="var(--elan-am-400)" style={{ flexShrink: 0, marginTop: 2 }} />
            <div>
              <div style={{ fontSize: '0.7rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.07em', color: 'var(--elan-am-500)', marginBottom: 6 }}>
                Daily Insight
              </div>
              <p style={{ fontSize: '0.875rem', color: 'var(--elan-ch-700)', lineHeight: 1.6 }}>{tip}</p>
            </div>
          </div>
        </ElanCard>

        </div>
      </div>

      <FloatingNav />
    </div>
  );
}
