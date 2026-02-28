'use client';

import { useState, useCallback } from 'react';
import { InteractionMode, ModeTransition, MultiModeState } from '../types';

// Mode display names and icons
const MODE_INFO: Record<InteractionMode, { name: string; icon: string; description: string }> = {
  drag_drop: {
    name: 'Drag & Drop',
    icon: '🎯',
    description: 'Drag labels to their correct positions',
  },
  click_to_identify: {
    name: 'Click to Identify',
    icon: '👆',
    description: 'Click on parts when prompted',
  },
  trace_path: {
    name: 'Trace Path',
    icon: '🔗',
    description: 'Trace the path through connected parts',
  },
  hierarchical: {
    name: 'Hierarchical',
    icon: '📊',
    description: 'Explore nested structures level by level',
  },
  description_matching: {
    name: 'Match Descriptions',
    icon: '📝',
    description: 'Match descriptions to diagram parts',
  },
  compare_contrast: {
    name: 'Compare & Contrast',
    icon: '⚖️',
    description: 'Find similarities and differences',
  },
  sequencing: {
    name: 'Sequencing',
    icon: '🔢',
    description: 'Arrange items in the correct order',
  },
  timed_challenge: {
    name: 'Timed Challenge',
    icon: '⏱️',
    description: 'Complete the task before time runs out',
  },
  sorting_categories: {
    name: 'Sorting Categories',
    icon: '📦',
    description: 'Sort items into the correct categories',
  },
  memory_match: {
    name: 'Memory Match',
    icon: '🃏',
    description: 'Match pairs by flipping cards',
  },
  branching_scenario: {
    name: 'Branching Scenario',
    icon: '🔀',
    description: 'Navigate through decision points',
  },
};

export interface ModeIndicatorProps {
  currentMode: InteractionMode;
  multiModeState?: MultiModeState | null;
  onModeSwitch?: (mode: InteractionMode) => void;
  allowManualSwitch?: boolean;
  showProgress?: boolean;
  pendingTransition?: ModeTransition;
  position?: 'top-left' | 'top-right' | 'bottom-left' | 'bottom-right' | 'inline';
}

/**
 * Mode indicator component that shows current interaction mode
 * and optionally allows switching between available modes
 */
export function ModeIndicator({
  currentMode,
  multiModeState,
  onModeSwitch,
  allowManualSwitch = false,
  showProgress = true,
  pendingTransition,
  position = 'top-right',
}: ModeIndicatorProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const modeInfo = MODE_INFO[currentMode];

  const handleModeClick = useCallback((mode: InteractionMode) => {
    if (onModeSwitch && mode !== currentMode) {
      onModeSwitch(mode);
      setIsExpanded(false);
    }
  }, [currentMode, onModeSwitch]);

  const positionClasses: Record<string, string> = {
    'top-left': 'absolute top-4 left-4',
    'top-right': 'absolute top-4 right-4',
    'bottom-left': 'absolute bottom-4 left-4',
    'bottom-right': 'absolute bottom-4 right-4',
    'inline': 'relative',
  };

  // Progress through modes
  const completedCount = multiModeState?.completedModes.length || 0;
  const totalModes = multiModeState?.availableModes.length || 1;

  return (
    <div className={`${positionClasses[position]} z-20`}>
      {/* Pending transition notification */}
      {pendingTransition && (
        <div className="absolute -top-16 left-0 right-0 bg-blue-100 dark:bg-blue-900 border border-blue-300 dark:border-blue-700 rounded-lg p-3 shadow-lg animate-pulse">
          <p className="text-sm text-blue-800 dark:text-blue-200 text-center">
            {pendingTransition.message || `Transitioning to ${MODE_INFO[pendingTransition.to]?.name || pendingTransition.to}...`}
          </p>
        </div>
      )}

      {/* Current mode badge */}
      <div
        className={`
          flex items-center gap-2 px-3 py-2 rounded-lg shadow-md
          bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700
          ${allowManualSwitch && multiModeState && multiModeState.availableModes.length > 1 ? 'cursor-pointer hover:shadow-lg transition-shadow' : ''}
        `}
        onClick={() => allowManualSwitch && setIsExpanded(!isExpanded)}
        role={allowManualSwitch ? 'button' : undefined}
        aria-expanded={isExpanded}
        aria-haspopup={allowManualSwitch}
      >
        <span className="text-xl" aria-hidden="true">{modeInfo.icon}</span>
        <div>
          <div className="text-sm font-medium text-gray-800 dark:text-gray-200">
            {modeInfo.name}
          </div>
          {showProgress && multiModeState && totalModes > 1 && (
            <div className="text-xs text-gray-500 dark:text-gray-400">
              Mode {completedCount + 1} of {totalModes}
            </div>
          )}
        </div>
        {allowManualSwitch && multiModeState && multiModeState.availableModes.length > 1 && (
          <span className="ml-2 text-gray-400">
            {isExpanded ? '▲' : '▼'}
          </span>
        )}
      </div>

      {/* Mode selector dropdown */}
      {isExpanded && allowManualSwitch && multiModeState && (
        <div className="absolute top-full mt-2 w-64 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-xl overflow-hidden">
          {multiModeState.availableModes.map((mode) => {
            const info = MODE_INFO[mode];
            const isActive = mode === currentMode;
            const isCompleted = multiModeState.completedModes.includes(mode);

            return (
              <button
                key={mode}
                onClick={() => handleModeClick(mode)}
                disabled={isActive}
                className={`
                  w-full flex items-center gap-3 px-4 py-3 text-left
                  transition-colors
                  ${isActive
                    ? 'bg-blue-50 dark:bg-blue-900/30 text-blue-800 dark:text-blue-200 cursor-default'
                    : 'hover:bg-gray-50 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-300'
                  }
                  ${isCompleted ? 'border-l-4 border-green-500' : ''}
                `}
              >
                <span className="text-xl" aria-hidden="true">{info.icon}</span>
                <div className="flex-1">
                  <div className="font-medium">{info.name}</div>
                  <div className="text-xs text-gray-500 dark:text-gray-400">
                    {info.description}
                  </div>
                </div>
                {isCompleted && (
                  <span className="text-green-500" aria-label="Completed">✓</span>
                )}
                {isActive && (
                  <span className="text-blue-500 text-xs font-medium">Active</span>
                )}
              </button>
            );
          })}
        </div>
      )}

      {/* Mode progress dots (when not expanded) */}
      {!isExpanded && showProgress && multiModeState && totalModes > 1 && (
        <div className="flex justify-center gap-1 mt-2">
          {multiModeState.availableModes.map((mode, index) => {
            const isActive = mode === currentMode;
            const isCompleted = multiModeState.completedModes.includes(mode);

            return (
              <div
                key={mode}
                className={`
                  w-2 h-2 rounded-full transition-all
                  ${isActive ? 'w-4 bg-blue-500' : ''}
                  ${isCompleted && !isActive ? 'bg-green-500' : ''}
                  ${!isActive && !isCompleted ? 'bg-gray-300 dark:bg-gray-600' : ''}
                `}
                title={MODE_INFO[mode].name}
              />
            );
          })}
        </div>
      )}
    </div>
  );
}

/**
 * Compact mode badge for inline display
 */
export function ModeBadge({ mode }: { mode: InteractionMode }) {
  const info = MODE_INFO[mode];

  return (
    <span className="inline-flex items-center gap-1 px-2 py-1 text-xs font-medium rounded-full bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300">
      <span aria-hidden="true">{info.icon}</span>
      {info.name}
    </span>
  );
}

export default ModeIndicator;
