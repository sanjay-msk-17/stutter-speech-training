'use client';
import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuthStore } from '@/lib/authStore';

export default function Home() {
  const router = useRouter();
  const { token } = useAuthStore();

  useEffect(() => {
    if (token) router.replace('/dashboard');
    else router.replace('/login');
  }, [token, router]);

  return (
    <div className="flex items-center justify-center min-h-screen">
      <div className="w-8 h-8 rounded-full border-4 border-indigo-500 border-t-transparent animate-spin" />
    </div>
  );
}
