/**
 * ExplanationPanel
 * Renders SHAP-based risk factor contributions as a horizontal bar chart.
 * Accepts the `explanation` object returned by the /assess endpoints.
 */

import styles from './ExplanationPanel.module.css';

export default function ExplanationPanel({ explanation }) {
  if (!explanation) return null;

  const { top_risk_factors = [], top_protective_factors = [], base_risk, summary } = explanation;

  // Combine and sort by absolute contribution
  const allFactors = [
    ...top_risk_factors.map((f) => ({ ...f, direction: 'risk' })),
    ...top_protective_factors.map((f) => ({ ...f, direction: 'protective' })),
  ].sort((a, b) => Math.abs(b.shap_value ?? b.contribution ?? 0) - Math.abs(a.shap_value ?? a.contribution ?? 0))
   .slice(0, 8);

  const maxVal = Math.max(...allFactors.map((f) => Math.abs(f.shap_value ?? f.contribution ?? 0)), 0.01);

  return (
    <div className={styles.panel}>
      <h3 className={styles.title}>What's driving your risk?</h3>
      {summary && <p className={styles.summary}>{summary}</p>}

      <div className={styles.chart}>
        {allFactors.map((f, i) => {
          const raw = f.shap_value ?? f.contribution ?? 0;
          const pct = (Math.abs(raw) / maxVal) * 100;
          const isRisk = f.direction === 'risk';
          return (
            <div key={i} className={styles.row}>
              <span className={styles.featureName}>
                {formatFeature(f.feature ?? f.factor)}
              </span>
              <div className={styles.barWrap}>
                <div
                  className={`${styles.bar} ${isRisk ? styles.riskBar : styles.protectBar}`}
                  style={{ width: `${pct}%` }}
                />
              </div>
              <span className={`${styles.value} ${isRisk ? styles.riskText : styles.protectText}`}>
                {isRisk ? '▲' : '▼'} {f.value !== undefined ? String(f.value) : ''}
              </span>
            </div>
          );
        })}
      </div>

      {base_risk !== undefined && (
        <p className={styles.baseRisk}>
          Population baseline risk: <strong>{(base_risk * 100).toFixed(1)}%</strong>
        </p>
      )}
    </div>
  );
}

function formatFeature(name) {
  if (!name) return '';
  return name.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}
