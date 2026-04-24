import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import TopBar from '../components/layout/TopBar';
import FloatingNav from '../components/layout/FloatingNav';
import RiskRing from '../components/health/RiskRing';
import RiskBadge from '../components/health/RiskBadge';
import ElanCard from '../components/ui/ElanCard';
import { ArrowRight, ClipboardList, Sparkles } from 'lucide-react';

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
    try {
      const stored = JSON.parse(localStorage.getItem('elan_assessments') || '[]');
      setHistory(stored);
    } catch { setHistory([]); }
  }, []);

  const latestByCondition = {};
  history.forEach(a => {
    if (!latestByCondition[a.condition]) latestByCondition[a.condition] = a;
  });

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

      <div style={{ flex: 1, overflowY: 'auto', padding: '0 20px 120px' }}>
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

        {/* Risk rings */}
        <div style={{ display: 'flex', gap: 12, marginBottom: 24, overflowX: 'auto', paddingBottom: 4 }}>
          {CONDITIONS.map(({ key, label, route }) => {
            const a = latestByCondition[key];
            return (
              <ElanCard key={key} onClick={() => navigate(route)}
                style={{ padding: 20, minWidth: 140, flex: 1, textAlign: 'center' }}>
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
                      width: 60, height: 60, borderRadius: '50%',
                      border: '3px dashed var(--elan-ch-200)',
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                    }}>
                      <ClipboardList size={22} color="var(--elan-ch-300)" />
                    </div>
                    <div style={{ fontSize: '0.78rem', fontWeight: 600, color: 'var(--elan-ch-700)' }}>{label}</div>
                    <div style={{ fontSize: '0.68rem', color: 'var(--elan-ch-400)' }}>Not assessed</div>
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
                <ElanCard key={i} style={{ padding: '14px 18px' }}>
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
                    </div>
                  </div>
                </ElanCard>
              ))}
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

        {/* CTA if no assessments */}
        {history.length === 0 && (
          <button
            onClick={() => navigate('/assess')}
            style={{
              display: 'flex', alignItems: 'center', justifyContent: 'space-between',
              width: '100%', marginTop: 16, padding: '18px 20px',
              background: 'var(--elan-ch-800)', borderRadius: 'var(--r-xl)',
              color: '#fff', border: 'none', cursor: 'pointer',
            }}
          >
            <div style={{ textAlign: 'left' }}>
              <div style={{ fontFamily: 'var(--elan-serif)', fontSize: '1.1rem', lineHeight: 1.2 }}>
                Start your first assessment
              </div>
              <div style={{ fontSize: '0.8rem', opacity: 0.7, marginTop: 4 }}>
                Takes about 3 minutes
              </div>
            </div>
            <ArrowRight size={20} />
          </button>
        )}
      </div>

      <FloatingNav />
    </div>
  );
}
