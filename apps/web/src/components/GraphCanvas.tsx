import React, { useRef, useEffect, useState, useMemo } from 'react';
import type { GraphNode, GraphEdge } from '../types';
import { ZoomIn, ZoomOut, RotateCcw, Table as TableIcon, Network } from 'lucide-react';

interface Props {
  nodes: GraphNode[];
  edges: GraphEdge[];
  onSelectNode: (node: GraphNode | null) => void;
  selectedNodeId?: string | null;
}

const CATEGORY_COLORS: Record<string, string> = {
  Technology: '#10b981', // emerald
  Organization: '#a855f7', // purple
  Concept: '#06b6d4',     // cyan
  Project: '#f59e0b',     // amber
  Person: '#ec4899',      // pink
  Language: '#3b82f6',    // blue
  Database: '#6366f1',    // indigo
  default: '#64748b'      // slate
};

export const GraphCanvas: React.FC<Props> = ({ nodes, edges, onSelectNode, selectedNodeId }) => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const [viewMode, setViewMode] = useState<'canvas' | 'table'>('canvas');
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });

  // Initialize node positions in a circular/force distribution
  const simNodes = useMemo(() => {
    const width = 800;
    const height = 550;
    const radius = Math.min(width, height) * 0.38;
    const angleStep = (2 * Math.PI) / (nodes.length || 1);

    return nodes.map((node, i) => ({
      ...node,
      x: width / 2 + radius * Math.cos(i * angleStep) + (Math.random() - 0.5) * 40,
      y: height / 2 + radius * Math.sin(i * angleStep) + (Math.random() - 0.5) * 40,
      vx: 0,
      vy: 0
    }));
  }, [nodes]);

  // Run a quick physics relaxation loop
  useEffect(() => {
    if (simNodes.length === 0) return;

    for (let step = 0; step < 60; step++) {
      // Repulsion between all nodes
      for (let i = 0; i < simNodes.length; i++) {
        for (let j = i + 1; j < simNodes.length; j++) {
          const dx = simNodes[j].x! - simNodes[i].x!;
          const dy = simNodes[j].y! - simNodes[i].y!;
          const dist = Math.sqrt(dx * dx + dy * dy) || 1;
          if (dist < 260) {
            const force = (260 - dist) / dist * 0.08;
            simNodes[i].x! -= dx * force;
            simNodes[i].y! -= dy * force;
            simNodes[j].x! += dx * force;
            simNodes[j].y! += dy * force;
          }
        }
      }

      // Spring attraction along edges
      const nodeMap = new Map(simNodes.map(n => [n.id, n]));
      for (const edge of edges) {
        const s = nodeMap.get(edge.source);
        const t = nodeMap.get(edge.target);
        if (s && t) {
          const dx = t.x! - s.x!;
          const dy = t.y! - s.y!;
          const dist = Math.sqrt(dx * dx + dy * dy) || 1;
          const force = (dist - 120) * 0.04;
          s.x! += (dx / dist) * force;
          s.y! += (dy / dist) * force;
          t.x! -= (dx / dist) * force;
          t.y! -= (dy / dist) * force;
        }
      }
    }
  }, [simNodes, edges]);

  // Draw canvas
  useEffect(() => {
    if (viewMode !== 'canvas') return;
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    ctx.save();
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Apply pan & zoom
    ctx.translate(pan.x, pan.y);
    ctx.scale(zoom, zoom);

    const nodeMap = new Map(simNodes.map(n => [n.id, n]));

    // Draw edges
    for (const edge of edges) {
      const s = nodeMap.get(edge.source);
      const t = nodeMap.get(edge.target);
      if (s && t) {
        const isHighlight = selectedNodeId && (s.id === selectedNodeId || t.id === selectedNodeId);
        ctx.beginPath();
        ctx.moveTo(s.x!, s.y!);
        ctx.lineTo(t.x!, t.y!);
        ctx.strokeStyle = isHighlight ? '#60a5fa' : '#334155';
        ctx.lineWidth = isHighlight ? 2.5 : 1.2;
        ctx.stroke();

        // Edge label
        const midX = (s.x! + t.x!) / 2;
        const midY = (s.y! + t.y!) / 2;
        ctx.font = '10px sans-serif';
        ctx.fillStyle = isHighlight ? '#93c5fd' : '#64748b';
        ctx.fillText(edge.relation, midX + 4, midY - 4);
      }
    }

    // Draw nodes
    for (const node of simNodes) {
      const isSelected = selectedNodeId === node.id;
      const color = CATEGORY_COLORS[node.category] || CATEGORY_COLORS.default;
      const radius = 16 + Math.min(node.degree * 2.5, 14);

      // Outer glow for selected
      if (isSelected) {
        ctx.beginPath();
        ctx.arc(node.x!, node.y!, radius + 6, 0, Math.PI * 2);
        ctx.fillStyle = 'rgba(96, 165, 250, 0.3)';
        ctx.fill();
      }

      // Circle
      ctx.beginPath();
      ctx.arc(node.x!, node.y!, radius, 0, Math.PI * 2);
      ctx.fillStyle = color;
      ctx.fill();
      ctx.lineWidth = 2;
      ctx.strokeStyle = isSelected ? '#ffffff' : '#1e293b';
      ctx.stroke();

      // Node label
      ctx.font = isSelected ? 'bold 12px sans-serif' : '11px sans-serif';
      ctx.fillStyle = '#f1f5f9';
      ctx.textAlign = 'center';
      ctx.fillText(node.name, node.x!, node.y! + radius + 15);

      // Category badge
      ctx.font = '9px sans-serif';
      ctx.fillStyle = '#94a3b8';
      ctx.fillText(node.category, node.x!, node.y! + radius + 27);
    }

    ctx.restore();
  }, [simNodes, edges, zoom, pan, selectedNodeId, viewMode]);

  // Handle canvas click to select node
  const handleCanvasClick = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    const clickX = (e.clientX - rect.left - pan.x) / zoom;
    const clickY = (e.clientY - rect.top - pan.y) / zoom;

    let clicked: GraphNode | null = null;
    for (const node of simNodes) {
      const radius = 16 + Math.min(node.degree * 2.5, 14);
      const dx = clickX - node.x!;
      const dy = clickY - node.y!;
      if (dx * dx + dy * dy <= radius * radius) {
        clicked = node;
        break;
      }
    }
    onSelectNode(clicked);
  };

  const handleMouseDown = (e: React.MouseEvent) => {
    setIsDragging(true);
    setDragStart({ x: e.clientX - pan.x, y: e.clientY - pan.y });
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (!isDragging) return;
    setPan({ x: e.clientX - dragStart.x, y: e.clientY - dragStart.y });
  };

  const handleMouseUp = () => setIsDragging(false);

  return (
    <div className="flex flex-col bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-xl">
      {/* Top Toolbar */}
      <div className="flex items-center justify-between px-4 py-2.5 bg-slate-950/80 border-b border-slate-800">
        <div className="flex items-center gap-2">
          <button
            onClick={() => setViewMode('canvas')}
            className={`flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-medium transition-colors ${
              viewMode === 'canvas' ? 'bg-blue-600 text-white' : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <Network className="w-3.5 h-3.5" />
            Interactive Graph
          </button>
          <button
            onClick={() => setViewMode('table')}
            className={`flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-medium transition-colors ${
              viewMode === 'table' ? 'bg-blue-600 text-white' : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <TableIcon className="w-3.5 h-3.5" />
            Accessible Table
          </button>
        </div>

        {viewMode === 'canvas' && (
          <div className="flex items-center gap-1 bg-slate-900 px-2 py-1 rounded-lg border border-slate-800">
            <button
              onClick={() => setZoom(z => Math.min(z + 0.15, 2.5))}
              className="p-1 text-slate-400 hover:text-slate-200"
              title="Zoom In"
            >
              <ZoomIn className="w-4 h-4" />
            </button>
            <button
              onClick={() => setZoom(z => Math.max(z - 0.15, 0.4))}
              className="p-1 text-slate-400 hover:text-slate-200"
              title="Zoom Out"
            >
              <ZoomOut className="w-4 h-4" />
            </button>
            <button
              onClick={() => { setZoom(1); setPan({ x: 0, y: 0 }); }}
              className="p-1 text-slate-400 hover:text-slate-200"
              title="Reset View"
            >
              <RotateCcw className="w-4 h-4" />
            </button>
            <span className="text-[11px] text-slate-400 ml-1 font-mono">{Math.round(zoom * 100)}%</span>
          </div>
        )}
      </div>

      {/* Main View Area */}
      {viewMode === 'canvas' ? (
        <div className="relative w-full h-[550px] bg-slate-950/60 overflow-hidden cursor-grab active:cursor-grabbing">
          <canvas
            ref={canvasRef}
            width={850}
            height={550}
            onClick={handleCanvasClick}
            onMouseDown={handleMouseDown}
            onMouseMove={handleMouseMove}
            onMouseUp={handleMouseUp}
            onMouseLeave={handleMouseUp}
            className="w-full h-full block"
          />
          {nodes.length === 0 && (
            <div className="absolute inset-0 flex items-center justify-center text-slate-500 text-sm">
              No graph entities or relationships recorded yet.
            </div>
          )}
        </div>
      ) : (
        <div className="p-4 max-h-[550px] overflow-y-auto">
          <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">Entities ({nodes.length})</h4>
          <table className="w-full text-left text-xs mb-6 border-collapse">
            <thead>
              <tr className="border-b border-slate-800 text-slate-400">
                <th className="py-2">Name</th>
                <th className="py-2">Category</th>
                <th className="py-2">Degree</th>
              </tr>
            </thead>
            <tbody>
              {nodes.map(n => (
                <tr
                  key={n.id}
                  onClick={() => onSelectNode(n)}
                  className="border-b border-slate-800/50 hover:bg-slate-800/40 cursor-pointer"
                >
                  <td className="py-2 font-medium text-slate-200">{n.name}</td>
                  <td className="py-2 text-slate-400">{n.category}</td>
                  <td className="py-2 text-blue-400 font-mono">{n.degree}</td>
                </tr>
              ))}
            </tbody>
          </table>

          <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">Relationships ({edges.length})</h4>
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="border-b border-slate-800 text-slate-400">
                <th className="py-2">Source</th>
                <th className="py-2">Relation</th>
                <th className="py-2">Target</th>
              </tr>
            </thead>
            <tbody>
              {edges.map(e => (
                <tr key={e.id} className="border-b border-slate-800/50">
                  <td className="py-2 text-slate-300">{nodes.find(n => n.id === e.source)?.name || e.source}</td>
                  <td className="py-2 text-cyan-400 font-mono">{e.relation}</td>
                  <td className="py-2 text-slate-300">{nodes.find(n => n.id === e.target)?.name || e.target}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};
