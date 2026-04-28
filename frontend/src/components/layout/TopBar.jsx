import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { useTheme } from '../../contexts/ThemeContext';
import { Settings, Sun, Moon } from 'lucide-react';

function ElanWaveform() {
  return (
    <svg width="28" height="28" viewBox="0 0 52 52" fill="none" aria-hidden="true">
      <rect width="52" height="52" rx="12" fill="var(--elan-primary-bg)" />
      <polyline
        points="8,26 17,26 20,14 24,38 27,26 44,26"
        stroke="var(--elan-primary-text)" strokeWidth="2.8" strokeLinecap="round" strokeLinejoin="round"
        fill="none"
      />
    </svg>
  );
}

export default function TopBar() {
  const { user, logout } = useAuth();
  const { theme, toggle } = useTheme();
  const navigate = useNavigate();
  const initials = user?.name
    ? user.name.split(' ').map(w => w[0]).slice(0, 2).join('').toUpperCase()
    : (user?.email?.[0] ?? '?').toUpperCase();

  return (
    <header style={{
      display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      padding: '16px 24px', flexShrink: 0,
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        <ElanWaveform />
        <span style={{
          fontFamily: 'var(--elan-serif)', fontSize: '1.25rem',
          color: 'var(--elan-ch-800)', letterSpacing: '-0.01em',
        }}>
          Élan
        </span>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <button
          onClick={toggle}
          aria-label={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
          title={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
          style={{
            width: 34, height: 34, borderRadius: 'var(--r-md)',
            background: 'transparent', color: 'var(--elan-ch-400)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            flexShrink: 0, transition: 'color var(--t-fast), background var(--t-fast)',
          }}
          onMouseEnter={e => {
            e.currentTarget.style.color = 'var(--elan-ch-800)';
            e.currentTarget.style.background = 'var(--elan-ch-100)';
          }}
          onMouseLeave={e => {
            e.currentTarget.style.color = 'var(--elan-ch-400)';
            e.currentTarget.style.background = 'transparent';
          }}
        >
          {theme === 'dark'
            ? <Sun size={18} strokeWidth={1.8} />
            : <Moon size={18} strokeWidth={1.8} />}
        </button>
        <button
          onClick={() => navigate('/settings')}
          aria-label="Settings"
          style={{
            width: 34, height: 34, borderRadius: 'var(--r-md)',
            background: 'transparent', color: 'var(--elan-ch-400)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            flexShrink: 0, transition: 'color var(--t-fast)',
          }}
          onMouseEnter={e => e.currentTarget.style.color = 'var(--elan-ch-800)'}
          onMouseLeave={e => e.currentTarget.style.color = 'var(--elan-ch-400)'}
        >
          <Settings size={18} strokeWidth={1.8} />
        </button>
        <button
          onClick={() => navigate('/profile')}
          aria-label="Profile"
          style={{
            width: 34, height: 34, borderRadius: '50%',
            background: 'var(--elan-primary-bg)', color: 'var(--elan-primary-text)',
            fontSize: '0.78rem', fontWeight: 700,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            flexShrink: 0,
            boxShadow: 'var(--shadow-xs)',
          }}
        >
          {initials}
        </button>
      </div>
    </header>
  );
}
