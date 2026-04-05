/**
 * RiskResultCard
 * Compact visual summary of a completed risk assessment.
 * Shown inline in the chat after a prediction completes.
 */

import styles from './RiskResultCard.module.css';

const CONDITION_LABELS = {
  diabetes: 'Diabetes',
  cvd: 'Cardiovascular Disease',
  hypertension: 'Hypertension',
};

const RISK_CONFIG = {
  Low:       { color: 'var(--color-low)',       emoji: '🟢', bar: 15 },
  Moderate:  { color: 'var(--color-moderate)',  emoji: '🟡', bar: 45 },
  High:      { color: 'var(--color-high)',      emoji: '🟠', bar: 72 },
  'Very High': { color: 'var(--color-very-high)', emoji: '🔴', bar: 92 },
};

export default function RiskResultCard({ result }) {
  if (!result) return null;

  const { condition, risk_percentage, risk_category } = result;
  const cfg = RISK_CONFIG[risk_category] ?? RISK_CONFIG['Moderate'];
  const label = CONDITION_LABELS[condition] ?? condition;

  return (
    <div className={styles.card} style={{ '--risk-color': cfg.color }}>
      <div className={styles.header}>
        <span className={styles.emoji}>{cfg.emoji}</span>
        <div>
          <p className={styles.conditionLabel}>{label} Risk</p>
          <p className={styles.categoryLabel}>{risk_category}</p>
        </div>
        <span className={styles.pct}>{risk_percentage.toFixed(1)}%</span>
      </div>

      {/* Risk bar */}
      <div className={styles.barTrack}>
        <div
          className={styles.barFill}
          style={{ width: `${Math.min(risk_percentage, 100)}%` }}
        />
      </div>

      <p className={styles.hint}>
        Ask me <em>"What should I do?"</em> for recommendations or{' '}
        <em>"What does that mean?"</em> for an explanation.
      </p>
    </div>
  );
}
