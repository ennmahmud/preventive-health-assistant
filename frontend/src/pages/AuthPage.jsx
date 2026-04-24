import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Heart, Eye, EyeOff, AlertCircle } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import styles from './AuthPage.module.css';

export default function AuthPage({ defaultMode = 'login' }) {
  const [mode, setMode] = useState(defaultMode);
  const [form, setForm] = useState({ name: '', email: '', password: '', confirm: '' });
  const [showPwd, setShowPwd] = useState(false);
  const [errors, setErrors] = useState({});
  const [isLoading, setIsLoading] = useState(false);
  const { login, signup } = useAuth();
  const navigate = useNavigate();

  const set = (field) => (e) => setForm(f => ({ ...f, [field]: e.target.value }));

  const validate = () => {
    const errs = {};
    if (mode === 'signup' && !form.name.trim()) errs.name = 'Full name is required.';
    if (!form.email.match(/^[^\s@]+@[^\s@]+\.[^\s@]+$/)) errs.email = 'Enter a valid email address.';
    if (form.password.length < 8) errs.password = 'Password must be at least 8 characters.';
    if (mode === 'signup' && form.password !== form.confirm) errs.confirm = 'Passwords do not match.';
    return errs;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    const errs = validate();
    if (Object.keys(errs).length) { setErrors(errs); return; }
    setErrors({});
    setIsLoading(true);
    try {
      if (mode === 'login') login(form.email, form.password);
      else signup(form.name.trim(), form.email, form.password);
      navigate('/', { replace: true });
    } catch (err) {
      setErrors({ submit: err.message });
    } finally {
      setIsLoading(false);
    }
  };

  const switchMode = (m) => {
    setMode(m);
    setErrors({});
    setForm({ name: '', email: '', password: '', confirm: '' });
  };

  return (
    <div className={styles.page}>
      <div className={styles.card}>
        <div className={styles.brand}>
          <div className={styles.brandIcon}>
            <Heart size={18} strokeWidth={2.5} color="#fff" />
          </div>
          <div>
            <div className={styles.brandName}>Health Assistant</div>
            <div className={styles.brandSub}>Preventive Risk AI</div>
          </div>
        </div>

        <div className={styles.toggle} role="tablist">
          <button role="tab" aria-selected={mode === 'login'} className={`${styles.toggleBtn} ${mode === 'login' ? styles.toggleActive : ''}`} onClick={() => switchMode('login')}>Sign In</button>
          <button role="tab" aria-selected={mode === 'signup'} className={`${styles.toggleBtn} ${mode === 'signup' ? styles.toggleActive : ''}`} onClick={() => switchMode('signup')}>Create Account</button>
        </div>

        <form className={styles.form} onSubmit={handleSubmit} noValidate>
          {mode === 'signup' && (
            <div className={styles.field}>
              <label className={styles.label} htmlFor="auth-name">Full name <span className={styles.required}>*</span></label>
              <input id="auth-name" className={`${styles.input} ${errors.name ? styles.inputError : ''}`} type="text" value={form.name} onChange={set('name')} placeholder="Jane Doe" autoComplete="name" />
              {errors.name && <FieldError msg={errors.name} />}
            </div>
          )}

          <div className={styles.field}>
            <label className={styles.label} htmlFor="auth-email">Email <span className={styles.required}>*</span></label>
            <input id="auth-email" className={`${styles.input} ${errors.email ? styles.inputError : ''}`} type="email" value={form.email} onChange={set('email')} placeholder="jane@example.com" autoComplete="email" />
            {errors.email && <FieldError msg={errors.email} />}
          </div>

          <div className={styles.field}>
            <label className={styles.label} htmlFor="auth-pwd">Password <span className={styles.required}>*</span></label>
            <div className={styles.pwdWrap}>
              <input id="auth-pwd" className={`${styles.input} ${styles.pwdInput} ${errors.password ? styles.inputError : ''}`} type={showPwd ? 'text' : 'password'} value={form.password} onChange={set('password')} placeholder={mode === 'signup' ? 'At least 8 characters' : '••••••••'} autoComplete={mode === 'login' ? 'current-password' : 'new-password'} />
              <button type="button" className={styles.eyeBtn} onClick={() => setShowPwd(v => !v)} aria-label={showPwd ? 'Hide password' : 'Show password'}>
                {showPwd ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            </div>
            {errors.password && <FieldError msg={errors.password} />}
          </div>

          {mode === 'signup' && (
            <div className={styles.field}>
              <label className={styles.label} htmlFor="auth-confirm">Confirm password <span className={styles.required}>*</span></label>
              <input id="auth-confirm" className={`${styles.input} ${errors.confirm ? styles.inputError : ''}`} type="password" value={form.confirm} onChange={set('confirm')} placeholder="Repeat password" autoComplete="new-password" />
              {errors.confirm && <FieldError msg={errors.confirm} />}
            </div>
          )}

          {errors.submit && (
            <div className={styles.submitError} role="alert">
              <AlertCircle size={15} />
              <span>{errors.submit}</span>
            </div>
          )}

          <button className={styles.submitBtn} type="submit" disabled={isLoading} aria-busy={isLoading}>
            {isLoading ? <span className={styles.spinner} /> : (mode === 'login' ? 'Sign In' : 'Create Account')}
          </button>
        </form>

        <p className={styles.footer}>For informational use only · Not medical advice</p>
      </div>
    </div>
  );
}

function FieldError({ msg }) {
  return (
    <div className={styles.fieldError} role="alert">
      <AlertCircle size={12} />
      <span>{msg}</span>
    </div>
  );
}
