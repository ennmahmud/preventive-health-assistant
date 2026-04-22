import { useState, useEffect, useRef } from 'react';
import WhatIfSimulator from './WhatIfSimulator';
import CohortComparison from './CohortComparison';
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

export default function AssessmentResults({ result, condition, answers, onStartNew, onContinueChat, userId }) {
  const [showAllRecs, setShowAllRecs] = useState(false);
  const [showAllFactors, setShowAllFactors] = useState(false);
  const [showSimulator, setShowSimulator] = useState(false);
  const scrollRef = useRef(null);

  // Always start at the top when a result is shown
  useEffect(() => {
    const el = scrollRef.current;
    if (!el) return;
    // requestAnimationFrame ensures the DOM has painted before scrolling
    const raf = requestAnimationFrame(() => { el.scrollTop = 0; });
    return () => cancelAnimationFrame(raf);
  }, [result]);

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

  // Cohort comparison — extract age + gender from answers
  const cohortAge    = answers?.age ?? null;
  const cohortGender = answers?.gender ?? answers?.biological_sex ?? null;

  const recs = recommendations || [];
  const sortedRecs = [
    ...recs.filter(r => r.priority === 'high'),
    ...recs.filter(r => r.priority === 'medium'),
    ...recs.filter(r => r.priority === 'low'),
  ];
  const visibleRecs = showAllRecs ? sortedRecs : sortedRecs.slice(0, 4);

  return (
    <div className={styles.results} ref={scrollRef}>
      {/* ── Risk summary card ── */}
      <div className={styles.riskCard} style={{ borderColor: color, color }}>
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

      {/* ── Cohort comparison ── */}
      {cohortAge && cohortGender && (
        <CohortComparison
          condition={condition}
          age={cohortAge}
          gender={cohortGender}
          userRisk={risk?.risk_probability ?? null}
        />
      )}

      {/* ── What's driving your risk ── */}
      {allFactors.length > 0 && (
        <div className={styles.section}>
          <h3 className={styles.sectionTitle}>What&apos;s driving your risk?</h3>
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

      {/* ── What-If Simulator ── */}
      {answers && Object.keys(answers).length > 0 && (
        <div>
          <button
            className={styles.toggleBtn}
            onClick={() => setShowSimulator(v => !v)}
          >
            {showSimulator ? '▲ Hide Simulator' : '✦ What If I Changed My Lifestyle?'}
          </button>
          {showSimulator && (
            <div style={{ marginTop: 12 }}>
              <WhatIfSimulator
                condition={condition}
                baselineAnswers={answers}
                baselineRisk={result?.risk}
                userId={userId}
              />
            </div>
          )}
        </div>
      )}

      {/* ── Actions ── */}
      <div className={styles.actions}>
        <button className={styles.newBtn} onClick={onStartNew}>
          ← New Assessment
        </button>
        <button
          className={styles.printBtn}
          onClick={() => printReport({ result, condition, allFactors, sortedRecs, narrative, pct, category, color })}
          title="Download / Print report"
        >
          🖨 Export
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

function printReport({ result, condition, allFactors, sortedRecs, narrative, pct, category, color }) {
  const condName = CONDITION_NAMES[condition] || condition;
  const now = new Date().toLocaleString('en-GB', { dateStyle: 'long', timeStyle: 'short' });

  const factorsRows = allFactors.map(f => {
    const name = PLAIN_FACTOR_NAMES[f.feature] || cleanFeatureName(f.feature);
    const isRisk = f.direction === 'risk';
    const dir = isRisk ? '↑ Increases risk' : '↓ Protective';
    const dirColor = isRisk ? '#dc2626' : '#16a34a';
    return `<tr>
      <td style="padding:8px 12px;border-bottom:1px solid #e5e7eb">${name}</td>
      <td style="padding:8px 12px;border-bottom:1px solid #e5e7eb;color:${dirColor};font-weight:600">${dir}</td>
    </tr>`;
  }).join('');

  const recItems = sortedRecs.map(r => {
    const pc = r.priority === 'high' ? '#dc2626' : r.priority === 'medium' ? '#d97706' : '#16a34a';
    const pl = r.priority ? r.priority.charAt(0).toUpperCase() + r.priority.slice(1) : 'Medium';
    const cat = r.category?.replace(/_/g, ' ') || '';
    return `<div style="margin-bottom:14px;padding:14px 16px;border-radius:8px;border:1px solid #e5e7eb;border-left:4px solid ${pc};page-break-inside:avoid">
      <div style="font-size:0.75rem;font-weight:700;text-transform:uppercase;letter-spacing:0.05em;color:${pc};margin-bottom:5px">${pl} Priority — ${cat}</div>
      <p style="margin:0;font-size:0.92rem;color:#1f2937;line-height:1.5">${r.recommendation}</p>
    </div>`;
  }).join('');

  const barWidth = `${Math.min(parseFloat(pct), 100)}%`;

  const html = `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Health Risk Report — ${condName}</title>
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');
    body {
      font-family: 'Inter', Georgia, serif;
      max-width: 780px;
      margin: 40px auto;
      padding: 0 28px;
      color: #111827;
      line-height: 1.65;
      -webkit-print-color-adjust: exact;
      print-color-adjust: exact;
    }
    .header { border-bottom: 2px solid #e5e7eb; padding-bottom: 18px; margin-bottom: 28px; }
    .header h1 { font-size: 1.5rem; margin: 0 0 4px; color: #111827; }
    .meta { color: #6b7280; font-size: 0.88rem; }
    .risk-card {
      border: 2px solid ${color};
      border-radius: 10px;
      padding: 22px 24px;
      margin-bottom: 32px;
      background: #fafafa;
    }
    .risk-top { display: flex; align-items: center; gap: 20px; margin-bottom: 14px; }
    .risk-pct { font-size: 2.4rem; font-weight: 900; color: ${color}; letter-spacing: -0.02em; }
    .risk-cat { font-size: 1.2rem; font-weight: 700; color: ${color}; }
    .cond-name { font-size: 0.8rem; color: #6b7280; margin-bottom: 3px; }
    .bar-track { height: 10px; background: #e5e7eb; border-radius: 999px; overflow: hidden; margin: 0 0 16px; }
    .bar-fill { height: 100%; background: ${color}; width: ${barWidth}; border-radius: 999px; }
    .narrative {
      background: #f9fafb;
      border-left: 4px solid ${color};
      padding: 12px 16px;
      border-radius: 4px;
      font-style: italic;
      color: #374151;
      margin-bottom: 14px;
    }
    .disclaimer { font-size: 0.78rem; color: #9ca3af; font-style: italic; }
    h2 { font-size: 1rem; font-weight: 700; border-bottom: 1px solid #e5e7eb; padding-bottom: 6px; margin: 28px 0 14px; color: #374151; }
    table { width: 100%; border-collapse: collapse; font-size: 0.9rem; }
    thead th { text-align: left; padding: 8px 12px; background: #f9fafb; font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.05em; color: #6b7280; border-bottom: 2px solid #e5e7eb; }
    .footer { margin-top: 40px; border-top: 1px solid #e5e7eb; padding-top: 18px; font-size: 0.8rem; color: #6b7280; font-style: italic; }
    @media print {
      body { margin: 24px; }
      .risk-card { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
    }
  </style>
</head>
<body>
  <div class="header">
    <h1>Health Risk Assessment Report</h1>
    <p class="meta">Condition: <strong>${condName}</strong> &nbsp;·&nbsp; Generated: ${now}</p>
  </div>

  <div class="risk-card">
    <div class="risk-top">
      <div>
        <div class="cond-name">${condName}</div>
        <div class="risk-cat">${category} Risk</div>
      </div>
      <div class="risk-pct">${pct}%</div>
    </div>
    <div class="bar-track"><div class="bar-fill"></div></div>
    ${narrative ? `<div class="narrative">${narrative}</div>` : ''}
    <p class="disclaimer">Screening tool only — not a medical diagnosis. Always consult a qualified healthcare professional.</p>
  </div>

  ${allFactors.length > 0 ? `
  <h2>What's Driving Your Risk</h2>
  <table>
    <thead><tr><th>Factor</th><th>Influence</th></tr></thead>
    <tbody>${factorsRows}</tbody>
  </table>` : ''}

  ${sortedRecs.length > 0 ? `
  <h2>Personalised Recommendations</h2>
  ${recItems}` : ''}

  <div class="footer">
    This report was generated by the Preventive Health Assistant — an AI-powered screening tool
    trained on NHANES population data. It is not a substitute for professional medical advice,
    diagnosis, or treatment. Always seek the guidance of a qualified healthcare provider
    with questions you may have regarding your health.
  </div>
</body>
</html>`;

  const blob = new Blob([html], { type: 'text/html;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const win = window.open(url, '_blank');
  if (win) {
    win.addEventListener('load', () => {
      setTimeout(() => {
        win.print();
        URL.revokeObjectURL(url);
      }, 300);
    });
  } else {
    // Fallback: direct download
    const a = document.createElement('a');
    a.href = url;
    a.download = `health-risk-report-${condition}-${new Date().toISOString().slice(0, 10)}.html`;
    a.click();
    URL.revokeObjectURL(url);
  }
}
