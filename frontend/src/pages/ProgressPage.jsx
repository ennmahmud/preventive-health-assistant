import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import TopBar from '../components/layout/TopBar';
import FloatingNav from '../components/layout/FloatingNav';
import ElanCard from '../components/ui/ElanCard';
import RiskBadge from '../components/health/RiskBadge';
import { fetchHistory, readLocal } from '../utils/assessmentHistory';
import { ChevronRight } from 'lucide-react';

const CONDITION_LABELS = {
  diabetes: 'Diabetes', cvd: 'Heart Disease', hypertension: 'Hypertension',
};
const RISK_COLORS = {
  low: 'var(--elan-sg-600)', moderate: 'var(--elan-am-400)',
  high: 'var(--elan-tc-400)', very_high: 'var(--elan-ch-800)',
};

function TrendBar({ history, condition, onOpen }) {
  if (!history.length) return null;
  const latest = history[0];
  const pct = Math.round((latest.result?.probability ?? 0) * 100);
  const color = RISK_COLORS[latest.result?.risk_level ?? 'low'];

  return (
    <ElanCard style={{ padding: '16px 20px' }} onClick={() => onOpen?.(latest)}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
        <span style={{ fontWeight: 600, fontSize: '0.9rem', color: 'var(--elan-ch-800)' }}>
          {CONDITION_LABELS[condition] ?? condition}
        </span>
        <RiskBadge level={latest.result?.risk_level ?? 'low'} />
      </div>
      <div style={{ display: 'flex', gap: 4, alignItems: 'flex-end', height: 56 }}>
        {history.slice(0, 8).reverse().map((a, i) => {
          const h = Math.max(8, (a.result?.probability ?? 0) * 100);
          const c = RISK_COLORS[a.result?.risk_level ?? 'low'];
          return (
            <div key={i} title={`${Math.round((a.result?.probability ?? 0) * 100)}%`}
              style={{
                flex: 1, background: c, borderRadius: 'var(--r-xs)',
                height: `${h}%`, opacity: i === history.slice(0, 8).length - 1 ? 1 : 0.45,
                transition: 'height 0.5s var(--ease-out)',
              }} />
          );
        })}
      </div>
      <div style={{ marginTop: 10, display: 'flex', justifyContent: 'space-between' }}>
        <span style={{ fontSize: '0.72rem', color: 'var(--elan-ch-400)' }}>
          {history.length} assessment{history.length !== 1 ? 's' : ''}
        </span>
        <span style={{ fontSize: '0.875rem', fontFamily: 'var(--elan-serif)', color }}>
          {pct}% current
        </span>
      </div>
    </ElanCard>
  );
}

