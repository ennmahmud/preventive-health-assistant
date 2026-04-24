import { NavLink, useNavigate } from 'react-router-dom';
import {
  LayoutDashboard, MessageCircle, ClipboardList,
  TrendingUp, User, Settings, Heart, LogOut,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import styles from './Sidebar.module.css';

const NAV_MAIN = [
  { to: '/',           Icon: LayoutDashboard, label: 'Dashboard',  end: true },
  { to: '/chat',       Icon: MessageCircle,   label: 'Chat' },
  { to: '/assessment', Icon: ClipboardList,   label: 'Assessment' },
  { to: '/progress',   Icon: TrendingUp,      label: 'Progress' },
];

const NAV_SECONDARY = [
  { to: '/profile',  Icon: User,     label: 'Profile' },
  { to: '/settings', Icon: Settings, label: 'Settings' },
];

export default function Sidebar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login', { replace: true });
  };

  return (
    <aside className={styles.sidebar} role="navigation" aria-label="Main navigation">
      {/* Brand */}
      <div className={styles.brand}>
        <div className={styles.brandIconWrap}>
          <Heart size={16} strokeWidth={2.5} color="#fff" />
        </div>
        <div>
          <div className={styles.brandName}>Health Assistant</div>
          <div className={styles.brandSub}>Preventive Risk AI</div>
        </div>
      </div>

      {/* Primary navigation */}
      <nav className={styles.nav}>
        <span className={styles.navSection}>Menu</span>
        {NAV_MAIN.map(({ to, Icon, label, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            className={({ isActive }) => `${styles.navItem} ${isActive ? styles.active : ''}`}
          >
            {({ isActive }) => (
              <>
                <Icon size={17} strokeWidth={isActive ? 2.5 : 2} className={styles.navIcon} />
                <span className={styles.navLabel}>{label}</span>
              </>
            )}
          </NavLink>
        ))}
      </nav>

      {/* Secondary navigation */}
      <div className={styles.navBottom}>
        <span className={styles.navSection}>Account</span>
        {NAV_SECONDARY.map(({ to, Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) => `${styles.navItem} ${isActive ? styles.active : ''}`}
          >
            {({ isActive }) => (
              <>
                <Icon size={17} strokeWidth={isActive ? 2.5 : 2} className={styles.navIcon} />
                <span className={styles.navLabel}>{label}</span>
              </>
            )}
          </NavLink>
        ))}
        <button className={`${styles.navItem} ${styles.logoutBtn}`} onClick={handleLogout} aria-label="Sign out">
          <LogOut size={17} strokeWidth={2} className={styles.navIcon} />
          <span className={styles.navLabel}>Sign Out</span>
        </button>
      </div>

      {/* User card footer */}
      <div className={styles.footer}>
        <div className={styles.userRow}>
          <div className={styles.userAvatar}>{user?.avatarInitials || '?'}</div>
          <div className={styles.userInfo}>
            <div className={styles.userName}>{user?.name || 'Guest'}</div>
            <div className={styles.userEmail}>{user?.email || ''}</div>
          </div>
        </div>
      </div>
    </aside>
  );
}
