/**
 * useChat — hook for the multi-turn chatbot conversation.
 *
 * Manages:
 *  - messages[]      full conversation history (for display)
 *  - sessionId       persisted across turns
 *  - lastResult      last completed risk assessment result
 *  - isLoading       true while waiting for a reply
 *  - error           last error string (null if none)
 *
 * Usage:
 *   const { messages, send, reset, isLoading, error, lastResult } = useChat();
 */

import { useState, useCallback } from 'react';
import { sendChatMessage, deleteSession } from '../utils/api';

export default function useChat(userId = null) {
  const [messages, setMessages] = useState([]);
  const [sessionId, setSessionId] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [lastResult, setLastResult] = useState(null);

  const send = useCallback(async (text) => {
    if (!text.trim()) return;

    // Optimistically add user message
    const userMsg = { role: 'user', content: text, id: Date.now() };
    setMessages((prev) => [...prev, userMsg]);
    setIsLoading(true);
    setError(null);

    try {
      const data = await sendChatMessage(text, sessionId, userId);
      setSessionId(data.session_id);

      const botMsg = {
        role: 'assistant',
        content: data.reply,
        id: Date.now() + 1,
        assessmentComplete: data.assessment_complete,
        result: data.result,
      };
      setMessages((prev) => [...prev, botMsg]);

      if (data.assessment_complete && data.result) {
        setLastResult(data.result);
      }
    } catch (err) {
      setError(err.message);
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: `⚠️ Something went wrong: ${err.message}. Please try again.`,
          id: Date.now() + 2,
          isError: true,
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  }, [sessionId]);

  const reset = useCallback(async () => {
    if (sessionId) {
      try { await deleteSession(sessionId); } catch (_) { /* ignore */ }
    }
    setMessages([]);
    setSessionId(null);
    setLastResult(null);
    setError(null);
  }, [sessionId]);

  return { messages, send, reset, isLoading, error, lastResult, sessionId };
}
