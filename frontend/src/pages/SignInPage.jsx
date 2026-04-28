import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import ElanButton from '../components/ui/ElanButton';
import ElanInput  from '../components/ui/ElanInput';

function ElanBrand() {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 12, marginBottom: 32 }}>
      <svg width="52" height="52" viewBox="0 0 52 52" fill="none" aria-hidden="true">
        <rect width="52" height="52" rx="14" fill="var(--elan-primary-bg)" />
        <polyline points="8,26 17,26 20,14 24,38 27,26 44,26"
          stroke="var(--elan-primary-text)" strokeWidth="2.8" strokeLinecap="round" strokeLinejoin="round" fill="none" />
      </svg>
      <div style={{ textAlign: 'center' }}>
        <div style={{
          fontFamily: 'var(--elan-serif)', fontSize: '2rem',
          color: 'var(--elan-ch-800)', letterSpacing: '-0.01em', lineHeight: 1,
        }}>Élan</div>
        <div style={{ fontSize: '0.8rem', color: 'var(--elan-ch-400)', marginTop: 4, letterSpacing: '0.06em' }}>
          LIVE WITH INTENTION
        </div>
      </div>
    </div>
  );
}

export default function SignInPage() {
  const { login, isLoading } = useAuth();
  const navigate = useNavigate();

  const [form, setForm] = useState({ email: '', password: '' });
  const [error, setError] = useState('');

  const set = (k) => (e) => setForm(p => ({ ...p, [k]: e.target.value }));

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    if (!form.email || !form.password) { setError('Please fill in all fields.'); return; }
    try {
      await login(form.email, form.password);
      navigate('/dashboard', { replace: true });
    } catch (err) {
      setError(err.response?.data?.detail || 'Invalid email or password.');
    }
  };

  return (
    <div style={{
      minHeight: '100dvh', display: 'flex', alignItems: 'center', justifyContent: 'center',
      background: 'var(--elan-bg)', padding: '24px 16px',
    }}>
      <div style={{ width: '100%', maxWidth: 400 }}>
        <ElanBrand />

        <div style={{
          background: 'var(--elan-surface)', borderRadius: 'var(--r-xl)',
          border: '1px solid var(--elan-border)', boxShadow: 'var(--shadow-md)',
          padding: '32px',
        }}>
          <h1 style={{
            fontFamily: 'var(--elan-serif)', fontSize: '1.5rem',
            color: 'var(--elan-ch-800)', marginBottom: 24,
          }}>Welcome back</h1>

          <form onSubmit={handleSubmit} noValidate style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
            <ElanInput id="email" label="Email" type="email" value={form.email}
              onChange={set('email')} autoComplete="email" required />
            <ElanInput id="password" label="Password" type="password" value={form.password}
              onChange={set('password')} autoComplete="current-password" required />

            {error && (
              <p role="alert" style={{
                fontSize: '0.84rem', color: 'var(--elan-tc-500)',
                padding: '10px 14px', background: 'var(--elan-tc-50)',
                borderRadius: 'var(--r-sm)', border: '1px solid var(--elan-tc-100)',
              }}>{error}</p>
            )}

            <ElanButton type="submit" loading={isLoading} fullWidth style={{ marginTop: 4 }}>
              Sign In
            </ElanButton>
          </form>
        </div>

        <p style={{ textAlign: 'center', marginTop: 20, fontSize: '0.875rem', color: 'var(--elan-ch-500)' }}>
          Don't have an account?{' '}
          <Link to="/signup" style={{ color: 'var(--elan-ch-800)', fontWeight: 600 }}>Create one</Link>
        </p>
      </div>
    </div>
  );
}
