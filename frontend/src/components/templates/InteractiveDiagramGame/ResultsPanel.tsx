'use client';

import { useEffect, useState } from 'react';
import { FeedbackMessages, SceneResult } from './types';
import { Confetti } from './animations';
import { useReducedMotion } from './hooks/useReducedMotion';
import type { GameplayMode } from './types';

interface ResultsPanelProps {
  score: number;
  maxScore: number;
  feedbackMessages?: FeedbackMessages;
  thresholds?: { perfect: number; great: number };
  onPlayAgain: () => void;
  onNewGame?: () => void;
  /** Multi-scene: per-scene results for breakdown table */
  sceneResults?: SceneResult[];
  /** Multi-scene: scene names for breakdown table */
  sceneNames?: string[];
  gameplayMode?: GameplayMode;
  /** Time elapsed in seconds (test mode) */
  elapsedSeconds?: number;
}

export default function ResultsPanel({
  score,
  maxScore,
  feedbackMessages,
  thresholds,
  onPlayAgain,
  onNewGame,
  sceneResults,
  sceneNames,
  gameplayMode = 'learn',
  elapsedSeconds,
}: ResultsPanelProps) {
  const percentage = maxScore > 0 ? Math.round((score / maxScore) * 100) : 0;
  const [showConfetti, setShowConfetti] = useState(false);
  const prefersReducedMotion = useReducedMotion();
  const isTestMode = gameplayMode === 'test';

  const perfectThreshold = thresholds?.perfect ?? 100;
  const greatThreshold = thresholds?.great ?? 70;

  // Trigger confetti for perfect or great scores (respects reduced motion preference)
  useEffect(() => {
    if (percentage >= greatThreshold && !prefersReducedMotion) {
      setShowConfetti(true);
    }
  }, [percentage, greatThreshold, prefersReducedMotion]);

  const getMessage = () => {
    if (percentage >= perfectThreshold) {
      return feedbackMessages?.perfect || 'Perfect! You labeled everything correctly!';
    } else if (percentage >= greatThreshold) {
      return feedbackMessages?.good || 'Great job! You got most of them right!';
    } else {
      return feedbackMessages?.retry || 'Keep practicing! You\'ll get better!';
    }
  };

  const getEmoji = () => {
    if (percentage >= perfectThreshold) return '\u{1F389}';
    if (percentage >= greatThreshold) return '\u{1F44F}';
    return '\u{1F4AA}';
  };

  return (
    <div className="text-center py-8 px-4">
      {/* Confetti celebration */}
      <Confetti
        isActive={showConfetti}
        duration={percentage === 100 ? 4000 : 2500}
        particleCount={percentage === 100 ? 80 : 40}
        onComplete={() => setShowConfetti(false)}
      />

      {/* Score circle - uses CSS custom properties for theming */}
      <div className="relative w-32 h-32 mx-auto mb-6">
        <svg
          className="w-full h-full transform -rotate-90"
          role="img"
          aria-label={`Score: ${percentage}%, ${score} out of ${maxScore} correct`}
        >
          <circle
            cx="64"
            cy="64"
            r="56"
            className="stroke-gray-200 dark:stroke-gray-700"
            strokeWidth="8"
            fill="none"
          />
          <circle
            cx="64"
            cy="64"
            r="56"
            stroke="url(#score-gradient)"
            strokeWidth="8"
            fill="none"
            strokeLinecap="round"
            strokeDasharray={`${(percentage / 100) * 351.86} 351.86`}
            className={prefersReducedMotion ? '' : 'transition-all duration-1000'}
          />
          <defs>
            <linearGradient id="score-gradient" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" className="[stop-color:theme(colors.blue.500)]" stopColor="var(--tw-stop-color, #3b82f6)" />
              <stop offset="100%" className="[stop-color:theme(colors.violet.500)]" stopColor="var(--tw-stop-color, #8b5cf6)" />
            </linearGradient>
          </defs>
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-3xl font-bold text-gray-800 dark:text-gray-100">{percentage}%</span>
          <span className="text-sm text-gray-500 dark:text-gray-400">{score}/{maxScore}</span>
        </div>
      </div>

      {/* Emoji and message */}
      <div className="text-5xl mb-4">{getEmoji()}</div>
      <h2 className="text-2xl font-bold text-gray-800 dark:text-gray-100 mb-2">
        {percentage >= perfectThreshold ? 'Congratulations!' : 'Game Complete!'}
      </h2>
      <p className="text-gray-600 dark:text-gray-300 mb-6 max-w-md mx-auto">{getMessage()}</p>

      {/* Test mode: detailed score breakdown */}
      {isTestMode && (
        <div className="max-w-sm mx-auto mb-6 bg-orange-50 dark:bg-orange-900/20 rounded-lg p-4">
          <h3 className="text-sm font-semibold text-orange-800 dark:text-orange-200 mb-3">Test Results</h3>
          <div className="grid grid-cols-2 gap-3 text-sm">
            <div className="text-left text-gray-600 dark:text-gray-400">Score</div>
            <div className="text-right font-semibold text-gray-800 dark:text-gray-200">{score} / {maxScore}</div>
            <div className="text-left text-gray-600 dark:text-gray-400">Percentage</div>
            <div className="text-right font-semibold text-gray-800 dark:text-gray-200">{percentage}%</div>
            {elapsedSeconds !== undefined && (
              <>
                <div className="text-left text-gray-600 dark:text-gray-400">Time</div>
                <div className="text-right font-semibold text-gray-800 dark:text-gray-200">
                  {Math.floor(elapsedSeconds / 60)}:{(elapsedSeconds % 60).toString().padStart(2, '0')}
                </div>
              </>
            )}
            <div className="text-left text-gray-600 dark:text-gray-400">Grade</div>
            <div className="text-right font-semibold">
              <span className={
                percentage >= 90 ? 'text-green-600 dark:text-green-400' :
                percentage >= 70 ? 'text-blue-600 dark:text-blue-400' :
                percentage >= 50 ? 'text-yellow-600 dark:text-yellow-400' :
                'text-red-600 dark:text-red-400'
              }>
                {percentage >= 90 ? 'A' : percentage >= 80 ? 'B' : percentage >= 70 ? 'C' : percentage >= 60 ? 'D' : 'F'}
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Scene breakdown table (multi-scene only) */}
      {sceneResults && sceneResults.length > 1 && (
        <div className="max-w-md mx-auto mb-6">
          <div className="bg-gray-50 dark:bg-gray-800/50 rounded-lg overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-200 dark:border-gray-700">
                  <th className="text-left px-4 py-2 text-gray-500 dark:text-gray-400 font-medium">Scene</th>
                  <th className="text-right px-4 py-2 text-gray-500 dark:text-gray-400 font-medium">Score</th>
                  <th className="text-right px-4 py-2 text-gray-500 dark:text-gray-400 font-medium">%</th>
                </tr>
              </thead>
              <tbody>
                {sceneResults.map((result, idx) => {
                  const pct = result.max_score > 0 ? Math.round((result.score / result.max_score) * 100) : 0;
                  const name = sceneNames?.[idx] || `Scene ${idx + 1}`;
                  return (
                    <tr key={`${result.scene_id}-${idx}`} className="border-b border-gray-100 dark:border-gray-700/50">
                      <td className="px-4 py-2 text-gray-700 dark:text-gray-300 truncate max-w-[200px]">{name}</td>
                      <td className="text-right px-4 py-2 font-medium text-gray-800 dark:text-gray-200">{result.score}/{result.max_score}</td>
                      <td className="text-right px-4 py-2">
                        <span className={`font-semibold ${pct >= 80 ? 'text-green-600 dark:text-green-400' : pct >= 50 ? 'text-yellow-600 dark:text-yellow-400' : 'text-red-500 dark:text-red-400'}`}>
                          {pct}%
                        </span>
                      </td>
                    </tr>
                  );
                })}
                <tr className="bg-gray-100 dark:bg-gray-700/50 font-semibold">
                  <td className="px-4 py-2 text-gray-800 dark:text-gray-200">Total</td>
                  <td className="text-right px-4 py-2 text-primary-600 dark:text-primary-400">{score}/{maxScore}</td>
                  <td className="text-right px-4 py-2 text-primary-600 dark:text-primary-400">{percentage}%</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Learn mode: educational feedback */}
      {!isTestMode && percentage < perfectThreshold && (
        <div className="max-w-md mx-auto mb-6 bg-blue-50 dark:bg-blue-900/20 rounded-lg p-4 text-left">
          <h3 className="text-sm font-semibold text-blue-800 dark:text-blue-200 mb-2">Learning Tips</h3>
          <p className="text-sm text-blue-700 dark:text-blue-300">
            Try again with hints enabled to learn the correct placements.
            Focus on understanding the relationships between components.
          </p>
        </div>
      )}

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
            className="px-6 py-3 bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-200 font-semibold rounded-lg hover:bg-gray-300 dark:hover:bg-gray-600 transition-colors"
          >
            New Game
          </button>
        )}
      </div>
    </div>
  );
}
