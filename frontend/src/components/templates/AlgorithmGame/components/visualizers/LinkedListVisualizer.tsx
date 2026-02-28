'use client';

import { useMemo } from 'react';
import { motion } from 'framer-motion';
import { LinkedListDataStructure, LLNodeState } from '../../types';

interface LinkedListVisualizerProps {
  dataStructure: LinkedListDataStructure;
  theme?: 'dark' | 'light';
}

const NODE_W = 80;
const NODE_H = 40;
const GAP = 60;
const PTR_SECTION_W = 20;

function getNodeBorder(state: LLNodeState, theme: string): string {
  const isDark = theme === 'dark';
  switch (state) {
    case 'current':
      return isDark ? '#facc15' : '#eab308';
    case 'prev':
      return isDark ? '#ef4444' : '#dc2626';
    case 'done':
      return isDark ? '#22c55e' : '#16a34a';
    default:
      return isDark ? '#4b5563' : '#d1d5db';
  }
}

function getNodeFill(state: LLNodeState, theme: string): string {
  const isDark = theme === 'dark';
  switch (state) {
    case 'current':
      return isDark ? 'rgba(250,204,21,0.1)' : '#fefce8';
    case 'prev':
      return isDark ? 'rgba(239,68,68,0.1)' : '#fef2f2';
    case 'done':
      return isDark ? 'rgba(34,197,94,0.1)' : '#f0fdf4';
    default:
      return isDark ? '#1f2937' : '#ffffff';
  }
}

interface LayoutLLNode {
  id: string;
  value: number | string;
  next: string | null;
  state: LLNodeState;
  x: number;
  y: number;
}

