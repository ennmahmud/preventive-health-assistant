import { useState } from 'react';
import { ChevronDown, ChevronUp } from 'lucide-react';

const PRIORITY_STYLES = {
  high:   { bg: 'var(--elan-tc-50)',  border: 'var(--elan-tc-200)',  dot: 'var(--elan-tc-400)'  },
  medium: { bg: 'var(--elan-am-50)',  border: 'var(--elan-am-200)',  dot: 'var(--elan-am-400)'  },
  low:    { bg: 'var(--elan-sg-50)',  border: 'var(--elan-sg-200)',  dot: 'var(--elan-sg-600)'  },
};

export default function RecommendationCard({ category = '', items = [] }) {
  const [open, setOpen] = useState(true);
  // Drop entries with no recommendation text — protects against empty/partial backend rows
  const validItems = (items || []).filter(it => (it?.recommendation ?? '').trim().length > 0);
  if (!validItems.length) return null;
  return (
    <div style={{
      border: '1px solid rgba(44,43,40,0.14)', borderRadius: 'var(--r-lg)',
      background: 'var(--elan-surface)', overflow: 'hidden',
      boxShadow: 'var(--shadow-sm)',
    }}>
      <button
        onClick={() => setOpen(v => !v)}
        style={{
          width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          padding: '14px 18px', background: 'transparent', textAlign: 'left',
        }}
      >
        <span style={{ fontWeight: 700, fontSize: '0.95rem', color: 'var(--elan-ch-800)' }}>
          {category || 'Recommendations'} <span style={{ color: 'var(--elan-ch-400)', fontWeight: 500, marginLeft: 6 }}>· {validItems.length}</span>
        </span>
        {open ? <ChevronUp size={16} color="var(--elan-ch-500)" /> : <ChevronDown size={16} color="var(--elan-ch-500)" />}
      </button>
      {open && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8, padding: '0 14px 14px' }}>
          {validItems.map((item, i) => {
            const s = PRIORITY_STYLES[item.priority] ?? PRIORITY_STYLES.medium;
            return (
              <div key={i} style={{
                display: 'flex', alignItems: 'flex-start', gap: 12,
                padding: '12px 14px',
                background: s.bg,
                border: `1px solid ${s.border}`,
                borderRadius: 'var(--r-md)',
              }}>
                <span style={{
                  width: 8, height: 8, borderRadius: '50%', background: s.dot,
                  flexShrink: 0, marginTop: 6,
                }} />
                <div style={{ display: 'flex', flexDirection: 'column', gap: 4, flex: 1, minWidth: 0 }}>
                  <span style={{ fontSize: '0.9rem', fontWeight: 600, color: 'var(--elan-ch-800)', lineHeight: 1.5 }}>
                    {item.recommendation}
                  </span>
                  {item.rationale && (
                    <span style={{ fontSize: '0.8rem', color: 'var(--elan-ch-600)', lineHeight: 1.55 }}>
                      {item.rationale}
                    </span>
                  )}
                  {item.source && (
                    <span style={{ fontSize: '0.7rem', color: 'var(--elan-ch-400)', fontStyle: 'italic' }}>
                      Source: {item.source}
                    </span>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
