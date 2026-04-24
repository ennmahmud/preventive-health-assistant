import client from './client';

export const sendMessage = (message, sessionId) =>
  client.post('/chat', { message, session_id: sessionId }).then(r => r.data);

export const clearSession = (sessionId) =>
  client.delete(`/chat/session/${sessionId}`).then(r => r.data);
