'use client';

import React, { useCallback, useEffect, useState } from 'react';
import { useCommandHistory, CommandHistoryState } from '../hooks';

/**
 * Props for UndoRedoControls component
 */
export interface UndoRedoControlsProps {
  /** Show tooltips on hover (default: true) */
  showTooltips?: boolean;
  /** Show keyboard shortcuts in tooltips (default: true) */
  showKeyboardHints?: boolean;
  /** Position style */
  position?: 'inline' | 'floating' | 'compact';
  /** Custom class name */
  className?: string;
  /** Callback when undo is performed */
  onUndo?: () => void;
  /** Callback when redo is performed */
  onRedo?: () => void;
  /** Disabled state */
  disabled?: boolean;
}

/**
 * UndoRedoControls - Visual controls for undo/redo functionality
 *
 * Provides:
 * - Undo/redo buttons with visual feedback
 * - Keyboard shortcut hints
 * - Tooltips showing action descriptions
 * - Disabled state when no actions available
 */
export function UndoRedoControls({
  showTooltips = true,
  showKeyboardHints = true,
  position = 'inline',
  className = '',
  onUndo,
  onRedo,
  disabled = false,
}: UndoRedoControlsProps) {
  const { undo, redo, canUndo, canRedo, historyState } = useCommandHistory();
  const [showUndoTooltip, setShowUndoTooltip] = useState(false);
  const [showRedoTooltip, setShowRedoTooltip] = useState(false);

  // Detect platform for keyboard shortcuts
  const isMac = typeof navigator !== 'undefined' && navigator.platform.toUpperCase().indexOf('MAC') >= 0;
  const undoShortcut = isMac ? '⌘Z' : 'Ctrl+Z';
  const redoShortcut = isMac ? '⌘⇧Z' : 'Ctrl+Y';

  const handleUndo = useCallback(() => {
    if (disabled || !canUndo) return;
    const command = undo();
    if (command) {
      onUndo?.();
    }
  }, [undo, canUndo, disabled, onUndo]);

  const handleRedo = useCallback(() => {
    if (disabled || !canRedo) return;
    const command = redo();
    if (command) {
      onRedo?.();
    }
  }, [redo, canRedo, disabled, onRedo]);

  // Position-specific styles
  const positionStyles: Record<string, string> = {
    inline: 'flex items-center gap-1',
    floating: 'fixed bottom-4 right-4 flex items-center gap-2 bg-white rounded-lg shadow-lg p-2',
    compact: 'flex items-center gap-0.5',
  };

  // Button size based on position
  const buttonStyles: Record<string, string> = {
    inline: 'p-2 rounded-lg',
    floating: 'p-3 rounded-lg',
    compact: 'p-1.5 rounded',
  };

  const iconSize: Record<string, string> = {
    inline: 'w-5 h-5',
    floating: 'w-6 h-6',
    compact: 'w-4 h-4',
  };

  return (
    <div
      className={`${positionStyles[position]} ${className}`}
      role="toolbar"
      aria-label="Undo and redo controls"
    >
      {/* Undo button */}
      <div className="relative">
        <button
          onClick={handleUndo}
          disabled={disabled || !canUndo}
          onMouseEnter={() => setShowUndoTooltip(true)}
          onMouseLeave={() => setShowUndoTooltip(false)}
          className={`
            ${buttonStyles[position]}
            transition-all duration-150
            ${
              canUndo && !disabled
                ? 'text-gray-700 hover:bg-gray-100 hover:text-blue-600 active:scale-95'
                : 'text-gray-300 cursor-not-allowed'
            }
          `}
          aria-label={`Undo${historyState.undoDescription ? `: ${historyState.undoDescription}` : ''}`}
          title={showTooltips ? undefined : `Undo (${undoShortcut})`}
        >
          {/* Undo icon (curved arrow left) */}
          <svg
            className={iconSize[position]}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
            aria-hidden="true"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M3 10h10a8 8 0 018 8v2M3 10l6 6m-6-6l6-6"
            />
          </svg>
        </button>

        {/* Undo tooltip */}
        {showTooltips && showUndoTooltip && canUndo && (
          <div
            className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-3 py-1.5 bg-gray-900 text-white text-xs rounded-lg whitespace-nowrap z-50"
            role="tooltip"
          >
            <div className="font-medium">
              Undo{historyState.undoDescription ? `: ${historyState.undoDescription}` : ''}
            </div>
            {showKeyboardHints && (
              <div className="text-gray-400 text-xs mt-0.5">{undoShortcut}</div>
            )}
            {/* Tooltip arrow */}
            <div className="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-gray-900" />
          </div>
        )}
      </div>

      {/* Redo button */}
      <div className="relative">
        <button
          onClick={handleRedo}
          disabled={disabled || !canRedo}
          onMouseEnter={() => setShowRedoTooltip(true)}
          onMouseLeave={() => setShowRedoTooltip(false)}
          className={`
            ${buttonStyles[position]}
            transition-all duration-150
            ${
              canRedo && !disabled
                ? 'text-gray-700 hover:bg-gray-100 hover:text-blue-600 active:scale-95'
                : 'text-gray-300 cursor-not-allowed'
            }
          `}
          aria-label={`Redo${historyState.redoDescription ? `: ${historyState.redoDescription}` : ''}`}
          title={showTooltips ? undefined : `Redo (${redoShortcut})`}
        >
          {/* Redo icon (curved arrow right) */}
          <svg
            className={iconSize[position]}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
            aria-hidden="true"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M21 10h-10a8 8 0 00-8 8v2M21 10l-6 6m6-6l-6-6"
            />
          </svg>
        </button>

        {/* Redo tooltip */}
        {showTooltips && showRedoTooltip && canRedo && (
          <div
            className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-3 py-1.5 bg-gray-900 text-white text-xs rounded-lg whitespace-nowrap z-50"
            role="tooltip"
          >
            <div className="font-medium">
              Redo{historyState.redoDescription ? `: ${historyState.redoDescription}` : ''}
            </div>
            {showKeyboardHints && (
              <div className="text-gray-400 text-xs mt-0.5">{redoShortcut}</div>
            )}
            {/* Tooltip arrow */}
            <div className="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-gray-900" />
          </div>
        )}
      </div>

      {/* History indicator (optional for floating mode) */}
      {position === 'floating' && historyState.historyLength > 0 && (
        <div className="ml-2 text-xs text-gray-500">
          {historyState.historyLength} action{historyState.historyLength !== 1 ? 's' : ''}
        </div>
      )}
    </div>
  );
}

/**
 * Minimal undo/redo buttons for tight spaces
 */
export function UndoRedoCompact(props: Omit<UndoRedoControlsProps, 'position'>) {
  return <UndoRedoControls {...props} position="compact" showTooltips={false} />;
}

/**
 * Floating undo/redo panel
 */
export function UndoRedoFloating(props: Omit<UndoRedoControlsProps, 'position'>) {
  return <UndoRedoControls {...props} position="floating" />;
}

export default UndoRedoControls;
