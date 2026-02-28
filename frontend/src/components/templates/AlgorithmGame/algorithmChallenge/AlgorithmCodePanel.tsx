'use client';

import { useCallback, useMemo } from 'react';
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
import { motion } from 'framer-motion';
import SourcePanel from '../components/SourcePanel';
import SolutionPanel from '../components/SolutionPanel';
import HintSystem from '../components/HintSystem';
import CodeEditorPanel from './CodeEditorPanel';
import { ChallengeMode, CodeSideState } from './combinedPuzzleTypes';
import { AlgorithmBuilderBlueprint, AlgorithmBuilderGameState } from '../types';

interface AlgorithmCodePanelProps {
  challengeMode: ChallengeMode;
  codeSide: CodeSideState;
  parsonsState: AlgorithmBuilderGameState;
  parsonsBlueprint: AlgorithmBuilderBlueprint;
  onActiveTabChange: (tab: 'parsons' | 'free_code') => void;
  onFreeCodeChange: (code: string) => void;
  onRunCode: () => void;
  onSubmitCode: () => void;
  onHint: (tier: number) => void;
  // Parsons DnD actions
  onMoveToSolution: (blockId: string, index: number) => void;
  onMoveToSource: (blockId: string) => void;
  onReorderSolution: (activeId: string, overId: string) => void;
  onSetIndent: (blockId: string, indent: number) => void;
  onSetActiveBlock: (id: string | null) => void;
  hints: [string, string, string];
  theme?: 'dark' | 'light';
}

