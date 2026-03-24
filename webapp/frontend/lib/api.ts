import axios from 'axios';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_URL,
  headers: { 'Content-Type': 'application/json' },
});

// Attach JWT token to every request
api.interceptors.request.use((config) => {
  if (typeof window !== 'undefined') {
    const token = localStorage.getItem('token');
    if (token) config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Auto-logout on 401
api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401 && typeof window !== 'undefined') {
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      window.location.href = '/login';
    }
    return Promise.reject(err);
  }
);

export default api;

// ── Auth ──────────────────────────────────────
export const authAPI = {
  signup: (data: { name: string; email: string; password: string }) =>
    api.post('/auth/signup', data),
  login: (data: { email: string; password: string }) =>
    api.post('/auth/login', data),
  logout: () => api.post('/auth/logout'),
  me: () => api.get('/auth/me'),
};

// ── Audio / Prediction ──────────────────────
export const predictionAPI = {
  uploadAudio: (blob: Blob, filename = 'recording.webm') => {
    const form = new FormData();
    form.append('file', blob, filename);
    return api.post('/upload-audio', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 120000,
    });
  },
};

// ── Sentences ────────────────────────────────
export const sentencesAPI = {
  getSentences: (count = 3) => api.get(`/get-sentences?count=${count}`),
};

// ── Progress ─────────────────────────────────
export const progressAPI = {
  getProgress: () => api.get('/get-progress'),
  saveProgress: (data: object) => api.post('/save-progress', data),
};