export default function LinkedListVisualizer({
  dataStructure,
  theme = 'dark',
}: LinkedListVisualizerProps) {
  const { nodes, head, pointers } = dataStructure;
  const isDark = theme === 'dark';

  // Lay out nodes in traversal order from head
  const layoutNodes = useMemo(() => {
    const nodeMap = new Map(nodes.map((n) => [n.id, n]));
    const result: LayoutLLNode[] = [];
    const visited = new Set<string>();

    // Walk from head
    let currentId = head;
    let x = 40;
    const y = 60;

    while (currentId && !visited.has(currentId)) {
      visited.add(currentId);
      const node = nodeMap.get(currentId);
      if (!node) break;
      result.push({ ...node, x, y });
      x += NODE_W + GAP;
      currentId = node.next;
    }

    // Add any orphan nodes not reachable from head
    for (const node of nodes) {
      if (!visited.has(node.id)) {
        result.push({ ...node, x, y });
        x += NODE_W + GAP;
      }
    }

    return result;
  }, [nodes, head]);

  const nodeMap = new Map(layoutNodes.map((n) => [n.id, n]));

  // SVG dimensions
  const maxX = layoutNodes.length > 0
    ? Math.max(...layoutNodes.map((n) => n.x)) + NODE_W + 40
    : 200;
  const svgH = 140;

  return (
    <div
      className={`rounded-lg p-4 ${isDark ? 'bg-[#1e1e1e]' : 'bg-gray-50'}`}
    >
      <h4
        className={`text-xs font-semibold mb-3 uppercase tracking-wider ${
          isDark ? 'text-gray-400' : 'text-gray-500'
        }`}
      >
        Linked List
      </h4>

      <div className="overflow-x-auto">
        <svg
          viewBox={`0 0 ${maxX} ${svgH}`}
          className="w-full"
          style={{ maxHeight: 180, minWidth: maxX * 0.6 }}
        >
          <defs>
            <marker
              id="ll-arrow"
              markerWidth="8"
              markerHeight="6"
              refX="8"
              refY="3"
              orient="auto"
            >
              <polygon points="0 0, 8 3, 0 6" fill={isDark ? '#6b7280' : '#9ca3af'} />
            </marker>
            {/* Pointer-specific arrow markers */}
            {pointers?.map((ptr) => (
              <marker
                key={`marker-${ptr.name}`}
                id={`ll-ptr-${ptr.name}`}
                markerWidth="8"
                markerHeight="6"
                refX="8"
                refY="3"
                orient="auto"
              >
                <polygon points="0 0, 8 3, 0 6" fill={ptr.color} />
              </marker>
            ))}
          </defs>

          {/* Next-pointer arrows between nodes */}
          {layoutNodes.map((node) => {
            if (!node.next) return null;
            const target = nodeMap.get(node.next);
            if (!target) return null;

            const x1 = node.x + NODE_W - PTR_SECTION_W / 2;
            const y1 = node.y + NODE_H / 2;
            const x2 = target.x;
            const y2 = target.y + NODE_H / 2;

            // Quadratic bezier for slight curve
            const cx = (x1 + x2) / 2;
            const cy = y1 - 15;

            return (
              <motion.path
                key={`next-${node.id}`}
                d={`M ${x1} ${y1} Q ${cx} ${cy} ${x2} ${y2}`}
                fill="none"
                stroke={isDark ? '#6b7280' : '#9ca3af'}
                strokeWidth={1.5}
                markerEnd="url(#ll-arrow)"
                initial={{ pathLength: 0 }}
                animate={{ pathLength: 1 }}
                transition={{ duration: 0.3 }}
              />
            );
          })}

          {/* Named pointers (prev, curr, next, head, tail) */}
          {pointers?.map((ptr) => {
            if (!ptr.target) return null;
            const target = nodeMap.get(ptr.target);
            if (!target) return null;

            const tx = target.x + NODE_W / 2;
            const ty = target.y + NODE_H + 8;

            return (
              <g key={`ptr-${ptr.name}`}>
                <motion.line
                  x1={tx}
                  y1={ty + 12}
                  x2={tx}
                  y2={ty + 2}
                  stroke={ptr.color}
                  strokeWidth={2}
                  markerEnd={`url(#ll-ptr-${ptr.name})`}
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ duration: 0.3 }}
                />
                <text
                  x={tx}
                  y={ty + 24}
                  textAnchor="middle"
                  fontSize={10}
                  fontWeight="bold"
                  fill={ptr.color}
                  fontFamily="monospace"
                >
                  {ptr.name}
                </text>
              </g>
            );
          })}

          {/* Nodes */}
          {layoutNodes.map((node) => {
            const fill = getNodeFill(node.state, theme);
            const stroke = getNodeBorder(node.state, theme);

            return (
              <motion.g
                key={node.id}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ type: 'spring', stiffness: 300, damping: 25 }}
              >
                {/* Value section */}
                <rect
                  x={node.x}
                  y={node.y}
                  width={NODE_W - PTR_SECTION_W}
                  height={NODE_H}
                  rx={4}
                  fill={fill}
                  stroke={stroke}
                  strokeWidth={2}
                />
                <text
                  x={node.x + (NODE_W - PTR_SECTION_W) / 2}
                  y={node.y + NODE_H / 2 + 1}
                  textAnchor="middle"
                  dominantBaseline="central"
                  fontSize={14}
                  fontWeight="bold"
                  fill={isDark ? '#e5e7eb' : '#1f2937'}
                  fontFamily="monospace"
                >
                  {node.value}
                </text>

                {/* Pointer section */}
                <rect
                  x={node.x + NODE_W - PTR_SECTION_W}
                  y={node.y}
                  width={PTR_SECTION_W}
                  height={NODE_H}
                  rx={0}
                  fill={isDark ? '#374151' : '#e5e7eb'}
                  stroke={stroke}
                  strokeWidth={2}
                />
                {/* Null symbol or dot */}
                <text
                  x={node.x + NODE_W - PTR_SECTION_W / 2}
                  y={node.y + NODE_H / 2 + 1}
                  textAnchor="middle"
                  dominantBaseline="central"
                  fontSize={node.next ? 10 : 12}
                  fill={isDark ? '#9ca3af' : '#6b7280'}
                  fontFamily="monospace"
                >
                  {node.next ? '→' : '⊥'}
                </text>
              </motion.g>
            );
          })}

          {/* "head" label above first node if no explicit head pointer */}
          {head && !pointers?.some((p) => p.name === 'head') && (() => {
            const headNode = nodeMap.get(head);
            if (!headNode) return null;
            return (
              <g>
                <text
                  x={headNode.x + NODE_W / 2}
                  y={headNode.y - 14}
                  textAnchor="middle"
                  fontSize={10}
                  fontWeight="bold"
                  fill={isDark ? '#60a5fa' : '#3b82f6'}
                  fontFamily="monospace"
                >
                  head
                </text>
                <line
                  x1={headNode.x + NODE_W / 2}
                  y1={headNode.y - 10}
                  x2={headNode.x + NODE_W / 2}
                  y2={headNode.y - 2}
                  stroke={isDark ? '#60a5fa' : '#3b82f6'}
                  strokeWidth={1.5}
                />
              </g>
            );
          })()}
        </svg>
      </div>

      {/* Legend */}
      <div className="flex items-center justify-center gap-4 mt-3 flex-wrap">
        {[
          { state: 'current' as const, label: 'Current', color: '#facc15' },
          { state: 'prev' as const, label: 'Previous', color: '#ef4444' },
          { state: 'done' as const, label: 'Reversed', color: '#22c55e' },
        ]
          .filter((s) => layoutNodes.some((n) => n.state === s.state))
          .map(({ state, label }) => (
            <div key={state} className="flex items-center gap-1.5">
              <div
                className="w-3 h-3 rounded-sm border-2"
                style={{
                  borderColor: getNodeBorder(state, theme),
                  backgroundColor: getNodeFill(state, theme),
                }}
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
