'use client';

import { useDroppable } from '@dnd-kit/core';
import { SortableContext, verticalListSortingStrategy } from '@dnd-kit/sortable';
import { ParsonsBlock, BlockFeedback, AlgorithmBuilderConfig } from '../types';
import SortableCodeBlock from './SortableCodeBlock';

interface SolutionPanelProps {
  blocks: ParsonsBlock[];
  totalCorrectBlocks: number;
  config: AlgorithmBuilderConfig;
  feedback?: BlockFeedback[];
  onIndentChange?: (blockId: string, indent: number) => void;
  disabled?: boolean;
  theme?: 'dark' | 'light';
}

export default function SolutionPanel({
  blocks,
  totalCorrectBlocks,
  config,
  feedback = [],
  onIndentChange,
  disabled = false,
  theme = 'dark',
}: SolutionPanelProps) {
  const isDark = theme === 'dark';
  const { setNodeRef, isOver } = useDroppable({ id: 'solution' });

  const getFeedbackStatus = (blockId: string) => {
    const fb = feedback.find((f) => f.blockId === blockId);
    return fb?.status ?? 'neutral';
  };

  return (
    <div
      className={`rounded-xl border-2 transition-colors ${
        isOver
          ? isDark
            ? 'border-primary-500/50 bg-primary-900/10'
            : 'border-primary-400 bg-primary-50/50'
          : isDark
            ? 'border-gray-700 bg-gray-900'
            : 'border-gray-200 bg-gray-50'
      }`}
    >
      <div
        className={`px-4 py-3 border-b flex items-center justify-between ${
          isDark ? 'border-gray-700' : 'border-gray-200'
        }`}
      >
        <h3 className={`font-semibold text-sm ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>
          Your Solution ({blocks.length}/{totalCorrectBlocks})
        </h3>
        {config.indentation_matters && (
          <span
            className={`text-xs px-2 py-0.5 rounded-full ${
              isDark ? 'bg-blue-900/30 text-blue-400' : 'bg-blue-100 text-blue-700'
            }`}
          >
            Indentation matters
          </span>
        )}
      </div>

      <div ref={setNodeRef} className="p-3 min-h-[200px]">
        <SortableContext
          items={blocks.map((b) => b.id)}
          strategy={verticalListSortingStrategy}
          disabled={disabled}
        >
          <div className="space-y-2">
            {blocks.map((block, i) => (
              <SortableCodeBlock
                key={block.id}
                block={block}
                feedbackStatus={getFeedbackStatus(block.id)}
                showIndentControls={config.allow_indent_adjustment}
                onIndentChange={onIndentChange}
                lineNumber={config.show_line_numbers ? i + 1 : undefined}
                disabled={disabled}
                theme={theme}
              />
            ))}
          </div>
        </SortableContext>

        {blocks.length === 0 && (
          <div
            className={`border-2 border-dashed rounded-lg py-12 text-center ${
              isDark ? 'border-gray-700 text-gray-600' : 'border-gray-300 text-gray-400'
            }`}
          >
            <p className="text-sm">Drag blocks here to build your solution</p>
            <p className="text-xs mt-1 opacity-60">Arrange them in the correct order</p>
          </div>
        )}
      </div>
    </div>
  );
}