export default function ProgressPage() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [history, setHistory] = useState([]);

  useEffect(() => {
    setHistory(readLocal(user?.id));
    if (user?.id) {
      fetchHistory(user.id).then(setHistory).catch(() => { /* keep cache */ });
    }
  }, [user?.id]);

  const byCondition = history.reduce((acc, a) => {
    (acc[a.condition] = acc[a.condition] || []).push(a); return acc;
  }, {});

  const streak = (() => {
    if (!history.length) return 0;
    const dates = [...new Set(history.map(a => new Date(a.completedAt).toDateString()))].sort((a, b) => new Date(b) - new Date(a));
    let s = 1, today = new Date().toDateString(), prev = today;
    if (dates[0] !== today) return 0;
    for (let i = 1; i < dates.length; i++) {
      const d = new Date(prev); d.setDate(d.getDate() - 1);
      if (dates[i] === d.toDateString()) { s++; prev = dates[i]; } else break;
    }
    return s;
  })();

  return (
    <div style={{ height: '100dvh', display: 'flex', flexDirection: 'column', background: 'var(--elan-bg)' }}>
      <TopBar />
      <div style={{ flex: 1, overflowY: 'auto', paddingBottom: 120 }}>
        <div className="elan-page-wrap">
        <h1 style={{ fontFamily: 'var(--elan-serif)', fontSize: '1.8rem', color: 'var(--elan-ch-800)', marginBottom: 8, letterSpacing: '-0.02em' }}>
          Your progress
        </h1>
        <p style={{ color: 'var(--elan-ch-400)', fontSize: '0.875rem', marginBottom: 24 }}>
          Track how your risk scores change over time.
        </p>

        {/* Streak */}
        <ElanCard style={{ padding: '20px', marginBottom: 20, display: 'flex', alignItems: 'center', gap: 20 }}>
          <div style={{
            width: 64, height: 64, borderRadius: 'var(--r-lg)',
            background: streak > 0 ? 'var(--elan-am-50)' : 'var(--elan-ch-50)',
            display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
            border: `1.5px solid ${streak > 0 ? 'var(--elan-am-200)' : 'var(--elan-ch-100)'}`,
            flexShrink: 0,
          }}>
            <span style={{ fontSize: '1.6rem', fontFamily: 'var(--elan-serif)', color: streak > 0 ? 'var(--elan-am-700)' : 'var(--elan-ch-400)', lineHeight: 1 }}>
              {streak}
            </span>
            <span style={{ fontSize: '0.6rem', textTransform: 'uppercase', letterSpacing: '0.06em', color: streak > 0 ? 'var(--elan-am-500)' : 'var(--elan-ch-400)', fontWeight: 700 }}>
              day{streak !== 1 ? 's' : ''}
            </span>
          </div>
          <div>
            <div style={{ fontWeight: 700, fontSize: '1rem', color: 'var(--elan-ch-800)' }}>
              {streak > 0 ? `${streak}-day streak` : 'No streak yet'}
            </div>
            <div style={{ fontSize: '0.8rem', color: 'var(--elan-ch-400)', marginTop: 4 }}>
              {streak > 0 ? 'Keep assessing daily to maintain your streak!' : 'Complete an assessment today to start.'}
            </div>
          </div>
        </ElanCard>

        {/* Trend bars */}
        {Object.entries(byCondition).length > 0 ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            {Object.entries(byCondition).map(([cond, recs]) => (
              <TrendBar
                key={cond}
                condition={cond}
                history={recs}
                onOpen={(latest) => navigate('/assess', { state: { condition: cond, result: latest.result } })}
              />
            ))}
          </div>
        ) : (
          <ElanCard style={{ padding: '32px 24px', textAlign: 'center' }}>
            <p style={{ color: 'var(--elan-ch-400)', fontSize: '0.9rem', lineHeight: 1.6 }}>
              No assessment history yet.<br />Complete your first assessment to start tracking progress.
            </p>
          </ElanCard>
        )}

        {/* Full history list */}
        {history.length > 0 && (
          <section style={{ marginTop: 24 }}>
            <h2 style={{ fontSize: '0.7rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.08em', color: 'var(--elan-ch-400)', marginBottom: 12 }}>
              All Assessments
            </h2>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {history.map((a, i) => (
                <ElanCard
                  key={`${a.condition}-${a.completedAt ?? i}`}
                  style={{ padding: '12px 18px' }}
                  onClick={() => navigate('/assess', { state: { condition: a.condition, result: a.result } })}
                >
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <div>
                      <div style={{ fontWeight: 600, fontSize: '0.875rem', color: 'var(--elan-ch-800)', textTransform: 'capitalize' }}>
                        {CONDITION_LABELS[a.condition] ?? a.condition}
                      </div>
                      <div style={{ fontSize: '0.72rem', color: 'var(--elan-ch-400)', marginTop: 1 }}>
                        {new Date(a.completedAt).toLocaleString('en-GB', { day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' })}
                      </div>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                      <RiskBadge level={a.result?.risk_level ?? 'low'} />
                      <span style={{ fontSize: '0.875rem', fontFamily: 'var(--elan-serif)', color: RISK_COLORS[a.result?.risk_level ?? 'low'] }}>
                        {Math.round((a.result?.probability ?? 0) * 100)}%
                      </span>
                      <ChevronRight size={16} color="var(--elan-ch-300)" />
                    </div>
                  </div>
                </ElanCard>
              ))}
            </div>
          </section>
        )}
        </div>
      </div>
      <FloatingNav />
    </div>
  );
}
