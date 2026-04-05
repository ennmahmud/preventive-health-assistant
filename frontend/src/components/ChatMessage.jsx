/**
 * ChatMessage
 * Renders a single conversation turn (user or assistant).
 * Assistant messages support Markdown via react-markdown.
 */

import ReactMarkdown from 'react-markdown';
import styles from './ChatMessage.module.css';

export default function ChatMessage({ message }) {
  const isUser = message.role === 'user';

  return (
    <div className={`${styles.wrapper} ${isUser ? styles.user : styles.assistant}`}>
      <div className={styles.avatar}>
        {isUser ? '👤' : '🩺'}
      </div>
      <div className={`${styles.bubble} ${message.isError ? styles.error : ''}`}>
        {isUser
          ? <p>{message.content}</p>
          : <ReactMarkdown>{message.content}</ReactMarkdown>
        }
      </div>
    </div>
  );
}
