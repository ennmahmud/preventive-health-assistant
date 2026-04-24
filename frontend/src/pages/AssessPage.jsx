import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import TopBar from '../components/layout/TopBar';
import FloatingNav from '../components/layout/FloatingNav';
import ElanCard from '../components/ui/ElanCard';
import ElanButton from '../components/ui/ElanButton';
import RiskRing from '../components/health/RiskRing';
import RiskBadge from '../components/health/RiskBadge';
import ShapBar from '../components/health/ShapBar';
import RecommendationCard from '../components/health/RecommendationCard';
import { assessDiabetes, assessCVD, assessHypertension } from '../api/health';
import { Heart, Activity, Droplets, ChevronLeft, ChevronDown, ChevronUp } from 'lucide-react';

/* ── Condition metadata ─────────────────────────────────────────── */
const CONDITIONS = {
  diabetes:     { label: 'Diabetes',      Icon: Droplets, color: 'var(--elan-am-400)', desc: 'Blood sugar & metabolic risk' },
  cvd:          { label: 'Heart Disease', Icon: Heart,    color: 'var(--elan-tc-400)', desc: 'Cardiovascular event risk' },
  hypertension: { label: 'Hypertension',  Icon: Activity, color: 'var(--elan-sg-600)', desc: 'High blood pressure risk' },
};

const GENDER_OPTIONS   = [{ value: 'male', label: 'Male' }, { value: 'female', label: 'Female' }];
const SMOKING_OPTIONS  = [{ value: 'never', label: 'Never smoked' }, { value: 'former', label: 'Former smoker' }, { value: 'current', label: 'Current smoker' }];
const BOOL_OPTIONS     = [{ value: 'false', label: 'No' }, { value: 'true', label: 'Yes' }];

/* Required fields — same for all conditions */
const REQUIRED_FIELDS = [
  { key: 'age',    label: 'Age',            type: 'number', unit: 'years', ph: '45',  min: 18, max: 120 },
  { key: 'gender', label: 'Biological sex', type: 'select', options: GENDER_OPTIONS },
];

/* Optional basic fields */
const BASIC_OPTIONAL = [
  { key: 'weight',  label: 'Weight',     type: 'number', unit: 'kg',  ph: '75',  min: 20,  max: 500 },
  { key: 'height',  label: 'Height',     type: 'number', unit: 'cm',  ph: '170', min: 100, max: 250 },
  { key: 'bmi',     label: 'BMI',        type: 'number', unit: 'kg/m²', ph: '26.0', min: 10, max: 80 },
  { key: 'smoking_status',    label: 'Smoking',          type: 'select', options: SMOKING_OPTIONS },
  { key: 'sedentary_minutes', label: 'Daily sitting time', type: 'number', unit: 'min/day', ph: '480', min: 0, max: 1440 },
];

/* Lab fields — per condition */
const LAB_FIELDS = {
  diabetes: [
    { key: 'fasting_glucose',   label: 'Fasting glucose',   type: 'number', unit: 'mg/dL', ph: '95',  min: 20,  max: 600,  hint: '(normal: 70–99)' },
    { key: 'hba1c',             label: 'HbA1c',             type: 'number', unit: '%',     ph: '5.4', min: 3,   max: 20,   hint: '(normal: <5.7%)' },
    { key: 'total_cholesterol', label: 'Total cholesterol',  type: 'number', unit: 'mg/dL', ph: '190', min: 50,  max: 500,  hint: '(normal: <200)' },
    { key: 'family_diabetes',   label: 'Family history of diabetes', type: 'bool' },
  ],
  cvd: [
    { key: 'systolic_bp',       label: 'Systolic BP',        type: 'number', unit: 'mmHg',  ph: '120', min: 60,  max: 250 },
    { key: 'diastolic_bp',      label: 'Diastolic BP',       type: 'number', unit: 'mmHg',  ph: '80',  min: 30,  max: 150 },
    { key: 'total_cholesterol', label: 'Total cholesterol',  type: 'number', unit: 'mg/dL', ph: '190', min: 50,  max: 500, hint: '(normal: <200)' },
    { key: 'hdl_cholesterol',   label: 'HDL cholesterol',    type: 'number', unit: 'mg/dL', ph: '55',  min: 10,  max: 150 },
    { key: 'fasting_glucose',   label: 'Fasting glucose',    type: 'number', unit: 'mg/dL', ph: '95',  min: 20,  max: 600 },
    { key: 'diabetes',          label: 'Known diabetes',     type: 'bool' },
  ],
  hypertension: [
    { key: 'systolic_bp',       label: 'Systolic BP',        type: 'number', unit: 'mmHg',  ph: '120', min: 60,  max: 260 },
    { key: 'diastolic_bp',      label: 'Diastolic BP',       type: 'number', unit: 'mmHg',  ph: '80',  min: 30,  max: 160 },
    { key: 'total_cholesterol', label: 'Total cholesterol',  type: 'number', unit: 'mg/dL', ph: '190', min: 50,  max: 500, hint: '(normal: <200)' },
    { key: 'fasting_glucose',   label: 'Fasting glucose',    type: 'number', unit: 'mg/dL', ph: '95',  min: 20,  max: 600 },
    { key: 'diabetes',          label: 'Known diabetes',     type: 'bool' },
  ],
};

