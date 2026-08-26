import React, { useState, useEffect } from 'react';
import { getTimeline, getHistory } from '../api';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  ReferenceLine,
  AreaChart,
  Area,
  Legend
} from 'recharts';
import {
  Search,
  Calendar,
  AlertTriangle,
  CheckCircle,
  TrendingUp,
  Fingerprint,
  Info,
  Clock,
  Sparkles,
  ShieldCheck,
  ShieldAlert
} from 'lucide-react';

export default function TimelineReplay({ selectedId, onSelectIdentity }) {
  const [identityId, setIdentityId] = useState(selectedId || '');
  const [timelineData, setTimelineData] = useState(null);
  const [historyList, setHistoryList] = useState([]);
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState(null);

  useEffect(() => {
    loadHistoryList();
  }, []);

  useEffect(() => {
    if (selectedId) {
      setIdentityId(selectedId);
      fetchTimeline(selectedId);
    }
  }, [selectedId]);

  const loadHistoryList = async () => {
    try {
      const list = await getHistory();
      setHistoryList(list);
      if (!identityId && list.length > 0) {
        const firstId = list[0].id;
        setIdentityId(firstId);
        fetchTimeline(firstId);
      }
    } catch (err) {
      console.error(err);
    }
  };

  const fetchTimeline = async (idToFetch) => {
    if (!idToFetch) return;
    try {
      setLoading(true);
      setErrorMsg(null);
      const data = await getTimeline(idToFetch.trim());
      setTimelineData(data);
      if (onSelectIdentity) {
        onSelectIdentity(idToFetch);
      }
    } catch (err) {
      console.error(err);
      setErrorMsg(`Could not load timeline for identity "${idToFetch}". Ensure ID exists.`);
      setTimelineData(null);
    } finally {
      setLoading(false);
    }
  };

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    fetchTimeline(identityId);
  };

  // Format data for Recharts
  const chartData = timelineData?.timeline?.map((item) => ({
    week: `W${item.week}`,
    weekNum: item.week,
    spend: item.spend,
    login_count: item.login_count,
    is_strike: item.fraud_strike,
    new_device: item.new_device,
    location_change: item.location_change,
    bill_paid_on_time: item.bill_paid_on_time
  })) || [];

  return (
    <div className="space-y-6">
      {/* Search & Selector Header */}
      <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-5 shadow-lg">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <form onSubmit={handleSearchSubmit} className="flex items-center space-x-3 flex-1 max-w-xl">
            <div className="relative flex-1">
              <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                placeholder="Enter Identity ID (e.g. VT-1024-A8F2)..."
                value={identityId}
                onChange={(e) => setIdentityId(e.target.value)}
                className="w-full bg-slate-950 border border-slate-700 rounded-lg pl-9 pr-4 py-2 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-emerald-500 font-mono"
              />
            </div>
            <button
              type="submit"
              disabled={loading || !identityId}
              className="bg-emerald-600 hover:bg-emerald-500 text-slate-950 font-bold px-4 py-2 rounded-lg text-sm transition disabled:opacity-50"
            >
              {loading ? 'Loading...' : 'Inspect'}
            </button>
          </form>

          {/* Quick Select dropdown */}
          {historyList.length > 0 && (
            <div className="flex items-center space-x-2">
              <span className="text-xs text-slate-400">Quick Select:</span>
              <select
                value={identityId}
                onChange={(e) => {
                  setIdentityId(e.target.value);
                  fetchTimeline(e.target.value);
                }}
                className="bg-slate-950 border border-slate-700 text-slate-200 text-xs rounded-lg px-3 py-2 font-mono focus:outline-none focus:border-emerald-500"
              >
                {historyList.map((h) => (
                  <option key={h.id} value={h.id}>
                    {h.id} ({h.type === 'sleeper' ? '🤖 Sleeper' : '👤 Benign'} - {h.flagged ? '🚩 Flagged' : '✅ Passed'})
                  </option>
                ))}
              </select>
            </div>
          )}
        </div>
      </div>

      {errorMsg && (
        <div className="bg-rose-950/40 border border-rose-800 text-rose-300 px-4 py-3 rounded-lg text-sm">
          {errorMsg}
        </div>
      )}

      {timelineData && (
        <>
          {/* Identity Summary Card & Forensics */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Left: Verdict Card */}
            <div className={`p-5 rounded-xl border ${
              timelineData.flagged 
                ? 'bg-rose-950/20 border-rose-800/60' 
                : 'bg-emerald-950/20 border-emerald-800/60'
            }`}>
              <div className="flex items-start justify-between">
                <div>
                  <span className="text-xs text-slate-400 font-mono">TARGET IDENTITY</span>
                  <h3 className="text-xl font-black text-slate-100 font-mono mt-0.5">{timelineData.id}</h3>
                </div>
                <div className={`p-2 rounded-lg ${
                  timelineData.flagged ? 'bg-rose-500/20 text-rose-400' : 'bg-emerald-500/20 text-emerald-400'
                }`}>
                  {timelineData.flagged ? <ShieldAlert className="w-6 h-6" /> : <ShieldCheck className="w-6 h-6" />}
                </div>
              </div>

              <div className="mt-4 space-y-2">
                <div className="flex justify-between text-xs py-1 border-b border-slate-800/60">
                  <span className="text-slate-400">Ground Truth Type:</span>
                  <span className={`font-semibold ${timelineData.type === 'sleeper' ? 'text-purple-400' : 'text-blue-400'}`}>
                    {timelineData.type === 'sleeper' ? '🤖 GenAI Sleeper Agent' : '👤 Organic Human'}
                  </span>
                </div>

                <div className="flex justify-between text-xs py-1 border-b border-slate-800/60">
                  <span className="text-slate-400">Sentinel Verdict:</span>
                  <span className={`font-bold ${timelineData.flagged ? 'text-rose-400' : 'text-emerald-400'}`}>
                    {timelineData.flagged ? '🚩 Flagged Synthetic' : '✅ Cleared Organic'}
                  </span>
                </div>

                <div className="flex justify-between text-xs py-1 border-b border-slate-800/60">
                  <span className="text-slate-400">Risk Probability:</span>
                  <span className={`font-mono font-bold ${timelineData.risk_score >= 0.65 ? 'text-rose-400' : 'text-emerald-400'}`}>
                    {(timelineData.risk_score * 100).toFixed(1)}%
                  </span>
                </div>

                <div className="flex justify-between text-xs py-1">
                  <span className="text-slate-400">Early Warning Trigger:</span>
                  <span className="font-mono font-semibold text-amber-400">
                    {timelineData.flag_week ? `Week ${timelineData.flag_week} of 24` : 'No trigger (Benign)'}
                  </span>
                </div>
              </div>

              {timelineData.flag_week && (
                <div className="mt-4 p-3 bg-amber-950/30 border border-amber-800/40 rounded-lg text-xs text-amber-200 flex items-start space-x-2">
                  <Clock className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
                  <span>
                    <strong>Early Interception:</strong> VeriTrace isolated this sleeper agent at <strong>Week {timelineData.flag_week}</strong>, protecting credit facilities {24 - timelineData.flag_week} weeks prior to terminal bust-out!
                  </span>
                </div>
              )}
            </div>

            {/* Right 2 cols: Behavioral Trajectory Forensics */}
            <div className="lg:col-span-2 bg-slate-900/80 border border-slate-800 rounded-xl p-5">
              <div className="flex items-center space-x-2 mb-4">
                <Fingerprint className="w-5 h-5 text-cyan-400" />
                <h4 className="text-sm font-semibold text-slate-200 uppercase tracking-wider">Incubation Behavioral Forensics</h4>
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <div className="bg-slate-950/70 p-3 rounded-lg border border-slate-800">
                  <p className="text-[11px] text-slate-400">Spend Linearity ($R^2$)</p>
                  <p className="text-lg font-bold font-mono text-cyan-400 mt-1">
                    {timelineData.features?.spend_smoothness !== undefined 
                      ? (timelineData.features.spend_smoothness * 100).toFixed(1) + '%' 
                      : 'N/A'}
                  </p>
                  <p className="text-[10px] text-slate-500 mt-0.5">High = Scripted Ramp</p>
                </div>

                <div className="bg-slate-950/70 p-3 rounded-lg border border-slate-800">
                  <p className="text-[11px] text-slate-400">Spend Monotonicity</p>
                  <p className="text-lg font-bold font-mono text-indigo-400 mt-1">
                    {timelineData.features?.spend_monotonicity !== undefined 
                      ? (timelineData.features.spend_monotonicity * 100).toFixed(1) + '%' 
                      : 'N/A'}
                  </p>
                  <p className="text-[10px] text-slate-500 mt-0.5">Non-decreasing spend %</p>
                </div>

                <div className="bg-slate-950/70 p-3 rounded-lg border border-slate-800">
                  <p className="text-[11px] text-slate-400">Login Regularity</p>
                  <p className="text-lg font-bold font-mono text-amber-400 mt-1">
                    {timelineData.features?.login_regularity !== undefined 
                      ? (timelineData.features.login_regularity * 100).toFixed(1) + '%' 
                      : 'N/A'}
                  </p>
                  <p className="text-[10px] text-slate-500 mt-0.5">Robotic session timing</p>
                </div>

                <div className="bg-slate-950/70 p-3 rounded-lg border border-slate-800">
                  <p className="text-[11px] text-slate-400">Variance Score</p>
                  <p className="text-lg font-bold font-mono text-emerald-400 mt-1">
                    {timelineData.features?.variance_score !== undefined 
                      ? timelineData.features.variance_score.toFixed(3) 
                      : 'N/A'}
                  </p>
                  <p className="text-[10px] text-slate-500 mt-0.5">Human noise index</p>
                </div>
              </div>

              <div className="mt-4 p-3 bg-slate-950/50 rounded-lg border border-slate-800 text-xs text-slate-300">
                <p className="leading-relaxed">
                  <strong className="text-slate-100">Forensic Trajectory Analysis:</strong> Real human spending shows organic variance, holiday dips, and fluctuating login hours. In contrast, GenAI sleeper agents follow an <em>uncanny monotonic linear ascent</em> with robotic regularity to establish creditworthiness before executing a terminal bust-out strike.
                </p>
              </div>
            </div>
          </div>

          {/* Recharts Trajectory Visualizer */}
          <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-5 shadow-xl">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-6">
              <div>
                <h4 className="text-base font-semibold text-slate-100 flex items-center space-x-2">
                  <TrendingUp className="w-5 h-5 text-emerald-400" />
                  <span>24-Week Spend & Incubation Trajectory Replay</span>
                </h4>
                <p className="text-xs text-slate-400 mt-0.5">
                  Visualizing weekly spend ($) with sentinel early-warning marker and terminal strike zone
                </p>
              </div>

              {timelineData.flag_week && (
                <div className="flex items-center space-x-2 bg-rose-950/50 border border-rose-800/80 px-3 py-1.5 rounded-lg text-xs text-rose-300">
                  <div className="w-2.5 h-2.5 rounded-full bg-rose-500 animate-ping" />
                  <span className="font-mono">Sentinel Flagged at Week {timelineData.flag_week}</span>
                </div>
              )}
            </div>

            {/* Spend Line Chart */}
            <div className="h-[360px] w-full">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={chartData} margin={{ top: 15, right: 30, left: 10, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1E293B" />
                  <XAxis 
                    dataKey="week" 
                    stroke="#64748B" 
                    tick={{ fontSize: 11, fill: '#94A3B8' }}
                  />
                  <YAxis 
                    stroke="#64748B" 
                    tick={{ fontSize: 11, fill: '#94A3B8' }}
                    tickFormatter={(val) => `$${val >= 1000 ? (val/1000).toFixed(1) + 'k' : val}`}
                  />
                  <Tooltip 
                    content={({ active, payload, label }) => {
                      if (active && payload && payload.length) {
                        const data = payload[0].payload;
                        return (
                          <div className="bg-slate-950 border border-slate-700 p-3 rounded-lg shadow-2xl text-xs space-y-1 font-sans">
                            <p className="font-bold text-slate-200 border-b border-slate-800 pb-1">{label} (Week {data.weekNum})</p>
                            <p className="text-emerald-400 font-mono">Weekly Spend: ${data.spend.toLocaleString()}</p>
                            <p className="text-cyan-400 font-mono">Logins: {data.login_count} sessions</p>
                            <p className="text-slate-400">Bill Paid on Time: {data.bill_paid_on_time ? '✅ Yes' : '❌ No'}</p>
                            {data.is_strike && (
                              <p className="text-rose-400 font-bold bg-rose-950/80 px-2 py-0.5 rounded border border-rose-800">
                                💥 TERMINAL FRAUD STRIKE (Bust-out)
                              </p>
                            )}
                          </div>
                        );
                      }
                      return null;
                    }}
                  />
                  <Legend verticalAlign="top" height={36} wrapperStyle={{ color: '#94A3B8', fontSize: '12px' }} />

                  {/* Flag Week Reference Line */}
                  {timelineData.flag_week && (
                    <ReferenceLine 
                      x={`W${timelineData.flag_week}`} 
                      stroke="#F43F5E" 
                      strokeWidth={2}
                      strokeDasharray="4 4"
                      label={{ 
                        value: `🚩 Flagged (W${timelineData.flag_week})`, 
                        position: 'top', 
                        fill: '#F43F5E', 
                        fontSize: 11,
                        fontWeight: 'bold'
                      }} 
                    />
                  )}

                  <Line 
                    type="monotone" 
                    dataKey="spend" 
                    name="Weekly Spend ($)"
                    stroke="#10B981" 
                    strokeWidth={2.5}
                    dot={(props) => {
                      const { cx, cy, payload } = props;
                      if (payload.is_strike) {
                        return (
                          <circle cx={cx} cy={cy} r={6} fill="#F43F5E" stroke="#FFF" strokeWidth={2} key={props.key} />
                        );
                      }
                      if (payload.weekNum === timelineData.flag_week) {
                        return (
                          <circle cx={cx} cy={cy} r={6} fill="#F59E0B" stroke="#FFF" strokeWidth={2} key={props.key} />
                        );
                      }
                      return <circle cx={cx} cy={cy} r={3} fill="#10B981" key={props.key} />;
                    }}
                    activeDot={{ r: 7 }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
