import React, { useState, useEffect, useRef } from 'react';
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
  ShieldAlert,
  Play,
  Pause,
  RotateCcw,
  SkipForward,
  SkipBack,
  FileText,
  Copy,
  Check,
  Eye,
  Sliders,
  ListFilter,
  BarChart3,
  Smartphone,
  CreditCard,
  MapPin
} from 'lucide-react';

export default function TimelineReplay({ selectedId, onSelectIdentity, showToast }) {
  const [identityId, setIdentityId] = useState(selectedId || '');
  const [timelineData, setTimelineData] = useState(null);
  const [historyList, setHistoryList] = useState([]);
  const [chartView, setChartView] = useState('spend'); // 'spend', 'logins', 'events'
  const [showOrganicBaseline, setShowOrganicBaseline] = useState(false);
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState(null);

  // Scrubber & Replay Player state
  const [currentPlaybackWeek, setCurrentPlaybackWeek] = useState(24);
  const [isPlaying, setIsPlaying] = useState(false);
  const playIntervalRef = useRef(null);

  // Selected Point Inspector
  const [selectedPoint, setSelectedPoint] = useState(null);
  const [copiedId, setCopiedId] = useState(false);

  useEffect(() => {
    loadHistoryList();
    return () => {
      if (playIntervalRef.current) clearInterval(playIntervalRef.current);
    };
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
      if (playIntervalRef.current) clearInterval(playIntervalRef.current);
      setIsPlaying(false);

      const data = await getTimeline(idToFetch.trim());
      setTimelineData(data);
      setCurrentPlaybackWeek(data.weeks_count || 24);
      setSelectedPoint(null);
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

  // Play / Pause Scrubber
  const togglePlay = () => {
    if (isPlaying) {
      if (playIntervalRef.current) clearInterval(playIntervalRef.current);
      setIsPlaying(false);
    } else {
      if (currentPlaybackWeek >= (timelineData?.weeks_count || 24)) {
        setCurrentPlaybackWeek(1);
      }
      setIsPlaying(true);
      playIntervalRef.current = setInterval(() => {
        setCurrentPlaybackWeek((prev) => {
          const maxWeeks = timelineData?.weeks_count || 24;
          if (prev >= maxWeeks) {
            clearInterval(playIntervalRef.current);
            setIsPlaying(false);
            return maxWeeks;
          }
          return prev + 1;
        });
      }, 350);
    }
  };

  const resetScrubber = () => {
    if (playIntervalRef.current) clearInterval(playIntervalRef.current);
    setIsPlaying(false);
    setCurrentPlaybackWeek(1);
  };

  // Sliced timeline data for animated playback scrubber
  const rawTimeline = timelineData?.timeline || [];
  const activeTimeline = rawTimeline.slice(0, currentPlaybackWeek);

  const chartData = activeTimeline.map((item) => {
    const organicSpendBaseline = Math.round(350 + 40 * Math.sin(item.week * 0.8) + (item.week % 4 === 0 ? 120 : -30));
    return {
      week: `W${item.week}`,
      weekNum: item.week,
      spend: item.spend,
      login_count: item.login_count,
      organic_ref: showOrganicBaseline ? organicSpendBaseline : undefined,
      is_strike: item.fraud_strike,
      new_device: item.new_device,
      location_change: item.location_change,
      bill_paid_on_time: item.bill_paid_on_time
    };
  });

  const riskPct = timelineData?.risk_score_pct ?? (timelineData?.risk_score ? timelineData.risk_score * 100 : 0);
  const isTriggeredAtCurrentWeek = timelineData?.flag_week && currentPlaybackWeek >= timelineData.flag_week;

  const copyId = () => {
    if (!timelineData?.id) return;
    navigator.clipboard.writeText(timelineData.id);
    setCopiedId(true);
    setTimeout(() => setCopiedId(false), 2000);
    if (showToast) showToast(`Copied ${timelineData.id}`, 'info');
  };

  // Feature meters helper
  const features = timelineData?.features || {};

  return (
    <div className="space-y-6">
      {/* Search & Selector Header */}
      <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-4 sm:p-5 shadow-lg">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <form onSubmit={handleSearchSubmit} className="flex items-center space-x-2 sm:space-x-3 flex-1 max-w-xl">
            <div className="relative flex-1">
              <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                placeholder="Enter Identity ID (e.g. VT-1024-A8F2)..."
                value={identityId}
                onChange={(e) => setIdentityId(e.target.value)}
                className="w-full bg-slate-950 border border-slate-700 rounded-lg pl-9 pr-4 py-2 text-xs sm:text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-emerald-500 font-mono"
              />
            </div>
            <button
              type="submit"
              disabled={loading || !identityId}
              className="bg-emerald-600 hover:bg-emerald-500 text-slate-950 font-bold px-3 sm:px-4 py-2 rounded-lg text-xs sm:text-sm transition disabled:opacity-50"
            >
              {loading ? 'Loading...' : 'Inspect'}
            </button>
          </form>

          {/* Quick Select dropdown */}
          {historyList.length > 0 && (
            <div className="flex items-center space-x-2">
              <span className="text-xs text-slate-400 whitespace-nowrap hidden sm:inline">History:</span>
              <select
                value={identityId}
                onChange={(e) => {
                  setIdentityId(e.target.value);
                  fetchTimeline(e.target.value);
                }}
                className="bg-slate-950 border border-slate-700 text-slate-200 text-xs rounded-lg px-3 py-2 font-mono focus:outline-none focus:border-emerald-500 w-full sm:max-w-xs truncate"
              >
                {historyList.map((h) => (
                  <option key={h.id} value={h.id}>
                    {h.id} — {h.type === 'sleeper' ? 'Sleeper' : 'Organic'} ({h.flagged ? 'Flagged' : 'Passed'})
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
            <div className={`p-4 sm:p-5 rounded-xl border flex flex-col justify-between shadow-lg ${
              timelineData.flagged 
                ? 'bg-rose-950/20 border-rose-800/60' 
                : 'bg-emerald-950/20 border-emerald-800/60'
            }`}>
              <div>
                <div className="flex items-start justify-between">
                  <div>
                    <span className="text-[10px] text-slate-400 font-mono tracking-wider">TELEMETRY TARGET</span>
                    <div className="flex items-center space-x-2 mt-0.5">
                      <h3 className="text-lg sm:text-xl font-black text-slate-100 font-mono">{timelineData.id}</h3>
                      <button onClick={copyId} className="text-slate-400 hover:text-white" title="Copy ID">
                        {copiedId ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                      </button>
                    </div>
                  </div>
                  <div className={`p-2 rounded-lg ${
                    timelineData.flagged ? 'bg-rose-500/20 text-rose-400' : 'bg-emerald-500/20 text-emerald-400'
                  }`}>
                    {timelineData.flagged ? <ShieldAlert className="w-6 h-6" /> : <ShieldCheck className="w-6 h-6" />}
                  </div>
                </div>

                <div className="mt-4 space-y-2">
                  <div className="flex justify-between text-xs py-1 border-b border-slate-800/60">
                    <span className="text-slate-400">Ground Truth:</span>
                    <span className={`font-semibold ${timelineData.type === 'sleeper' ? 'text-purple-400' : 'text-blue-400'}`}>
                      {timelineData.type === 'sleeper' ? 'GenAI Sleeper Agent' : 'Organic Human'}
                    </span>
                  </div>

                  <div className="flex justify-between text-xs py-1 border-b border-slate-800/60">
                    <span className="text-slate-400">Sentinel Verdict:</span>
                    <span className={`font-bold ${timelineData.flagged ? 'text-rose-400' : 'text-emerald-400'}`}>
                      {timelineData.flagged ? 'Flagged Synthetic' : 'Cleared Organic'}
                    </span>
                  </div>

                  <div className="flex justify-between text-xs py-1 border-b border-slate-800/60">
                    <span className="text-slate-400">Composite Risk:</span>
                    <span className={`font-mono font-bold ${riskPct >= 55 ? 'text-rose-400' : 'text-emerald-400'}`}>
                      {riskPct.toFixed(1)}%
                    </span>
                  </div>

                  {timelineData.ring_id && (
                    <div className="flex justify-between text-xs py-1 border-b border-slate-800/60">
                      <span className="text-slate-400">Syndicate Ring:</span>
                      <span className="font-mono text-amber-400 font-bold">{timelineData.ring_id}</span>
                    </div>
                  )}

                  <div className="flex justify-between text-xs py-1">
                    <span className="text-slate-400">Early Warning:</span>
                    <span className="font-mono font-semibold text-amber-400">
                      {timelineData.flag_week ? `Week ${timelineData.flag_week} of 24` : 'No trigger (Benign)'}
                    </span>
                  </div>
                </div>
              </div>

              {/* Dynamic Live Scrubber Alarm */}
              {isTriggeredAtCurrentWeek ? (
                <div className="mt-4 p-3 bg-rose-950/50 border border-rose-700/70 rounded-lg text-xs text-rose-200 flex items-start space-x-2 animate-pulse">
                  <Clock className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
                  <div>
                    <strong className="text-rose-300">EARLY INTERCEPTION ALARM TRIGGERED</strong>
                    <p className="text-[11px] mt-0.5 text-slate-300">
                      VeriTrace intercepted this sleeper agent at <strong>Week {timelineData.flag_week}</strong> ({24 - timelineData.flag_week} weeks ahead of terminal strike).
                    </p>
                  </div>
                </div>
              ) : timelineData.flag_week ? (
                <div className="mt-4 p-3 bg-amber-950/30 border border-amber-800/40 rounded-lg text-xs text-amber-200 flex items-start space-x-2">
                  <Clock className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
                  <span>
                    Incubating behavior... Early warning trigger programmed at <strong>Week {timelineData.flag_week}</strong>.
                  </span>
                </div>
              ) : (
                <div className="mt-4 p-3 bg-emerald-950/30 border border-emerald-800/40 rounded-lg text-xs text-emerald-200 flex items-start space-x-2">
                  <CheckCircle className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                  <span>
                    <strong>Organic Profile:</strong> Normal spend variance, Poisson login behavior, and genuine consumer patterns.
                  </span>
                </div>
              )}
            </div>

            {/* Right 2 cols: Multi-Signal Forensics & Feature Meters */}
            <div className="lg:col-span-2 bg-slate-900/80 border border-slate-800 rounded-xl p-4 sm:p-5 flex flex-col justify-between shadow-lg">
              <div>
                <div className="flex items-center justify-between border-b border-slate-800 pb-3 mb-4">
                  <div className="flex items-center space-x-2">
                    <Fingerprint className="w-5 h-5 text-cyan-400" />
                    <h4 className="text-sm font-semibold text-slate-200 uppercase tracking-wider">Multi-Signal Forensic Meters</h4>
                  </div>
                  {timelineData.risk_breakdown && (
                    <div className="flex items-center space-x-2 text-[11px] font-mono">
                      <span className="text-slate-400">Trajectory: <strong className="text-cyan-400">{(timelineData.risk_breakdown.trajectory_risk * 100).toFixed(0)}%</strong></span>
                      <span className="text-slate-600">|</span>
                      <span className="text-slate-400">Tx Anomaly: <strong className="text-rose-400">{(timelineData.risk_breakdown.transaction_anomaly * 100).toFixed(0)}%</strong></span>
                    </div>
                  )}
                </div>

                {/* 6 Real Forensic Feature Meters */}
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                  <div className="bg-slate-950/80 p-3 rounded-lg border border-slate-800">
                    <div className="flex justify-between items-center text-[10px] text-slate-400 font-mono">
                      <span>LINEARITY ($R^2$)</span>
                      <span className="text-cyan-400 font-bold">{features.spend_smoothness !== undefined ? `${(features.spend_smoothness * 100).toFixed(0)}%` : '—'}</span>
                    </div>
                    <div className="w-full bg-slate-800 h-1.5 rounded-full mt-2 overflow-hidden">
                      <div className="bg-cyan-500 h-full rounded-full transition-all duration-500" style={{ width: `${(features.spend_smoothness || 0) * 100}%` }} />
                    </div>
                    <p className="text-[10px] text-slate-500 mt-1">Scripted monotonic ramp</p>
                  </div>

                  <div className="bg-slate-950/80 p-3 rounded-lg border border-slate-800">
                    <div className="flex justify-between items-center text-[10px] text-slate-400 font-mono">
                      <span>MONOTONICITY</span>
                      <span className="text-indigo-400 font-bold">{features.spend_monotonicity !== undefined ? `${(features.spend_monotonicity * 100).toFixed(0)}%` : '—'}</span>
                    </div>
                    <div className="w-full bg-slate-800 h-1.5 rounded-full mt-2 overflow-hidden">
                      <div className="bg-indigo-500 h-full rounded-full transition-all duration-500" style={{ width: `${(features.spend_monotonicity || 0) * 100}%` }} />
                    </div>
                    <p className="text-[10px] text-slate-500 mt-1">Non-decreasing week ratio</p>
                  </div>

                  <div className="bg-slate-950/80 p-3 rounded-lg border border-slate-800">
                    <div className="flex justify-between items-center text-[10px] text-slate-400 font-mono">
                      <span>LOGIN REGULARITY</span>
                      <span className="text-amber-400 font-bold">{features.login_regularity !== undefined ? `${(features.login_regularity * 100).toFixed(0)}%` : '—'}</span>
                    </div>
                    <div className="w-full bg-slate-800 h-1.5 rounded-full mt-2 overflow-hidden">
                      <div className="bg-amber-500 h-full rounded-full transition-all duration-500" style={{ width: `${(features.login_regularity || 0) * 100}%` }} />
                    </div>
                    <p className="text-[10px] text-slate-500 mt-1">Session timing predictability</p>
                  </div>

                  <div className="bg-slate-950/80 p-3 rounded-lg border border-slate-800">
                    <div className="flex justify-between items-center text-[10px] text-slate-400 font-mono">
                      <span>VARIANCE (CV)</span>
                      <span className="text-emerald-400 font-bold">{features.variance_score !== undefined ? features.variance_score.toFixed(2) : '—'}</span>
                    </div>
                    <div className="w-full bg-slate-800 h-1.5 rounded-full mt-2 overflow-hidden">
                      <div className="bg-emerald-500 h-full rounded-full transition-all duration-500" style={{ width: `${Math.min(100, (features.variance_score || 0) * 150)}%` }} />
                    </div>
                    <p className="text-[10px] text-slate-500 mt-1">Natural human noise level</p>
                  </div>

                  <div className="bg-slate-950/80 p-3 rounded-lg border border-slate-800">
                    <div className="flex justify-between items-center text-[10px] text-slate-400 font-mono">
                      <span>BUST-OUT SURGE</span>
                      <span className="text-rose-400 font-bold">{features.bust_out_ratio !== undefined ? `${(features.bust_out_ratio * 100).toFixed(0)}%` : '0%'}</span>
                    </div>
                    <div className="w-full bg-slate-800 h-1.5 rounded-full mt-2 overflow-hidden">
                      <div className="bg-rose-500 h-full rounded-full transition-all duration-500" style={{ width: `${(features.bust_out_ratio || 0) * 100}%` }} />
                    </div>
                    <p className="text-[10px] text-slate-500 mt-1">Terminal jump vs history</p>
                  </div>

                  <div className="bg-slate-950/80 p-3 rounded-lg border border-slate-800">
                    <div className="flex justify-between items-center text-[10px] text-slate-400 font-mono">
                      <span>DEVICE STABILITY</span>
                      <span className="text-teal-400 font-bold">{features.device_change_rate !== undefined ? `${(features.device_change_rate * 100).toFixed(0)}%` : '0%'}</span>
                    </div>
                    <div className="w-full bg-slate-800 h-1.5 rounded-full mt-2 overflow-hidden">
                      <div className="bg-teal-500 h-full rounded-full transition-all duration-500" style={{ width: `${Math.min(100, (features.device_change_rate || 0) * 500)}%` }} />
                    </div>
                    <p className="text-[10px] text-slate-500 mt-1">Device switch frequency</p>
                  </div>
                </div>

                {/* Real Explainability Reasons List */}
                {timelineData.detection_reasons && timelineData.detection_reasons.length > 0 && (
                  <div className="mt-4 p-3.5 bg-slate-950/80 rounded-lg border border-slate-800 space-y-1.5">
                    <div className="flex items-center space-x-1.5 text-xs font-semibold text-slate-200">
                      <FileText className="w-3.5 h-3.5 text-cyan-400" />
                      <span>Sentinel Explainable AI Forensic Audit Trail</span>
                    </div>
                    <ul className="space-y-1 text-[11px] text-slate-300">
                      {timelineData.detection_reasons.map((reason, idx) => (
                        <li key={idx} className="flex items-start space-x-2">
                          <span className="text-rose-400 font-bold">•</span>
                          <span>{reason}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Recharts Trajectory Visualizer & Interactive Video Scrubber */}
          <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4 sm:p-5 shadow-xl space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-800 pb-3">
              <div>
                <h4 className="text-base font-semibold text-slate-100 flex items-center space-x-2">
                  <TrendingUp className="w-5 h-5 text-emerald-400" />
                  <span>24-Week Spend & Incubation Trajectory Replay</span>
                </h4>
                <p className="text-xs text-slate-400 mt-0.5">
                  Play week-by-week incubation to witness Sentinel early detection trigger before the strike
                </p>
              </div>

              <div className="flex items-center flex-wrap gap-2.5">
                {/* Benchmark Toggle */}
                <label className="flex items-center space-x-1.5 bg-slate-950 px-2.5 py-1 rounded-lg border border-slate-800 text-xs text-slate-300 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={showOrganicBaseline}
                    onChange={(e) => setShowOrganicBaseline(e.target.checked)}
                    className="accent-emerald-500 rounded"
                  />
                  <span>Organic Benchmark</span>
                </label>

                {/* View toggles */}
                <div className="flex items-center bg-slate-950 p-1 rounded-lg border border-slate-800 text-xs">
                  <button
                    onClick={() => setChartView('spend')}
                    className={`px-3 py-1 rounded font-medium transition ${
                      chartView === 'spend' ? 'bg-slate-800 text-emerald-300 shadow-sm' : 'text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    Spend ($)
                  </button>
                  <button
                    onClick={() => setChartView('logins')}
                    className={`px-3 py-1 rounded font-medium transition ${
                      chartView === 'logins' ? 'bg-slate-800 text-cyan-300 shadow-sm' : 'text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    Logins
                  </button>
                  <button
                    onClick={() => setChartView('events')}
                    className={`px-3 py-1 rounded font-medium transition ${
                      chartView === 'events' ? 'bg-slate-800 text-purple-300 shadow-sm' : 'text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    Event Log
                  </button>
                </div>
              </div>
            </div>

            {/* Interactive Timeline Video Player Bar */}
            <div className="bg-slate-950/90 border border-slate-800 p-3 rounded-xl flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div className="flex items-center space-x-2">
                <button
                  onClick={resetScrubber}
                  className="p-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg transition"
                  title="Reset to Week 1"
                >
                  <RotateCcw className="w-3.5 h-3.5" />
                </button>
                <button
                  onClick={() => setCurrentPlaybackWeek(Math.max(1, currentPlaybackWeek - 1))}
                  className="p-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg transition"
                  title="Step Back 1 Week"
                >
                  <SkipBack className="w-3.5 h-3.5" />
                </button>
                <button
                  onClick={togglePlay}
                  className={`flex items-center space-x-1.5 px-3.5 py-1.5 rounded-lg text-xs font-bold transition shadow-md ${
                    isPlaying 
                      ? 'bg-rose-600 hover:bg-rose-500 text-white animate-pulse' 
                      : 'bg-emerald-600 hover:bg-emerald-500 text-slate-950'
                  }`}
                >
                  {isPlaying ? <Pause className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5 fill-current" />}
                  <span>{isPlaying ? 'Pause' : 'Play Incubation'}</span>
                </button>
                <button
                  onClick={() => setCurrentPlaybackWeek(Math.min(timelineData.weeks_count || 24, currentPlaybackWeek + 1))}
                  className="p-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg transition"
                  title="Step Forward 1 Week"
                >
                  <SkipForward className="w-3.5 h-3.5" />
                </button>
              </div>

              {/* Scrubber Slider */}
              <div className="flex-1 flex items-center space-x-3 max-w-md">
                <span className="text-xs font-mono text-slate-400">W1</span>
                <input
                  type="range"
                  min="1"
                  max={timelineData.weeks_count || 24}
                  value={currentPlaybackWeek}
                  onChange={(e) => {
                    if (playIntervalRef.current) clearInterval(playIntervalRef.current);
                    setIsPlaying(false);
                    setCurrentPlaybackWeek(parseInt(e.target.value));
                  }}
                  className="flex-1 accent-emerald-500 cursor-pointer"
                />
                <span className="text-xs font-mono font-bold text-emerald-400 bg-slate-900 px-2.5 py-0.5 rounded border border-slate-800">
                  Week {currentPlaybackWeek} / {timelineData.weeks_count || 24}
                </span>
              </div>
            </div>

            {/* Chart View or Event Log View */}
            {chartView !== 'events' ? (
              <div className="h-[320px] sm:h-[380px] w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart 
                    data={chartData} 
                    margin={{ top: 15, right: 30, left: 10, bottom: 5 }}
                    onClick={(e) => {
                      if (e && e.activePayload && e.activePayload.length) {
                        setSelectedPoint(e.activePayload[0].payload);
                      }
                    }}
                  >
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
                            <div className="bg-slate-950 border border-slate-700 p-3 rounded-lg shadow-2xl text-xs space-y-1.5 font-sans">
                              <p className="font-bold text-slate-200 border-b border-slate-800 pb-1">{label} (Week {data.weekNum})</p>
                              <p className="text-emerald-400 font-mono font-semibold">Weekly Spend: ${data.spend?.toLocaleString()}</p>
                              <p className="text-cyan-400 font-mono">Logins: {data.login_count} sessions</p>
                              <p className="text-slate-400">Bill Paid on Time: {data.bill_paid_on_time ? 'Yes' : 'No'}</p>
                              {data.new_device && (
                                <p className="text-amber-400">Device Change Event</p>
                              )}
                              {data.location_change && (
                                <p className="text-indigo-400">Geo Location Shift</p>
                              )}
                              {data.is_strike && (
                                <p className="text-rose-400 font-bold bg-rose-950/80 px-2 py-0.5 rounded border border-rose-800">
                                  TERMINAL FRAUD STRIKE (Bust-out)
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
                    {timelineData.flag_week && currentPlaybackWeek >= timelineData.flag_week && (
                      <ReferenceLine 
                        x={`W${timelineData.flag_week}`} 
                        stroke="#F43F5E" 
                        strokeWidth={2}
                        strokeDasharray="4 4"
                        label={{ 
                          value: `Flagged (W${timelineData.flag_week})`, 
                          position: 'top', 
                          fill: '#F43F5E', 
                          fontSize: 11,
                          fontWeight: 'bold'
                        }} 
                      />
                    )}

                    {showOrganicBaseline && (
                      <Line 
                        type="monotone" 
                        dataKey="organic_ref" 
                        name="Organic Human Baseline ($)"
                        stroke="#64748B" 
                        strokeWidth={1.5}
                        strokeDasharray="4 4"
                        dot={false}
                      />
                    )}

                    {chartView === 'spend' ? (
                      <Line 
                        type="monotone" 
                        dataKey="spend" 
                        name="Observed Weekly Spend ($)"
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
                          return <circle cx={cx} cy={cy} r={3.5} fill="#10B981" key={props.key} />;
                        }}
                        activeDot={{ r: 7 }}
                      />
                    ) : (
                      <Line 
                        type="monotone" 
                        dataKey="login_count" 
                        name="Logins / Week"
                        stroke="#06B6D4" 
                        strokeWidth={2.5}
                        dot={{ r: 4, fill: '#06B6D4' }}
                        activeDot={{ r: 7 }}
                      />
                    )}
                  </LineChart>
                </ResponsiveContainer>
              </div>
            ) : (
              /* Event Log Table View */
              <div className="overflow-x-auto max-h-[360px]">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-950 text-slate-400 uppercase tracking-wider sticky top-0">
                    <tr>
                      <th className="py-2.5 px-3">Week</th>
                      <th className="py-2.5 px-3">Weekly Spend</th>
                      <th className="py-2.5 px-3">Logins</th>
                      <th className="py-2.5 px-3">Bill Payment</th>
                      <th className="py-2.5 px-3">Device / Geo</th>
                      <th className="py-2.5 px-3">Event Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800 font-sans">
                    {activeTimeline.map((item) => (
                      <tr key={item.week} className="hover:bg-slate-800/40">
                        <td className="py-2 px-3 font-mono font-bold text-slate-200">
                          Week {item.week}
                        </td>
                        <td className="py-2 px-3 font-mono font-semibold text-emerald-400">
                          ${item.spend.toLocaleString()}
                        </td>
                        <td className="py-2 px-3 font-mono text-cyan-400">
                          {item.login_count} sessions
                        </td>
                        <td className="py-2 px-3">
                          {item.bill_paid_on_time ? (
                            <span className="text-emerald-400">On Time</span>
                          ) : (
                            <span className="text-rose-400 font-bold">Defaulted</span>
                          )}
                        </td>
                        <td className="py-2 px-3 text-slate-400">
                          {item.new_device && <span className="mr-1.5 text-amber-400">New Device</span>}
                          {item.location_change && <span className="text-indigo-400">Geo Shift</span>}
                          {!item.new_device && !item.location_change && <span className="text-slate-500">Primary Device</span>}
                        </td>
                        <td className="py-2 px-3">
                          {item.fraud_strike ? (
                            <span className="px-2 py-0.5 rounded bg-rose-950 text-rose-300 border border-rose-800 font-bold text-[10px]">
                              TERMINAL STRIKE
                            </span>
                          ) : item.week === timelineData.flag_week ? (
                            <span className="px-2 py-0.5 rounded bg-amber-950 text-amber-300 border border-amber-800 font-bold text-[10px]">
                              SENTINEL TRIGGER
                            </span>
                          ) : (
                            <span className="text-slate-500 text-[11px]">Normal Incubation</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {/* Clicked Data Point Drilldown */}
            {selectedPoint && (
              <div className="p-3 bg-slate-950 border border-slate-800 rounded-lg flex items-center justify-between text-xs">
                <div className="flex items-center space-x-3">
                  <Eye className="w-4 h-4 text-cyan-400" />
                  <span>
                    Inspecting <strong>{selectedPoint.week} (Week {selectedPoint.weekNum})</strong>: Spend: <strong className="font-mono text-emerald-400">${selectedPoint.spend}</strong> | Logins: <strong className="font-mono text-cyan-400">{selectedPoint.login_count}</strong> | Status: {selectedPoint.is_strike ? 'Strike Event' : 'Incubation'}
                  </span>
                </div>
                <button 
                  onClick={() => setSelectedPoint(null)}
                  className="text-slate-500 hover:text-slate-300"
                >
                  Dismiss
                </button>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}
