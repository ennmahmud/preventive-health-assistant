import client from './client';

function userId() {
  try {
    const u = JSON.parse(localStorage.getItem('elan_user') || 'null');
    return u?.id ?? null;
  } catch { return null; }
}

export const assessDiabetes = (metrics) =>
  client.post('/health/diabetes/assess', { metrics, include_explanation: true, include_recommendations: true, user_id: userId() }).then(r => r.data);

export const assessCVD = (metrics) =>
  client.post('/health/cvd/assess', { metrics, include_explanation: true, include_recommendations: true, user_id: userId() }).then(r => r.data);

export const assessHypertension = (metrics) =>
  client.post('/health/hypertension/assess', { metrics, include_explanation: true, include_recommendations: true, user_id: userId() }).then(r => r.data);
