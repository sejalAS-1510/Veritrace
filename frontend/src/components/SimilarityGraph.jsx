import React, { useState, useEffect, useRef } from 'react';
import ForceGraph2D from 'react-force-graph-2d';
import { getSimilarityGraph } from '../api';
import { Network, RefreshCw, Sliders, ShieldAlert, ShieldCheck, Info, Sparkles, ExternalLink } from 'lucide-react';

export default function SimilarityGraph({ onSelectIdentity }) {
  const [graphData, setGraphData] = useState({ nodes: [], edges: [] });
  const [threshold, setThreshold] = useState(0.88);
  const [loading, setLoading] = useState(true);
  const [selectedNode, setSelectedNode] = useState(null);
  const [errorMsg, setErrorMsg] = useState(null);
  const fgRef = useRef();

  useEffect(() => {
    fetchGraph(threshold);
  }, [threshold]);

  const fetchGraph = async (thresh) => {
    try {
      setLoading(true);
      setErrorMsg(null);
      const data = await getSimilarityGraph(thresh);
      
      // Format data for ForceGraph2D (expects { nodes, links })
      const formatted = {
        nodes: (data.nodes || []).map((n) => ({
          ...n,
          val: n.flagged ? 8 : 5,
        })),
        links: (data.edges || []).map((e) => ({
          source: e.source,
          target: e.target,
          weight: e.weight,
        }))
      };
      setGraphData(formatted);
    } catch (err) {
      console.error(err);
      setErrorMsg('Failed to load similarity network graph.');
    } finally {
      setLoading(false);
    }
  };

  const handleNodeClick = (node) => {
    setSelectedNode(node);
  };

  return (
    <div className="space-y-6">
      {/* Header & Filter Controls */}
      <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-5 shadow-lg flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex items-center space-x-3">
          <div className="p-2.5 bg-indigo-500/10 border border-indigo-500/30 rounded-lg text-indigo-400">
            <Network className="w-6 h-6" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-slate-100">Behavioral Cosine Similarity Graph</h3>
            <p className="text-xs text-slate-400">
              Correlating synthetic incubation trajectories to isolate coordinated GenAI fraud rings (clones sharing prompt templates)
            </p>
          </div>
        </div>

        <div className="flex items-center flex-wrap gap-4">
          {/* Threshold Slider */}
          <div className="flex items-center space-x-3 bg-slate-950 px-3.5 py-2 rounded-lg border border-slate-800 text-xs">
            <Sliders className="w-3.5 h-3.5 text-slate-400" />
            <span className="text-slate-400">Cosine Threshold:</span>
            <span className="font-mono font-bold text-cyan-400">{threshold}</span>
            <input
              type="range"
              min="0.70"
              max="0.98"
              step="0.02"
              value={threshold}
              onChange={(e) => setThreshold(parseFloat(e.target.value))}
              className="w-24 accent-cyan-500 cursor-pointer"
            />
          </div>

          <button
            onClick={() => fetchGraph(threshold)}
            className="flex items-center space-x-2 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs px-3.5 py-2 rounded-lg border border-slate-700 transition"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            <span>Recalculate Graph</span>
          </button>
        </div>
      </div>

      {errorMsg && (
        <div className="bg-rose-950/40 border border-rose-800 text-rose-300 px-4 py-3 rounded-lg text-sm">
          {errorMsg}
        </div>
      )}

      {/* Graph Area & Node Inspector */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Main 2D Force Graph (3 cols) */}
        <div className="lg:col-span-3 bg-slate-950/90 border border-slate-800 rounded-xl overflow-hidden shadow-2xl relative h-[540px] flex items-center justify-center">
          {/* Graph Legend Overlay */}
          <div className="absolute top-4 left-4 z-10 bg-slate-900/80 backdrop-blur-md border border-slate-800 px-3.5 py-2.5 rounded-lg text-xs space-y-1.5 shadow-lg">
            <p className="font-bold text-slate-300 text-[11px] uppercase tracking-wider mb-1">Graph Legend</p>
            <div className="flex items-center space-x-2">
              <span className="w-3 h-3 rounded-full bg-rose-500 inline-block shadow-sm shadow-rose-500/50"></span>
              <span className="text-slate-300">Flagged Sleeper Agent (High Risk)</span>
            </div>
            <div className="flex items-center space-x-2">
              <span className="w-3 h-3 rounded-full bg-emerald-500 inline-block shadow-sm shadow-emerald-500/50"></span>
              <span className="text-slate-300">Cleared Organic Human</span>
            </div>
            <div className="flex items-center space-x-2">
              <span className="w-6 h-0.5 bg-cyan-500/80 inline-block"></span>
              <span className="text-slate-300">Trajectory Similarity Edge (&ge; {threshold})</span>
            </div>
          </div>

          {loading ? (
            <div className="text-center space-y-3">
              <RefreshCw className="w-8 h-8 text-cyan-400 animate-spin mx-auto" />
              <p className="text-xs text-slate-400">Computing Trajectory Similarity Matrix...</p>
            </div>
          ) : graphData.nodes.length === 0 ? (
            <div className="text-center space-y-2 p-6">
              <p className="text-sm text-slate-400">No identities available in graph.</p>
              <p className="text-xs text-slate-500">Generate identities from the Live Feed to populate the similarity network.</p>
            </div>
          ) : (
            <ForceGraph2D
              ref={fgRef}
              width={750}
              height={540}
              graphData={graphData}
              backgroundColor="#090D16"
              nodeLabel={(node) => `${node.id} (${node.flagged ? '🚩 Flagged' : '✅ Passed'}) - Risk: ${(node.risk_score * 100).toFixed(0)}%`}
              nodeColor={(node) => (node.flagged ? '#F43F5E' : '#10B981')}
              nodeRelSize={6}
              linkColor={() => 'rgba(6, 182, 212, 0.45)'}
              linkWidth={(link) => (link.weight ? (link.weight - 0.8) * 12 : 1.5)}
              onNodeClick={handleNodeClick}
              nodeCanvasObject={(node, ctx, globalScale) => {
                const label = node.id;
                const fontSize = 11 / globalScale;
                ctx.font = `${fontSize}px JetBrains Mono, monospace`;

                // Node circle
                ctx.beginPath();
                ctx.arc(node.x, node.y, node.flagged ? 7 : 5, 0, 2 * Math.PI, false);
                ctx.fillStyle = node.flagged ? '#F43F5E' : '#10B981';
                ctx.shadowColor = node.flagged ? '#F43F5E' : '#10B981';
                ctx.shadowBlur = node.flagged ? 12 : 6;
                ctx.fill();
                ctx.shadowBlur = 0; // reset

                // Text label
                ctx.textAlign = 'center';
                ctx.textBaseline = 'middle';
                ctx.fillStyle = '#E2E8F0';
                ctx.fillText(label, node.x, node.y + (node.flagged ? 12 : 10));
              }}
            />
          )}
        </div>

        {/* Node Inspector Card (1 col) */}
        <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-5 flex flex-col justify-between">
          <div>
            <div className="flex items-center space-x-2 border-b border-slate-800 pb-3 mb-4">
              <Sparkles className="w-4 h-4 text-cyan-400" />
              <h4 className="text-sm font-semibold text-slate-200 uppercase tracking-wider">Cluster Inspector</h4>
            </div>

            {selectedNode ? (
              <div className="space-y-4">
                <div className="p-3 bg-slate-950 rounded-lg border border-slate-800">
                  <span className="text-[10px] text-slate-500 uppercase tracking-wider font-mono">SELECTED NODE</span>
                  <p className="text-base font-bold text-slate-100 font-mono mt-0.5">{selectedNode.id}</p>
                </div>

                <div className="space-y-2 text-xs">
                  <div className="flex justify-between py-1 border-b border-slate-800/60">
                    <span className="text-slate-400">Ground Truth:</span>
                    <span className={`font-semibold ${selectedNode.type === 'sleeper' ? 'text-purple-400' : 'text-blue-400'}`}>
                      {selectedNode.type === 'sleeper' ? '🤖 Sleeper Agent' : '👤 Organic'}
                    </span>
                  </div>

                  <div className="flex justify-between py-1 border-b border-slate-800/60">
                    <span className="text-slate-400">Sentinel Verdict:</span>
                    <span className={`font-bold ${selectedNode.flagged ? 'text-rose-400' : 'text-emerald-400'}`}>
                      {selectedNode.flagged ? '🚩 Flagged Synthetic' : '✅ Passed Organic'}
                    </span>
                  </div>

                  <div className="flex justify-between py-1 border-b border-slate-800/60">
                    <span className="text-slate-400">Risk Score:</span>
                    <span className={`font-mono font-bold ${selectedNode.risk_score >= 0.65 ? 'text-rose-400' : 'text-emerald-400'}`}>
                      {(selectedNode.risk_score * 100).toFixed(1)}%
                    </span>
                  </div>

                  {selectedNode.ring_id && (
                    <div className="flex justify-between py-1 border-b border-slate-800/60">
                      <span className="text-slate-400">Fraud Ring Cluster:</span>
                      <span className="font-mono text-amber-400 font-bold">{selectedNode.ring_id}</span>
                    </div>
                  )}
                </div>

                {onSelectIdentity && (
                  <button
                    onClick={() => onSelectIdentity(selectedNode.id)}
                    className="w-full flex items-center justify-center space-x-2 bg-emerald-600 hover:bg-emerald-500 text-slate-950 font-bold text-xs py-2.5 rounded-lg transition mt-4"
                  >
                    <span>Inspect Timeline Replay</span>
                    <ExternalLink className="w-3.5 h-3.5" />
                  </button>
                )}
              </div>
            ) : (
              <div className="text-center py-12 text-slate-500 text-xs space-y-2">
                <Info className="w-6 h-6 mx-auto text-slate-600" />
                <p>Click on any node in the graph to inspect identity telemetry, cluster peers, and fraud ring tags.</p>
              </div>
            )}
          </div>

          <div className="mt-4 p-3 bg-slate-950/60 rounded-lg border border-slate-800/80 text-[11px] text-slate-400">
            <p>
              <strong className="text-slate-300">Fraud Ring Detection:</strong> Sleeper agents generated from identical LLM prompt templates exhibit tightly clustered cosine similarity (&gt;0.90), revealing coordinated syndicates.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
