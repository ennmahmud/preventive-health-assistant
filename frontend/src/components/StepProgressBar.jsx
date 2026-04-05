import styles from './StepProgressBar.module.css';

export default function StepProgressBar({ current, total, labels = [] }) {
  return (
    <div className={styles.bar}>
      {Array.from({ length: total }, (_, i) => {
        const stepNum = i + 1;
        const status = stepNum < current ? 'done' : stepNum === current ? 'active' : 'upcoming';
        return (
          <div key={i} className={`${styles.step} ${styles[status]}`}>
            <div className={styles.circle}>
              {status === 'done' ? '✓' : stepNum}
            </div>
            {labels[i] && <div className={styles.stepLabel}>{labels[i]}</div>}
            {i < total - 1 && <div className={`${styles.connector} ${status === 'done' ? styles.connectorDone : ''}`} />}
          </div>
        );
      })}
    </div>
  );
}
