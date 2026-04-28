import { useLocation, useNavigate } from 'react-router-dom';
import { MessageCircle, ClipboardList, TrendingUp, LayoutDashboard } from 'lucide-react';

const NAV = [
  { to: '/dashboard', Icon: LayoutDashboard, label: 'Home' },
  { to: '/assess',    Icon: ClipboardList,   label: 'Assess' },
  { to: '/chat',      Icon: MessageCircle,   label: 'Chat' },
  { to: '/progress',  Icon: TrendingUp,      label: 'Progress' },
];

export default function FloatingNav() {
  const { pathname } = useLocation();
  const navigate = useNavigate();

  return (
    <nav style={{
      position: 'fixed', bottom: 24, left: '50%', transform: 'translateX(-50%)',
      zIndex: 50, display: 'flex', alignItems: 'center', gap: 4,
      background: 'var(--elan-primary-bg)',
      borderRadius: 'var(--r-pill)',
      padding: '8px 12px',
      boxShadow: 'var(--shadow-nav), var(--glow-cream)',
    }} aria-label="Main navigation">
      {NAV.map(({ to, Icon, label }) => {
        const active = pathname === to || (to !== '/dashboard' && pathname.startsWith(to));
        return (
          <button
            key={to}
            onClick={() => navigate(to)}
            aria-label={label}
            aria-current={active ? 'page' : undefined}
            style={{
              display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 3,
              padding: '8px 16px', borderRadius: 'var(--r-xl)',
              background: active ? 'rgba(20,17,13,0.10)' : 'transparent',
              color: active ? 'var(--elan-primary-text)' : 'var(--elan-primary-muted)',
              transition: 'background var(--t-fast) var(--ease-out), color var(--t-fast)',
              minWidth: 64, minHeight: 44,
            }}
            onMouseEnter={e => {
              if (!active) e.currentTarget.style.color = 'var(--elan-primary-text)';
            }}
            onMouseLeave={e => {
              if (!active) e.currentTarget.style.color = 'var(--elan-primary-muted)';
            }}
          >
            <Icon size={20} strokeWidth={active ? 2.5 : 1.8} />
            <span style={{ fontSize: '0.65rem', fontWeight: active ? 600 : 500, letterSpacing: '0.02em' }}>
              {label}
            </span>
          </button>
        );
      })}
    </nav>
  );
}
