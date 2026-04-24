import { useState } from 'react';
import { ChevronDown, ChevronUp } from 'lucide-react';

const PRIORITY_STYLES = {
  high:   { bg: 'var(--elan-tc-50)',  border: 'var(--elan-tc-200)',  dot: 'var(--elan-tc-400)'  },
  medium: { bg: 'var(--elan-am-50)',  border: 'var(--elan-am-200)',  dot: 'var(--elan-am-400)'  },
  low:    { bg: 'var(--elan-sg-50)',  border: 'var(--elan-sg-200)',  dot: 'var(--elan-sg-600)'  },
};

export default function RecommendationCard({ category = '', items = [] }) {
  const [open, setOpen] = useState(true);
  if (!items.length) return null;
  return (
    <div style={{
      border: '1px solid var(--elan-border)', borderRadius: 'var(--r-lg)',
      background: 'var(--elan-surface)', overflow: 'hidden',
    }}>
      <button
        onClick={() => setOpen(v => !v)}
        style={{
          width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          padding: '14px 18px', background: 'transparent', textAlign: 'left',
        }}
      >
        <span style={{ fontWeight: 600, fontSize: '0.9rem', color: 'var(--elan-ch-800)' }}>{category}</span>
        {open ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
      </button>
      {open && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 0 }}>
          {items.map((item, i) => {
            const s = PRIORITY_STYLES[item.priority] ?? PRIORITY_STYLES.medium;
            return (
              <div key={i} style={{
                display: 'flex', alignItems: 'flex-start', gap: 12,
                padding: '12px 18px',
                background: s.bg, borderTop: `1px solid ${s.border}`,
              }}>
                <span style={{
                  width: 8, height: 8, borderRadius: '50%', background: s.dot,
                  flexShrink: 0, marginTop: 5,
                }} />
                <span style={{ fontSize: '0.875rem', color: 'var(--elan-ch-700)', lineHeight: 1.6 }}>
                  {item.recommendation}
                </span>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
