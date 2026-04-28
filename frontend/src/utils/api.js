/* API client for the Preventive Health Assistant backend. */

const BASE = '/api/v1';

/* Attach the user's JWT (or fall back to no auth in dev) to every request. */
function authHeaders(extra = {}) {
  const headers = { ...extra };
  try {
    const token = localStorage.getItem('elan_token');
    if (token) headers.Authorization = `Bearer ${token}`;
  } catch { /* localStorage unavailable (SSR / private mode) — skip */ }
  return headers;
}

async function handleResponse(res) {
  if (res.status === 401) {
    // Token expired / missing — bounce to sign-in just like the axios client does.
    try {
      localStorage.removeItem('elan_token');
      localStorage.removeItem('elan_user');
    } catch { /* ignore */ }
    if (typeof window !== 'undefined' && !window.location.pathname.startsWith('/signin')) {
      window.location.href = '/signin';
    }
  }
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

// ── Chat ─────────────────────────────────────────────────────────────────────

/* Send a chat message. */
export async function sendChatMessage(message, sessionId = null, userId = null, assessmentContext = null) {
  const res = await fetch(`${BASE}/chat`, {
    method: 'POST',
    headers: authHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify({
      message,
      session_id: sessionId,
      user_id: userId,
      assessment_context: assessmentContext ?? null,
    }),
  });
  return handleResponse(res);
}

export async function deleteSession(sessionId) {
  const res = await fetch(`${BASE}/chat/session/${sessionId}`, {
    method: 'DELETE',
    headers: authHeaders(),
  });
  return handleResponse(res);
}

// ── Profile ───────────────────────────────────────────────────────────────────

export async function getUserProfile(userId) {
  const res = await fetch(`${BASE}/profile/${userId}`, { headers: authHeaders() });
  return handleResponse(res);
}

export async function upsertUserProfile(userId, profileData) {
  const res = await fetch(`${BASE}/profile`, {
    method: 'POST',
    headers: authHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify({ user_id: userId, ...profileData }),
  });
  return handleResponse(res);
}

export async function deleteUserProfile(userId) {
  const res = await fetch(`${BASE}/profile/${userId}`, {
    method: 'DELETE',
    headers: authHeaders(),
  });
  return handleResponse(res);
}

export async function getAssessmentHistory(userId, limit = 20) {
  const res = await fetch(`${BASE}/profile/${userId}/history?limit=${limit}`, {
    headers: authHeaders(),
  });
  return handleResponse(res);
}

export async function getAllConditionsTrend(userId) {
  // Fetch last 20 assessments for trend charts
  return getAssessmentHistory(userId, 20);
}

// ── Structured Assessment ─────────────────────────────────────────────────────

/* Run a structured lifestyle-based assessment. */
export async function runStructuredAssessment(payload) {
  const res = await fetch(`${BASE}/assessment`, {
    method: 'POST',
    headers: authHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify(payload),
  });
  return handleResponse(res);
}

export async function getAssessmentQuestions(condition) {
  const res = await fetch(`${BASE}/assessment/questions/${condition}`, {
    headers: authHeaders(),
  });
  return handleResponse(res);
}

/* Run a what-if simulation. */
export async function simulateWhatIf(condition, baselineAnswers, changes, userId = null) {
  const res = await fetch(`${BASE}/assessment/simulate`, {
    method: 'POST',
    headers: authHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify({
      condition,
      baseline_answers: baselineAnswers,
      changes,
      user_id: userId,
    }),
  });
  return handleResponse(res);
}

// ── Cohort Comparison ─────────────────────────────────────────────────────────

/* Fetch cohort average risk for a given condition, age, and gender. */
export async function getCohortComparison(condition, age, gender, userRisk = null) {
  let url = `${BASE}/assessment/cohort?condition=${condition}&age=${age}&gender=${gender}`;
  if (userRisk !== null) url += `&user_risk=${userRisk}`;
  const res = await fetch(url, { headers: authHeaders() });
  return handleResponse(res);
}

// ── Model Info ────────────────────────────────────────────────────────────────

export async function getDiabetesModelInfo() {
  const res = await fetch(`${BASE}/health/diabetes/model-info`, { headers: authHeaders() });
  return handleResponse(res);
}
