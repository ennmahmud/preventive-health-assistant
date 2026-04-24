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
      background: 'var(--elan-ch-800)', borderRadius: 'var(--r-pill)',
      padding: '8px 12px', boxShadow: 'var(--shadow-nav)',
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
              background: active ? 'rgba(255,255,255,0.15)' : 'transparent',
              color: active ? '#FFFFFF' : 'rgba(255,255,255,0.50)',
              transition: 'background var(--t-fast) var(--ease-out), color var(--t-fast)',
              minWidth: 64, minHeight: 44,
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
