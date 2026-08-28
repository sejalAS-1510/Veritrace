import React, { useState, useEffect, useRef } from 'react';
import { generateIdentity, generateBatch, getHistory, getGlobalMetrics } from '../api';
import { 
  Zap, 
  ShieldAlert, 
  ShieldCheck, 
  RefreshCw, 
  UserCheck, 
  Bot, 
  Flame, 
  Activity, 
  Layers, 
  SlidersHorizontal,
  ChevronRight,
  PackagePlus,
  AlertOctagon,
  CheckCircle2,
  HelpCircle,
  Clock,
  Sparkles,
  Search,
  Filter,
  Play,
  Pause,
  Download,
  Copy,
  Sliders,
  X,
  FileCode,
  Check,
  ExternalLink
} from 'lucide-react';

export default function LiveFeed({ onSelectIdentity, showToast }) {
  const [history, setHistory] = useState([]);
  const [metrics, setMetrics] = useState(null);
  const [loading, setLoading] = useState(false);
  const [batchLoading, setBatchLoading] = useState(false);
  const [fetchingHistory, setFetchingHistory] = useState(true);
  const [lastGenerated, setLastGenerated] = useState(null);
  const [genMode, setGenMode] = useState('random'); // 'random', 'sleeper', 'benign'
  const [filterType, setFilterType] = useState('all'); // 'all', 'sleeper', 'benign', 'flagged'
  const [searchQuery, setSearchQuery] = useState('');
  const [errorMsg, setErrorMsg] = useState(null);

  // Live Stream Simulation state
  const [isStreaming, setIsStreaming] = useState(false);
  const streamIntervalRef = useRef(null);

  // Custom Forge Modal state
  const [showConfigModal, setShowConfigModal] = useState(false);
  const [customWeeks, setCustomWeeks] = useState(24);
  const [customRingId, setCustomRingId] = useState('');
  const [customType, setCustomType] = useState('sleeper');

  // Quick Inspector Modal
  const [inspectingAccount, setInspectingAccount] = useState(null);
  const [copiedId, setCopiedId] = useState(null);

  useEffect(() => {
    loadAllData();
    return () => {
      if (streamIntervalRef.current) clearInterval(streamIntervalRef.current);
    };
  }, []);

  const loadAllData = async () => {
    try {
      setFetchingHistory(true);
      setErrorMsg(null);
      const [historyData, metricsData] = await Promise.all([
        getHistory(),
        getGlobalMetrics().catch(() => null)
      ]);
      setHistory(historyData);
      if (metricsData) setMetrics(metricsData);
    } catch (err) {
      console.error(err);
      setErrorMsg('Could not connect to Sentinel API. Ensure backend is running on http://localhost:8000.');
    } finally {
      setFetchingHistory(false);
    }
  };

  const handleGenerate = async (customPayload = null) => {
    try {
      setLoading(true);
      setErrorMsg(null);
      let payload = {};
      if (customPayload) {
        payload = customPayload;
      } else {
        if (genMode === 'sleeper') payload.identity_type = 'sleeper';
        if (genMode === 'benign') payload.identity_type = 'benign';
      }

      const result = await generateIdentity(payload);
      setLastGenerated(result);
      setHistory(prev => [result, ...prev]);

      if (showToast) {
        if (result.flagged) {
          showToast(`Sleeper Agent ${result.id} intercepted at Week ${result.flag_week || 24}!`, 'alert');
        } else {
          showToast(`Organic Identity ${result.id} cleared verification.`, 'success');
        }
      }
      
      // Refresh global metrics
      getGlobalMetrics().then(m => setMetrics(m)).catch(() => {});
      return result;
    } catch (err) {
      console.error(err);
      setErrorMsg('Failed to generate identity attempt. Make sure backend is running.');
    } finally {
      setLoading(false);
    }
  };

  const handleGenerateBatch = async () => {
    try {
      setBatchLoading(true);
      setErrorMsg(null);
      const result = await generateBatch({ count: 10, sleeper_ratio: 0.5 });
      await loadAllData();
      if (result.identities && result.identities.length > 0) {
        setLastGenerated(result.identities[0]);
      }
      if (showToast) {
        showToast(`Seeded 10 identities with Syndicate Ring (${result.fraud_rings_seeded?.[0] || 'RING'})`, 'success');
      }
    } catch (err) {
      console.error(err);
      setErrorMsg('Failed to generate batch of identities.');
    } finally {
      setBatchLoading(false);
    }
  };

  // Toggle Live Traffic Stream
  const toggleStreaming = () => {
    if (isStreaming) {
      if (streamIntervalRef.current) clearInterval(streamIntervalRef.current);
      setIsStreaming(false);
      if (showToast) showToast('Traffic stream paused', 'info');
    } else {
      setIsStreaming(true);
      if (showToast) showToast('Real-time traffic stream started (2.5s intervals)', 'success');
      streamIntervalRef.current = setInterval(() => {
        handleGenerate();
      }, 2500);
    }
  };

  const handleCustomForgeSubmit = async (e) => {
    e.preventDefault();
    setShowConfigModal(false);
    await handleGenerate({
      identity_type: customType,
      weeks: customWeeks,
      ring_id: customRingId.trim() || undefined
    });
  };

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
    setCopiedId(text);
    setTimeout(() => setCopiedId(null), 2000);
    if (showToast) showToast(`Copied ${text} to clipboard`, 'info');
  };

  const handleExportData = () => {
    const jsonStr = JSON.stringify(history, null, 2);
    const blob = new Blob([jsonStr], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `veritrace-surveillance-audit-${new Date().toISOString().slice(0, 10)}.json`;
    a.click();
    URL.revokeObjectURL(url);
    if (showToast) showToast('Downloaded surveillance forensics JSON', 'success');
  };

  // Filter and search logic
  const filteredHistory = history.filter(item => {
    if (filterType === 'sleeper' && item.type !== 'sleeper') return false;
    if (filterType === 'benign' && item.type !== 'benign') return false;
    if (filterType === 'flagged' && !item.flagged) return false;
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      const idMatch = item.id?.toLowerCase().includes(q);
      const ringMatch = item.ring_id?.toLowerCase().includes(q);
      return idMatch || ringMatch;
    }
    return true;
  });

  return (
    <div className="space-y-6">
      {/* Real Metrics Banner */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
        <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-3.5 flex flex-col justify-between shadow-lg">
          <span className="text-[11px] text-slate-400 font-medium uppercase tracking-wider">Monitored</span>
          <div className="flex items-baseline space-x-1.5 mt-1">
            <span className="text-2xl font-black text-slate-100 font-mono">{metrics?.total_identities ?? history.length}</span>
            <span className="text-[10px] text-slate-500">accounts</span>
          </div>
          <div className="mt-2 text-[10px] text-emerald-400 flex items-center space-x-1">
            <CheckCircle2 className="w-3 h-3" />
            <span>Active surveillance</span>
          </div>
        </div>

        <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-3.5 flex flex-col justify-between shadow-lg">
          <span className="text-[11px] text-slate-400 font-medium uppercase tracking-wider">Sleepers Caught</span>
          <div className="flex items-baseline space-x-1.5 mt-1">
            <span className="text-2xl font-black text-rose-400 font-mono">
              {metrics?.true_positives ?? history.filter(h => h.flagged).length}
            </span>
            <span className="text-[10px] text-slate-500">/ {metrics?.total_sleepers ?? history.filter(h => h.type === 'sleeper').length}</span>
          </div>
          <div className="mt-2 text-[10px] text-rose-400 flex items-center space-x-1">
            <ShieldAlert className="w-3 h-3" />
            <span>Flagged synthetic</span>
          </div>
        </div>

        <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-3.5 flex flex-col justify-between shadow-lg">
          <span className="text-[11px] text-slate-400 font-medium uppercase tracking-wider">Detection Rate</span>
          <div className="flex items-baseline space-x-1 mt-1">
            <span className="text-2xl font-black text-cyan-400 font-mono">
              {metrics?.detection_rate_pct !== null && metrics?.detection_rate_pct !== undefined 
                ? `${metrics.detection_rate_pct}%` 
                : '—'}
            </span>
          </div>
          <div className="mt-2 text-[10px] text-cyan-400 flex items-center space-x-1">
            <Flame className="w-3 h-3" />
            <span>Sleeper recall</span>
          </div>
        </div>

        <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-3.5 flex flex-col justify-between shadow-lg">
          <span className="text-[11px] text-slate-400 font-medium uppercase tracking-wider">Precision</span>
          <div className="flex items-baseline space-x-1 mt-1">
            <span className="text-2xl font-black text-emerald-400 font-mono">
              {metrics?.precision !== null && metrics?.precision !== undefined 
                ? `${(metrics.precision * 100).toFixed(1)}%` 
                : '—'}
            </span>
          </div>
          <div className="mt-2 text-[10px] text-emerald-400 flex items-center space-x-1">
            <UserCheck className="w-3 h-3" />
            <span>F1: {metrics?.f1_score !== null && metrics?.f1_score !== undefined ? metrics.f1_score.toFixed(3) : '—'}</span>
          </div>
        </div>

        <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-3.5 flex flex-col justify-between shadow-lg">
          <span className="text-[11px] text-slate-400 font-medium uppercase tracking-wider">False Positive</span>
          <div className="flex items-baseline space-x-1 mt-1">
            <span className="text-2xl font-black text-slate-200 font-mono">
              {metrics?.false_positive_rate_pct !== null && metrics?.false_positive_rate_pct !== undefined 
                ? `${metrics.false_positive_rate_pct}%` 
                : '—'}
            </span>
          </div>
          <div className="mt-2 text-[10px] text-slate-400 flex items-center space-x-1">
            <ShieldCheck className="w-3 h-3 text-emerald-400" />
            <span>Benign cleared</span>
          </div>
        </div>

        <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-3.5 flex flex-col justify-between shadow-lg">
          <span className="text-[11px] text-slate-400 font-medium uppercase tracking-wider">Early Intercept</span>
          <div className="flex items-baseline space-x-1 mt-1">
            <span className="text-2xl font-black text-amber-400 font-mono">
              {metrics?.avg_flag_week ? `W${metrics.avg_flag_week}` : '—'}
            </span>
            {metrics?.avg_flag_week ? <span className="text-[10px] text-slate-500">/ 24</span> : null}
          </div>
          <div className="mt-2 text-[10px] text-amber-400 flex items-center space-x-1">
            <Clock className="w-3 h-3" />
            <span>Pre-strike alarm</span>
          </div>
        </div>
      </div>

      {/* Generator & Interactive Control Bar */}
      <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-5 shadow-lg flex flex-col lg:flex-row lg:items-center justify-between gap-4">
        <div className="flex items-center space-x-3">
          <div className="p-2.5 bg-emerald-500/10 border border-emerald-500/30 rounded-lg text-emerald-400">
            <Bot className="w-6 h-6" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h3 className="text-lg font-semibold text-slate-100">Adversarial Forge Engine</h3>
              {isStreaming && (
                <span className="flex items-center space-x-1.5 text-[10px] px-2 py-0.5 rounded-full bg-rose-950 border border-rose-800 text-rose-300 font-mono font-bold animate-pulse">
                  <span className="w-1.5 h-1.5 rounded-full bg-rose-400"></span>
                  <span>STREAMING REAL-TIME TRAFFIC</span>
                </span>
              )}
            </div>
            <p className="text-xs text-slate-400">Simulate GenAI synthetic identity incubation & automated sleeper syndicate penetration</p>
          </div>
        </div>

        <div className="flex items-center flex-wrap gap-2">
          {/* Mode Selector */}
          <div className="flex items-center bg-slate-950 p-1 rounded-lg border border-slate-800 text-xs">
            <button
              type="button"
              onClick={() => setGenMode('random')}
              className={`px-3 py-1.5 rounded-md font-medium transition ${
                genMode === 'random' ? 'bg-slate-800 text-white shadow-sm' : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              50/50 Mix
            </button>
            <button
              type="button"
              onClick={() => setGenMode('sleeper')}
              className={`px-3 py-1.5 rounded-md font-medium transition ${
                genMode === 'sleeper' ? 'bg-rose-950/90 text-rose-200 border border-rose-800/80 shadow-sm' : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              Sleeper
            </button>
            <button
              type="button"
              onClick={() => setGenMode('benign')}
              className={`px-3 py-1.5 rounded-md font-medium transition ${
                genMode === 'benign' ? 'bg-emerald-950/90 text-emerald-200 border border-emerald-800/80 shadow-sm' : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              Organic
            </button>
          </div>

          {/* Action Buttons */}
          <button
            onClick={() => handleGenerate()}
            disabled={loading || isStreaming}
            className="flex items-center space-x-1.5 bg-gradient-to-r from-emerald-500 to-teal-600 hover:from-emerald-400 hover:to-teal-500 text-slate-950 font-bold px-3.5 py-2 rounded-lg shadow-lg shadow-emerald-950/40 text-xs transition active:scale-95 disabled:opacity-50"
          >
            <Zap className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            <span>{loading ? 'Synthesizing...' : 'Generate'}</span>
          </button>

          {/* Streaming Toggle Button */}
          <button
            onClick={toggleStreaming}
            className={`flex items-center space-x-1.5 text-xs px-3 py-2 rounded-lg font-semibold transition ${
              isStreaming
                ? 'bg-rose-600 hover:bg-rose-500 text-white shadow-lg shadow-rose-950/50 animate-pulse'
                : 'bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700'
            }`}
          >
            {isStreaming ? <Pause className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5 text-emerald-400" />}
            <span>{isStreaming ? 'Pause Stream' : 'Live Stream'}</span>
          </button>

          {/* Custom Forge Config Button */}
          <button
            onClick={() => setShowConfigModal(true)}
            className="flex items-center space-x-1 bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs px-2.5 py-2 rounded-lg border border-slate-700 transition"
            title="Custom Generator Parameters"
          >
            <Sliders className="w-3.5 h-3.5 text-cyan-400" />
            <span className="hidden sm:inline">Config</span>
          </button>

          {/* Batch Seed Button */}
          <button
            onClick={handleGenerateBatch}
            disabled={batchLoading || isStreaming}
            className="flex items-center space-x-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 font-semibold px-3 py-2 rounded-lg border border-slate-700 text-xs transition disabled:opacity-50"
            title="Generates 10 accounts with a coordinated fraud ring"
          >
            <PackagePlus className={`w-3.5 h-3.5 text-amber-400 ${batchLoading ? 'animate-spin' : ''}`} />
            <span>Seed Ring (10)</span>
          </button>

          <button
            onClick={loadAllData}
            title="Refresh All Data"
            className="p-2 bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-slate-200 rounded-lg border border-slate-700 transition"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${fetchingHistory ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {errorMsg && (
        <div className="bg-rose-950/40 border border-rose-800 text-rose-300 px-4 py-3 rounded-lg text-sm flex items-center justify-between">
          <span>{errorMsg}</span>
          <button onClick={loadAllData} className="text-xs bg-rose-900 hover:bg-rose-800 px-2 py-1 rounded">Retry</button>
        </div>
      )}

      {/* Latest Attempt Spotlight Card */}
      {lastGenerated && (
        <div className={`p-4 rounded-xl border transition-all ${
          lastGenerated.flagged 
            ? 'bg-gradient-to-r from-rose-950/40 via-slate-900 to-slate-900 border-rose-800/80 glow-rose' 
            : 'bg-gradient-to-r from-emerald-950/40 via-slate-900 to-slate-900 border-emerald-800/80 glow-emerald'
        }`}>
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div className="flex items-start space-x-3">
              <div className={`p-2.5 rounded-lg mt-0.5 ${
                lastGenerated.flagged ? 'bg-rose-500/20 text-rose-400' : 'bg-emerald-500/20 text-emerald-400'
              }`}>
                {lastGenerated.flagged ? <ShieldAlert className="w-6 h-6" /> : <ShieldCheck className="w-6 h-6" />}
              </div>
              <div className="space-y-1">
                <div className="flex items-center flex-wrap gap-2">
                  <span className="font-mono text-base font-bold text-white">{lastGenerated.id}</span>
                  <button 
                    onClick={() => copyToClipboard(lastGenerated.id)}
                    className="text-slate-400 hover:text-slate-200 transition"
                    title="Copy Identity ID"
                  >
                    {copiedId === lastGenerated.id ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                  </button>
                  <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                    lastGenerated.type === 'sleeper' 
                      ? 'bg-purple-950 text-purple-300 border border-purple-800' 
                      : 'bg-blue-950 text-blue-300 border border-blue-800'
                  }`}>
                    {lastGenerated.type === 'sleeper' ? 'Ground Truth: Sleeper Agent' : 'Ground Truth: Organic Human'}
                  </span>
                  {lastGenerated.ring_id && (
                    <span className="text-xs px-2 py-0.5 rounded-full bg-amber-950 text-amber-300 border border-amber-800 font-mono font-semibold">
                      Ring: {lastGenerated.ring_id}
                    </span>
                  )}
                </div>

                <p className="text-xs text-slate-300">
                  Sentinel Verdict: <strong className={lastGenerated.flagged ? 'text-rose-400' : 'text-emerald-400'}>
                    {lastGenerated.flagged ? 'FLAGGED FOR BUST-OUT FRAUD' : 'CLEARED ORGANIC BEHAVIOR'}
                  </strong>
                  {lastGenerated.flag_week ? (
                    <span className="ml-2 text-slate-400">
                      (Early Trigger: <strong className="text-amber-400 font-mono">Week {lastGenerated.flag_week} of 24</strong>)
                    </span>
                  ) : null}
                </p>

                {/* Real Explainability Reasons */}
                {lastGenerated.detection_reasons && lastGenerated.detection_reasons.length > 0 && (
                  <div className="mt-2 flex flex-wrap gap-1.5">
                    {lastGenerated.detection_reasons.map((reason, i) => (
                      <span key={i} className="text-[11px] bg-slate-950/80 border border-slate-800 text-slate-300 px-2 py-0.5 rounded flex items-center space-x-1">
                        <span className="text-rose-400 font-bold">•</span>
                        <span>{reason}</span>
                      </span>
                    ))}
                  </div>
                )}
              </div>
            </div>

            <div className="flex items-center space-x-4 shrink-0">
              <div className="text-right">
                <p className="text-[11px] text-slate-400">Risk Probability</p>
                <p className={`text-2xl font-black font-mono ${
                  (lastGenerated.risk_score_pct ?? lastGenerated.risk_score * 100) >= 55 ? 'text-rose-400' : 'text-emerald-400'
                }`}>
                  {(lastGenerated.risk_score_pct ?? lastGenerated.risk_score * 100).toFixed(1)}%
                </p>
              </div>

              {onSelectIdentity && (
                <button
                  onClick={() => onSelectIdentity(lastGenerated.id)}
                  className="flex items-center space-x-1 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs px-3.5 py-2.5 rounded-lg border border-slate-700 transition shadow-md"
                >
                  <span>Replay Trajectory</span>
                  <ChevronRight className="w-3.5 h-3.5 text-cyan-400" />
                </button>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Surveillance Feed Table Header & Controls */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-xl overflow-hidden shadow-xl">
        <div className="p-4 border-b border-slate-800 flex flex-col md:flex-row md:items-center justify-between gap-3">
          <div className="flex items-center space-x-2">
            <Layers className="w-4 h-4 text-emerald-400" />
            <h3 className="text-sm font-semibold text-slate-200 uppercase tracking-wider">Live Sentinel Surveillance Feed</h3>
            <span className="text-xs text-slate-500 font-mono">({filteredHistory.length} displayed)</span>
          </div>

          <div className="flex items-center flex-wrap gap-2">
            {/* Filter Tabs */}
            <div className="flex items-center bg-slate-950 p-1 rounded-lg border border-slate-800 text-xs">
              <button
                onClick={() => setFilterType('all')}
                className={`px-2.5 py-1 rounded font-medium transition ${
                  filterType === 'all' ? 'bg-slate-800 text-white' : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                All
              </button>
              <button
                onClick={() => setFilterType('sleeper')}
                className={`px-2.5 py-1 rounded font-medium transition ${
                  filterType === 'sleeper' ? 'bg-purple-950 text-purple-200 border border-purple-800' : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                Sleepers
              </button>
              <button
                onClick={() => setFilterType('benign')}
                className={`px-2.5 py-1 rounded font-medium transition ${
                  filterType === 'benign' ? 'bg-blue-950 text-blue-200 border border-blue-800' : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                Organic
              </button>
              <button
                onClick={() => setFilterType('flagged')}
                className={`px-2.5 py-1 rounded font-medium transition ${
                  filterType === 'flagged' ? 'bg-rose-950 text-rose-200 border border-rose-800' : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                Flagged
              </button>
            </div>

            {/* Search */}
            <div className="relative">
              <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                placeholder="Filter ID / Ring..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="bg-slate-950 border border-slate-700 rounded-lg pl-8 pr-3 py-1 text-xs text-slate-100 placeholder-slate-500 font-mono focus:outline-none focus:border-emerald-500 w-36"
              />
            </div>

            {/* Export JSON Button */}
            <button
              onClick={handleExportData}
              className="flex items-center space-x-1 bg-slate-950 hover:bg-slate-800 text-slate-300 text-xs px-2.5 py-1.5 rounded-lg border border-slate-700 transition"
              title="Download JSON Report"
            >
              <Download className="w-3.5 h-3.5 text-slate-400" />
              <span className="hidden sm:inline">Export</span>
            </button>
          </div>
        </div>

        {/* Real Table */}
        <div className="overflow-x-auto max-h-[520px]">
          <table className="w-full text-left border-collapse text-xs">
            <thead className="bg-slate-950/80 text-slate-400 uppercase tracking-wider sticky top-0 z-10 border-b border-slate-800">
              <tr>
                <th className="py-3 px-4">Identity ID</th>
                <th className="py-3 px-4">Ground Truth</th>
                <th className="py-3 px-4">Sentinel Verdict</th>
                <th className="py-3 px-4">Early Intercept</th>
                <th className="py-3 px-4">Risk Score</th>
                <th className="py-3 px-4">Forensic Explainability</th>
                <th className="py-3 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-sans">
              {filteredHistory.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-8 text-center text-slate-500">
                    No matching identities found. Click "Generate" or "Seed Ring Batch" above.
                  </td>
                </tr>
              ) : (
                filteredHistory.map((item, idx) => {
                  const riskPct = item.risk_score_pct ?? (item.risk_score * 100);
                  return (
                    <tr 
                      key={item.id || idx}
                      className="hover:bg-slate-800/40 transition group cursor-pointer"
                      onClick={() => setInspectingAccount(item)}
                    >
                      <td className="py-3 px-4 font-mono font-semibold text-slate-200">
                        <div className="flex items-center space-x-1.5">
                          <span>{item.id}</span>
                          {item.ring_id && (
                            <span className="text-[10px] px-1.5 py-0.5 rounded bg-amber-950 text-amber-300 border border-amber-800/50">
                              {item.ring_id}
                            </span>
                          )}
                        </div>
                      </td>

                      <td className="py-3 px-4">
                        <span className={`inline-flex items-center px-2 py-0.5 rounded text-[11px] font-medium ${
                          item.type === 'sleeper'
                            ? 'bg-purple-950 text-purple-300 border border-purple-800/60'
                            : 'bg-blue-950 text-blue-300 border border-blue-800/60'
                        }`}>
                          {item.type === 'sleeper' ? 'Sleeper' : 'Organic'}
                        </span>
                      </td>

                      <td className="py-3 px-4">
                        {item.flagged ? (
                          <span className="inline-flex items-center space-x-1 text-rose-400 font-bold bg-rose-950/60 px-2 py-0.5 rounded border border-rose-800/50">
                            <span>Flagged</span>
                          </span>
                        ) : (
                          <span className="inline-flex items-center space-x-1 text-emerald-400 font-bold bg-emerald-950/60 px-2 py-0.5 rounded border border-emerald-800/50">
                            <span>Cleared</span>
                          </span>
                        )}
                      </td>

                      <td className="py-3 px-4 text-slate-300 font-mono">
                        {item.flag_week ? (
                          <span className="text-amber-400 font-semibold">
                            Week {item.flag_week} <span className="text-slate-500 font-normal">/ 24</span>
                          </span>
                        ) : (
                          <span className="text-slate-500">—</span>
                        )}
                      </td>

                      <td className="py-3 px-4">
                        <div className="flex items-center space-x-2">
                          <div className="w-16 bg-slate-800 rounded-full h-2 overflow-hidden">
                            <div 
                              className={`h-full rounded-full ${
                                riskPct >= 55 
                                  ? 'bg-rose-500' 
                                  : riskPct >= 40 
                                  ? 'bg-amber-500' 
                                  : 'bg-emerald-500'
                              }`}
                              style={{ width: `${Math.min(100, Math.max(5, riskPct))}%` }}
                            />
                          </div>
                          <span className={`font-mono font-bold ${
                            riskPct >= 55 ? 'text-rose-400' : 'text-emerald-400'
                          }`}>
                            {riskPct.toFixed(1)}%
                          </span>
                        </div>
                      </td>

                      <td className="py-3 px-4 max-w-xs truncate text-[11px] text-slate-400">
                        {item.detection_reasons && item.detection_reasons.length > 0 ? (
                          <span title={item.detection_reasons.join(' | ')} className="text-slate-300">
                            {item.detection_reasons[0]}
                            {item.detection_reasons.length > 1 && ` (+${item.detection_reasons.length - 1} more)`}
                          </span>
                        ) : (
                          <span className="text-slate-500">Normal organic variance</span>
                        )}
                      </td>

                      <td className="py-3 px-4 text-right" onClick={(e) => e.stopPropagation()}>
                        {onSelectIdentity && (
                          <button
                            onClick={() => onSelectIdentity(item.id)}
                            className="opacity-80 group-hover:opacity-100 text-xs text-cyan-400 hover:text-cyan-300 font-medium transition inline-flex items-center space-x-0.5"
                          >
                            <span>Replay</span>
                            <ChevronRight className="w-3.5 h-3.5" />
                          </button>
                        )}
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Interactive Custom Forge Configuration Modal */}
      {showConfigModal && (
        <div className="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-md w-full p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center space-x-2">
                <Sliders className="w-5 h-5 text-cyan-400" />
                <h4 className="text-base font-bold text-white">Custom Forge Generator</h4>
              </div>
              <button 
                onClick={() => setShowConfigModal(false)}
                className="text-slate-400 hover:text-white"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleCustomForgeSubmit} className="space-y-4 text-xs">
              <div>
                <label className="block text-slate-300 font-medium mb-1">Identity Archetype</label>
                <select
                  value={customType}
                  onChange={(e) => setCustomType(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2.5 text-slate-100 font-mono focus:border-cyan-500 focus:outline-none"
                >
                  <option value="sleeper">Sleeper Agent (Incubation + Strike)</option>
                  <option value="benign">Organic Human (Poisson Fluctuations)</option>
                </select>
              </div>

              <div>
                <label className="block text-slate-300 font-medium mb-1">
                  Timeline Length: <span className="font-mono text-cyan-400 font-bold">{customWeeks} Weeks</span>
                </label>
                <input
                  type="range"
                  min="6"
                  max="48"
                  value={customWeeks}
                  onChange={(e) => setCustomWeeks(parseInt(e.target.value))}
                  className="w-full accent-cyan-500 cursor-pointer"
                />
              </div>

              <div>
                <label className="block text-slate-300 font-medium mb-1">Syndicate Ring Tag (Optional)</label>
                <input
                  type="text"
                  placeholder="e.g. RING-ALPHA, RING-7F2B..."
                  value={customRingId}
                  onChange={(e) => setCustomRingId(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2 text-slate-100 font-mono focus:border-cyan-500 focus:outline-none"
                />
                <p className="text-[10px] text-slate-500 mt-1">Accounts with the same tag share identical prompt parameters in the similarity graph.</p>
              </div>

              <div className="pt-2 flex justify-end space-x-2">
                <button
                  type="button"
                  onClick={() => setShowConfigModal(false)}
                  className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg font-medium"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-gradient-to-r from-cyan-500 to-teal-600 text-slate-950 font-bold rounded-lg shadow-md"
                >
                  Synthesize Identity
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Interactive Account Detail Quick Drawer / Modal */}
      {inspectingAccount && (
        <div className="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-lg w-full p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div>
                <span className="text-[10px] text-slate-400 uppercase font-mono">ACCOUNT DOSSIER</span>
                <h4 className="text-lg font-black text-white font-mono">{inspectingAccount.id}</h4>
              </div>
              <button 
                onClick={() => setInspectingAccount(null)}
                className="text-slate-400 hover:text-white"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="space-y-3 text-xs">
              <div className="grid grid-cols-2 gap-2">
                <div className="bg-slate-950 p-2.5 rounded-lg border border-slate-800">
                  <span className="text-[10px] text-slate-500">Ground Truth</span>
                  <p className="font-bold text-slate-200 mt-0.5">
                    {inspectingAccount.type === 'sleeper' ? 'Sleeper Agent' : 'Organic Human'}
                  </p>
                </div>
                <div className="bg-slate-950 p-2.5 rounded-lg border border-slate-800">
                  <span className="text-[10px] text-slate-500">Sentinel Verdict</span>
                  <p className={`font-bold mt-0.5 ${inspectingAccount.flagged ? 'text-rose-400' : 'text-emerald-400'}`}>
                    {inspectingAccount.flagged ? 'Flagged Synthetic' : 'Cleared Organic'}
                  </p>
                </div>
                <div className="bg-slate-950 p-2.5 rounded-lg border border-slate-800">
                  <span className="text-[10px] text-slate-500">Risk Score</span>
                  <p className="font-mono font-bold text-slate-200 mt-0.5">
                    {(inspectingAccount.risk_score_pct ?? inspectingAccount.risk_score * 100).toFixed(1)}%
                  </p>
                </div>
                <div className="bg-slate-950 p-2.5 rounded-lg border border-slate-800">
                  <span className="text-[10px] text-slate-500">Early Trigger</span>
                  <p className="font-mono font-bold text-amber-400 mt-0.5">
                    {inspectingAccount.flag_week ? `Week ${inspectingAccount.flag_week}` : 'N/A'}
                  </p>
                </div>
              </div>

              {inspectingAccount.detection_reasons && inspectingAccount.detection_reasons.length > 0 && (
                <div className="p-3 bg-slate-950 rounded-lg border border-slate-800 space-y-1">
                  <span className="text-[10px] text-slate-400 uppercase font-semibold">Explainability Audit</span>
                  <ul className="space-y-1 text-[11px] text-slate-300">
                    {inspectingAccount.detection_reasons.map((r, i) => (
                      <li key={i} className="flex items-start space-x-1.5">
                        <span className="text-rose-400 font-bold">•</span>
                        <span>{r}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              <div className="pt-2 flex justify-between items-center">
                <button
                  onClick={() => copyToClipboard(JSON.stringify(inspectingAccount, null, 2))}
                  className="flex items-center space-x-1 text-slate-400 hover:text-slate-200 text-xs"
                >
                  <Copy className="w-3.5 h-3.5" />
                  <span>Copy Raw JSON</span>
                </button>

                <div className="flex space-x-2">
                  <button
                    onClick={() => setInspectingAccount(null)}
                    className="px-3 py-1.5 bg-slate-800 text-slate-300 rounded-lg font-medium"
                  >
                    Close
                  </button>
                  {onSelectIdentity && (
                    <button
                      onClick={() => {
                        const targetId = inspectingAccount.id;
                        setInspectingAccount(null);
                        onSelectIdentity(targetId);
                      }}
                      className="flex items-center space-x-1 px-3.5 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-slate-950 font-bold rounded-lg"
                    >
                      <span>Replay Trajectory</span>
                      <ExternalLink className="w-3.5 h-3.5" />
                    </button>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
