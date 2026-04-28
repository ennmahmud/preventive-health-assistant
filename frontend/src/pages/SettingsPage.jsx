import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ChevronLeft, Lock, Shield, Info, Moon, Sun, LogOut, Trash2 } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { useTheme } from '../contexts/ThemeContext';
import ElanButton from '../components/ui/ElanButton';
import ElanInput  from '../components/ui/ElanInput';
import FloatingNav from '../components/layout/FloatingNav';

function Group({ title, children }) {
  return (
    <section style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
      <h2 style={{ fontSize: '0.68rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.08em', color: 'var(--elan-ch-400)', margin: 0, paddingLeft: 4 }}>
        {title}
      </h2>
      <div style={{ background: 'var(--elan-surface)', border: '1px solid var(--elan-border)', borderRadius: 'var(--r-lg)', overflow: 'hidden', boxShadow: 'var(--shadow-xs)' }}>
        {children}
      </div>
    </section>
  );
}

function InfoRow({ label, value }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '13px 16px', borderBottom: '1px solid var(--elan-sep)' }}>
      <span style={{ fontSize: '0.875rem', fontWeight: 500, color: 'var(--elan-ch-800)' }}>{label}</span>
      <span style={{ fontSize: '0.84rem', color: 'var(--elan-ch-400)', maxWidth: '60%', textAlign: 'right', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{value || '—'}</span>
    </div>
  );
}

function DangerButton({ icon: Icon, label, onClick }) {
  return (
    <button onClick={onClick} style={{
      display: 'flex', alignItems: 'center', gap: 12,
      padding: '13px 16px', width: '100%', background: 'none',
      borderBottom: '1px solid var(--elan-sep)', cursor: 'pointer',
      color: 'var(--elan-tc-400)', fontSize: '0.9rem', fontWeight: 500,
      transition: 'background var(--t-fast)',
    }}
      onMouseEnter={e => e.currentTarget.style.background = 'rgba(204,88,64,0.05)'}
      onMouseLeave={e => e.currentTarget.style.background = 'none'}
    >
      <Icon size={16} />
      {label}
    </button>
  );
}

