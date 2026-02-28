'use client';

import { motion } from 'framer-motion';
import { GraphDataStructure, GraphNodeState, GraphEdgeState } from '../../types';

interface GraphVisualizerProps {
  dataStructure: GraphDataStructure;
  theme?: 'dark' | 'light';
}

const NODE_RADIUS = 22;

function getNodeFill(state: GraphNodeState, theme: string): string {
  const isDark = theme === 'dark';
  switch (state) {
    case 'unvisited':
      return isDark ? '#4b5563' : '#d1d5db';
    case 'in_frontier':
      return isDark ? '#60a5fa' : '#3b82f6';
    case 'current':
      return isDark ? '#facc15' : '#eab308';
    case 'visited':
      return isDark ? '#22c55e' : '#16a34a';
  }
}

function getNodeStroke(state: GraphNodeState, theme: string): string {
  const isDark = theme === 'dark';
  switch (state) {
    case 'unvisited':
      return isDark ? '#6b7280' : '#9ca3af';
    case 'in_frontier':
      return isDark ? '#93c5fd' : '#60a5fa';
    case 'current':
      return isDark ? '#fde047' : '#facc15';
    case 'visited':
      return isDark ? '#4ade80' : '#22c55e';
  }
}

function getEdgeColor(state: GraphEdgeState): string {
  switch (state) {
    case 'default':
      return '#6b7280';
    case 'exploring':
      return '#f97316';
    case 'visited':
      return '#22c55e';
    case 'in_result':
      return '#22c55e';
  }
}

function getEdgeWidth(state: GraphEdgeState): number {
  return state === 'in_result' ? 3 : state === 'exploring' ? 2.5 : 1.5;
}

