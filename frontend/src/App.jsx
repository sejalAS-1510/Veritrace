import React, { useState } from 'react';
import LiveFeed from './components/LiveFeed';
import TimelineReplay from './components/TimelineReplay';
import ArmsRaceChart from './components/ArmsRaceChart';
import SimilarityGraph from './components/SimilarityGraph';
import { 
  Shield, 
  Activity, 
  TrendingUp, 
  Swords, 
  Network, 
  Radio,
  Lock,
  Terminal,
  Layers
} from 'lucide-react';

export default function App() {
  const [activeTab, setActiveTab] = useState('live_feed'); // 'live_feed', 'timeline', 'arms_race', 'graph'
  const [selectedIdentityId, setSelectedIdentityId] = useState(null);

  const handleSelectIdentity = (id) => {
    setSelectedIdentityId(id);
    setActiveTab('timeline');
  };

  return (
    <div className="min-h-screen bg-[#0B0F19] text-slate-100 flex flex-col font-sans">
      {/* Top Navbar */}
      <header className="border-b border-slate-800/80 bg-slate-950/80 backdrop-blur-md sticky top-0 z-30">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="p-2 bg-gradient-to-br from-emerald-500 to-teal-700 rounded-xl shadow-lg shadow-emerald-500/20 text-slate-950 font-black">
              <Shield className="w-6 h-6 text-slate-950 fill-current" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <h1 className="text-lg font-black tracking-tight bg-gradient-to-r from-slate-100 via-emerald-200 to-teal-400 bg-clip-text text-transparent">
                  🛡️ VeriTrace
                </h1>
                <span className="text-[10px] px-2 py-0.5 rounded-full bg-emerald-950 border border-emerald-800 text-emerald-300 font-mono font-semibold">
                  v1.0 Sentinel
                </span>
              </div>
              <p className="text-[11px] text-slate-400 font-medium">
                Adversarial AI Defense against GenAI Synthetic Sleeper Agents
              </p>
            </div>
          </div>

          <div className="hidden md:flex items-center space-x-4">
            <div className="flex items-center space-x-2 bg-slate-900 px-3 py-1.5 rounded-lg border border-slate-800 text-xs">
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
              </span>
              <span className="text-slate-300 font-mono">Sentinel Engine: ACTIVE</span>
            </div>

            <div className="flex items-center space-x-1 text-slate-400 text-xs font-mono bg-slate-900/60 px-2.5 py-1.5 rounded-lg border border-slate-800">
              <Terminal className="w-3.5 h-3.5 text-emerald-400" />
              <span>MasterCard Hackathon Edition</span>
            </div>
          </div>
        </div>

        {/* Tab Navigation */}
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <nav className="flex space-x-1 overflow-x-auto py-2">
            <button
              onClick={() => setActiveTab('live_feed')}
              className={`flex items-center space-x-2 px-4 py-2 rounded-lg text-xs font-semibold transition whitespace-nowrap ${
                activeTab === 'live_feed'
                  ? 'bg-slate-800 text-emerald-400 border border-slate-700 shadow-md'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
              }`}
            >
              <Activity className="w-4 h-4" />
              <span>⚡ Live Feed</span>
            </button>

            <button
              onClick={() => setActiveTab('timeline')}
              className={`flex items-center space-x-2 px-4 py-2 rounded-lg text-xs font-semibold transition whitespace-nowrap ${
                activeTab === 'timeline'
                  ? 'bg-slate-800 text-emerald-400 border border-slate-700 shadow-md'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
              }`}
            >
              <TrendingUp className="w-4 h-4" />
              <span>📈 Timeline Replay</span>
            </button>

            <button
              onClick={() => setActiveTab('arms_race')}
              className={`flex items-center space-x-2 px-4 py-2 rounded-lg text-xs font-semibold transition whitespace-nowrap ${
                activeTab === 'arms_race'
                  ? 'bg-slate-800 text-cyan-400 border border-slate-700 shadow-md'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
              }`}
            >
              <Swords className="w-4 h-4" />
              <span>⚔️ Arms Race</span>
            </button>

            <button
              onClick={() => setActiveTab('graph')}
              className={`flex items-center space-x-2 px-4 py-2 rounded-lg text-xs font-semibold transition whitespace-nowrap ${
                activeTab === 'graph'
                  ? 'bg-slate-800 text-indigo-400 border border-slate-700 shadow-md'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
              }`}
            >
              <Network className="w-4 h-4" />
              <span>🕸️ Similarity Graph</span>
            </button>
          </nav>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {activeTab === 'live_feed' && (
          <LiveFeed onSelectIdentity={handleSelectIdentity} />
        )}

        {activeTab === 'timeline' && (
          <TimelineReplay 
            selectedId={selectedIdentityId} 
            onSelectIdentity={(id) => setSelectedIdentityId(id)} 
          />
        )}

        {activeTab === 'arms_race' && (
          <ArmsRaceChart />
        )}

        {activeTab === 'graph' && (
          <SimilarityGraph onSelectIdentity={handleSelectIdentity} />
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-800/80 bg-slate-950/60 py-4 mt-auto">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between text-xs text-slate-500 gap-2">
          <p>
            🛡️ <strong>VeriTrace Sentinel</strong> — Real-time Incubation Forensics & Sleeper Syndicate Defense
          </p>
          <p className="font-mono text-[11px]">
            MasterCard Adversarial Synthetic Identity Defense System
          </p>
        </div>
      </footer>
    </div>
  );
}
