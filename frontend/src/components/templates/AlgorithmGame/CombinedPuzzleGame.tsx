'use client';

import { useCallback, useMemo } from 'react';
import { motion } from 'framer-motion';
import { useCombinedPuzzleMachine } from './hooks/useCombinedPuzzleMachine';
import { isGenericBlueprint, migrateBlueprint } from './constraintPuzzle/migrateBlueprint';
import BoardRouter from './constraintPuzzle/BoardRouter';
import HintSystem from './components/HintSystem';
import AlgorithmCodePanel from './algorithmChallenge/AlgorithmCodePanel';
import TestRunnerPanel from './algorithmChallenge/TestRunnerPanel';
import SolutionComparison from './algorithmChallenge/SolutionComparison';
import {
  CombinedPuzzleBlueprint,
  getSerializerForBoardType,
} from './algorithmChallenge/combinedPuzzleTypes';

interface CombinedPuzzleGameProps {
  blueprint: CombinedPuzzleBlueprint;
  onComplete?: (score: number) => void;
  theme?: 'dark' | 'light';
}

export default function CombinedPuzzleGame({
  blueprint,
  onComplete,
  theme = 'dark',
}: CombinedPuzzleGameProps) {
  const isDark = theme === 'dark';

  // Ensure puzzle blueprint is in generic format
  const normalizedBlueprint = useMemo<CombinedPuzzleBlueprint>(() => {
    const puzzleBp = isGenericBlueprint(blueprint.puzzleBlueprint)
      ? blueprint.puzzleBlueprint
      : migrateBlueprint(blueprint.puzzleBlueprint as never);
    return { ...blueprint, puzzleBlueprint: puzzleBp };
  }, [blueprint]);

  const {
    gamePhase,
    codeSide,
    scoring,
    puzzleMachine,
    parsonsMachine,
    parsonsBlueprint,
    startGame,
    setActiveTab,
    setFreeCode,
    runCode,
    submitCode,
    useCodeHint,
    tryComparison,
    completeGame,
    resetGame,
  } = useCombinedPuzzleMachine(normalizedBlueprint);

  const puzzleBp = normalizedBlueprint.puzzleBlueprint;
  const challenge = normalizedBlueprint.algorithmChallenge;
  const icon = normalizedBlueprint.icon ?? '\u{1F9E9}';

  const puzzleSolved =
    puzzleMachine.state.phase === 'PUZZLE_SOLVED' ||
    puzzleMachine.state.phase === 'ALGORITHM_REVEAL' ||
    puzzleMachine.state.phase === 'COMPLETED';

  const puzzleSerialized = useMemo(() => {
    const serializer = getSerializerForBoardType(puzzleBp.boardConfig.boardType);
    return serializer(puzzleMachine.state);
  }, [puzzleBp.boardConfig.boardType, puzzleMachine.state]);

  const handleSubmitCode = useCallback(() => {
    submitCode();
    // Check both sides after a tick to let state settle
    setTimeout(() => tryComparison(), 0);
  }, [submitCode, tryComparison]);

  const handleCheckPuzzleSolution = useCallback(() => {
    puzzleMachine.checkSolution();
    setTimeout(() => tryComparison(), 0);
  }, [puzzleMachine, tryComparison]);

  const handleComplete = useCallback(() => {
    completeGame();
    onComplete?.(scoring.totalScore);
  }, [completeGame, onComplete, scoring.totalScore]);

  // ======================== INTRO ========================
  if (gamePhase === 'INTRO') {
    return (
      <div className={`rounded-2xl border p-6 max-w-5xl mx-auto ${isDark ? 'border-gray-700 bg-gray-900' : 'border-gray-200 bg-white'}`}>
        <div className="text-center space-y-4">
          <div className="text-4xl">{icon}</div>
          <h2 className={`text-2xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>
            {normalizedBlueprint.title}
          </h2>
          <p className={`text-sm max-w-xl mx-auto ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
            {normalizedBlueprint.description}
          </p>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 max-w-2xl mx-auto mt-6">
            <div className={`rounded-lg p-4 text-left ${isDark ? 'bg-gray-800' : 'bg-gray-50'}`}>
              <div className={`text-sm font-semibold mb-1 ${isDark ? 'text-blue-400' : 'text-blue-600'}`}>
                Code Challenge
              </div>
              <p className={`text-xs ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
                {challenge.mode === 'parsons'
                  ? 'Arrange code blocks to implement the algorithm.'
                  : challenge.mode === 'free_code'
                    ? 'Write the algorithm from scratch in Python.'
                    : 'Choose Parsons blocks or free code to implement the algorithm.'}
              </p>
            </div>
            <div className={`rounded-lg p-4 text-left ${isDark ? 'bg-gray-800' : 'bg-gray-50'}`}>
              <div className={`text-sm font-semibold mb-1 ${isDark ? 'text-purple-400' : 'text-purple-600'}`}>
                Manual Puzzle
              </div>
              <p className={`text-xs ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
                {puzzleBp.objective}
              </p>
            </div>
          </div>

          <div className={`text-xs max-w-md mx-auto ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>
            Solve both sides, then earn a bonus if your code output matches your manual solution!
          </div>

          <motion.button
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            onClick={startGame}
            className="px-8 py-3 rounded-lg bg-blue-600 text-white font-semibold hover:bg-blue-500 transition-colors"
          >
            Start Challenge
          </motion.button>
        </div>
      </div>
    );
  }

  // ======================== COMPARING ========================
  if (gamePhase === 'COMPARING') {
    return (
      <div className="max-w-5xl mx-auto">
        <SolutionComparison
          scoring={scoring}
          codeOutput={codeSide.puzzleCaseOutput}
          puzzleSerialized={puzzleSerialized}
          onContinue={handleComplete}
          theme={theme}
        />
      </div>
    );
  }

  // ======================== COMPLETED ========================
  if (gamePhase === 'COMPLETED') {
    const pct = Math.round((scoring.totalScore / 700) * 100);
    return (
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        className={`rounded-2xl border p-8 max-w-3xl mx-auto ${isDark ? 'border-gray-700 bg-gray-900' : 'border-gray-200 bg-white'}`}
      >
        <div className="text-center space-y-6">
          <motion.div
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            transition={{ type: 'spring', delay: 0.2 }}
            className="w-28 h-28 mx-auto bg-gradient-to-br from-blue-500 to-purple-500 rounded-full flex items-center justify-center shadow-lg"
          >
            <span className="text-3xl font-bold text-white">{pct}%</span>
          </motion.div>

          <h2 className={`text-3xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>
            Challenge Complete!
          </h2>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 max-w-lg mx-auto">
            {[
              { label: 'Code', value: scoring.codeScore, color: 'text-blue-400' },
              { label: 'Puzzle', value: scoring.puzzleScore, color: 'text-purple-400' },
              { label: 'Bonus', value: scoring.consistencyBonus, color: 'text-green-400' },
              { label: 'Total', value: scoring.totalScore, color: 'text-yellow-400' },
            ].map((s, i) => (
              <motion.div
                key={s.label}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.3 + i * 0.08 }}
                className={`p-3 rounded-lg ${isDark ? 'bg-gray-800' : 'bg-gray-100'}`}
              >
                <div className={`text-2xl font-bold ${s.color}`}>{s.value}</div>
                <div className={`text-xs ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>{s.label}</div>
              </motion.div>
            ))}
          </div>

          <motion.button
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            onClick={resetGame}
            className="px-8 py-3 rounded-lg bg-blue-600 text-white font-medium hover:bg-blue-500 transition-colors"
          >
            Play Again
          </motion.button>
        </div>
      </motion.div>
    );
  }

  // ======================== PLAYING ========================
  return (
    <div className="max-w-[1400px] mx-auto space-y-4">
      {/* Header */}
      <div className={`rounded-xl border px-5 py-3 flex items-center justify-between ${isDark ? 'border-gray-700 bg-gray-900' : 'border-gray-200 bg-white'}`}>
        <div className="flex items-center gap-3">
          <span className="text-lg">{icon}</span>
          <div>
            <h2 className={`font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>
              {normalizedBlueprint.title}
            </h2>
            <p className={`text-xs ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
              {normalizedBlueprint.description}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3 text-xs">
          <span className={`px-2 py-1 rounded-full ${
            codeSide.phase === 'SUBMITTED'
              ? 'bg-green-600/20 text-green-400'
              : isDark ? 'bg-gray-800 text-gray-400' : 'bg-gray-100 text-gray-500'
          }`}>
            Code: {codeSide.phase === 'SUBMITTED' ? 'Done' : 'In Progress'}
          </span>
          <span className={`px-2 py-1 rounded-full ${
            puzzleSolved
              ? 'bg-green-600/20 text-green-400'
              : isDark ? 'bg-gray-800 text-gray-400' : 'bg-gray-100 text-gray-500'
          }`}>
            Puzzle: {puzzleSolved ? 'Done' : 'In Progress'}
          </span>
        </div>
      </div>

      {/* Side-by-side layout */}
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-4">
        {/* Left: Code Panel (3 cols) */}
        <div className="lg:col-span-3">
          <AlgorithmCodePanel
            challengeMode={challenge.mode}
            codeSide={codeSide}
            parsonsState={parsonsMachine.state}
            parsonsBlueprint={parsonsBlueprint}
            onActiveTabChange={setActiveTab}
            onFreeCodeChange={setFreeCode}
            onRunCode={runCode}
            onSubmitCode={handleSubmitCode}
            onHint={useCodeHint}
            onMoveToSolution={parsonsMachine.moveToSolution}
            onMoveToSource={parsonsMachine.moveToSource}
            onReorderSolution={parsonsMachine.reorderSolution}
            onSetIndent={parsonsMachine.setIndent}
            onSetActiveBlock={parsonsMachine.setActiveBlock}
            hints={challenge.hints}
            theme={theme}
          />
        </div>

        {/* Right: Puzzle Board (2 cols) */}
        <div className="lg:col-span-2">
          <div className={`rounded-xl border ${isDark ? 'border-gray-700 bg-gray-900' : 'border-gray-200 bg-white'}`}>
            <div className={`px-4 py-3 border-b ${isDark ? 'border-gray-700' : 'border-gray-200'}`}>
              <span className={`text-sm font-semibold ${isDark ? 'text-gray-200' : 'text-gray-800'}`}>
                Manual Puzzle
              </span>
              <span className={`text-xs ml-2 ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>
                Moves: {puzzleMachine.state.scoring.moveCount}
              </span>
            </div>

            <div className="p-4 space-y-4">
              <div className={`text-xs ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
                {puzzleBp.objective}
              </div>

              {puzzleMachine.state.phase === 'PUZZLE_SOLVED' ? (
                <div className={`text-center py-4 rounded-lg ${isDark ? 'bg-green-900/20' : 'bg-green-50'}`}>
                  <div className="text-2xl mb-1">{puzzleMachine.state.scoring.optimalityRatio >= 1 ? '\u{1F3C6}' : '\u2705'}</div>
                  <div className={`text-sm font-medium ${isDark ? 'text-green-300' : 'text-green-700'}`}>
                    {puzzleMachine.state.feedbackMessage}
                  </div>
                  <div className={`text-xs mt-1 ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
                    Score: {puzzleMachine.state.scoring.totalScore}
                  </div>
                </div>
              ) : (
                <>
                  <BoardRouter
                    config={puzzleBp.boardConfig}
                    state={puzzleMachine.state}
                    dispatch={puzzleMachine.dispatch}
                    constraints={puzzleBp.constraints}
                    constraintResults={puzzleMachine.state.constraintResults}
                    theme={theme}
                  />

                  {puzzleMachine.state.feedbackMessage && (
                    <div className={`text-xs px-3 py-2 rounded-lg ${
                      puzzleMachine.state.feedbackType === 'error'
                        ? isDark ? 'bg-red-900/20 text-red-300' : 'bg-red-50 text-red-600'
                        : isDark ? 'bg-blue-900/20 text-blue-300' : 'bg-blue-50 text-blue-600'
                    }`}>
                      {puzzleMachine.state.feedbackMessage}
                    </div>
                  )}

                  <div className="flex items-center justify-between">
                    <HintSystem
                      hints={puzzleBp.hints}
                      currentTier={puzzleMachine.state.hintTier}
                      onRequestHint={(tier: number) => puzzleMachine.useHint(tier)}
                      theme={theme}
                    />
                    <motion.button
                      whileHover={{ scale: 1.02 }}
                      whileTap={{ scale: 0.98 }}
                      onClick={handleCheckPuzzleSolution}
                      className="px-4 py-2 rounded-lg bg-purple-600 text-white text-sm font-medium hover:bg-purple-500 transition-colors"
                    >
                      Check Solution
                    </motion.button>
                  </div>
                </>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Bottom: Test Runner */}
      <TestRunnerPanel
        results={codeSide.testResults}
        passRate={codeSide.passRate}
        theme={theme}
      />

      {/* Both done prompt */}
      {puzzleSolved && codeSide.phase === 'SUBMITTED' && gamePhase === 'PLAYING' && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className={`rounded-xl border p-4 text-center ${isDark ? 'border-green-800 bg-green-900/20' : 'border-green-200 bg-green-50'}`}
        >
          <p className={`text-sm font-medium mb-2 ${isDark ? 'text-green-300' : 'text-green-700'}`}>
            Both sides complete! Ready to compare your solutions?
          </p>
          <motion.button
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            onClick={tryComparison}
            className="px-6 py-2 rounded-lg bg-green-600 text-white font-medium hover:bg-green-500 transition-colors"
          >
            Compare Solutions
          </motion.button>
        </motion.div>
      )}
    </div>
  );
}
