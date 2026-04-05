/**
 * API client for the Preventive Health Assistant backend.
 */

const BASE = '/api/v1';

async function handleResponse(res) {
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

// ── Chat ─────────────────────────────────────────────────────────────────────

/**
 * Send a chat message.
 * @param {string} message
 * @param {string|null} sessionId
 * @param {string|null} userId  — stable user UUID for profile memory
 */
export async function sendChatMessage(message, sessionId = null, userId = null) {
  const res = await fetch(`${BASE}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, session_id: sessionId, user_id: userId }),
  });
  return handleResponse(res);
}

export async function deleteSession(sessionId) {
  const res = await fetch(`${BASE}/chat/session/${sessionId}`, { method: 'DELETE' });
  return handleResponse(res);
}

// ── Profile ───────────────────────────────────────────────────────────────────

export async function getUserProfile(userId) {
  const res = await fetch(`${BASE}/profile/${userId}`);
  return handleResponse(res);
}

export async function upsertUserProfile(userId, profileData) {
  const res = await fetch(`${BASE}/profile`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ user_id: userId, ...profileData }),
  });
  return handleResponse(res);
}

export async function deleteUserProfile(userId) {
  const res = await fetch(`${BASE}/profile/${userId}`, { method: 'DELETE' });
  return handleResponse(res);
}

export async function getAssessmentHistory(userId, limit = 10) {
  const res = await fetch(`${BASE}/profile/${userId}/history?limit=${limit}`);
  return handleResponse(res);
}

// ── Structured Assessment ─────────────────────────────────────────────────────

/**
 * Run a structured lifestyle-based assessment.
 * @param {{ condition, answers, user_id, include_explanation, include_recommendations }} payload
 */
export async function runStructuredAssessment(payload) {
  const res = await fetch(`${BASE}/assessment`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  return handleResponse(res);
}

export async function getAssessmentQuestions(condition) {
  const res = await fetch(`${BASE}/assessment/questions/${condition}`);
  return handleResponse(res);
}

// ── Model Info ────────────────────────────────────────────────────────────────

export async function getDiabetesModelInfo() {
  const res = await fetch(`${BASE}/health/diabetes/model-info`);
  return handleResponse(res);
}
