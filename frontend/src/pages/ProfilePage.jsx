import { useState } from 'react';
import { Save, CheckCircle, Camera } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import styles from './ProfilePage.module.css';

const GENDER_OPTIONS = [
  { value: 'male',   label: 'Male' },
  { value: 'female', label: 'Female' },
  { value: 'other',  label: 'Non-binary / Other' },
  { value: 'prefer_not', label: 'Prefer not to say' },
];

export default function ProfilePage() {
  const { user, updateProfile } = useAuth();
  const [form, setForm] = useState({
    name:   user?.name   || '',
    email:  user?.email  || '',
    dob:    user?.dob    || '',
    gender: user?.gender || '',
    height: user?.height || '',
    weight: user?.weight || '',
  });
  const [saved, setSaved] = useState(false);
  const [errors, setErrors] = useState({});

  const set = (field) => (e) => setForm(f => ({ ...f, [field]: e.target.value }));

  const bmiVal = (() => {
    const h = parseFloat(form.height) / 100;
    const w = parseFloat(form.weight);
    if (!h || !w || h <= 0) return null;
    return (w / (h * h)).toFixed(1);
  })();

  const bmiMeta = (b) => {
    if (!b) return null;
    const v = parseFloat(b);
    if (v < 18.5) return { label: 'Underweight', color: '#007AFF' };
    if (v < 25)   return { label: 'Healthy',     color: '#34C759' };
    if (v < 30)   return { label: 'Overweight',  color: '#FF9500' };
    return               { label: 'Obese',        color: '#FF3B30' };
  };

  const validate = () => {
    const errs = {};
    if (!form.name.trim()) errs.name = 'Name is required.';
    if (!form.email.match(/^[^\s@]+@[^\s@]+\.[^\s@]+$/)) errs.email = 'Enter a valid email.';
    return errs;
  };

  const handleSave = (e) => {
    e.preventDefault();
    const errs = validate();
    if (Object.keys(errs).length) { setErrors(errs); return; }
    setErrors({});
    updateProfile(form);
    setSaved(true);
    setTimeout(() => setSaved(false), 2500);
  };

  const bmiInfo = bmiMeta(bmiVal);

  return (
    <div className={styles.page}>
      <header className={styles.pageHeader}>
        <h1 className={styles.pageTitle}>Profile</h1>
        <p className={styles.pageSub}>Manage your personal information and health metrics.</p>
      </header>

      {/* Avatar hero */}
      <div className={styles.avatarSection}>
        <div className={styles.avatarWrap}>
          <div className={styles.avatar}>{user?.avatarInitials || '?'}</div>
          <button className={styles.avatarEditBtn} aria-label="Change photo" disabled>
            <Camera size={14} strokeWidth={2} />
          </button>
        </div>
        <div className={styles.avatarInfo}>
          <div className={styles.avatarName}>{user?.name || 'Your Name'}</div>
          <div className={styles.avatarEmail}>{user?.email || ''}</div>
          {user?.createdAt && (
            <div className={styles.avatarSince}>
              Member since {new Date(user.createdAt).toLocaleDateString('en-GB', { month: 'long', year: 'numeric' })}
            </div>
          )}
        </div>
      </div>

      <form className={styles.form} onSubmit={handleSave} noValidate>
        {/* Personal info */}
        <FieldGroup title="Personal Information">
          <Field id="prof-name" label="Full name" required error={errors.name}>
            <input className={`${styles.input} ${errors.name ? styles.inputError : ''}`} id="prof-name" type="text" value={form.name} onChange={set('name')} placeholder="Jane Doe" autoComplete="name" />
          </Field>
          <Field id="prof-email" label="Email address" required error={errors.email}>
            <input className={`${styles.input} ${errors.email ? styles.inputError : ''}`} id="prof-email" type="email" value={form.email} onChange={set('email')} placeholder="jane@example.com" autoComplete="email" />
          </Field>
          <Field id="prof-dob" label="Date of birth">
            <input className={styles.input} id="prof-dob" type="date" value={form.dob} onChange={set('dob')} max={new Date().toISOString().split('T')[0]} />
          </Field>
          <Field id="prof-gender" label="Biological sex">
            <select className={styles.input} id="prof-gender" value={form.gender} onChange={set('gender')}>
              <option value="">Select…</option>
              {GENDER_OPTIONS.map(g => <option key={g.value} value={g.value}>{g.label}</option>)}
            </select>
          </Field>
        </FieldGroup>

        {/* Body metrics */}
        <FieldGroup title="Body Metrics">
          <div className={styles.metricRow}>
            <Field id="prof-height" label="Height (cm)">
              <input className={styles.input} id="prof-height" type="number" min="50" max="300" value={form.height} onChange={set('height')} placeholder="170" />
            </Field>
            <Field id="prof-weight" label="Weight (kg)">
              <input className={styles.input} id="prof-weight" type="number" min="20" max="500" value={form.weight} onChange={set('weight')} placeholder="70" />
            </Field>
          </div>

          {bmiVal && bmiInfo && (
            <div className={styles.bmiCard} style={{ borderColor: `${bmiInfo.color}30`, background: `${bmiInfo.color}08` }}>
              <div className={styles.bmiLeft}>
                <div className={styles.bmiTitle}>BMI</div>
                <div className={styles.bmiValue} style={{ color: bmiInfo.color }}>{bmiVal}</div>
              </div>
              <div>
                <div className={styles.bmiCat} style={{ color: bmiInfo.color, background: `${bmiInfo.color}18` }}>{bmiInfo.label}</div>
                <div className={styles.bmiHint}>Body Mass Index based on height and weight.</div>
              </div>
            </div>
          )}
        </FieldGroup>

        <div className={styles.saveRow}>
          <button
            className={`${styles.saveBtn} ${saved ? styles.saveBtnDone : ''}`}
            type="submit"
          >
            {saved
              ? <><CheckCircle size={16} strokeWidth={2.5} /> Saved</>
              : <><Save size={16} strokeWidth={2} /> Save Changes</>}
          </button>
        </div>
      </form>
    </div>
  );
}

function FieldGroup({ title, children }) {
  return (
    <section className={styles.group}>
      <h2 className={styles.groupTitle}>{title}</h2>
      <div className={styles.groupCard}>{children}</div>
    </section>
  );
}

function Field({ id, label, required, error, children }) {
  return (
    <div className={styles.field}>
      <label className={styles.label} htmlFor={id}>
        {label}{required && <span className={styles.required}> *</span>}
      </label>
      {children}
      {error && <span className={styles.fieldError} role="alert">{error}</span>}
    </div>
  );
}
