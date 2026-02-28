'use client';

import { motion } from 'framer-motion';
import { NQueensPuzzleData } from '../types';

interface NQueensBoardProps {
  data: NQueensPuzzleData;
  queenPositions: { row: number; col: number }[];
  onPlaceQueen: (row: number, col: number) => void;
  onRemoveQueen: (row: number, col: number) => void;
  disabled?: boolean;
  theme?: 'dark' | 'light';
}

function isConflict(
  positions: { row: number; col: number }[],
  row: number,
  col: number,
): boolean {
  return positions.some(
    (q) =>
      q.row === row ||
      q.col === col ||
      Math.abs(q.row - row) === Math.abs(q.col - col),
  );
}

export default function NQueensBoard({
  data,
  queenPositions,
  onPlaceQueen,
  onRemoveQueen,
  disabled = false,
  theme = 'dark',
}: NQueensBoardProps) {
  const isDark = theme === 'dark';
  const n = data.boardSize;

  const isPrePlaced = (row: number, col: number) =>
    data.prePlaced?.some((p) => p.row === row && p.col === col) ?? false;

  const hasQueen = (row: number, col: number) =>
    queenPositions.some((q) => q.row === row && q.col === col);

  const handleClick = (row: number, col: number) => {
    if (disabled) return;
    if (isPrePlaced(row, col)) return;
    if (hasQueen(row, col)) {
      onRemoveQueen(row, col);
    } else {
      onPlaceQueen(row, col);
    }
  };

  // Determine threatened cells for highlighting
  const threatened = new Set<string>();
  for (const q of queenPositions) {
    for (let i = 0; i < n; i++) {
      threatened.add(`${q.row},${i}`);
      threatened.add(`${i},${q.col}`);
      if (q.row + i < n && q.col + i < n) threatened.add(`${q.row + i},${q.col + i}`);
      if (q.row - i >= 0 && q.col - i >= 0) threatened.add(`${q.row - i},${q.col - i}`);
      if (q.row + i < n && q.col - i >= 0) threatened.add(`${q.row + i},${q.col - i}`);
      if (q.row - i >= 0 && q.col + i < n) threatened.add(`${q.row - i},${q.col + i}`);
    }
  }

  const cellSize = Math.min(48, Math.floor(320 / n));

  return (
    <div className="space-y-3">
      <div className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
        Queens placed: {queenPositions.length}/{n}
      </div>

      <div className="flex justify-center">
        <div
          className={`inline-grid border rounded-lg overflow-hidden ${
            isDark ? 'border-gray-600' : 'border-gray-300'
          }`}
          style={{
            gridTemplateColumns: `repeat(${n}, ${cellSize}px)`,
            gridTemplateRows: `repeat(${n}, ${cellSize}px)`,
          }}
        >
          {Array.from({ length: n * n }).map((_, idx) => {
            const row = Math.floor(idx / n);
            const col = idx % n;
            const isLight = (row + col) % 2 === 0;
            const queen = hasQueen(row, col);
            const prePlaced = isPrePlaced(row, col);
            const isThreatened = !queen && threatened.has(`${row},${col}`);

            // Conflict: two queens share row/col/diagonal
            const queenConflict =
              queen &&
              isConflict(
                queenPositions.filter(
                  (q) => !(q.row === row && q.col === col),
                ),
                row,
                col,
              );

            let bg: string;
            if (queen && queenConflict) {
              bg = isDark ? 'bg-red-800' : 'bg-red-200';
            } else if (queen) {
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
                disabled={disabled || prePlaced}
                whileHover={!disabled && !prePlaced ? { scale: 1.05 } : undefined}
                className={`flex items-center justify-center text-lg ${bg} ${
                  disabled || prePlaced ? 'cursor-default' : 'cursor-pointer'
                } transition-colors`}
                style={{ width: cellSize, height: cellSize }}
              >
                {queen && (
                  <span className={prePlaced ? 'opacity-60' : ''}>
                    {'\u265B'}
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
