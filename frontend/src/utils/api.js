/**
 * API client for the Preventive Health Assistant backend.
 */

const BASE = '/api/v1';

/**
 * Send a chat message.
 *
 * @param {string} message
 * @param {string|null} sessionId
 * @returns {Promise<{session_id, reply, assessment_complete, result}>}
 */
export async function sendChatMessage(message, sessionId = null) {
  const res = await fetch(`${BASE}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, session_id: sessionId }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

/**
 * Delete (clear) a chat session.
 */
export async function deleteSession(sessionId) {
  const res = await fetch(`${BASE}/chat/session/${sessionId}`, { method: 'DELETE' });
  if (!res.ok) throw new Error(`Failed to clear session: HTTP ${res.status}`);
  return res.json();
}

/**
 * Fetch diabetes model info.
 */
export async function getDiabetesModelInfo() {
  const res = await fetch(`${BASE}/health/diabetes/model-info`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}
