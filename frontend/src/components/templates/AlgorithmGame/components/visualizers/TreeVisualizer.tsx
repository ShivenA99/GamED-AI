'use client';

import { motion } from 'framer-motion';
import { useMemo } from 'react';
import { TreeDataStructure, TreeNodeState } from '../../types';

interface TreeVisualizerProps {
  dataStructure: TreeDataStructure;
  theme?: 'dark' | 'light';
}

const NODE_R = 20;
const LEVEL_HEIGHT = 70;
const BASE_SPREAD = 120;

interface LayoutNode {
  id: string;
  value: number;
  state: TreeNodeState;
  x: number;
  y: number;
  childIds: string[]; // unified child list (binary or N-ary)
}

function getNodeFill(state: TreeNodeState, theme: string): string {
  const isDark = theme === 'dark';
  switch (state) {
    case 'comparing':
      return isDark ? 'rgba(250,204,21,0.15)' : '#fef9c3';
    case 'path':
      return isDark ? 'rgba(96,165,250,0.15)' : '#dbeafe';
    case 'found':
      return isDark ? 'rgba(34,197,94,0.15)' : '#dcfce7';
    case 'inserted':
      return isDark ? 'rgba(168,85,247,0.15)' : '#f3e8ff';
    default:
      return isDark ? '#1f2937' : '#ffffff';
  }
}

function getNodeStroke(state: TreeNodeState, theme: string): string {
  const isDark = theme === 'dark';
  switch (state) {
    case 'comparing':
      return isDark ? '#facc15' : '#eab308';
    case 'path':
      return isDark ? '#60a5fa' : '#3b82f6';
    case 'found':
      return isDark ? '#22c55e' : '#16a34a';
    case 'inserted':
      return isDark ? '#a855f7' : '#9333ea';
    default:
      return isDark ? '#4b5563' : '#d1d5db';
  }
}

/**
 * Get the children of a tree node, supporting both binary (left/right) and N-ary (children[]) formats.
 */
function getChildIds(node: { left?: string; right?: string; children?: string[] }): string[] {
  // N-ary: explicit children array takes priority if present and non-empty
  if (node.children && node.children.length > 0) {
    return node.children;
  }
  // Binary: convert left/right to children list
  return [node.left, node.right].filter(Boolean) as string[];
}

function layoutTree(
  ds: TreeDataStructure,
): { layoutNodes: LayoutNode[]; edges: { from: LayoutNode; to: LayoutNode; onPath: boolean }[]; isNary: boolean } {
  const nodeMap = new Map(ds.nodes.map((n) => [n.id, n]));
  const layoutNodes: LayoutNode[] = [];
  const edges: { from: LayoutNode; to: LayoutNode; onPath: boolean }[] = [];
  const pathSet = new Set(ds.highlightPath || []);

  // Detect N-ary: any node has children array with more than 2 entries
  const isNary = ds.nodes.some((n) => n.children && n.children.length > 2);

  function traverse(id: string, x: number, y: number, spread: number) {
    const node = nodeMap.get(id);
    if (!node) return;

    const childIds = getChildIds(node);
    const ln: LayoutNode = { id: node.id, value: node.value, state: node.state, x, y, childIds };
    layoutNodes.push(ln);

    const childCount = childIds.length;
    if (childCount === 0) return;

    const cy = y + LEVEL_HEIGHT;
    const childSpread = spread / Math.max(childCount - 1, 1);

    if (childCount === 1) {
      // Single child: place directly below
      const childId = childIds[0];
      if (nodeMap.has(childId)) {
        traverse(childId, x, cy, spread / 2);
        const childLayout = layoutNodes.find((n) => n.id === childId)!;
        edges.push({ from: ln, to: childLayout, onPath: pathSet.has(id) && pathSet.has(childId) });
      }
    } else if (childCount === 2) {
      // Binary: left/right spread (original behavior)
      const [leftId, rightId] = childIds;
      if (nodeMap.has(leftId)) {
        traverse(leftId, x - spread, cy, spread / 2);
        const childLayout = layoutNodes.find((n) => n.id === leftId)!;
        edges.push({ from: ln, to: childLayout, onPath: pathSet.has(id) && pathSet.has(leftId) });
      }
      if (nodeMap.has(rightId)) {
        traverse(rightId, x + spread, cy, spread / 2);
        const childLayout = layoutNodes.find((n) => n.id === rightId)!;
        edges.push({ from: ln, to: childLayout, onPath: pathSet.has(id) && pathSet.has(rightId) });
      }
    } else {
      // N-ary: space children evenly across the spread
      const totalWidth = spread * 2;
      childIds.forEach((childId, i) => {
        if (!nodeMap.has(childId)) return;
        const cx = x - spread + (totalWidth * i) / (childCount - 1);
        traverse(childId, cx, cy, childSpread / 2);
        const childLayout = layoutNodes.find((n) => n.id === childId)!;
        edges.push({ from: ln, to: childLayout, onPath: pathSet.has(id) && pathSet.has(childId) });
      });
    }
  }

  if (ds.root) {
    traverse(ds.root, 0, 40, BASE_SPREAD);
  }

  return { layoutNodes, edges, isNary };
}

