/* WhatIfSimulator */

import { useState, useCallback } from 'react';
import { simulateWhatIf } from '../utils/api';
import styles from './WhatIfSimulator.module.css';

const RISK_COLORS = {
  Low: '#16a34a',
  Moderate: '#ca8a04',
  High: '#ea580c',
  'Very High': '#dc2626',
};

// Lifestyle levers available per condition
const LEVERS = {
  diabetes: [
    { key: 'smoking_status', label: 'Smoking', type: 'choice', options: [{ v: 'never', l: 'Never smoked' }, { v: 'former', l: 'Former smoker' }, { v: 'current', l: 'Current smoker' }] },
    { key: 'activity_level', label: 'Activity level', type: 'choice', options: [{ v: 'sedentary', l: 'Sedentary' }, { v: 'light', l: 'Light' }, { v: 'moderate', l: 'Moderate' }, { v: 'active', l: 'Active' }] },
    { key: 'diet_quality', label: 'Diet quality', type: 'choice', options: [{ v: 'poor', l: 'Poor' }, { v: 'mixed', l: 'Mixed' }, { v: 'healthy', l: 'Healthy' }] },
    { key: 'sugar_intake', label: 'Sugar intake', type: 'choice', options: [{ v: 'heavy', l: 'Heavy' }, { v: 'daily', l: 'Daily' }, { v: 'occasional', l: 'Occasional' }, { v: 'none', l: 'None/Rare' }] },
    { key: 'sleep_hours', label: 'Sleep', type: 'choice', options: [{ v: 'under5', l: '<5 hrs' }, { v: '5to6', l: '5–6 hrs' }, { v: '7to8', l: '7–8 hrs' }, { v: 'over8', l: '>8 hrs' }] },
    { key: 'stress_level', label: 'Stress level', type: 'slider', min: 1, max: 5, unit: '/5' },
    { key: 'weight_kg', label: 'Weight', type: 'slider', min: 40, max: 180, unit: ' kg' },
  ],
  cvd: [
    { key: 'smoking_status', label: 'Smoking', type: 'choice', options: [{ v: 'current', l: 'Current smoker' }, { v: 'former', l: 'Former smoker' }, { v: 'never', l: 'Never smoked' }] },
    { key: 'activity_level', label: 'Activity level', type: 'choice', options: [{ v: 'sedentary', l: 'Sedentary' }, { v: 'light', l: 'Light' }, { v: 'moderate', l: 'Moderate' }, { v: 'active', l: 'Active' }] },
    { key: 'diet_quality', label: 'Diet quality', type: 'choice', options: [{ v: 'poor', l: 'Poor' }, { v: 'mixed', l: 'Mixed' }, { v: 'healthy', l: 'Healthy' }] },
    { key: 'alcohol_weekly', label: 'Alcohol', type: 'choice', options: [{ v: 'heavy', l: 'Heavy (>14 units)' }, { v: 'moderate', l: 'Moderate' }, { v: 'light', l: 'Light' }, { v: 'none', l: 'None' }] },
    { key: 'stress_level', label: 'Stress level', type: 'slider', min: 1, max: 5, unit: '/5' },
    { key: 'weight_kg', label: 'Weight', type: 'slider', min: 40, max: 180, unit: ' kg' },
  ],
  hypertension: [
    { key: 'salt_intake', label: 'Salt intake', type: 'choice', options: [{ v: 'high', l: 'High' }, { v: 'moderate', l: 'Moderate' }, { v: 'low', l: 'Low' }] },
    { key: 'activity_level', label: 'Activity level', type: 'choice', options: [{ v: 'sedentary', l: 'Sedentary' }, { v: 'light', l: 'Light' }, { v: 'moderate', l: 'Moderate' }, { v: 'active', l: 'Active' }] },
    { key: 'alcohol_weekly', label: 'Alcohol', type: 'choice', options: [{ v: 'heavy', l: 'Heavy' }, { v: 'moderate', l: 'Moderate' }, { v: 'light', l: 'Light' }, { v: 'none', l: 'None' }] },
    { key: 'stress_level', label: 'Stress level', type: 'slider', min: 1, max: 5, unit: '/5' },
    { key: 'sleep_hours', label: 'Sleep', type: 'choice', options: [{ v: 'under5', l: '<5 hrs' }, { v: '5to6', l: '5–6 hrs' }, { v: '7to8', l: '7–8 hrs' }, { v: 'over8', l: '>8 hrs' }] },
    { key: 'weight_kg', label: 'Weight', type: 'slider', min: 40, max: 180, unit: ' kg' },
    { key: 'diet_quality', label: 'Diet quality', type: 'choice', options: [{ v: 'poor', l: 'Poor' }, { v: 'mixed', l: 'Mixed' }, { v: 'healthy', l: 'Healthy' }] },
  ],
};

