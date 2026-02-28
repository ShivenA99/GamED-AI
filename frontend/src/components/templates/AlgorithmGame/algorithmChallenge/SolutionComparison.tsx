'use client';

import { motion } from 'framer-motion';
import { CombinedScoring } from './combinedPuzzleTypes';

interface SolutionComparisonProps {
  scoring: CombinedScoring;
  codeOutput: string | null;
  puzzleSerialized: string;
  onContinue: () => void;
  theme?: 'dark' | 'light';
}

export default function SolutionComparison({
  scoring,
  codeOutput,
  puzzleSerialized,
  onContinue,
  theme = 'dark',
}: SolutionComparisonProps) {
  const isDark = theme === 'dark';
  const match = scoring.consistencyBonus > 0;

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.97 }}
      animate={{ opacity: 1, scale: 1 }}
      className={`rounded-xl border p-6 ${isDark ? 'border-gray-700 bg-gray-900' : 'border-gray-200 bg-white'}`}
    >
      <h3 className={`text-lg font-bold text-center mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>
        Solution Comparison
      </h3>

      {/* Side-by-side comparison */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
        {/* Code output */}
        <div className={`rounded-lg p-4 ${isDark ? 'bg-gray-800' : 'bg-gray-50'}`}>
          <div className={`text-xs font-medium mb-2 ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
            Your Code Output
          </div>
          <code className={`text-sm block ${isDark ? 'text-blue-400' : 'text-blue-600'}`}>
            {codeOutput || '(no output)'}
          </code>
        </div>

        {/* Puzzle solution */}
        <div className={`rounded-lg p-4 ${isDark ? 'bg-gray-800' : 'bg-gray-50'}`}>
          <div className={`text-xs font-medium mb-2 ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
            Your Manual Solution
          </div>
          <code className={`text-sm block ${isDark ? 'text-purple-400' : 'text-purple-600'}`}>
            {puzzleSerialized || '(empty)'}
          </code>
        </div>
      </div>

      {/* Match indicator */}
      <div className={`text-center mb-6 py-3 rounded-lg ${
        match
          ? isDark ? 'bg-green-900/20 border border-green-800' : 'bg-green-50 border border-green-200'
          : isDark ? 'bg-yellow-900/20 border border-yellow-800' : 'bg-yellow-50 border border-yellow-200'
      }`}>
        <span className={`text-sm font-medium ${
          match
            ? isDark ? 'text-green-300' : 'text-green-700'
            : isDark ? 'text-yellow-300' : 'text-yellow-700'
        }`}>
          {match
            ? 'Your code and manual solutions match! +100 bonus!'
            : 'Solutions differ — no consistency bonus this time.'}
        </span>
      </div>

      {/* Score breakdown */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
        {[
          { label: 'Code Score', value: scoring.codeScore, max: 300, color: 'text-blue-400' },
          { label: 'Puzzle Score', value: scoring.puzzleScore, max: 300, color: 'text-purple-400' },
          { label: 'Consistency', value: scoring.consistencyBonus, max: 100, color: 'text-green-400' },
          { label: 'Total', value: scoring.totalScore, max: 700, color: 'text-yellow-400' },
        ].map((item) => (
          <motion.div
            key={item.label}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className={`rounded-lg p-3 text-center ${isDark ? 'bg-gray-800' : 'bg-gray-100'}`}
          >
            <div className={`text-2xl font-bold ${item.color}`}>
              {item.value}
            </div>
            <div className={`text-xs ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
              {item.label} / {item.max}
            </div>
          </motion.div>
        ))}
      </div>

      <div className="text-center">
        <motion.button
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
          onClick={onContinue}
          className="px-8 py-3 rounded-lg bg-blue-600 text-white font-medium hover:bg-blue-500 transition-colors"
        >
          See Final Results
        </motion.button>
      </div>
    </motion.div>
  );
}
