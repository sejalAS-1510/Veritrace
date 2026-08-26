import React, { useState, useEffect } from 'react';
import { generateIdentity, getHistory } from '../api';
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
  ChevronRight
} from 'lucide-react';

export default function LiveFeed({ onSelectIdentity }) {
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(false);
  const [fetchingHistory, setFetchingHistory] = useState(true);
  const [lastGenerated, setLastGenerated] = useState(null);
  const [genMode, setGenMode] = useState('random'); // 'random', 'sleeper', 'benign'
  const [errorMsg, setErrorMsg] = useState(null);

  useEffect(() => {
    loadHistory();
  }, []);

  const loadHistory = async () => {
    try {
      setFetchingHistory(true);
      setErrorMsg(null);
      const data = await getHistory();
      setHistory(data);
    } catch (err) {
      console.error(err);
      setErrorMsg('Could not connect to Sentinel API. Ensure backend is running on http://localhost:8000.');
    } finally {
      setFetchingHistory(false);
    }
  };

  const handleGenerate = async () => {
    try {
      setLoading(true);
      setErrorMsg(null);
      const payload = {};
      if (genMode === 'sleeper') payload.identity_type = 'sleeper';
      if (genMode === 'benign') payload.identity_type = 'benign';

      const result = await generateIdentity(payload);
      setLastGenerated(result);
      // Prepend to current history
      setHistory(prev => [result, ...prev]);
    } catch (err) {
      console.error(err);
      setErrorMsg('Failed to generate identity attempt. Make sure backend is running.');
    } finally {
      setLoading(false);
    }
  };

  // Metrics calculation
  const total = history.length;
  const flaggedCount = history.filter(h => h.flagged).length;
  const sleeperCount = history.filter(h => h.type === 'sleeper').length;
  const caughtSleepers = history.filter(h => h.type === 'sleeper' && h.flagged).length;
  const catchRate = sleeperCount > 0 ? ((caughtSleepers / sleeperCount) * 100).toFixed(1) : '100.0';

  return (
    <div className="space-y-6">
      {/* Metrics Banner */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4 flex items-center justify-between">
          <div>
            <p className="text-xs text-slate-400 font-medium uppercase tracking-wider">Identities Monitored</p>
            <p className="text-2xl font-bold text-slate-100 mt-1 font-mono">{total}</p>
          </div>
          <div className="p-3 bg-slate-800 rounded-lg text-slate-300">
            <Activity className="w-5 h-5 text-cyan-400" />
          </div>
        </div>

        <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4 flex items-center justify-between">
          <div>
            <p className="text-xs text-slate-400 font-medium uppercase tracking-wider">Sleeper Agents Detected</p>
            <p className="text-2xl font-bold text-rose-400 mt-1 font-mono">{flaggedCount}</p>
          </div>
          <div className="p-3 bg-rose-950/50 border border-rose-800/40 rounded-lg text-rose-400">
            <ShieldAlert className="w-5 h-5" />
          </div>
        </div>

        <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4 flex items-center justify-between">
          <div>
            <p className="text-xs text-slate-400 font-medium uppercase tracking-wider">Organic Humans Cleared</p>
            <p className="text-2xl font-bold text-emerald-400 mt-1 font-mono">{total - flaggedCount}</p>
          </div>
          <div className="p-3 bg-emerald-950/50 border border-emerald-800/40 rounded-lg text-emerald-400">
            <ShieldCheck className="w-5 h-5" />
          </div>
        </div>

        <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4 flex items-center justify-between">
          <div>
            <p className="text-xs text-slate-400 font-medium uppercase tracking-wider">Sentinel Intercept Rate</p>
            <p className="text-2xl font-bold text-cyan-400 mt-1 font-mono">{catchRate}%</p>
          </div>
          <div className="p-3 bg-cyan-950/50 border border-cyan-800/40 rounded-lg text-cyan-400">
            <Flame className="w-5 h-5" />
          </div>
        </div>
      </div>

      {/* Generator Control Bar */}
      <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-5 shadow-lg flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex items-center space-x-3">
          <div className="p-2.5 bg-emerald-500/10 border border-emerald-500/30 rounded-lg text-emerald-400">
            <Bot className="w-6 h-6" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-slate-100">Adversarial Forge Generator</h3>
            <p className="text-xs text-slate-400">Simulate GenAI synthetic borrower incubation & sleeper agent penetration attempts</p>
          </div>
        </div>

        <div className="flex items-center flex-wrap gap-3">
          {/* Mode Selector */}
          <div className="flex items-center bg-slate-800/80 p-1 rounded-lg border border-slate-700 text-xs">
            <button
              type="button"
              onClick={() => setGenMode('random')}
              className={`px-3 py-1.5 rounded-md font-medium transition ${
                genMode === 'random' ? 'bg-slate-700 text-white shadow-sm' : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              50/50 Random
            </button>
            <button
              type="button"
              onClick={() => setGenMode('sleeper')}
              className={`px-3 py-1.5 rounded-md font-medium transition ${
                genMode === 'sleeper' ? 'bg-rose-900/80 text-rose-200 border border-rose-700/50 shadow-sm' : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              Force Sleeper
            </button>
            <button
              type="button"
              onClick={() => setGenMode('benign')}
              className={`px-3 py-1.5 rounded-md font-medium transition ${
                genMode === 'benign' ? 'bg-emerald-900/80 text-emerald-200 border border-emerald-700/50 shadow-sm' : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              Force Benign
            </button>
          </div>

          {/* Action Button */}
          <button
            onClick={handleGenerate}
            disabled={loading}
            className="flex items-center space-x-2 bg-gradient-to-r from-emerald-500 to-teal-600 hover:from-emerald-400 hover:to-teal-500 text-slate-950 font-bold px-5 py-2.5 rounded-lg shadow-lg shadow-emerald-950/40 transition active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Zap className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            <span>{loading ? 'Synthesizing...' : '⚡ Generate New Attempt'}</span>
          </button>

          <button
            onClick={loadHistory}
            title="Refresh History"
            className="p-2.5 bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-slate-200 rounded-lg border border-slate-700 transition"
          >
            <RefreshCw className={`w-4 h-4 ${fetchingHistory ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {errorMsg && (
        <div className="bg-rose-950/40 border border-rose-800 text-rose-300 px-4 py-3 rounded-lg text-sm flex items-center justify-between">
          <span>{errorMsg}</span>
          <button onClick={loadHistory} className="text-xs bg-rose-900 hover:bg-rose-800 px-2 py-1 rounded">Retry</button>
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
              <div className={`p-2 rounded-lg mt-0.5 ${
                lastGenerated.flagged ? 'bg-rose-500/20 text-rose-400' : 'bg-emerald-500/20 text-emerald-400'
              }`}>
                {lastGenerated.flagged ? <ShieldAlert className="w-6 h-6" /> : <ShieldCheck className="w-6 h-6" />}
              </div>
              <div>
                <div className="flex items-center space-x-2">
                  <span className="font-mono text-base font-bold text-white">{lastGenerated.id}</span>
                  <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                    lastGenerated.type === 'sleeper' 
                      ? 'bg-purple-950/80 text-purple-300 border border-purple-800' 
                      : 'bg-blue-950/80 text-blue-300 border border-blue-800'
                  }`}>
                    {lastGenerated.type === 'sleeper' ? '🤖 Synthetic Sleeper' : '👤 Organic Human'}
                  </span>
                  {lastGenerated.ring_id && (
                    <span className="text-xs px-2 py-0.5 rounded-full bg-amber-950/80 text-amber-300 border border-amber-800 font-mono">
                      {lastGenerated.ring_id}
                    </span>
                  )}
                </div>
                <p className="text-xs text-slate-400 mt-1">
                  Sentinel Verdict: <strong className={lastGenerated.flagged ? 'text-rose-400' : 'text-emerald-400'}>
                    {lastGenerated.flagged ? '🚩 FLAGGED FOR BUST-OUT FRAUD' : '✅ PASSED ORGANIC VERIFICATION'}
                  </strong>
                  {lastGenerated.flag_week && (
                    <span className="ml-2 text-slate-400">
                      (Intercepted at <strong className="text-amber-400">Week {lastGenerated.flag_week}</strong> of 24)
                    </span>
                  )}
                </p>
              </div>
            </div>

            <div className="flex items-center space-x-4">
              <div className="text-right">
                <p className="text-xs text-slate-400">Risk Score</p>
                <p className={`text-2xl font-black font-mono ${
                  lastGenerated.risk_score >= 0.65 ? 'text-rose-400' : 'text-emerald-400'
                }`}>
                  {(lastGenerated.risk_score * 100).toFixed(1)}%
                </p>
              </div>
              {onSelectIdentity && (
                <button
                  onClick={() => onSelectIdentity(lastGenerated.id)}
                  className="flex items-center space-x-1 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs px-3 py-2 rounded-lg border border-slate-700 transition"
                >
                  <span>Replay Timeline</span>
                  <ChevronRight className="w-3.5 h-3.5" />
                </button>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Live Feed Table */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-xl overflow-hidden shadow-xl">
        <div className="px-5 py-4 border-b border-slate-800 flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <Layers className="w-4 h-4 text-emerald-400" />
            <h3 className="text-sm font-semibold text-slate-200 uppercase tracking-wider">Sentinel Surveillance Feed</h3>
          </div>
          <span className="text-xs text-slate-500 font-mono">Real-time Stream ({history.length} records)</span>
        </div>

        <div className="overflow-x-auto max-h-[480px]">
          <table className="w-full text-left border-collapse text-xs">
            <thead className="bg-slate-950/80 text-slate-400 uppercase tracking-wider sticky top-0 z-10 border-b border-slate-800">
              <tr>
                <th className="py-3 px-4">Identity ID</th>
                <th className="py-3 px-4">Ground Truth Type</th>
                <th className="py-3 px-4">Sentinel Verdict</th>
                <th className="py-3 px-4">Early Intercept</th>
                <th className="py-3 px-4">Risk Probability</th>
                <th className="py-3 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-sans">
              {history.length === 0 ? (
                <tr>
                  <td colSpan={6} className="py-8 text-center text-slate-500">
                    No identities monitored yet. Click "⚡ Generate New Attempt" above to start.
                  </td>
                </tr>
              ) : (
                history.map((item, idx) => (
                  <tr 
                    key={item.id || idx}
                    className="hover:bg-slate-800/40 transition group"
                  >
                    <td className="py-3 px-4 font-mono font-semibold text-slate-200">
                      {item.id}
                      {item.ring_id && (
                        <span className="ml-2 text-[10px] px-1.5 py-0.5 rounded bg-amber-950 text-amber-300 border border-amber-800/50">
                          {item.ring_id}
                        </span>
                      )}
                    </td>

                    <td className="py-3 px-4">
                      <span className={`inline-flex items-center px-2 py-0.5 rounded text-[11px] font-medium ${
                        item.type === 'sleeper'
                          ? 'bg-purple-950 text-purple-300 border border-purple-800/60'
                          : 'bg-blue-950 text-blue-300 border border-blue-800/60'
                      }`}>
                        {item.type === 'sleeper' ? '🤖 GenAI Sleeper' : '👤 Organic Human'}
                      </span>
                    </td>

                    <td className="py-3 px-4">
                      {item.flagged ? (
                        <span className="inline-flex items-center space-x-1 text-rose-400 font-bold bg-rose-950/60 px-2 py-0.5 rounded border border-rose-800/50">
                          <span>🚩 Flagged</span>
                        </span>
                      ) : (
                        <span className="inline-flex items-center space-x-1 text-emerald-400 font-bold bg-emerald-950/60 px-2 py-0.5 rounded border border-emerald-800/50">
                          <span>✅ Passed</span>
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
                        <div className="w-20 bg-slate-800 rounded-full h-2 overflow-hidden">
                          <div 
                            className={`h-full rounded-full ${
                              item.risk_score >= 0.65 
                                ? 'bg-rose-500' 
                                : item.risk_score >= 0.40 
                                ? 'bg-amber-500' 
                                : 'bg-emerald-500'
                            }`}
                            style={{ width: `${Math.min(100, Math.max(5, item.risk_score * 100))}%` }}
                          />
                        </div>
                        <span className={`font-mono font-bold ${
                          item.risk_score >= 0.65 ? 'text-rose-400' : 'text-emerald-400'
                        }`}>
                          {(item.risk_score * 100).toFixed(0)}%
                        </span>
                      </div>
                    </td>

                    <td className="py-3 px-4 text-right">
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
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
