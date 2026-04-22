/* TrendDashboard */

import { useState, useEffect } from 'react';
import { getAssessmentHistory } from '../utils/api';
import styles from './TrendDashboard.module.css';

const CONDITION_META = {
  diabetes: { label: 'Diabetes', emoji: '🩸', color: '#5b8dee' },
  cvd:      { label: 'Heart Disease', emoji: '❤️', color: '#ef4444' },
  hypertension: { label: 'Hypertension', emoji: '🫀', color: '#f59e0b' },
};

const RISK_COLORS = {
  Low: '#16a34a',
  Moderate: '#ca8a04',
  High: '#ea580c',
  'Very High': '#dc2626',
};

const RISK_ORDER = ['Low', 'Moderate', 'High', 'Very High'];

function formatDate(iso) {
  return new Date(iso).toLocaleDateString('en-GB', { day: 'numeric', month: 'short' });
}

// ── Sparkline SVG ──────────────────────────────────────────────────────────────

function Sparkline({ points, color, width = 260, height = 64 }) {
  if (!points || points.length < 2) return null;

  const minY = 0;
  const maxY = 100;
  const padX = 4;
  const padY = 6;

  const xs = points.map((_, i) => padX + (i / (points.length - 1)) * (width - padX * 2));
  const ys = points.map(v => padY + (1 - (v - minY) / (maxY - minY)) * (height - padY * 2));

  const path = xs.map((x, i) => `${i === 0 ? 'M' : 'L'} ${x} ${ys[i]}`).join(' ');
  const area = `${path} L ${xs[xs.length - 1]} ${height} L ${xs[0]} ${height} Z`;

  const lastX = xs[xs.length - 1];
  const lastY = ys[ys.length - 1];

  return (
    <svg viewBox={`0 0 ${width} ${height}`} className={styles.sparkline}>
      <defs>
        <linearGradient id={`grad-${color.replace('#','')}`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity="0.3" />
          <stop offset="100%" stopColor={color} stopOpacity="0.03" />
        </linearGradient>
      </defs>
      <path d={area} fill={`url(#grad-${color.replace('#','')})`} />
      <path d={path} fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
      {/* Latest point dot */}
      <circle cx={lastX} cy={lastY} r="4" fill={color} />
    </svg>
  );
}

// ── Condition card ──────────────────────────────────────────────────────────────

function ConditionCard({ condition, entries }) {
  const meta = CONDITION_META[condition] || { label: condition, emoji: '📊', color: '#5b8dee' };

  if (!entries || entries.length === 0) {
    return (
      <div className={styles.card}>
        <div className={styles.cardHeader}>
          <span className={styles.cardEmoji}>{meta.emoji}</span>
          <div>
            <div className={styles.cardLabel}>{meta.label}</div>
            <div className={styles.cardSub}>No assessments yet</div>
          </div>
        </div>
        <div className={styles.noData}>
          Complete an assessment to start tracking your trend
        </div>
      </div>
    );
  }

  // Sort oldest→newest
  const sorted = [...entries].sort((a, b) => new Date(a.created_at) - new Date(b.created_at));
  const latest = sorted[sorted.length - 1];
  const previous = sorted.length > 1 ? sorted[sorted.length - 2] : null;

  const latestPct = (latest.risk_probability * 100).toFixed(1);
  const riskColor = RISK_COLORS[latest.risk_category] || meta.color;

  const delta = previous
    ? ((latest.risk_probability - previous.risk_probability) * 100).toFixed(1)
    : null;

  const points = sorted.map(e => e.risk_probability * 100);

  return (
    <div className={styles.card}>
      <div className={styles.cardHeader}>
        <span className={styles.cardEmoji}>{meta.emoji}</span>
        <div className={styles.cardInfo}>
          <div className={styles.cardLabel}>{meta.label}</div>
          <div className={styles.cardSub}>{sorted.length} assessment{sorted.length !== 1 ? 's' : ''}</div>
        </div>
        <div className={styles.cardRisk}>
          <span className={styles.riskPct} style={{ color: riskColor }}>
            {latestPct}%
          </span>
          <span className={styles.riskCat} style={{ color: riskColor }}>
            {latest.risk_category}
          </span>
        </div>
      </div>

      {/* Trend delta */}
      {delta !== null && (
        <div className={`${styles.delta} ${parseFloat(delta) < 0 ? styles.deltaGood : styles.deltaBad}`}>
          {parseFloat(delta) < 0 ? '↓' : '↑'} {Math.abs(parseFloat(delta)).toFixed(1)}% since last assessment
          {parseFloat(delta) < 0 ? ' — improving' : ' — needs attention'}
        </div>
      )}

      {/* Sparkline */}
      <Sparkline points={points} color={meta.color} />

      {/* Timeline */}
      <div className={styles.timeline}>
        {sorted.slice(-5).map((e, i) => (
          <div key={e.result_id || i} className={styles.timelineItem}>
            <div className={styles.timelineDot} style={{ background: RISK_COLORS[e.risk_category] || '#888' }} />
            <div className={styles.timelineInfo}>
              <span className={styles.timelineDate}>{formatDate(e.created_at)}</span>
              <span className={styles.timelinePct} style={{ color: RISK_COLORS[e.risk_category] }}>
                {(e.risk_probability * 100).toFixed(1)}%
              </span>
              <span className={styles.timelineCat}>{e.risk_category}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Main component ─────────────────────────────────────────────────────────────

export default function TrendDashboard({ userId }) {
  const [history, setHistory] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!userId) { setIsLoading(false); return; }
    getAssessmentHistory(userId, 30)
      .then(data => {
        setHistory(data.history || []);
        setIsLoading(false);
      })
      .catch(e => {
        setError(e.message);
        setIsLoading(false);
      });
  }, [userId]);

  // Group by condition
  const byCondition = {};
  for (const cond of ['diabetes', 'cvd', 'hypertension']) {
    byCondition[cond] = history.filter(h => h.condition === cond);
  }

  const totalAssessments = history.length;
  const improving = Object.values(byCondition).filter(entries => {
    if (entries.length < 2) return false;
    const sorted = [...entries].sort((a, b) => new Date(a.created_at) - new Date(b.created_at));
    return sorted[sorted.length - 1].risk_probability < sorted[sorted.length - 2].risk_probability;
  }).length;

  if (!userId) {
    return (
      <div className={styles.empty}>
        <div className={styles.emptyIcon}>📈</div>
        <h3>Track Your Progress</h3>
        <p>Complete your first assessment to start tracking your health trend over time.</p>
      </div>
    );
  }

  if (isLoading) {
    return <div className={styles.loading}>Loading your health history…</div>;
  }

  if (error) {
    return <div className={styles.error}>Failed to load history: {error}</div>;
  }

  return (
    <div className={styles.root}>
      {/* Summary banner */}
      {totalAssessments > 0 && (
        <div className={styles.summary}>
          <div className={styles.summaryItem}>
            <div className={styles.summaryValue}>{totalAssessments}</div>
            <div className={styles.summaryLabel}>Total assessments</div>
          </div>
          <div className={styles.summaryDivider} />
          <div className={styles.summaryItem}>
            <div className={styles.summaryValue} style={{ color: '#16a34a' }}>{improving}</div>
            <div className={styles.summaryLabel}>Conditions improving</div>
          </div>
          <div className={styles.summaryDivider} />
          <div className={styles.summaryItem}>
            <div className={styles.summaryValue}>{Object.keys(byCondition).filter(c => byCondition[c].length > 0).length}</div>
            <div className={styles.summaryLabel}>Conditions tracked</div>
          </div>
        </div>
      )}

      {totalAssessments === 0 ? (
        <div className={styles.empty}>
          <div className={styles.emptyIcon}>📈</div>
          <h3>No assessments yet</h3>
          <p>Complete your first risk assessment to see your trend here.</p>
        </div>
      ) : (
        <div className={styles.cards}>
          {['diabetes', 'cvd', 'hypertension'].map(cond => (
            <ConditionCard key={cond} condition={cond} entries={byCondition[cond]} />
          ))}
        </div>
      )}
    </div>
  );
}
