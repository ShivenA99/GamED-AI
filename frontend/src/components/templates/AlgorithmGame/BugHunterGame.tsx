'use client';

import { useCallback, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import ClickableCodePanel from './components/ClickableCodePanel';
import TestCasePanel from './components/TestCasePanel';
import FixPanel from './components/FixPanel';
import BugCounter from './components/BugCounter';
import FeedbackToast from './components/FeedbackToast';
import HintSystem from './components/HintSystem';
import InlineCompletionPanel from './components/InlineCompletionPanel';
import RoundHeader from './components/RoundHeader';
import { useBugHunterMachine } from './hooks/useBugHunterMachine';
import { useBugHunterScoring } from './hooks/useBugHunterScoring';
import { BugHunterBlueprint, GameplayMode } from './types';
import { executeWithStringMatch } from './services/codeExecution';

interface BugHunterGameProps {
  blueprint: BugHunterBlueprint;
  onComplete?: (score: number) => void;
  theme?: 'dark' | 'light';
  gameplayMode?: GameplayMode;
}

export default function BugHunterGame({
  blueprint,
  onComplete,
  theme = 'dark',
  gameplayMode = 'learn',
}: BugHunterGameProps) {
  const isTestMode = gameplayMode === 'test';
  const hintPenalties: [number, number, number] = isTestMode ? [0.1, 0.2, 0.3] : [0, 0, 0];
  const isDark = theme === 'dark';

  const {
    state,
    normalized,
    currentRound,
    currentBug,
    startHunting,
    clickLine,
    selectLine,
    confirmSelection,
    dismissFeedback,
    submitFix,
    setTestResults,
    setExecutionPending,
    advanceAfterFix,
    advanceRound,
    useHint,
    startVerification,
    complete,
    reset,
  } = useBugHunterMachine(blueprint);

  const { finalScore, accuracy, message } = useBugHunterScoring(state.scoring);

  // Fire onComplete exactly once when game completes (must be before any conditional returns)
  const completedRef = useRef(false);
  useEffect(() => {
    if (state.phase === 'COMPLETED' && !completedRef.current) {
      completedRef.current = true;
      onComplete?.(finalScore);
    }
    if (state.phase === 'INIT') {
      completedRef.current = false;
    }
  }, [state.phase, finalScore, onComplete]);

  const fixMode = normalized.config.fixMode;
  const isMultiRound = normalized.rounds.length > 1;
  const isMultiLineBug = currentBug ? currentBug.bugLines.length > 1 : false;

  // Compute fixed bugs info for the code panel
  // In test mode, hide the green fix overlay (correctLineText) while still hunting —
  // showing the correct code for previously fixed bugs gives away patterns for remaining bugs.
  const fixedBugs = currentRound
    ? currentRound.bugs
        .filter((b) => state.fixedBugIds.includes(b.bugId))
        .map((b) => {
          const bugLines = b.bugLines ?? (b.lineNumber != null ? [b.lineNumber] : []);
          const buggyLinesText = b.buggyLinesText ?? (b.buggyLineText ? [b.buggyLineText] : []);
          const correctLinesText = b.correctLinesText ?? (b.correctLineText ? [b.correctLineText] : []);

          if (bugLines.length > 1) {
            return { bugLines, buggyLinesText, correctLinesText };
          }
          return {
            lineNumber: bugLines[0] ?? 0,
            buggyLineText: buggyLinesText[0] ?? '',
            correctLineText: correctLinesText[0] ?? '',
          };
        })
    : [];

  const isHunting = state.phase === 'BUG_HUNTING';
  const isFixing = state.phase === 'LINE_SELECTED' || state.phase === 'WRONG_FIX';

  // Handle free-text test execution
  const handleRunTests = useCallback(
    (code: string) => {
      if (!currentBug || !currentRound) return;
      setExecutionPending(true);

      // Use string match execution (simulates backend)
      setTimeout(() => {
        const results = executeWithStringMatch(
          code,
          currentBug.correctLinesText,
          currentRound.testCases,
          currentBug.bugId,
        );
        setTestResults(results);
      }, 500); // Small delay for UX
    },
    [currentBug, currentRound, setTestResults, setExecutionPending],
  );

  // Check if we need to show "Next Round" vs "Next Bug" after fix
  const allBugsInRoundFixed = currentRound
    ? currentRound.bugs.every((b) => state.fixedBugIds.includes(b.bugId))
    : false;

  // In test mode, suppress the green fix overlay while still hunting for more bugs.
  // Only show fix overlays once all bugs in the round are found or the game is completed.
  const showFixOverlays = !isTestMode || allBugsInRoundFixed || state.phase === 'VERIFICATION' || state.phase === 'COMPLETED';
  const displayFixedBugs = showFixOverlays ? fixedBugs : [];
  const isLastRound = state.currentRoundIndex >= normalized.rounds.length - 1;

  // --- READING_CODE / INIT phase ---
  if (state.phase === 'INIT' || state.phase === 'READING_CODE') {
    const round = currentRound;
    if (!round) return null;

    return (
      <div className={`rounded-xl overflow-hidden ${isDark ? 'bg-gray-900' : 'bg-white'}`}>
        {/* Header */}
        <div className={`px-6 py-4 border-b ${isDark ? 'border-gray-700 bg-gray-800' : 'border-gray-200 bg-gray-50'}`}>
          <h2 className={`text-xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>
            {normalized.algorithmName} — Bug Hunter
          </h2>
          <p className={`text-sm mt-1 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
            {normalized.narrativeIntro}
          </p>
        </div>

        <div className="p-6">
          {isMultiRound && (
            <RoundHeader
              currentRound={state.currentRoundIndex}
              totalRounds={normalized.rounds.length}
              roundTitle={round.title}
              theme={theme}
            />
          )}

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Code */}
            <div className="lg:col-span-2">
              <ClickableCodePanel
                code={round.buggyCode}
                language={normalized.language}
                lineStates={{}}
                fixedBugs={[]}
                clickable={false}
                onLineClick={() => {}}
                selectedLine={null}
                theme={theme}
              />
            </div>

            {/* Test cases */}
            <div>
              <TestCasePanel
                testCases={round.testCases}
                fixedBugIds={[]}
                theme={theme}
              />
            </div>
          </div>

          {/* Start button */}
          <div className="mt-6 text-center">
            <p className={`text-sm mb-3 ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
              Read the code and observe the failing test cases, then start hunting for {round.bugs.length} bug{round.bugs.length > 1 ? 's' : ''}.
            </p>
            <motion.button
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={startHunting}
              className="px-8 py-3 bg-primary-500 text-white rounded-lg hover:bg-primary-600 transition-colors font-medium text-lg"
            >
              {state.phase === 'READING_CODE' ? 'Start Hunting' : 'Start Hunting'}
            </motion.button>
          </div>
        </div>
      </div>
    );
  }

  // --- VERIFICATION phase (inline) ---
  if (state.phase === 'VERIFICATION') {
    // Collect all test cases across all rounds, with unique IDs
    const allTestCases = normalized.rounds.flatMap((r, ri) =>
      r.testCases.map((tc) => ({ ...tc, id: `r${ri}_${tc.id}` })),
    );

    return (
      <div className={`rounded-xl overflow-hidden ${isDark ? 'bg-gray-900' : 'bg-white'}`}>
        {/* Header */}
        <div className={`px-6 py-4 border-b ${isDark ? 'border-gray-700 bg-gray-800' : 'border-gray-200 bg-gray-50'}`}>
          <h2 className={`text-xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>
            {normalized.algorithmName} — Bug Hunter
          </h2>
        </div>

        <div className="p-6">
          {/* Show code from current (last) round with all fixes */}
          {currentRound && (
            <div className="mb-6">
              <ClickableCodePanel
                code={currentRound.buggyCode}
                language={normalized.language}
                lineStates={state.lineStates}
                fixedBugs={displayFixedBugs}
                clickable={false}
                onLineClick={() => {}}
                selectedLine={null}
                theme={theme}
              />
            </div>
          )}

          <InlineCompletionPanel
            testCases={allTestCases}
            scoring={state.scoring}
            onComplete={complete}
            theme={theme}
          />
        </div>
      </div>
    );
  }

  // --- COMPLETED phase ---
  if (state.phase === 'COMPLETED') {
    return (
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        className={`rounded-xl p-8 ${isDark ? 'bg-gray-900' : 'bg-white'}`}
      >
        <div className="text-center">
          <motion.div
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            transition={{ type: 'spring', delay: 0.2 }}
            className="w-28 h-28 mx-auto mb-6 bg-gradient-to-br from-primary-500 to-secondary-500 rounded-full flex items-center justify-center shadow-lg"
          >
            <span className="text-3xl font-bold text-white">{accuracy}%</span>
          </motion.div>

          <h2 className={`text-3xl font-bold mb-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>
            Bugs Squashed!
          </h2>
          <p className={`text-lg mb-8 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
            {message}
          </p>

          {/* Stats grid */}
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4 mb-8 max-w-lg mx-auto">
            {[
              { label: 'Final Score', value: finalScore, color: 'text-primary-500' },
              { label: 'Bugs Found', value: `${state.scoring.bugsFound}/${state.scoring.totalBugs}`, color: 'text-green-400' },
              { label: 'Wrong Clicks', value: state.scoring.wrongLineClicks, color: state.scoring.wrongLineClicks === 0 ? 'text-green-400' : 'text-yellow-400' },
              { label: 'Wrong Fixes', value: state.scoring.wrongFixAttempts, color: state.scoring.wrongFixAttempts === 0 ? 'text-green-400' : 'text-yellow-400' },
              { label: 'Hints Used', value: state.scoring.hintsUsed, color: 'text-blue-400' },
              { label: 'Accuracy', value: `${accuracy}%`, color: accuracy === 100 ? 'text-green-400' : 'text-yellow-400' },
            ].map((stat, i) => (
              <motion.div
                key={stat.label}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.3 + i * 0.08 }}
                className={`p-3 rounded-lg ${isDark ? 'bg-gray-800' : 'bg-gray-100'}`}
              >
                <div className={`text-2xl font-bold ${stat.color}`}>{stat.value}</div>
                <div className={`text-xs ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
                  {stat.label}
                </div>
              </motion.div>
            ))}
          </div>

          {/* Bonuses */}
          {state.scoring.bonuses.length > 0 && (
            <div className="mb-6 max-w-sm mx-auto">
              {state.scoring.bonuses.map((b) => (
                <div
                  key={b.type}
                  className={`flex justify-between text-sm px-3 py-1 ${isDark ? 'text-yellow-300' : 'text-yellow-700'}`}
                >
                  <span>{b.type}</span>
                  <span className="font-bold">+{b.points}</span>
                </div>
              ))}
            </div>
          )}

          <button
            onClick={reset}
            className="px-8 py-3 bg-primary-500 text-white rounded-lg hover:bg-primary-600 transition-colors font-medium"
          >
            Play Again
          </button>
        </div>
      </motion.div>
    );
  }

  // --- BUG_HUNTING / LINE_SELECTED / WRONG_FIX / BUG_FIXED phases ---
  if (!currentRound) return null;

  return (
    <div className={`rounded-xl overflow-hidden ${isDark ? 'bg-gray-900' : 'bg-white'}`}>
      {/* Header */}
      <div className={`px-6 py-4 border-b ${isDark ? 'border-gray-700 bg-gray-800' : 'border-gray-200 bg-gray-50'}`}>
        <div className="flex items-center justify-between">
          <div>
            <h2 className={`text-xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>
              {normalized.algorithmName} — Bug Hunter
            </h2>
            <p className={`text-sm mt-0.5 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
              Find and fix the bugs in this code
            </p>
          </div>
          <BugCounter
            total={currentRound.bugs.length}
            found={currentRound.bugs.filter((b) => state.fixedBugIds.includes(b.bugId)).length}
            theme={theme}
          />
        </div>
      </div>

      {/* Round header */}
      {isMultiRound && (
        <div className="px-6 pt-3">
          <RoundHeader
            currentRound={state.currentRoundIndex}
            totalRounds={normalized.rounds.length}
            roundTitle={currentRound.title}
            theme={theme}
          />
        </div>
      )}

      {/* Score bar */}
      <div className={`px-6 py-2 flex items-center gap-4 ${isDark ? 'bg-gray-800/50' : 'bg-gray-100'}`}>
        <div className="flex items-center gap-1.5">
          <span className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>Score:</span>
          <AnimatePresence mode="popLayout">
            <motion.span
              key={state.scoring.totalScore}
              initial={{ y: -10, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              className="font-bold text-lg text-primary-500"
            >
              {Math.max(0, state.scoring.totalScore)}
            </motion.span>
          </AnimatePresence>
        </div>
        {state.scoring.wrongLineClicks > 0 && (
          <span className={`text-xs ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>
            Wrong clicks: {state.scoring.wrongLineClicks}
          </span>
        )}
        {fixMode === 'free_text' && (
          <span className={`text-xs px-2 py-0.5 rounded-full ml-2 ${
            isDark ? 'bg-blue-900/30 text-blue-400' : 'bg-blue-100 text-blue-700'
          }`}>
            Free Text
          </span>
        )}
        {currentBug && (
          <span className={`text-xs ml-auto px-2 py-0.5 rounded-full ${
            currentBug.difficulty === 1
              ? isDark ? 'bg-green-900/30 text-green-400' : 'bg-green-100 text-green-700'
              : currentBug.difficulty === 2
              ? isDark ? 'bg-yellow-900/30 text-yellow-400' : 'bg-yellow-100 text-yellow-700'
              : isDark ? 'bg-red-900/30 text-red-400' : 'bg-red-100 text-red-700'
          }`}>
            {currentBug.difficulty === 1 ? 'Easy' : currentBug.difficulty === 2 ? 'Medium' : 'Hard'}
          </span>
        )}
      </div>

      {/* Feedback toast */}
      {state.phase === 'BUG_HUNTING' && state.feedbackMessage && (
        <div className="px-6 pt-3">
          <FeedbackToast
            message={state.feedbackMessage}
            type={state.feedbackType}
            onDismiss={dismissFeedback}
            theme={theme}
          />
        </div>
      )}

      {/* Main content */}
      <div className="p-6">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left 2/3: Code + Fix Panel */}
          <div className="lg:col-span-2 space-y-4">
            <ClickableCodePanel
              code={currentRound.buggyCode}
              language={normalized.language}
              lineStates={state.lineStates}
              fixedBugs={displayFixedBugs}
              clickable={isHunting}
              onLineClick={clickLine}
              onLineSelect={selectLine}
              onConfirmSelection={confirmSelection}
              selectedLine={state.selectedLine}
              selectedLines={state.selectedLines}
              multiLineMode={isHunting && isMultiLineBug}
              theme={theme}
            />

            {/* Fix Panel — shown when line selected or wrong fix */}
            <AnimatePresence>
              {isFixing && currentBug && (
                <FixPanel
                  buggyLineText={currentBug.buggyLinesText[0]}
                  buggyLinesText={currentBug.buggyLinesText}
                  lineNumber={currentBug.bugLines[0]}
                  bugLines={currentBug.bugLines}
                  fixOptions={currentBug.fixOptions}
                  fixMode={fixMode}
                  onSubmit={submitFix}
                  onRunTests={handleRunTests}
                  feedbackMessage={state.phase === 'WRONG_FIX' ? state.feedbackMessage : null}
                  feedbackType={state.phase === 'WRONG_FIX' ? 'error' : null}
                  testResults={state.testResults}
                  showTestResults={state.showTestResults}
                  executionPending={state.executionPending}
                  theme={theme}
                />
              )}
            </AnimatePresence>

            {/* Bug Fixed feedback */}
            <AnimatePresence>
              {state.phase === 'BUG_FIXED' && currentBug && (
                <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0 }}
                  className={`p-4 rounded-lg border ${
                    isDark
                      ? 'bg-green-900/20 border-green-800/40'
                      : 'bg-green-50 border-green-200'
                  }`}
                >
                  <div className="flex items-start gap-3">
                    <motion.span
                      initial={{ scale: 0 }}
                      animate={{ scale: 1 }}
                      transition={{ type: 'spring' }}
                      className="text-2xl"
                    >
                      {'\u2713'}
                    </motion.span>
                    <div>
                      <h4 className={`font-bold mb-1 ${isDark ? 'text-green-300' : 'text-green-800'}`}>
                        Bug Fixed!
                      </h4>
                      {isTestMode ? (
                        <p className={`text-sm mb-2 ${isDark ? 'text-green-200' : 'text-green-700'}`}>
                          Nice find! Keep hunting for the remaining bugs.
                        </p>
                      ) : (
                        <>
                          <p className={`text-sm mb-2 ${isDark ? 'text-green-200' : 'text-green-700'}`}>
                            {state.feedbackMessage}
                          </p>
                          <p className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
                            {currentBug.explanation}
                          </p>
                          <div className="mt-2">
                            <span className={`text-xs px-2 py-0.5 rounded-full ${
                              isDark ? 'bg-gray-700 text-gray-300' : 'bg-gray-200 text-gray-600'
                            }`}>
                              Bug type: {currentBug.bugType.replace(/_/g, ' ')}
                            </span>
                          </div>
                        </>
                      )}
                    </div>
                  </div>

                  <div className="mt-4 flex justify-end">
                    <motion.button
                      whileHover={{ scale: 1.02 }}
                      whileTap={{ scale: 0.98 }}
                      onClick={() => {
                        if (allBugsInRoundFixed) {
                          if (isLastRound) {
                            startVerification();
                          } else {
                            advanceRound();
                          }
                        } else {
                          advanceAfterFix();
                        }
                      }}
                      className="px-6 py-2 rounded-lg font-medium text-sm bg-primary-500 text-white hover:bg-primary-600 transition-colors"
                    >
                      {allBugsInRoundFixed
                        ? isLastRound
                          ? 'Run Verification'
                          : `Next Round (${state.currentRoundIndex + 2}/${normalized.rounds.length})`
                        : `Hunt Next Bug (${currentRound.bugs.filter((b) => state.fixedBugIds.includes(b.bugId)).length}/${currentRound.bugs.length})`}
                    </motion.button>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>

            {/* Hints — shown during hunting */}
            {isHunting && currentBug && (
              <HintSystem
                hints={currentBug.hints}
                currentTier={state.hintTier}
                onRequestHint={useHint}
                theme={theme}
                hintPenalties={hintPenalties}
              />
            )}
          </div>

          {/* Right 1/3: Test Cases */}
          <div>
            <TestCasePanel
              testCases={currentRound.testCases}
              fixedBugIds={state.fixedBugIds}
              theme={theme}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
