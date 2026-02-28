'use client';

import { useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

interface HintSystemProps {
  hints: [string, string, string];
  currentTier: number;
  onRequestHint: (tier: number) => void;
  theme?: 'dark' | 'light';
  /** Penalty percentages per tier. Defaults to [0.1, 0.2, 0.3]. Pass [0,0,0] for learn mode. */
  hintPenalties?: [number, number, number];
}

const TIER_NAMES = ['Nudge', 'Clue', 'Answer'];
const TIER_COLORS = [
  'border-yellow-500/40 bg-yellow-500/10 text-yellow-300',
  'border-orange-500/40 bg-orange-500/10 text-orange-300',
  'border-red-500/40 bg-red-500/10 text-red-300',
];
const TIER_COLORS_LIGHT = [
  'border-yellow-400 bg-yellow-50 text-yellow-800',
  'border-orange-400 bg-orange-50 text-orange-800',
  'border-red-400 bg-red-50 text-red-800',
];

export default function HintSystem({
  hints,
  currentTier,
  onRequestHint,
  theme = 'dark',
  hintPenalties = [0.1, 0.2, 0.3],
}: HintSystemProps) {
  const nextTier = currentTier + 1;
  const hasMoreHints = nextTier <= 3;
  const colors = theme === 'dark' ? TIER_COLORS : TIER_COLORS_LIGHT;

  // Build labels dynamically from penalties
  const tierLabels = useMemo(() =>
    TIER_NAMES.map((name, i) => {
      const pct = Math.round((hintPenalties[i] ?? 0) * 100);
      return pct > 0 ? `${name} (-${pct}%)` : `${name} (free)`;
    }),
    [hintPenalties],
  );

  return (
    <div className="space-y-2">
      {/* Show used hints */}
      <AnimatePresence>
        {Array.from({ length: currentTier }, (_, i) => (
          <motion.div
            key={i}
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            className={`p-3 rounded-lg border text-sm ${colors[i]}`}
          >
            <span className="font-semibold text-xs uppercase tracking-wider block mb-1">
              {tierLabels[i]}
            </span>
            {hints[i]}
          </motion.div>
        ))}
      </AnimatePresence>

      {/* Request next hint button */}
      {hasMoreHints && (
        <button
          onClick={() => onRequestHint(nextTier)}
          className={`text-xs px-3 py-1.5 rounded-md transition-colors ${
            theme === 'dark'
              ? 'bg-gray-700 text-gray-300 hover:bg-gray-600'
              : 'bg-gray-200 text-gray-600 hover:bg-gray-300'
          }`}
        >
          {currentTier === 0 ? 'Need a hint?' : `Get ${TIER_NAMES[currentTier]} hint`}
          <span className="ml-1 opacity-60">({tierLabels[currentTier] || tierLabels[2]})</span>
        </button>
      )}
    </div>
  );
}
