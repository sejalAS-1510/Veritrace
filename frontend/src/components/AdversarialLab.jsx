import React, { useState, useEffect, useRef } from 'react';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  ReferenceLine,
  Legend,
} from 'recharts';
import {
  Swords,
  ShieldAlert,
  ShieldCheck,
  Zap,
  RefreshCw,
  ChevronRight,
  BarChart2,
  Bot,
  Shield,
  Activity,
  AlertTriangle,
  CheckCircle,
  Info,
} from 'lucide-react';
import { runAdversarialRound, resetAdversarialSession, getAdversarialRounds, getMetrics } from '../api';

// ── Outcome badge ──────────────────────────────────────────────────────────────
function OutcomeBadge({ outcome }) {
  if (outcome === 'DETECTED') {
    return (
      <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-emerald-950 text-emerald-300 border border-emerald-800">
        <ShieldCheck className="w-3 h-3" />
        <span>DETECTED</span>
      </span>
    );
  }
  return (
    <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-rose-950 text-rose-300 border border-rose-800">
      <ShieldAlert className="w-3 h-3" />
      <span>EVADED</span>
    </span>
  );
}

// ── Risk bar ───────────────────────────────────────────────────────────────────
function RiskBar({ pct }) {
  const color = pct >= 65 ? 'bg-rose-500' : pct >= 40 ? 'bg-amber-500' : 'bg-emerald-500';
  return (
    <div className="flex items-center space-x-2">
      <div className="w-24 bg-slate-800 rounded-full h-2 overflow-hidden">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${Math.min(100, pct)}%` }} />
      </div>
      <span className={`font-mono font-bold text-xs ${pct >= 65 ? 'text-rose-400' : 'text-emerald-400'}`}>
        {pct}%
      </span>
    </div>
  );
}

// ── Stat tile ──────────────────────────────────────────────────────────────────
function StatTile({ label, value, sub, color = 'text-slate-100', icon: Icon, iconColor }) {
  return (
    <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4 flex items-center justify-between">
      <div>
        <p className="text-xs text-slate-400 uppercase tracking-wider">{label}</p>
        <p className={`text-2xl font-black font-mono mt-1 ${color}`}>{value ?? '—'}</p>
        {sub && <p className="text-[11px] text-slate-500 mt-0.5">{sub}</p>}
      </div>
      {Icon && (
        <div className={`p-3 rounded-lg bg-slate-800 ${iconColor ?? 'text-slate-300'}`}>
          <Icon className="w-5 h-5" />
        </div>
      )}
    </div>
  );
}

export default function AdversarialLab() {
  const [rounds, setRounds] = useState([]);
  const [metrics, setMetrics] = useState(null);
  const [latest, setLatest] = useState(null);
  const [running, setRunning] = useState(false);
  const [resetting, setResetting] = useState(false);
  const [error, setError] = useState(null);
  const bottomRef = useRef(null);

  // Load initial demo rounds + metrics
  useEffect(() => {
    loadRounds();
    loadMetrics();
  }, []);

  // Auto-scroll to latest round
  useEffect(() => {
    if (bottomRef.current) {
      bottomRef.current.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
  }, [rounds]);

  async function loadRounds() {
    try {
      const data = await getAdversarialRounds();
      setRounds(data);
      if (data.length > 0) setLatest(data[data.length - 1]);
    } catch (e) {
      console.error(e);
    }
  }

  async function loadMetrics() {
    try {
      const data = await getMetrics();
      setMetrics(data);
    } catch (e) {
      console.error(e);
    }
  }

  async function handleRunRound() {
    try {
      setRunning(true);
      setError(null);
      const result = await runAdversarialRound();
      setRounds((prev) => [...prev, result]);
      setLatest(result);
      await loadMetrics();
    } catch (e) {
      console.error(e);
      setError('Failed to run adversarial round. Is the backend running on port 8000?');
    } finally {
      setRunning(false);
    }
  }

  async function handleReset() {
    try {
      setResetting(true);
      setError(null);
      await resetAdversarialSession();
      setRounds([]);
      setLatest(null);
      setMetrics(null);
      await loadRounds();
    } catch (e) {
      console.error(e);
      setError('Reset failed. Is the backend running?');
    } finally {
      setResetting(false);
    }
  }

  // Chart data — catch rate over rounds
  const chartData = rounds.map((r) => ({
    round: `R${r.round_number}`,
    roundNum: r.round_number,
    catch_rate: r.rolling_catch_rate ?? (r.outcome === 'DETECTED' ? 100 : 0),
    risk_pct: r.risk_score_pct,
    adversarial_score: r.adversarial_score,
    outcome: r.outcome,
  }));

  // Count totals from live data
  const totalRounds = rounds.filter((r) => r.round_number !== undefined || r.outcome).length;
  const detectedCount = rounds.filter((r) => r.outcome === 'DETECTED').length;
  const evadedCount = rounds.filter((r) => r.outcome === 'EVADED').length;
  const catchRateLive =
    totalRounds > 0 ? ((detectedCount / totalRounds) * 100).toFixed(1) : null;

  return (
    <div className="space-y-6">
      {/* ── Header + Controls ──────────────────────────────────────────────── */}
      <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-5 shadow-lg">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="flex items-center space-x-3">
            <div className="p-2.5 bg-rose-500/10 border border-rose-500/30 rounded-lg text-rose-400">
              <Swords className="w-6 h-6" />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-slate-100">
                🔴 FORGE vs 🔵 SENTINEL — Live Adversarial Lab
              </h3>
              <p className="text-xs text-slate-400">
                Each round: Forge generates a mutated sleeper attack → Sentinel evaluates →
                feedback drives next mutation. Watch the arms race unfold.
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3 flex-wrap">
            <button
              onClick={handleRunRound}
              disabled={running}
              className="flex items-center space-x-2 bg-gradient-to-r from-rose-600 to-rose-700 hover:from-rose-500 hover:to-rose-600 text-white font-bold px-5 py-2.5 rounded-lg shadow-lg transition active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Zap className={`w-4 h-4 ${running ? 'animate-spin' : ''}`} />
              <span>{running ? 'Running...' : '⚡ Run Next Round'}</span>
            </button>

            <button
              onClick={handleReset}
              disabled={resetting}
              className="flex items-center space-x-2 bg-slate-800 hover:bg-slate-700 text-slate-300 text-sm px-4 py-2.5 rounded-lg border border-slate-700 transition disabled:opacity-50"
            >
              <RefreshCw className={`w-4 h-4 ${resetting ? 'animate-spin' : ''}`} />
              <span>Reset Session</span>
            </button>
          </div>
        </div>
      </div>

      {error && (
        <div className="bg-rose-950/40 border border-rose-800 text-rose-300 px-4 py-3 rounded-lg text-sm flex items-center space-x-2">
          <AlertTriangle className="w-4 h-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* ── Stat tiles ────────────────────────────────────────────────────── */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatTile
          label="Rounds Run"
          value={totalRounds}
          icon={Activity}
          iconColor="text-cyan-400"
        />
        <StatTile
          label="Attacks Detected"
          value={detectedCount}
          color="text-emerald-400"
          icon={ShieldCheck}
          iconColor="text-emerald-400"
        />
        <StatTile
          label="Attacks Evaded"
          value={evadedCount}
          color="text-rose-400"
          icon={ShieldAlert}
          iconColor="text-rose-400"
        />
        <StatTile
          label="Live Catch Rate"
          value={catchRateLive !== null ? `${catchRateLive}%` : '—'}
          color={
            catchRateLive !== null
              ? Number(catchRateLive) >= 75
                ? 'text-emerald-400'
                : 'text-amber-400'
              : 'text-slate-400'
          }
          icon={BarChart2}
          iconColor="text-indigo-400"
        />
      </div>

      {/* ── Latest Round Spotlight ────────────────────────────────────────── */}
      {latest && (
        <div
          className={`p-5 rounded-xl border transition-all ${
            latest.outcome === 'DETECTED'
              ? 'bg-gradient-to-r from-emerald-950/40 via-slate-900 to-slate-900 border-emerald-800/60'
              : 'bg-gradient-to-r from-rose-950/40 via-slate-900 to-slate-900 border-rose-800/60'
          }`}
        >
          <div className="flex flex-col md:flex-row md:items-start justify-between gap-4">
            <div className="space-y-2 flex-1">
              <div className="flex items-center space-x-3">
                <span className="text-sm font-bold text-slate-300 font-mono">
                  Round {latest.round_number}
                </span>
                <OutcomeBadge outcome={latest.outcome} />
                {latest.identity_id && (
                  <span className="text-xs text-slate-500 font-mono">{latest.identity_id}</span>
                )}
              </div>
              <p className="text-xs text-slate-400 leading-relaxed max-w-2xl">
                {latest.round_summary}
              </p>
              {latest.mutation_description && (
                <div className="flex items-start space-x-2 mt-2 bg-slate-950/60 px-3 py-2 rounded-lg border border-slate-800 text-xs">
                  <Bot className="w-3.5 h-3.5 text-rose-400 shrink-0 mt-0.5" />
                  <span className="text-slate-300">
                    <strong className="text-rose-400">Forge mutates:</strong>{' '}
                    {latest.mutation_description}
                  </span>
                </div>
              )}
            </div>

            {/* Right: Risk + Features */}
            <div className="md:min-w-[200px] space-y-3">
              <div className="text-right">
                <p className="text-xs text-slate-400">Risk Score</p>
                <p
                  className={`text-3xl font-black font-mono ${
                    (latest.risk_score_pct ?? latest.risk_score * 100) >= 65
                      ? 'text-rose-400'
                      : 'text-emerald-400'
                  }`}
                >
                  {latest.risk_score_pct ?? (latest.risk_score * 100)?.toFixed(1)}
                  <span className="text-base">/100</span>
                </p>
              </div>
              {latest.features && (
                <div className="grid grid-cols-2 gap-1.5">
                  {Object.entries(latest.features).map(([key, val]) => (
                    <div key={key} className="bg-slate-950/60 px-2 py-1.5 rounded border border-slate-800">
                      <p className="text-[9px] text-slate-500 uppercase tracking-wide">
                        {key.replace(/_/g, ' ')}
                      </p>
                      <p className="text-xs font-mono font-bold text-slate-300">
                        {(val * 100).toFixed(0)}%
                      </p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* ── Arms Race Chart ───────────────────────────────────────────────── */}
      {chartData.length > 0 && (
        <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-5 shadow-xl">
          <div className="flex items-center justify-between mb-5">
            <div>
              <h4 className="text-base font-semibold text-slate-100 flex items-center space-x-2">
                <Activity className="w-5 h-5 text-cyan-400" />
                <span>Live Arms Race — Catch Rate vs. Round</span>
              </h4>
              <p className="text-xs text-slate-400 mt-0.5">
                Sentinel catch rate drops when Forge mutates successfully; recovers as Sentinel adapts.
              </p>
            </div>
          </div>

          <div className="h-[300px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData} margin={{ top: 10, right: 30, left: 10, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1E293B" />
                <XAxis dataKey="round" stroke="#64748B" tick={{ fontSize: 11, fill: '#94A3B8' }} />
                <YAxis
                  domain={[0, 100]}
                  stroke="#64748B"
                  tick={{ fontSize: 11, fill: '#94A3B8' }}
                  tickFormatter={(v) => `${v}%`}
                />
                <Tooltip
                  content={({ active, payload, label }) => {
                    if (active && payload && payload.length) {
                      const d = payload[0].payload;
                      return (
                        <div className="bg-slate-950 border border-slate-700 p-3 rounded-lg shadow-2xl text-xs space-y-1">
                          <p className="font-bold text-slate-200 border-b border-slate-800 pb-1">{label}</p>
                          <p className="text-cyan-400 font-mono">
                            Catch Rate: {d.catch_rate}%
                          </p>
                          <p className="text-amber-400 font-mono">
                            Risk Score: {d.risk_pct}%
                          </p>
                          <p
                            className={
                              d.outcome === 'DETECTED' ? 'text-emerald-400' : 'text-rose-400'
                            }
                          >
                            {d.outcome === 'DETECTED' ? '✅ Detected' : '🚨 Evaded'}
                          </p>
                        </div>
                      );
                    }
                    return null;
                  }}
                />
                <Legend verticalAlign="top" height={32} wrapperStyle={{ color: '#94A3B8', fontSize: '12px' }} />
                <ReferenceLine
                  y={75}
                  stroke="#475569"
                  strokeDasharray="4 4"
                  label={{ value: 'Target (75%)', position: 'right', fill: '#64748B', fontSize: 10 }}
                />
                <Line
                  type="monotone"
                  dataKey="catch_rate"
                  name="Sentinel Catch Rate (%)"
                  stroke="#06B6D4"
                  strokeWidth={3}
                  dot={(props) => {
                    const { cx, cy, payload } = props;
                    const fill = payload.outcome === 'DETECTED' ? '#10B981' : '#F43F5E';
                    return (
                      <circle
                        key={props.key}
                        cx={cx}
                        cy={cy}
                        r={5}
                        fill={fill}
                        stroke="#0F172A"
                        strokeWidth={2}
                      />
                    );
                  }}
                  activeDot={{ r: 8 }}
                />
                <Line
                  type="monotone"
                  dataKey="risk_pct"
                  name="Attack Risk Score (%)"
                  stroke="#F59E0B"
                  strokeWidth={2}
                  strokeDasharray="5 3"
                  dot={false}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* ── Metrics Panel ─────────────────────────────────────────────────── */}
      {metrics && metrics.total_rounds > 0 && (
        <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-5 shadow-xl">
          <div className="flex items-center space-x-2 mb-4">
            <BarChart2 className="w-5 h-5 text-indigo-400" />
            <h4 className="text-sm font-semibold text-slate-200 uppercase tracking-wider">
              Performance Metrics
            </h4>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="bg-slate-950/70 p-3 rounded-lg border border-slate-800">
              <p className="text-[11px] text-slate-400 uppercase">Detection Rate</p>
              <p className="text-xl font-black font-mono text-emerald-400 mt-1">
                {metrics.detection_rate_pct}%
              </p>
              <p className="text-[10px] text-slate-500 mt-0.5">Recall</p>
            </div>
            <div className="bg-slate-950/70 p-3 rounded-lg border border-slate-800">
              <p className="text-[11px] text-slate-400 uppercase">Evasion Rate</p>
              <p className="text-xl font-black font-mono text-rose-400 mt-1">
                {metrics.evasion_rate_pct}%
              </p>
              <p className="text-[10px] text-slate-500 mt-0.5">Missed attacks</p>
            </div>
            <div className="bg-slate-950/70 p-3 rounded-lg border border-slate-800">
              <p className="text-[11px] text-slate-400 uppercase">F1 Score</p>
              <p className="text-xl font-black font-mono text-cyan-400 mt-1">
                {metrics.f1_score?.toFixed(2) ?? '—'}
              </p>
              <p className="text-[10px] text-slate-500 mt-0.5">Harmonic mean</p>
            </div>
            <div className="bg-slate-950/70 p-3 rounded-lg border border-slate-800">
              <p className="text-[11px] text-slate-400 uppercase">Avg Flag Week</p>
              <p className="text-xl font-black font-mono text-amber-400 mt-1">
                {metrics.avg_flag_week ? `W${metrics.avg_flag_week}` : '—'}
              </p>
              <p className="text-[10px] text-slate-500 mt-0.5">Early warning</p>
            </div>
          </div>
        </div>
      )}

      {/* ── Round History Table ───────────────────────────────────────────── */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-xl overflow-hidden shadow-xl">
        <div className="px-5 py-4 border-b border-slate-800 flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <Swords className="w-4 h-4 text-rose-400" />
            <h4 className="text-sm font-semibold text-slate-200 uppercase tracking-wider">
              Round-by-Round History
            </h4>
          </div>
          <span className="text-xs text-slate-500 font-mono">{totalRounds} rounds</span>
        </div>

        <div className="overflow-x-auto max-h-[480px]">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-950/80 text-slate-400 uppercase tracking-wider border-b border-slate-800 sticky top-0 z-10">
              <tr>
                <th className="py-3 px-4">Round</th>
                <th className="py-3 px-4">Outcome</th>
                <th className="py-3 px-4">Risk Score</th>
                <th className="py-3 px-4">Catch Rate</th>
                <th className="py-3 px-4">Forge Mutation</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {rounds.length === 0 && (
                <tr>
                  <td colSpan={5} className="py-8 text-center text-slate-500">
                    No rounds yet. Click "⚡ Run Next Round" to start the adversarial loop.
                  </td>
                </tr>
              )}
              {rounds.map((r, idx) => (
                <tr key={idx} className="hover:bg-slate-800/40 transition">
                  <td className="py-3 px-4 font-mono font-bold text-slate-200">
                    Round {r.round_number}
                  </td>
                  <td className="py-3 px-4">
                    <OutcomeBadge outcome={r.outcome} />
                  </td>
                  <td className="py-3 px-4">
                    <RiskBar pct={r.risk_score_pct ?? Math.round((r.risk_score ?? 0) * 100)} />
                  </td>
                  <td className="py-3 px-4 font-mono text-cyan-400 font-semibold">
                    {r.rolling_catch_rate !== undefined ? `${r.rolling_catch_rate}%` : '—'}
                  </td>
                  <td className="py-3 px-4 text-slate-400 text-[11px] max-w-xs truncate" title={r.mutation_description}>
                    {r.mutation_description || '—'}
                  </td>
                </tr>
              ))}
              <tr>
                <td colSpan={5} ref={bottomRef} className="h-0 p-0 border-0" />
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      {/* ── Help note ─────────────────────────────────────────────────────── */}
      <div className="flex items-start space-x-3 bg-slate-900/60 border border-slate-800 rounded-xl p-4 text-xs text-slate-400">
        <Info className="w-4 h-4 text-cyan-400 shrink-0 mt-0.5" />
        <p>
          <strong className="text-slate-300">How the loop works:</strong> Each round,{' '}
          <span className="text-rose-400">Forge</span> generates a mutated sleeper identity.{' '}
          <span className="text-cyan-400">Sentinel</span> scores its trajectory. If detected,
          the mutation engine targets the specific signals that gave it away (spend linearity,
          monotonicity, login regularity). After enough rounds, watch evasion rates dip then
          recover as both sides evolve.
        </p>
      </div>
    </div>
  );
}
