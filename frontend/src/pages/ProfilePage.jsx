import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ChevronLeft, Check } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import ElanButton from '../components/ui/ElanButton';
import ElanInput from '../components/ui/ElanInput';
import FloatingNav from '../components/layout/FloatingNav';

const GENDER_OPTIONS = [
  { value: '',       label: 'Prefer not to say' },
  { value: 'male',   label: 'Male' },
  { value: 'female', label: 'Female' },
  { value: 'other',  label: 'Other' },
];

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
      <span style={{ fontSize: '0.84rem', color: 'var(--elan-ch-400)', maxWidth: '55%', textAlign: 'right', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{value || '—'}</span>
    </div>
  );
}

export default function ProfilePage() {
  const { user, updateProfile } = useAuth();
  const navigate = useNavigate();

  const [form, setForm] = useState({
    name:   user?.name   || '',
    dob:    user?.dob    || '',
    gender: user?.gender || '',
    height: user?.height || '',
    weight: user?.weight || '',
  });
  const [loading, setLoading]   = useState(false);
  const [saved,   setSaved]     = useState(false);
  const [error,   setError]     = useState('');

  const set = k => e => setForm(p => ({ ...p, [k]: e.target.value }));

  const initials = user?.name
    ? user.name.split(' ').map(w => w[0]).slice(0, 2).join('').toUpperCase()
    : (user?.email?.[0] ?? '?').toUpperCase();

  const bmi = (() => {
    const h = parseFloat(form.height);
    const w = parseFloat(form.weight);
    if (h > 0 && w > 0) return (w / ((h / 100) ** 2)).toFixed(1);
    return null;
  })();

  const handleSave = async (e) => {
    e.preventDefault();
    setError(''); setLoading(true);
    try {
      const updates = {};
      Object.entries(form).forEach(([k, v]) => { if (v !== '') updates[k] = v; });
      await updateProfile(updates);
      setSaved(true);
      setTimeout(() => setSaved(false), 2500);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to save profile.');
    } finally {
      setLoading(false);
    }
  };

  const selectStyle = {
    height: 48, width: '100%', padding: '0 12px',
    background: '#fff', border: '1.5px solid var(--elan-ch-200)',
    borderRadius: 'var(--r-md)', color: 'var(--elan-ch-800)',
    fontSize: '0.9375rem', outline: 'none', appearance: 'none',
    transition: 'border-color var(--t-fast)',
  };

  return (
    <div style={{ height: '100dvh', display: 'flex', flexDirection: 'column', background: 'var(--elan-bg)' }}>
      {/* Header */}
      <div style={{ padding: '16px 20px', display: 'flex', alignItems: 'center', gap: 12, flexShrink: 0, borderBottom: '1px solid var(--elan-sep)' }}>
        <button onClick={() => navigate(-1)} style={{ background: 'none', color: 'var(--elan-ch-500)', display: 'flex', alignItems: 'center', gap: 4, fontSize: '0.875rem', cursor: 'pointer' }}>
          <ChevronLeft size={18} />
        </button>
        <span style={{ fontWeight: 700, fontSize: '1rem', color: 'var(--elan-ch-800)' }}>Profile</span>
      </div>

      <div style={{ flex: 1, overflowY: 'auto', padding: '24px 20px 120px', display: 'flex', flexDirection: 'column', gap: 24 }}>
        {/* Avatar */}
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 12 }}>
          <div style={{
            width: 72, height: 72, borderRadius: '50%',
            background: 'var(--elan-ch-800)', color: '#fff',
            fontFamily: 'var(--elan-serif)', fontSize: '1.6rem',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}>
            {initials}
          </div>
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontFamily: 'var(--elan-serif)', fontSize: '1.2rem', color: 'var(--elan-ch-800)' }}>
              {user?.name || 'Your Name'}
            </div>
            <div style={{ fontSize: '0.8rem', color: 'var(--elan-ch-400)', marginTop: 2 }}>{user?.email}</div>
          </div>
        </div>

        {/* Account info (read-only) */}
        <Group title="Account">
          <InfoRow label="Email"        value={user?.email} />
          <InfoRow label="Member since" value={user?.created_at ? new Date(user.created_at).toLocaleDateString('en-GB', { month: 'long', year: 'numeric' }) : ''} />
          <div style={{ padding: '13px 16px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: '0.875rem', fontWeight: 500, color: 'var(--elan-ch-800)' }}>BMI</span>
            <span style={{ fontSize: '0.84rem', color: bmi ? 'var(--elan-ch-600)' : 'var(--elan-ch-300)', fontFamily: bmi ? 'var(--elan-serif)' : 'inherit' }}>
              {bmi || 'Fill height & weight'}
            </span>
          </div>
        </Group>

        {/* Editable fields */}
        <form onSubmit={handleSave} noValidate>
          <Group title="Personal Details">
            <div style={{ padding: '16px', display: 'flex', flexDirection: 'column', gap: 16 }}>
              {error && (
                <p role="alert" style={{ fontSize: '0.82rem', color: 'var(--elan-tc-500)', padding: '10px 14px', background: 'var(--elan-tc-50)', borderRadius: 'var(--r-sm)', border: '1px solid var(--elan-tc-100)', margin: 0 }}>
                  {error}
                </p>
              )}

              <ElanInput id="name" label="Full name" type="text" value={form.name} onChange={set('name')} autoComplete="name" />
              <ElanInput id="dob"  label="Date of birth" type="date" value={form.dob}  onChange={set('dob')} />

              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                <label style={{ fontSize: '0.78rem', fontWeight: 600, color: 'var(--elan-ch-600)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
                  Sex
                </label>
                <select value={form.gender} onChange={set('gender')} style={selectStyle}>
                  {GENDER_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
                </select>
              </div>

              <div style={{ display: 'flex', gap: 12 }}>
                <div style={{ flex: 1 }}>
                  <ElanInput id="height" label="Height (cm)" type="number" value={form.height} onChange={set('height')} placeholder="170" />
                </div>
                <div style={{ flex: 1 }}>
                  <ElanInput id="weight" label="Weight (kg)" type="number" value={form.weight} onChange={set('weight')} placeholder="70" />
                </div>
              </div>

              <ElanButton
                type="submit" loading={loading} fullWidth
                style={saved ? { background: 'var(--elan-sg-600)' } : {}}
              >
                {saved ? <><Check size={16} /> Saved</> : 'Save Changes'}
              </ElanButton>
            </div>
          </Group>
        </form>
      </div>

      <FloatingNav />
    </div>
  );
}
