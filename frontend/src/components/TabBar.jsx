import styles from './TabBar.module.css';

const TABS = [
  { id: 'chat', label: '💬 Chat', desc: 'Conversational' },
  { id: 'assessment', label: '📋 Assessment', desc: 'Step-by-step' },
];

export default function TabBar({ activeTab, onTabChange }) {
  return (
    <div className={styles.tabBar}>
      {TABS.map((tab) => (
        <button
          key={tab.id}
          className={`${styles.tab} ${activeTab === tab.id ? styles.active : ''}`}
          onClick={() => onTabChange(tab.id)}
        >
          <span className={styles.label}>{tab.label}</span>
          <span className={styles.desc}>{tab.desc}</span>
        </button>
      ))}
    </div>
  );
}
