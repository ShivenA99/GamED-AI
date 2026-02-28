'use client';

import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { TestCase, BugHunterScoringState } from '../types';

interface VerificationPanelProps {
  testCases: TestCase[];
  scoring: BugHunterScoringState;
  onComplete: () => void;
  theme?: 'dark' | 'light';
}

export default function VerificationPanel({
  testCases,
  scoring,
  onComplete,
  theme = 'dark',
}: VerificationPanelProps) {
  const isDark = theme === 'dark';
  const [revealedCount, setRevealedCount] = useState(0);

  // Animate test results one by one
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
    <div className={`rounded-xl p-6 ${isDark ? 'bg-gray-900' : 'bg-white'}`}>
      <h2
        className={`text-xl font-bold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}
      >
        Verification — Running Tests
      </h2>

      {/* Test results */}
      <div className="space-y-3 mb-6">
        {testCases.map((tc, i) => (
          <motion.div
            key={tc.id}
            initial={{ opacity: 0, x: -20 }}
            animate={i < revealedCount ? { opacity: 1, x: 0 } : {}}
            transition={{ type: 'spring', stiffness: 300, damping: 25 }}
            className={`flex items-center gap-3 p-3 rounded-lg ${
              i < revealedCount
                ? isDark
                  ? 'bg-green-900/20 border border-green-800/40'
                  : 'bg-green-50 border border-green-200'
                : isDark
                ? 'bg-gray-800 border border-gray-700'
                : 'bg-gray-100 border border-gray-200'
            }`}
          >
            {/* Animated checkmark */}
            {i < revealedCount ? (
              <motion.span
                initial={{ scale: 0 }}
                animate={{ scale: 1 }}
                transition={{ type: 'spring', delay: 0.1 }}
                className="text-green-400 text-lg font-bold"
              >
                {'\u2713'}
              </motion.span>
            ) : (
              <span className={`text-lg ${isDark ? 'text-gray-600' : 'text-gray-400'}`}>
                {'\u25CB'}
              </span>
            )}

            <div className="flex-1">
              <span className={`text-sm font-medium ${isDark ? 'text-gray-200' : 'text-gray-800'}`}>
                Test {i + 1}
              </span>
              <span className={`ml-2 text-xs font-mono ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>
                {tc.inputDescription}
              </span>
            </div>

            {i < revealedCount && (
              <motion.span
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className={`text-xs font-mono ${isDark ? 'text-green-400' : 'text-green-600'}`}
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
          className="mb-6 space-y-2"
        >
          <h3 className={`text-sm font-semibold ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
            Bonuses
          </h3>
          {scoring.bonuses.map((b, i) => (
            <motion.div
              key={b.type}
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: i * 0.15 }}
              className={`flex items-center justify-between p-2 rounded-lg ${
                isDark ? 'bg-yellow-900/20' : 'bg-yellow-50'
              }`}
            >
              <span className={`text-sm ${isDark ? 'text-yellow-300' : 'text-yellow-700'}`}>
                {b.type}
              </span>
              <span className="text-sm font-bold text-yellow-400">+{b.points}</span>
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
          <div className={`text-3xl font-bold mb-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>
            Score: {Math.max(0, scoring.totalScore)}
          </div>
          <div className={`text-sm mb-4 ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
            {scoring.bugsFound}/{scoring.totalBugs} bugs found
            {scoring.wrongLineClicks > 0 && ` \u2022 ${scoring.wrongLineClicks} wrong clicks`}
          </div>
          <motion.button
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            onClick={onComplete}
            className="px-8 py-3 bg-primary-500 text-white rounded-lg hover:bg-primary-600 transition-colors font-medium"
          >
            Finish
          </motion.button>
        </motion.div>
      )}
    </div>
  );
}
