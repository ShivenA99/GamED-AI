'use client';

import { useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ComplexityAnalyzerBlueprint, GameplayMode } from './types';
import { useComplexityAnalyzerMachine } from './hooks/useComplexityAnalyzerMachine';
import ComplexityCodePanel from './components/ComplexityCodePanel';
import GrowthDataPanel from './components/GrowthDataPanel';
import ComplexityOptionGrid from './components/ComplexityOptionGrid';
import HintSystem from './components/HintSystem';

interface ComplexityAnalyzerGameProps {
  blueprint: ComplexityAnalyzerBlueprint;
  onComplete?: (score: number) => void;
  theme?: 'dark' | 'light';
  gameplayMode?: GameplayMode;
}

export default function ComplexityAnalyzerGame({
  blueprint,
  onComplete,
  theme = 'dark',
  gameplayMode = 'learn',
}: ComplexityAnalyzerGameProps) {
  const isTestMode = gameplayMode === 'test';
  const hintPenalties: [number, number, number] = isTestMode ? [0.1, 0.2, 0.3] : [0, 0, 0];
  const isDark = theme === 'dark';
  const {
    state,
    currentChallenge,
    start,
    selectAnswer,
    selectSection,
    submit,
    nextChallenge,
    useHint,
    reset,
  } = useComplexityAnalyzerMachine(blueprint);

  const { phase, scoring } = state;

  const maxPossible = useMemo(
    () => blueprint.challenges.reduce((s, c) => s + c.points, 0) + 200,
    [blueprint],
  );

  const handleNext = () => {
    const nextIdx = state.currentChallengeIndex + 1;
    if (nextIdx >= blueprint.challenges.length) {
      nextChallenge(); // triggers COMPLETED in reducer
      onComplete?.(scoring.totalScore);
    } else {
      nextChallenge();
    }
  };

  // ---------- INIT phase ----------
  if (phase === 'INIT') {
    return (
      <div className={`rounded-2xl border p-6 max-w-3xl mx-auto ${isDark ? 'border-gray-700 bg-gray-900' : 'border-gray-200 bg-white'}`}>
        <div className="text-center space-y-4">
          <div className="text-4xl">{'\\u{1F4CA}'}</div>
          <h2 className={`text-2xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>
            Complexity Analyzer
          </h2>
          <h3 className={`text-lg font-medium ${isDark ? 'text-blue-400' : 'text-blue-600'}`}>
            {blueprint.algorithmName}
          </h3>
          <p className={`text-sm max-w-lg mx-auto ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
            {blueprint.algorithmDescription}
          </p>

          <div className={`rounded-lg p-4 text-sm ${isDark ? 'bg-gray-800 text-gray-300' : 'bg-gray-50 text-gray-600'}`}>
            <p className="font-medium mb-2">How it works:</p>
            <ul className="text-left space-y-1 list-disc pl-5">
              <li>Analyze code snippets, growth data, or multi-section algorithms</li>
              <li>Identify the Big-O time complexity from the options</li>
              <li>For bottleneck challenges, also identify the slowest section</li>
              <li>Use hints if stuck (-30% points per hint tier)</li>
            </ul>
          </div>

          <div className={`flex items-center justify-center gap-4 text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
            <span>{blueprint.challenges.length} challenges</span>
            <span className="w-1 h-1 rounded-full bg-current" />
            <span>{maxPossible} max points</span>
          </div>

          <motion.button
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            onClick={start}
            className="px-8 py-3 rounded-lg bg-blue-600 text-white font-semibold hover:bg-blue-500 transition-colors"
          >
            Start Analysis
          </motion.button>
        </div>
      </div>
    );
  }

  // ---------- COMPLETED phase ----------
  if (phase === 'COMPLETED') {
    const pct = maxPossible > 0 ? Math.round((scoring.totalScore / maxPossible) * 100) : 0;
    const radius = 54;
    const circumference = 2 * Math.PI * radius;
    const offset = circumference * (1 - pct / 100);

    return (
      <div className={`rounded-2xl border p-6 max-w-3xl mx-auto ${isDark ? 'border-gray-700 bg-gray-900' : 'border-gray-200 bg-white'}`}>
        <div className="text-center space-y-6">
          <h2 className={`text-2xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>
            Analysis Complete!
          </h2>

          {/* Score circle */}
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
                <span className={`text-3xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>
                  {pct}%
                </span>
                <span className={`text-xs ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
                  {scoring.totalScore}/{maxPossible}
                </span>
              </div>
            </div>
          </div>

          {/* Stats */}
          <div className="grid grid-cols-3 gap-4 max-w-md mx-auto">
            <div className={`rounded-lg p-3 ${isDark ? 'bg-gray-800' : 'bg-gray-50'}`}>
              <div className={`text-xl font-bold ${isDark ? 'text-green-400' : 'text-green-600'}`}>
                {scoring.correctCount}/{scoring.totalChallenges}
              </div>
              <div className={`text-xs ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>Correct</div>
            </div>
            <div className={`rounded-lg p-3 ${isDark ? 'bg-gray-800' : 'bg-gray-50'}`}>
              <div className={`text-xl font-bold ${isDark ? 'text-yellow-400' : 'text-yellow-600'}`}>
                {scoring.hintsUsed}
              </div>
              <div className={`text-xs ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>Hints Used</div>
            </div>
            <div className={`rounded-lg p-3 ${isDark ? 'bg-gray-800' : 'bg-gray-50'}`}>
              <div className={`text-xl font-bold ${isDark ? 'text-blue-400' : 'text-blue-600'}`}>
                {scoring.totalScore}
              </div>
              <div className={`text-xs ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>Score</div>
            </div>
          </div>

          {/* Bonuses */}
          {scoring.bonuses.length > 0 && (
            <div className="space-y-1">
              {scoring.bonuses.map((b, i) => (
                <div key={i} className={`text-sm ${isDark ? 'text-yellow-400' : 'text-yellow-600'}`}>
                  +{b.points} {b.type}
                </div>
              ))}
            </div>
          )}

          {/* Per-challenge breakdown */}
          <div className="space-y-2 text-left max-w-md mx-auto">
            <h3 className={`text-sm font-medium ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>
              Challenge Breakdown
            </h3>
            {scoring.perChallenge.map((pc) => {
              const ch = blueprint.challenges.find((c) => c.challengeId === pc.challengeId);
              return (
                <div key={pc.challengeId} className={`flex items-center justify-between text-sm rounded-lg px-3 py-2 ${isDark ? 'bg-gray-800' : 'bg-gray-50'}`}>
                  <span className={isDark ? 'text-gray-300' : 'text-gray-700'}>
                    {ch?.title ?? pc.challengeId}
                  </span>
                  <span className={pc.correct ? (isDark ? 'text-green-400' : 'text-green-600') : (isDark ? 'text-red-400' : 'text-red-600')}>
                    {pc.correct ? '+' : ''}{pc.points} pts
                  </span>
                </div>
              );
            })}
          </div>

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

  // ---------- CHALLENGE / FEEDBACK phase ----------
  if (!currentChallenge) return null;

  const isFeedback = phase === 'FEEDBACK';
  const challengeNum = state.currentChallengeIndex + 1;
  const totalChallenges = blueprint.challenges.length;

  return (
    <div className={`rounded-2xl border max-w-4xl mx-auto ${isDark ? 'border-gray-700 bg-gray-900' : 'border-gray-200 bg-white'}`}>
      {/* Header */}
      <div className={`px-5 py-3 border-b flex items-center justify-between ${isDark ? 'border-gray-700' : 'border-gray-200'}`}>
        <div className="flex items-center gap-3">
          <span className={`text-sm font-medium ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
            Challenge {challengeNum}/{totalChallenges}
          </span>
          <span className={`text-xs px-2 py-0.5 rounded-full ${
            currentChallenge.type === 'identify_from_code'
              ? isDark ? 'bg-blue-900/40 text-blue-300' : 'bg-blue-100 text-blue-700'
              : currentChallenge.type === 'infer_from_growth'
                ? isDark ? 'bg-purple-900/40 text-purple-300' : 'bg-purple-100 text-purple-700'
                : isDark ? 'bg-orange-900/40 text-orange-300' : 'bg-orange-100 text-orange-700'
          }`}>
            {currentChallenge.type === 'identify_from_code' && 'Code Analysis'}
            {currentChallenge.type === 'infer_from_growth' && 'Growth Data'}
            {currentChallenge.type === 'find_bottleneck' && 'Find Bottleneck'}
          </span>
        </div>
        <div className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
          Score: {scoring.totalScore}
        </div>
      </div>

      {/* Progress bar */}
      <div className={`h-1 ${isDark ? 'bg-gray-800' : 'bg-gray-100'}`}>
        <motion.div
          className="h-full bg-blue-500"
          initial={{ width: 0 }}
          animate={{ width: `${(challengeNum / totalChallenges) * 100}%` }}
          transition={{ duration: 0.3 }}
        />
      </div>

      <div className="p-5 space-y-5">
        {/* Title & description */}
        <div>
          <h3 className={`text-lg font-semibold ${isDark ? 'text-white' : 'text-gray-900'}`}>
            {currentChallenge.title}
          </h3>
          {currentChallenge.description && (
            <p className={`text-sm mt-1 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
              {currentChallenge.description}
            </p>
          )}
        </div>

        {/* Challenge content */}
        <AnimatePresence mode="wait">
          <motion.div
            key={currentChallenge.challengeId}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            transition={{ duration: 0.2 }}
          >
            {/* Code panel for identify_from_code and find_bottleneck */}
            {currentChallenge.code && (
              <ComplexityCodePanel
                challenge={currentChallenge}
                selectedSection={state.selectedSection}
                onSelectSection={selectSection}
                theme={theme}
                showFeedback={isFeedback}
                isCorrect={state.isCorrect}
              />
            )}

            {/* Growth data panel */}
            {currentChallenge.growthData && (
              <GrowthDataPanel
                inputSizes={currentChallenge.growthData.inputSizes}
                operationCounts={currentChallenge.growthData.operationCounts}
                theme={theme}
              />
            )}
          </motion.div>
        </AnimatePresence>

        {/* Options grid */}
        <div>
          <p className={`text-sm font-medium mb-3 ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>
            What is the time complexity?
          </p>
          <ComplexityOptionGrid
            options={currentChallenge.options}
            selectedAnswer={state.selectedAnswer}
            onSelect={selectAnswer}
            disabled={isFeedback}
            correctAnswer={isFeedback ? currentChallenge.correctComplexity : null}
            showFeedback={isFeedback}
            theme={theme}
          />
        </div>

        {/* Feedback explanation */}
        {isFeedback && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className={`rounded-lg p-4 text-sm ${
              state.isCorrect
                ? isDark ? 'bg-green-900/20 border border-green-800 text-green-300' : 'bg-green-50 border border-green-200 text-green-700'
                : isDark ? 'bg-red-900/20 border border-red-800 text-red-300' : 'bg-red-50 border border-red-200 text-red-700'
            }`}
          >
            <p className="font-medium mb-1">
              {state.isCorrect
                ? 'Correct!'
                : isTestMode
                  ? 'Incorrect'
                  : `Incorrect — the answer is ${currentChallenge.correctComplexity}`}
            </p>
            {(!isTestMode || state.isCorrect) && (
            <p className={isDark ? 'text-gray-400' : 'text-gray-600'}>
              {currentChallenge.explanation}
            </p>
            )}
          </motion.div>
        )}

        {/* Actions: hints + submit/next */}
        <div className="flex items-center justify-between">
          {!isFeedback ? (
            <HintSystem
              hints={currentChallenge.hints}
              currentTier={state.hintTier}
              onRequestHint={(tier: number) => useHint(tier)}
              theme={theme}
              hintPenalties={hintPenalties}
            />
          ) : (
            <div />
          )}

          {isFeedback ? (
            <motion.button
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={handleNext}
              className="px-6 py-2 rounded-lg bg-blue-600 text-white font-medium hover:bg-blue-500 transition-colors"
            >
              {state.currentChallengeIndex + 1 >= totalChallenges
                ? 'See Results'
                : 'Next Challenge'}
            </motion.button>
          ) : (
            <motion.button
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={submit}
              disabled={!state.selectedAnswer}
              className={`px-6 py-2 rounded-lg font-medium transition-colors ${
                state.selectedAnswer
                  ? 'bg-blue-600 text-white hover:bg-blue-500'
                  : isDark
                    ? 'bg-gray-700 text-gray-500 cursor-not-allowed'
                    : 'bg-gray-200 text-gray-400 cursor-not-allowed'
              }`}
            >
              Submit Answer
            </motion.button>
          )}
        </div>
      </div>
    </div>
  );
}
