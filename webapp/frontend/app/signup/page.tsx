'use client';
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import toast from 'react-hot-toast';
import { authAPI } from '@/lib/api';
import { useAuthStore } from '@/lib/authStore';

export default function SignupPage() {
  const router = useRouter();
  const { setAuth } = useAuthStore();
  const [form, setForm] = useState({ name: '', email: '', password: '', confirm: '' });
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (form.password !== form.confirm) { toast.error('Passwords do not match'); return; }
    if (form.password.length < 8) { toast.error('Password must be at least 8 characters'); return; }
    setLoading(true);
    try {
      const res = await authAPI.signup({ name: form.name, email: form.email, password: form.password });
      setAuth(res.data.access_token, res.data.user);
      toast.success(`Welcome, ${res.data.user.name}! 🎉`);
      router.push('/dashboard');
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Signup failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-4" style={{
      background: 'radial-gradient(ellipse at 70% 20%, rgba(167,139,250,0.15) 0%, transparent 60%), radial-gradient(ellipse at 20% 80%, rgba(99,102,241,0.1) 0%, transparent 60%), #030712'
    }}>
      <div className="pointer-events-none fixed inset-0 overflow-hidden">
        <div className="absolute top-20 right-20 w-80 h-80 rounded-full opacity-15 blur-3xl" style={{ background: 'radial-gradient(circle, #a78bfa, transparent)' }} />
        <div className="absolute bottom-20 left-20 w-80 h-80 rounded-full opacity-15 blur-3xl" style={{ background: 'radial-gradient(circle, #6366f1, transparent)' }} />
      </div>

      <div className="w-full max-w-md fade-up">
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl mb-4" style={{ background: 'linear-gradient(135deg, #6366f1, #a78bfa)' }}>
            <span className="text-3xl">🎙️</span>
          </div>
          <h1 className="text-3xl font-bold grad-text">StutterAI</h1>
          <p className="text-gray-400 mt-2">Create your free account</p>
        </div>

        <div className="glass p-8">
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">Full Name</label>
              <input type="text" required className="input-field" placeholder="Your Name"
                value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">Email</label>
              <input type="email" required className="input-field" placeholder="you@example.com"
                value={form.email} onChange={e => setForm({ ...form, email: e.target.value })} />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">Password</label>
              <input type="password" required className="input-field" placeholder="Min 8 characters"
                value={form.password} onChange={e => setForm({ ...form, password: e.target.value })} />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">Confirm Password</label>
              <input type="password" required className="input-field" placeholder="Repeat password"
                value={form.confirm} onChange={e => setForm({ ...form, confirm: e.target.value })} />
            </div>
            <button type="submit" disabled={loading} className="btn-primary w-full flex items-center justify-center gap-2 mt-2">
              {loading ? <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" /> : null}
              {loading ? 'Creating account…' : 'Create Account'}
            </button>
          </form>

          <p className="text-center text-gray-400 text-sm mt-6">
            Already have an account?{' '}
            <Link href="/login" className="text-indigo-400 hover:text-indigo-300 font-medium">Sign In</Link>
          </p>
        </div>
      </div>
    </div>
  );
}
