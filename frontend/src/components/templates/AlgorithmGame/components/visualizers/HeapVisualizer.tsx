'use client';

import { motion, AnimatePresence } from 'framer-motion';
import { useMemo } from 'react';
import { HeapDataStructure } from '../../types';

interface HeapVisualizerProps {
  dataStructure: HeapDataStructure;
  theme?: 'dark' | 'light';
}

const NODE_R = 20;
const LEVEL_HEIGHT = 60;
const BASE_SPREAD = 110;

interface HeapLayoutNode {
  index: number;
  value: any;
  label: string;
  x: number;
  y: number;
  highlighted: boolean;
  parentIndex: number | null;
}

// Format an element value for display. Handles plain numbers and tuples like [0, "Starbase"].
function formatElement(el: any): string {
  if (Array.isArray(el)) {
    // Priority queue tuple: [priority, label] — show "label(priority)"
    if (el.length === 2 && typeof el[1] === 'string') return `${el[1]}(${el[0]})`;
    return el.join(',');
  }
  return String(el ?? '');
}

function getNodeFill(highlighted: boolean, theme: string): string {
  const isDark = theme === 'dark';
  if (highlighted) {
    return isDark ? 'rgba(250,204,21,0.2)' : '#fef9c3';
  }
  return isDark ? '#1f2937' : '#ffffff';
}

function getNodeStroke(highlighted: boolean, theme: string): string {
  const isDark = theme === 'dark';
  if (highlighted) {
    return isDark ? '#facc15' : '#eab308';
  }
  return isDark ? '#4b5563' : '#d1d5db';
}

function layoutHeapTree(
  elements: any[],
  highlightSet: Set<number>,
): HeapLayoutNode[] {
  const nodes: HeapLayoutNode[] = [];

  function traverse(index: number, x: number, y: number, spread: number, parentIndex: number | null) {
    if (index >= elements.length) return;

    nodes.push({
      index,
      value: elements[index],
      label: formatElement(elements[index]),
      x,
      y,
      highlighted: highlightSet.has(index),
      parentIndex,
    });

    const leftChild = 2 * index + 1;
    const rightChild = 2 * index + 2;

    if (leftChild < elements.length) {
      traverse(leftChild, x - spread, y + LEVEL_HEIGHT, spread / 2, index);
    }
    if (rightChild < elements.length) {
      traverse(rightChild, x + spread, y + LEVEL_HEIGHT, spread / 2, index);
    }
  }

  if (elements.length > 0) {
    traverse(0, 0, 40, BASE_SPREAD, null);
  }

  return nodes;
}

function getHighlightBg(highlighted: boolean, theme: string): string {
  const isDark = theme === 'dark';
  if (highlighted) {
    return isDark ? 'bg-yellow-500/30 border-yellow-400' : 'bg-yellow-200 border-yellow-500';
  }
  return isDark ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-300';
}

