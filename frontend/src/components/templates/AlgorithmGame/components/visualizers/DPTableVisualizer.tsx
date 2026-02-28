'use client';

import { useState } from 'react';
import { motion } from 'framer-motion';
import { DPTableDataStructure, DPCellState } from '../../types';

interface DPTableVisualizerProps {
  dataStructure: DPTableDataStructure;
  theme?: 'dark' | 'light';
}

const CELL_SIZE = 56;
const CELL_GAP = 4;

function getCellFill(state: DPCellState, theme: string): string {
  const isDark = theme === 'dark';
  switch (state) {
    case 'empty':
      return isDark ? '#1f2937' : '#ffffff';
    case 'filled':
      return isDark ? '#334155' : '#e2e8f0';
    case 'computing':
      return isDark ? 'rgba(250,204,21,0.2)' : '#fef9c3';
    case 'read':
      return isDark ? 'rgba(249,115,22,0.2)' : '#ffedd5';
    case 'optimal':
      return isDark ? 'rgba(34,197,94,0.2)' : '#dcfce7';
  }
}

function getCellBorder(state: DPCellState, theme: string): string {
  const isDark = theme === 'dark';
  switch (state) {
    case 'empty':
      return isDark ? '#374151' : '#d1d5db';
    case 'filled':
      return isDark ? '#475569' : '#94a3b8';
    case 'computing':
      return isDark ? '#facc15' : '#eab308';
    case 'read':
      return isDark ? '#f97316' : '#ea580c';
    case 'optimal':
      return isDark ? '#22c55e' : '#16a34a';
  }
}

