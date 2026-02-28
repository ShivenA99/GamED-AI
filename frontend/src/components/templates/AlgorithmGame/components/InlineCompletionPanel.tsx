'use client';

import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { TestCase, BugHunterScoringState } from '../types';

interface InlineCompletionPanelProps {
  testCases: TestCase[];
  scoring: BugHunterScoringState;
  onComplete: () => void;
  theme?: 'dark' | 'light';
}

export default function InlineCompletionPanel({
  testCases,
  scoring,
  onComplete,
  theme = 'dark',
}: InlineCompletionPanelProps) {
  const isDark = theme === 'dark';
  const [revealedCount, setRevealedCount] = useState(0);

  useEffect(() => {
    if (revealedCount < testCases.length) {
      const timer = setTimeout(() => {
        setRevealedCount((c) => c + 1);
      }, 400);
      return () => clearTimeout(timer);
    }
  }, [revealedCount, testCases.length]);

  const allRevealed = revealedCount >= testCases.length;

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className={`rounded-lg border p-4 ${
        isDark ? 'bg-gray-800/50 border-gray-700' : 'bg-gray-50 border-gray-200'
      }`}
    >
      <h3
        className={`text-sm font-semibold mb-3 ${isDark ? 'text-gray-300' : 'text-gray-700'}`}
      >
        Verification — Running Tests
      </h3>

      {/* Test results */}
      <div className="space-y-2 mb-4">
        {testCases.map((tc, i) => (
          <motion.div
            key={tc.id}
            initial={{ opacity: 0, x: -20 }}
            animate={i < revealedCount ? { opacity: 1, x: 0 } : {}}
            transition={{ type: 'spring', stiffness: 300, damping: 25 }}
            className={`flex items-center gap-2 p-2 rounded text-sm ${
              i < revealedCount
                ? isDark
                  ? 'bg-green-900/20 border border-green-800/40'
                  : 'bg-green-50 border border-green-200'
                : isDark
                ? 'bg-gray-800 border border-gray-700'
                : 'bg-gray-100 border border-gray-200'
            }`}
          >
            {i < revealedCount ? (
              <motion.span
                initial={{ scale: 0 }}
                animate={{ scale: 1 }}
                transition={{ type: 'spring', delay: 0.1 }}
                className="text-green-400 font-bold"
              >
                {'\u2713'}
              </motion.span>
            ) : (
              <span className={isDark ? 'text-gray-600' : 'text-gray-400'}>
                {'\u25CB'}
              </span>
            )}

            <span className={`text-sm font-medium ${isDark ? 'text-gray-200' : 'text-gray-800'}`}>
              Test {i + 1}
            </span>
            <span className={`text-xs font-mono ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>
              {tc.inputDescription}
            </span>

            {i < revealedCount && (
              <motion.span
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className={`ml-auto text-xs font-mono ${isDark ? 'text-green-400' : 'text-green-600'}`}
              >
                {tc.expectedOutput}
              </motion.span>
            )}
          </motion.div>
        ))}
      </div>

      {/* Bonuses */}
      {allRevealed && scoring.bonuses.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-4 space-y-1.5"
        >
          <h4 className={`text-xs font-semibold ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
            Bonuses
          </h4>
          {scoring.bonuses.map((b, i) => (
            <motion.div
              key={b.type}
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: i * 0.15 }}
              className={`flex items-center justify-between p-2 rounded text-sm ${
                isDark ? 'bg-yellow-900/20' : 'bg-yellow-50'
              }`}
            >
              <span className={isDark ? 'text-yellow-300' : 'text-yellow-700'}>
                {b.type}
              </span>
              <span className="font-bold text-yellow-400">+{b.points}</span>
            </motion.div>
          ))}
        </motion.div>
      )}

      {/* Final score + continue */}
      {allRevealed && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.3 }}
          className="text-center"
        >
          <div className={`text-2xl font-bold mb-1 ${isDark ? 'text-white' : 'text-gray-900'}`}>
            Score: {Math.max(0, scoring.totalScore)}
          </div>
          <div className={`text-sm mb-3 ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
            {scoring.bugsFound}/{scoring.totalBugs} bugs found
            {scoring.wrongLineClicks > 0 && ` \u2022 ${scoring.wrongLineClicks} wrong clicks`}
          </div>
          <motion.button
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            onClick={onComplete}
            className="px-6 py-2 bg-primary-500 text-white rounded-lg hover:bg-primary-600 transition-colors font-medium text-sm"
          >
            Finish
          </motion.button>
        </motion.div>
      )}
    </motion.div>
  );
}
