/* CohortComparison */

import { useState, useEffect } from 'react';
import { getCohortComparison } from '../utils/api';
import styles from './CohortComparison.module.css';

const CONDITION_NAMES = {
  diabetes: 'Diabetes',
  cvd: 'Heart Disease',
  hypertension: 'Hypertension',
};

export default function CohortComparison({ condition, age, gender, userRisk }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!condition || !age || !gender || userRisk == null) return;
    // Normalise gender value (wizard uses "male"/"female"; some paths use 0/1)
    const genderStr = gender === 1 || gender === '1' ? 'male'
                    : gender === 0 || gender === '0' ? 'female'
                    : String(gender).toLowerCase();
    if (!['male', 'female'].includes(genderStr)) return;

    getCohortComparison(condition, age, genderStr, userRisk)
      .then(setData)
      .catch(e => setError(e.message));
  }, [condition, age, gender, userRisk]);

  if (error || !data) return null;

  const userPct     = (data.user_risk * 100).toFixed(1);
  const cohortPct   = (data.cohort_avg_risk * 100).toFixed(1);
  const ratio       = data.ratio_vs_cohort;
  const delta       = data.delta_vs_cohort_pct;
  const isHigher    = delta > 0;

  // Bar widths — normalised so the larger fills 100%
  const maxVal = Math.max(data.user_risk, data.cohort_avg_risk, 0.01);
  const userBar   = Math.min((data.user_risk / maxVal) * 100, 100);
  const cohortBar = Math.min((data.cohort_avg_risk / maxVal) * 100, 100);

  const ratioLabel = ratio === null
    ? null
    : ratio >= 2
      ? `${ratio.toFixed(1)}× higher than average`
      : ratio <= 0.5
        ? `${(1 / ratio).toFixed(1)}× lower than average`
        : delta > 0
          ? `+${delta.toFixed(1)}% above average`
          : `${Math.abs(delta).toFixed(1)}% below average`;

  const ratioColor = isHigher ? '#ef4444' : '#16a34a';

  return (
    <div className={styles.card}>
      <div className={styles.header}>
        <span className={styles.title}>How do you compare?</span>
        <span className={styles.sub}>
          vs. {data.age_bucket}-year-old {data.gender}s in NHANES
        </span>
      </div>

      <div className={styles.bars}>
        {/* User bar */}
        <div className={styles.barRow}>
          <span className={styles.barLabel}>You</span>
          <div className={styles.barTrack}>
            <div
              className={styles.barFill}
              style={{ width: `${userBar}%`, background: isHigher ? '#ef4444' : '#16a34a' }}
            />
          </div>
          <span className={styles.barPct} style={{ color: isHigher ? '#ef4444' : '#16a34a' }}>
            {userPct}%
          </span>
        </div>

        {/* Cohort bar */}
        <div className={styles.barRow}>
          <span className={styles.barLabel}>Average</span>
          <div className={styles.barTrack}>
            <div
              className={styles.barFill}
              style={{ width: `${cohortBar}%`, background: '#6b7280' }}
            />
          </div>
          <span className={styles.barPct} style={{ color: 'var(--color-text-muted)' }}>
            {cohortPct}%
          </span>
        </div>
      </div>

      {ratioLabel && (
        <div className={styles.badge} style={{ color: ratioColor, borderColor: ratioColor }}>
          {isHigher ? '▲' : '▼'} {ratioLabel}
        </div>
      )}

      <p className={styles.footnote}>
        Based on {data.cohort_count.toLocaleString()} NHANES participants in your demographic group.
      </p>
    </div>
  );
}