export default function WhatIfSimulator({ condition, baselineAnswers, baselineRisk, userId }) {
  const levers = LEVERS[condition] || [];

  // Changes relative to baseline
  const [changes, setChanges] = useState({});
  const [simResult, setSimResult] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleChange = (key, value) => {
    setChanges(prev => ({ ...prev, [key]: value }));
    setSimResult(null); // clear stale result
  };

  const handleReset = () => {
    setChanges({});
    setSimResult(null);
    setError(null);
  };

  const runSimulation = useCallback(async () => {
    if (Object.keys(changes).length === 0) return;
    setIsLoading(true);
    setError(null);
    try {
      const res = await simulateWhatIf(condition, baselineAnswers, changes, userId);
      setSimResult(res);
    } catch (e) {
      setError(e.message || 'Simulation failed');
    } finally {
      setIsLoading(false);
    }
  }, [condition, baselineAnswers, changes, userId]);

  const baselinePct = baselineRisk?.risk_percentage ?? baselineRisk?.risk_probability * 100 ?? 0;
  const baselineCat = baselineRisk?.risk_category ?? 'Unknown';
  const simPct = simResult?.simulated_risk?.risk_percentage ?? null;
  const simCat = simResult?.simulated_risk?.risk_category ?? null;
  const delta = simResult?.delta_percentage ?? null;
  const hasChanges = Object.keys(changes).length > 0;

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <h3 className={styles.title}>What If I Changed My Lifestyle?</h3>
        <p className={styles.subtitle}>
          Adjust the sliders to see how lifestyle changes would affect your risk.
        </p>
      </div>

      {/* Risk comparison bar */}
      <div className={styles.comparison}>
        <div className={styles.comparisonItem}>
          <div className={styles.compLabel}>Current Risk</div>
          <div className={styles.compValue} style={{ color: RISK_COLORS[baselineCat] }}>
            {baselinePct.toFixed(1)}%
          </div>
          <div className={styles.compCat} style={{ color: RISK_COLORS[baselineCat] }}>
            {baselineCat}
          </div>
        </div>

        <div className={styles.arrow}>
          {delta !== null ? (
            <span className={delta < 0 ? styles.arrowGood : styles.arrowBad}>
              {delta < 0 ? '↓' : '↑'} {Math.abs(delta).toFixed(1)}%
            </span>
          ) : (
            <span className={styles.arrowNeutral}>→</span>
          )}
        </div>

        <div className={styles.comparisonItem}>
          <div className={styles.compLabel}>Simulated Risk</div>
          {simPct !== null ? (
            <>
              <div className={styles.compValue} style={{ color: RISK_COLORS[simCat] }}>
                {simPct.toFixed(1)}%
              </div>
              <div className={styles.compCat} style={{ color: RISK_COLORS[simCat] }}>
                {simCat}
              </div>
            </>
          ) : (
            <div className={styles.compPlaceholder}>—</div>
          )}
        </div>
      </div>

      {/* Progress bar comparison */}
      {simPct !== null && (
        <div className={styles.bars}>
          <div className={styles.barRow}>
            <span className={styles.barLabel}>Before</span>
            <div className={styles.barTrack}>
              <div
                className={styles.barFill}
                style={{ width: `${baselinePct}%`, background: RISK_COLORS[baselineCat] }}
              />
            </div>
          </div>
          <div className={styles.barRow}>
            <span className={styles.barLabel}>After</span>
            <div className={styles.barTrack}>
              <div
                className={styles.barFill}
                style={{ width: `${simPct}%`, background: RISK_COLORS[simCat] }}
              />
            </div>
          </div>
        </div>
      )}

      {/* Levers */}
      <div className={styles.levers}>
        {levers.map(lever => {
          const currentVal = changes[lever.key] ?? baselineAnswers?.[lever.key] ?? null;
          return (
            <div key={lever.key} className={styles.lever}>
              <div className={styles.leverHeader}>
                <span className={styles.leverLabel}>{lever.label}</span>
                {changes[lever.key] !== undefined && (
                  <span className={styles.changedBadge}>changed</span>
                )}
              </div>

              {lever.type === 'choice' ? (
                <div className={styles.choiceGroup}>
                  {lever.options.map(opt => (
                    <button
                      key={opt.v}
                      className={`${styles.choiceBtn} ${currentVal === opt.v ? styles.choiceActive : ''}`}
                      onClick={() => handleChange(lever.key, opt.v)}
                    >
                      {opt.l}
                    </button>
                  ))}
                </div>
              ) : (
                <div className={styles.sliderRow}>
                  <input
                    type="range"
                    min={lever.min}
                    max={lever.max}
                    value={currentVal ?? Math.round((lever.min + lever.max) / 2)}
                    onChange={e => handleChange(lever.key, Number(e.target.value))}
                    className={styles.slider}
                  />
                  <span className={styles.sliderVal}>
                    {currentVal ?? '—'}{lever.unit}
                  </span>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {error && <p className={styles.error}>{error}</p>}

      {/* Actions */}
      <div className={styles.actions}>
        <button
          className={styles.resetBtn}
          onClick={handleReset}
          disabled={!hasChanges && !simResult}
        >
          Reset
        </button>
        <button
          className={styles.simulateBtn}
          onClick={runSimulation}
          disabled={!hasChanges || isLoading}
        >
          {isLoading ? 'Simulating…' : `Simulate ${Object.keys(changes).length} Change${Object.keys(changes).length !== 1 ? 's' : ''}`}
        </button>
      </div>

      {simResult && delta !== null && (
        <div className={`${styles.summary} ${delta < 0 ? styles.summaryGood : styles.summaryBad}`}>
          {delta < 0
            ? `These changes could reduce your ${condition} risk by ${Math.abs(delta).toFixed(1)} percentage points.`
            : `These changes would increase your risk by ${delta.toFixed(1)} percentage points.`}
        </div>
      )}
    </div>
  );
}
