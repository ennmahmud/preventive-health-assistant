import styles from './ConditionSelector.module.css';

const CONDITIONS = [
  {
    id: 'diabetes',
    emoji: '🩸',
    label: 'Diabetes',
    desc: 'Risk of developing type 2 diabetes based on your lifestyle, diet, and family history.',
    factors: ['Diet & sugar intake', 'Activity level', 'Family history', 'Body weight'],
  },
  {
    id: 'cvd',
    emoji: '❤️',
    label: 'Heart Disease (CVD)',
    desc: 'Risk of cardiovascular disease including heart attack and stroke.',
    factors: ['Smoking & alcohol', 'Activity level', 'Family history', 'Stress & diet'],
  },
  {
    id: 'hypertension',
    emoji: '🫀',
    label: 'Hypertension',
    desc: 'Risk of developing high blood pressure — no BP reading required.',
    factors: ['Salt intake', 'Activity & weight', 'Family history', 'Sleep & stress'],
  },
];

export default function ConditionSelector({ onSelect, isLoading }) {
  return (
    <div className={styles.grid}>
      {CONDITIONS.map((c) => (
        <button
          key={c.id}
          className={styles.card}
          onClick={() => onSelect(c.id)}
          disabled={isLoading}
        >
          <div className={styles.emoji}>{c.emoji}</div>
          <div className={styles.label}>{c.label}</div>
          <div className={styles.desc}>{c.desc}</div>
          <ul className={styles.factors}>
            {c.factors.map((f) => (
              <li key={f}>{f}</li>
            ))}
          </ul>
          <div className={styles.cta}>Start Assessment →</div>
        </button>
      ))}
    </div>
  );
}
