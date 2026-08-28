import React, { useState, useEffect } from 'react';
import { 
  getAdversarialRounds, 
  getAdversarialStatus, 
  getAdversarialMetrics, 
  runAdversarialRound, 
  resetAdversarialSession 
} from '../api';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  ReferenceLine,
  Legend
} from 'recharts';
import { 
  Swords, 
  ShieldAlert, 
  Zap, 
  TrendingUp, 
  RefreshCw, 
  Cpu, 
  Award, 
  RotateCcw,
  Sliders,
  CheckCircle2,
  AlertTriangle,
  Play,
  Flame,
  Bot,
  Shield,
  ChevronDown,
  ChevronUp,
  Layers,
  Sparkles
} from 'lucide-react';

export default function ArmsRaceChart({ showToast }) {
  const [rounds, setRounds] = useState([]);
  const [status, setStatus] = useState(null);
  const [metrics, setMetrics] = useState(null);
  const [loading, setLoading] = useState(false);
  const [runningRound, setRunningRound] = useState(false);
  const [autoRunning, setAutoRunning] = useState(false);
  const [expandedRound, setExpandedRound] = useState(null);
  const [errorMsg, setErrorMsg] = useState(null);

  useEffect(() => {
    fetchAllData();
  }, []);

  const fetchAllData = async () => {
    try {
      setLoading(true);
      setErrorMsg(null);
      const [roundsData, statusData, metricsData] = await Promise.all([
        getAdversarialRounds(),
        getAdversarialStatus().catch(() => null),
        getAdversarialMetrics().catch(() => null)
      ]);
      setRounds(roundsData);
      if (statusData) setStatus(statusData);
      if (metricsData) setMetrics(metricsData);
    } catch (err) {
      console.error(err);
      setErrorMsg('Failed to load adversarial session data.');
    } finally {
      setLoading(false);
    }
  };

  const handleRunRound = async () => {
    try {
      setRunningRound(true);
      setErrorMsg(null);
      const res = await runAdversarialRound();
      await fetchAllData();
      if (showToast) {
        if (res.outcome === 'DETECTED') {
          showToast(`Round ${res.round_number}: Sentinel intercepted attack (${res.risk_score_pct}% risk)`, 'alert');
        } else {
          showToast(`Round ${res.round_number}: Forge EVADED detection (${res.risk_score_pct}% risk)!`, 'info');
        }
      }
    } catch (err) {
      console.error(err);
      setErrorMsg('Error executing adversarial round.');
    } finally {
      setRunningRound(false);
    }
  };

  const handleAutoRun = async (count = 5) => {
    try {
      setAutoRunning(true);
      setErrorMsg(null);
      for (let i = 0; i < count; i++) {
        await runAdversarialRound();
        await fetchAllData();
        await new Promise(r => setTimeout(r, 650));
      }
      if (showToast) showToast(`Completed ${count}-round adversarial simulation`, 'success');
    } catch (err) {
      console.error(err);
      setErrorMsg('Error during multi-round simulation.');
    } finally {
      setAutoRunning(false);
    }
  };

  const handleReset = async () => {
    try {
      setLoading(true);
      setErrorMsg(null);
      await resetAdversarialSession();
      await fetchAllData();
      if (showToast) showToast('Adversarial session reset to Round 0', 'info');
    } catch (err) {
      console.error(err);
      setErrorMsg('Failed to reset adversarial session.');
    } finally {
      setLoading(false);
    }
  };

  // Prepare real chart data
  const chartData = rounds.map((r) => ({
    round: `R${r.round_number}`,
    roundNum: r.round_number,
    catch_rate: r.rolling_catch_rate ?? (r.outcome === 'DETECTED' ? 100 : 0),
    evasion_rate: r.rolling_evasion_rate ?? 0,
    risk_score_pct: r.risk_score_pct ?? (r.risk_score ? r.risk_score * 100 : 0),
    threshold_pct: r.sentinel_threshold ? (r.sentinel_threshold * 100) : 55,
    outcome: r.outcome,
    is_detected: r.outcome === 'DETECTED',
    mutation_description: r.mutation_description,
    round_summary: r.round_summary,
    sentinel_note: r.sentinel_note,
    features: r.features,
    forge_params_used: r.forge_params_used
  }));

  const forgeParams = status?.forge_params || {};

  return (
    <div className="space-y-6">
      {/* Real Adversarial Status KPI Banner */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
        <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-3.5 flex flex-col justify-between shadow-lg">
          <span className="text-[11px] text-slate-400 font-medium uppercase tracking-wider">Rounds Run</span>
          <div className="flex items-baseline space-x-1.5 mt-1">
            <span className="text-2xl font-black text-slate-100 font-mono">{status?.round_number ?? rounds.length}</span>
            <span className="text-[10px] text-slate-500">cycles</span>
          </div>
          <div className="mt-2 text-[10px] text-cyan-400 flex items-center space-x-1">
            <Cpu className="w-3 h-3" />
            <span>Active simulation</span>
          </div>
        </div>

        <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-3.5 flex flex-col justify-between shadow-lg">
          <span className="text-[11px] text-slate-400 font-medium uppercase tracking-wider">Detected Attacks</span>
          <div className="flex items-baseline space-x-1.5 mt-1">
            <span className="text-2xl font-black text-emerald-400 font-mono">{status?.total_detected ?? rounds.filter(r => r.outcome === 'DETECTED').length}</span>
            <span className="text-[10px] text-slate-500">/ {status?.total_attacks ?? rounds.length}</span>
          </div>
          <div className="mt-2 text-[10px] text-emerald-400 flex items-center space-x-1">
            <CheckCircle2 className="w-3 h-3" />
            <span>Interceptions</span>
          </div>
        </div>

        <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-3.5 flex flex-col justify-between shadow-lg">
          <span className="text-[11px] text-slate-400 font-medium uppercase tracking-wider">Evaded (Missed)</span>
          <div className="flex items-baseline space-x-1.5 mt-1">
            <span className="text-2xl font-black text-rose-400 font-mono">{status?.total_evaded ?? rounds.filter(r => r.outcome === 'EVADED').length}</span>
            <span className="text-[10px] text-slate-500">misses</span>
          </div>
          <div className="mt-2 text-[10px] text-rose-400 flex items-center space-x-1">
            <AlertTriangle className="w-3 h-3" />
            <span>Forge evasions</span>
          </div>
        </div>

        <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-3.5 flex flex-col justify-between shadow-lg">
          <span className="text-[11px] text-slate-400 font-medium uppercase tracking-wider">Catch Rate</span>
          <div className="flex items-baseline space-x-1 mt-1">
            <span className="text-2xl font-black text-cyan-400 font-mono">
              {status?.current_catch_rate !== null && status?.current_catch_rate !== undefined 
                ? `${status.current_catch_rate}%` 
                : '—'}
            </span>
          </div>
          <div className="mt-2 text-[10px] text-cyan-400 flex items-center space-x-1">
            <Award className="w-3 h-3" />
            <span>Sentinel recall</span>
          </div>
        </div>


        <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-3.5 flex flex-col justify-between shadow-lg">
          <span className="text-[11px] text-slate-400 font-medium uppercase tracking-wider">Adaptive Thresh</span>
          <div className="flex items-baseline space-x-1 mt-1">
            <span className="text-2xl font-black text-amber-400 font-mono">
              {status?.sentinel_threshold ? status.sentinel_threshold.toFixed(2) : '0.55'}
            </span>
          </div>
          <div className="mt-2 text-[10px] text-amber-400 flex items-center space-x-1">
            <Shield className="w-3 h-3" />
            <span>Sensitivity target</span>
          </div>
        </div>

        <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-3.5 flex flex-col justify-between shadow-lg">
          <span className="text-[11px] text-slate-400 font-medium uppercase tracking-wider">Forge Stealth</span>
          <div className="flex items-baseline space-x-1 mt-1">
            <span className="text-2xl font-black text-purple-400 font-mono">
              Level {status?.stealth_level || 1}
            </span>
            <span className="text-[10px] text-slate-500">/ 3</span>
          </div>
          <div className="mt-2 text-[10px] text-purple-400 flex items-center space-x-1">
            <Bot className="w-3 h-3" />
            <span>Mutation level</span>
          </div>
        </div>
      </div>

      {/* Interactive Combat Center: Attacker vs Defender */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Left: Forge Attacker Card */}
        <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-4 flex flex-col justify-between shadow-lg">
          <div className="flex items-center justify-between border-b border-slate-800 pb-2.5">
            <div className="flex items-center space-x-2">
              <Bot className="w-5 h-5 text-purple-400" />
              <h4 className="text-sm font-bold text-slate-100">Forge AI (Attacker)</h4>
            </div>
            <span className="text-[10px] px-2 py-0.5 rounded bg-purple-950 text-purple-300 border border-purple-800 font-mono">
              Mutating Engine
            </span>
          </div>

          <div className="mt-3 space-y-2 text-xs">
            <div className="flex justify-between py-1 border-b border-slate-800/60">
              <span className="text-slate-400">Spend Noise Factor:</span>
              <span className="font-mono font-bold text-cyan-400">{forgeParams.noise_factor?.toFixed(3) || '0.035'}</span>
            </div>
            <div className="flex justify-between py-1 border-b border-slate-800/60">
              <span className="text-slate-400">Dip Probability:</span>
              <span className="font-mono font-bold text-indigo-400">{(forgeParams.dip_probability * 100)?.toFixed(0) || '4'}%</span>
            </div>
            <div className="flex justify-between py-1 border-b border-slate-800/60">
              <span className="text-slate-400">Login Jitter:</span>
              <span className="font-mono font-bold text-amber-400">±{forgeParams.login_jitter ?? 1} sessions</span>
            </div>
            <div className="flex justify-between py-1">
              <span className="text-slate-400">Terminal Surge Cap:</span>
              <span className="font-mono font-bold text-rose-400">{forgeParams.surge_multiplier_cap?.toFixed(1) || '20.0'}x</span>
            </div>
          </div>
        </div>

        {/* Center: Live Action War Room */}
        <div className="bg-gradient-to-b from-slate-900 via-slate-900 to-slate-950 border border-slate-800 rounded-xl p-5 flex flex-col justify-between items-center text-center shadow-xl">
          <div className="flex items-center space-x-2">
            <Swords className="w-6 h-6 text-rose-400 animate-pulse" />
            <h4 className="text-base font-bold text-slate-100">Live Adversarial Arena</h4>
          </div>
          <p className="text-xs text-slate-400 max-w-xs mt-1">
            Simulate adaptive arms race cycles: Forge shifts prompt templates to evade, Sentinel tightens multi-signal forensics to catch.
          </p>

          <div className="flex items-center space-x-2.5 my-4">
            <button
              onClick={handleRunRound}
              disabled={runningRound || autoRunning}
              className="flex items-center space-x-1.5 bg-gradient-to-r from-rose-600 to-red-600 hover:from-rose-500 hover:to-red-500 text-white font-bold px-4 py-2.5 rounded-lg shadow-lg shadow-rose-950/50 text-xs transition active:scale-95 disabled:opacity-50"
            >
              <Swords className={`w-4 h-4 ${runningRound ? 'animate-spin' : ''}`} />
              <span>{runningRound ? 'Simulating...' : 'Run Next Round'}</span>
            </button>

            <button
              onClick={() => handleAutoRun(5)}
              disabled={runningRound || autoRunning}
              className="flex items-center space-x-1.5 bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white font-bold px-3.5 py-2.5 rounded-lg text-xs transition active:scale-95 disabled:opacity-50"
            >
              <Play className={`w-3.5 h-3.5 ${autoRunning ? 'animate-spin' : ''}`} />
              <span>{autoRunning ? 'Playing...' : 'Auto 5x'}</span>
            </button>

            <button
              onClick={handleReset}
              disabled={loading || runningRound || autoRunning}
              className="p-2.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg border border-slate-700 transition"
              title="Reset Session"
            >
              <RotateCcw className="w-4 h-4" />
            </button>
          </div>

          <span className="text-[10px] text-slate-500 font-mono">
            Round {status?.round_number ?? rounds.length} of active session
          </span>
        </div>

        {/* Right: Sentinel Defender Card */}
        <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-4 flex flex-col justify-between shadow-lg">
          <div className="flex items-center justify-between border-b border-slate-800 pb-2.5">
            <div className="flex items-center space-x-2">
              <Shield className="w-5 h-5 text-emerald-400" />
              <h4 className="text-sm font-bold text-slate-100">Sentinel (Defender)</h4>
            </div>
            <span className="text-[10px] px-2 py-0.5 rounded bg-emerald-950 text-emerald-300 border border-emerald-800 font-mono">
              Trajectory Scorer
            </span>
          </div>

          <div className="mt-3 space-y-2 text-xs">
            <div className="flex justify-between py-1 border-b border-slate-800/60">
              <span className="text-slate-400">Detection Threshold:</span>
              <span className="font-mono font-bold text-amber-400">{status?.sentinel_threshold?.toFixed(2) || '0.55'}</span>
            </div>
            <div className="flex justify-between py-1 border-b border-slate-800/60">
              <span className="text-slate-400">Trajectory Weight:</span>
              <span className="font-mono font-bold text-cyan-400">60% (R² + Regularity)</span>
            </div>
            <div className="flex justify-between py-1 border-b border-slate-800/60">
              <span className="text-slate-400">Transaction Anomaly:</span>
              <span className="font-mono font-bold text-rose-400">40% (Outlier Z-Score)</span>
            </div>
            <div className="flex justify-between py-1">
              <span className="text-slate-400">Similarity Clustering:</span>
              <span className="font-mono font-bold text-emerald-400">Cosine &ge; 0.88</span>
            </div>
          </div>
        </div>
      </div>

      {errorMsg && (
        <div className="bg-rose-950/40 border border-rose-800 text-rose-300 px-4 py-3 rounded-lg text-sm flex items-center justify-between">
          <span>{errorMsg}</span>
          <button onClick={fetchAllData} className="text-xs bg-rose-900 hover:bg-rose-800 px-2 py-1 rounded">Retry</button>
        </div>
      )}

      {/* Main Real Progression Chart */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-5 shadow-xl">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-6">
          <div>
            <h4 className="text-base font-semibold text-slate-100 flex items-center space-x-2">
              <TrendingUp className="w-5 h-5 text-cyan-400" />
              <span>Real Adversarial Progression & Interception Catch Rate</span>
            </h4>
            <p className="text-xs text-slate-400 mt-0.5">
              Live progression of Sentinel catch rate vs. Forge's mutated attacks.
            </p>
          </div>

          <div className="flex items-center space-x-2 bg-slate-950 px-3 py-1 rounded-lg border border-slate-800 text-xs font-mono">
            <span className="text-slate-400">Total Rounds:</span>
            <strong className="text-cyan-400">{rounds.length}</strong>
          </div>
        </div>

        {rounds.length === 0 ? (
          <div className="h-[280px] flex flex-col items-center justify-center text-center p-6 border border-dashed border-slate-800 rounded-xl space-y-3">
            <Swords className="w-10 h-10 text-slate-600 animate-pulse" />
            <div>
              <h5 className="text-sm font-semibold text-slate-300">No Adversarial Rounds Executed Yet</h5>
              <p className="text-xs text-slate-500 max-w-sm mt-1">
                Click "Run Next Round" or "Auto 5x" above to start the live adversarial combat loop between Forge AI and Sentinel.
              </p>
            </div>
          </div>
        ) : (
          <div className="h-[360px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData} margin={{ top: 15, right: 30, left: 10, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1E293B" />
                <XAxis 
                  dataKey="round" 
                  stroke="#64748B" 
                  tick={{ fontSize: 11, fill: '#94A3B8' }}
                />
                <YAxis 
                  domain={[0, 100]}
                  stroke="#64748B" 
                  tick={{ fontSize: 11, fill: '#94A3B8' }}
                  tickFormatter={(val) => `${val}%`}
                />
                <Tooltip 
                  content={({ active, payload, label }) => {
                    if (active && payload && payload.length) {
                      const data = payload[0].payload;
                      return (
                        <div className="bg-slate-950 border border-slate-700 p-3 rounded-lg shadow-2xl text-xs space-y-1.5 font-sans max-w-sm">
                          <div className="flex items-center justify-between border-b border-slate-800 pb-1">
                            <p className="font-bold text-slate-200">{label}</p>
                            <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                              data.outcome === 'DETECTED' ? 'bg-emerald-950 text-emerald-300 border border-emerald-800' : 'bg-rose-950 text-rose-300 border border-rose-800'
                            }`}>
                              {data.outcome}
                            </span>
                          </div>
                          <p className="text-cyan-400 font-mono font-bold">
                            Rolling Catch Rate: {data.catch_rate.toFixed(1)}%
                          </p>
                          <p className="text-slate-300 font-mono">
                            Attack Risk Score: {data.risk_score_pct.toFixed(1)}% (Threshold: {data.threshold_pct.toFixed(1)}%)
                          </p>
                          {data.mutation_description && (
                            <p className="text-purple-300 text-[11px] bg-purple-950/40 p-1.5 rounded border border-purple-800/40">
                              <strong>Forge Mutated:</strong> {data.mutation_description}
                            </p>
                          )}
                          {data.sentinel_note && (
                            <p className="text-amber-300 text-[11px]">
                              <strong>Sentinel Reaction:</strong> {data.sentinel_note}
                            </p>
                          )}
                        </div>
                      );
                    }
                    return null;
                  }}
                />
                <Legend verticalAlign="top" height={36} wrapperStyle={{ color: '#94A3B8', fontSize: '12px' }} />
                
                <ReferenceLine 
                  y={55} 
                  stroke="#475569" 
                  strokeDasharray="4 4" 
                  label={{ value: 'Sentinel Threshold (55%)', position: 'right', fill: '#64748B', fontSize: 10 }}
                />

                <Line 
                  type="monotone" 
                  dataKey="catch_rate" 
                  name="Rolling Catch Rate (%)"
                  stroke="#06B6D4" 
                  strokeWidth={3}
                  dot={{ r: 4, fill: '#06B6D4' }}
                  activeDot={{ r: 7 }}
                />

                <Line 
                  type="monotone" 
                  dataKey="risk_score_pct" 
                  name="Attack Risk Score (%)"
                  stroke="#F43F5E" 
                  strokeWidth={2}
                  strokeDasharray="2 2"
                  dot={(props) => {
                    const { cx, cy, payload } = props;
                    const isDet = payload.outcome === 'DETECTED';
                    return (
                      <circle 
                        cx={cx} 
                        cy={cy} 
                        r={5} 
                        fill={isDet ? '#10B981' : '#F43F5E'} 
                        stroke="#0F172A" 
                        strokeWidth={2} 
                        key={props.key} 
                      />
                    );
                  }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>

      {/* Round-by-Round Evolution Log Table with Expandable Row Inspector */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-xl overflow-hidden shadow-xl">
        <div className="px-5 py-4 border-b border-slate-800 flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <Cpu className="w-4 h-4 text-cyan-400" />
            <h4 className="text-sm font-semibold text-slate-200 uppercase tracking-wider">Adversarial Mutation & Interception Audit Log</h4>
          </div>
          <span className="text-xs text-slate-500 font-mono">{rounds.length} total rounds</span>
        </div>

        <div className="overflow-x-auto max-h-[440px]">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-950/80 text-slate-400 uppercase tracking-wider border-b border-slate-800 sticky top-0 z-10">
              <tr>
                <th className="py-3 px-4">Round</th>
                <th className="py-3 px-4">Outcome</th>
                <th className="py-3 px-4">Attack Risk</th>
                <th className="py-3 px-4">Forge Mutation Countermeasure</th>
                <th className="py-3 px-4">Sentinel Adaptation</th>
                <th className="py-3 px-4">Catch Rate</th>
                <th className="py-3 px-4 text-right">Details</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-sans">
              {rounds.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-8 text-center text-slate-500">
                    No rounds run yet. Click "Run Next Round" or "Auto 5x" to start the adversarial loop.
                  </td>
                </tr>
              ) : (
                rounds.map((r, i) => {
                  const isExpanded = expandedRound === i;
                  return (
                    <React.Fragment key={i}>
                      <tr 
                        className="hover:bg-slate-800/40 transition cursor-pointer"
                        onClick={() => setExpandedRound(isExpanded ? null : i)}
                      >
                        <td className="py-3 px-4 font-mono font-bold text-slate-200">
                          R{r.round_number}
                        </td>
                        <td className="py-3 px-4">
                          {r.outcome === 'DETECTED' ? (
                            <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-bold bg-emerald-950 text-emerald-300 border border-emerald-800/60">
                              DETECTED
                            </span>
                          ) : (
                            <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-bold bg-rose-950 text-rose-300 border border-rose-800/60">
                              EVADED
                            </span>
                          )}
                        </td>
                        <td className="py-3 px-4 font-mono font-bold">
                          <span className={(r.risk_score_pct ?? (r.risk_score * 100)) >= 55 ? 'text-rose-400' : 'text-emerald-400'}>
                            {(r.risk_score_pct ?? (r.risk_score * 100)).toFixed(1)}%
                          </span>
                        </td>
                        <td className="py-3 px-4 text-slate-300 max-w-xs truncate" title={r.mutation_description}>
                          {r.mutation_description || 'Initial baseline parameter set'}
                        </td>
                        <td className="py-3 px-4 text-amber-300 font-mono text-[11px]">
                          {r.sentinel_note || `Threshold: ${r.sentinel_threshold ? r.sentinel_threshold.toFixed(2) : '0.55'}`}
                        </td>
                        <td className="py-3 px-4 font-mono font-bold text-cyan-400">
                          {r.rolling_catch_rate !== undefined ? `${r.rolling_catch_rate.toFixed(1)}%` : '—'}
                        </td>
                        <td className="py-3 px-4 text-right text-slate-400">
                          {isExpanded ? <ChevronUp className="w-4 h-4 inline" /> : <ChevronDown className="w-4 h-4 inline" />}
                        </td>
                      </tr>

                      {/* Expandable Details Row */}
                      {isExpanded && (
                        <tr className="bg-slate-950/80">
                          <td colSpan={7} className="p-4 border-b border-slate-800 space-y-3">
                            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-[11px]">
                              <div className="bg-slate-900 p-2.5 rounded-lg border border-slate-800">
                                <span className="text-slate-400 font-mono uppercase font-bold">Round Summary</span>
                                <p className="text-slate-200 mt-1">{r.round_summary || 'N/A'}</p>
                              </div>
                              <div className="bg-slate-900 p-2.5 rounded-lg border border-slate-800">
                                <span className="text-slate-400 font-mono uppercase font-bold">Detection Features</span>
                                <div className="mt-1 text-slate-300 space-y-0.5 font-mono">
                                  <p>Linearity (R²): {r.features?.spend_smoothness?.toFixed(2) || 'N/A'}</p>
                                  <p>Monotonicity: {r.features?.spend_monotonicity?.toFixed(2) || 'N/A'}</p>
                                  <p>Login Regularity: {r.features?.login_regularity?.toFixed(2) || 'N/A'}</p>
                                </div>
                              </div>
                              <div className="bg-slate-900 p-2.5 rounded-lg border border-slate-800">
                                <span className="text-slate-400 font-mono uppercase font-bold">Forge Parameters Used</span>
                                <div className="mt-1 text-slate-300 space-y-0.5 font-mono">
                                  <p>Noise: {r.forge_params_used?.noise_factor?.toFixed(3) || '0.035'}</p>
                                  <p>Dip Prob: {(r.forge_params_used?.dip_probability * 100)?.toFixed(0) || '4'}%</p>
                                  <p>Surge Cap: {r.forge_params_used?.surge_multiplier_cap?.toFixed(1) || '20.0'}x</p>
                                </div>
                              </div>
                            </div>
                          </td>
                        </tr>
                      )}
                    </React.Fragment>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