export default function SettingsPage() {
  const { user, logout, changePassword, deleteAccount } = useAuth();
  const { theme, toggle } = useTheme();
  const navigate = useNavigate();

  // Password form
  const [pwd, setPwd]         = useState({ current: '', next: '', confirm: '' });
  const [pwdLoading, setPwdL] = useState(false);
  const [pwdError, setPwdErr] = useState('');
  const [pwdSaved, setPwdSav] = useState(false);
  const setP = k => e => setPwd(p => ({ ...p, [k]: e.target.value }));

  // Confirmation states
  const [confirmLogout, setConfirmLogout] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [deletePassword, setDeletePassword] = useState('');
  const [deleteError, setDeleteError]     = useState('');
  const [deleteLoading, setDeleteLoading] = useState(false);

  const handleChangePwd = async (e) => {
    e.preventDefault();
    setPwdErr('');
    if (pwd.next.length < 8) { setPwdErr('New password must be at least 8 characters.'); return; }
    if (pwd.next !== pwd.confirm) { setPwdErr('Passwords do not match.'); return; }
    setPwdL(true);
    try {
      await changePassword(pwd.current, pwd.next);
      setPwd({ current: '', next: '', confirm: '' });
      setPwdSav(true);
      setTimeout(() => setPwdSav(false), 2500);
    } catch (err) {
      setPwdErr(err.response?.data?.detail || 'Incorrect current password.');
    } finally { setPwdL(false); }
  };

  const handleLogout = () => { logout(); navigate('/signin', { replace: true }); };

  const handleDelete = async () => {
    setDeleteError(''); setDeleteLoading(true);
    try {
      await deleteAccount(deletePassword);
      navigate('/signin', { replace: true });
    } catch (err) {
      setDeleteError(err.response?.data?.detail || 'Incorrect password.');
      setDeleteLoading(false);
    }
  };

  return (
    <div style={{ height: '100dvh', display: 'flex', flexDirection: 'column', background: 'var(--elan-bg)' }}>
      {/* Header */}
      <div style={{ padding: '16px 20px', display: 'flex', alignItems: 'center', gap: 12, flexShrink: 0, borderBottom: '1px solid var(--elan-sep)' }}>
        <button onClick={() => navigate(-1)} style={{ background: 'none', color: 'var(--elan-ch-500)', display: 'flex', alignItems: 'center', cursor: 'pointer' }}>
          <ChevronLeft size={18} />
        </button>
        <span style={{ fontWeight: 700, fontSize: '1rem', color: 'var(--elan-ch-800)' }}>Settings</span>
      </div>

      <div style={{ flex: 1, overflowY: 'auto', padding: '24px 20px 120px', display: 'flex', flexDirection: 'column', gap: 24 }}>

        {/* Account */}
        <Group title="Account">
          <InfoRow label="Name"         value={user?.name} />
          <InfoRow label="Email"        value={user?.email} />
          <InfoRow label="Member since" value={user?.created_at ? new Date(user.created_at).toLocaleDateString('en-GB', { month: 'long', year: 'numeric' }) : ''} />
        </Group>

        {/* Appearance */}
        <Group title="Appearance">
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '13px 16px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              {theme === 'dark' ? <Moon size={16} color="var(--elan-ch-400)" /> : <Sun size={16} color="var(--elan-ch-400)" />}
              <span style={{ fontSize: '0.875rem', fontWeight: 500, color: 'var(--elan-ch-800)' }}>Dark mode</span>
            </div>
            {/* Toggle switch */}
            <button onClick={toggle} role="switch" aria-checked={theme === 'dark'}
              style={{
                width: 48, height: 28, borderRadius: 'var(--r-pill)', border: 'none', cursor: 'pointer',
                background: theme === 'dark' ? 'var(--elan-ch-800)' : 'var(--elan-ch-200)',
                position: 'relative', transition: 'background var(--t-base)',
                flexShrink: 0,
              }}>
              <span style={{
                position: 'absolute', top: 3,
                left: theme === 'dark' ? 23 : 3,
                width: 22, height: 22, borderRadius: '50%', background: '#fff',
                boxShadow: '0 1px 4px rgba(0,0,0,0.2)',
                transition: 'left var(--t-base) var(--ease-spring)',
              }} />
            </button>
          </div>
        </Group>

        {/* Change password */}
        <Group title="Security">
          <div style={{ padding: '16px', display: 'flex', flexDirection: 'column', gap: 14 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <Lock size={15} color="var(--elan-ch-400)" />
              <span style={{ fontWeight: 600, fontSize: '0.9rem', color: 'var(--elan-ch-800)' }}>Change Password</span>
            </div>
            <form onSubmit={handleChangePwd} noValidate style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              <ElanInput id="pwd-cur" label="Current password" type="password" value={pwd.current} onChange={setP('current')} autoComplete="current-password" />
              <ElanInput id="pwd-new" label="New password"     type="password" value={pwd.next}    onChange={setP('next')}    autoComplete="new-password" />
              <ElanInput id="pwd-cfm" label="Confirm new"      type="password" value={pwd.confirm} onChange={setP('confirm')} autoComplete="new-password" />
              {pwdError && (
                <p role="alert" style={{ fontSize: '0.8rem', color: 'var(--elan-tc-500)', padding: '8px 12px', background: 'var(--elan-tc-50)', borderRadius: 'var(--r-sm)', border: '1px solid var(--elan-tc-100)', margin: 0 }}>
                  {pwdError}
                </p>
              )}
              <ElanButton type="submit" loading={pwdLoading}
                style={pwdSaved ? { background: 'var(--elan-sg-600)', alignSelf: 'flex-start', height: 40, padding: '0 18px' } : { alignSelf: 'flex-start', height: 40, padding: '0 18px' }}>
                {pwdSaved ? 'Updated!' : 'Update Password'}
              </ElanButton>
            </form>
          </div>
        </Group>

        {/* Privacy */}
        <Group title="Privacy & Data">
          <div style={{ display: 'flex', alignItems: 'flex-start', gap: 12, padding: '14px 16px' }}>
            <Shield size={15} color="var(--elan-sg-600)" style={{ flexShrink: 0, marginTop: 2 }} />
            <p style={{ fontSize: '0.84rem', color: 'var(--elan-ch-500)', lineHeight: 1.65, margin: 0 }}>
              All health data is stored locally on this device and on your local API server. Nothing is shared with third parties.
            </p>
          </div>
        </Group>

        {/* About */}
        <Group title="About">
          <InfoRow label="App"        value="Preventive Health Assistant" />
          <InfoRow label="Version"    value="1.0.0" />
          <InfoRow label="Models"     value="XGBoost · NHANES · Claude AI" />
          <div style={{ display: 'flex', alignItems: 'flex-start', gap: 8, padding: '10px 16px' }}>
            <Info size={13} color="var(--elan-ch-300)" style={{ flexShrink: 0, marginTop: 1 }} />
            <span style={{ fontSize: '0.74rem', color: 'var(--elan-ch-400)', lineHeight: 1.55 }}>
              For informational use only. Always consult a qualified healthcare professional.
            </span>
          </div>
        </Group>

        {/* Account actions */}
        <Group title="Account Actions">
          {!confirmLogout ? (
            <DangerButton icon={LogOut} label="Sign Out" onClick={() => setConfirmLogout(true)} />
          ) : (
            <div style={{ padding: '14px 16px', display: 'flex', flexDirection: 'column', gap: 10, borderBottom: '1px solid var(--elan-sep)' }}>
              <span style={{ fontSize: '0.875rem', color: 'var(--elan-ch-800)' }}>Sign out of your account?</span>
              <div style={{ display: 'flex', gap: 8 }}>
                <button onClick={handleLogout} style={{ height: 36, padding: '0 16px', background: 'var(--elan-tc-400)', color: '#fff', border: 'none', borderRadius: 'var(--r-xs)', fontSize: '0.84rem', fontWeight: 600, cursor: 'pointer' }}>
                  Sign Out
                </button>
                <button onClick={() => setConfirmLogout(false)} style={{ height: 36, padding: '0 16px', background: 'var(--elan-ch-100)', color: 'var(--elan-ch-700)', border: 'none', borderRadius: 'var(--r-xs)', fontSize: '0.84rem', cursor: 'pointer' }}>
                  Cancel
                </button>
              </div>
            </div>
          )}

          {!confirmDelete ? (
            <DangerButton icon={Trash2} label="Delete Account" onClick={() => setConfirmDelete(true)} />
          ) : (
            <div style={{ padding: '14px 16px', display: 'flex', flexDirection: 'column', gap: 10 }}>
              <span style={{ fontSize: '0.875rem', color: 'var(--elan-ch-800)', lineHeight: 1.5 }}>
                This permanently deletes your account and all data. Enter your password to confirm.
              </span>
              <ElanInput id="del-pwd" label="Your password" type="password"
                value={deletePassword} onChange={e => setDeletePassword(e.target.value)} autoComplete="current-password" />
              {deleteError && (
                <p role="alert" style={{ fontSize: '0.8rem', color: 'var(--elan-tc-500)', padding: '8px 12px', background: 'var(--elan-tc-50)', borderRadius: 'var(--r-sm)', border: '1px solid var(--elan-tc-100)', margin: 0 }}>
                  {deleteError}
                </p>
              )}
              <div style={{ display: 'flex', gap: 8 }}>
                <button onClick={handleDelete} disabled={deleteLoading || !deletePassword}
                  style={{ height: 36, padding: '0 16px', background: 'var(--elan-tc-400)', color: '#fff', border: 'none', borderRadius: 'var(--r-xs)', fontSize: '0.84rem', fontWeight: 600, cursor: 'pointer', opacity: deleteLoading || !deletePassword ? 0.5 : 1 }}>
                  {deleteLoading ? 'Deleting…' : 'Delete Forever'}
                </button>
                <button onClick={() => { setConfirmDelete(false); setDeletePassword(''); setDeleteError(''); }}
                  style={{ height: 36, padding: '0 16px', background: 'var(--elan-ch-100)', color: 'var(--elan-ch-700)', border: 'none', borderRadius: 'var(--r-xs)', fontSize: '0.84rem', cursor: 'pointer' }}>
                  Cancel
                </button>
              </div>
            </div>
          )}
        </Group>

      </div>
      <FloatingNav />
    </div>
  );
}
