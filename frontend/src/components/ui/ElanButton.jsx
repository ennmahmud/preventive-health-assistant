export default function ElanButton({
  children, onClick, type = 'button', variant = 'primary',
  disabled = false, loading = false, fullWidth = false, style: extra,
}) {
  const base = {
    display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
    gap: 8, height: 48, padding: '0 24px',
    borderRadius: 'var(--r-pill)', fontWeight: 600, fontSize: '0.9375rem',
    transition: 'all var(--t-base) var(--ease-out)',
    cursor: disabled || loading ? 'not-allowed' : 'pointer',
    opacity: disabled ? 0.5 : 1,
    width: fullWidth ? '100%' : undefined,
    ...extra,
  };

  const variants = {
    primary: {
      background: 'var(--elan-ch-800)', color: '#fff',
    },
    secondary: {
      background: 'transparent', color: 'var(--elan-ch-800)',
      border: '1.5px solid var(--elan-ch-200)',
    },
    ghost: {
      background: 'transparent', color: 'var(--elan-ch-600)',
    },
    danger: {
      background: 'var(--elan-tc-400)', color: '#fff',
    },
  };

  return (
    <button type={type} onClick={onClick} disabled={disabled || loading}
      style={{ ...base, ...variants[variant] }}
      onMouseEnter={e => { if (!disabled && !loading) e.currentTarget.style.opacity = '0.85'; }}
      onMouseLeave={e => { e.currentTarget.style.opacity = disabled ? '0.5' : '1'; }}
    >
      {loading ? (
        <span style={{
          width: 16, height: 16, border: '2px solid currentColor',
          borderTopColor: 'transparent', borderRadius: '50%',
          animation: 'elan-spin 0.7s linear infinite',
        }} />
      ) : children}
    </button>
  );
}
