'use client';
import { useState, useRef, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { useAuthStore } from '@/lib/authStore';
import { predictionAPI } from '@/lib/api';
import AppLayout from '@/components/AppLayout';
import toast from 'react-hot-toast';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Cell
} from 'recharts';

const CLASS_COLORS: Record<string, string> = {
  'Fluent Speech': '#10b981',
  'Block': '#ef4444',
  'Prolongation': '#f59e0b',
  'Sound Repetition': '#6366f1',
  'Word Repetition': '#a78bfa',
  'Interjection': '#ec4899',
};

const MAX_DURATION = 30; // seconds

export default function AnalysisPage() {
  const router = useRouter();
  const { token } = useAuthStore();

  const [recording, setRecording] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [elapsed, setElapsed] = useState(0);
  const [bars, setBars] = useState<number[]>(Array(28).fill(0.3));

  const mediaRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const animRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (!token) router.replace('/login');
  }, [token, router]);

  const stopAll = useCallback(() => {
    if (timerRef.current) clearInterval(timerRef.current);
    if (animRef.current) clearInterval(animRef.current);
    setBars(Array(28).fill(0.3));
  }, []);

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mr = new MediaRecorder(stream, { mimeType: 'audio/webm' });
      chunksRef.current = [];
      mr.ondataavailable = (e) => { if (e.data.size > 0) chunksRef.current.push(e.data); };
      mr.onstop = () => {
        stream.getTracks().forEach((t) => t.stop());
        handleUpload();
      };
      mr.start(250);
      mediaRef.current = mr;
      setRecording(true);
      setResult(null);
      setElapsed(0);

      // Timer
      timerRef.current = setInterval(() => {
        setElapsed((p) => {
          if (p + 1 >= MAX_DURATION) {
            stopRecording();
            return MAX_DURATION;
          }
          return p + 1;
        });
      }, 1000);

      // Waveform animation
      animRef.current = setInterval(() => {
        setBars(Array(28).fill(0).map(() => 0.2 + Math.random() * 0.8));
      }, 80);
    } catch {
      toast.error('Microphone access denied. Please allow microphone in browser settings.');
    }
  };

  const stopRecording = () => {
    if (mediaRef.current && mediaRef.current.state !== 'inactive') {
      mediaRef.current.stop();
    }
    setRecording(false);
    stopAll();
  };

  const handleUpload = async () => {
    if (chunksRef.current.length === 0) { toast.error('No audio captured'); return; }
    const blob = new Blob(chunksRef.current, { type: 'audio/webm' });
    setAnalyzing(true);
    try {
      const res = await predictionAPI.uploadAudio(blob, 'recording.webm');
      setResult(res.data);
      toast.success('Analysis complete!');
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Analysis failed — try again');
    } finally {
      setAnalyzing(false);
    }
  };

  const progress = (elapsed / MAX_DURATION) * 100;

  const barData = result?.label_counts
    ? Object.entries(result.label_counts).map(([name, value]) => ({ name, value }))
    : [];

  const fluentPct = result ? Math.round((result.fluent_ratio || 0) * 100) : 0;

  return (
    <AppLayout>
      <div className="fade-up space-y-8 max-w-3xl mx-auto">
        {/* Header */}
        <div>
          <h1 className="text-3xl font-bold text-white">Speech Analysis</h1>
          <p className="text-gray-400 mt-1">Record your speech and get an instant stutter analysis</p>
        </div>

        {/* Recorder card */}
        <div className="glass p-8">
          {/* Waveform */}
          <div className="flex items-center justify-center gap-[3px] h-20 mb-8">
            {bars.map((h, i) => (
              <div
                key={i}
                style={{
                  height: `${h * 100}%`,
                  width: 3,
                  borderRadius: 2,
                  background: recording
                    ? 'linear-gradient(180deg, #6366f1, #a78bfa)'
                    : 'rgba(255,255,255,0.1)',
                  transition: recording ? 'height 0.08s ease' : 'height 0.4s ease',
                }}
              />
            ))}
          </div>

          {/* Timer */}
          {recording && (
            <div className="mb-6">
              <div className="flex justify-between text-xs text-gray-400 mb-1">
                <span>{elapsed}s</span>
                <span>{MAX_DURATION}s max</span>
              </div>
              <div className="h-1 rounded-full bg-white/10 overflow-hidden">
                <div
                  className="h-full rounded-full transition-all duration-1000"
                  style={{
                    width: `${progress}%`,
                    background: progress > 80
                      ? 'linear-gradient(90deg, #6366f1, #ef4444)'
                      : 'linear-gradient(90deg, #6366f1, #a78bfa)',
                  }}
                />
              </div>
            </div>
          )}

          {/* Buttons */}
          <div className="flex justify-center gap-4">
            {!recording && !analyzing && (
              <button
                onClick={startRecording}
                className="btn-primary flex items-center gap-3 px-8 py-4 text-lg relative"
                id="start-recording-btn"
              >
                <span className={recording ? 'mic-pulse relative' : ''}>🎙️</span>
                Start Recording
              </button>
            )}
            {recording && (
              <button
                onClick={stopRecording}
                className="btn-secondary flex items-center gap-3 px-8 py-4 text-lg"
                id="stop-recording-btn"
                style={{ background: 'rgba(239,68,68,0.15)', borderColor: 'rgba(239,68,68,0.3)' }}
              >
                ⏹️ Stop & Analyze
              </button>
            )}
            {analyzing && (
              <div className="flex items-center gap-3 text-gray-300 text-lg">
                <span className="w-6 h-6 border-2 border-indigo-400 border-t-transparent rounded-full animate-spin" />
                Analyzing speech…
              </div>
            )}
          </div>
          <p className="text-center text-gray-600 text-xs mt-4">
            Speak naturally for at least 5 seconds. Max 30 seconds.
          </p>
        </div>

        {/* Result */}
        {result && (
          <div className="space-y-4 fade-up">
            {/* Verdict */}
            <div className="glass p-6 flex items-center gap-5">
              <div
                className="w-16 h-16 rounded-2xl flex items-center justify-center text-3xl flex-shrink-0"
                style={{ background: `${CLASS_COLORS[result.predicted_class] || '#6366f1'}22`, border: `2px solid ${CLASS_COLORS[result.predicted_class] || '#6366f1'}` }}
              >
                {result.predicted_class === 'Fluent Speech' ? '✅' : '⚠️'}
              </div>
              <div className="flex-1">
                <p className="text-gray-400 text-sm">Overall Result</p>
                <h2 className="text-2xl font-bold text-white">{result.predicted_class}</h2>
                <p className="text-gray-400 text-sm mt-1">
                  {fluentPct}% fluent · {result.num_segments} segments · {Math.round(result.duration || 0)}s recorded
                </p>
              </div>
              {/* Fluency ring */}
              <div className="flex flex-col items-center">
                <svg width="72" height="72" viewBox="0 0 72 72">
                  <circle cx="36" cy="36" r="30" fill="none" stroke="rgba(255,255,255,0.08)" strokeWidth="8" />
                  <circle cx="36" cy="36" r="30" fill="none"
                    stroke={CLASS_COLORS['Fluent Speech']}
                    strokeWidth="8"
                    strokeDasharray={`${(fluentPct / 100) * 188.5} 188.5`}
                    strokeLinecap="round"
                    transform="rotate(-90 36 36)" />
                </svg>
                <span className="text-white font-bold text-sm -mt-1">{fluentPct}%</span>
                <span className="text-gray-500 text-xs">Fluent</span>
              </div>
            </div>

            {/* Bar chart */}
            {barData.length > 0 && (
              <div className="glass p-6">
                <h3 className="text-lg font-semibold text-white mb-4">Segment Breakdown</h3>
                <ResponsiveContainer width="100%" height={200}>
                  <BarChart data={barData} layout="vertical" margin={{ left: 20 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" horizontal={false} />
                    <XAxis type="number" stroke="#6b7280" tick={{ fill: '#9ca3af' }} />
                    <YAxis type="category" dataKey="name" stroke="#6b7280" tick={{ fill: '#9ca3af' }} width={110} />
                    <Tooltip
                      contentStyle={{ background: '#1e1b4b', border: '1px solid #4f46e5', borderRadius: 8 }}
                      formatter={(v: any) => [`${v} segments`, 'Count']}
                    />
                    <Bar dataKey="value" radius={[0, 6, 6, 0]}>
                      {barData.map((entry, i) => (
                        <Cell key={i} fill={CLASS_COLORS[entry.name] || '#6366f1'} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}

            {/* Record again */}
            <div className="flex justify-center">
              <button
                onClick={() => { setResult(null); setElapsed(0); }}
                className="btn-secondary flex items-center gap-2"
              >
                🔄 Record Again
              </button>
            </div>
          </div>
        )}
      </div>
    </AppLayout>
  );
}
