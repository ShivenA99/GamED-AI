'use client';

import { useSortable } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { ParsonsBlock, BlockFeedbackStatus } from '../types';
import IndentControls from './IndentControls';

interface SortableCodeBlockProps {
  block: ParsonsBlock;
  feedbackStatus?: BlockFeedbackStatus;
  showIndentControls?: boolean;
  onIndentChange?: (blockId: string, indent: number) => void;
  lineNumber?: number;
  disabled?: boolean;
  theme?: 'dark' | 'light';
}

const STATUS_STYLES: Record<
  BlockFeedbackStatus,
  { dark: string; light: string; icon: string }
> = {
  correct: {
    dark: 'border-green-500/60 bg-green-900/20',
    light: 'border-green-500 bg-green-50',
    icon: '\u2713',
  },
  wrong_position: {
    dark: 'border-orange-500/60 bg-orange-900/20',
    light: 'border-orange-500 bg-orange-50',
    icon: '\u2195',
  },
  wrong_indent: {
    dark: 'border-yellow-500/60 bg-yellow-900/20',
    light: 'border-yellow-500 bg-yellow-50',
    icon: '\u2194',
  },
  distractor_included: {
    dark: 'border-red-500/60 bg-red-900/20',
    light: 'border-red-500 bg-red-50',
    icon: '\u2717',
  },
  distractor_excluded: {
    dark: 'border-green-500/40 bg-green-900/10',
    light: 'border-green-400 bg-green-50/50',
    icon: '\u2713',
  },
  missing: {
    dark: 'border-red-400/40 bg-red-900/10',
    light: 'border-red-400 bg-red-50/50',
    icon: '!',
  },
  neutral: {
    dark: 'border-gray-600 bg-gray-800',
    light: 'border-gray-300 bg-white',
    icon: '',
  },
};

export default function SortableCodeBlock({
  block,
  feedbackStatus = 'neutral',
  showIndentControls = false,
  onIndentChange,
  lineNumber,
  disabled = false,
  theme = 'dark',
}: SortableCodeBlockProps) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } =
    useSortable({ id: block.id, disabled });

  const isDark = theme === 'dark';
  const styles = STATUS_STYLES[feedbackStatus];

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    zIndex: isDragging ? 50 : 0,
    paddingLeft: `${block.indent_level * 24 + 12}px`,
  };

  return (
    <div
      ref={setNodeRef}
      style={style}
      {...attributes}
      {...listeners}
      className={`
        flex items-center gap-2 pr-3 py-2 rounded-lg border-2
        font-mono text-sm select-none touch-none
        transition-shadow
        ${isDragging ? 'shadow-xl opacity-70' : 'shadow-sm'}
        ${isDark ? styles.dark : styles.light}
        ${disabled ? 'cursor-default opacity-70' : 'cursor-grab active:cursor-grabbing'}
      `}
      title={
        feedbackStatus === 'distractor_included' && block.distractor_explanation
          ? block.distractor_explanation
          : feedbackStatus === 'wrong_indent'
            ? `Incorrect indentation — try adjusting`
            : undefined
      }
    >
      {/* Line number */}
      {lineNumber != null && (
        <span
          className={`text-xs w-5 text-right shrink-0 ${
            isDark ? 'text-gray-500' : 'text-gray-400'
          }`}
        >
          {lineNumber}
        </span>
      )}

      {/* Code text */}
      <span className={`flex-1 whitespace-pre ${isDark ? 'text-gray-200' : 'text-gray-800'}`}>
        {block.code}
      </span>

      {/* Feedback icon */}
      {feedbackStatus !== 'neutral' && styles.icon && (
        <span
          className={`text-sm shrink-0 font-bold ${
            feedbackStatus === 'correct' || feedbackStatus === 'distractor_excluded'
              ? 'text-green-500'
              : feedbackStatus === 'wrong_position'
                ? 'text-orange-500'
                : feedbackStatus === 'wrong_indent'
                  ? 'text-yellow-500'
                  : 'text-red-500'
          }`}
        >
          {styles.icon}
        </span>
      )}

      {/* Indent controls */}
      {showIndentControls && onIndentChange && !disabled && (
        <IndentControls
          indentLevel={block.indent_level}
          onChange={(level) => onIndentChange(block.id, level)}
          disabled={disabled}
          theme={theme}
        />
      )}
    </div>
  );
}
