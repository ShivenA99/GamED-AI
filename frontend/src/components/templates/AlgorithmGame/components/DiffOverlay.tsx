'use client';

import { motion } from 'framer-motion';
import { PredictionResult, ExtendedPrediction } from '../types';

interface DiffOverlayProps {
  prediction: ExtendedPrediction;
  result: PredictionResult;
  theme?: 'dark' | 'light';
}

export default function DiffOverlay({ prediction, result, theme = 'dark' }: DiffOverlayProps) {
  const { isCorrect, playerAnswer, correctAnswer } = result;

  // Arrangement diff: show per-position green/red
  if (prediction.type === 'arrangement') {
    const player = playerAnswer as number[];
    const correct = correctAnswer as number[];

    return (
      <div
        className={`p-4 rounded-lg border-2 ${
          isCorrect
            ? 'border-green-500/50 bg-green-500/10'
            : 'border-red-500/50 bg-red-500/10'
        }`}
      >
        <div className="text-xs font-semibold mb-2 uppercase tracking-wider text-gray-400">
          {isCorrect ? 'Perfect!' : 'Your answer vs Correct'}
        </div>
        <div className="flex gap-2 justify-center">
          {correct.map((val, idx) => {
            const match = player[idx] === val;
            return (
              <motion.div
                key={idx}
                initial={{ scale: 0.8, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                transition={{ delay: idx * 0.08 }}
                className={`w-12 h-12 flex flex-col items-center justify-center rounded-lg border-2 font-mono text-sm font-bold ${
                  match
                    ? 'border-green-400 bg-green-500/20 text-green-300'
                    : 'border-red-400 bg-red-500/20 text-red-300'
                }`}
              >
                <span>{player[idx] ?? '?'}</span>
                {!match && (
                  <span className="text-xs text-green-400 mt-0.5">{val}</span>
                )}
              </motion.div>
            );
          })}
        </div>
        {!isCorrect && (
          <div className="flex gap-2 justify-center mt-2">
            {correct.map((val, idx) => (
              <div
                key={idx}
                className="w-12 text-center text-xs text-green-400 font-mono"
              >
                {player[idx] !== val ? val : ''}
              </div>
            ))}
          </div>
        )}
      </div>
    );
  }

  // Value / MC / Multi-select: simple correct/incorrect display
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className={`p-4 rounded-lg border-2 ${
        isCorrect
          ? 'border-green-500/50 bg-green-500/10'
          : 'border-red-500/50 bg-red-500/10'
      }`}
    >
      <div className="flex items-center gap-2 mb-1">
        {isCorrect ? (
          <svg className="w-5 h-5 text-green-400" fill="currentColor" viewBox="0 0 20 20">
            <path
              fillRule="evenodd"
              d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
              clipRule="evenodd"
            />
          </svg>
        ) : (
          <svg className="w-5 h-5 text-red-400" fill="currentColor" viewBox="0 0 20 20">
            <path
              fillRule="evenodd"
              d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
              clipRule="evenodd"
            />
          </svg>
        )}
        <span
          className={`font-semibold ${
            isCorrect ? 'text-green-400' : 'text-red-400'
          }`}
        >
          {isCorrect ? 'Correct!' : 'Incorrect'}
        </span>
      </div>

      {!isCorrect && (
        <div className={`text-sm mt-1 ${theme === 'dark' ? 'text-gray-300' : 'text-gray-600'}`}>
          <span className="text-red-400 line-through mr-2">
            {Array.isArray(playerAnswer) ? playerAnswer.join(', ') : String(playerAnswer)}
          </span>
          <span className="text-green-400">
            {Array.isArray(correctAnswer) ? correctAnswer.join(', ') : String(correctAnswer)}
          </span>
        </div>
      )}
    </motion.div>
  );
}
