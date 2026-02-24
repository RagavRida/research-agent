import React, { useState, useEffect, useRef } from 'react';
import {
  Search, Layout, Activity, CheckCircle2, Circle, Clock, Database, FileText,
  Zap, ShieldCheck, AlertCircle, ChevronDown, ChevronUp, Terminal, Cpu,
  Globe, BookOpen, Newspaper, Layers, Send, RotateCcw, Copy, ExternalLink,
  Grid
} from 'lucide-react';

const STEP_TYPES = {
  plan: { label: 'PLAN', color: '#7c3aed', icon: '◈' },
  search_initial: { label: 'SEARCH', color: '#10b981', icon: '⌕' },
  search_retry: { label: 'SEARCH ↺ RETRY', color: '#f59e0b', icon: '↺⌕' },
  evaluate_retry: { label: 'EVALUATE → RETRY', color: '#f43f5e', icon: '◎↺' },
  evaluate_pass: { label: 'EVALUATE → PASS ✓', color: '#10b981', icon: '◎✓' },
  synthesize: { label: 'SYNTHESIZE', color: '#9333ea', icon: '⬡' },
  final: { label: 'FINAL', color: '#f43f5e', icon: '✦' },
  // Legacy support
  PLAN: { label: 'PLAN', color: '#7c3aed', icon: '◈' },
  SEARCH: { label: 'SEARCH', color: '#10b981', icon: '⌕' },
  EVALUATE: { label: 'EVALUATE', color: '#f59e0b', icon: '◎' },
  SYNTHESIZE: { label: 'SYNTHESIZE', color: '#9333ea', icon: '⬡' },
  FINAL: { label: 'FINAL', color: '#f43f5e', icon: '✦' },
};

const TOOLS = [
  { id: 'tavily', name: 'Tavily Search', icon: Globe },
  { id: 'scholar', name: 'Scholar API', icon: BookOpen },
  { id: 'news', name: 'News API', icon: Newspaper },
  { id: 'synthesizer', name: 'Synthesizer', icon: Layers },
];

const TypewriterText = ({ text, speed = 30, onComplete = undefined }) => {
  const [displayedText, setDisplayedText] = useState('');
  const [isComplete, setIsComplete] = useState(false);
  const index = useRef(0);

  useEffect(() => {
    setDisplayedText('');
    index.current = 0;
    setIsComplete(false);
  }, [text]);

  useEffect(() => {
    if (index.current < text.length) {
      const timeout = setTimeout(() => {
        setDisplayedText((prev) => prev + text.charAt(index.current));
        index.current += 1;
      }, speed);
      return () => clearTimeout(timeout);
    } else if (!isComplete) {
      setIsComplete(true);
      if (onComplete) onComplete();
    }
  }, [displayedText, text, speed, onComplete, isComplete]);

  return (
    <span className={!isComplete ? 'cursor-blink' : ''}>
      {displayedText}
    </span>
  );
};

const ConfidenceBar = ({ value, label = "CONFIDENCE LEVEL" }) => {
  const getColor = (v) => {
    if (v < 40) return 'bg-rose-500';
    if (v < 70) return 'bg-amber-500';
    if (v < 85) return 'bg-blue-500';
    return 'bg-emerald-500';
  };

  return (
    <div className="mt-2">
      <div className="flex justify-between text-[10px] uppercase tracking-wider mb-1 text-slate-400 font-mono">
        <span>{label}</span>
        <span>{value}%</span>
      </div>
      <div className="w-full h-2 bg-slate-800 rounded-full overflow-hidden border border-slate-700">
        <div
          className={`h-full transition-all duration-800 ease-out ${getColor(value)}`}
          style={{ width: `${value}%` }}
        />
      </div>
      {value < 85 && (
        <div className="text-[9px] text-rose-500 font-bold mt-1 tracking-widest uppercase">
          ⚠ BELOW THRESHOLD — RETRY TRIGGERED
        </div>
      )}
    </div>
  );
};

const ConfidenceDial = ({ value, history }) => {
  const radius = 40;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (value / 100) * circumference;

  const getColor = (v) => {
    if (v === 0) return '#334155';
    if (v < 40) return '#f43f5e';
    if (v < 70) return '#f59e0b';
    if (v < 85) return '#3b82f6';
    return '#10b981';
  };

  const getTrend = () => {
    if (history.length < 2) return null;
    const current = history[history.length - 1];
    const prev = history[history.length - 2];
    if (current > prev) return <span className="text-emerald-500 ml-1">↑</span>;
    if (current < prev) return <span className="text-rose-500 ml-1">↓</span>;
    return <span className="text-slate-500 ml-1">—</span>;
  };

  return (
    <div className="relative flex flex-col items-center justify-center w-full">
      <div className="relative flex items-center justify-center w-40 h-40">
        <svg className="w-full h-full transform -rotate-90">
          <circle
            cx="80"
            cy="80"
            r={radius}
            stroke="#1e293b"
            strokeWidth="8"
            fill="transparent"
          />
          {/* Tick marks */}
          {Array.from({ length: 10 }).map((_, i) => (
            <line
              key={i}
              x1="80" y1="36" x2="80" y2="40"
              stroke="#cbd5e1"
              strokeWidth="1"
              opacity="0.2"
              transform={`rotate(${i * 36} 80 80)`}
            />
          ))}
          <circle
            cx="80"
            cy="80"
            r={radius}
            stroke={getColor(value)}
            strokeWidth="8"
            fill="transparent"
            strokeDasharray={circumference}
            style={{ strokeDashoffset: offset, transition: 'stroke-dashoffset 1s ease-out, stroke 1s' }}
            strokeLinecap="round"
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-4xl font-bold font-mono text-white flex items-center">
            {value}%
            <span className="text-lg opacity-80">{getTrend()}</span>
          </span>
        </div>
      </div>

      {/* History Graph */}
      <div className="mt-4 w-full px-8">
        <div className="text-[8px] text-slate-500 font-mono tracking-widest mb-1 text-center">PER ITERATION HISTORY</div>
        <div className="flex gap-1 h-6 items-end justify-center">
          {Array.from({ length: 5 }).map((_, i) => {
            const val = history[i];
            const height = val ? `${val}%` : '4px';
            const color = val ? getColor(val) : '#1e293b';
            return (
              <div
                key={i}
                className="w-4 rounded-t-sm transition-all duration-500"
                style={{ height, backgroundColor: color }}
              />
            );
          })}
        </div>
      </div>
    </div>
  );
};

