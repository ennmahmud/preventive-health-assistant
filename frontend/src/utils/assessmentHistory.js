/**
 * Per-user assessment history cache.
 *
 * The localStorage key is namespaced by user id so two accounts on the
 * same browser can't see each other's data. The previous global key
 * `elan_assessments` is treated as legacy and migrated lazily on first
 * read by an authenticated user.
 *
 * The backend's /profile/{user_id}/history endpoint is the source of
 * truth — these helpers exist to (a) keep the UI fast on cold loads
 * and (b) tolerate the API being briefly unavailable.
 */

import { getAssessmentHistory } from './api';

const LEGACY_KEY = 'elan_assessments';
const PER_USER_PREFIX = 'elan_assessments:';
const MAX_CACHED = 50;

function safeUserId() {
  try {
    const raw = localStorage.getItem('elan_user');
    if (!raw) return null;
    const u = JSON.parse(raw);
    return u?.id || null;
  } catch {
    return null;
  }
}

function keyFor(userId) {
  return userId ? `${PER_USER_PREFIX}${userId}` : null;
}

/* Read the per-user cache, falling back to (and migrating from) the
 * legacy global key the first time we see this user. */
export function readLocal(userId = safeUserId()) {
  const k = keyFor(userId);
  if (!k) return [];
  try {
    const cached = localStorage.getItem(k);
    if (cached) return JSON.parse(cached);

    // One-time migration of the old shared key.
    const legacy = localStorage.getItem(LEGACY_KEY);
    if (legacy) {
      const parsed = JSON.parse(legacy);
      if (Array.isArray(parsed) && parsed.length) {
        localStorage.setItem(k, JSON.stringify(parsed.slice(0, MAX_CACHED)));
      }
      // Remove the global key so other users on the same browser don't see it.
      localStorage.removeItem(LEGACY_KEY);
      return parsed || [];
    }
    return [];
  } catch {
    return [];
  }
}

/* Append a freshly-completed assessment to the per-user cache. */
export function appendLocal(record, userId = safeUserId()) {
  const k = keyFor(userId);
  if (!k) return;
  try {
    const stored = readLocal(userId);
    stored.unshift(record);
    localStorage.setItem(k, JSON.stringify(stored.slice(0, MAX_CACHED)));
  } catch {
    /* localStorage full / unavailable — ignore */
  }
}

/* Wipe just this user's cached history (used on logout / account delete). */
export function clearLocal(userId = safeUserId()) {
  const k = keyFor(userId);
  if (k) {
    try { localStorage.removeItem(k); } catch { /* ignore */ }
  }
}

/* Normalise a backend AssessmentResult row into the same shape the UI
 * already uses for locally-cached records:
 *   { condition, completedAt, result: { probability, risk_level, interpretation,
 *                                       top_factors, protective_factors, recommendations } }
 *
 * The backend may return either:
 *   (a) raw_result already in the normalised client shape (stored by appendLocal), OR
 *   (b) flat fields (risk_probability, risk_category) with an optional raw_result
 *       containing explanation / recommendations from the original API response.
 */
function fromApiRow(row) {
  const raw = row.raw_result ?? {};

  // (a) raw_result is already the normalised shape — pass it straight through.
  if (typeof raw.probability === 'number') {
    return {
      condition:   row.condition,
      completedAt: row.created_at ? new Date(row.created_at).getTime() : Date.now(),
      result:      raw,
    };
  }

  // (b) Build normalised shape from flat API fields + optional nested data.
  const riskCategory =
    row.risk_category ??
    raw.risk?.risk_category ??
    '';

  return {
    condition:   row.condition,
    completedAt: row.created_at ? new Date(row.created_at).getTime() : Date.now(),
    result: {
      probability:        row.risk_probability ?? raw.risk?.risk_probability ?? 0,
      risk_level:         riskCategory
                            ? riskCategory.toLowerCase().replace(/\s+/g, '_')
                            : 'low',
      interpretation:     raw.explanation?.summary ?? '',
      top_factors:        raw.explanation?.risk_factors ?? [],
      protective_factors: raw.explanation?.protective_factors ?? [],
      recommendations:    raw.recommendations ?? [],
    },
  };
}

/**
 * Fetch history from the API and update the local cache. On any
 * failure (offline, 401, etc.) we fall back to whatever we already
 * have locally so the UI still renders.
 */
export async function fetchHistory(userId = safeUserId(), { limit = 20 } = {}) {
  if (!userId) return readLocal(userId);
  try {
    const rows = await getAssessmentHistory(userId, limit);
    const normalised = (rows || []).map(fromApiRow);
    const k = keyFor(userId);
    if (k) {
      try {
        localStorage.setItem(k, JSON.stringify(normalised.slice(0, MAX_CACHED)));
      } catch { /* cache write failed — ignore */ }
    }
    return normalised;
  } catch {
    return readLocal(userId);
  }
}