const ENDPOINTS = { diabetes: assessDiabetes, cvd: assessCVD, hypertension: assessHypertension };

/* ── Build payload — only include fields the user actually filled in ── */
function buildMetrics(form, condition) {
  const allFields = [...REQUIRED_FIELDS, ...BASIC_OPTIONAL, ...(LAB_FIELDS[condition] || [])];
  const metrics = {};
  allFields.forEach(f => {
    const raw = form[f.key];
    if (raw === undefined || raw === '' || raw === null) return;
    if (f.type === 'number') {
      const n = parseFloat(raw);
      if (!isNaN(n)) metrics[f.key] = n;
    } else if (f.type === 'bool') {
      metrics[f.key] = raw === 'true';
    } else {
      metrics[f.key] = raw;
    }
  });
  return metrics;
}

/* ── Parse backend validation errors into readable messages ── */
function parseError(err) {
  const data = err.response?.data;
  if (!data) return 'Assessment failed. Is the API running?';
  if (typeof data.detail === 'string') return data.detail;
  if (Array.isArray(data.detail)) {
    return data.detail.map(e => {
      const field = e.loc?.slice(-1)[0] ?? 'field';
      return `${field}: ${e.msg}`;
    }).join('\n');
  }
  return JSON.stringify(data.detail);
}

/* ── Normalize varied response shapes from the three routes ── */
function normalizeResult(data) {
  const result = data.result ?? data;
  return {
    probability:    result.probability    ?? (result.risk_probability ?? 0),
    risk_level:     result.risk_level     ?? (result.risk_category?.toLowerCase().replace(' ', '_') ?? 'low'),
    interpretation: result.interpretation ?? result.message ?? data.message ?? '',
    top_factors:    data.top_factors      ?? result.explanation?.risk_factors ?? [],
    recommendations: data.recommendations ?? [],
  };
}

/* ── Single field renderer ─────────────────────────────────────── */
function FieldRow({ field, value, onChange }) {
  const base = {
    height: 44, width: '100%', padding: '0 12px',
    background: '#fff', border: '1.5px solid var(--elan-ch-200)',
    borderRadius: 'var(--r-md)', color: 'var(--elan-ch-800)',
    fontSize: '0.9375rem', outline: 'none',
    transition: 'border-color var(--t-fast)',
  };
  const opts = field.type === 'bool' ? BOOL_OPTIONS : field.options;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 5 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
        <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--elan-ch-600)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
          {field.label}
        </label>
        <span style={{ fontSize: '0.7rem', color: 'var(--elan-ch-300)' }}>
          {field.unit ?? ''} {field.hint ?? ''}
        </span>
      </div>
      {(field.type === 'select' || field.type === 'bool') ? (
        <select value={value ?? ''} onChange={e => onChange(e.target.value)}
          style={{ ...base, appearance: 'none', cursor: 'pointer' }}>
          <option value="">Select…</option>
          {opts.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
        </select>
      ) : (
        <input
          type="number" step="any" value={value ?? ''} placeholder={field.ph}
          onChange={e => onChange(e.target.value)}
          style={base}
          onFocus={e => { e.target.style.borderColor = 'var(--elan-ch-800)'; }}
          onBlur={e => { e.target.style.borderColor = 'var(--elan-ch-200)'; }}
        />
      )}
    </div>
  );
}

