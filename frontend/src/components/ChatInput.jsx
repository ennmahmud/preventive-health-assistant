/* ChatInput */

import { useState, useRef, useEffect } from 'react';
import styles from './ChatInput.module.css';

export default function ChatInput({ onSend, disabled }) {
  const [value, setValue] = useState('');
  const textareaRef = useRef(null);

  // Auto-resize the textarea to fit content, up to the CSS max-height
  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = 'auto';                          // shrink first
    el.style.height = `${el.scrollHeight}px`;          // then grow to content
  }, [value]);

  // Reset height after sending
  function handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  }

  function submit() {
    const text = value.trim();
    if (!text || disabled) return;
    onSend(text);
    setValue('');
    // Let the useEffect handle height reset on next render
  }

  return (
    <div className={styles.container}>
      <textarea
        ref={textareaRef}
        className={styles.textarea}
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Type a message… (Enter to send)"
        disabled={disabled}
        rows={1}
        autoFocus
      />
      <button
        className={styles.sendBtn}
        onClick={submit}
        disabled={disabled || !value.trim()}
        aria-label="Send"
      >
        {disabled
          ? <span className={styles.spinner} />
          : <SendIcon />
        }
      </button>
    </div>
  );
}

function SendIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
      <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z" />
    </svg>
  );
}
