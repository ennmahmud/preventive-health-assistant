import { useState } from 'react';
import { Eye, EyeOff } from 'lucide-react';

export default function ElanInput({
  id, label, type = 'text', value, onChange, placeholder,
  error, autoComplete, required,
}) {
  const [showPwd, setShowPwd] = useState(false);
  const isPassword = type === 'password';
  const inputType = isPassword ? (showPwd ? 'text' : 'password') : type;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
      {label && (
        <label htmlFor={id} style={{
          fontSize: '0.78rem', fontWeight: 600, color: 'var(--elan-ch-600)',
          textTransform: 'uppercase', letterSpacing: '0.06em',
        }}>
          {label}{required && <span style={{ color: 'var(--elan-tc-400)', marginLeft: 3 }}>*</span>}
        </label>
      )}
      <div style={{ position: 'relative' }}>
        <input
          id={id} type={inputType} value={value} onChange={onChange}
          placeholder={placeholder} autoComplete={autoComplete}
          required={required}
          style={{
            height: 48, width: '100%',
            padding: isPassword ? '0 44px 0 16px' : '0 16px',
            background: '#fff',
            border: `1.5px solid ${error ? 'var(--elan-tc-400)' : 'var(--elan-ch-200)'}`,
            borderRadius: 'var(--r-md)',
            color: 'var(--elan-ch-800)', fontSize: '0.9375rem',
            transition: 'border-color var(--t-fast), box-shadow var(--t-fast)',
            outline: 'none',
          }}
          onFocus={e => {
            e.target.style.borderColor = 'var(--elan-ch-800)';
            e.target.style.boxShadow = '0 0 0 3px rgba(44,43,40,0.10)';
          }}
          onBlur={e => {
            e.target.style.borderColor = error ? 'var(--elan-tc-400)' : 'var(--elan-ch-200)';
            e.target.style.boxShadow = 'none';
          }}
        />
        {isPassword && (
          <button type="button" onClick={() => setShowPwd(v => !v)}
            aria-label={showPwd ? 'Hide password' : 'Show password'}
            style={{
              position: 'absolute', right: 12, top: '50%', transform: 'translateY(-50%)',
              background: 'none', color: 'var(--elan-ch-400)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              width: 28, height: 28, borderRadius: 'var(--r-xs)',
              transition: 'color var(--t-fast)',
            }}
            onMouseEnter={e => e.currentTarget.style.color = 'var(--elan-ch-800)'}
            onMouseLeave={e => e.currentTarget.style.color = 'var(--elan-ch-400)'}
          >
            {showPwd ? <EyeOff size={15} /> : <Eye size={15} />}
          </button>
        )}
      </div>
      {error && (
        <span role="alert" style={{ fontSize: '0.78rem', color: 'var(--elan-tc-500)' }}>{error}</span>
      )}
    </div>
  );
}
