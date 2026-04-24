import client from './client';

export const assessDiabetes = (metrics) =>
  client.post('/health/diabetes/assess', { metrics, include_explanation: true, include_recommendations: true }).then(r => r.data);

export const assessCVD = (metrics) =>
  client.post('/health/cvd/assess', { metrics, include_explanation: true, include_recommendations: true }).then(r => r.data);

export const assessHypertension = (metrics) =>
  client.post('/health/hypertension/assess', { metrics, include_explanation: true, include_recommendations: true }).then(r => r.data);
