import React, { useState, useEffect } from 'react';
import { getRounds } from '../api';
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
import { Swords, ShieldAlert, Zap, TrendingUp, RefreshCw, Cpu, Award } from 'lucide-react';

export default function ArmsRaceChart() {
  const [rounds, setRounds] = useState([]);
  const [loading, setLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState(null);

  useEffect(() => {
    fetchRoundsData();
  }, []);

  const fetchRoundsData = async () => {
    try {
      setLoading(true);
      setErrorMsg(null);
      const data = await getRounds();
      setRounds(data);
    } catch (err) {
      console.error(err);
      setErrorMsg('Failed to load arms race data from Sentinel API.');
    } finally {
      setLoading(false);
    }
  };

  const chartData = rounds.map((r) => ({
    round: `Round ${r.round}`,
    roundNum: r.round,
    catch_rate: r.catch_rate,
    stage: r.stage,
    adversary_strategy: r.adversary_strategy
  }));

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-5 shadow-lg flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex items-center space-x-3">
          <div className="p-2.5 bg-rose-500/10 border border-rose-500/30 rounded-lg text-rose-400">
            <Swords className="w-6 h-6" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-slate-100">Adversarial Arms Race Simulation</h3>
            <p className="text-xs text-slate-400">
              Simulating iterative adaptation cycles: GenAI Sleeper Prompt Tuning vs. VeriTrace Sentinel Forensics
            </p>
          </div>
        </div>

        <button
          onClick={fetchRoundsData}
          className="flex items-center space-x-2 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs px-3.5 py-2 rounded-lg border border-slate-700 transition"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          <span>Reload Simulation</span>
        </button>
      </div>

      {errorMsg && (
        <div className="bg-rose-950/40 border border-rose-800 text-rose-300 px-4 py-3 rounded-lg text-sm">
          {errorMsg}
        </div>
      )}

      {/* Main Chart */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-5 shadow-xl">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-6">
          <div>
            <h4 className="text-base font-semibold text-slate-100 flex items-center space-x-2">
              <TrendingUp className="w-5 h-5 text-cyan-400" />
              <span>Sentinel Interception Rate vs. Adversarial Evolution (10 Rounds)</span>
            </h4>
            <p className="text-xs text-slate-400 mt-0.5">
              Notice the evasion dip (Rounds 4-5) when LLM agents inject noise, followed by Sentinel recovery via Trajectory $R^2$ & Cosine Graphing.
            </p>
          </div>

          <div className="flex items-center space-x-2 bg-emerald-950/40 border border-emerald-800/60 px-3 py-1 rounded-lg text-xs text-emerald-300 font-mono">
            <Award className="w-4 h-4 text-emerald-400" />
            <span>Peak Accuracy: 96.8%</span>
          </div>
        </div>

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
                domain={[40, 100]}
                stroke="#64748B" 
                tick={{ fontSize: 11, fill: '#94A3B8' }}
                tickFormatter={(val) => `${val}%`}
              />
              <Tooltip 
                content={({ active, payload, label }) => {
                  if (active && payload && payload.length) {
                    const data = payload[0].payload;
                    return (
                      <div className="bg-slate-950 border border-slate-700 p-3 rounded-lg shadow-2xl text-xs space-y-1.5 font-sans">
                        <p className="font-bold text-slate-200 border-b border-slate-800 pb-1">{label}: {data.stage}</p>
                        <p className="text-cyan-400 font-mono font-bold text-sm">
                          Interception Rate: {data.catch_rate}%
                        </p>
                        <p className="text-rose-300">
                          <strong>Adversary Move:</strong> {data.adversary_strategy}
                        </p>
                      </div>
                    );
                  }
                  return null;
                }}
              />
              <Legend verticalAlign="top" height={36} wrapperStyle={{ color: '#94A3B8', fontSize: '12px' }} />
              
              {/* Reference line for baseline acceptable threshold */}
              <ReferenceLine 
                y={75} 
                stroke="#475569" 
                strokeDasharray="4 4" 
                label={{ value: 'Target Baseline (75%)', position: 'right', fill: '#64748B', fontSize: 10 }}
              />

              <Line 
                type="monotone" 
                dataKey="catch_rate" 
                name="Sentinel Interception Catch Rate (%)"
                stroke="#06B6D4" 
                strokeWidth={3}
                dot={{ r: 5, fill: '#06B6D4', stroke: '#0F172A', strokeWidth: 2 }}
                activeDot={{ r: 8, fill: '#38BDF8' }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Rounds Table / Timeline Breakdown */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-xl overflow-hidden shadow-xl">
        <div className="px-5 py-4 border-b border-slate-800 flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <Cpu className="w-4 h-4 text-cyan-400" />
            <h4 className="text-sm font-semibold text-slate-200 uppercase tracking-wider">Round-by-Round Adversarial Evolution Log</h4>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-950/80 text-slate-400 uppercase tracking-wider border-b border-slate-800">
              <tr>
                <th className="py-3 px-4">Round</th>
                <th className="py-3 px-4">Sentinel Stage</th>
                <th className="py-3 px-4">Adversary Tactics / Prompt Strategy</th>
                <th className="py-3 px-4">Catch Rate</th>
                <th className="py-3 px-4">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-sans">
              {rounds.map((r) => (
                <tr key={r.round} className="hover:bg-slate-800/40 transition">
                  <td className="py-3 px-4 font-mono font-bold text-slate-200">
                    Round {r.round}
                  </td>
                  <td className="py-3 px-4 font-semibold text-slate-300">
                    {r.stage}
                  </td>
                  <td className="py-3 px-4 text-slate-400">
                    {r.adversary_strategy}
                  </td>
                  <td className="py-3 px-4 font-mono font-bold">
                    <span className={r.catch_rate >= 80 ? 'text-emerald-400' : r.catch_rate >= 60 ? 'text-amber-400' : 'text-rose-400'}>
                      {r.catch_rate}%
                    </span>
                  </td>
                  <td className="py-3 px-4">
                    {r.catch_rate >= 80 ? (
                      <span className="text-[11px] px-2 py-0.5 rounded bg-emerald-950 text-emerald-300 border border-emerald-800/50">
                        Sentinel Dominant
                      </span>
                    ) : r.catch_rate >= 60 ? (
                      <span className="text-[11px] px-2 py-0.5 rounded bg-amber-950 text-amber-300 border border-amber-800/50">
                        Evolving
                      </span>
                    ) : (
                      <span className="text-[11px] px-2 py-0.5 rounded bg-rose-950 text-rose-300 border border-rose-800/50">
                        Adversary Breakthrough
                      </span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
