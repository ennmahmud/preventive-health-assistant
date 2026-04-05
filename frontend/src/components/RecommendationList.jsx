/**
 * RecommendationList
 * Renders health recommendations grouped by priority.
 * Accepts `recommendations` array from the /assess endpoints.
 */

import styles from './RecommendationList.module.css';

const PRIORITY_CONFIG = {
  high:   { label: 'High priority', color: 'var(--color-very-high)', icon: '🔴' },
  medium: { label: 'Moderate',       color: 'var(--color-moderate)',  icon: '🟡' },
  low:    { label: 'Low priority',   color: 'var(--color-low)',       icon: '🟢' },
};

const CATEGORY_ICONS = {
  diet:       '🥗',
  exercise:   '🏃',
  medical:    '🏥',
  lifestyle:  '💡',
  weight:     '⚖️',
  smoking:    '🚭',
  monitoring: '📊',
};

export default function RecommendationList({ recommendations = [] }) {
  if (!recommendations.length) return null;

  const grouped = {
    high:   recommendations.filter((r) => r.priority === 'high'),
    medium: recommendations.filter((r) => r.priority === 'medium'),
    low:    recommendations.filter((r) => r.priority === 'low'),
  };

  return (
    <div className={styles.container}>
      <h3 className={styles.title}>Recommendations</h3>
      {['high', 'medium', 'low'].map((priority) => {
        const items = grouped[priority];
        if (!items.length) return null;
        const cfg = PRIORITY_CONFIG[priority];
        return (
          <div key={priority} className={styles.group}>
            <p className={styles.groupLabel} style={{ color: cfg.color }}>
              {cfg.icon} {cfg.label}
            </p>
            {items.map((rec, i) => (
              <RecommendationItem key={i} rec={rec} />
            ))}
          </div>
        );
      })}
    </div>
  );
}

function RecommendationItem({ rec }) {
  const icon = CATEGORY_ICONS[rec.category?.toLowerCase()] ?? '•';
  return (
    <div className={styles.item}>
      <span className={styles.itemIcon}>{icon}</span>
      <div className={styles.itemBody}>
        <p className={styles.itemText}>{rec.recommendation}</p>
        {rec.rationale && (
          <p className={styles.itemRationale}>{rec.rationale}</p>
        )}
        {rec.source && (
          <p className={styles.itemSource}>Source: {rec.source}</p>
        )}
      </div>
    </div>
  );
}
