export default function ShapBar({ factors = [] }) {
  // Drop rows with no label so we don't render blank tracks
  const valid = (factors || []).filter(f =>
    String(f?.feature_label ?? f?.feature ?? '').trim().length > 0
  );
  if (!valid.length) return null;
  const maxAbs = Math.max(...valid.map(f => Math.abs(f.shap_value || 0)), 0.001);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      {valid.map((f, i) => {
        const v = f.shap_value || 0;
        const pct = (Math.abs(v) / maxAbs) * 100;
        const isRisk = v >= 0;
        const color = isRisk ? 'var(--elan-tc-400)' : 'var(--elan-sg-600)';
        const label = f.feature_label ?? f.feature ?? '';
        return (
          <div key={i} style={{ display: 'flex', flexDirection: 'column', gap: 5 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: '0.85rem', color: 'var(--elan-ch-800)', fontWeight: 600 }}>
                {label}
              </span>
              <span style={{
                fontSize: '0.72rem', color, fontWeight: 700,
                padding: '2px 8px', borderRadius: 'var(--r-pill)',
                background: isRisk ? 'var(--elan-tc-50)' : 'var(--elan-sg-50)',
                border: `1px solid ${isRisk ? 'var(--elan-tc-200)' : 'var(--elan-sg-200)'}`,
                textTransform: 'uppercase', letterSpacing: '0.04em',
              }}>
                {isRisk ? 'Increases' : 'Decreases'}
              </span>
            </div>
            <div style={{
              height: 8, background: 'var(--elan-ch-100)', borderRadius: 'var(--r-pill)', overflow: 'hidden',
            }}>
              <div style={{
                height: '100%', width: `${Math.max(4, pct)}%`, background: color,
                borderRadius: 'var(--r-pill)',
                transition: 'width 0.6s var(--ease-out)',
              }} />
            </div>
          </div>
        );
      })}
    </div>
  );
}
