import styles from './AssessmentResults.module.css';

const RISK_COLORS = {
  Low: '#16a34a',
  Moderate: '#d97706',
  High: '#ea580c',
  'Very High': '#dc2626',
};

const RISK_EMOJIS = {
  Low: '🟢',
  Moderate: '🟡',
  High: '🟠',
  'Very High': '🔴',
};

const CONDITION_NAMES = {
  diabetes: 'Diabetes',
  cvd: 'Cardiovascular Disease',
  hypertension: 'Hypertension',
};

export default function AssessmentResults({ result, condition, onStartNew, onContinueChat }) {
  if (!result) return null;

  const { risk, explanation, recommendations } = result;
  const category = risk?.risk_category || 'Unknown';
  const pct = ((risk?.risk_probability || 0) * 100).toFixed(1);
  const color = RISK_COLORS[category] || '#6b7280';
  const emoji = RISK_EMOJIS[category] || '⚪';

  return (
    <div className={styles.results}>
      {/* Risk summary */}
      <div className={styles.riskCard} style={{ borderColor: color }}>
        <div className={styles.riskHeader}>
          <span className={styles.emoji}>{emoji}</span>
          <div>
            <div className={styles.conditionName}>{CONDITION_NAMES[condition] || condition}</div>
            <div className={styles.riskCategory} style={{ color }}>{category} Risk</div>
          </div>
          <div className={styles.riskPct} style={{ color }}>{pct}%</div>
        </div>

        {/* Risk bar */}
        <div className={styles.barTrack}>
          <div
            className={styles.barFill}
            style={{ width: `${Math.min(parseFloat(pct), 100)}%`, background: color }}
          />
        </div>

        <p className={styles.disclaimer}>
          Screening tool only — not a medical diagnosis. Always consult a qualified healthcare professional.
        </p>
      </div>

      {/* Explanation */}
      {explanation && (
        <div className={styles.section}>
          <h3 className={styles.sectionTitle}>What's driving your risk?</h3>
          <div className={styles.factors}>
            {explanation.top_risk_factors?.slice(0, 4).map((f) => (
              <div key={f.feature} className={styles.factorRow}>
                <span className={styles.factorName}>{cleanFeatureName(f.feature)}</span>
                <div className={styles.factorBar}>
                  <div
                    className={styles.factorFill}
                    style={{ width: `${Math.min(Math.abs(f.importance || f.shap_value || 0) * 200, 100)}%`, background: '#ef4444' }}
                  />
                </div>
                <span className={styles.factorTag}>↑ risk</span>
              </div>
            ))}
            {explanation.top_protective_factors?.slice(0, 3).map((f) => (
              <div key={f.feature} className={styles.factorRow}>
                <span className={styles.factorName}>{cleanFeatureName(f.feature)}</span>
                <div className={styles.factorBar}>
                  <div
                    className={styles.factorFill}
                    style={{ width: `${Math.min(Math.abs(f.importance || f.shap_value || 0) * 200, 100)}%`, background: '#16a34a' }}
                  />
                </div>
                <span className={styles.factorTag} style={{ color: '#16a34a' }}>↓ protective</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Recommendations */}
      {recommendations?.length > 0 && (
        <div className={styles.section}>
          <h3 className={styles.sectionTitle}>Personalised Recommendations</h3>
          <div className={styles.recs}>
            {recommendations.slice(0, 6).map((r, i) => (
              <div key={i} className={`${styles.rec} ${styles[r.priority || 'medium']}`}>
                <div className={styles.recPriority}>
                  {r.priority === 'high' ? '🔴' : r.priority === 'medium' ? '🟡' : '🟢'}
                </div>
                <div className={styles.recText}>
                  <strong>{r.category?.replace(/_/g, ' ')}</strong>
                  <p>{r.recommendation}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Actions */}
      <div className={styles.actions}>
        <button className={styles.newBtn} onClick={onStartNew}>
          ← Start New Assessment
        </button>
        {onContinueChat && (
          <button className={styles.chatBtn} onClick={onContinueChat}>
            💬 Continue in Chat
          </button>
        )}
      </div>
    </div>
  );
}

function cleanFeatureName(name) {
  return name
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase())
    .replace(/Bmi/, 'BMI')
    .replace(/Hba1c/, 'HbA1c')
    .replace(/Hdl/, 'HDL')
    .replace(/Cvd/, 'CVD')
    .replace(/Bp/, 'BP');
}
