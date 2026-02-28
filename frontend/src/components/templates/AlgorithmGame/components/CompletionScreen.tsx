'use client';

import { motion } from 'framer-motion';
import { ScoringState } from '../types';

interface CompletionScreenProps {
  scoring: ScoringState;
  finalScore: number;
  totalSteps: number;
  onReset: () => void;
  theme?: 'dark' | 'light';
}

export default function CompletionScreen({
  scoring,
  finalScore,
  totalSteps,
  onReset,
  theme = 'dark',
}: CompletionScreenProps) {
  const accuracy =
    scoring.totalPredictions > 0
      ? Math.round((scoring.correctCount / scoring.totalPredictions) * 100)
      : 100;

  const maxPossible = scoring.totalPredictions * 100 * 3; // theoretical max w/ max streak
  const scorePercent = maxPossible > 0 ? Math.min(100, Math.round((finalScore / maxPossible) * 100)) : 100;

  const isPerfect = scoring.incorrectCount === 0 && scoring.totalPredictions > 0;

  const message =
    accuracy >= 90
      ? 'Outstanding! You traced the algorithm like a pro!'
      : accuracy >= 70
      ? 'Good work! You understand the algorithm well.'
      : accuracy >= 50
      ? 'Not bad! Keep practicing to improve your accuracy.'
      : 'Keep at it! Understanding code execution takes practice.';

  const stats = [
    { label: 'Final Score', value: finalScore, color: 'text-primary-500' },
    { label: 'Accuracy', value: `${accuracy}%`, color: accuracy >= 70 ? 'text-green-400' : 'text-yellow-400' },
    { label: 'Best Streak', value: scoring.maxStreak, color: 'text-orange-400' },
    { label: 'Hints Used', value: scoring.hintsUsed, color: 'text-blue-400' },
    { label: 'Steps Predicted', value: `${scoring.totalPredictions}/${totalSteps}`, color: 'text-purple-400' },
    { label: 'Correct', value: scoring.correctCount, color: 'text-green-400' },
  ];

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      className={`rounded-xl p-8 ${theme === 'dark' ? 'bg-gray-900' : 'bg-white'}`}
    >
      <div className="text-center">
        {/* Score circle */}
        <motion.div
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          transition={{ type: 'spring', delay: 0.2 }}
          className="w-28 h-28 mx-auto mb-6 bg-gradient-to-br from-primary-500 to-secondary-500 rounded-full flex items-center justify-center shadow-lg"
        >
          <span className="text-3xl font-bold text-white">{accuracy}%</span>
        </motion.div>

        {isPerfect && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.5 }}
            className="text-2xl mb-2"
          >
            Perfect Run! +20% Bonus
          </motion.div>
        )}

        <h2
          className={`text-3xl font-bold mb-2 ${
            theme === 'dark' ? 'text-white' : 'text-gray-900'
          }`}
        >
          Algorithm Traced!
        </h2>
        <p
          className={`text-lg mb-8 ${
            theme === 'dark' ? 'text-gray-300' : 'text-gray-600'
          }`}
        >
          {message}
        </p>

        {/* Stats grid */}
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4 mb-8 max-w-lg mx-auto">
          {stats.map((stat, i) => (
            <motion.div
              key={stat.label}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.3 + i * 0.08 }}
              className={`p-3 rounded-lg ${
                theme === 'dark' ? 'bg-gray-800' : 'bg-gray-100'
              }`}
            >
              <div className={`text-2xl font-bold ${stat.color}`}>
                {stat.value}
              </div>
              <div
                className={`text-xs ${
                  theme === 'dark' ? 'text-gray-400' : 'text-gray-500'
                }`}
              >
                {stat.label}
              </div>
            </motion.div>
          ))}
        </div>

        <button
          onClick={onReset}
          className="px-8 py-3 bg-primary-500 text-white rounded-lg hover:bg-primary-600 transition-colors font-medium"
        >
          Play Again
        </button>
      </div>
    </motion.div>
  );
}
