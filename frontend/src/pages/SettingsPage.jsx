import { useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Eye, EyeOff, LogOut, Trash2, Shield, Info, Lock } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import styles from './SettingsPage.module.css';

export default function SettingsPage() {
  const { user, logout, changePassword, deleteAccount } = useAuth();
  const navigate = useNavigate();

  const [pwdForm, setPwdForm] = useState({ current: '', next: '', confirm: '' });
  const [showPwd, setShowPwd]   = useState(false);
  const [pwdError, setPwdError] = useState('');
  const [pwdSaved, setPwdSaved] = useState(false);
  const [pwdLoading, setPwdLoading] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [confirmLogout, setConfirmLogout] = useState(false);
  const [deleteLoading, setDeleteLoading] = useState(false);
  const [deleteError, setDeleteError] = useState('');
  const [deletePwd, setDeletePwd] = useState('');

  const setP = (f) => (e) => setPwdForm(p => ({ ...p, [f]: e.target.value }));

  const handleChangePwd = useCallback(async (e) => {
    e.preventDefault();
    setPwdError('');
    if (pwdForm.next.length < 8) { setPwdError('New password must be at least 8 characters.'); return; }
    if (pwdForm.next !== pwdForm.confirm) { setPwdError('Passwords do not match.'); return; }
    setPwdLoading(true);
    try {
      await changePassword(pwdForm.current, pwdForm.next);
      setPwdForm({ current: '', next: '', confirm: '' });
      setPwdSaved(true);
      setTimeout(() => setPwdSaved(false), 2500);
    } catch (err) {
      setPwdError(err?.response?.data?.detail || 'Failed to update password.');
    } finally {
      setPwdLoading(false);
    }
  }, [pwdForm, changePassword]);

  const handleLogout = useCallback(() => {
    logout();
    navigate('/signin', { replace: true });
  }, [logout, navigate]);

  const handleDelete = useCallback(async () => {
    setDeleteError('');
    setDeleteLoading(true);
    try {
      await deleteAccount(deletePwd);
      navigate('/signin', { replace: true });
    } catch (err) {
      setDeleteError(err?.response?.data?.detail || 'Deletion failed.');
    } finally {
      setDeleteLoading(false);
    }
  }, [deletePwd, deleteAccount, navigate]);

  return (
    <div className={styles.page}>
      <header className={styles.pageHeader}>
        <h1 className={styles.pageTitle}>Settings</h1>
        <p className={styles.pageSub}>Account preferences and privacy controls.</p>
      </header>

      {/* Account info */}
      <Group title="Account">
        <Row label="Name"         value={user?.name || '—'} />
        <Row label="Email"        value={user?.email || '—'} />
        <Row label="Member since" value={user?.created_at ? new Date(user.created_at).toLocaleDateString('en-GB', { month: 'long', year: 'numeric' }) : '—'} />
      </Group>

      {/* Change password */}
      <Group title="Security">
        <div className={styles.pwdSection}>
          <div className={styles.pwdHeader}>
            <Lock size={16} color="var(--color-text-muted)" />
            <span className={styles.pwdTitle}>Change Password</span>
          </div>
          <form className={styles.pwdForm} onSubmit={handleChangePwd} noValidate>
            <PwdField id="pwd-cur" label="Current password" value={pwdForm.current} onChange={setP('current')} show={showPwd} onToggle={() => setShowPwd(v => !v)} autoComplete="current-password" />
            <PwdField id="pwd-new" label="New password"     value={pwdForm.next}    onChange={setP('next')}    show={showPwd} onToggle={() => setShowPwd(v => !v)} autoComplete="new-password" />
            <PwdField id="pwd-cfm" label="Confirm new"      value={pwdForm.confirm} onChange={setP('confirm')} show={showPwd} onToggle={() => setShowPwd(v => !v)} autoComplete="new-password" />
            {pwdError && <p className={styles.pwdError} role="alert">{pwdError}</p>}
            <button className={`${styles.pwdBtn} ${pwdSaved ? styles.pwdBtnDone : ''}`} type="submit" disabled={pwdLoading}>
              {pwdSaved ? 'Password updated!' : pwdLoading ? 'Updating…' : 'Update Password'}
            </button>
          </form>
        </div>
      </Group>

      {/* Privacy */}
      <Group title="Privacy & Data">
        <div className={styles.infoRow}>
          <Shield size={16} color="var(--color-accent)" className={styles.shieldIcon} />
          <p className={styles.privacyText}>
            All health data is stored locally on this device. Nothing is shared with third parties. Assessment results are processed by the API running on your local network.
          </p>
        </div>
      </Group>

      {/* About */}
      <Group title="About">
        <Row label="App"        value="Preventive Health Assistant" />
        <Row label="Version"    value="1.0.0" />
        <Row label="Models"     value="XGBoost · NHANES · Claude AI" />
        <Row label="Disclaimer" value="Not a substitute for medical advice" />
        <div className={styles.aboutBadge}>
          <Info size={13} color="var(--color-text-muted)" />
          <span>For informational use only. Always consult a qualified healthcare professional.</span>
        </div>
      </Group>

      {/* Danger zone */}
      <Group title="Account Actions">
        {!confirmLogout ? (
          <button className={styles.dangerRow} onClick={() => setConfirmLogout(true)}>
            <LogOut size={16} />
            <span>Sign Out</span>
          </button>
        ) : (
          <div className={styles.confirmRow}>
            <span className={styles.confirmText}>Sign out of your account?</span>
            <div className={styles.confirmBtns}>
              <button className={styles.confirmYes} onClick={handleLogout}>Sign Out</button>
              <button className={styles.confirmNo}  onClick={() => setConfirmLogout(false)}>Cancel</button>
            </div>
          </div>
        )}

        {!confirmDelete ? (
          <button className={`${styles.dangerRow} ${styles.dangerRowDelete}`} onClick={() => setConfirmDelete(true)}>
            <Trash2 size={16} />
            <span>Delete Account</span>
          </button>
        ) : (
          <div className={styles.confirmRow}>
            <span className={styles.confirmText}>Enter your password to permanently delete your account and all data.</span>
            <input
              className={styles.pwdInput}
              type="password"
              placeholder="Your password"
              value={deletePwd}
              onChange={e => setDeletePwd(e.target.value)}
              autoComplete="current-password"
            />
            {deleteError && <p className={styles.pwdError} role="alert">{deleteError}</p>}
            <div className={styles.confirmBtns}>
              <button className={styles.confirmYes} onClick={handleDelete} disabled={deleteLoading}>
                {deleteLoading ? 'Deleting…' : 'Delete Forever'}
              </button>
              <button className={styles.confirmNo} onClick={() => { setConfirmDelete(false); setDeletePwd(''); setDeleteError(''); }}>
                Cancel
              </button>
            </div>
          </div>
        )}
      </Group>
    </div>
  );
}

function Group({ title, children }) {
  return (
    <section className={styles.group}>
      <h2 className={styles.groupTitle}>{title}</h2>
      <div className={styles.groupCard}>{children}</div>
    </section>
  );
}

function Row({ label, value }) {
  return (
    <div className={styles.row}>
      <span className={styles.rowLabel}>{label}</span>
      <span className={styles.rowValue}>{value}</span>
    </div>
  );
}

function PwdField({ id, label, value, onChange, show, onToggle, autoComplete }) {
  return (
    <div className={styles.pwdField}>
      <label className={styles.pwdLabel} htmlFor={id}>{label}</label>
      <div className={styles.pwdWrap}>
        <input id={id} className={styles.pwdInput} type={show ? 'text' : 'password'} value={value} onChange={onChange} autoComplete={autoComplete} />
        <button type="button" className={styles.eyeBtn} onClick={onToggle} aria-label={show ? 'Hide password' : 'Show password'}>
          {show ? <EyeOff size={14} /> : <Eye size={14} />}
        </button>
      </div>
    </div>
  );
}