export default function GraphVisualizer({
  dataStructure,
  theme = 'dark',
}: GraphVisualizerProps) {
  const { nodes, edges, auxiliary } = dataStructure;
  const isDark = theme === 'dark';
  const nodeMap = new Map(nodes.map((n) => [n.id, n]));

  // Compute SVG viewBox from node positions
  const xs = nodes.map((n) => n.x);
  const ys = nodes.map((n) => n.y);
  const pad = 50;
  const minX = Math.min(...xs) - pad;
  const minY = Math.min(...ys) - pad;
  const maxX = Math.max(...xs) + pad;
  const maxY = Math.max(...ys) + pad;
  const svgW = maxX - minX;
  const svgH = maxY - minY;

  return (
    <div
      className={`rounded-lg p-4 ${isDark ? 'bg-[#1e1e1e]' : 'bg-gray-50'}`}
    >
      <h4
        className={`text-xs font-semibold mb-3 uppercase tracking-wider ${
          isDark ? 'text-gray-400' : 'text-gray-500'
        }`}
      >
        Graph State
      </h4>

      <svg
        viewBox={`${minX} ${minY} ${svgW} ${svgH}`}
        className="w-full"
        style={{ maxHeight: 280 }}
      >
        <defs>
          <marker
            id="arrowhead"
            markerWidth="8"
            markerHeight="6"
            refX="8"
            refY="3"
            orient="auto"
          >
            <polygon points="0 0, 8 3, 0 6" fill="#6b7280" />
          </marker>
          <marker
            id="arrowhead-exploring"
            markerWidth="8"
            markerHeight="6"
            refX="8"
            refY="3"
            orient="auto"
          >
            <polygon points="0 0, 8 3, 0 6" fill="#f97316" />
          </marker>
          <marker
            id="arrowhead-visited"
            markerWidth="8"
            markerHeight="6"
            refX="8"
            refY="3"
            orient="auto"
          >
            <polygon points="0 0, 8 3, 0 6" fill="#22c55e" />
          </marker>
        </defs>

        {/* Edges */}
        {edges.map((edge, i) => {
          const from = nodeMap.get(edge.from);
          const to = nodeMap.get(edge.to);
          if (!from || !to) return null;

          const dx = to.x - from.x;
          const dy = to.y - from.y;
          const dist = Math.sqrt(dx * dx + dy * dy) || 1;
          const ux = dx / dist;
          const uy = dy / dist;

          const x1 = from.x + ux * NODE_RADIUS;
          const y1 = from.y + uy * NODE_RADIUS;
          const x2 = to.x - ux * (NODE_RADIUS + 6);
          const y2 = to.y - uy * (NODE_RADIUS + 6);

          const color = getEdgeColor(edge.state);
          const width = getEdgeWidth(edge.state);
          const markerId =
            edge.state === 'exploring'
              ? 'url(#arrowhead-exploring)'
              : edge.state === 'visited' || edge.state === 'in_result'
              ? 'url(#arrowhead-visited)'
              : 'url(#arrowhead)';

          return (
            <g key={`edge-${i}`}>
              <motion.line
                x1={x1}
                y1={y1}
                x2={x2}
                y2={y2}
                stroke={color}
                strokeWidth={width}
                markerEnd={edge.directed !== false ? markerId : undefined}
                initial={{ pathLength: 0, opacity: 0 }}
                animate={{ pathLength: 1, opacity: 1 }}
                transition={{ duration: 0.3 }}
                strokeDasharray={edge.state === 'exploring' ? '6 3' : undefined}
              >
                {edge.state === 'exploring' && (
                  <animate
                    attributeName="stroke-dashoffset"
                    from="9"
                    to="0"
                    dur="0.6s"
                    repeatCount="indefinite"
                  />
                )}
              </motion.line>
              {edge.weight !== undefined && (
                <text
                  x={(from.x + to.x) / 2}
                  y={(from.y + to.y) / 2 - 8}
                  textAnchor="middle"
                  fontSize={11}
                  fill={isDark ? '#9ca3af' : '#6b7280'}
                  fontFamily="monospace"
                >
                  {edge.weight}
                </text>
              )}
            </g>
          );
        })}

        {/* Nodes */}
        {nodes.map((node) => {
          const fill = getNodeFill(node.state, theme);
          const stroke = getNodeStroke(node.state, theme);

          return (
            <motion.g
              key={node.id}
              initial={{ scale: 0, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              transition={{ type: 'spring', stiffness: 300, damping: 25 }}
            >
              {/* Glow ring for current */}
              {node.state === 'current' && (
                <motion.circle
                  cx={node.x}
                  cy={node.y}
                  r={NODE_RADIUS + 6}
                  fill="none"
                  stroke={stroke}
                  strokeWidth={2}
                  opacity={0.4}
                  animate={{ r: [NODE_RADIUS + 4, NODE_RADIUS + 8, NODE_RADIUS + 4] }}
                  transition={{ duration: 1.5, repeat: Infinity }}
                />
              )}

              {/* Pulse for frontier */}
              {node.state === 'in_frontier' && (
                <motion.circle
                  cx={node.x}
                  cy={node.y}
                  r={NODE_RADIUS}
                  fill="none"
                  stroke={stroke}
                  strokeWidth={2}
                  animate={{ opacity: [0.3, 0.8, 0.3] }}
                  transition={{ duration: 1.2, repeat: Infinity }}
                />
              )}

              <circle
                cx={node.x}
                cy={node.y}
                r={NODE_RADIUS}
                fill={fill}
                stroke={stroke}
                strokeWidth={2}
              />
              <text
                x={node.x}
                y={node.y + 1}
                textAnchor="middle"
                dominantBaseline="central"
                fontSize={13}
                fontWeight="bold"
                fill={node.state === 'current' ? '#000' : '#fff'}
                fontFamily="monospace"
              >
                {node.label}
              </text>
            </motion.g>
          );
        })}
      </svg>

      {/* Auxiliary panel (queue/stack display) */}
      {auxiliary && (
        <div className="mt-3">
          <div
            className={`text-xs font-semibold uppercase tracking-wider mb-1.5 ${
              isDark ? 'text-gray-400' : 'text-gray-500'
            }`}
          >
            {auxiliary.label}
          </div>
          <div className="flex gap-1.5 flex-wrap">
            {auxiliary.items.length === 0 ? (
              <span className={`text-xs italic ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>
                (empty)
              </span>
            ) : (
              auxiliary.items.map((item, i) => (
                <motion.span
                  key={`${item}-${i}`}
                  initial={{ opacity: 0, scale: 0.8 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{ type: 'spring', stiffness: 400, damping: 20, delay: i * 0.05 }}
                  className={`px-2.5 py-1 rounded text-xs font-mono font-bold ${
                    isDark
                      ? 'bg-blue-500/20 text-blue-300 border border-blue-500/30'
                      : 'bg-blue-100 text-blue-700 border border-blue-300'
                  }`}
                >
                  {item}
                </motion.span>
              ))
            )}
          </div>
        </div>
      )}

      {/* Legend */}
      <div className="flex items-center justify-center gap-4 mt-3 flex-wrap">
        {[
          { state: 'unvisited' as const, label: 'Unvisited' },
          { state: 'in_frontier' as const, label: 'Frontier' },
          { state: 'current' as const, label: 'Current' },
          { state: 'visited' as const, label: 'Visited' },
        ]
          .filter((s) => nodes.some((n) => n.state === s.state))
          .map(({ state, label }) => (
            <div key={state} className="flex items-center gap-1.5">
              <div
                className="w-3 h-3 rounded-full"
                style={{ backgroundColor: getNodeFill(state, theme) }}
              />
              <span className={`text-xs ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
                {label}
              </span>
            </div>
          ))}
      </div>
    </div>
  );
}
