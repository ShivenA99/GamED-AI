'use client';

import { useCallback, useEffect, useMemo, useRef } from 'react';
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  DragEndEvent,
  DragStartEvent,
  DragOverlay,
} from '@dnd-kit/core';
import { sortableKeyboardCoordinates } from '@dnd-kit/sortable';
import { motion, AnimatePresence } from 'framer-motion';
import { useAlgorithmBuilderMachine } from './hooks/useAlgorithmBuilderMachine';
import {
  gradeSubmission,
  useAlgorithmBuilderScoring,
} from './hooks/useAlgorithmBuilderScoring';
import { AlgorithmBuilderBlueprint, GameplayMode } from './types';
import SourcePanel from './components/SourcePanel';
import SolutionPanel from './components/SolutionPanel';
import HintSystem from './components/HintSystem';

interface AlgorithmBuilderGameProps {
  blueprint: AlgorithmBuilderBlueprint;
  onComplete?: (score: number) => void;
  theme?: 'dark' | 'light';
  gameplayMode?: GameplayMode;
}

export default function AlgorithmBuilderGame({
  blueprint,
  onComplete,
  theme = 'dark',
  gameplayMode = 'learn',
}: AlgorithmBuilderGameProps) {
  const isTestMode = gameplayMode === 'test';
  const hintPenalties: [number, number, number] = isTestMode ? [0.1, 0.2, 0.3] : [0, 0, 0];
  const isDark = theme === 'dark';

  const {
    state,
    startBuilding,
    moveToSolution,
    moveToSource,
    reorderSolution,
    setIndent,
    setActiveBlock,
    submit,
    retry,
    useHint,
    reset,
  } = useAlgorithmBuilderMachine(blueprint);

  const totalBlocks = (blueprint.correct_order?.length ?? 0) + (blueprint.distractors?.length ?? 0);
  const { finalScore, accuracy, message } = useAlgorithmBuilderScoring(
    state.scoring,
    totalBlocks,
  );

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

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 5 } }),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    }),
  );

  // Find which container a block belongs to
  const findContainer = useCallback(
    (id: string): 'source' | 'solution' | null => {
      if (id === 'source' || id === 'solution') return id as 'source' | 'solution';
      if (state.sourceBlocks.find((b) => b.id === id)) return 'source';
      if (state.solutionBlocks.find((b) => b.id === id)) return 'solution';
      return null;
    },
    [state.sourceBlocks, state.solutionBlocks],
  );

  // Get the block being dragged for the DragOverlay
  const activeBlock = useMemo(() => {
    if (!state.activeBlockId) return null;
    return (
      state.sourceBlocks.find((b) => b.id === state.activeBlockId) ??
      state.solutionBlocks.find((b) => b.id === state.activeBlockId) ??
      null
    );
  }, [state.activeBlockId, state.sourceBlocks, state.solutionBlocks]);

  const handleDragStart = useCallback(
    (event: DragStartEvent) => {
      setActiveBlock(String(event.active.id));
    },
    [setActiveBlock],
  );

  const handleDragEnd = useCallback(
    (event: DragEndEvent) => {
      const { active, over } = event;
      setActiveBlock(null);

      if (!over) return;

      const activeId = String(active.id);
      const overId = String(over.id);

      const activeContainer = findContainer(activeId);
      const overContainer = findContainer(overId);

      if (!activeContainer || !overContainer) return;

      if (activeContainer === overContainer) {
        // Same container reorder (only meaningful in solution)
        if (activeContainer === 'solution' && activeId !== overId) {
          reorderSolution(activeId, overId);
        }
      } else {
        // Cross-container move
        if (activeContainer === 'source' && overContainer === 'solution') {
          if (overId === 'solution') {
            // Dropped on empty solution container
            moveToSolution(activeId, state.solutionBlocks.length);
          } else {
            // Dropped on a specific block in solution
            const overIndex = state.solutionBlocks.findIndex((b) => b.id === overId);
            moveToSolution(
              activeId,
              overIndex >= 0 ? overIndex : state.solutionBlocks.length,
            );
          }
        } else if (activeContainer === 'solution' && overContainer === 'source') {
          moveToSource(activeId);
        }
      }
    },
    [
      findContainer,
      state.solutionBlocks,
      moveToSolution,
      moveToSource,
      reorderSolution,
      setActiveBlock,
    ],
  );

  const handleSubmit = useCallback(() => {
    const result = gradeSubmission(
      state.solutionBlocks,
      state.sourceBlocks,
      blueprint,
      state.scoring.attempts,
      state.scoring.hintPenalty,
    );
    submit(result.feedback, result.score, result.bonuses, result.allCorrect);
  }, [state.solutionBlocks, state.sourceBlocks, blueprint, state.scoring, submit]);

  const handleIndentChange = useCallback(
    (blockId: string, indent: number) => {
      setIndent(blockId, indent);
    },
    [setIndent],
  );

  // --- INIT phase ---
  if (state.phase === 'INIT') {
    return (
      <div className={`rounded-xl overflow-hidden ${isDark ? 'bg-gray-900' : 'bg-white'}`}>
        <div
          className={`px-6 py-4 border-b ${
            isDark ? 'border-gray-700 bg-gray-800' : 'border-gray-200 bg-gray-50'
          }`}
        >
          <h2 className={`text-xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>
            {blueprint.algorithmName} — Algorithm Builder
          </h2>
          <p className={`text-sm mt-1 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
            {blueprint.algorithmDescription}
          </p>
        </div>

        <div className="p-6">
          <div className={`p-5 rounded-lg mb-6 ${isDark ? 'bg-gray-800' : 'bg-gray-100'}`}>
            <h3 className={`font-semibold mb-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>
              Your Task
            </h3>
            <p className={`text-sm ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
              {blueprint.problemDescription}
            </p>
            <div className="flex flex-wrap gap-2 mt-3">
              <span
                className={`text-xs px-2 py-1 rounded-full ${
                  isDark ? 'bg-gray-700 text-gray-300' : 'bg-gray-200 text-gray-600'
                }`}
              >
                {blueprint.correct_order.length} correct blocks
              </span>
              <span
                className={`text-xs px-2 py-1 rounded-full ${
                  isDark ? 'bg-gray-700 text-gray-300' : 'bg-gray-200 text-gray-600'
                }`}
              >
                {blueprint.distractors.length} distractor
                {blueprint.distractors.length !== 1 ? 's' : ''}
              </span>
              <span
                className={`text-xs px-2 py-1 rounded-full ${
                  isDark ? 'bg-blue-900/30 text-blue-400' : 'bg-blue-100 text-blue-700'
                }`}
              >
                {blueprint.language}
              </span>
              {blueprint.config.indentation_matters && (
                <span
                  className={`text-xs px-2 py-1 rounded-full ${
                    isDark
                      ? 'bg-purple-900/30 text-purple-400'
                      : 'bg-purple-100 text-purple-700'
                  }`}
                >
                  Indentation matters
                </span>
              )}
            </div>
          </div>

          <div className="text-center">
            <motion.button
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={startBuilding}
              className="px-8 py-3 bg-primary-500 text-white rounded-lg hover:bg-primary-600 transition-colors font-medium text-lg"
            >
              Start Building
            </motion.button>
          </div>
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

          <h2
            className={`text-3xl font-bold mb-2 ${isDark ? 'text-white' : 'text-gray-900'}`}
          >
            Algorithm Built!
          </h2>
          <p className={`text-lg mb-8 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
            {message}
          </p>

          <div className="grid grid-cols-2 md:grid-cols-3 gap-4 mb-8 max-w-lg mx-auto">
            {[
              { label: 'Final Score', value: finalScore, color: 'text-primary-500' },
              {
                label: 'Accuracy',
                value: `${accuracy}%`,
                color: accuracy === 100 ? 'text-green-400' : 'text-yellow-400',
              },
              {
                label: 'Attempts',
                value: state.scoring.attempts,
                color:
                  state.scoring.attempts <= 1 ? 'text-green-400' : 'text-yellow-400',
              },
              { label: 'Hints Used', value: state.scoring.hintsUsed, color: 'text-blue-400' },
              {
                label: 'Blocks Placed',
                value: `${state.solutionBlocks.length}/${blueprint.correct_order.length}`,
                color: 'text-purple-400',
              },
              {
                label: 'Distractors',
                value: `${blueprint.distractors.length} avoided`,
                color: 'text-green-400',
              },
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

          {state.scoring.bonuses.length > 0 && (
            <div className="mb-6 max-w-sm mx-auto">
              {state.scoring.bonuses.map((b) => (
                <div
                  key={b.type}
                  className={`flex justify-between text-sm px-3 py-1 ${
                    isDark ? 'text-yellow-300' : 'text-yellow-700'
                  }`}
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

  // --- BUILDING / FEEDBACK_SHOWN phases ---
  const isFeedbackPhase = state.phase === 'FEEDBACK_SHOWN';
  const maxAttemptsReached =
    blueprint.config.max_attempts != null &&
    state.scoring.attempts >= blueprint.config.max_attempts;

  return (
    <div className={`rounded-xl overflow-hidden ${isDark ? 'bg-gray-900' : 'bg-white'}`}>
      {/* Header */}
      <div
        className={`px-6 py-4 border-b ${
          isDark ? 'border-gray-700 bg-gray-800' : 'border-gray-200 bg-gray-50'
        }`}
      >
        <h2 className={`text-xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>
          {blueprint.algorithmName} — Algorithm Builder
        </h2>
        <p className={`text-sm mt-0.5 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          {blueprint.problemDescription}
        </p>
      </div>

      {/* Score bar */}
      <div
        className={`px-6 py-2 flex items-center gap-4 ${
          isDark ? 'bg-gray-800/50' : 'bg-gray-100'
        }`}
      >
        <div className="flex items-center gap-1.5">
          <span className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
            Score:
          </span>
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
        {state.scoring.attempts > 0 && (
          <span className={`text-xs ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>
            Attempt {state.scoring.attempts}
            {blueprint.config.max_attempts
              ? ` / ${blueprint.config.max_attempts}`
              : ''}
          </span>
        )}
        <span
          className={`text-xs ml-auto px-2 py-0.5 rounded-full ${
            isDark ? 'bg-blue-900/30 text-blue-400' : 'bg-blue-100 text-blue-700'
          }`}
        >
          {blueprint.language}
        </span>
      </div>

      {/* Feedback message */}
      <AnimatePresence>
        {state.feedbackMessage && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className={`px-6 py-3 text-sm ${
              state.feedbackType === 'success'
                ? isDark
                  ? 'bg-green-900/20 text-green-300'
                  : 'bg-green-50 text-green-700'
                : state.feedbackType === 'error'
                  ? isDark
                    ? 'bg-red-900/20 text-red-300'
                    : 'bg-red-50 text-red-700'
                  : isDark
                    ? 'bg-blue-900/20 text-blue-300'
                    : 'bg-blue-50 text-blue-700'
            }`}
          >
            {state.feedbackMessage}
          </motion.div>
        )}
      </AnimatePresence>

      {/* Main content */}
      <div className="p-6">
        <DndContext
          sensors={sensors}
          collisionDetection={closestCenter}
          onDragStart={handleDragStart}
          onDragEnd={handleDragEnd}
        >
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Source panel (left) */}
            <SourcePanel
              blocks={state.sourceBlocks}
              feedback={isFeedbackPhase ? state.scoring.perBlockFeedback : []}
              disabled={isFeedbackPhase}
              theme={theme}
            />

            {/* Solution panel (right) */}
            <SolutionPanel
              blocks={state.solutionBlocks}
              totalCorrectBlocks={blueprint.correct_order.length}
              config={blueprint.config}
              feedback={isFeedbackPhase ? state.scoring.perBlockFeedback : []}
              onIndentChange={handleIndentChange}
              disabled={isFeedbackPhase}
              theme={theme}
            />
          </div>

          {/* Drag overlay */}
          <DragOverlay>
            {activeBlock ? (
              <div
                className={`px-3 py-2 rounded-lg border-2 font-mono text-sm shadow-xl ${
                  isDark
                    ? 'border-primary-500 bg-gray-800 text-gray-200'
                    : 'border-primary-500 bg-white text-gray-800'
                }`}
                style={{ paddingLeft: `${activeBlock.indent_level * 24 + 12}px` }}
              >
                {activeBlock.code}
              </div>
            ) : null}
          </DragOverlay>
        </DndContext>

        {/* Action buttons + hints */}
        <div className="mt-6 flex flex-col lg:flex-row items-start lg:items-end justify-between gap-4">
          <div className="flex-1">
            {!isFeedbackPhase && (
              <HintSystem
                hints={blueprint.hints}
                currentTier={state.hintTier}
                onRequestHint={useHint}
                theme={theme}
                hintPenalties={hintPenalties}
              />
            )}

            {/* Distractor explanations in feedback phase */}
            {isFeedbackPhase && (
              <div className="space-y-1">
                {state.scoring.perBlockFeedback
                  .filter((f) => f.status === 'distractor_included')
                  .map((f) => {
                    const block = state.solutionBlocks.find((b) => b.id === f.blockId);
                    return block?.distractor_explanation ? (
                      <div
                        key={f.blockId}
                        className={`text-xs p-2 rounded ${
                          isDark
                            ? 'bg-red-900/20 text-red-300'
                            : 'bg-red-50 text-red-700'
                        }`}
                      >
                        <span className="font-mono">{block.code}</span>:{' '}
                        {block.distractor_explanation}
                      </div>
                    ) : null;
                  })}
              </div>
            )}
          </div>

          <div className="flex gap-3 shrink-0">
            {isFeedbackPhase && !maxAttemptsReached && (
              <motion.button
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                onClick={retry}
                className={`px-6 py-2.5 rounded-lg font-medium text-sm transition-colors ${
                  isDark
                    ? 'bg-gray-700 text-gray-200 hover:bg-gray-600'
                    : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                }`}
              >
                Try Again
              </motion.button>
            )}

            {!isFeedbackPhase && (
              <motion.button
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                onClick={handleSubmit}
                disabled={state.solutionBlocks.length === 0}
                className={`px-6 py-2.5 rounded-lg font-medium text-sm transition-colors ${
                  state.solutionBlocks.length === 0
                    ? 'bg-gray-600 text-gray-400 cursor-not-allowed'
                    : 'bg-primary-500 text-white hover:bg-primary-600'
                }`}
              >
                Submit Solution
              </motion.button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
