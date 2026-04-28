const STYLES = {
  low:       { bg: 'var(--elan-sg-50)',  border: 'var(--elan-sg-200)',  text: 'var(--elan-sg-700)',  label: 'Low' },
  moderate:  { bg: 'var(--elan-am-50)',  border: 'var(--elan-am-200)',  text: 'var(--elan-am-700)',  label: 'Moderate' },
  high:      { bg: 'var(--elan-tc-50)',  border: 'var(--elan-tc-200)',  text: 'var(--elan-tc-700)',  label: 'High' },
  very_high: { bg: 'var(--elan-ch-100)', border: 'var(--elan-ch-200)', text: 'var(--elan-ch-800)',  label: 'Very High' },
};

export default function RiskBadge({ level = 'low', size = 'md' }) {
  const s = STYLES[level] ?? STYLES.low;
  const isLg = size === 'lg';
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: isLg ? 7 : 5,
      padding: isLg ? '6px 14px' : '3px 10px', borderRadius: 'var(--r-pill)',
      background: s.bg, border: `1px solid ${s.border}`,
      color: s.text, fontSize: isLg ? '0.85rem' : '0.72rem',
      fontWeight: 700, letterSpacing: '0.04em', textTransform: 'uppercase',
    }}>
      <span style={{
        width: isLg ? 8 : 6, height: isLg ? 8 : 6,
        borderRadius: '50%', background: s.text, flexShrink: 0,
      }} />
      {s.label} risk
    </span>
  );
}