export default function AlgorithmCodePanel({
  challengeMode,
  codeSide,
  parsonsState,
  parsonsBlueprint,
  onActiveTabChange,
  onFreeCodeChange,
  onRunCode,
  onSubmitCode,
  onHint,
  onMoveToSolution,
  onMoveToSource,
  onReorderSolution,
  onSetIndent,
  onSetActiveBlock,
  hints,
  theme = 'dark',
}: AlgorithmCodePanelProps) {
  const isDark = theme === 'dark';
  const showTabs = challengeMode === 'both';
  const isSubmitted = codeSide.phase === 'SUBMITTED';

  // DnD sensors
  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 5 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }),
  );

  const findContainer = useCallback(
    (id: string): 'source' | 'solution' | null => {
      if (id === 'source' || id === 'solution') return id as 'source' | 'solution';
      if (parsonsState.sourceBlocks.find((b) => b.id === id)) return 'source';
      if (parsonsState.solutionBlocks.find((b) => b.id === id)) return 'solution';
      return null;
    },
    [parsonsState.sourceBlocks, parsonsState.solutionBlocks],
  );

  const activeBlock = useMemo(() => {
    if (!parsonsState.activeBlockId) return null;
    return (
      parsonsState.sourceBlocks.find((b) => b.id === parsonsState.activeBlockId) ??
      parsonsState.solutionBlocks.find((b) => b.id === parsonsState.activeBlockId) ??
      null
    );
  }, [parsonsState.activeBlockId, parsonsState.sourceBlocks, parsonsState.solutionBlocks]);

  const handleDragStart = useCallback(
    (e: DragStartEvent) => onSetActiveBlock(String(e.active.id)),
    [onSetActiveBlock],
  );

  const handleDragEnd = useCallback(
    (e: DragEndEvent) => {
      const { active, over } = e;
      onSetActiveBlock(null);
      if (!over) return;

      const activeId = String(active.id);
      const overId = String(over.id);
      const from = findContainer(activeId);
      const to = findContainer(overId);
      if (!from || !to) return;

      if (from === to) {
        if (from === 'solution' && activeId !== overId) {
          onReorderSolution(activeId, overId);
        }
      } else if (from === 'source' && to === 'solution') {
        const idx =
          overId === 'solution'
            ? parsonsState.solutionBlocks.length
            : parsonsState.solutionBlocks.findIndex((b) => b.id === overId);
        onMoveToSolution(activeId, idx >= 0 ? idx : parsonsState.solutionBlocks.length);
      } else if (from === 'solution' && to === 'source') {
        onMoveToSource(activeId);
      }
    },
    [findContainer, parsonsState.solutionBlocks, onMoveToSolution, onMoveToSource, onReorderSolution, onSetActiveBlock],
  );

  return (
    <div className={`rounded-xl border ${isDark ? 'border-gray-700 bg-gray-900' : 'border-gray-200 bg-white'}`}>
      {/* Header + Tabs */}
      <div className={`px-4 py-3 border-b flex items-center gap-3 ${isDark ? 'border-gray-700' : 'border-gray-200'}`}>
        <span className={`text-sm font-semibold ${isDark ? 'text-gray-200' : 'text-gray-800'}`}>
          Algorithm Code
        </span>

        {showTabs && (
          <div className="flex gap-1 ml-auto">
            {(['parsons', 'free_code'] as const).map((tab) => (
              <button
                key={tab}
                onClick={() => onActiveTabChange(tab)}
                disabled={isSubmitted}
                className={`px-3 py-1 text-xs rounded-md font-medium transition-colors ${
                  codeSide.activeTab === tab
                    ? 'bg-blue-600 text-white'
                    : isDark
                      ? 'bg-gray-800 text-gray-400 hover:text-gray-200'
                      : 'bg-gray-100 text-gray-500 hover:text-gray-700'
                }`}
              >
                {tab === 'parsons' ? 'Parsons' : 'Free Code'}
              </button>
            ))}
          </div>
        )}

        {isSubmitted && (
          <span className="ml-auto text-xs px-2 py-0.5 rounded-full bg-green-600/20 text-green-400 font-medium">
            Submitted
          </span>
        )}
      </div>

      {/* Content */}
      <div className="p-4 space-y-4">
        {codeSide.activeTab === 'parsons' ? (
          <DndContext
            sensors={sensors}
            collisionDetection={closestCenter}
            onDragStart={handleDragStart}
            onDragEnd={handleDragEnd}
          >
            <div className="grid grid-cols-1 gap-4">
              <SourcePanel
                blocks={parsonsState.sourceBlocks}
                feedback={[]}
                disabled={isSubmitted}
                theme={theme}
              />
              <SolutionPanel
                blocks={parsonsState.solutionBlocks}
                totalCorrectBlocks={parsonsBlueprint.correct_order.length}
                config={parsonsBlueprint.config}
                feedback={[]}
                onIndentChange={onSetIndent}
                disabled={isSubmitted}
                theme={theme}
              />
            </div>
            <DragOverlay>
              {activeBlock ? (
                <div
                  className={`px-3 py-2 rounded-lg border-2 font-mono text-sm shadow-xl ${
                    isDark
                      ? 'border-blue-500 bg-gray-800 text-gray-200'
                      : 'border-blue-500 bg-white text-gray-800'
                  }`}
                  style={{ paddingLeft: `${activeBlock.indent_level * 24 + 12}px` }}
                >
                  {activeBlock.code}
                </div>
              ) : null}
            </DragOverlay>
          </DndContext>
        ) : (
          <CodeEditorPanel
            value={codeSide.freeCodeValue}
            onChange={onFreeCodeChange}
            disabled={isSubmitted}
            theme={theme}
            height="280px"
          />
        )}

        {/* Error message */}
        {codeSide.errorMessage && (
          <div className={`text-xs px-3 py-2 rounded-lg ${isDark ? 'bg-red-900/20 text-red-300' : 'bg-red-50 text-red-600'}`}>
            {codeSide.errorMessage}
          </div>
        )}

        {/* Hints + Actions */}
        <div className="flex items-end justify-between gap-3">
          <HintSystem
            hints={hints}
            currentTier={codeSide.hintTier}
            onRequestHint={onHint}
            theme={theme}
          />

          <div className="flex gap-2 shrink-0">
            <motion.button
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={onRunCode}
              disabled={isSubmitted || codeSide.phase === 'RUNNING'}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                isSubmitted || codeSide.phase === 'RUNNING'
                  ? 'bg-gray-700 text-gray-500 cursor-not-allowed'
                  : 'bg-green-600 text-white hover:bg-green-500'
              }`}
            >
              {codeSide.phase === 'RUNNING'
                ? codeSide.pyodideLoading
                  ? 'Loading Python...'
                  : 'Running...'
                : 'Run Code'}
            </motion.button>

            {codeSide.testResults.length > 0 && !isSubmitted && (
              <motion.button
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                onClick={onSubmitCode}
                className="px-4 py-2 rounded-lg text-sm font-medium bg-blue-600 text-white hover:bg-blue-500 transition-colors"
              >
                Submit Code
              </motion.button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
