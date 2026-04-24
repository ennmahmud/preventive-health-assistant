import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';

function ElanWaveform() {
  return (
    <svg width="28" height="28" viewBox="0 0 52 52" fill="none" aria-hidden="true">
      <rect width="52" height="52" rx="12" fill="var(--elan-ch-800)" />
      <polyline
        points="8,26 17,26 20,14 24,38 27,26 44,26"
        stroke="white" strokeWidth="2.8" strokeLinecap="round" strokeLinejoin="round"
        fill="none"
      />
    </svg>
  );
}

export default function TopBar() {
  const { user, logout } = useAuth();
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

      <button
        onClick={() => navigate('/profile')}
        aria-label="Profile"
        style={{
          width: 36, height: 36, borderRadius: '50%',
          background: 'var(--elan-ch-800)', color: '#fff',
          fontSize: '0.78rem', fontWeight: 700,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          flexShrink: 0,
        }}
      >
        {initials}
      </button>
    </header>
  );
}
