import React, { useState, useEffect, useRef } from 'react';
import { getSimilarityGraph } from '../api';
import { 
  Network, 
  RefreshCw, 
  Sliders, 
  ShieldAlert, 
  ShieldCheck, 
  Info, 
  Sparkles, 
  ExternalLink, 
  Users, 
  ZoomIn, 
  ZoomOut, 
  Maximize2, 
  Minimize2,
  Search, 
  Check, 
  Copy,
  Lock,
  Unlock,
  Move
} from 'lucide-react';

export default function SimilarityGraph({ onSelectIdentity, showToast }) {
  const [rawData, setRawData] = useState({ nodes: [], edges: [], fraud_rings: [] });
  const [nodes, setNodes] = useState([]);
  const [edges, setEdges] = useState([]);
  const [threshold, setThreshold] = useState(0.88);
  const [loading, setLoading] = useState(true);
  const [selectedNode, setSelectedNode] = useState(null);
  const [highlightedRing, setHighlightedRing] = useState(null);
  const [quarantinedRings, setQuarantinedRings] = useState(new Set());
  const [searchQuery, setSearchQuery] = useState('');
  const [copiedId, setCopiedId] = useState(false);
  const [errorMsg, setErrorMsg] = useState(null);
  const [isFullscreen, setIsFullscreen] = useState(false);

  // Dynamic dimensions
  const [dimensions, setDimensions] = useState({ width: 760, height: 580 });

  // Pan & Zoom state
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [isPanning, setIsPanning] = useState(false);
  const [startPan, setStartPan] = useState({ x: 0, y: 0 });
  const [draggedNode, setDraggedNode] = useState(null);

  const containerRef = useRef(null);
  const animFrameRef = useRef(null);

  // ResizeObserver to ensure 100% responsiveness on any screen
  useEffect(() => {
    if (!containerRef.current) return;
    const observer = new ResizeObserver((entries) => {
      for (const entry of entries) {
        if (entry.contentRect.width > 0) {
          setDimensions({
            width: Math.max(320, entry.contentRect.width),
            height: isFullscreen ? Math.max(500, window.innerHeight - 120) : 580
          });
        }
      }
    });
    observer.observe(containerRef.current);
    return () => observer.disconnect();
  }, [isFullscreen]);

  useEffect(() => {
    fetchGraphData(threshold);
  }, [threshold]);

  const fetchGraphData = async (thresh) => {
    try {
      setLoading(true);
      setErrorMsg(null);
      const data = await getSimilarityGraph(thresh);
      setRawData(data);

      const rawNodes = data.nodes || [];
      const rawEdges = data.edges || [];

      // Initialize node positions in a radial cluster
      const initializedNodes = rawNodes.map((n, idx) => {
        const angle = (idx / Math.max(1, rawNodes.length)) * 2 * Math.PI;
        const radius = n.ring_id ? 110 + (idx % 3) * 35 : 170 + (idx % 4) * 30;
        return {
          ...n,
          x: dimensions.width / 2 + radius * Math.cos(angle) + (Math.random() - 0.5) * 20,
          y: dimensions.height / 2 + radius * Math.sin(angle) + (Math.random() - 0.5) * 20,
          vx: 0,
          vy: 0,
          radius: n.flagged ? 16 : 13
        };
      });

      setNodes(initializedNodes);
      setEdges(rawEdges);
    } catch (err) {
      console.error(err);
      setErrorMsg('Failed to load network graph from Sentinel API.');
    } finally {
      setLoading(false);
    }
  };

  // Run physics spring-repulsion simulation on nodes
  useEffect(() => {
    if (nodes.length === 0) return;

    let iterations = 0;
    const maxIterations = 80;

    const stepSimulation = () => {
      setNodes((prevNodes) => {
        if (prevNodes.length === 0) return prevNodes;
        const newNodes = prevNodes.map((n) => ({ ...n }));
        const nodeMap = new Map(newNodes.map((n) => [n.id, n]));

        const kRep = 3200;
        const kAtt = 0.045;
        const kGrav = 0.02;
        const targetDist = 110;

        // 1. Repulsion between all pairs
        for (let i = 0; i < newNodes.length; i++) {
          for (let j = i + 1; j < newNodes.length; j++) {
            const n1 = newNodes[i];
            const n2 = newNodes[j];
            let dx = n2.x - n1.x;
            let dy = n2.y - n1.y;
            let dist = Math.sqrt(dx * dx + dy * dy) || 1;

            if (dist < 320) {
              const force = kRep / (dist * dist + 100);
              const fx = (dx / dist) * force;
              const fy = (dy / dist) * force;

              if (draggedNode !== n1.id) {
                n1.vx -= fx;
                n1.vy -= fy;
              }
              if (draggedNode !== n2.id) {
                n2.vx += fx;
                n2.vy += fy;
              }
            }
          }
        }

        // 2. Attraction along similarity edges
        for (const edge of edges) {
          const sId = typeof edge.source === 'object' ? edge.source.id : edge.source;
          const tId = typeof edge.target === 'object' ? edge.target.id : edge.target;
          const n1 = nodeMap.get(sId);
          const n2 = nodeMap.get(tId);

          if (n1 && n2) {
            let dx = n2.x - n1.x;
            let dy = n2.y - n1.y;
            let dist = Math.sqrt(dx * dx + dy * dy) || 1;
            const weight = edge.weight || 0.9;
            const displacement = dist - targetDist;
            const force = kAtt * displacement * weight;

            const fx = (dx / dist) * force;
            const fy = (dy / dist) * force;

            if (draggedNode !== n1.id) {
              n1.vx -= fx;
              n1.vy -= fy;
            }
            if (draggedNode !== n2.id) {
              n2.vx += fx;
              n2.vy += fy;
            }
          }
        }

        // 3. Gravity towards center + Velocity damping
        for (const n of newNodes) {
          if (draggedNode === n.id) continue;

          const cdx = dimensions.width / 2 - n.x;
          const cdy = dimensions.height / 2 - n.y;
          n.vx += cdx * kGrav;
          n.vy += cdy * kGrav;

          n.vx *= 0.82;
          n.vy *= 0.82;

          n.x += n.vx;
          n.y += n.vy;

          n.x = Math.max(30, Math.min(dimensions.width - 30, n.x));
          n.y = Math.max(30, Math.min(dimensions.height - 30, n.y));
        }

        return newNodes;
      });

      iterations++;
      if (iterations < maxIterations || draggedNode) {
        animFrameRef.current = requestAnimationFrame(stepSimulation);
      }
    };

    animFrameRef.current = requestAnimationFrame(stepSimulation);

    return () => {
      if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current);
    };
  }, [edges, draggedNode, dimensions]);

  // Pan & Zoom controls
  const handleWheel = (e) => {
    e.preventDefault();
    const zoomFactor = e.deltaY < 0 ? 1.1 : 0.9;
    setZoom((prev) => Math.max(0.4, Math.min(3.0, prev * zoomFactor)));
  };

  const handleMouseDown = (e) => {
    if (e.target.tagName === 'svg' || e.target.id === 'graph-bg') {
      setIsPanning(true);
      setStartPan({ x: e.clientX - pan.x, y: e.clientY - pan.y });
    }
  };

  const handleMouseMove = (e) => {
    if (isPanning) {
      setPan({
        x: e.clientX - startPan.x,
        y: e.clientY - startPan.y
      });
    } else if (draggedNode) {
      const svgRect = containerRef.current?.getBoundingClientRect();
      if (svgRect) {
        const mouseX = (e.clientX - svgRect.left - pan.x) / zoom;
        const mouseY = (e.clientY - svgRect.top - pan.y) / zoom;
        setNodes((prev) =>
          prev.map((n) => (n.id === draggedNode ? { ...n, x: mouseX, y: mouseY, vx: 0, vy: 0 } : n))
        );
      }
    }
  };

  const handleMouseUp = () => {
    setIsPanning(false);
    setDraggedNode(null);
  };

  const handleNodeMouseDown = (e, node) => {
    e.stopPropagation();
    setDraggedNode(node.id);
    setSelectedNode(node);
  };

  const handleRingClick = (ring) => {
    if (highlightedRing === ring.ring_id) {
      setHighlightedRing(null);
    } else {
      setHighlightedRing(ring.ring_id);
      const ringNodes = nodes.filter((n) => n.ring_id === ring.ring_id);
      if (ringNodes.length > 0) {
        const avgX = ringNodes.reduce((acc, n) => acc + n.x, 0) / ringNodes.length;
        const avgY = ringNodes.reduce((acc, n) => acc + n.y, 0) / ringNodes.length;
        setPan({
          x: dimensions.width / 2 - avgX * 1.5,
          y: dimensions.height / 2 - avgY * 1.5
        });
        setZoom(1.5);
      }
      if (showToast) showToast(`Highlighting syndicate ${ring.ring_id} (${ring.size} accounts)`, 'info');
    }
  };

  const handleQuarantineRing = (ringId) => {
    setQuarantinedRings((prev) => {
      const next = new Set(prev);
      if (next.has(ringId)) {
        next.delete(ringId);
        if (showToast) showToast(`Unblocked syndicate ${ringId}`, 'info');
      } else {
        next.add(ringId);
        if (showToast) showToast(`Quarantined and blocked syndicate ${ringId}!`, 'alert');
      }
      return next;
    });
  };

  const handleSearch = (e) => {
    e.preventDefault();
    if (!searchQuery.trim()) return;
    const target = nodes.find((n) => n.id.toLowerCase().includes(searchQuery.toLowerCase().trim()));
    if (target) {
      setSelectedNode(target);
      setPan({
        x: dimensions.width / 2 - target.x * 1.8,
        y: dimensions.height / 2 - target.y * 1.8
      });
      setZoom(1.8);
      if (showToast) showToast(`Found identity ${target.id}`, 'success');
    } else {
      if (showToast) showToast(`Identity "${searchQuery}" not found in graph`, 'info');
    }
  };

  const resetView = () => {
    setZoom(1);
    setPan({ x: 0, y: 0 });
    setSelectedNode(null);
    setHighlightedRing(null);
  };

  const copyId = (text) => {
    navigator.clipboard.writeText(text);
    setCopiedId(true);
    setTimeout(() => setCopiedId(false), 2000);
    if (showToast) showToast(`Copied ${text}`, 'info');
  };

  const nodePositionMap = new Map(nodes.map((n) => [n.id, n]));

  const connectedEdges = selectedNode
    ? edges.filter((e) => {
        const s = typeof e.source === 'object' ? e.source.id : e.source;
        const t = typeof e.target === 'object' ? e.target.id : e.target;
        return s === selectedNode.id || t === selectedNode.id;
      })
    : [];

  return (
    <div className={`space-y-6 ${isFullscreen ? 'fixed inset-0 z-50 bg-[#070A13] p-6 overflow-y-auto' : ''}`}>
      {/* Header & Filter Controls */}
      <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-4 sm:p-5 shadow-lg flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex items-center space-x-3">
          <div className="p-2.5 bg-indigo-500/10 border border-indigo-500/30 rounded-lg text-indigo-400">
            <Network className="w-6 h-6" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h3 className="text-lg font-semibold text-slate-100">Behavioral Cosine Similarity Graph</h3>
              <span className="text-[10px] px-2 py-0.5 rounded bg-indigo-950 text-indigo-300 font-mono border border-indigo-800 font-bold hidden sm:inline-block">
                NetworkX Cluster Forensics
              </span>
            </div>
            <p className="text-xs text-slate-400">
              Correlating synthetic incubation trajectories to isolate coordinated GenAI fraud rings (clones sharing prompt templates)
            </p>
          </div>
        </div>

        <div className="flex items-center flex-wrap gap-2.5">
          {/* Node Search Bar */}
          <form onSubmit={handleSearch} className="relative flex-1 sm:flex-initial">
            <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Find node ID..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="bg-slate-950 border border-slate-700 rounded-lg pl-8 pr-3 py-1.5 text-xs text-slate-100 font-mono focus:border-cyan-500 focus:outline-none w-full sm:w-36"
            />
          </form>

          {/* Threshold Slider */}
          <div className="flex items-center space-x-2 bg-slate-950 px-2.5 py-1.5 rounded-lg border border-slate-800 text-xs">
            <Sliders className="w-3.5 h-3.5 text-slate-400" />
            <span className="text-slate-400">Cosine:</span>
            <span className="font-mono font-bold text-cyan-400">{threshold.toFixed(2)}</span>
            <input
              type="range"
              min="0.70"
              max="0.98"
              step="0.02"
              value={threshold}
              onChange={(e) => setThreshold(parseFloat(e.target.value))}
              className="w-16 sm:w-20 accent-cyan-500 cursor-pointer"
            />
          </div>

          <button
            onClick={() => fetchGraphData(threshold)}
            className="flex items-center space-x-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs px-3 py-1.5 rounded-lg border border-slate-700 transition"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            <span className="hidden sm:inline">Recalculate</span>
          </button>
        </div>
      </div>

      {errorMsg && (
        <div className="bg-rose-950/40 border border-rose-800 text-rose-300 px-4 py-3 rounded-lg text-sm">
          {errorMsg}
        </div>
      )}

      {/* Graph Area & Sidebars */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Main Interactive SVG Canvas Graph (3 cols) */}
        <div 
          ref={containerRef}
          className={`lg:col-span-3 bg-slate-950/95 border border-slate-800 rounded-xl overflow-hidden shadow-2xl relative select-none flex items-center justify-center ${
            isFullscreen ? 'h-[75vh]' : 'h-[480px] sm:h-[580px]'
          }`}
          onWheel={handleWheel}
          onMouseDown={handleMouseDown}
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
        >
          {/* Graph Legend Overlay */}
          <div className="absolute top-4 left-4 z-10 bg-slate-900/85 backdrop-blur-md border border-slate-800 px-3 py-2 rounded-lg text-xs space-y-1 shadow-lg pointer-events-none">
            <p className="font-bold text-slate-300 text-[10px] uppercase tracking-wider mb-0.5">Graph Legend</p>
            <div className="flex items-center space-x-2">
              <span className="w-2.5 h-2.5 rounded-full bg-rose-500 inline-block shadow-sm shadow-rose-500/50"></span>
              <span className="text-slate-300 text-[11px]">Flagged Sleeper</span>
            </div>
            <div className="flex items-center space-x-2">
              <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 inline-block shadow-sm shadow-emerald-500/50"></span>
              <span className="text-slate-300 text-[11px]">Organic Human</span>
            </div>
            <div className="flex items-center space-x-2">
              <span className="w-5 h-0.5 bg-cyan-500/80 inline-block"></span>
              <span className="text-slate-300 text-[11px]">Similarity Edge</span>
            </div>
          </div>

          {/* Interactive Zoom Toolbar Overlay */}
          <div className="absolute top-4 right-4 z-10 bg-slate-900/85 backdrop-blur-md border border-slate-800 p-1.5 rounded-lg flex flex-col space-y-1 shadow-lg">
            <button
              onClick={() => setZoom((z) => Math.min(3.0, z * 1.25))}
              className="p-1.5 hover:bg-slate-800 text-slate-300 hover:text-white rounded transition"
              title="Zoom In"
            >
              <ZoomIn className="w-4 h-4" />
            </button>
            <button
              onClick={() => setZoom((z) => Math.max(0.4, z * 0.8))}
              className="p-1.5 hover:bg-slate-800 text-slate-300 hover:text-white rounded transition"
              title="Zoom Out"
            >
              <ZoomOut className="w-4 h-4" />
            </button>
            <button
              onClick={resetView}
              className="p-1.5 hover:bg-slate-800 text-slate-300 hover:text-white rounded transition"
              title="Reset View"
            >
              <RefreshCw className="w-4 h-4" />
            </button>
            <button
              onClick={() => setIsFullscreen(!isFullscreen)}
              className="p-1.5 hover:bg-slate-800 text-slate-300 hover:text-white rounded transition"
              title={isFullscreen ? "Exit Fullscreen" : "Fullscreen"}
            >
              {isFullscreen ? <Minimize2 className="w-4 h-4" /> : <Maximize2 className="w-4 h-4" />}
            </button>
          </div>

          {/* Stats badge overlay */}
          <div className="absolute bottom-4 left-4 z-10 bg-slate-900/80 backdrop-blur-md border border-slate-800 px-3 py-1.5 rounded-lg text-[10px] sm:text-[11px] font-mono text-slate-400 flex items-center space-x-2 sm:space-x-3 pointer-events-none">
            <span>Nodes: <strong className="text-slate-200">{nodes.length}</strong></span>
            <span>Edges: <strong className="text-cyan-400">{edges.length}</strong></span>
            <span className="hidden sm:inline">Zoom: {(zoom * 100).toFixed(0)}%</span>
          </div>

          {/* Drag instruction overlay */}
          <div className="absolute bottom-4 right-4 z-10 text-[10px] text-slate-500 font-mono pointer-events-none hidden sm:flex items-center space-x-1">
            <Move className="w-3 h-3" />
            <span>Drag nodes to reposition</span>
          </div>

          {loading ? (
            <div className="text-center space-y-3">
              <RefreshCw className="w-8 h-8 text-cyan-400 animate-spin mx-auto" />
              <p className="text-xs text-slate-400">Computing NetworkX Cosine Similarity Matrix...</p>
            </div>
          ) : nodes.length === 0 ? (
            <div className="text-center space-y-2 p-6">
              <p className="text-sm text-slate-400">No identities available in graph.</p>
              <p className="text-xs text-slate-500">Generate identities from the Live Feed to populate the similarity network.</p>
            </div>
          ) : (
            <svg
              id="graph-bg"
              width="100%"
              height="100%"
              viewBox={`0 0 ${dimensions.width} ${dimensions.height}`}
              className="cursor-grab active:cursor-grabbing w-full h-full"
            >
              <defs>
                <filter id="glow-rose" x="-50%" y="-50%" width="200%" height="200%">
                  <feGaussianBlur stdDeviation="4" result="coloredBlur" />
                  <feMerge>
                    <feMergeNode in="coloredBlur" />
                    <feMergeNode in="SourceGraphic" />
                  </feMerge>
                </filter>
                <filter id="glow-gold" x="-50%" y="-50%" width="200%" height="200%">
                  <feGaussianBlur stdDeviation="6" result="coloredBlur" />
                  <feMerge>
                    <feMergeNode in="coloredBlur" />
                    <feMergeNode in="SourceGraphic" />
                  </feMerge>
                </filter>
                <filter id="glow-cyan" x="-50%" y="-50%" width="200%" height="200%">
                  <feGaussianBlur stdDeviation="5" result="coloredBlur" />
                  <feMerge>
                    <feMergeNode in="coloredBlur" />
                    <feMergeNode in="SourceGraphic" />
                  </feMerge>
                </filter>
              </defs>

              <g transform={`translate(${pan.x}, ${pan.y}) scale(${zoom})`}>
                {/* 1. Draw Edges */}
                {edges.map((edge, idx) => {
                  const sId = typeof edge.source === 'object' ? edge.source.id : edge.source;
                  const tId = typeof edge.target === 'object' ? edge.target.id : edge.target;
                  const sNode = nodePositionMap.get(sId);
                  const tNode = nodePositionMap.get(tId);

                  if (!sNode || !tNode) return null;

                  const isConnectedToSelected = selectedNode && (sId === selectedNode.id || tId === selectedNode.id);
                  const isRingEdge = highlightedRing && sNode.ring_id === highlightedRing && tNode.ring_id === highlightedRing;
                  const strokeColor = isRingEdge 
                    ? '#F59E0B' 
                    : isConnectedToSelected 
                    ? '#06B6D4' 
                    : 'rgba(6, 182, 212, 0.35)';

                  const strokeWidth = isRingEdge ? 2.5 : isConnectedToSelected ? 2.2 : Math.max(1, (edge.weight - 0.8) * 8);

                  return (
                    <line
                      key={idx}
                      x1={sNode.x}
                      y1={sNode.y}
                      x2={tNode.x}
                      y2={tNode.y}
                      stroke={strokeColor}
                      strokeWidth={strokeWidth}
                      strokeOpacity={isRingEdge || isConnectedToSelected ? 0.95 : 0.6}
                    />
                  );
                })}

                {/* 2. Draw Nodes */}
                {nodes.map((node) => {
                  const isSelected = selectedNode && node.id === selectedNode.id;
                  const isRingMember = highlightedRing && node.ring_id === highlightedRing;
                  const isQuarantined = node.ring_id && quarantinedRings.has(node.ring_id);

                  let fillColor = node.flagged ? '#F43F5E' : '#10B981';
                  let filterId = node.flagged ? 'url(#glow-rose)' : undefined;

                  if (isQuarantined) {
                    fillColor = '#991B1B';
                  } else if (isRingMember) {
                    fillColor = '#F59E0B';
                    filterId = 'url(#glow-gold)';
                  } else if (isSelected) {
                    fillColor = '#06B6D4';
                    filterId = 'url(#glow-cyan)';
                  }

                  const radius = isSelected ? 18 : isRingMember ? 16 : (node.flagged ? 14 : 11);

                  return (
                    <g
                      key={node.id}
                      transform={`translate(${node.x}, ${node.y})`}
                      className="cursor-pointer"
                      onMouseDown={(e) => handleNodeMouseDown(e, node)}
                      onClick={(e) => {
                        e.stopPropagation();
                        setSelectedNode(node);
                      }}
                    >
                      {/* Outer pulse ring for highlighted or selected */}
                      {(isRingMember || isSelected) && (
                        <circle
                          r={radius + 6}
                          fill="none"
                          stroke={isRingMember ? '#F59E0B' : '#06B6D4'}
                          strokeWidth="2"
                          strokeDasharray="4 3"
                          className="animate-spin"
                          style={{ animationDuration: '6s' }}
                        />
                      )}

                      {/* Main Node Circle */}
                      <circle
                        r={radius}
                        fill={fillColor}
                        filter={filterId}
                        stroke="#0F172A"
                        strokeWidth="2.5"
                      />

                      {/* Node Text Label */}
                      <text
                        y={radius + 13}
                        textAnchor="middle"
                        fill={isRingMember ? '#FDE68A' : isSelected ? '#A5F3FC' : '#CBD5E1'}
                        fontSize="10px"
                        fontFamily="monospace"
                        fontWeight={isSelected || isRingMember ? 'bold' : 'normal'}
                        className="pointer-events-none drop-shadow"
                      >
                        {node.id}
                      </text>
                    </g>
                  );
                })}
              </g>
            </svg>
          )}
        </div>

        {/* Node Inspector & Fraud Rings Panel (1 col) */}
        <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4 sm:p-5 flex flex-col justify-between space-y-4 shadow-lg">
          <div>
            <div className="flex items-center space-x-2 border-b border-slate-800 pb-3 mb-4">
              <Sparkles className="w-4 h-4 text-cyan-400" />
              <h4 className="text-sm font-semibold text-slate-200 uppercase tracking-wider">Cluster Dossier</h4>
            </div>

            {selectedNode ? (
              <div className="space-y-3.5">
                <div className="p-3 bg-slate-950 rounded-lg border border-slate-800">
                  <span className="text-[10px] text-slate-500 uppercase tracking-wider font-mono">SELECTED IDENTITY</span>
                  <div className="flex items-center justify-between mt-0.5">
                    <p className="text-base font-bold text-slate-100 font-mono">{selectedNode.id}</p>
                    <button onClick={() => copyId(selectedNode.id)} className="text-slate-400 hover:text-white">
                      {copiedId ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                    </button>
                  </div>
                </div>

                <div className="space-y-2 text-xs">
                  <div className="flex justify-between py-1 border-b border-slate-800/60">
                    <span className="text-slate-400">Ground Truth:</span>
                    <span className={`font-semibold ${selectedNode.type === 'sleeper' ? 'text-purple-400' : 'text-blue-400'}`}>
                      {selectedNode.type === 'sleeper' ? 'Sleeper Agent' : 'Organic'}
                    </span>
                  </div>

                  <div className="flex justify-between py-1 border-b border-slate-800/60">
                    <span className="text-slate-400">Sentinel Verdict:</span>
                    <span className={`font-bold ${selectedNode.flagged ? 'text-rose-400' : 'text-emerald-400'}`}>
                      {selectedNode.flagged ? 'Flagged Synthetic' : 'Passed Organic'}
                    </span>
                  </div>

                  <div className="flex justify-between py-1 border-b border-slate-800/60">
                    <span className="text-slate-400">Risk Score:</span>
                    <span className={`font-mono font-bold ${(selectedNode.risk_score * 100) >= 55 ? 'text-rose-400' : 'text-emerald-400'}`}>
                      {(selectedNode.risk_score * 100).toFixed(1)}%
                    </span>
                  </div>

                  {selectedNode.ring_id && (
                    <div className="flex justify-between py-1 border-b border-slate-800/60">
                      <span className="text-slate-400">Syndicate Ring:</span>
                      <span className="font-mono text-amber-400 font-bold">{selectedNode.ring_id}</span>
                    </div>
                  )}

                  <div className="flex justify-between py-1 border-b border-slate-800/60">
                    <span className="text-slate-400">Connected Peers:</span>
                    <span className="font-mono text-cyan-400 font-bold">{connectedEdges.length} accounts</span>
                  </div>
                </div>

                {onSelectIdentity && (
                  <button
                    onClick={() => onSelectIdentity(selectedNode.id)}
                    className="w-full flex items-center justify-center space-x-2 bg-emerald-600 hover:bg-emerald-500 text-slate-950 font-bold text-xs py-2.5 rounded-lg transition mt-3 shadow-md"
                  >
                    <span>Inspect 24-Week Replay</span>
                    <ExternalLink className="w-3.5 h-3.5" />
                  </button>
                )}
              </div>
            ) : (
              <div className="text-center py-5 text-slate-500 text-xs space-y-2">
                <Info className="w-6 h-6 mx-auto text-slate-600" />
                <p>Click on any node in the network to inspect identity telemetry and cluster connections.</p>
              </div>
            )}

            {/* Detected Fraud Rings Syndicate List with Quarantine Action */}
            {rawData.fraud_rings && rawData.fraud_rings.length > 0 && (
              <div className="mt-4 pt-3.5 border-t border-slate-800 space-y-2">
                <div className="flex items-center justify-between text-xs">
                  <div className="flex items-center space-x-1.5 font-semibold text-amber-300">
                    <Users className="w-3.5 h-3.5 text-amber-400" />
                    <span>Detected Fraud Rings ({rawData.fraud_rings.length})</span>
                  </div>
                </div>

                <div className="space-y-1.5 max-h-40 overflow-y-auto">
                  {rawData.fraud_rings.map((ring, idx) => {
                    const isQuarantined = quarantinedRings.has(ring.ring_id);
                    return (
                      <div
                        key={idx}
                        className={`w-full p-2 rounded-lg border text-xs flex items-center justify-between transition ${
                          highlightedRing === ring.ring_id
                            ? 'bg-amber-950/80 border-amber-700 text-amber-200 shadow-md'
                            : isQuarantined
                            ? 'bg-rose-950/40 border-rose-800/80 text-rose-200'
                            : 'bg-slate-950/60 border-slate-800 text-slate-300'
                        }`}
                      >
                        <button
                          onClick={() => handleRingClick(ring)}
                          className="flex-1 text-left flex items-center space-x-2"
                        >
                          <span className="font-mono font-bold">{ring.ring_id}</span>
                          <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-900 border border-slate-700 text-slate-400">
                            {ring.size} members
                          </span>
                        </button>

                        <button
                          onClick={() => handleQuarantineRing(ring.ring_id)}
                          className={`text-[10px] px-2 py-0.5 rounded font-bold transition ${
                            isQuarantined
                              ? 'bg-rose-900 hover:bg-rose-800 text-white'
                              : 'bg-slate-800 hover:bg-rose-900/60 text-slate-300 hover:text-rose-200'
                          }`}
                          title={isQuarantined ? 'Unblock syndicate' : 'Quarantine all accounts in ring'}
                        >
                          {isQuarantined ? 'Quarantined' : 'Quarantine'}
                        </button>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </div>

          <div className="p-3 bg-slate-950/70 rounded-lg border border-slate-800/80 text-[11px] text-slate-400">
            <p>
              <strong className="text-slate-300">Syndicate Quarantine:</strong> Quarantining a fraud ring cluster automatically freezes all credit lines across all {highlightedRing ? 'ring members' : 'correlated accounts'}.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
