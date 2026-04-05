import { useState } from 'react';
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

// Plain-language names for SHAP features
const PLAIN_FACTOR_NAMES = {
  hba1c: 'Blood sugar (HbA1c)',
  fasting_glucose: 'Fasting blood sugar',
  bmi: 'Body weight (BMI)',
  age: 'Age',
  total_cholesterol: 'Total cholesterol',
  hdl_cholesterol: 'HDL (good cholesterol)',
  systolic_bp: 'Blood pressure',
  sedentary_minutes: 'Sedentary time',
  vigorous_rec_minutes: 'Vigorous exercise',
  moderate_rec_minutes: 'Moderate exercise',
  walk_minutes: 'Daily walking',
  smoking_status: 'Smoking history',
  smoked_100: 'Smoking history',
  alcohol_use: 'Alcohol intake',
  diet_quality: 'Diet quality',
  salt_intake: 'Salt intake',
  sleep_hours: 'Sleep quality',
  stress_level: 'Stress level',
  family_diabetes: 'Family history (diabetes)',
  family_cvd: 'Family history (heart disease)',
  family_htn: 'Family history (hypertension)',
  waist_circumference: 'Waist circumference',
  sugar_intake: 'Sugar intake',
  diabetes: 'Diabetes diagnosis',
  self_reported_hbp: 'High blood pressure history',
  self_reported_hchol: 'High cholesterol history',
  prediabetes_flag: 'Pre-diabetes',
  cardiac_symptoms: 'Cardiac symptoms',
  race_ethnicity: 'Ethnic background',
};

// Plain-English risk interpretation per condition + category
const RISK_NARRATIVES = {
  diabetes: {
    Low: 'Your lifestyle profile suggests a low chance of developing type 2 diabetes. Keeping active and eating well are your strongest protections.',
    Moderate: 'Some risk factors are present. Small changes to your diet and activity level can meaningfully reduce this risk over time.',
    High: 'Several risk factors are elevated. Speak to your doctor about blood sugar monitoring and a diabetes prevention plan.',
    'Very High': 'Multiple significant risk factors detected. Early action is important — please consult a healthcare professional.',
  },
  cvd: {
    Low: 'Your cardiovascular risk appears low based on your lifestyle profile. Staying active and keeping stress in check will maintain this.',
    Moderate: 'Some heart risk factors are present. Focus on diet, regular exercise, and managing stress to reduce your risk.',
    High: 'Your heart disease risk is elevated. A consultation with your doctor — including cholesterol and blood pressure checks — is strongly recommended.',
    'Very High': 'Multiple serious cardiovascular risk factors detected. Please seek medical advice as soon as possible.',
  },
  hypertension: {
    Low: 'Your risk of developing high blood pressure appears low. Maintaining a low-salt diet and staying active keeps it that way.',
    Moderate: 'Some factors are increasing your hypertension risk. Reducing salt, managing stress, and staying active will help.',
    High: 'Your hypertension risk is elevated. A blood pressure check and lifestyle review with your doctor is strongly advised.',
    'Very High': 'Multiple significant risk factors for hypertension detected. Please see a healthcare professional soon.',
  },
};

