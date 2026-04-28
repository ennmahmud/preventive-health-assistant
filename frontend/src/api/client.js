import axios from 'axios';

const BASE = import.meta.env.VITE_API_URL
  ? `${import.meta.env.VITE_API_URL}/api/v1`
  : '/api/v1';

const client = axios.create({ baseURL: BASE, timeout: 30000 });

client.interceptors.request.use((config) => {
  const token = localStorage.getItem('elan_token');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

client.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('elan_token');
      localStorage.removeItem('elan_user');
      window.location.href = '/signin';
    }
    return Promise.reject(err);
  }
);

export default client;