const LogCard = (props) => {
  const { step, isLatest, index } = props;
  const [isExpanded, setIsExpanded] = useState(true);
  const typeInfo = STEP_TYPES[step.type] || STEP_TYPES['PLAN'];
  const isRetryEval = step.type === 'evaluate_retry';
  const isRetrySearch = step.type === 'search_retry';
  const isPass = step.type === 'evaluate_pass';
  const isRetryLegacy = step.type === 'EVALUATE' && step.data && step.data.decision === 'retry';
  const isAnyRetry = isRetryEval || isRetryLegacy;

  const borderColor = isRetryEval ? '#f43f5e'
    : isRetrySearch ? '#f59e0b'
      : isPass ? '#10b981'
        : typeInfo.color;

  const bgClass = isRetryEval ? 'bg-[#1a0808]/80'
    : isRetrySearch ? 'bg-[#1a1408]/60'
      : isPass ? 'bg-[#081a10]/60'
        : 'bg-slate-900/50';

  return (
    <div
      data-log-index={index}
      className={`mb-4 border-l-[5px] rounded-r-lg overflow-hidden animate-slide-up transition-all
        ${bgClass}
        ${isLatest ? 'ring-1 ring-cyan-500/30 shadow-[0_0_15px_rgba(0,212,255,0.1)]' : ''}
        ${isRetryEval ? 'ring-1 ring-rose-500/20 shadow-[0_0_20px_rgba(244,63,94,0.15)]' : ''}
      `}
      style={{ borderLeftColor: borderColor, borderLeftWidth: isRetryEval ? '6px' : '5px' }}
    >
      <div className="p-4">
        <div className="flex justify-between items-start mb-3">
          <div className="flex items-center gap-2">
            {/* Badge — split pill for evaluate_retry */}
            {isRetryEval ? (
              <div className="flex">
                <span className="px-2 py-0.5 text-[10px] font-bold rounded-l text-white tracking-widest bg-amber-500">EVALUATE</span>
                <span className="px-2 py-0.5 text-[10px] font-bold rounded-r text-white tracking-widest bg-rose-500 flex items-center gap-1">
                  RETRY <RotateCcw size={10} />
                </span>
              </div>
            ) : (
              <span
                className="px-2 py-0.5 text-[10px] font-bold rounded text-white tracking-widest"
                style={{ backgroundColor: borderColor }}
              >
                {typeInfo.label}
              </span>
            )}
            <span className="text-xl opacity-80">{typeInfo.icon}</span>
            <span className="text-[10px] text-slate-500 font-mono ml-2">[{step.stepNum}/8]</span>
          </div>
          <div className="flex flex-col items-end">
            <span className="text-[10px] font-mono text-slate-400">{step.timestamp}</span>
            {step.durationMs && <span className="text-[8px] font-mono text-slate-600">{Math.round(step.durationMs)}ms</span>}
          </div>
        </div>

        {isAnyRetry && (
          <div className="mb-3 p-2 bg-rose-500/10 border border-rose-500/30 rounded text-rose-400 text-xs font-mono font-bold flex items-center gap-2 animate-shimmer">
            <RotateCcw size={14} />
            SELF-CORRECTION TRIGGERED — Reformulating search strategy
          </div>
        )}

        <div className="space-y-3">
          <div className="border border-slate-800/50 p-2 rounded bg-black/20">
            <span className="text-[9px] font-mono text-slate-500 uppercase tracking-widest block mb-1">⟨ CHAIN OF THOUGHT ⟩</span>
            <p className="text-[13px] italic text-slate-400 leading-relaxed font-serif">
              <TypewriterText text={step.thinking} />
            </p>
          </div>

          <div className="flex gap-2 items-center bg-cyan-950/20 p-2 border-l-2 border-cyan-500 rounded-r">
            <span className="text-cyan-500">▸</span>
            <span className="text-[10px] font-mono text-cyan-500/60 uppercase tracking-widest">ACTION:</span>
            <p className="text-sm font-medium text-cyan-400 tracking-wide">
              {step.action}
            </p>
          </div>

          {/* ── Confidence bar for evaluate cards ── */}
          {(isRetryEval || isPass) && step.data?.confidence !== undefined && (
            <ConfidenceBar value={step.data.confidence} />
          )}

          {/* ── Gaps section for evaluate_retry ── */}
          {isRetryEval && step.data?.gaps_identified && step.data.gaps_identified.length > 0 && (
            <div className="bg-rose-950/20 p-2 rounded border border-rose-900/30">
              <span className="text-rose-400 block mb-1 font-bold text-[9px] uppercase tracking-widest">▾ GAPS IDENTIFIED</span>
              <ul className="list-none space-y-1">
                {step.data.gaps_identified.map((gap, i) => (
                  <li key={i} className="text-[10px] text-rose-300/80 flex items-start gap-2">
                    <span className="text-rose-500 mt-0.5">•</span>
                    <span className="animate-slide-up" style={{ animationDelay: `${i * 150}ms` }}>{gap}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* ── Reformulation strategy for evaluate_retry ── */}
          {isRetryEval && step.data?.reformulation_hint && (
            <div className="bg-amber-950/20 p-2 rounded border border-amber-900/30">
              <span className="text-amber-400 block mb-1 font-bold text-[9px] uppercase tracking-widest">▾ REFORMULATION STRATEGY</span>
              <div className="flex items-center gap-2 mb-1">
                <span className="text-[9px] px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-400 border border-amber-500/30 font-bold uppercase">
                  {step.data.reformulation_strategy || 'NARROWER'}
                </span>
              </div>
              <p className="text-[11px] text-amber-300/80 italic">{step.data.reformulation_hint}</p>
            </div>
          )}

          {/* ── Query diff for search_retry ── */}
          {isRetrySearch && step.data?.reformulation_hint_used && (
            <div className="bg-amber-950/10 p-2 rounded border border-amber-900/20">
              <span className="text-amber-400 block mb-1 font-bold text-[9px] uppercase tracking-widest">QUERY REFORMULATION</span>
              <div className="space-y-1">
                <div className="flex items-center gap-2 text-[10px]">
                  <span className="text-rose-400 line-through opacity-70">{step.data.reformulation_hint_used?.slice(0, 60)}</span>
                </div>
                <div className="flex items-center gap-2 text-[10px]">
                  <span className="text-amber-400 font-bold">→</span>
                  <span className="text-amber-300 font-medium">"{step.data.query}"</span>
                </div>
                {step.data.reformulation_strategy && (
                  <span className="text-[8px] text-amber-500/60">+{step.data.reformulation_strategy}</span>
                )}
              </div>
            </div>
          )}

          {step.data && (
            <div className="mt-4 pt-2">
              <button
                onClick={() => setIsExpanded(!isExpanded)}
                className="flex items-center gap-1 text-[10px] font-mono text-slate-500 hover:text-slate-300 transition-colors w-full p-1 hover:bg-slate-800/50 rounded"
              >
                {isExpanded ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
                ▾ DATA PAYLOAD
              </button>

              {isExpanded && (
                <div className="mt-2 bg-[#050505] rounded p-3 font-mono text-[11px] text-slate-300 border border-slate-800/50 shadow-inner">
                  {(step.type === 'SEARCH' || step.type === 'search_initial' || step.type === 'search_retry') && (
                    <div className="space-y-1">
                      <div className="flex justify-between"><span className="text-emerald-500">query:</span> <span>"{step.data.query}"</span></div>
                      <div className="flex justify-between"><span className="text-emerald-500">tool:</span> <span>{step.data.tool}</span></div>
                      <div className="flex justify-between"><span className="text-emerald-500">results:</span> <span>{step.data.results_count || step.data.resultsCount || 0} items found</span></div>
                      {step.data.is_retry && (
                        <>
                          <div className="flex justify-between"><span className="text-amber-500">is_retry:</span> <span className="text-amber-400">true</span></div>
                          <div className="flex justify-between"><span className="text-amber-500">iteration:</span> <span>{step.data.iteration}</span></div>
                          <div className="flex justify-between"><span className="text-amber-500">previous_confidence:</span> <span>{step.data.previous_confidence}%</span></div>
                        </>
                      )}
                    </div>
                  )}
                  {(step.type === 'EVALUATE' || step.type === 'evaluate_retry' || step.type === 'evaluate_pass') && (
                    <div className="space-y-1">
                      <div className="flex justify-between"><span className={isRetryEval ? 'text-rose-500' : 'text-emerald-500'}>confidence:</span> <span>{step.data.confidence}%</span></div>
                      <div className="flex justify-between"><span className="text-amber-500">threshold_met:</span> <span>{String(step.data.threshold_met)}</span></div>
                      <div className="flex justify-between"><span className="text-amber-500">sources_found:</span> <span>{step.data.sources_found}</span></div>
                      <div className="flex justify-between"><span className="text-amber-500">decision:</span> <span>{step.data.decision}</span></div>
                      {step.data.confidence_delta !== undefined && (
                        <div className="flex justify-between">
                          <span className="text-amber-500">confidence_delta:</span>
                          <span className={step.data.confidence_delta > 0 ? 'text-emerald-400' : 'text-rose-400'}>
                            {step.data.confidence_delta > 0 ? '+' : ''}{step.data.confidence_delta}%
                          </span>
                        </div>
                      )}
                    </div>
                  )}
                  {step.type === 'SYNTHESIZE' || step.type === 'synthesize' ? (
                    <div className="space-y-2">
                      <div className="flex justify-between"><span className="text-purple-500">sources_used:</span> <span>{step.data.sources_used || step.data.sourcesCount}</span></div>
                      <div className="flex justify-between"><span className="text-purple-500">final_confidence:</span> <span>{step.data.final_confidence}%</span></div>
                      {step.data.key_findings && (
                        <div className="mt-2 text-[10px] text-slate-400">{JSON.stringify(step.data.key_findings, null, 2)}</div>
                      )}
                    </div>
                  ) : null}
                  {(step.type === 'FINAL' || step.type === 'final') && (
                    <div className="space-y-2">
                      <div className="text-rose-400 font-bold mb-1">EXECUTIVE SUMMARY READY</div>
                      <div className="flex justify-between mt-2 pt-2 border-t border-slate-800">
                        <span className="text-rose-500">final_confidence:</span>
                        <span>{step.data.confidence || step.data.final_confidence}%</span>
                      </div>
                    </div>
                  )}
                  {step.type === 'plan' || step.type === 'PLAN' ? (
                    <div className="space-y-1">
                      <span className="text-violet-500 block mb-1 tracking-widest uppercase">Strategy:</span>
                      {(step.data.tasks || step.data.subtasks || []).map((t, i) => (
                        <div key={i} className="flex justify-between text-slate-400 py-1 border-b border-slate-800/50 last:border-0">
                          <span className="truncate pr-2">{i + 1}. {t.label || t.task}</span>
                          <span className={`text-[9px] px-1 rounded font-bold ${t.priority === 'HIGH' ? 'bg-rose-500/20 text-rose-400' :
                            t.priority === 'MED' ? 'bg-amber-500/20 text-amber-400' :
                              'bg-slate-700/50 text-slate-400'
                            }`}>{t.priority}</span>
                        </div>
                      ))}
                    </div>
                  ) : null}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default function App() {
  const [query, setQuery] = useState('');
  const [isRunning, setIsRunning] = useState(false);
  const [logs, setLogs] = useState([]);
  const [plan, setPlan] = useState([]);
  const [stats, setStats] = useState({ steps: 0, searches: 0, iterations: 0, startTime: null, tokens: 0 });
  const [elapsedTime, setElapsedTime] = useState('00:00');
  const [confidence, setConfidence] = useState(0);
  const [confidenceHistory, setConfidenceHistory] = useState([]);
  const [sources, setSources] = useState([]);
  const [contradictions, setContradictions] = useState([]);
  const [toolUsage, setToolUsage] = useState(
    TOOLS.map(t => ({ ...t, count: 0, lastUsed: '--:--', active: false, history: [0, 0, 0, 0, 0] }))
  );
  const [showFinal, setShowFinal] = useState(false);
  const [finalAnswer, setFinalAnswer] = useState(null);
  const [autoScroll, setAutoScroll] = useState(true);
  const [toasts, setToasts] = useState([]);
  const [progress, setProgress] = useState(0);
  // ── Self-correction state ──
  const [retryEvents, setRetryEvents] = useState([]);
  const [gaps, setGaps] = useState([]);
  const [activeRetryBanner, setActiveRetryBanner] = useState(null);
  const [iterationData, setIterationData] = useState([]);
  const [replayTarget, setReplayTarget] = useState(null);
  const [confidenceDelta, setConfidenceDelta] = useState(null);
  const [backendUrl] = useState('http://localhost:8000');
  // ── Model selector state ──
  const [availableModels, setAvailableModels] = useState({ providers: [], active_provider: 'groq', active_model: '' });
  const [selectedProvider, setSelectedProvider] = useState('groq');
  const [selectedModel, setSelectedModel] = useState('llama-3.3-70b-versatile');

  const logEndRef = useRef(null);
  const timerRef = useRef(null);
  const retryCardRef = useRef(null);

  // Global Keyboard Shortcuts
  useEffect(() => {
    const handleKeyDown = (e) => {
      // Don't trigger if input is focused
      if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') {
        if (e.code === 'Escape') {
          e.target.blur();
        }
        return;
      }

      if (e.code === 'Space' && !isRunning) {
        e.preventDefault();
        runSimulation();
      } else if (e.code === 'Escape' || e.code === 'KeyR') {
        resetState();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [isRunning]);

  // Fetch available models on mount
  useEffect(() => {
    fetch(`${backendUrl}/api/models`)
      .then(r => r.json())
      .then(data => {
        setAvailableModels(data);
        setSelectedProvider(data.active_provider || 'groq');
        setSelectedModel(data.active_model || 'llama-3.3-70b-versatile');
      })
      .catch(() => { });
  }, [backendUrl]);

  const handleModelSwitch = async (provider: string, model: string) => {
    setSelectedProvider(provider);
    setSelectedModel(model);
    try {
      await fetch(`${backendUrl}/api/models/switch`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ provider, model }),
      });
      showToast(`⚡ Switched to ${provider}/${model}`, 'cyan');
    } catch {
      showToast('Failed to switch model', 'rose');
    }
  };

  // Tooltip initial toast
  useEffect(() => {
    showToast("Keyboard ready: [SPACE] Deploy · [ESC] Reset", 'cyan');
  }, []);

  const showToast = (message, type = 'cyan') => {
    const id = Date.now();
    setToasts(prev => [...prev, { id, message, type }]);
    setTimeout(() => {
      setToasts(prev => prev.filter(t => t.id !== id));
    }, 3000);
  };

  // Auto-scroll logs
  useEffect(() => {
    if (autoScroll) {
      logEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [logs, autoScroll]);

  // Timer logic
  useEffect(() => {
    if (isRunning && stats.startTime) {
      timerRef.current = setInterval(() => {
        const diff = Math.floor((Date.now() - stats.startTime) / 1000);
        const mins = Math.floor(diff / 60).toString().padStart(2, '0');
        const secs = (diff % 60).toString().padStart(2, '0');
        setElapsedTime(`${mins}:${secs}`);
      }, 1000);
    } else {
      clearInterval(timerRef.current);
    }
    return () => clearInterval(timerRef.current);
  }, [isRunning, stats.startTime]);

  const resetState = () => {
    setIsRunning(false);
    setLogs([]);
    setPlan([]);
    setStats({ steps: 0, searches: 0, iterations: 0, startTime: null, tokens: 0 });
    setElapsedTime('00:00');
    setConfidence(0);
    setConfidenceHistory([]);
    setSources([]);
    setContradictions([]);
    setToolUsage(TOOLS.map(t => ({ ...t, count: 0, lastUsed: '--:--', active: false, history: [0, 0, 0, 0, 0] })));
    setShowFinal(false);
    setFinalAnswer(null);
    setProgress(0);
    setRetryEvents([]);
    setGaps([]);
    setActiveRetryBanner(null);
    setIterationData([]);
    setReplayTarget(null);
    setConfidenceDelta(null);
  };

  const activateTool = (toolId) => {
    setToolUsage(prev => prev.map(t => {
      if (t.id === toolId) {
        const newHistory = [...t.history.slice(1), 1];
        return {
          ...t,
          count: t.count + 1,
          lastUsed: new Date().toLocaleTimeString([], { hour12: false }),
          active: true,
          history: newHistory
        };
      }
      return { ...t, active: false, history: [...t.history.slice(1), 0] };
    }));

    const toolName = TOOLS.find(t => t.id === toolId)?.name || toolId;
    showToast(`⚡ ${toolName} activated`, 'cyan');

    setTimeout(() => {
      setToolUsage(prev => prev.map(t => ({ ...t, active: false })));
    }, 600);
  };

  const addLog = (step) => {
    setLogs(prev => [...prev, { ...step, timestamp: new Date().toLocaleTimeString([], { hour12: false }) }]);
    setStats(prev => ({ ...prev, steps: prev.steps + 1, tokens: prev.tokens + Math.floor(Math.random() * 400 + 100) }));
  };

  const runSimulation = async () => {
    if (!query.trim()) return;

    resetState();
    setIsRunning(true);
    setStats(prev => ({ ...prev, startTime: Date.now() }));
    setProgress(5);

    try {
      const response = await fetch(`${backendUrl}/api/research/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query }),
      });

      if (!response.ok) {
        throw new Error(`Backend returned ${response.status}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      let stepCount = 0;
      let searchCount = 0;
      let iterCount = 0;
      let totalTokens = 0;

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue;
          let event;
          try {
            event = JSON.parse(line.slice(6));
          } catch { continue; }

          switch (event.event_type) {

            case 'step': {
              const step = event.data;
              stepCount++;
              totalTokens += step.tokens_used || 0;

              // Map step to log entry
              const logEntry = {
                type: step.type,
                stepNum: step.step_id,
                durationMs: step.duration_ms,
                thinking: step.thinking,
                action: step.action,
                data: step.data || {},
                timestamp: new Date(step.timestamp).toLocaleTimeString([], { hour12: false }),
              };
              setLogs(prev => [...prev, logEntry]);

              // Update plan from plan steps
              if (step.type === 'plan' && step.data?.subtasks) {
                const tasks = step.data.subtasks.map(t => ({
                  id: t.id,
                  label: t.task,
                  priority: t.priority,
                  status: 'pending',
                  tool: t.tool,
                }));
                setPlan(tasks);
                setProgress(15);
              }

              // Handle search steps — activate tools, populate sources
              if (step.type === 'search_initial' || step.type === 'search_retry') {
                searchCount++;
                const toolId = step.data?.tool === 'scholar_search' ? 'scholar'
                  : step.data?.tool === 'news_search' ? 'news' : 'tavily';
                activateTool(toolId);
                iterCount = step.data?.iteration || iterCount;
                setProgress(prev => Math.min(prev + 15, 80));

                // Extract sources from search results and add to Sources panel
                if (step.data?.sources && Array.isArray(step.data.sources)) {
                  const newSources = step.data.sources
                    .filter(s => s.url && s.title)
                    .map((s, i) => ({
                      id: Date.now() + i,
                      domain: (() => { try { return new URL(s.url).hostname.replace('www.', ''); } catch { return s.url; } })(),
                      url: s.url,
                      title: s.title,
                      snippet: '',
                      reliability: s.score > 0.8 ? 'HIGH' : s.score > 0.5 ? 'MEDIUM' : 'LOW',
                      type: s.source_type === 'academic' ? 'Academic'
                        : s.source_type === 'news' ? 'News'
                          : s.source_type === 'official' ? 'Official' : 'Web',
                    }));
                  setSources(prev => {
                    const existingUrls = new Set(prev.map(s => s.url));
                    const unique = newSources.filter(s => !existingUrls.has(s.url));
                    return [...prev, ...unique];
                  });
                }

                // Build iteration timeline entry
                setIterationData(prev => [...prev, {
                  iteration: step.data?.iteration || prev.length + 1,
                  query: step.data?.query || '',
                  tool: step.data?.tool || 'web_search',
                  type: step.type,
                  confidence: null,
                  passed: null,
                  gaps: [],
                }]);
              }

              // Handle evaluate steps — update confidence inline
              if (step.type === 'evaluate_retry' || step.type === 'evaluate_pass') {
                const conf = step.data?.confidence || 0;
                const prevConf = step.data?.previous_confidence || 0;
                const delta = conf - prevConf;
                setConfidence(conf);
                setConfidenceHistory(prev => [...prev, conf]);
                setConfidenceDelta(delta);
                setTimeout(() => setConfidenceDelta(null), 3000);

                // Update iteration timeline with evaluation result
                setIterationData(prev => {
                  const updated = [...prev];
                  if (updated.length > 0) {
                    updated[updated.length - 1] = {
                      ...updated[updated.length - 1],
                      confidence: conf,
                      passed: step.type === 'evaluate_pass',
                      gaps: step.data?.gaps_identified || [],
                    };
                  }
                  return updated;
                });
              }

              // Handle synthesize step
              if (step.type === 'synthesize') {
                activateTool('synthesizer');
                setProgress(90);
                setPlan(prev => prev.map(t => ({ ...t, status: 'complete' })));

                // Populate sources from citations if available
                if (step.data?.citations) {
                  const realSources = step.data.citations.map((c, i) => ({
                    id: i + 1,
                    domain: (() => { try { return new URL(c.url).hostname.replace('www.', ''); } catch { return c.url; } })(),
                    url: c.url,
                    title: c.title,
                    snippet: '',
                    reliability: c.reliability || 'MEDIUM',
                    type: 'Web',
                  }));
                  setSources(prev => prev.length > 0 ? prev : realSources);
                }

                if (step.data?.answer) {
                  const finalData = {
                    summary: `Research complete`,
                    confidence: step.data.final_confidence || confidence,
                    caveats: step.data.caveats || [],
                    answer: step.data.answer,
                  };
                  setFinalAnswer(finalData);
                  setShowFinal(true);
                  setConfidence(step.data.final_confidence || confidence);
                }
              }

              setStats(prev => ({
                ...prev,
                steps: stepCount,
                searches: searchCount,
                iterations: iterCount,
                tokens: totalTokens,
              }));
              break;
            }

            case 'retry_triggered': {
              const retryData = event.data;
              const banner = {
                ...retryData,
                id: crypto.randomUUID(),
                timestamp: new Date().toISOString(),
              };
              setActiveRetryBanner(banner);
              setRetryEvents(prev => [...prev, retryData]);
              showToast(`↺ Self-correction triggered — confidence ${retryData.confidence}%`, 'rose');
              // Auto-dismiss after 8 seconds
              setTimeout(() => setActiveRetryBanner(null), 8000);
              break;
            }

            case 'confidence_update': {
              const { current, history, passed } = event.data;
              setConfidence(current);
              setConfidenceHistory(history);
              break;
            }

            case 'gaps_updated': {
              setGaps(event.data.gaps || []);
              break;
            }

            case 'complete': {
              const completeData = event.data;
              setProgress(100);
              setIsRunning(false);

              if (completeData.final_answer && !finalAnswer) {
                const finalData = {
                  summary: `Research complete — ${completeData.total_iterations || 0} iterations`,
                  confidence: completeData.confidence || confidence,
                  caveats: completeData.caveats || [],
                  answer: completeData.final_answer,
                };
                setFinalAnswer(finalData);
                setShowFinal(true);
                setConfidence(completeData.confidence || confidence);
              }

              if (completeData.citations) {
                setSources(prev => {
                  if (prev.length > 0) return prev;
                  return completeData.citations.map((c, i) => ({
                    id: i + 1,
                    domain: (() => { try { return new URL(c.url).hostname.replace('www.', ''); } catch { return c.url; } })(),
                    url: c.url,
                    title: c.title,
                    snippet: '',
                    reliability: c.reliability || 'MEDIUM',
                    type: 'Web',
                  }));
                });
              }

              if (completeData.contradictions_found) {
                setContradictions(completeData.contradictions_found.map(c => ({
                  sourceA: 'Source A', claimA: c.split(' vs ')[0] || c,
                  sourceB: 'Source B', claimB: c.split(' vs ')[1] || '',
                  resolution: 'See final answer for resolution',
                })));
              }

              showToast(
                `✓ Research complete — ${completeData.confidence || 0}% confidence`,
                (completeData.confidence || 0) > 80 ? 'green' : 'amber'
              );
              break;
            }
          }
        }
      }
    } catch (err) {
      console.error('SSE stream error:', err);
      showToast(`Backend connection failed: ${err.message}`, 'rose');
      setIsRunning(false);
    }
  };

  // ── Replay Retry Moment ──
  const replayRetryMoment = () => {
    const retryIdx = logs.findIndex(l => l.type === 'evaluate_retry');
    if (retryIdx < 0) {
      showToast('No retry moment found in this session', 'amber');
      return;
    }
    setReplayTarget(retryIdx);
    // Scroll to the retry card
    const cards = document.querySelectorAll('[data-log-index]');
    const retryCard = cards[retryIdx];
    if (retryCard) {
      retryCard.scrollIntoView({ behavior: 'smooth', block: 'center' });
      retryCard.classList.add('replay-highlight');
      setTimeout(() => {
        retryCard.classList.remove('replay-highlight');
        // Now scroll to the next search_retry
        const retrySearchIdx = logs.findIndex((l, i) => i > retryIdx && l.type === 'search_retry');
        if (retrySearchIdx >= 0 && cards[retrySearchIdx]) {
          setTimeout(() => {
            cards[retrySearchIdx].scrollIntoView({ behavior: 'smooth', block: 'center' });
            cards[retrySearchIdx].classList.add('replay-highlight');
            setTimeout(() => cards[retrySearchIdx].classList.remove('replay-highlight'), 3000);
          }, 2000);
        }
      }, 3000);
    }
    setReplayTarget(null);
  };

  const getSourceBadgeColor = (type) => {
    switch (type) {
      case 'Academic': return 'bg-violet-500/20 text-violet-400 border-violet-500/30';
      case 'News': return 'bg-cyan-500/20 text-cyan-400 border-cyan-500/30';
      case 'Official': return 'bg-blue-500/20 text-blue-400 border-blue-500/30';
      default: return 'bg-slate-500/20 text-slate-400 border-slate-500/30';
    }
  };

  return (
    <div className="h-screen flex flex-col bg-[#080b14] relative overflow-hidden scanlines">
      {/* Global Progress Bar */}
      <div className="absolute top-0 left-0 h-[3px] bg-cyan-500 z-50 transition-all duration-300 shadow-[0_0_10px_#00d4ff]" style={{ width: `${progress}%` }} />

      {/* Global Toast System */}
      <div className="absolute top-16 right-6 z-50 flex flex-col gap-2 pointer-events-none">
        {toasts.map(toast => (
          <div key={toast.id} className={`animate-toast flex items-center px-4 py-3 rounded-lg border shadow-lg bg-slate-900 border-${toast.type}-500/50`}>
            <span className={`text-[12px] font-mono font-bold text-${toast.type}-400`}>{toast.message}</span>
          </div>
        ))}
      </div>

      {/* Header */}
      <header className="relative flex-col z-10">
        <div className="h-14 border-b border-cyan-500/30 bg-black/60 flex items-center justify-between px-6 bg-scanline">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-cyan-500/10 border border-cyan-500/60 rounded flex items-center justify-center shadow-[0_0_15px_rgba(0,212,255,0.2)]">
              <Cpu className="text-cyan-400" size={18} />
            </div>
            <h1 className="text-lg font-bold tracking-tight text-glow text-cyan-400">
              ARIA <span className="text-cyan-500/70 font-mono font-light text-sm ml-2 glow-none">— Autonomous Research Intelligence Agent</span>
            </h1>
          </div>

          <div className="flex items-center gap-6 font-mono text-[10px]">
            <div className="flex items-center gap-2">
              <span className="text-slate-500">MODEL</span>
              <span className="px-2 py-0.5 border border-cyan-500/30 bg-slate-900 text-cyan-400 rounded-full font-bold shadow-[0_0_8px_rgba(0,212,255,0.1)]">{selectedModel.toUpperCase()}</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-slate-500">SESSION</span>
              <span className="text-cyan-400 flex items-center gap-1"><Clock size={10} /> {elapsedTime}</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-slate-500">STATUS</span>
              {isRunning ? (
                <div className="w-2.5 h-2.5 rounded-full bg-emerald-500 relative animate-ripple" />
              ) : (
                <div className="w-2.5 h-2.5 rounded-full bg-amber-500 animate-pulse" />
              )}
            </div>
          </div>
        </div>

        {/* Breadcrumb row */}
        <div className="h-6 bg-slate-950 border-b border-cyan-500/10 flex items-center px-6 text-[10px] font-mono text-slate-500">
          <span className="text-cyan-500 mr-2">[{isRunning ? 'ACTIVE' : 'IDLE'}]</span>
          {isRunning ? 'Agent currently executing workflow sequence' : 'Ready to deploy'}
          <span className="mx-2 opacity-30">·</span> Max iterations: 8
          <span className="mx-2 opacity-30">·</span> Confidence threshold: 85%
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 flex overflow-hidden p-4 gap-4">

        {/* Left Panel (25%) */}
        <aside className="w-1/4 flex flex-col gap-4 overflow-y-auto custom-scrollbar pr-1">
          {/* Research Plan */}
          <section className="bg-slate-900/40 border border-cyan-500/10 rounded-lg p-4 flex-1 flex flex-col">
            <h2 className="text-[11px] font-mono font-bold text-cyan-400 mb-4 tracking-widest flex items-center gap-2">
              <Layout size={14} /> [ RESEARCH PLAN ]
            </h2>
            <div className="space-y-3 flex-1">
              {plan.length > 0 ? plan.map((task, i) => (
                <div key={task.id} className={`relative p-3 rounded-lg border flex gap-3 items-start bg-gradient-to-r from-slate-900/80 to-slate-900/20
                  ${task.priority === 'HIGH' ? 'border-rose-500/10 border-l-rose-500 border-l-[4px]' :
                    task.priority === 'MED' ? 'border-amber-500/10 border-l-amber-500 border-l-[4px]' :
                      'border-slate-500/10 border-l-slate-500 border-l-[4px]'}`}>
                  <div className="mt-0.5">
                    {task.status === 'complete' ? (
                      <CheckCircle2 size={14} className="text-emerald-500" />
                    ) : task.status === 'active' ? (
                      <Activity size={14} className="text-cyan-400 animate-pulse" />
                    ) : (
                      <Circle size={14} className="text-slate-600" />
                    )}
                  </div>
                  <div className="flex-1">
                    <div className="flex justify-between items-center mb-1">
                      <span className="text-[9px] font-mono font-bold text-slate-400">{task.id}</span>
                      <div className="flex gap-1">
                        <span className={`text-[8px] font-bold px-1 rounded ${task.priority === 'HIGH' ? 'bg-rose-500/20 text-rose-400' : task.priority === 'MED' ? 'bg-amber-500/20 text-amber-400' : 'bg-slate-700/50 text-slate-400'}`}>
                          {task.priority}
                        </span>
                        <span className="text-[8px] font-bold px-1 rounded bg-blue-500/20 text-blue-400">
                          {task.tool}
                        </span>
                      </div>
                    </div>
                    <p className={`text-xs leading-tight ${task.status === 'complete' ? 'text-slate-500 line-through' : 'text-slate-300'}`}>
                      {task.label}
                    </p>
                  </div>
                </div>
              )) : (
                <div className="h-full flex flex-col items-center justify-center p-6 border border-dashed border-slate-700/50 rounded-lg bg-slate-900/20">
                  <div className="text-slate-500 mb-2 font-mono text-xl">◈</div>
                  <div className="text-xs text-slate-400 font-mono tracking-wide">Awaiting research query</div>
                  <div className="text-[10px] text-slate-600 mt-2 text-center">Subtasks will appear here once agent is deployed</div>
                </div>
              )}
            </div>
          </section>

          {/* Tool Usage */}
          <section className="bg-slate-900/40 border border-cyan-500/10 rounded-lg p-4">
            <h2 className="text-[11px] font-mono font-bold text-cyan-400 mb-4 tracking-widest flex items-center gap-2">
              <Database size={14} /> [ TOOLS ACTIVATED ]
            </h2>
            <div className="space-y-3">
              {toolUsage.map((tool) => (
                <div key={tool.id} className={`flex items-center justify-between p-2 rounded border border-slate-800 transition-all ${tool.active ? 'tool-row-flash border-cyan-500/50' : 'bg-black/30'}`}>
                  <div className="flex items-center gap-3">
                    <tool.icon size={16} className={tool.count > 0 ? 'text-cyan-400' : 'text-slate-600'} />
                    <div className="flex flex-col">
                      <span className={`text-[11px] font-bold ${tool.count > 0 ? 'text-slate-200' : 'text-slate-500'}`}>{tool.name}</span>
                      <span className="text-[8px] font-mono text-slate-600 uppercase">LAST: {tool.lastUsed}</span>
                    </div>
                  </div>
                  <div className="flex flex-col items-end gap-1">
                    <span className={`text-[9px] font-mono px-1.5 py-0.5 rounded border ${tool.count > 0 ? 'border-cyan-500/50 text-cyan-400 bg-cyan-500/10' : 'border-slate-700 text-slate-500'}`}>
                      {tool.count} calls
                    </span>
                    <div className="flex gap-px h-2 items-end">
                      {tool.history.map((val, i) => (
                        <div key={i} className={`w-1 transition-all ${val > 0 ? 'h-full bg-cyan-500' : 'h-1 bg-slate-800'}`} />
                      ))}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </section>

          {/* Stats */}
          <section className="bg-slate-900/40 border border-cyan-500/10 rounded-lg p-4">
            <h2 className="text-[11px] font-mono font-bold text-cyan-400 mb-4 tracking-widest flex items-center gap-2">
              <Activity size={14} /> [ AGENT STATS ]
            </h2>
            <div className="grid grid-cols-2 gap-3 mb-4">
              <div className="bg-black/40 border border-slate-800 rounded p-2 flex flex-col items-center">
                <span className="text-[9px] text-slate-500 font-bold uppercase tracking-widest mb-1">Steps</span>
                <span className="text-xl font-mono text-cyan-400 text-glow">{stats.steps}</span>
              </div>
              <div className="bg-black/40 border border-slate-800 rounded p-2 flex flex-col items-center">
                <span className="text-[9px] text-slate-500 font-bold uppercase tracking-widest mb-1">Searches</span>
                <span className="text-xl font-mono text-cyan-400 text-glow">{stats.searches}</span>
              </div>
              <div className="bg-black/40 border border-slate-800 rounded p-2 flex flex-col items-center">
                <span className="text-[9px] text-slate-500 font-bold uppercase tracking-widest mb-1">Iterations</span>
                <span className="text-xl font-mono text-cyan-400 text-glow">{stats.iterations}</span>
              </div>
              <div className="bg-black/40 border border-slate-800 rounded p-2 flex flex-col items-center">
                <span className="text-[9px] text-slate-500 font-bold uppercase tracking-widest mb-1">Tokens</span>
                <span className="text-xl font-mono text-purple-400 drop-shadow-[0_0_8px_rgba(147,51,234,0.5)]">{stats.tokens}</span>
              </div>
            </div>

            <div className="mt-2 pt-3 border-t border-slate-800">
              <div className="flex justify-between text-[8px] text-slate-500 font-mono tracking-widest mb-2">
                <span>ITERATION PROGRESS</span>
                <span>{stats.iterations} / 8</span>
              </div>
              <div className="w-full h-1 bg-slate-800 rounded-full overflow-hidden">
                <div className="h-full bg-cyan-500 transition-all duration-300 shadow-[0_0_8px_#00d4ff]" style={{ width: `${(stats.iterations / 8) * 100}%` }} />
              </div>
            </div>
          </section>

          {/* Gap Tracker */}
          {gaps.length > 0 && (
            <section className="bg-slate-900/40 border border-rose-500/10 rounded-lg p-4">
              <h2 className="text-[11px] font-mono font-bold text-rose-400 mb-4 tracking-widest flex items-center gap-2">
                <AlertCircle size={14} /> [ GAP TRACKER ]
              </h2>
              <div className="space-y-2">
                {gaps.map((gap, i) => {
                  const isResolved = confidenceHistory.length > 1 && confidenceHistory[confidenceHistory.length - 1] >= 85;
                  return (
                    <div key={i} className="flex items-start gap-2 p-2 rounded border border-slate-800 bg-black/30 animate-slide-up" style={{ animationDelay: `${i * 100}ms` }}>
                      <div className={`mt-0.5 w-2 h-2 rounded-full flex-shrink-0 ${isResolved ? 'bg-emerald-500' : 'bg-rose-500 animate-pulse'}`} />
                      <div className="flex-1">
                        <p className={`text-[10px] font-mono leading-tight ${isResolved ? 'text-slate-500 line-through' : 'text-slate-300'}`}>{gap}</p>
                        <span className={`text-[8px] font-bold uppercase tracking-widest mt-0.5 ${isResolved ? 'text-emerald-500' : 'text-rose-400'}`}>
                          {isResolved ? '✓ RESOLVED' : '○ OPEN'}
                        </span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </section>
          )}
        </aside>

        {/* Center Panel (45%) */}
        <section className="flex-1 flex flex-col bg-slate-900 border border-cyan-500/20 rounded-lg overflow-hidden center-panel-bg shadow-lg shadow-black/50 relative">
          <div className="p-3 border-b border-cyan-500/20 bg-black/80 flex justify-between items-center z-10">
            <div className="flex items-center gap-2">
              <span className="text-cyan-500 font-mono font-bold text-sm">{'>'}</span>
              <span className="text-[12px] font-mono font-bold text-cyan-400 tracking-widest text-glow">THINKING_LOG_STREAM</span>
            </div>
            <div className="flex items-center gap-4">
              {/* Replay Retry Moment button */}
              {retryEvents.length > 0 && (
                <button
                  onClick={replayRetryMoment}
                  className="px-2 py-1 rounded-full text-[9px] font-mono font-bold transition-all border bg-rose-500/10 border-rose-500/30 text-rose-400 hover:bg-rose-500/20 flex items-center gap-1"
                >
                  <RotateCcw size={10} /> REPLAY RETRY
                </button>
              )}
              <button
                onClick={() => setAutoScroll(!autoScroll)}
                className={`px-2 py-1 rounded-full text-[9px] font-mono font-bold transition-all border ${autoScroll ? 'bg-cyan-500/20 border-cyan-500/50 text-cyan-400' : 'bg-slate-800 border-slate-700 text-slate-500'}`}
              >
                AUTO-SCROLL {autoScroll ? '↓' : '⏸'}
              </button>
              <div className="flex items-center gap-1.5 border border-slate-800 px-2 py-0.5 rounded-full bg-slate-900">
                <div className={`w-1.5 h-1.5 rounded-full ${isRunning ? 'bg-emerald-500 animate-pulse shadow-[0_0_5px_#10b981]' : 'bg-rose-500'}`} />
                <span className={`text-[9px] font-mono font-bold ${isRunning ? 'text-emerald-500' : 'text-rose-500'}`}>● LIVE</span>
              </div>
            </div>
          </div>

          <div className="flex-1 overflow-y-auto p-5 custom-scrollbar relative z-0">
            {logs.length > 0 ? (
              <div className="max-w-3xl mx-auto pb-10">
                {/* Confidence Delta indicator */}
                {confidenceDelta !== null && (
                  <div className={`text-center mb-3 py-1 px-3 rounded-full text-[10px] font-mono font-bold inline-flex items-center gap-1 mx-auto ${confidenceDelta > 0 ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' : 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                    }`}>
                    CONFIDENCE {confidenceDelta > 0 ? '↑' : '↓'} {confidenceDelta > 0 ? '+' : ''}{confidenceDelta}%
                  </div>
                )}

                {/* Active Retry Banner */}
                {activeRetryBanner && (
                  <div className="mb-6 p-4 bg-gradient-to-r from-rose-500/10 via-rose-500/5 to-transparent border border-rose-500/30 rounded-lg animate-slide-up shadow-[0_0_30px_rgba(244,63,94,0.1)]">
                    <div className="flex items-center gap-3 mb-2">
                      <div className="w-8 h-8 bg-rose-500/20 border border-rose-500/50 rounded-full flex items-center justify-center">
                        <RotateCcw size={16} className="text-rose-400 animate-spin" style={{ animationDuration: '3s' }} />
                      </div>
                      <div>
                        <div className="text-[11px] font-mono font-bold text-rose-400 tracking-widest">SELF-CORRECTION IN PROGRESS</div>
                        <div className="text-[9px] text-rose-400/60 font-mono">Iteration {activeRetryBanner.iteration} · Confidence: {activeRetryBanner.confidence}%</div>
                      </div>
                    </div>
                    <div className="text-[10px] text-slate-400 font-mono mb-2">
                      <span className="text-rose-400 font-bold">Failed query:</span> {activeRetryBanner.failed_query?.slice(0, 80)}
                    </div>
                    {activeRetryBanner.gaps && activeRetryBanner.gaps.length > 0 && (
                      <div className="flex flex-wrap gap-1">
                        {activeRetryBanner.gaps.map((gap, i) => (
                          <span key={i} className="text-[8px] bg-rose-500/10 border border-rose-500/20 text-rose-300 px-1.5 py-0.5 rounded">{gap}</span>
                        ))}
                      </div>
                    )}
                  </div>
                )}

                {logs.map((step, idx) => {
                  // Insert visual separator before search_retry cards
                  const showRetryDivider = step.type === 'search_retry' && idx > 0;
                  return (
                    <React.Fragment key={idx}>
                      {showRetryDivider && (
                        <div className="flex items-center gap-3 my-6">
                          <div className="flex-1 h-px bg-gradient-to-r from-transparent via-rose-500/40 to-transparent" />
                          <span className="text-[9px] font-mono font-bold text-rose-400 tracking-widest flex items-center gap-1">
                            <RotateCcw size={10} /> ATTEMPT {iterationData.length}
                          </span>
                          <div className="flex-1 h-px bg-gradient-to-r from-transparent via-rose-500/40 to-transparent" />
                        </div>
                      )}
                      <LogCard step={step} isLatest={idx === logs.length - 1} index={idx} />
                    </React.Fragment>
                  );
                })}
                <div ref={logEndRef} className="h-4" />
              </div>
            ) : (
              <div className="h-full flex flex-col items-center justify-center relative">
                <div className="absolute inset-0 flex flex-col gap-4 p-8 opacity-[0.03] pointer-events-none">
                  <div className="w-full h-32 bg-white rounded-lg animate-shimmer" />
                  <div className="w-full h-24 bg-white rounded-lg animate-shimmer" style={{ animationDelay: '0.2s' }} />
                  <div className="w-3/4 h-24 bg-white rounded-lg animate-shimmer" style={{ animationDelay: '0.4s' }} />
                </div>

                <div className="z-10 flex flex-col items-center">
                  <div className="relative">
                    <div className="absolute inset-0 bg-cyan-500 blur-xl opacity-20 animate-pulse rounded-full" />
                    <Zap size={64} className="mb-6 text-cyan-400 animate-pulse relative z-10 drop-shadow-[0_0_15px_rgba(0,212,255,0.4)]" />
                  </div>
                  <p className="text-lg font-mono font-bold text-slate-300 tracking-wider">WAITING FOR DEPLOYMENT...</p>
                  <p className="text-xs text-slate-500 font-mono mt-2">Log entries will appear here during execution</p>
                </div>
              </div>
            )}
          </div>
        </section>

        {/* Right Panel (30%) */}
        <aside className="w-[30%] flex flex-col gap-4 overflow-y-auto custom-scrollbar pr-1">
          {/* Confidence Dashboard */}
          <section className="bg-slate-900/40 border border-cyan-500/10 rounded-lg p-5">
            <h2 className="text-[11px] font-mono font-bold text-cyan-400 mb-6 tracking-widest flex items-center gap-2">
              <Cpu size={14} /> [ CONFIDENCE TRACKER ]
            </h2>
            <ConfidenceDial value={confidence} history={confidenceHistory} />
            <div className="flex items-center justify-center mt-6 p-2 bg-slate-950/50 rounded border border-slate-800">
              <ShieldCheck size={14} className="text-emerald-500 mr-2" />
              <span className="text-[10px] text-slate-400 font-mono">Minimum Threshold: 85%</span>
            </div>
          </section>

          {/* Iteration Timeline */}
          {iterationData.length > 0 && (
            <section className="bg-slate-900/40 border border-cyan-500/10 rounded-lg p-4">
              <h2 className="text-[11px] font-mono font-bold text-cyan-400 mb-4 tracking-widest flex items-center gap-2">
                <Activity size={14} /> [ ITERATION TIMELINE ]
              </h2>
              <div className="relative">
                {/* Vertical line */}
                <div className="absolute left-3 top-2 bottom-2 w-px bg-slate-700" />
                <div className="space-y-3">
                  {iterationData.map((iter, i) => {
                    const isRetry = iter.type === 'search_retry';
                    const passed = iter.passed === true;
                    const dotColor = passed ? 'bg-emerald-500' : isRetry ? 'bg-rose-500' : 'bg-cyan-500';
                    return (
                      <div key={i} className="flex items-start gap-3 pl-1 relative animate-slide-up" style={{ animationDelay: `${i * 100}ms` }}>
                        <div className={`w-5 h-5 rounded-full flex items-center justify-center text-[9px] font-bold text-white z-10 ${dotColor} shadow-lg`}>
                          {i + 1}
                        </div>
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-0.5">
                            <span className={`text-[9px] font-mono font-bold ${isRetry ? 'text-amber-400' : 'text-slate-300'}`}>
                              {isRetry ? '↺ RETRY' : 'SEARCH'}
                            </span>
                            <span className="text-[8px] px-1 rounded bg-blue-500/20 text-blue-300 border border-blue-500/20">{iter.tool}</span>
                          </div>
                          <p className="text-[9px] text-slate-500 font-mono truncate max-w-[180px]">"{iter.query}"</p>
                          {iter.confidence !== null && (
                            <div className="flex items-center gap-2 mt-1">
                              <span className={`text-[10px] font-mono font-bold ${passed ? 'text-emerald-400' : 'text-rose-400'}`}>
                                {iter.confidence}%
                              </span>
                              {passed ? (
                                <span className="text-[8px] bg-emerald-500/20 text-emerald-400 px-1 rounded font-bold">PASS</span>
                              ) : (
                                <span className="text-[8px] bg-rose-500/20 text-rose-400 px-1 rounded font-bold">RETRY</span>
                              )}
                            </div>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            </section>
          )}

          {/* Sources Panel */}
          <section className="bg-slate-900/40 border border-cyan-500/10 rounded-lg p-4 flex-1 flex flex-col">
            <h2 className="text-[11px] font-mono font-bold text-cyan-400 mb-4 tracking-widest flex items-center gap-2">
              <FileText size={14} /> [ SOURCES FOUND ]
            </h2>
            <div className="space-y-3 overflow-y-auto custom-scrollbar flex-1 pb-2">
              {sources.length > 0 ? sources.map((source) => (
                <div key={source.id} className="p-3 bg-slate-950 border border-slate-800 rounded-lg animate-slide-up hover:border-cyan-500/30 hover:bg-black transition-all group relative overflow-hidden">
                  <div className="absolute top-0 right-0 w-16 h-16 bg-gradient-to-bl from-cyan-500/10 to-transparent opacity-0 group-hover:opacity-100 transition-opacity rounded-tr-lg" />

                  <div className="flex justify-between items-start mb-2 relative z-10">
                    <div className="flex items-center gap-2">
                      <div className="w-5 h-5 rounded-full bg-slate-800 border border-slate-600 flex items-center justify-center text-[10px] font-bold text-slate-300 shadow-inner">
                        {source.domain.charAt(0).toUpperCase()}
                      </div>
                      <div className="flex flex-col">
                        <span className="text-[11px] font-bold text-slate-200">{source.domain}</span>
                        {source.title && (
                          <span className="text-[9px] text-cyan-400/70 font-medium leading-tight mt-0.5 max-w-[140px] truncate" title={source.title}>{source.title}</span>
                        )}
                        <span className="text-[8px] text-slate-500 overflow-hidden text-ellipsis whitespace-nowrap w-32">{source.url}</span>
                      </div>
                    </div>
                    <div className="flex flex-col gap-1 items-end">
                      <span className={`text-[8px] font-bold px-1.5 py-0.5 rounded border ${source.reliability === 'HIGH' ? 'border-emerald-500/30 text-emerald-400 bg-emerald-500/10' :
                        source.reliability === 'MEDIUM' ? 'border-amber-500/30 text-amber-400 bg-amber-500/10' :
                          'border-rose-500/30 text-rose-400 bg-rose-500/10'
                        }`}>
                        {source.reliability}
                      </span>
                      {source.type && (
                        <span className={`text-[8px] px-1 rounded border ${getSourceBadgeColor(source.type)}`}>
                          {source.type}
                        </span>
                      )}
                    </div>
                  </div>
                  <p className="text-[11px] text-slate-400 leading-snug italic mt-2 relative z-10">"{source.snippet}"</p>
                </div>
              )) : (
                <div className="h-full flex flex-col items-center justify-center p-6 border border-dashed border-slate-800 rounded-lg bg-black/20">
                  <Grid size={24} className="text-slate-600 mb-2 opacity-50" />
                  <div className="text-[10px] text-slate-500 font-mono text-center">Sources will appear as agent searches</div>
                </div>
              )}
            </div>

            {/* Contradiction Monitor */}
            <div className="mt-4 pt-4 border-t border-slate-800">
              <h3 className="text-[10px] font-mono font-bold text-rose-400 mb-3 tracking-widest flex items-center gap-2">
                <AlertCircle size={12} /> [ CONTRADICTION MONITOR ]
              </h3>
              {contradictions.length > 0 ? contradictions.map((c, i) => (
                <div key={i} className="bg-rose-950/20 border border-rose-900/50 rounded-lg p-2.5 animate-slide-up">
                  <div className="flex gap-2 text-[10px]">
                    <div className="flex-1 bg-black/40 p-1.5 rounded border border-slate-800">
                      <span className="font-bold text-slate-400 block mb-0.5">{c.sourceA}</span>
                      <span className="text-slate-300">"{c.claimA}"</span>
                    </div>
                    <div className="flex items-center font-bold text-rose-500">VS</div>
                    <div className="flex-1 bg-black/40 p-1.5 rounded border border-slate-800">
                      <span className="font-bold text-slate-400 block mb-0.5">{c.sourceB}</span>
                      <span className="text-slate-300">"{c.claimB}"</span>
                    </div>
                  </div>
                  <div className="mt-2 text-[9px] text-rose-300/80 italic pl-1 border-l-2 border-rose-500/50">
                    Resolution:   {c.resolution}
                  </div>
                </div>
              )) : (
                <div className="text-[10px] text-slate-600 font-mono italic px-2">No contradictions detected</div>
              )}
            </div>

            {/* Hallucination Risk Panel */}
            <div className="mt-4 pt-4 border-t border-slate-800">
              <h3 className="text-[10px] font-mono font-bold text-cyan-500/70 mb-3 tracking-widest">
                [ HALLUCINATION RISK ]
              </h3>
              {(() => {
                // Compute dynamic hallucination metrics
                const uniqueDomains = new Set(sources.map(s => s.domain)).size;
                const sourceDiversity = Math.min(100, sources.length > 0 ? (uniqueDomains / Math.max(sources.length, 1)) * 100 : 0);
                const claimVerification = confidence > 0 ? confidence : 0;
                const totalIters = iterationData.length;
                const retryCount = iterationData.filter(d => d.type === 'search_retry').length;
                const loopRisk = totalIters > 0 ? (retryCount / totalIters) * 100 : 0;
                return (
                  <div className="space-y-2">
                    <div className="flex justify-between items-center bg-black/40 p-1.5 rounded border border-slate-800">
                      <span className="text-[9px] text-slate-400 uppercase">Source Diversity</span>
                      <div className="flex items-center gap-2">
                        <span className="text-[9px] font-mono text-slate-500">{Math.round(sourceDiversity)}%</span>
                        <div className="w-16 h-1.5 bg-slate-800 rounded-full overflow-hidden">
                          <div className={`h-full rounded-full transition-all duration-500 ${sourceDiversity > 60 ? 'bg-emerald-500' : sourceDiversity > 30 ? 'bg-amber-500' : 'bg-rose-500'}`} style={{ width: `${sourceDiversity}%` }} />
                        </div>
                      </div>
                    </div>
                    <div className="flex justify-between items-center bg-black/40 p-1.5 rounded border border-slate-800">
                      <span className="text-[9px] text-slate-400 uppercase">Claim Verification</span>
                      <div className="flex items-center gap-2">
                        <span className="text-[9px] font-mono text-slate-500">{Math.round(claimVerification)}%</span>
                        <div className="w-16 h-1.5 bg-slate-800 rounded-full overflow-hidden">
                          <div className={`h-full rounded-full transition-all duration-500 ${claimVerification > 70 ? 'bg-emerald-500' : claimVerification > 40 ? 'bg-amber-500' : 'bg-rose-500'}`} style={{ width: `${claimVerification}%` }} />
                        </div>
                      </div>
                    </div>
                    <div className="flex justify-between items-center bg-black/40 p-1.5 rounded border border-slate-800">
                      <span className="text-[9px] text-slate-400 uppercase">Loop Detection</span>
                      <div className="flex items-center gap-2">
                        <span className="text-[9px] font-mono text-slate-500">{Math.round(loopRisk)}%</span>
                        <div className="w-16 h-1.5 bg-slate-800 rounded-full overflow-hidden">
                          <div className={`h-full rounded-full transition-all duration-500 ${loopRisk < 30 ? 'bg-emerald-500' : loopRisk < 60 ? 'bg-amber-500' : 'bg-rose-500'}`} style={{ width: `${loopRisk}%` }} />
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })()}
            </div>
          </section>

          {/* Final Answer Panel */}
          {showFinal && finalAnswer && (
            <section className="bg-[#12080a] border border-rose-500/50 rounded-lg p-5 animate-slide-up shadow-[0_0_30px_rgba(244,63,94,0.15)] relative overflow-hidden">
              <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-rose-500/20 via-rose-500 to-rose-500/20" />
              <div className="flex items-center gap-2 mb-4 mt-1">
                <ShieldCheck size={18} className="text-rose-500" />
                <h2 className="text-xs font-mono font-bold text-rose-500 tracking-widest text-shadow-sm">[ RESEARCH COMPLETE ]</h2>
              </div>
              <div className="text-[13px] text-slate-200 leading-relaxed mb-5 font-serif border-l-2 border-rose-500/30 pl-3">
                <TypewriterText text={finalAnswer.answer} speed={15} />
              </div>
              <div className="space-y-2 mb-5 bg-black/40 p-3 rounded border border-rose-900/30">
                <div className="flex items-center gap-2 text-[10px] text-rose-400">
                  <AlertCircle size={14} />
                  <span className="font-bold uppercase tracking-widest">Caveats:</span>
                </div>
                <ul className="text-[11px] text-slate-400 space-y-1.5 ml-6 list-disc marker:text-rose-500">
                  {finalAnswer.caveats.map((c, i) => <li key={i}>{c}</li>)}
                </ul>
              </div>
              <div className="flex gap-2">
                <button className="flex-1 bg-rose-500 hover:bg-rose-400 text-white py-2.5 rounded text-[11px] font-bold font-mono tracking-widest flex items-center justify-center gap-2 transition-all shadow-[0_0_15px_rgba(244,63,94,0.4)]">
                  <Copy size={14} /> COPY DOSSIER
                </button>
              </div>
            </section>
          )}
        </aside>
      </main>

      {/* Bottom Input Bar */}
      <footer className="p-4 bg-black/80 border-t border-cyan-500/30 z-20 backdrop-blur-md">
        <div className="max-w-6xl mx-auto">
          <div className="flex gap-3 mb-2">
            <div className="flex-1 relative group glow-border rounded-lg bg-slate-900/80 transition-all">
              <div className="absolute left-4 top-1/2 -translate-y-1/2 text-cyan-500 font-mono font-bold pointer-events-none">
                {'>'}
              </div>
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && runSimulation()}
                placeholder="Ask ARIA anything — e.g. Impact of AGI on employment..."
                className="w-full bg-transparent border-0 rounded-lg py-3.5 pl-10 pr-12 text-sm text-white focus:outline-none placeholder:text-slate-500 font-mono"
                disabled={isRunning}
              />
              <div className="absolute right-3 top-1/2 -translate-y-1/2 flex items-center gap-2">
                <button
                  onClick={resetState}
                  className="p-1.5 rounded text-slate-500 hover:bg-slate-800 hover:text-white transition-all"
                  title="Reset Agent (Esc)"
                >
                  <RotateCcw size={16} />
                </button>
              </div>
            </div>
            <button
              onClick={() => isRunning ? resetState() : runSimulation()}
              disabled={!isRunning && !query.trim()}
              className={`px-8 rounded-lg font-mono font-bold text-xs tracking-widest flex items-center gap-3 transition-all group overflow-hidden relative ${isRunning
                ? 'bg-rose-500/10 hover:bg-rose-500/20 text-rose-500 border border-rose-500/50'
                : !query.trim()
                  ? 'bg-slate-800 text-slate-500 cursor-not-allowed border border-slate-700'
                  : 'bg-cyan-600 hover:bg-cyan-500 text-white shadow-[0_0_15px_rgba(0,212,255,0.4)] hover:shadow-[0_0_25px_rgba(0,212,255,0.6)]'
                }`}
            >
              {!isRunning && query.trim() && (
                <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent translate-x-[-100%] group-hover:animate-shimmer" />
              )}
              {isRunning ? (
                <>
                  <div className="w-2 h-2 bg-rose-500" /> {/* Stop square */}
                  ABORT MISSION
                </>
              ) : (
                <>
                  DEPLOY AGENT
                  <Send size={16} className="slide-right-arrow" />
                </>
              )}
            </button>
          </div>

          <div className="flex gap-2 items-center mb-1">
            {/* Model Selector */}
            <div className="relative">
              <select
                value={`${selectedProvider}::${selectedModel}`}
                onChange={(e) => {
                  const [prov, mod] = e.target.value.split('::');
                  handleModelSwitch(prov, mod);
                }}
                disabled={isRunning}
                className="appearance-none bg-slate-800/80 border border-slate-600/50 rounded-lg px-3 py-1.5 text-[10px] font-mono text-cyan-300 focus:outline-none focus:border-cyan-500/50 cursor-pointer hover:bg-slate-700/80 transition-all pr-6"
                style={{ backgroundImage: `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' fill='%2306b6d4' viewBox='0 0 16 16'%3E%3Cpath d='M4 6l4 4 4-4'/%3E%3C/svg%3E")`, backgroundRepeat: 'no-repeat', backgroundPosition: 'right 6px center' }}
              >
                {availableModels.providers.map((prov: any) => (
                  <optgroup key={prov.id} label={`${prov.name}${!prov.available ? ' (no key)' : ''}`}>
                    {prov.models.map((m: any) => (
                      <option key={`${prov.id}::${m.id}`} value={`${prov.id}::${m.id}`} disabled={!prov.available}>
                        {m.name}
                      </option>
                    ))}
                  </optgroup>
                ))}
              </select>
            </div>
            <span className="text-[10px] text-cyan-500/60 uppercase font-mono mr-2 tracking-widest">Quick Queries:</span>
            {[
              "Impact of AGI on global employment by 2030",
              "Is cold fusion scientifically viable today?",
              "Geopolitical consequences of BRICS de-dollarization"
            ].map((txt) => (
              <button
                key={txt}
                onClick={() => setQuery(txt)}
                disabled={isRunning}
                className={`px-4 py-1.5 rounded-full border text-[10px] font-mono group flex items-center gap-1 transition-all ${query === txt
                  ? 'bg-cyan-500/20 border-cyan-500/50 text-cyan-300'
                  : 'bg-slate-900/60 border-slate-700/50 text-slate-400 hover:border-cyan-500/50 hover:text-cyan-400 hover:bg-slate-800'
                  } ${isRunning ? 'opacity-50 cursor-not-allowed' : ''}`}
              >
                <span className="truncate max-w-[200px]">{txt}</span>
                <span className="opacity-0 group-hover:opacity-100 transition-opacity slide-right-arrow text-cyan-500">→</span>
              </button>
            ))}
          </div>

          <div className="text-center mt-3">
            <span className="text-[9px] text-slate-600 font-mono tracking-widest">Press Enter or <span className="bg-slate-800 px-1 rounded text-slate-400">Space</span> to deploy · <span className="bg-slate-800 px-1 rounded text-slate-400">Esc</span> to reset · <span className="text-cyan-500/50">↑↓</span> to browse history</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
