import { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import TopBar from '../components/layout/TopBar';
import FloatingNav from '../components/layout/FloatingNav';
import ElanCard from '../components/ui/ElanCard';
import ElanButton from '../components/ui/ElanButton';
import RiskRing from '../components/health/RiskRing';
import RiskBadge from '../components/health/RiskBadge';
import ShapBar from '../components/health/ShapBar';
import RecommendationCard from '../components/health/RecommendationCard';
import { assessDiabetes, assessCVD, assessHypertension } from '../api/health';
import { appendLocal } from '../utils/assessmentHistory';
import { Heart, Activity, Droplets, ChevronLeft, ChevronDown, ChevronUp, MessageCircle, CheckCircle2, Share2, Check } from 'lucide-react';

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

/* ── Normalize the backend response shape ── */
// All three routes return: { risk: { risk_probability, risk_category }, explanation: { risk_factors, summary }, recommendations }
function normalizeResult(data) {
  const risk = data.risk ?? data;
  return {
    probability:     risk.risk_probability ?? risk.probability ?? 0,
    risk_level:      risk.risk_category
                       ? risk.risk_category.toLowerCase().replace(/\s+/g, '_')
                       : (risk.risk_level ?? 'low'),
    interpretation:  data.explanation?.summary ?? risk.interpretation ?? '',
    top_factors:     data.explanation?.risk_factors ?? data.top_factors ?? [],
    protective_factors: data.explanation?.protective_factors ?? [],
    recommendations: data.recommendations ?? [],
  };
}

/* Prettify a snake_case feature key to a human label */
function prettifyFeature(name) {
  if (!name) return '';
  const map = {
    bmi: 'BMI',
    hba1c: 'HbA1c',
    hdl_cholesterol: 'HDL cholesterol',
    total_cholesterol: 'Total cholesterol',
    fasting_glucose: 'Fasting glucose',
    systolic_bp: 'Systolic BP',
    diastolic_bp: 'Diastolic BP',
    sedentary_minutes: 'Sedentary time',
    smoking_status: 'Smoking',
    family_diabetes: 'Family history (diabetes)',
    family_cvd: 'Family history (heart disease)',
    family_htn: 'Family history (hypertension)',
    waist_circumference: 'Waist circumference',
  };
  if (map[name]) return map[name];
  return String(name)
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

/* Prettify a recommendation category like "diet" → "Diet" */
function prettifyCategory(cat) {
  if (!cat) return 'General';
  return String(cat)
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

/* ── Share card generator (Canvas API, no external deps) ─────── */
const RISK_HEX = { low: '#6BAE65', moderate: '#F0BE48', high: '#F47358', very_high: '#C44A36' };
const RISK_LABEL = { low: 'Low Risk', moderate: 'Moderate Risk', high: 'High Risk', very_high: 'Very High Risk' };

function _rrect(ctx, x, y, w, h, r) {
  ctx.beginPath();
  if (ctx.roundRect) {
    ctx.roundRect(x, y, w, h, r);
  } else {
    ctx.moveTo(x + r, y);
    ctx.lineTo(x + w - r, y); ctx.quadraticCurveTo(x + w, y, x + w, y + r);
    ctx.lineTo(x + w, y + h - r); ctx.quadraticCurveTo(x + w, y + h, x + w - r, y + h);
    ctx.lineTo(x + r, y + h); ctx.quadraticCurveTo(x, y + h, x, y + h - r);
    ctx.lineTo(x, y + r); ctx.quadraticCurveTo(x, y, x + r, y);
    ctx.closePath();
  }
}

async function generateShareCard(result, conditionLabel) {
  const W = 1080, H = 540, PAD = 56;
  const canvas = document.createElement('canvas');
  canvas.width = W; canvas.height = H;
  const ctx = canvas.getContext('2d');

  const riskColor = RISK_HEX[result.risk_level] ?? '#F47358';
  const riskLabel = RISK_LABEL[result.risk_level] ?? 'Unknown';
  const pct = Math.round((result.probability ?? 0) * 100);

  // ── Background: dark warm
  ctx.fillStyle = '#0B0907';
  ctx.fillRect(0, 0, W, H);

  // Ambient radial glow from top-center using risk color
  const grd = ctx.createRadialGradient(W / 2, -60, 20, W / 2, -60, 500);
  grd.addColorStop(0, riskColor + '28');
  grd.addColorStop(1, 'transparent');
  ctx.fillStyle = grd;
  ctx.fillRect(0, 0, W, H);

  // Subtle right-side vertical separator
  ctx.strokeStyle = 'rgba(242,237,227,0.06)';
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(W * 0.52, PAD + 40);
  ctx.lineTo(W * 0.52, H - PAD - 40);
  ctx.stroke();

  // ── Wait for web fonts (loaded by @fontsource at app boot)
  await document.fonts.ready;

  const SERIF  = '"DM Serif Display", Georgia, serif';
  const SANS   = '"Plus Jakarta Sans", system-ui, sans-serif';

  // ── Top-left: ECG waveform path
  ctx.strokeStyle = '#F2EDE3';
  ctx.lineWidth = 2.2;
  ctx.lineCap = 'round';
  ctx.lineJoin = 'round';
  ctx.beginPath();
  const ex = PAD, ey = 52;
  [[ex,ey],[ex+14,ey],[ex+20,ey-16],[ex+26,ey+18],[ex+32,ey],[ex+52,ey]].forEach(([x,y],i) =>
    i === 0 ? ctx.moveTo(x,y) : ctx.lineTo(x,y)
  );
  ctx.stroke();

  // "Élan" wordmark
  ctx.fillStyle = '#F2EDE3';
  ctx.font = `600 20px ${SERIF}`;
  ctx.textAlign = 'left';
  ctx.fillText('Élan', PAD + 62, ey + 7);

  // Date — top right
  const dateStr = new Date().toLocaleDateString('en-GB', { day: 'numeric', month: 'long', year: 'numeric' });
  ctx.fillStyle = '#524C42';
  ctx.font = `500 14px ${SANS}`;
  ctx.textAlign = 'right';
  ctx.fillText(dateStr, W - PAD, ey + 7);

  // Separator under header
  ctx.strokeStyle = 'rgba(242,237,227,0.07)';
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(PAD, 80); ctx.lineTo(W - PAD, 80);
  ctx.stroke();

  // ── Left column ──────────────────────────────────────────────
  const LX = PAD;

  // Condition label
  ctx.fillStyle = '#6E6759';
  ctx.font = `700 12px ${SANS}`;
  ctx.textAlign = 'left';
  ctx.fillText(conditionLabel.toUpperCase() + ' · RISK ASSESSMENT', LX, 122);

  // Big percentage
  ctx.fillStyle = '#F2EDE3';
  ctx.font = `700 128px ${SERIF}`;
  ctx.fillText(`${pct}%`, LX, 272);

  // Risk level badge pill
  ctx.font = `700 15px ${SANS}`;
  const bTxt = riskLabel;
  const bW = ctx.measureText(bTxt).width + 32;
  const bH = 34, bX = LX, bY = 296;
  ctx.fillStyle = riskColor + '25';
  _rrect(ctx, bX, bY, bW, bH, 17); ctx.fill();
  ctx.strokeStyle = riskColor + '70';
  ctx.lineWidth = 1.5;
  _rrect(ctx, bX, bY, bW, bH, 17); ctx.stroke();
  ctx.fillStyle = riskColor;
  ctx.fillText(bTxt, bX + 16, bY + 23);

  // Interpretation snippet (word-wrapped, max 2 lines)
  if (result.interpretation) {
    const maxTxtW = W * 0.52 - PAD - 20;
    ctx.fillStyle = 'rgba(242,237,227,0.38)';
    ctx.font = `400 14px ${SANS}`;
    const words = result.interpretation.split(' ');
    let line = '', lines = [], lineCount = 0;
    for (const word of words) {
      const test = line + word + ' ';
      if (ctx.measureText(test).width > maxTxtW && line) {
        lines.push(line.trim());
        line = word + ' ';
        if (++lineCount >= 2) break;
      } else { line = test; }
    }
    if (line.trim() && lineCount < 2) lines.push(line.trim());
    lines.forEach((l, i) => ctx.fillText(l, LX, 360 + i * 22));
  }

  // ── Right column ─────────────────────────────────────────────
  const RX = W * 0.52 + 40;

  // "Key factors" heading
  const factors = (result.top_factors ?? []).slice(0, 4);
  if (factors.length) {
    ctx.fillStyle = '#6E6759';
    ctx.font = `700 12px ${SANS}`;
    ctx.fillText('KEY FACTORS', RX, 122);

    ctx.font = `500 16px ${SANS}`;
    factors.forEach((f, i) => {
      const label = prettifyFeature(f.factor ?? f.feature ?? String(f));
      const dotY = 150 + i * 46;
      // Dot
      ctx.fillStyle = riskColor;
      ctx.beginPath();
      ctx.arc(RX + 5, dotY, 4, 0, Math.PI * 2);
      ctx.fill();
      // Label
      ctx.fillStyle = 'rgba(242,237,227,0.80)';
      ctx.fillText(label, RX + 18, dotY + 6);
      // Subtle underline
      ctx.strokeStyle = 'rgba(242,237,227,0.06)';
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(RX, dotY + 16); ctx.lineTo(W - PAD, dotY + 16);
      ctx.stroke();
    });
  } else {
    // No factors — show reassurance text
    ctx.fillStyle = 'rgba(242,237,227,0.30)';
    ctx.font = `400 15px ${SANS}`;
    const msg = result.risk_level === 'low'
      ? 'Your lifestyle markers are\nlooking healthy. Keep it up!'
      : 'Complete an assessment with lab\nvalues for detailed factor analysis.';
    msg.split('\n').forEach((l, i) => ctx.fillText(l, RX, 160 + i * 26));
  }

  // ── Bottom bar ────────────────────────────────────────────────
  ctx.strokeStyle = 'rgba(242,237,227,0.07)';
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(PAD, H - 64); ctx.lineTo(W - PAD, H - 64);
  ctx.stroke();

  ctx.fillStyle = '#3A352D';
  ctx.font = `500 13px ${SANS}`;
  ctx.textAlign = 'left';
  ctx.fillText('Generated by Élan · Preventive Health Intelligence', PAD, H - 36);
  ctx.textAlign = 'right';
  ctx.fillStyle = '#3A352D';
  ctx.fillText('Not a medical diagnosis — consult your doctor', W - PAD, H - 36);

  // ── Download or share
  const filename = `elan-${conditionLabel.toLowerCase().replace(/\s+/g, '-')}-risk.png`;

  if (navigator.share && navigator.canShare) {
    canvas.toBlob(async (blob) => {
      const file = new File([blob], filename, { type: 'image/png' });
      if (navigator.canShare({ files: [file] })) {
        try {
          await navigator.share({ files: [file], title: `My ${conditionLabel} Risk — Élan` });
          return;
        } catch (_) { /* user cancelled or share failed — fall through to download */ }
      }
      _downloadCanvas(canvas, filename);
    }, 'image/png');
  } else {
    _downloadCanvas(canvas, filename);
  }
}

function _downloadCanvas(canvas, filename) {
  const a = document.createElement('a');
  a.download = filename;
  a.href = canvas.toDataURL('image/png');
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
}

/* ── Single field renderer ─────────────────────────────────────── */
function FieldRow({ field, value, onChange }) {
  const base = {
    height: 44, width: '100%', padding: '0 12px',
    background: 'var(--elan-surface)', border: '1.5px solid var(--elan-ch-200)',
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
  const location = useLocation();
  const [selected, setSelected] = useState(null);
  const [form, setForm] = useState({});
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false); // share/save card state

  /* Pre-select condition from navigation state (Progress page) or ?c= query param (Dashboard rings) */
  useEffect(() => {
    const s = location.state;
    if (s && s.condition && s.result) {
      setSelected(s.condition);
      setResult(s.result);
      setError('');
      window.history.replaceState({}, document.title);
      return;
    }
    const param = new URLSearchParams(location.search).get('c');
    if (param && CONDITIONS[param] && !selected) {
      setSelected(param);
    }
  }, [location.state, location.search]);

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
      // Per-user cache — backend persists the canonical record via the
      // assess endpoints when the user is authenticated.
      appendLocal({ condition: selected, result: normalized, completedAt: Date.now() });
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
        <div style={{ flex: 1, overflowY: 'auto', paddingBottom: 120 }}>
          <div className="elan-page-wrap">
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
    // Combine risk factors AND protective factors so both directions are visualised
    const riskFs       = (result.top_factors ?? []).map(f => ({ ...f, _isRisk: true }));
    const protectiveFs = (result.protective_factors ?? []).map(f => ({ ...f, _isRisk: false }));
    const shapFactors  = [...riskFs, ...protectiveFs].map(f => ({
      feature_label: prettifyFeature(f.factor ?? f.feature ?? ''),
      shap_value:    (f._isRisk ? 1 : -1) * Math.abs(f.contribution ?? f.shap_value ?? 0),
    }));

    return (
      <div style={{ height: '100dvh', display: 'flex', flexDirection: 'column', background: 'var(--elan-bg)' }}>
        <div style={{ padding: '16px 20px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexShrink: 0, borderBottom: '1px solid var(--elan-sep)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <button onClick={reset} style={{ background: 'none', color: 'var(--elan-ch-500)', display: 'flex', alignItems: 'center', gap: 4, fontSize: '0.875rem', cursor: 'pointer' }}>
              <ChevronLeft size={18} /> New assessment
            </button>
            <span style={{ fontWeight: 600, color: 'var(--elan-ch-800)' }}>{cond.label} Result</span>
          </div>

          {/* Share / Save card button */}
          <button
            onClick={async () => {
              if (saving) return;
              setSaving(true);
              try { await generateShareCard(result, cond.label); }
              finally {
                setTimeout(() => setSaving(false), 2000);
              }
            }}
            style={{
              display: 'flex', alignItems: 'center', gap: 7,
              padding: '8px 14px',
              background: saving ? 'var(--elan-sg-50)' : 'var(--elan-surface)',
              border: `1.5px solid ${saving ? 'var(--elan-sg-300)' : 'var(--elan-ch-200)'}`,
              borderRadius: 'var(--r-pill)',
              color: saving ? 'var(--elan-sg-700)' : 'var(--elan-ch-700)',
              fontSize: '0.8rem', fontWeight: 600,
              cursor: saving ? 'default' : 'pointer',
              fontFamily: 'inherit',
              transition: 'all var(--t-base)',
            }}
            onMouseEnter={e => { if (!saving) { e.currentTarget.style.borderColor = 'var(--elan-ch-400)'; e.currentTarget.style.color = 'var(--elan-ch-800)'; }}}
            onMouseLeave={e => { if (!saving) { e.currentTarget.style.borderColor = 'var(--elan-ch-200)'; e.currentTarget.style.color = 'var(--elan-ch-700)'; }}}
          >
            {saving
              ? <><Check size={14} />&nbsp;Saved!</>
              : <><Share2 size={14} />&nbsp;Save card</>
            }
          </button>
        </div>
        <div style={{ flex: 1, overflowY: 'auto' }}>
         <div style={{ maxWidth: 720, margin: '0 auto', padding: '20px 20px 120px', display: 'flex', flexDirection: 'column', gap: 20 }}>

          {/* Completion moment */}
          <div style={{
            display: 'flex', alignItems: 'center', gap: 10,
            padding: '12px 16px',
            background: 'var(--elan-sg-50)',
            border: '1px solid var(--elan-sg-200)',
            borderRadius: 'var(--r-lg)',
          }}>
            <CheckCircle2 size={18} color="var(--elan-sg-600)" style={{ flexShrink: 0 }} />
            <div>
              <div style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--elan-sg-600)' }}>Assessment complete</div>
              <div style={{ fontSize: '0.75rem', color: 'var(--elan-ch-500)', marginTop: 1 }}>
                Your {cond.label.toLowerCase()} risk has been calculated.
              </div>
            </div>
          </div>

          <ElanCard style={{ padding: '32px 24px', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 18 }}>
            <RiskRing probability={result.probability} risk_level={result.risk_level} condition={cond.label} size={160} />
            <RiskBadge level={result.risk_level} />
          </ElanCard>

          {result.interpretation && (
            <div style={{
              padding: '18px 20px',
              background: 'var(--elan-surface)',
              border: '1px solid rgba(44,43,40,0.14)',
              borderLeft: `4px solid ${cond.color}`,
              borderRadius: 'var(--r-lg)',
              boxShadow: 'var(--shadow-sm)',
            }}>
              <div style={{
                fontSize: '0.7rem', fontWeight: 700, letterSpacing: '0.08em',
                textTransform: 'uppercase', color: 'var(--elan-ch-500)', marginBottom: 8,
              }}>
                What this means
              </div>
              <p style={{
                fontSize: '0.95rem',
                color: 'var(--elan-ch-800)',
                lineHeight: 1.6,
                margin: 0,
              }}>
                {result.interpretation}
              </p>
            </div>
          )}

          {/* Primary Chat CTA — immediately after risk card */}
          <button
            onClick={() => navigate('/chat')}
            style={{
              display: 'flex', alignItems: 'center', justifyContent: 'space-between',
              width: '100%', padding: '16px 20px',
              background: 'var(--elan-primary-bg)', borderRadius: 'var(--r-xl)',
              color: 'var(--elan-primary-text)', border: 'none', cursor: 'pointer',
              boxShadow: 'var(--shadow-md), var(--glow-cream)',
              transition: 'transform var(--t-base) var(--ease-out), box-shadow var(--t-base)',
            }}
            onMouseEnter={e => {
              e.currentTarget.style.background = 'var(--elan-primary-bg-hover)';
              e.currentTarget.style.transform = 'translateY(-1px)';
            }}
            onMouseLeave={e => {
              e.currentTarget.style.background = 'var(--elan-primary-bg)';
              e.currentTarget.style.transform = 'translateY(0)';
            }}
          >
            <div style={{ textAlign: 'left' }}>
              <div style={{ fontFamily: 'var(--elan-serif)', fontSize: '1rem', lineHeight: 1.2, color: 'var(--elan-primary-text)' }}>
                Discuss with your AI assistant
              </div>
              <div style={{ fontSize: '0.78rem', color: 'var(--elan-primary-muted)', marginTop: 4 }}>
                Explain your result · Get a personalised plan
              </div>
            </div>
            <div style={{
              width: 36, height: 36, borderRadius: '50%',
              background: 'rgba(20,17,13,0.10)',
              display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
              color: 'var(--elan-primary-text)',
            }}>
              <MessageCircle size={17} />
            </div>
          </button>

          {shapFactors.length > 0 && (
            <ElanCard style={{ padding: '18px 20px' }}>
              <h3 style={{ fontWeight: 700, fontSize: '0.875rem', color: 'var(--elan-ch-800)', marginBottom: 16 }}>Key Contributing Factors</h3>
              <ShapBar factors={shapFactors} />
            </ElanCard>
          )}
          {Object.entries(byCategory).map(([cat, items]) => (
            <RecommendationCard key={cat} category={prettifyCategory(cat)} items={items} />
          ))}
         </div>
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

      <div style={{ flex: 1, overflowY: 'auto', padding: '16px 0 120px' }}>
        <div className="elan-page-wrap">
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
      </div>
      <FloatingNav />
    </div>
  );
}
