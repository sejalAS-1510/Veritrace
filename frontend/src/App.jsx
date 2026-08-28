import React, { useState, useEffect } from 'react';
import LiveFeed from './components/LiveFeed';
import TimelineReplay from './components/TimelineReplay';
import ArmsRaceChart from './components/ArmsRaceChart';
import SimilarityGraph from './components/SimilarityGraph';
import { getSystemStatus, getGlobalMetrics } from './api';
import { 
  Shield, 
  Activity, 
  TrendingUp, 
  Swords, 
  Network, 
  Terminal,
  Cpu,
  RefreshCw,
  Menu,
  X,
  CheckCircle2,
  AlertTriangle,
  Radio,
  Sliders,
  Sparkles
} from 'lucide-react';

export default function App() {
  const [activeTab, setActiveTab] = useState('live_feed'); // 'live_feed', 'timeline', 'arms_race', 'graph'
  const [selectedIdentityId, setSelectedIdentityId] = useState(null);
  const [systemInfo, setSystemInfo] = useState(null);
  const [metricsInfo, setMetricsInfo] = useState(null);
  const [toastMessage, setToastMessage] = useState(null);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  useEffect(() => {
    loadStatus();
    const interval = setInterval(loadStatus, 12000);
    return () => clearInterval(interval);
  }, []);

  const loadStatus = async () => {
    try {
      const [sys, met] = await Promise.all([
        getSystemStatus().catch(() => null),
        getGlobalMetrics().catch(() => null)
      ]);
      if (sys) setSystemInfo(sys);
      if (met) setMetricsInfo(met);
    } catch (e) {
      console.error(e);
    }
  };

  const showToast = (msg, type = 'info') => {
    setToastMessage({ text: msg, type });
    setTimeout(() => setToastMessage(null), 3500);
  };

  const handleSelectIdentity = (id) => {
    setSelectedIdentityId(id);
    setActiveTab('timeline');
    setMobileMenuOpen(false);
    showToast(`Loaded timeline for identity ${id}`, 'info');
  };

  const navItems = [
    { id: 'live_feed', label: 'Live Feed & Forge', icon: Activity, badge: 'Real-time' },
    { id: 'timeline', label: '24-Week Replay', icon: TrendingUp, badge: 'Forensics' },
    { id: 'arms_race', label: 'Adversarial Arms Race', icon: Swords, badge: 'Live Combat' },
    { id: 'graph', label: 'Fraud Ring Graph', icon: Network, badge: 'Syndicates' }
  ];

  return (
    <div className="min-h-screen bg-[#070A13] text-slate-100 flex flex-col font-sans selection:bg-emerald-500 selection:text-slate-950 relative overflow-x-hidden">
      {/* Ambient background glow effects */}
      <div className="fixed top-0 left-1/4 w-96 h-96 bg-emerald-500/5 rounded-full blur-3xl pointer-events-none -z-10" />
      <div className="fixed bottom-0 right-1/4 w-96 h-96 bg-cyan-500/5 rounded-full blur-3xl pointer-events-none -z-10" />
      <div className="fixed top-1/2 right-10 w-72 h-72 bg-rose-500/5 rounded-full blur-3xl pointer-events-none -z-10" />

      {/* Toast Notification Banner */}
      {toastMessage && (
        <div className="fixed bottom-5 right-5 z-50 animate-bounce">
          <div className={`px-4 py-2.5 rounded-xl border shadow-2xl backdrop-blur-md flex items-center space-x-2.5 text-xs font-semibold ${
            toastMessage.type === 'alert' 
              ? 'bg-rose-950/90 border-rose-700 text-rose-200 shadow-rose-950/50' 
              : toastMessage.type === 'success'
              ? 'bg-emerald-950/90 border-emerald-700 text-emerald-200 shadow-emerald-950/50'
              : 'bg-slate-900/90 border-slate-700 text-slate-200 shadow-slate-950/50'
          }`}>
            {toastMessage.type === 'alert' ? (
              <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0" />
            ) : (
              <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
            )}
            <span>{toastMessage.text}</span>
          </div>
        </div>
      )}

      {/* Top Navbar */}
      <header className="border-b border-slate-800/80 bg-slate-950/85 backdrop-blur-md sticky top-0 z-40 shadow-xl">
        <div className="max-w-7xl mx-auto px-3 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="p-2 bg-gradient-to-br from-emerald-500 via-teal-600 to-cyan-600 rounded-xl shadow-lg shadow-emerald-500/20 text-slate-950 font-black">
              <Shield className="w-6 h-6 text-slate-950 fill-current" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <h1 className="text-lg sm:text-xl font-black tracking-tight bg-gradient-to-r from-white via-emerald-200 to-teal-400 bg-clip-text text-transparent">
                  VeriTrace
                </h1>
                <span className="text-[10px] px-2 py-0.5 rounded-full bg-emerald-950 border border-emerald-800 text-emerald-300 font-mono font-semibold hidden sm:inline-block">
                  v2.0 Sentinel
                </span>
              </div>
              <p className="text-[10px] sm:text-[11px] text-slate-400 font-medium truncate max-w-[200px] sm:max-w-none">
                Adversarial AI Defense against GenAI Sleeper Agents
              </p>
            </div>
          </div>

          {/* Desktop Status Badges */}
          <div className="hidden lg:flex items-center space-x-3">
            <div className="flex items-center space-x-2 bg-slate-900/90 px-3 py-1.5 rounded-lg border border-slate-800 text-xs shadow-inner">
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
              </span>
              <span className="text-slate-300 font-mono">
                Sentinel: {systemInfo?.status ? 'ONLINE' : 'CONNECTING'}
              </span>
            </div>

            {systemInfo && (
              <div className="flex items-center space-x-2 bg-slate-900/70 px-3 py-1.5 rounded-lg border border-slate-800 text-xs font-mono text-slate-300">
                <span>Monitored: <strong className="text-emerald-400">{systemInfo.identities_monitored}</strong></span>
                <span className="text-slate-600">|</span>
                <span>Flagged: <strong className="text-rose-400">{systemInfo.sleeper_agents_flagged}</strong></span>
              </div>
            )}

            <button
              onClick={loadStatus}
              title="Refresh Global Telemetry"
              className="p-1.5 bg-slate-900 hover:bg-slate-800 text-slate-400 hover:text-slate-200 rounded-lg border border-slate-800 transition"
            >
              <RefreshCw className="w-3.5 h-3.5" />
            </button>
          </div>

          {/* Mobile Menu Toggle Button */}
          <div className="lg:hidden flex items-center space-x-2">
            <div className="flex items-center space-x-1 bg-slate-900 px-2 py-1 rounded-lg border border-slate-800 text-[11px] font-mono">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping inline-block"></span>
              <span className="text-slate-300">{systemInfo?.identities_monitored || 10} IDs</span>
            </div>
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="p-2 bg-slate-900 hover:bg-slate-800 text-slate-300 rounded-lg border border-slate-800 transition"
            >
              {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
            </button>
          </div>
        </div>

        {/* Desktop Tab Navigation */}
        <div className="hidden lg:block max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 border-t border-slate-800/40">
          <nav className="flex space-x-2 overflow-x-auto py-2">
            {navItems.map((tab) => {
              const Icon = tab.icon;
              const isActive = activeTab === tab.id;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`flex items-center space-x-2 px-4 py-2 rounded-lg text-xs font-semibold transition whitespace-nowrap ${
                    isActive
                      ? 'bg-slate-800/90 text-emerald-400 border border-slate-700 shadow-md ring-1 ring-emerald-500/30'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900/60'
                  }`}
                >
                  <Icon className={`w-4 h-4 ${isActive ? 'text-emerald-400' : 'text-slate-500'}`} />
                  <span>{tab.label}</span>
                </button>
              );
            })}
          </nav>
        </div>

        {/* Mobile Dropdown Navigation Drawer */}
        {mobileMenuOpen && (
          <div className="lg:hidden bg-slate-950 border-b border-slate-800 p-3 space-y-1 animate-fadeIn">
            {navItems.map((tab) => {
              const Icon = tab.icon;
              const isActive = activeTab === tab.id;
              return (
                <button
                  key={tab.id}
                  onClick={() => {
                    setActiveTab(tab.id);
                    setMobileMenuOpen(false);
                  }}
                  className={`w-full flex items-center justify-between px-3 py-2.5 rounded-lg text-xs font-semibold transition ${
                    isActive
                      ? 'bg-emerald-950/80 text-emerald-300 border border-emerald-800/60'
                      : 'text-slate-400 hover:bg-slate-900 text-left'
                  }`}
                >
                  <div className="flex items-center space-x-2.5">
                    <Icon className={`w-4 h-4 ${isActive ? 'text-emerald-400' : 'text-slate-500'}`} />
                    <span>{tab.label}</span>
                  </div>
                  <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-900 border border-slate-800 text-slate-400">
                    {tab.badge}
                  </span>
                </button>
              );
            })}
          </div>
        )}
      </header>

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-3 sm:px-6 lg:px-8 py-6 sm:py-8">
        {activeTab === 'live_feed' && (
          <LiveFeed 
            onSelectIdentity={handleSelectIdentity} 
            showToast={showToast}
          />
        )}

        {activeTab === 'timeline' && (
          <TimelineReplay 
            selectedId={selectedIdentityId} 
            onSelectIdentity={(id) => setSelectedIdentityId(id)} 
            showToast={showToast}
          />
        )}

        {activeTab === 'arms_race' && (
          <ArmsRaceChart 
            showToast={showToast}
          />
        )}

        {activeTab === 'graph' && (
          <SimilarityGraph 
            onSelectIdentity={handleSelectIdentity} 
            showToast={showToast}
          />
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-800/80 bg-slate-950/80 backdrop-blur-md py-4 mt-auto">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between text-xs text-slate-500 gap-2">
          <div className="flex items-center space-x-2">
            <span className="w-2 h-2 rounded-full bg-emerald-500 inline-block"></span>
            <p>
              <strong>VeriTrace Sentinel</strong> — Multi-Signal Incubation Forensics & Sleeper Syndicate Defense
            </p>
          </div>
          <p className="font-mono text-[11px] text-slate-400">
            Autonomous Fraud Trajectory Intelligence
          </p>
        </div>
      </footer>
    </div>
  );
}
