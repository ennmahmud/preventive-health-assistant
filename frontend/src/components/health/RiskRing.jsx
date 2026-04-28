const RISK_COLORS = {
  low:       'var(--elan-sg-600)',
  moderate:  'var(--elan-am-400)',
  high:      'var(--elan-tc-400)',
  very_high: 'var(--elan-ch-800)',
};

const RISK_LABELS = {
  low: 'Low', moderate: 'Moderate', high: 'High', very_high: 'Very High',
};

export default function RiskRing({ probability = 0, risk_level = 'low', condition = '', size = 120 }) {
  const pct = Math.min(100, Math.max(0, Math.round(probability * 100)));
  const r = (size - 16) / 2;
  const circ = 2 * Math.PI * r;
  const offset = circ * (1 - pct / 100);
  const color = RISK_COLORS[risk_level] ?? RISK_COLORS.low;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 8 }}>
      <div style={{ position: 'relative', width: size, height: size }}>
        <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} style={{ transform: 'rotate(-90deg)' }}>
          <circle
            cx={size / 2} cy={size / 2} r={r}
            fill="none" stroke="var(--elan-ch-100)" strokeWidth="8"
          />
          <circle
            cx={size / 2} cy={size / 2} r={r}
            fill="none" stroke={color} strokeWidth="8"
            strokeLinecap="round"
            strokeDasharray={circ}
            strokeDashoffset={offset}
            style={{ transition: 'stroke-dashoffset 0.8s var(--ease-out)' }}
          />
        </svg>
        <div style={{
          position: 'absolute', inset: 0, display: 'flex',
          flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
        }}>
          <span style={{
            fontFamily: 'var(--elan-serif)',
            fontSize: size < 100 ? '1.6rem' : size < 140 ? '2rem' : '2.4rem',
            fontWeight: 400,
            color: color, lineHeight: 1,
          }}>{pct}%</span>
          <span style={{
            fontSize: size < 100 ? '0.62rem' : '0.75rem',
            color: 'var(--elan-ch-500)', marginTop: 4,
            textTransform: 'uppercase', letterSpacing: '0.08em', fontWeight: 600,
          }}>risk</span>
        </div>
      </div>
      {condition && (
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: '0.78rem', fontWeight: 600, color: 'var(--elan-ch-800)' }}>{condition}</div>
          <div style={{ fontSize: '0.7rem', color, fontWeight: 600, marginTop: 2 }}>{RISK_LABELS[risk_level]}</div>
        </div>
      )}
    </div>
  );
}
