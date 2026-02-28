'use client';

import { useMemo } from 'react';
import { motion } from 'framer-motion';
import { ConstraintPuzzleBlueprint, GameplayMode } from './types';
import { GenericConstraintPuzzleBlueprint } from './constraintPuzzle/constraintPuzzleTypes';
import { isGenericBlueprint, migrateBlueprint } from './constraintPuzzle/migrateBlueprint';
import { useGenericConstraintPuzzleMachine } from './hooks/useGenericConstraintPuzzleMachine';
import { normalizeBoardType } from './constraintPuzzle/boardRegistry';
import { normalizeBlueprint } from './constraintPuzzle/normalizeConstraints';
import BoardRouter from './constraintPuzzle/BoardRouter';
import HintSystem from './components/HintSystem';

interface ConstraintPuzzleGameProps {
  blueprint: ConstraintPuzzleBlueprint | GenericConstraintPuzzleBlueprint;
  onComplete?: (score: number) => void;
  theme?: 'dark' | 'light';
  gameplayMode?: GameplayMode;
}

export default function ConstraintPuzzleGame({
  blueprint: rawBlueprint,
  onComplete,
  theme = 'dark',
  gameplayMode = 'learn',
}: ConstraintPuzzleGameProps) {
  const isTestMode = gameplayMode === 'test';
  const hintPenalties: [number, number, number] = isTestMode ? [0.1, 0.2, 0.3] : [0, 0, 0];
  const isDark = theme === 'dark';

  // Migrate legacy blueprints to generic format, normalize boardType,
  // and normalize constraints/scoring/items from backend LLM format
  const blueprint = useMemo<GenericConstraintPuzzleBlueprint>(() => {
    const bp = isGenericBlueprint(rawBlueprint)
      ? rawBlueprint
      : migrateBlueprint(rawBlueprint);

    // Normalize LLM-generated boardType to a canonical value.
    // Mutate in-place on a shallow clone to preserve the discriminated union type.
    const canonicalType = normalizeBoardType(bp.boardConfig.boardType);
    let normalized = bp;
    if (canonicalType !== bp.boardConfig.boardType) {
      const normalizedConfig = { ...bp.boardConfig };
      (normalizedConfig as { boardType: string }).boardType = canonicalType;
      normalized = { ...bp, boardConfig: normalizedConfig } as GenericConstraintPuzzleBlueprint;
    }

    // Normalize constraint shapes, scoring config, and item field names
    // to handle mismatches between backend LLM output and frontend types
    return normalizeBlueprint(normalized);
  }, [rawBlueprint]);

  const {
    state,
    dispatch,
    start,
    undo,
    checkSolution,
    revealAlgorithm,
    useHint,
    complete,
    reset,
  } = useGenericConstraintPuzzleMachine(blueprint);

  const { phase, scoring } = state;

  const icon = blueprint.icon ?? '\u{1F9E9}';

  // ---------- INIT ----------
  if (phase === 'INIT') {
    return (
      <div className={`rounded-2xl border p-6 max-w-3xl mx-auto ${isDark ? 'border-gray-700 bg-gray-900' : 'border-gray-200 bg-white'}`}>
        <div className="text-center space-y-4">
          <div className="text-4xl">{icon}</div>
          <h2 className={`text-2xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>
            {blueprint.title}
          </h2>
          <p className={`text-sm max-w-lg mx-auto ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
            {blueprint.narrative}
          </p>

          <div className={`rounded-lg p-4 text-sm text-left ${isDark ? 'bg-gray-800 text-gray-300' : 'bg-gray-50 text-gray-600'}`}>
            <p className="font-medium mb-2">Rules:</p>
            <ul className="space-y-1 list-disc pl-5">
              {blueprint.rules.map((r, i) => (
                <li key={i}>{r}</li>
              ))}
            </ul>
          </div>

          <div className={`text-sm font-medium ${isDark ? 'text-blue-400' : 'text-blue-600'}`}>
            Objective: {blueprint.objective}
          </div>

          <motion.button
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            onClick={start}
            className="px-8 py-3 rounded-lg bg-blue-600 text-white font-semibold hover:bg-blue-500 transition-colors"
          >
            Start Puzzle
          </motion.button>
        </div>
      </div>
    );
  }

  // ---------- COMPLETED ----------
  if (phase === 'COMPLETED') {
    const maxScore = 300 + 150;
    const pct = Math.min(Math.round((scoring.totalScore / maxScore) * 100), 100);
    const radius = 54;
    const circumference = 2 * Math.PI * radius;
    const offset = circumference * (1 - pct / 100);

    return (
      <div className={`rounded-2xl border p-6 max-w-3xl mx-auto ${isDark ? 'border-gray-700 bg-gray-900' : 'border-gray-200 bg-white'}`}>
        <div className="text-center space-y-6">
          <h2 className={`text-2xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>
            Puzzle Complete!
          </h2>

          <div className="flex justify-center">
            <div className="relative w-36 h-36">
              <svg viewBox="0 0 120 120" className="w-full h-full -rotate-90">
                <circle cx="60" cy="60" r={radius} fill="none" stroke={isDark ? '#374151' : '#e5e7eb'} strokeWidth="8" />
                <motion.circle
                  cx="60" cy="60" r={radius} fill="none"
                  stroke={pct >= 70 ? '#22c55e' : pct >= 40 ? '#eab308' : '#ef4444'}
                  strokeWidth="8" strokeLinecap="round"
                  strokeDasharray={circumference}
                  initial={{ strokeDashoffset: circumference }}
                  animate={{ strokeDashoffset: offset }}
                  transition={{ duration: 1.2, ease: 'easeOut' }}
                />
              </svg>
              <div className="absolute inset-0 flex flex-col items-center justify-center">
                <span className={`text-3xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>{scoring.totalScore}</span>
                <span className={`text-xs ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>points</span>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-3 gap-4 max-w-md mx-auto">
            <div className={`rounded-lg p-3 ${isDark ? 'bg-gray-800' : 'bg-gray-50'}`}>
              <div className={`text-xl font-bold ${isDark ? 'text-blue-400' : 'text-blue-600'}`}>
                {Math.round(scoring.optimalityRatio * 100)}%
              </div>
              <div className={`text-xs ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>Optimality</div>
            </div>
            <div className={`rounded-lg p-3 ${isDark ? 'bg-gray-800' : 'bg-gray-50'}`}>
              <div className={`text-xl font-bold ${isDark ? 'text-green-400' : 'text-green-600'}`}>
                {scoring.moveCount}
              </div>
              <div className={`text-xs ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>Moves</div>
            </div>
            <div className={`rounded-lg p-3 ${isDark ? 'bg-gray-800' : 'bg-gray-50'}`}>
              <div className={`text-xl font-bold ${isDark ? 'text-yellow-400' : 'text-yellow-600'}`}>
                {scoring.hintsUsed}
              </div>
              <div className={`text-xs ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>Hints</div>
            </div>
          </div>

          {scoring.bonuses.length > 0 && (
            <div className="space-y-1">
              {scoring.bonuses.map((b, i) => (
                <div key={i} className={`text-sm ${isDark ? 'text-yellow-400' : 'text-yellow-600'}`}>
                  +{b.points} {b.type}
                </div>
              ))}
            </div>
          )}

          <motion.button
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            onClick={reset}
            className={`px-6 py-2 rounded-lg font-medium transition-colors ${isDark ? 'bg-gray-700 text-gray-200 hover:bg-gray-600' : 'bg-gray-200 text-gray-800 hover:bg-gray-300'}`}
          >
            Play Again
          </motion.button>
        </div>
      </div>
    );
  }

  // ---------- ALGORITHM REVEAL ----------
  if (phase === 'ALGORITHM_REVEAL') {
    return (
      <div className={`rounded-2xl border p-6 max-w-3xl mx-auto ${isDark ? 'border-gray-700 bg-gray-900' : 'border-gray-200 bg-white'}`}>
        <div className="space-y-5">
          <h2 className={`text-xl font-bold text-center ${isDark ? 'text-white' : 'text-gray-900'}`}>
            Algorithm: {blueprint.algorithmName}
          </h2>

          <div className={`rounded-lg p-4 text-sm ${isDark ? 'bg-gray-800 text-gray-300' : 'bg-gray-50 text-gray-600'}`}>
            {blueprint.algorithmExplanation}
          </div>

          <div className={`rounded-lg p-4 text-sm ${isDark ? 'bg-blue-900/20 border border-blue-800 text-blue-300' : 'bg-blue-50 border border-blue-200 text-blue-700'}`}>
            <span className="font-medium">Optimal solution:</span>{' '}
            {blueprint.optimalSolutionDescription}
          </div>

          <div className="flex justify-center gap-3">
            <motion.button
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={complete}
              className="px-6 py-2 rounded-lg bg-blue-600 text-white font-medium hover:bg-blue-500 transition-colors"
            >
              See Final Score
            </motion.button>
          </div>
        </div>
      </div>
    );
  }

  // ---------- PUZZLE_SOLVED ----------
  if (phase === 'PUZZLE_SOLVED') {
    return (
      <div className={`rounded-2xl border p-6 max-w-3xl mx-auto ${isDark ? 'border-gray-700 bg-gray-900' : 'border-gray-200 bg-white'}`}>
        <div className="text-center space-y-5">
          <div className="text-4xl">{scoring.optimalityRatio >= 1 ? '\u{1F3C6}' : '\u2705'}</div>
          <h2 className={`text-xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>
            {state.feedbackMessage}
          </h2>

          <div className={`text-lg font-semibold ${isDark ? 'text-blue-400' : 'text-blue-600'}`}>
            Score: {scoring.totalScore}
          </div>

          <p className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
            Want to learn the algorithm behind the optimal solution?
          </p>

          <div className="flex justify-center gap-3">
            <motion.button
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={revealAlgorithm}
              className="px-6 py-2 rounded-lg bg-blue-600 text-white font-medium hover:bg-blue-500 transition-colors"
            >
              Reveal Algorithm
            </motion.button>
            <motion.button
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={complete}
              className={`px-6 py-2 rounded-lg font-medium transition-colors ${isDark ? 'bg-gray-700 text-gray-200 hover:bg-gray-600' : 'bg-gray-200 text-gray-800 hover:bg-gray-300'}`}
            >
              Skip to Results
            </motion.button>
          </div>
        </div>
      </div>
    );
  }

  // ---------- PLAYING ----------
  return (
    <div className={`rounded-2xl border max-w-3xl mx-auto ${isDark ? 'border-gray-700 bg-gray-900' : 'border-gray-200 bg-white'}`}>
      {/* Header */}
      <div className={`px-5 py-3 border-b flex items-center justify-between ${isDark ? 'border-gray-700' : 'border-gray-200'}`}>
        <div className="flex items-center gap-3">
          <span className="text-lg">{icon}</span>
          <h3 className={`font-semibold ${isDark ? 'text-white' : 'text-gray-900'}`}>
            {blueprint.title}
          </h3>
        </div>
        <div className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
          Moves: {scoring.moveCount}
        </div>
      </div>

      <div className="p-5 space-y-5">
        {/* Objective */}
        <div className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          {blueprint.objective}
        </div>

        {/* Generic board via registry dispatch */}
        <BoardRouter
          config={blueprint.boardConfig}
          state={state}
          dispatch={dispatch}
          constraints={blueprint.constraints}
          constraintResults={state.constraintResults}
          theme={theme}
        />

        {/* Feedback */}
        {state.feedbackMessage && (
          <motion.div
            initial={{ opacity: 0, y: 5 }}
            animate={{ opacity: 1, y: 0 }}
            className={`rounded-lg px-4 py-2 text-sm ${
              state.feedbackType === 'error'
                ? isDark ? 'bg-red-900/20 text-red-300 border border-red-800' : 'bg-red-50 text-red-700 border border-red-200'
                : state.feedbackType === 'success'
                  ? isDark ? 'bg-green-900/20 text-green-300 border border-green-800' : 'bg-green-50 text-green-700 border border-green-200'
                  : isDark ? 'bg-blue-900/20 text-blue-300 border border-blue-800' : 'bg-blue-50 text-blue-700 border border-blue-200'
            }`}
          >
            {state.feedbackMessage}
          </motion.div>
        )}

        {/* Actions */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <HintSystem
              hints={blueprint.hints}
              currentTier={state.hintTier}
              onRequestHint={(tier: number) => useHint(tier)}
              theme={theme}
              hintPenalties={hintPenalties}
            />
            {blueprint.allowUndo && (
              <button
                onClick={undo}
                disabled={state.moveHistory.length === 0}
                className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                  state.moveHistory.length > 0
                    ? isDark ? 'bg-gray-700 text-gray-300 hover:bg-gray-600' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                    : isDark ? 'bg-gray-800 text-gray-600 cursor-not-allowed' : 'bg-gray-50 text-gray-300 cursor-not-allowed'
                }`}
              >
                Reset Board
              </button>
            )}
          </div>

          <motion.button
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            onClick={checkSolution}
            className="px-6 py-2 rounded-lg bg-blue-600 text-white font-medium hover:bg-blue-500 transition-colors"
          >
            Check Solution
          </motion.button>
        </div>
      </div>
    </div>
  );
}
