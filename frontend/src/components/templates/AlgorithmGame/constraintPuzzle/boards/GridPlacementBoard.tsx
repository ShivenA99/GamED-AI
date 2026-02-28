'use client';

import { motion } from 'framer-motion';
import {
  BoardRendererProps,
  GridPlacementBoardConfig,
} from '../constraintPuzzleTypes';

export default function GridPlacementBoard({
  config,
  state,
  dispatch,
  disabled = false,
  theme = 'dark',
}: BoardRendererProps) {
  const isDark = theme === 'dark';
  const cfg = config as GridPlacementBoardConfig;
  const { rows, cols, pieceIcon = '\u25CF', prePopulated = [], highlightThreats = false } = cfg;

  const isLocked = (row: number, col: number) =>
    prePopulated.some((p) => p.row === row && p.col === col && p.locked);

  const hasPlacement = (row: number, col: number) =>
    state.placements.some((p) => p.row === row && p.col === col);

  const handleClick = (row: number, col: number) => {
    if (disabled || isLocked(row, col)) return;
    if (hasPlacement(row, col)) {
      dispatch({ type: 'REMOVE_PLACEMENT', row, col });
    } else {
      dispatch({ type: 'PLACE', row, col });
    }
  };

  // Compute threatened cells for highlighting (row/col/diagonal for each placement)
  const threatened = new Set<string>();
  if (highlightThreats) {
    for (const p of state.placements) {
      for (let i = 0; i < Math.max(rows, cols); i++) {
        if (i < cols) threatened.add(`${p.row},${i}`);
        if (i < rows) threatened.add(`${i},${p.col}`);
        if (p.row + i < rows && p.col + i < cols) threatened.add(`${p.row + i},${p.col + i}`);
        if (p.row - i >= 0 && p.col - i >= 0) threatened.add(`${p.row - i},${p.col - i}`);
        if (p.row + i < rows && p.col - i >= 0) threatened.add(`${p.row + i},${p.col - i}`);
        if (p.row - i >= 0 && p.col + i < cols) threatened.add(`${p.row - i},${p.col + i}`);
      }
    }
  }

  // Conflict detection: is this placed piece conflicting with another?
  const isConflict = (row: number, col: number): boolean => {
    return state.placements.some(
      (other) =>
        !(other.row === row && other.col === col) &&
        (other.row === row ||
          other.col === col ||
          Math.abs(other.row - row) === Math.abs(other.col - col)),
    );
  };

  const cellSize = Math.min(48, Math.floor(320 / Math.max(rows, cols)));

  return (
    <div className="space-y-3">
      <div className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
        Placed: {state.placements.length}
      </div>

      <div className="flex justify-center">
        <div
          className={`inline-grid border rounded-lg overflow-hidden ${isDark ? 'border-gray-600' : 'border-gray-300'}`}
          style={{
            gridTemplateColumns: `repeat(${cols}, ${cellSize}px)`,
            gridTemplateRows: `repeat(${rows}, ${cellSize}px)`,
          }}
        >
          {Array.from({ length: rows * cols }).map((_, idx) => {
            const row = Math.floor(idx / cols);
            const col = idx % cols;
            const isLight = (row + col) % 2 === 0;
            const placed = hasPlacement(row, col);
            const locked = isLocked(row, col);
            const isThreatened = !placed && highlightThreats && threatened.has(`${row},${col}`);
            const conflict = placed && highlightThreats && isConflict(row, col);

            let bg: string;
            if (placed && conflict) {
              bg = isDark ? 'bg-red-800' : 'bg-red-200';
            } else if (placed) {
              bg = isDark ? 'bg-blue-800' : 'bg-blue-200';
            } else if (isThreatened) {
              bg = isLight
                ? isDark ? 'bg-gray-700/60' : 'bg-orange-50'
                : isDark ? 'bg-gray-600/60' : 'bg-orange-100';
            } else {
              bg = isLight
                ? isDark ? 'bg-gray-700' : 'bg-gray-100'
                : isDark ? 'bg-gray-600' : 'bg-gray-300';
            }

            return (
              <motion.button
                key={idx}
                onClick={() => handleClick(row, col)}
                disabled={disabled || locked}
                whileHover={!disabled && !locked ? { scale: 1.05 } : undefined}
                className={`flex items-center justify-center text-lg ${bg} ${
                  disabled || locked ? 'cursor-default' : 'cursor-pointer'
                } transition-colors`}
                style={{ width: cellSize, height: cellSize }}
              >
                {placed && (
                  <span className={locked ? 'opacity-60' : ''}>
                    {pieceIcon}
                  </span>
                )}
              </motion.button>
            );
          })}
        </div>
      </div>
    </div>
  );
}
