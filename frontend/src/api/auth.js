import client from './client';

export async function login(email, password) {
  const form = new URLSearchParams({ username: email, password });
  const { data } = await client.post('/auth/login', form, {
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  });
  return data; // { access_token, token_type, user }
}

export async function register(name, email, password) {
  const { data } = await client.post('/auth/register', { name, email, password });
  return data;
}

export function logout() {
  localStorage.removeItem('elan_token');
  localStorage.removeItem('elan_user');
}