export default function HeapVisualizer({
  dataStructure,
  theme = 'dark',
}: HeapVisualizerProps) {
  const { elements = [], heapType, highlights = [] } = dataStructure;
  const isDark = theme === 'dark';
  const highlightSet = useMemo(() => new Set(highlights), [highlights]);

  const layoutNodes = useMemo(
    () => layoutHeapTree(elements, highlightSet),
    [elements, highlightSet],
  );

  // Build a map for quick lookup by index
  const nodeMap = useMemo(
    () => new Map(layoutNodes.map((n) => [n.index, n])),
    [layoutNodes],
  );

  // Compute SVG viewBox
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
        {heapType === 'min' ? 'Min' : heapType === 'max' ? 'Max' : 'Priority'} Queue
      </h4>

      {/* Tree View */}
      {elements.length > 0 && (
        <svg
          viewBox={`${minX} ${minY} ${maxX - minX} ${maxY - minY}`}
          className="w-full mb-4"
          style={{ maxHeight: 250 }}
        >
          {/* Edges */}
          {layoutNodes
            .filter((n) => n.parentIndex !== null)
            .map((node) => {
              const parent = nodeMap.get(node.parentIndex!);
              if (!parent) return null;
              const bothHighlighted = node.highlighted && parent.highlighted;
              return (
                <motion.line
                  key={`edge-${node.index}`}
                  x1={parent.x}
                  y1={parent.y + NODE_R}
                  x2={node.x}
                  y2={node.y - NODE_R}
                  stroke={
                    bothHighlighted
                      ? isDark ? '#facc15' : '#eab308'
                      : isDark ? '#374151' : '#d1d5db'
                  }
                  strokeWidth={bothHighlighted ? 2.5 : 1.5}
                  initial={{ pathLength: 0 }}
                  animate={{ pathLength: 1 }}
                  transition={{ duration: 0.3 }}
                />
              );
            })}

          {/* Nodes */}
          {layoutNodes.map((node) => {
            const fill = getNodeFill(node.highlighted, theme);
            const stroke = getNodeStroke(node.highlighted, theme);

            return (
              <motion.g
                key={`node-${node.index}`}
                initial={{ scale: 0, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                transition={{ type: 'spring', stiffness: 300, damping: 20, delay: node.index * 0.03 }}
                style={{ transformOrigin: `${node.x}px ${node.y}px` }}
              >
                {/* Highlight pulse */}
                {node.highlighted && (
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
                  fontSize={node.label.length > 4 ? 9 : 13}
                  fontWeight="bold"
                  fill={isDark ? '#e5e7eb' : '#1f2937'}
                  fontFamily="monospace"
                >
                  {node.label}
                </text>
              </motion.g>
            );
          })}
        </svg>
      )}

      {/* Array View */}
      <div className="mt-2">
        <div
          className={`text-xs font-semibold mb-2 uppercase tracking-wider ${
            isDark ? 'text-gray-500' : 'text-gray-400'
          }`}
        >
          Array Representation
        </div>

        <div className="flex justify-center gap-1.5 flex-wrap">
          <AnimatePresence mode="popLayout">
            {elements.length === 0 ? (
              <motion.div
                key="empty"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className={`text-center py-4 text-xs italic ${
                  isDark ? 'text-gray-500' : 'text-gray-400'
                }`}
              >
                (empty)
              </motion.div>
            ) : (
              elements.map((val, idx) => {
                const highlighted = highlightSet.has(idx);
                const cellColor = getHighlightBg(highlighted, theme);

                return (
                  <motion.div
                    key={`arr-${idx}`}
                    layout
                    initial={{ opacity: 0, scale: 0.8 }}
                    animate={{ opacity: 1, scale: 1 }}
                    exit={{ opacity: 0, scale: 0.8 }}
                    transition={{ type: 'spring', stiffness: 300, damping: 25 }}
                    className="flex flex-col items-center"
                  >
                    <div
                      className={`min-w-10 px-1.5 text-center py-1.5 rounded border-2 font-mono text-xs font-bold ${cellColor} ${
                        isDark ? 'text-white' : 'text-gray-900'
                      }`}
                    >
                      {formatElement(val)}
                    </div>
                    <span
                      className={`text-xs font-mono mt-0.5 ${
                        isDark ? 'text-gray-500' : 'text-gray-400'
                      }`}
                    >
                      [{idx}]
                    </span>
                  </motion.div>
                );
              })
            )}
          </AnimatePresence>
        </div>
      </div>

      {/* Legend */}
      {highlights.length > 0 && (
        <div className="flex items-center justify-center gap-4 mt-3">
          <div className="flex items-center gap-1.5">
            <div
              className={`w-3 h-3 rounded-sm border-2 ${
                isDark ? 'bg-yellow-500/30 border-yellow-400' : 'bg-yellow-200 border-yellow-500'
              }`}
            />
            <span className={`text-xs ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
              Active
            </span>
          </div>
        </div>
      )}
    </div>
  );
}