export default function AssessmentResults({ result, condition, onStartNew, onContinueChat }) {
  const [showAllRecs, setShowAllRecs] = useState(false);
  const [showAllFactors, setShowAllFactors] = useState(false);

  if (!result) return null;

  const { risk, explanation, recommendations } = result;
  const category = risk?.risk_category || 'Unknown';
  const pct = ((risk?.risk_probability || 0) * 100).toFixed(1);
  const color = RISK_COLORS[category] || '#6b7280';
  const emoji = RISK_EMOJIS[category] || '⚪';
  const narrative = RISK_NARRATIVES[condition]?.[category];

  // All factors combined, sorted by absolute SHAP magnitude
  const allRiskFactors = explanation?.top_risk_factors || [];
  const allProtectFactors = explanation?.top_protective_factors || [];
  const allFactors = [
    ...allRiskFactors.map(f => ({ ...f, direction: 'risk' })),
    ...allProtectFactors.map(f => ({ ...f, direction: 'protective' })),
  ].sort((a, b) => Math.abs(b.shap_value || 0) - Math.abs(a.shap_value || 0));

  const maxShap = allFactors.reduce((m, f) => Math.max(m, Math.abs(f.shap_value || 0)), 0.001);
  const visibleFactors = showAllFactors ? allFactors : allFactors.slice(0, 5);

  const recs = recommendations || [];
  const sortedRecs = [
    ...recs.filter(r => r.priority === 'high'),
    ...recs.filter(r => r.priority === 'medium'),
    ...recs.filter(r => r.priority === 'low'),
  ];
  const visibleRecs = showAllRecs ? sortedRecs : sortedRecs.slice(0, 4);

  return (
    <div className={styles.results}>
      {/* ── Risk summary card ── */}
      <div className={styles.riskCard} style={{ borderColor: color }}>
        <div className={styles.riskHeader}>
          <span className={styles.emoji}>{emoji}</span>
          <div>
            <div className={styles.conditionName}>{CONDITION_NAMES[condition] || condition}</div>
            <div className={styles.riskCategory} style={{ color }}>{category} Risk</div>
          </div>
          <div className={styles.riskPct} style={{ color }}>{pct}%</div>
        </div>

        <div className={styles.barTrack}>
          <div
            className={styles.barFill}
            style={{ width: `${Math.min(parseFloat(pct), 100)}%`, background: color }}
          />
        </div>

        {narrative && <p className={styles.narrative}>{narrative}</p>}

        <p className={styles.disclaimer}>
          Screening tool only — not a medical diagnosis. Always consult a qualified healthcare professional.
        </p>
      </div>

      {/* ── What's driving your risk ── */}
      {allFactors.length > 0 && (
        <div className={styles.section}>
          <h3 className={styles.sectionTitle}>What's driving your risk?</h3>
          <div className={styles.factors}>
            {visibleFactors.map((f) => {
              const isRisk = f.direction === 'risk';
              const barColor = isRisk ? '#ef4444' : '#16a34a';
              const barWidth = `${Math.min((Math.abs(f.shap_value || 0) / maxShap) * 100, 100)}%`;
              const name = PLAIN_FACTOR_NAMES[f.feature] || cleanFeatureName(f.feature);
              return (
                <div key={f.feature} className={styles.factorRow}>
                  <span className={styles.factorName}>{name}</span>
                  <div className={styles.factorBar}>
                    <div className={styles.factorFill} style={{ width: barWidth, background: barColor }} />
                  </div>
                  <span className={styles.factorTag} style={{ color: barColor }}>
                    {isRisk ? '↑ risk' : '↓ protective'}
                  </span>
                </div>
              );
            })}
          </div>
          {allFactors.length > 5 && (
            <button className={styles.toggleBtn} onClick={() => setShowAllFactors(v => !v)}>
              {showAllFactors ? '▲ Show less' : `▼ Show all ${allFactors.length} factors`}
            </button>
          )}
        </div>
      )}

      {/* ── Recommendations ── */}
      {sortedRecs.length > 0 && (
        <div className={styles.section}>
          <h3 className={styles.sectionTitle}>Personalised Recommendations</h3>
          <div className={styles.recs}>
            {visibleRecs.map((r, i) => (
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
          {sortedRecs.length > 4 && (
            <button className={styles.toggleBtn} onClick={() => setShowAllRecs(v => !v)}>
              {showAllRecs ? '▲ Show fewer' : `▼ Show all ${sortedRecs.length} recommendations`}
            </button>
          )}
        </div>
      )}

      {/* ── Actions ── */}
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
    .replace(/Hdl/, 'HDL');
}
