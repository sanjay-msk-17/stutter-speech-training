'use client';
import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuthStore } from '@/lib/authStore';
import { progressAPI } from '@/lib/api';
import AppLayout from '@/components/AppLayout';
import {
  LineChart, Line, PieChart, Pie, Cell, Tooltip, ResponsiveContainer,
  XAxis, YAxis, CartesianGrid, Legend
} from 'recharts';

const CLASS_COLORS: Record<string, string> = {
  'Fluent Speech': '#10b981',
  'Block': '#ef4444',
  'Prolongation': '#f59e0b',
  'Sound Repetition': '#6366f1',
  'Word Repetition': '#a78bfa',
  'Interjection': '#ec4899',
};

const STAT_CARDS = [
  { key: 'session_count', label: 'Sessions', icon: '🎤', suffix: '' },
  { key: 'streak', label: 'Day Streak', icon: '🔥', suffix: ' days' },
  { key: 'points', label: 'Points', icon: '⭐', suffix: '' },
  { key: 'improvement_score', label: 'Improvement', icon: '📈', suffix: '%' },
];

export default function DashboardPage() {
  const router = useRouter();
  const { token, user } = useAuthStore();
  const [progress, setProgress] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!token) { router.replace('/login'); return; }
    progressAPI.getProgress().then(r => setProgress(r.data)).catch(() => {}).finally(() => setLoading(false));
  }, [token, router]);

  if (loading) return (
    <AppLayout>
      <div className="flex items-center justify-center h-64">
        <div className="w-8 h-8 rounded-full border-4 border-indigo-500 border-t-transparent animate-spin" />
      </div>
    </AppLayout>
  );

  const sessions = progress?.sessions || [];
  const history = progress?.stutter_history || [];

  // Build line chart data (last 10 sessions: fluent ratio over time)
  const lineData = history.slice(-10).map((h: any, i: number) => ({
    name: `S${i + 1}`,
    'Fluent %': Math.round((h.fluent_ratio || 0) * 100),
  }));

  // Build pie chart data from aggregated label_counts across all sessions
  const totalCounts: Record<string, number> = {};
  sessions.forEach((s: any) => {
    if (s.label_counts) {
      Object.entries(s.label_counts).forEach(([k, v]) => {
        totalCounts[k] = (totalCounts[k] || 0) + (v as number);
      });
    }
  });
  const pieData = Object.entries(totalCounts).map(([name, value]) => ({ name, value }));

  const totalMinutes = Math.round((progress?.total_time || 0) / 60);

  return (
    <AppLayout>
      <div className="fade-up space-y-8">
        {/* Header */}
        <div>
          <h1 className="text-3xl font-bold text-white">
            Welcome back, <span className="grad-text">{user?.name?.split(' ')[0]}</span> 👋
          </h1>
          <p className="text-gray-400 mt-1">Here's your speech training progress</p>
        </div>

        {/* Stat cards */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {STAT_CARDS.map(({ key, label, icon, suffix }) => (
            <div key={key} className="glass p-5">
              <div className="text-2xl mb-2">{icon}</div>
              <div className="text-2xl font-bold text-white">
                {key === 'improvement_score'
                  ? `${progress?.[key] > 0 ? '+' : ''}${progress?.[key] ?? 0}`
                  : (progress?.[key] ?? 0)}{suffix}
              </div>
              <div className="text-gray-400 text-sm mt-1">{label}</div>
            </div>
          ))}
          <div className="glass p-5">
            <div className="text-2xl mb-2">⏱️</div>
            <div className="text-2xl font-bold text-white">{totalMinutes} min</div>
            <div className="text-gray-400 text-sm mt-1">Total Speaking Time</div>
          </div>
        </div>

        {/* Charts row */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Fluent % trend */}
          <div className="glass p-6">
            <h2 className="text-lg font-semibold text-white mb-4">Fluency Trend</h2>
            {lineData.length > 0 ? (
              <ResponsiveContainer width="100%" height={220}>
                <LineChart data={lineData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                  <XAxis dataKey="name" stroke="#6b7280" tick={{ fill: '#9ca3af' }} />
                  <YAxis stroke="#6b7280" tick={{ fill: '#9ca3af' }} domain={[0, 100]} unit="%" />
                  <Tooltip contentStyle={{ background: '#1e1b4b', border: '1px solid #4f46e5', borderRadius: 8 }} />
                  <Line type="monotone" dataKey="Fluent %" stroke="#6366f1" strokeWidth={2}
                    dot={{ fill: '#6366f1', r: 4 }} activeDot={{ r: 6, fill: '#a78bfa' }} />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex flex-col items-center justify-center h-[220px] text-gray-500">
                <span className="text-4xl mb-3">🎤</span>
                <p>No sessions yet — start recording!</p>
              </div>
            )}
          </div>

          {/* Stutter type distribution pie */}
          <div className="glass p-6">
            <h2 className="text-lg font-semibold text-white mb-4">Stutter Type Distribution</h2>
            {pieData.length > 0 ? (
              <ResponsiveContainer width="100%" height={220}>
                <PieChart>
                  <Pie data={pieData} cx="50%" cy="50%" innerRadius={55} outerRadius={85}
                    paddingAngle={3} dataKey="value">
                    {pieData.map((entry, i) => (
                      <Cell key={i} fill={CLASS_COLORS[entry.name] || '#6366f1'} />
                    ))}
                  </Pie>
                  <Tooltip contentStyle={{ background: '#1e1b4b', border: '1px solid #4f46e5', borderRadius: 8 }} />
                  <Legend formatter={(v) => <span style={{ color: '#9ca3af' }}>{v}</span>} />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex flex-col items-center justify-center h-[220px] text-gray-500">
                <span className="text-4xl mb-3">📊</span>
                <p>Record a session to see distribution</p>
              </div>
            )}
          </div>
        </div>

        {/* Recent sessions */}
        <div className="glass p-6">
          <h2 className="text-lg font-semibold text-white mb-4">Recent Sessions</h2>
          {sessions.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              <span className="text-4xl mb-3 block">🎙️</span>
              <p>No sessions recorded yet</p>
              <a href="/analysis" className="text-indigo-400 text-sm mt-2 inline-block hover:text-indigo-300">
                Start your first session →
              </a>
            </div>
          ) : (
            <div className="space-y-3">
              {sessions.slice(0, 8).map((s: any) => (
                <div key={s.id} className="flex items-center justify-between p-3 rounded-xl"
                  style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.06)' }}>
                  <div className="flex items-center gap-3">
                    <div className="w-2 h-2 rounded-full"
                      style={{ background: CLASS_COLORS[s.predicted_class] || '#6366f1' }} />
                    <div>
                      <p className="text-white text-sm font-medium">{s.predicted_class}</p>
                      <p className="text-gray-500 text-xs">
                        {s.timestamp ? new Date(s.timestamp).toLocaleString() : '—'}
                      </p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="text-white text-sm">{Math.round(s.duration || 0)}s</p>
                    <p className="text-gray-500 text-xs">{Math.round((s.fluent_ratio || 0) * 100)}% fluent</p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </AppLayout>
  );
}
