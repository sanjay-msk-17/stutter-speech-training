'use client';
import React from 'react';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { useAuthStore } from '@/lib/authStore';
import { authAPI } from '@/lib/api';
import toast from 'react-hot-toast';

const NAV = [
  { href: '/dashboard', label: 'Dashboard', icon: '📊' },
  { href: '/analysis', label: 'Speech Analysis', icon: '🎙️' },
  { href: '/exercises', label: 'Training', icon: '🧘' },
];

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { user, clearAuth } = useAuthStore();

  const handleLogout = async () => {
    try { await authAPI.logout(); } catch {}
    clearAuth();
    toast.success('Logged out');
    router.push('/login');
  };

  return (
    <div className="flex min-h-screen">
      {/* Sidebar */}
      <aside className="w-64 flex-shrink-0 flex flex-col" style={{
        background: 'rgba(10,8,25,0.95)',
        borderRight: '1px solid rgba(255,255,255,0.06)',
      }}>
        {/* Logo */}
        <div className="p-6 border-b border-white/5">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl flex items-center justify-center text-xl"
              style={{ background: 'linear-gradient(135deg, #6366f1, #a78bfa)' }}>🎙️</div>
            <div>
              <p className="font-bold text-white">StutterAI</p>
              <p className="text-xs text-gray-500">Speech Training</p>
            </div>
          </div>
        </div>

        {/* Nav */}
        <nav className="flex-1 p-4 space-y-1">
          {NAV.map(({ href, label, icon }) => (
            <Link key={href} href={href}
              className={`sidebar-link ${pathname === href ? 'active' : ''}`}>
              <span className="text-lg">{icon}</span>
              <span>{label}</span>
            </Link>
          ))}
        </nav>

        {/* User */}
        <div className="p-4 border-t border-white/5">
          <div className="glass p-3 mb-3">
            <p className="text-white font-medium text-sm truncate">{user?.name || 'User'}</p>
            <p className="text-gray-500 text-xs truncate">{user?.email}</p>
          </div>
          <button onClick={handleLogout} className="btn-secondary w-full text-sm py-2">
            🚪 Sign Out
          </button>
        </div>
      </aside>

      {/* Main */}
      <main className="flex-1 overflow-auto" style={{ background: '#040812' }}>
        {/* Top glow */}
        <div className="pointer-events-none fixed top-0 left-64 right-0 h-px" style={{
          background: 'linear-gradient(90deg, transparent, #6366f1, transparent)'
        }} />
        <div className="p-8">{children}</div>
      </main>
    </div>
  );
}
