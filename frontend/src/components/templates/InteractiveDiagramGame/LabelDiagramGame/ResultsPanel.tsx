'use client';

import { FeedbackMessages } from './types';

interface ResultsPanelProps {
  score: number;
  maxScore: number;
  feedbackMessages?: FeedbackMessages;
  onPlayAgain: () => void;
  onNewGame?: () => void;
}

export default function ResultsPanel({
  score,
  maxScore,
  feedbackMessages,
  onPlayAgain,
  onNewGame,
}: ResultsPanelProps) {
  const percentage = maxScore > 0 ? Math.round((score / maxScore) * 100) : 0;

  const getMessage = () => {
    if (percentage === 100) {
      return feedbackMessages?.perfect || 'Perfect! You labeled everything correctly!';
    } else if (percentage >= 70) {
      return feedbackMessages?.good || 'Great job! You got most of them right!';
    } else {
      return feedbackMessages?.retry || 'Keep practicing! You\'ll get better!';
    }
  };

  const getEmoji = () => {
    if (percentage === 100) return '🎉';
    if (percentage >= 70) return '👏';
    return '💪';
  };

  return (
    <div className="text-center py-8 px-4">
      {/* Score circle */}
      <div className="relative w-32 h-32 mx-auto mb-6">
        <svg className="w-full h-full transform -rotate-90">
          <circle
            cx="64"
            cy="64"
            r="56"
            stroke="#e5e7eb"
            strokeWidth="8"
            fill="none"
          />
          <circle
            cx="64"
            cy="64"
            r="56"
            stroke="url(#gradient)"
            strokeWidth="8"
            fill="none"
            strokeLinecap="round"
            strokeDasharray={`${(percentage / 100) * 351.86} 351.86`}
            className="transition-all duration-1000"
          />
          <defs>
            <linearGradient id="gradient" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stopColor="#3b82f6" />
              <stop offset="100%" stopColor="#8b5cf6" />
            </linearGradient>
          </defs>
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-3xl font-bold text-gray-800">{percentage}%</span>
          <span className="text-sm text-gray-500">{score}/{maxScore}</span>
        </div>
      </div>

      {/* Emoji and message */}
      <div className="text-5xl mb-4">{getEmoji()}</div>
      <h2 className="text-2xl font-bold text-gray-800 mb-2">
        {percentage === 100 ? 'Congratulations!' : 'Game Complete!'}
      </h2>
      <p className="text-gray-600 mb-6 max-w-md mx-auto">{getMessage()}</p>

      {/* Action buttons */}
      <div className="flex justify-center gap-4">
        <button
          onClick={onPlayAgain}
          className="px-6 py-3 bg-gradient-to-r from-primary-500 to-secondary-500 text-white font-semibold rounded-lg hover:from-primary-600 hover:to-secondary-600 shadow-lg hover:shadow-xl transition-all"
        >
          Play Again
        </button>
        {onNewGame && (
          <button
            onClick={onNewGame}
            className="px-6 py-3 bg-gray-200 text-gray-700 font-semibold rounded-lg hover:bg-gray-300 transition-colors"
          >
            New Game
          </button>
        )}
      </div>
    </div>
  );
}