export default function DPTableVisualizer({
  dataStructure,
  theme = 'dark',
}: DPTableVisualizerProps) {
  const { cells, rowLabels, colLabels, activeCell, dependencies } = dataStructure;
  const isDark = theme === 'dark';
  const [hoverCell, setHoverCell] = useState<[number, number] | null>(null);

  const rows = cells.length;
  const cols = cells[0]?.length ?? 0;

  const labelOffset = colLabels ? 24 : 0;
  const rowLabelOffset = rowLabels ? 50 : 0;
  const svgW = rowLabelOffset + cols * (CELL_SIZE + CELL_GAP) + 20;
  const svgH = labelOffset + rows * (CELL_SIZE + CELL_GAP) + 20;

  function cellX(c: number) {
    return rowLabelOffset + c * (CELL_SIZE + CELL_GAP) + 10;
  }
  function cellY(r: number) {
    return labelOffset + r * (CELL_SIZE + CELL_GAP) + 10;
  }
  function cellCenterX(c: number) {
    return cellX(c) + CELL_SIZE / 2;
  }
  function cellCenterY(r: number) {
    return cellY(r) + CELL_SIZE / 2;
  }

  return (
    <div
      className={`rounded-lg p-4 ${isDark ? 'bg-[#1e1e1e]' : 'bg-gray-50'}`}
    >
      <h4
        className={`text-xs font-semibold mb-3 uppercase tracking-wider ${
          isDark ? 'text-gray-400' : 'text-gray-500'
        }`}
      >
        DP Table
      </h4>

      <div className="overflow-x-auto">
        <svg
          viewBox={`0 0 ${svgW} ${svgH}`}
          className="w-full"
          style={{ maxHeight: 320 }}
        >
          {/* Column labels */}
          {colLabels?.map((label, c) => (
            <text
              key={`col-${c}`}
              x={cellCenterX(c)}
              y={8}
              textAnchor="middle"
              fontSize={10}
              fill={isDark ? '#9ca3af' : '#6b7280'}
              fontFamily="monospace"
            >
              {label}
            </text>
          ))}

          {/* Row labels */}
          {rowLabels?.map((label, r) => (
            <text
              key={`row-${r}`}
              x={rowLabelOffset - 6}
              y={cellCenterY(r) + 1}
              textAnchor="end"
              dominantBaseline="central"
              fontSize={10}
              fill={isDark ? '#9ca3af' : '#6b7280'}
              fontFamily="monospace"
            >
              {label}
            </text>
          ))}

          {/* Dependency arrows */}
          {dependencies?.map((dep, i) => {
            const [fr, fc] = dep.from;
            const [tr, tc] = dep.to;
            return (
              <motion.line
                key={`dep-${i}`}
                x1={cellCenterX(fc)}
                y1={cellCenterY(fr)}
                x2={cellCenterX(tc)}
                y2={cellCenterY(tr)}
                stroke={isDark ? '#f97316' : '#ea580c'}
                strokeWidth={1.5}
                markerEnd="url(#dp-arrow)"
                initial={{ opacity: 0 }}
                animate={{ opacity: 0.7 }}
                transition={{ duration: 0.3, delay: i * 0.1 }}
              />
            );
          })}

          <defs>
            <marker
              id="dp-arrow"
              markerWidth="6"
              markerHeight="5"
              refX="6"
              refY="2.5"
              orient="auto"
            >
              <polygon
                points="0 0, 6 2.5, 0 5"
                fill={isDark ? '#f97316' : '#ea580c'}
              />
            </marker>
          </defs>

          {/* Cells */}
          {cells.map((row, r) =>
            row.map((cell, c) => {
              const isActive =
                activeCell && activeCell[0] === r && activeCell[1] === c;
              const fill = getCellFill(cell.state, theme);
              const border = getCellBorder(cell.state, theme);

              return (
                <g
                  key={`cell-${r}-${c}`}
                  onMouseEnter={() => setHoverCell([r, c])}
                  onMouseLeave={() => setHoverCell(null)}
                  style={{ cursor: 'default' }}
                >
                  <motion.rect
                    x={cellX(c)}
                    y={cellY(r)}
                    width={CELL_SIZE}
                    height={CELL_SIZE}
                    rx={6}
                    fill={fill}
                    stroke={border}
                    strokeWidth={isActive ? 2.5 : 1.5}
                    initial={{ opacity: 0, scale: 0.8 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ duration: 0.2, delay: (r * cols + c) * 0.03 }}
                  />
                  <text
                    x={cellCenterX(c)}
                    y={cellCenterY(r) + 1}
                    textAnchor="middle"
                    dominantBaseline="central"
                    fontSize={14}
                    fontWeight="bold"
                    fill={
                      cell.value === null
                        ? isDark
                          ? '#4b5563'
                          : '#d1d5db'
                        : isDark
                        ? '#e5e7eb'
                        : '#1f2937'
                    }
                    fontFamily="monospace"
                  >
                    {cell.value === null ? '?' : cell.value}
                  </text>
                </g>
              );
            }),
          )}

          {/* Hover tooltip */}
          {hoverCell && (() => {
            const [hr, hc] = hoverCell;
            const cell = cells[hr]?.[hc];
            if (!cell || cell.value === null) return null;
            const deps = dependencies?.filter(
              (d) => d.to[0] === hr && d.to[1] === hc,
            );
            const tooltipText =
              deps && deps.length > 0
                ? `${cell.value} = f(${deps.map((d) => `[${d.from}]`).join(', ')})`
                : `${cell.value}`;
            const tx = cellCenterX(hc);
            const ty = cellY(hr) - 10;
            return (
              <g>
                <rect
                  x={tx - 40}
                  y={ty - 16}
                  width={80}
                  height={20}
                  rx={4}
                  fill={isDark ? '#374151' : '#f3f4f6'}
                  stroke={isDark ? '#4b5563' : '#d1d5db'}
                  strokeWidth={1}
                />
                <text
                  x={tx}
                  y={ty - 5}
                  textAnchor="middle"
                  fontSize={10}
                  fill={isDark ? '#d1d5db' : '#374151'}
                  fontFamily="monospace"
                >
                  {tooltipText}
                </text>
              </g>
            );
          })()}
        </svg>
      </div>

      {/* Legend */}
      <div className="flex items-center justify-center gap-4 mt-3 flex-wrap">
        {[
          { state: 'empty' as const, label: 'Empty' },
          { state: 'filled' as const, label: 'Filled' },
          { state: 'computing' as const, label: 'Computing' },
          { state: 'read' as const, label: 'Reading' },
          { state: 'optimal' as const, label: 'Optimal' },
        ]
          .filter((s) =>
            cells.some((row) => row.some((c) => c.state === s.state)),
          )
          .map(({ state, label }) => (
            <div key={state} className="flex items-center gap-1.5">
              <div
                className="w-3 h-3 rounded-sm border"
                style={{
                  backgroundColor: getCellFill(state, theme),
                  borderColor: getCellBorder(state, theme),
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
