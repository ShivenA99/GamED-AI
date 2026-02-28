'use client';

import { useMemo } from 'react';
import { motion } from 'framer-motion';
import {
  BoardRendererProps,
  GraphInteractionBoardConfig,
} from '../constraintPuzzleTypes';

export default function GraphInteractionBoard({
  config,
  state,
  dispatch,
  disabled = false,
  theme = 'dark',
}: BoardRendererProps) {
  const isDark = theme === 'dark';
  const cfg = config as GraphInteractionBoardConfig;
  const extra = (cfg as any).extra ?? {};

  // LLM sometimes puts nodes/edges inside `extra` instead of top-level config
  const rawNodes: any[] = cfg.nodes ?? extra.nodes ?? [];
  const rawEdges: any[] = cfg.edges ?? extra.edges ?? [];
  const selectionMode = cfg.selectionMode ?? 'edge';

  // Auto-generate x/y positions if missing (circular layout)
  const nodes = useMemo(() => {
    if (rawNodes.length === 0) return [];
    const needsLayout = rawNodes.some((n: any) => n.x == null || n.y == null);
    if (!needsLayout) return rawNodes;
    const cx = 200, cy = 150, r = 120;
    return rawNodes.map((n: any, i: number) => ({
      ...n,
      x: n.x ?? cx + r * Math.cos((2 * Math.PI * i) / rawNodes.length - Math.PI / 2),
      y: n.y ?? cy + r * Math.sin((2 * Math.PI * i) / rawNodes.length - Math.PI / 2),
    }));
  }, [rawNodes]);
  const edges = rawEdges;

  // Compute SVG viewBox from node positions
  const viewBox = useMemo(() => {
    if (nodes.length === 0) return '0 0 400 300';
    const pad = 40;
    const xs = nodes.map((n) => n.x);
    const ys = nodes.map((n) => n.y);
    const minX = Math.min(...xs) - pad;
    const minY = Math.min(...ys) - pad;
    const maxX = Math.max(...xs) + pad;
    const maxY = Math.max(...ys) + pad;
    return `${minX} ${minY} ${maxX - minX} ${maxY - minY}`;
  }, [nodes]);

  const nodeById = useMemo(() => {
    const map = new Map<string, (typeof nodes)[0]>();
    for (const n of nodes) map.set(n.id, n);
    return map;
  }, [nodes]);

  const isNodeSelected = (id: string) => state.selectedIds.includes(id);
  const isEdgeSelected = (id: string) => state.selectedEdgeIds.includes(id);

  const handleNodeClick = (id: string) => {
    if (disabled || (selectionMode !== 'nodes' && selectionMode !== 'both')) return;
    dispatch({ type: 'TOGGLE', id });
  };

  const handleEdgeClick = (id: string) => {
    if (disabled || (selectionMode !== 'edges' && selectionMode !== 'both')) return;
    if (isEdgeSelected(id)) {
      dispatch({ type: 'DESELECT_EDGE', edgeId: id });
    } else {
      dispatch({ type: 'SELECT_EDGE', edgeId: id });
    }
  };

  // Edge midpoint for weight label
  const edgeMidpoint = (from: string, to: string) => {
    const a = nodeById.get(from);
    const b = nodeById.get(to);
    if (!a || !b) return { x: 0, y: 0 };
    return { x: (a.x + b.x) / 2, y: (a.y + b.y) / 2 };
  };

  const nodeRadius = 20;

  return (
    <div className="space-y-3">
      <div className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
        {selectionMode === 'edges'
          ? `Edges selected: ${state.selectedEdgeIds.length}`
          : selectionMode === 'nodes'
            ? `Nodes selected: ${state.selectedIds.length}`
            : `Nodes: ${state.selectedIds.length} | Edges: ${state.selectedEdgeIds.length}`}
      </div>

      <div className="flex justify-center">
        <svg
          viewBox={viewBox}
          className={`w-full max-w-lg rounded-lg border ${isDark ? 'border-gray-600 bg-gray-800' : 'border-gray-300 bg-gray-50'}`}
          style={{ minHeight: 250 }}
        >
          {/* Arrow marker for directed edges */}
          <defs>
            <marker
              id="arrowhead"
              markerWidth="10"
              markerHeight="7"
              refX="10"
              refY="3.5"
              orient="auto"
            >
              <polygon
                points="0 0, 10 3.5, 0 7"
                fill={isDark ? '#9ca3af' : '#6b7280'}
              />
            </marker>
            <marker
              id="arrowhead-selected"
              markerWidth="10"
              markerHeight="7"
              refX="10"
              refY="3.5"
              orient="auto"
            >
              <polygon points="0 0, 10 3.5, 0 7" fill="#3b82f6" />
            </marker>
          </defs>

          {/* Edges */}
          {edges.map((edge) => {
            const from = nodeById.get(edge.from);
            const to = nodeById.get(edge.to);
            if (!from || !to) return null;
            const selected = isEdgeSelected(edge.id);
            const mid = edgeMidpoint(edge.from, edge.to);
            const canSelect = selectionMode === 'edges' || selectionMode === 'both';

            return (
              <g key={edge.id}>
                {/* Invisible wider hit area */}
                {canSelect && !disabled && (
                  <line
                    x1={from.x}
                    y1={from.y}
                    x2={to.x}
                    y2={to.y}
                    stroke="transparent"
                    strokeWidth={16}
                    className="cursor-pointer"
                    onClick={() => handleEdgeClick(edge.id)}
                  />
                )}
                <line
                  x1={from.x}
                  y1={from.y}
                  x2={to.x}
                  y2={to.y}
                  stroke={selected ? '#3b82f6' : isDark ? '#6b7280' : '#9ca3af'}
                  strokeWidth={selected ? 3 : 2}
                  markerEnd={edge.directed ? (selected ? 'url(#arrowhead-selected)' : 'url(#arrowhead)') : undefined}
                  className={canSelect && !disabled ? 'cursor-pointer' : ''}
                  onClick={canSelect && !disabled ? () => handleEdgeClick(edge.id) : undefined}
                />
                {/* Weight label */}
                {edge.weight != null && (
                  <text
                    x={mid.x}
                    y={mid.y - 8}
                    textAnchor="middle"
                    className="text-xs font-medium"
                    fill={selected ? '#3b82f6' : isDark ? '#d1d5db' : '#374151'}
                  >
                    {edge.weight}
                  </text>
                )}
              </g>
            );
          })}

          {/* Nodes */}
          {nodes.map((node) => {
            const selected = isNodeSelected(node.id);
            const canSelect = selectionMode === 'nodes' || selectionMode === 'both';

            return (
              <g
                key={node.id}
                onClick={canSelect && !disabled ? () => handleNodeClick(node.id) : undefined}
                className={canSelect && !disabled ? 'cursor-pointer' : ''}
              >
                <circle
                  cx={node.x}
                  cy={node.y}
                  r={nodeRadius}
                  fill={
                    selected
                      ? '#3b82f6'
                      : isDark ? '#374151' : '#f3f4f6'
                  }
                  stroke={
                    selected
                      ? '#2563eb'
                      : isDark ? '#6b7280' : '#9ca3af'
                  }
                  strokeWidth={2}
                />
                <text
                  x={node.x}
                  y={node.y}
                  textAnchor="middle"
                  dominantBaseline="central"
                  className="text-xs font-medium pointer-events-none"
                  fill={selected ? '#ffffff' : isDark ? '#e5e7eb' : '#1f2937'}
                >
                  {node.label}
                </text>
              </g>
            );
          })}
        </svg>
      </div>
    </div>
  );
}
