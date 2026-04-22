/* API client for the Preventive Health Assistant backend. */

const BASE = '/api/v1';

async function handleResponse(res) {
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
    headers: { 'Content-Type': 'application/json' },
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

export async function getAssessmentHistory(userId, limit = 20) {
  const res = await fetch(`${BASE}/profile/${userId}/history?limit=${limit}`);
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
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  return handleResponse(res);
}

export async function getAssessmentQuestions(condition) {
  const res = await fetch(`${BASE}/assessment/questions/${condition}`);
  return handleResponse(res);
}

/* Run a what-if simulation. */
export async function simulateWhatIf(condition, baselineAnswers, changes, userId = null) {
  const res = await fetch(`${BASE}/assessment/simulate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
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
  const res = await fetch(url);
  return handleResponse(res);
}

// ── Model Info ────────────────────────────────────────────────────────────────

export async function getDiabetesModelInfo() {
  const res = await fetch(`${BASE}/health/diabetes/model-info`);
  return handleResponse(res);
}
