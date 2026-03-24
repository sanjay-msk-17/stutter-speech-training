'use client';
import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface AuthUser {
  id: number;
  name: string;
  email: string;
}

interface AuthState {
  token: string | null;
  user: AuthUser | null;
  setAuth: (token: string, user: AuthUser) => void;
  clearAuth: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      token: null,
      user: null,
      setAuth: (token, user) => {
        if (typeof window !== 'undefined') {
          localStorage.setItem('token', token);
          localStorage.setItem('user', JSON.stringify(user));
        }
        set({ token, user });
      },
      clearAuth: () => {
        if (typeof window !== 'undefined') {
          localStorage.removeItem('token');
          localStorage.removeItem('user');
        }
        set({ token: null, user: null });
      },
    }),
    { name: 'auth-storage' }
  )
);
