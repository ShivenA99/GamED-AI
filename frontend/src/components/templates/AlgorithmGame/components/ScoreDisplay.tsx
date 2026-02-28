'use client';

import { motion, AnimatePresence } from 'framer-motion';
import { ScoringState } from '../types';

interface ScoreDisplayProps {
  scoring: ScoringState;
  multiplier: number;
  theme?: 'dark' | 'light';
}

export default function ScoreDisplay({ scoring, multiplier, theme = 'dark' }: ScoreDisplayProps) {
  return (
    <div
      className={`flex items-center gap-4 px-4 py-2 rounded-lg ${
        theme === 'dark' ? 'bg-gray-800/50' : 'bg-gray-100'
      }`}
    >
      {/* Score */}
      <div className="flex items-center gap-1.5">
        <span className={`text-sm ${theme === 'dark' ? 'text-gray-400' : 'text-gray-500'}`}>
          Score:
        </span>
        <AnimatePresence mode="popLayout">
          <motion.span
            key={scoring.totalScore}
            initial={{ y: -10, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            className="font-bold text-lg text-primary-500"
          >
            {scoring.totalScore}
          </motion.span>
        </AnimatePresence>
      </div>

      {/* Streak */}
      <AnimatePresence>
        {scoring.streak > 0 && (
          <motion.div
            initial={{ scale: 0, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0, opacity: 0 }}
            className="flex items-center gap-1"
          >
            <motion.span
              animate={scoring.streak >= 3 ? { scale: [1, 1.2, 1] } : {}}
              transition={{ duration: 0.3, repeat: scoring.streak >= 5 ? Infinity : 0, repeatDelay: 0.5 }}
              className="text-lg"
              role="img"
              aria-label="fire"
            >
              {scoring.streak >= 8 ? '\u{1F525}\u{1F525}' : '\u{1F525}'}
            </motion.span>
            <span className="font-bold text-orange-400">{scoring.streak}</span>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Multiplier */}
      <AnimatePresence>
        {multiplier > 1 && (
          <motion.div
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            exit={{ scale: 0 }}
            className={`px-2 py-0.5 rounded-full text-xs font-bold ${
              multiplier >= 3
                ? 'bg-red-500/20 text-red-400 border border-red-500/30'
                : multiplier >= 2
                ? 'bg-orange-500/20 text-orange-400 border border-orange-500/30'
                : 'bg-yellow-500/20 text-yellow-400 border border-yellow-500/30'
            }`}
          >
            {multiplier}x
          </motion.div>
        )}
      </AnimatePresence>

      {/* Correct / Total */}
      {scoring.totalPredictions > 0 && (
        <span
          className={`text-xs ml-auto ${
            theme === 'dark' ? 'text-gray-500' : 'text-gray-400'
          }`}
        >
          {scoring.correctCount}/{scoring.totalPredictions} correct
        </span>
      )}
    </div>
  );
}
