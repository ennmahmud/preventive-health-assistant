import { useState, useRef, useEffect } from 'react';
import { Send } from 'lucide-react';
import TopBar from '../components/layout/TopBar';
import FloatingNav from '../components/layout/FloatingNav';
import { sendMessage } from '../api/chat';

const SESSION_KEY = 'elan_chat_session';

function Bubble({ msg }) {
  const isUser = msg.role === 'user';
  return (
    <div style={{ display: 'flex', justifyContent: isUser ? 'flex-end' : 'flex-start', marginBottom: 12 }}>
      <div style={{
        maxWidth: '80%', padding: '12px 16px',
        borderRadius: isUser ? '18px 18px 4px 18px' : '18px 18px 18px 4px',
        background: isUser ? 'var(--elan-ch-800)' : 'var(--elan-surface)',
        color: isUser ? '#fff' : 'var(--elan-ch-800)',
        border: isUser ? 'none' : '1px solid var(--elan-border)',
        boxShadow: isUser ? 'none' : 'var(--shadow-xs)',
        fontSize: '0.9rem', lineHeight: 1.65, whiteSpace: 'pre-wrap',
      }}>
        {msg.content}
      </div>
    </div>
  );
}

function TypingDots() {
  return (
    <div style={{ display: 'flex', justifyContent: 'flex-start', marginBottom: 12 }}>
      <div style={{
        padding: '14px 18px', borderRadius: '18px 18px 18px 4px',
        background: 'var(--elan-surface)', border: '1px solid var(--elan-border)',
        boxShadow: 'var(--shadow-xs)', display: 'flex', gap: 5, alignItems: 'center',
      }}>
        {[0, 1, 2].map(i => (
          <span key={i} style={{
            width: 7, height: 7, borderRadius: '50%',
            background: 'var(--elan-ch-300)', display: 'inline-block',
            animation: `elan-bounce 1.2s ease-in-out ${i * 0.2}s infinite`,
          }} />
        ))}
      </div>
    </div>
  );
}

export default function ChatPage() {
  const [messages, setMessages] = useState([{
    role: 'assistant',
    content: "Hi! I'm your Élan health assistant. Ask me about diabetes, heart disease, or hypertension — or just describe your numbers and I'll help interpret them.",
  }]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  // Use session_id returned by the server, not a locally generated UUID
  const [sessionId, setSessionId] = useState(() => localStorage.getItem(SESSION_KEY) || null);
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  const send = async () => {
    const text = input.trim();
    if (!text || loading) return;
    setInput('');
    setMessages(m => [...m, { role: 'user', content: text }]);
    setLoading(true);
    try {
      // Send current sessionId (null on first message — server creates a new one)
      const data = await sendMessage(text, sessionId);
      // Save the server-assigned session_id for subsequent turns
      if (data.session_id) {
        setSessionId(data.session_id);
        localStorage.setItem(SESSION_KEY, data.session_id);
      }
      // Backend field is `reply`, not `response`
      setMessages(m => [...m, { role: 'assistant', content: data.reply || '…' }]);
    } catch (err) {
      const detail = err.response?.data?.detail;
      setMessages(m => [...m, {
        role: 'assistant',
        content: typeof detail === 'string' ? detail : 'Sorry, I could not reach the server. Make sure the API is running.',
      }]);
    } finally {
      setLoading(false);
    }
  };

  const handleKey = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); }
  };

  return (
    <div style={{ height: '100dvh', display: 'flex', flexDirection: 'column', background: 'var(--elan-bg)' }}>
      <TopBar />

      <div style={{ flex: 1, overflowY: 'auto', padding: '12px 16px 8px' }}>
        {messages.map((m, i) => <Bubble key={i} msg={m} />)}
        {loading && <TypingDots />}
        <div ref={bottomRef} />
      </div>

      {/* Input — sits above FloatingNav */}
      <div style={{ padding: '10px 16px 96px', background: 'var(--elan-bg)', borderTop: '1px solid var(--elan-sep)' }}>
        <div style={{
          display: 'flex', alignItems: 'flex-end', gap: 10,
          background: 'var(--elan-surface)', border: '1.5px solid var(--elan-ch-200)',
          borderRadius: 'var(--r-xl)', padding: '10px 14px', boxShadow: 'var(--shadow-xs)',
        }}>
          <textarea
            value={input} onChange={e => setInput(e.target.value)} onKeyDown={handleKey}
            placeholder="Ask about your health…" rows={1}
            style={{
              flex: 1, resize: 'none', border: 'none', background: 'transparent',
              color: 'var(--elan-ch-800)', fontSize: '0.9375rem', lineHeight: 1.5,
              outline: 'none', maxHeight: 120,
            }}
          />
          <button
            onClick={send} disabled={!input.trim() || loading} aria-label="Send"
            style={{
              width: 36, height: 36, borderRadius: '50%', flexShrink: 0,
              background: input.trim() && !loading ? 'var(--elan-ch-800)' : 'var(--elan-ch-100)',
              color: input.trim() && !loading ? '#fff' : 'var(--elan-ch-300)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              transition: 'all var(--t-base)',
            }}
          >
            <Send size={15} />
          </button>
        </div>
      </div>

      <FloatingNav />

      <style>{`
        @keyframes elan-bounce {
          0%, 80%, 100% { transform: translateY(0); opacity: 0.5; }
          40% { transform: translateY(-6px); opacity: 1; }
        }
      `}</style>
    </div>
  );
}