/* ── Collapsible section ─────────────────────────────────────────── */
function Section({ title, subtitle, children, defaultOpen = true }) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div style={{ borderRadius: 'var(--r-lg)', border: '1px solid var(--elan-border)', overflow: 'hidden', background: 'var(--elan-surface)' }}>
      <button type="button" onClick={() => setOpen(v => !v)}
        style={{ width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '14px 16px', background: 'none', cursor: 'pointer' }}>
        <div style={{ textAlign: 'left' }}>
          <div style={{ fontWeight: 700, fontSize: '0.875rem', color: 'var(--elan-ch-800)' }}>{title}</div>
          {subtitle && <div style={{ fontSize: '0.72rem', color: 'var(--elan-ch-400)', marginTop: 2 }}>{subtitle}</div>}
        </div>
        {open ? <ChevronUp size={16} color="var(--elan-ch-400)" /> : <ChevronDown size={16} color="var(--elan-ch-400)" />}
      </button>
      {open && (
        <div style={{ padding: '4px 16px 16px', display: 'flex', flexDirection: 'column', gap: 14, borderTop: '1px solid var(--elan-sep)' }}>
          {children}
        </div>
      )}
    </div>
  );
}

/* ── Main page ───────────────────────────────────────────────────── */
export default function AssessPage() {
  const navigate = useNavigate();
  const [selected, setSelected] = useState(null);
  const [form, setForm] = useState({});
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const set = k => v => setForm(p => ({ ...p, [k]: v }));

  const handleAssess = async (e) => {
    e.preventDefault();
    setError(''); setLoading(true);
    try {
      const metrics = buildMetrics(form, selected);
      if (!metrics.age)    { setError('Age is required.'); setLoading(false); return; }
      if (!metrics.gender) { setError('Biological sex is required.'); setLoading(false); return; }
      const raw = await ENDPOINTS[selected](metrics);
      const normalized = normalizeResult(raw);
      setResult(normalized);
      const stored = JSON.parse(localStorage.getItem('elan_assessments') || '[]');
      stored.unshift({ condition: selected, result: normalized, completedAt: Date.now() });
      localStorage.setItem('elan_assessments', JSON.stringify(stored.slice(0, 50)));
    } catch (err) {
      setError(parseError(err));
    } finally { setLoading(false); }
  };

  const reset = () => { setResult(null); setForm({}); setError(''); };

  /* Condition picker */
  if (!selected) {
    return (
      <div style={{ height: '100dvh', display: 'flex', flexDirection: 'column', background: 'var(--elan-bg)' }}>
        <TopBar />
        <div style={{ flex: 1, overflowY: 'auto', padding: '0 20px 120px' }}>
          <h1 style={{ fontFamily: 'var(--elan-serif)', fontSize: '1.8rem', color: 'var(--elan-ch-800)', marginBottom: 8, letterSpacing: '-0.02em' }}>Assess your risk</h1>
          <p style={{ color: 'var(--elan-ch-400)', fontSize: '0.875rem', marginBottom: 24 }}>Choose a condition to evaluate.</p>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            {Object.entries(CONDITIONS).map(([key, { label, Icon, color, desc }]) => (
              <ElanCard key={key} onClick={() => { setSelected(key); setForm({}); setResult(null); setError(''); }} style={{ padding: '20px 22px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
                  <div style={{ width: 48, height: 48, borderRadius: 'var(--r-md)', background: `${color}18`, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                    <Icon size={22} color={color} />
                  </div>
                  <div>
                    <div style={{ fontWeight: 700, fontSize: '1rem', color: 'var(--elan-ch-800)' }}>{label}</div>
                    <div style={{ fontSize: '0.8rem', color: 'var(--elan-ch-400)', marginTop: 2 }}>{desc}</div>
                  </div>
                </div>
              </ElanCard>
            ))}
          </div>
        </div>
        <FloatingNav />
      </div>
    );
  }

  const cond = CONDITIONS[selected];

  /* Results */
  if (result) {
    const byCategory = (result.recommendations ?? []).reduce((acc, r) => {
      const cat = r.category || 'General';
      (acc[cat] = acc[cat] || []).push(r); return acc;
    }, {});
    const shapFactors = (result.top_factors ?? []).map(f => ({
      feature_label: f.factor ?? f.feature ?? '',
      shap_value:    f.contribution ?? f.shap_value ?? 0,
    }));

    return (
      <div style={{ height: '100dvh', display: 'flex', flexDirection: 'column', background: 'var(--elan-bg)' }}>
        <div style={{ padding: '16px 20px', display: 'flex', alignItems: 'center', gap: 12, flexShrink: 0, borderBottom: '1px solid var(--elan-sep)' }}>
          <button onClick={reset} style={{ background: 'none', color: 'var(--elan-ch-500)', display: 'flex', alignItems: 'center', gap: 4, fontSize: '0.875rem', cursor: 'pointer' }}>
            <ChevronLeft size={18} /> New assessment
          </button>
          <span style={{ fontWeight: 600, color: 'var(--elan-ch-800)' }}>{cond.label} Result</span>
        </div>
        <div style={{ flex: 1, overflowY: 'auto', padding: '16px 20px 120px', display: 'flex', flexDirection: 'column', gap: 16 }}>
          <ElanCard style={{ padding: 24, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 16 }}>
            <RiskRing probability={result.probability} risk_level={result.risk_level} condition={cond.label} size={140} />
            <RiskBadge level={result.risk_level} />
            {result.interpretation && (
              <p style={{ textAlign: 'center', fontSize: '0.875rem', color: 'var(--elan-ch-600)', lineHeight: 1.6, maxWidth: 320 }}>
                {result.interpretation}
              </p>
            )}
          </ElanCard>
          {shapFactors.length > 0 && (
            <ElanCard style={{ padding: '18px 20px' }}>
              <h3 style={{ fontWeight: 700, fontSize: '0.875rem', color: 'var(--elan-ch-800)', marginBottom: 16 }}>Key Contributing Factors</h3>
              <ShapBar factors={shapFactors} />
            </ElanCard>
          )}
          {Object.entries(byCategory).map(([cat, items]) => (
            <RecommendationCard key={cat} category={cat} items={items} />
          ))}
          <ElanButton onClick={() => navigate('/chat')} variant="secondary" fullWidth>
            Discuss with AI assistant
          </ElanButton>
        </div>
        <FloatingNav />
      </div>
    );
  }

  /* Form */
  return (
    <div style={{ height: '100dvh', display: 'flex', flexDirection: 'column', background: 'var(--elan-bg)' }}>
      <div style={{ padding: '16px 20px', display: 'flex', alignItems: 'center', gap: 12, flexShrink: 0, borderBottom: '1px solid var(--elan-sep)' }}>
        <button onClick={() => setSelected(null)} style={{ background: 'none', color: 'var(--elan-ch-500)', display: 'flex', alignItems: 'center', gap: 4, fontSize: '0.875rem', cursor: 'pointer' }}>
          <ChevronLeft size={18} /> Conditions
        </button>
        <span style={{ fontWeight: 600, color: 'var(--elan-ch-800)' }}>{cond.label}</span>
      </div>

      <div style={{ flex: 1, overflowY: 'auto', padding: '16px 20px 120px' }}>
        {error && (
          <pre role="alert" style={{
            fontSize: '0.82rem', color: 'var(--elan-tc-500)',
            padding: '10px 14px', background: 'var(--elan-tc-50)',
            borderRadius: 'var(--r-sm)', marginBottom: 16,
            border: '1px solid var(--elan-tc-100)',
            whiteSpace: 'pre-wrap', fontFamily: 'inherit',
          }}>{error}</pre>
        )}

        <form onSubmit={handleAssess} noValidate style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          {/* Required */}
          <Section title="Required" defaultOpen>
            {REQUIRED_FIELDS.map(f => (
              <FieldRow key={f.key} field={f} value={form[f.key]} onChange={set(f.key)} />
            ))}
          </Section>

          {/* Basic optional */}
          <Section title="Body measurements" subtitle="Optional — leave blank if unknown" defaultOpen={false}>
            {BASIC_OPTIONAL.map(f => (
              <FieldRow key={f.key} field={f} value={form[f.key]} onChange={set(f.key)} />
            ))}
          </Section>

          {/* Lab results */}
          <Section
            title="Lab results"
            subtitle="Optional — skip if you don't have these. All values in mg/dL."
            defaultOpen={false}
          >
            <p style={{ fontSize: '0.78rem', color: 'var(--elan-ch-400)', lineHeight: 1.5, margin: 0 }}>
              Leave any field blank if you don't know it. The model works without lab results — they just improve accuracy.
            </p>
            {LAB_FIELDS[selected].map(f => (
              <FieldRow key={f.key} field={f} value={form[f.key]} onChange={set(f.key)} />
            ))}
          </Section>

          <ElanButton type="submit" loading={loading} fullWidth>
            Calculate Risk
          </ElanButton>
        </form>
      </div>
      <FloatingNav />
    </div>
  );
}
