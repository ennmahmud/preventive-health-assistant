export default function ElanCard({ children, style: extra, onClick }) {
  return (
    <div
      onClick={onClick}
      role={onClick ? 'button' : undefined}
      tabIndex={onClick ? 0 : undefined}
      style={{
        background: 'var(--elan-surface)',
        border: '1px solid var(--elan-border)',
        borderRadius: 'var(--r-lg)',
        boxShadow: 'var(--shadow-sm)',
        overflow: 'hidden',
        cursor: onClick ? 'pointer' : undefined,
        transition: onClick ? 'box-shadow var(--t-base), transform var(--t-base), border-color var(--t-base)' : undefined,
        ...extra,
      }}
      onMouseEnter={onClick ? e => {
        e.currentTarget.style.boxShadow = 'var(--shadow-md)';
        e.currentTarget.style.transform = 'translateY(-1px)';
        e.currentTarget.style.borderColor = 'rgba(242,237,227,0.14)';
      } : undefined}
      onMouseLeave={onClick ? e => {
        e.currentTarget.style.boxShadow = 'var(--shadow-sm)';
        e.currentTarget.style.transform = 'translateY(0)';
        e.currentTarget.style.borderColor = 'var(--elan-border)';
      } : undefined}
    >
      {children}
    </div>
  );
}
