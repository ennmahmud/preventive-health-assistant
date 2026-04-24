const STYLES = {
  low:       { bg: 'var(--elan-sg-50)',  border: 'var(--elan-sg-200)',  text: 'var(--elan-sg-700)',  label: 'Low' },
  moderate:  { bg: 'var(--elan-am-50)',  border: 'var(--elan-am-200)',  text: 'var(--elan-am-700)',  label: 'Moderate' },
  high:      { bg: 'var(--elan-tc-50)',  border: 'var(--elan-tc-200)',  text: 'var(--elan-tc-700)',  label: 'High' },
  very_high: { bg: 'var(--elan-ch-100)', border: 'var(--elan-ch-200)', text: 'var(--elan-ch-800)',  label: 'Very High' },
};

export default function RiskBadge({ level = 'low' }) {
  const s = STYLES[level] ?? STYLES.low;
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: 5,
      padding: '3px 10px', borderRadius: 'var(--r-pill)',
      background: s.bg, border: `1px solid ${s.border}`,
      color: s.text, fontSize: '0.72rem', fontWeight: 600, letterSpacing: '0.02em',
    }}>
      <span style={{
        width: 6, height: 6, borderRadius: '50%', background: s.text, flexShrink: 0,
      }} />
      {s.label}
    </span>
  );
}
