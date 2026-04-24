export default function ShapBar({ factors = [] }) {
  if (!factors.length) return null;
  const maxAbs = Math.max(...factors.map(f => Math.abs(f.shap_value)), 0.001);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
      {factors.map((f, i) => {
        const pct = (Math.abs(f.shap_value) / maxAbs) * 100;
        const isRisk = f.shap_value > 0;
        const color = isRisk ? 'var(--elan-tc-400)' : 'var(--elan-sg-600)';
        return (
          <div key={i} style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: '0.8rem', color: 'var(--elan-ch-700)', fontWeight: 500 }}>
                {f.feature_label ?? f.feature}
              </span>
              <span style={{ fontSize: '0.7rem', color, fontWeight: 600 }}>
                {isRisk ? '+' : ''}{f.shap_value.toFixed(3)}
              </span>
            </div>
            <div style={{
              height: 6, background: 'var(--elan-ch-100)', borderRadius: 'var(--r-pill)', overflow: 'hidden',
            }}>
              <div style={{
                height: '100%', width: `${pct}%`, background: color,
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
