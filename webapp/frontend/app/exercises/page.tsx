'use client';
import { useState, useEffect, useRef, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { useAuthStore } from '@/lib/authStore';
import { sentencesAPI } from '@/lib/api';
import AppLayout from '@/components/AppLayout';
import toast from 'react-hot-toast';

const EXERCISE_DURATION = 30; // seconds per sentence

const BREATHING_STEPS = [
  { label: 'Breathe In', duration: 4, color: '#6366f1', scale: 1.25 },
  { label: 'Hold', duration: 4, color: '#a78bfa', scale: 1.25 },
  { label: 'Breathe Out', duration: 6, color: '#10b981', scale: 1 },
];

const TIPS = [
  '💡 Speak slowly and deliberately — there\'s no rush.',
  '💡 Feel the vibration in your chest as you speak each word.',
  '💡 If you get stuck, pause, breathe, then continue.',
  '💡 Use a gentle onset — start words softly, not with force.',
  '💡 Stretch vowels slightly: "Soooo… I went to the store."',
];

export default function ExercisesPage() {
  const router = useRouter();
  const { token } = useAuthStore();

  const [sentences, setSentences] = useState<string[]>([]);
  const [current, setCurrent] = useState(0);
  const [done, setDone] = useState<boolean[]>([]);
  const [elapsed, setElapsed] = useState(0);
  const [timerRunning, setTimerRunning] = useState(false);
  const [breathStep, setBreathStep] = useState(0);
  const [breathElapsed, setBreathElapsed] = useState(0);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState<'sentences' | 'breathing'>('sentences');

  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const breathRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (!token) { router.replace('/login'); return; }
    sentencesAPI.getSentences(5)
      .then((r) => {
        setSentences(r.data.sentences || []);
        setDone(new Array(r.data.sentences?.length || 5).fill(false));
      })
      .catch(() => {
        const fallback = [
          'She sells seashells by the seashore.',
          'How much wood would a woodchuck chuck?',
          'Peter Piper picked a peck of pickled peppers.',
          'The big black bear sat on the big black rug.',
          'Can you can a can as a canner can can?',
        ];
        setSentences(fallback);
        setDone(new Array(fallback.length).fill(false));
      })
      .finally(() => setLoading(false));
  }, [token, router]);

  // Timer
  const startTimer = () => {
    if (timerRunning) return;
    setElapsed(0);
    setTimerRunning(true);
    timerRef.current = setInterval(() => {
      setElapsed((p) => {
        if (p + 1 >= EXERCISE_DURATION) {
          clearInterval(timerRef.current!);
          setTimerRunning(false);
          return EXERCISE_DURATION;
        }
        return p + 1;
      });
    }, 1000);
  };

  const resetTimer = () => {
    if (timerRef.current) clearInterval(timerRef.current);
    setTimerRunning(false);
    setElapsed(0);
  };

  const markDone = () => {
    const updated = [...done];
    updated[current] = true;
    setDone(updated);
    resetTimer();
    if (current < sentences.length - 1) {
      setCurrent(current + 1);
      toast.success('Great job! Moving to next sentence.');
    } else {
      toast.success('🎉 All sentences complete! Well done!');
    }
  };

  // Breathing exercise
  useEffect(() => {
    if (tab !== 'breathing') {
      if (breathRef.current) clearInterval(breathRef.current);
      setBreathElapsed(0); setBreathStep(0);
      return;
    }
    breathRef.current = setInterval(() => {
      setBreathElapsed((prev) => {
        const step = BREATHING_STEPS[breathStep];
        if (prev + 1 >= step.duration) {
          setBreathStep((s) => (s + 1) % BREATHING_STEPS.length);
          return 0;
        }
        return prev + 1;
      });
    }, 1000);
    return () => { if (breathRef.current) clearInterval(breathRef.current); };
  }, [tab, breathStep]);

  useEffect(() => () => {
    if (timerRef.current) clearInterval(timerRef.current);
    if (breathRef.current) clearInterval(breathRef.current);
  }, []);

  const completedCount = done.filter(Boolean).length;
  const timerProgress = (elapsed / EXERCISE_DURATION) * 100;
  const currentStep = BREATHING_STEPS[breathStep];
  const breathProgress = (breathElapsed / currentStep.duration) * 100;

  if (loading) return (
    <AppLayout>
      <div className="flex items-center justify-center h-64">
        <div className="w-8 h-8 rounded-full border-4 border-indigo-500 border-t-transparent animate-spin" />
      </div>
    </AppLayout>
  );

  return (
    <AppLayout>
      <div className="fade-up space-y-8 max-w-3xl mx-auto">
        {/* Header */}
        <div>
          <h1 className="text-3xl font-bold text-white">Speech Training</h1>
          <p className="text-gray-400 mt-1">Practice sentences and breathing exercises to build fluency</p>
        </div>

        {/* Progress overview */}
        <div className="glass p-5 flex items-center gap-6">
          <div className="flex-1">
            <div className="flex justify-between text-sm text-gray-400 mb-2">
              <span>Session Progress</span>
              <span>{completedCount} / {sentences.length} done</span>
            </div>
            <div className="h-2 rounded-full bg-white/10 overflow-hidden">
              <div
                className="h-full rounded-full transition-all duration-500"
                style={{
                  width: `${(completedCount / Math.max(sentences.length, 1)) * 100}%`,
                  background: 'linear-gradient(90deg, #6366f1, #10b981)',
                }}
              />
            </div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-white">{completedCount}</div>
            <div className="text-xs text-gray-500">Completed</div>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex gap-2 p-1 rounded-xl" style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.06)' }}>
          {(['sentences', 'breathing'] as const).map((t) => (
            <button
              key={t}
              onClick={() => { setTab(t); resetTimer(); }}
              className="flex-1 py-2 rounded-lg text-sm font-medium transition-all duration-200"
              style={tab === t
                ? { background: 'rgba(99,102,241,0.25)', color: '#a78bfa', border: '1px solid rgba(99,102,241,0.3)' }
                : { color: '#6b7280' }}
            >
              {t === 'sentences' ? '📝 Practice Sentences' : '🌬️ Breathing Exercise'}
            </button>
          ))}
        </div>

        {/* Sentences Tab */}
        {tab === 'sentences' && sentences.length > 0 && (
          <div className="space-y-4">
            {/* Sentence list */}
            <div className="space-y-2">
              {sentences.map((s, i) => (
                <button
                  key={i}
                  onClick={() => { setCurrent(i); resetTimer(); }}
                  className="w-full text-left p-4 rounded-xl transition-all duration-200"
                  style={{
                    background: i === current
                      ? 'rgba(99,102,241,0.15)'
                      : done[i] ? 'rgba(16,185,129,0.08)' : 'rgba(255,255,255,0.03)',
                    border: i === current
                      ? '1px solid rgba(99,102,241,0.4)'
                      : done[i] ? '1px solid rgba(16,185,129,0.2)' : '1px solid rgba(255,255,255,0.06)',
                  }}
                >
                  <div className="flex items-start gap-3">
                    <span className="text-lg flex-shrink-0 mt-0.5">{done[i] ? '✅' : i === current ? '▶️' : '○'}</span>
                    <span className={`text-sm ${i === current ? 'text-white font-medium' : done[i] ? 'text-gray-500 line-through' : 'text-gray-300'}`}>
                      {s}
                    </span>
                  </div>
                </button>
              ))}
            </div>

            {/* Active sentence practice */}
            {!done[current] && (
              <div className="glass p-6 space-y-5">
                <h3 className="text-white font-semibold">Current Sentence</h3>
                <p className="text-2xl text-indigo-300 font-medium leading-relaxed">
                  &ldquo;{sentences[current]}&rdquo;
                </p>

                {/* Timer */}
                <div>
                  <div className="flex justify-between text-xs text-gray-400 mb-1">
                    <span>{timerRunning ? `${elapsed}s` : 'Ready'}</span>
                    <span>{EXERCISE_DURATION}s</span>
                  </div>
                  <div className="h-1.5 rounded-full bg-white/10 overflow-hidden">
                    <div
                      className="h-full rounded-full transition-all duration-1000"
                      style={{
                        width: `${timerProgress}%`,
                        background: timerProgress > 80
                          ? 'linear-gradient(90deg, #6366f1, #f59e0b)'
                          : 'linear-gradient(90deg, #6366f1, #a78bfa)',
                      }}
                    />
                  </div>
                </div>

                <div className="flex gap-3">
                  {!timerRunning ? (
                    <button onClick={startTimer} className="btn-primary flex-1 flex items-center justify-center gap-2" id="start-timer-btn">
                      ▶️ Start Speaking
                    </button>
                  ) : (
                    <button onClick={resetTimer} className="btn-secondary flex-1">⏸ Pause</button>
                  )}
                  <button
                    onClick={markDone}
                    className="btn-secondary px-5"
                    style={{ color: '#10b981', borderColor: 'rgba(16,185,129,0.3)' }}
                  >
                    ✓ Done
                  </button>
                </div>

                {/* Random tip */}
                <p className="text-gray-500 text-xs">{TIPS[current % TIPS.length]}</p>
              </div>
            )}

            {done[current] && current < sentences.length - 1 && (
              <button onClick={() => setCurrent(current + 1)} className="btn-primary w-full">
                Next Sentence →
              </button>
            )}

            {completedCount === sentences.length && (
              <div className="glass p-8 text-center">
                <div className="text-5xl mb-4">🎉</div>
                <h3 className="text-2xl font-bold text-white mb-2">Session Complete!</h3>
                <p className="text-gray-400">You completed all {sentences.length} sentences. Great work on your speech training!</p>
                <button
                  className="btn-primary mt-6"
                  onClick={() => window.location.reload()}
                >
                  Start Another Session
                </button>
              </div>
            )}
          </div>
        )}

        {/* Breathing Tab */}
        {tab === 'breathing' && (
          <div className="glass p-8 flex flex-col items-center gap-8">
            <h3 className="text-white font-semibold text-lg">4-4-6 Diaphragmatic Breathing</h3>
            <p className="text-gray-400 text-sm text-center max-w-sm">
              This pattern activates your parasympathetic nervous system, reducing speaking anxiety and stuttering.
            </p>

            {/* Animated circle */}
            <div className="relative flex items-center justify-center" style={{ width: 200, height: 200 }}>
              {/* Glow ring */}
              <div
                className="absolute inset-0 rounded-full transition-all duration-1000"
                style={{
                  boxShadow: `0 0 60px ${currentStep.color}44, 0 0 120px ${currentStep.color}22`,
                  opacity: 0.8,
                }}
              />
              {/* SVG progress */}
              <svg width="200" height="200" viewBox="0 0 200 200" className="absolute inset-0">
                <circle cx="100" cy="100" r="88" fill="none" stroke="rgba(255,255,255,0.05)" strokeWidth="12" />
                <circle
                  cx="100" cy="100" r="88" fill="none"
                  stroke={currentStep.color}
                  strokeWidth="12"
                  strokeDasharray={`${(breathProgress / 100) * 553} 553`}
                  strokeLinecap="round"
                  transform="rotate(-90 100 100)"
                  style={{ transition: 'stroke-dasharray 1s linear, stroke 0.5s ease' }}
                />
              </svg>
              {/* Inner circle that scales */}
              <div
                className="rounded-full flex items-center justify-center transition-all duration-1000"
                style={{
                  width: 130,
                  height: 130,
                  background: `radial-gradient(circle, ${currentStep.color}33, transparent)`,
                  border: `2px solid ${currentStep.color}66`,
                  transform: `scale(${breathProgress > 50 ? currentStep.scale : 1 + (currentStep.scale - 1) * breathProgress / 50})`,
                }}
              >
                <div className="text-center">
                  <div className="text-white font-bold text-lg">{currentStep.label}</div>
                  <div className="text-gray-300 text-2xl font-mono mt-1">
                    {currentStep.duration - breathElapsed}s
                  </div>
                </div>
              </div>
            </div>

            {/* Steps legend */}
            <div className="flex gap-6">
              {BREATHING_STEPS.map((s, i) => (
                <div key={i} className="text-center">
                  <div className="w-3 h-3 rounded-full mx-auto mb-1" style={{ background: s.color, opacity: breathStep === i ? 1 : 0.3 }} />
                  <div className="text-xs text-gray-400">{s.label}</div>
                  <div className="text-xs" style={{ color: s.color }}>{s.duration}s</div>
                </div>
              ))}
            </div>

            <p className="text-gray-500 text-xs text-center">
              Breathe with the circle. This automatically cycles — just follow the cues.
            </p>
          </div>
        )}
      </div>
    </AppLayout>
  );
}