export default function TreeVisualizer({
  dataStructure,
  theme = 'dark',
}: TreeVisualizerProps) {
  const isDark = theme === 'dark';
  const { layoutNodes, edges, isNary } = useMemo(
    () => layoutTree(dataStructure),
    [dataStructure],
  );

  // Compute viewBox
  const xs = layoutNodes.map((n) => n.x);
  const ys = layoutNodes.map((n) => n.y);
  const pad = 40;
  const minX = Math.min(...xs, 0) - pad;
  const minY = Math.min(...ys, 0) - pad;
  const maxX = Math.max(...xs, 0) + pad;
  const maxY = Math.max(...ys, 0) + pad;

  return (
    <div
      className={`rounded-lg p-4 ${isDark ? 'bg-[#1e1e1e]' : 'bg-gray-50'}`}
    >
      <h4
        className={`text-xs font-semibold mb-3 uppercase tracking-wider ${
          isDark ? 'text-gray-400' : 'text-gray-500'
        }`}
      >
        {isNary ? 'N-ary Tree' : 'Binary Search Tree'}
      </h4>

      <svg
        viewBox={`${minX} ${minY} ${maxX - minX} ${maxY - minY}`}
        className="w-full"
        style={{ maxHeight: 300 }}
      >
        {/* Edges */}
        {edges.map((edge, i) => (
          <motion.line
            key={`edge-${i}`}
            x1={edge.from.x}
            y1={edge.from.y + NODE_R}
            x2={edge.to.x}
            y2={edge.to.y - NODE_R}
            stroke={edge.onPath ? (isDark ? '#60a5fa' : '#3b82f6') : (isDark ? '#374151' : '#d1d5db')}
            strokeWidth={edge.onPath ? 2.5 : 1.5}
            initial={{ pathLength: 0 }}
            animate={{ pathLength: 1 }}
            transition={{ duration: 0.3, delay: edge.onPath ? i * 0.15 : 0 }}
          />
        ))}

        {/* Nodes */}
        {layoutNodes.map((node) => {
          const fill = getNodeFill(node.state, theme);
          const stroke = getNodeStroke(node.state, theme);
          const isInserted = node.state === 'inserted';

          return (
            <motion.g
              key={node.id}
              initial={isInserted ? { scale: 0, opacity: 0 } : { opacity: 1 }}
              animate={{ scale: 1, opacity: 1 }}
              transition={
                isInserted
                  ? { type: 'spring', stiffness: 300, damping: 15 }
                  : { duration: 0.2 }
              }
              style={{ transformOrigin: `${node.x}px ${node.y}px` }}
            >
              {/* Pulse for comparing */}
              {node.state === 'comparing' && (
                <motion.circle
                  cx={node.x}
                  cy={node.y}
                  r={NODE_R + 4}
                  fill="none"
                  stroke={stroke}
                  strokeWidth={2}
                  animate={{ opacity: [0.3, 0.8, 0.3] }}
                  transition={{ duration: 1, repeat: Infinity }}
                />
              )}

              <circle
                cx={node.x}
                cy={node.y}
                r={NODE_R}
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
                fill={isDark ? '#e5e7eb' : '#1f2937'}
                fontFamily="monospace"
              >
                {node.value}
              </text>
            </motion.g>
          );
        })}
      </svg>

      {/* Legend */}
      <div className="flex items-center justify-center gap-4 mt-3 flex-wrap">
        {[
          { state: 'comparing' as const, label: 'Comparing' },
          { state: 'path' as const, label: 'Path' },
          { state: 'found' as const, label: 'Found' },
          { state: 'inserted' as const, label: 'Inserted' },
        ]
          .filter((s) => layoutNodes.some((n) => n.state === s.state))
          .map(({ state, label }) => (
            <div key={state} className="flex items-center gap-1.5">
              <div
                className="w-3 h-3 rounded-full border-2"
                style={{
                  borderColor: getNodeStroke(state, theme),
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
