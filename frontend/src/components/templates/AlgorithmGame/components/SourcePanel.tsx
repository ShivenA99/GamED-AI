'use client';

import { useDroppable } from '@dnd-kit/core';
import { SortableContext, verticalListSortingStrategy } from '@dnd-kit/sortable';
import { ParsonsBlock, BlockFeedback } from '../types';
import SortableCodeBlock from './SortableCodeBlock';

interface SourcePanelProps {
  blocks: ParsonsBlock[];
  feedback?: BlockFeedback[];
  disabled?: boolean;
  theme?: 'dark' | 'light';
}

export default function SourcePanel({
  blocks,
  feedback = [],
  disabled = false,
  theme = 'dark',
}: SourcePanelProps) {
  const isDark = theme === 'dark';
  const { setNodeRef, isOver } = useDroppable({ id: 'source' });

  const getFeedbackStatus = (blockId: string) => {
    const fb = feedback.find((f) => f.blockId === blockId);
    return fb?.status ?? 'neutral';
  };

  return (
    <div
      className={`rounded-xl border-2 transition-colors ${
        isOver
          ? isDark
            ? 'border-blue-500/50 bg-blue-900/10'
            : 'border-blue-400 bg-blue-50/50'
          : isDark
            ? 'border-gray-700 bg-gray-900'
            : 'border-gray-200 bg-gray-50'
      }`}
    >
      <div className={`px-4 py-3 border-b ${isDark ? 'border-gray-700' : 'border-gray-200'}`}>
        <h3 className={`font-semibold text-sm ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>
          Available Blocks ({blocks.length})
        </h3>
      </div>

      <div ref={setNodeRef} className="p-3 min-h-[120px]">
        <SortableContext
          items={blocks.map((b) => b.id)}
          strategy={verticalListSortingStrategy}
          disabled={disabled}
        >
          <div className="space-y-2">
            {blocks.map((block) => (
              <SortableCodeBlock
                key={block.id}
                block={block}
                feedbackStatus={getFeedbackStatus(block.id)}
                disabled={disabled}
                theme={theme}
              />
            ))}
          </div>
        </SortableContext>

        {blocks.length === 0 && (
          <div className={`text-center py-8 text-sm ${isDark ? 'text-gray-600' : 'text-gray-400'}`}>
            All blocks placed in solution
          </div>
        )}
      </div>
    </div>
  );
}
