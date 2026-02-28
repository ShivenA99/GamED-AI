'use client';

import { useEffect, useRef, useState } from 'react';
import type { SceneTask, TaskResult } from './types';
import type { GameplayMode } from './types';

interface TaskProgressProps {
  tasks: SceneTask[];
  currentTaskIndex: number;
  taskResults: TaskResult[];
}

function TaskProgressBar({ tasks, currentTaskIndex, taskResults }: TaskProgressProps) {
  if (tasks.length <= 1) return null;

  const completedIds = new Set(taskResults.map(r => r.task_id));

  return (
    <div className="flex items-center gap-1 px-3 py-2 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
      {tasks.map((task, idx) => {
        const isCompleted = completedIds.has(task.task_id);
        const isCurrent = idx === currentTaskIndex;
        const isFuture = idx > currentTaskIndex && !isCompleted;

        return (
          <div key={task.task_id} className="flex items-center">
            {idx > 0 && (
              <div className={`w-4 h-0.5 mx-0.5 ${isCompleted || isCurrent ? 'bg-primary-400' : 'bg-gray-300 dark:bg-gray-600'}`} />
            )}
            <div
              className={`
                flex items-center gap-1 px-2 py-1 rounded text-xs font-medium transition-all
                ${isCurrent ? 'bg-primary-100 dark:bg-primary-900/50 text-primary-700 dark:text-primary-300 ring-1 ring-primary-400' : ''}
                ${isCompleted ? 'bg-green-100 dark:bg-green-900/50 text-green-700 dark:text-green-300' : ''}
                ${isFuture ? 'bg-gray-100 dark:bg-gray-600 text-gray-400 dark:text-gray-500' : ''}
              `}
              title={task.title}
            >
              {isCompleted && (
                <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                </svg>
              )}
              <span className="max-w-[100px] truncate">{idx + 1}. {task.title}</span>
            </div>
          </div>
        );
      })}
    </div>
  );
}

function Timer({ running }: { running: boolean }) {
  const [seconds, setSeconds] = useState(0);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (running) {
      intervalRef.current = setInterval(() => setSeconds(s => s + 1), 1000);
    }
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [running]);

  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;

  return (
    <div className="flex items-center gap-1.5 px-3 py-1.5 bg-gray-100 dark:bg-gray-700 rounded-lg text-sm font-mono">
      <svg className="w-4 h-4 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
      <span className="text-gray-700 dark:text-gray-300">
        {mins}:{secs.toString().padStart(2, '0')}
      </span>
    </div>
  );
}

interface GameControlsProps {
  showHints: boolean;
  onToggleHints: () => void;
  onReset: () => void;
  hasHints: boolean;
  score: number;
  maxScore: number;
  /** Multi-scene: total score across all scenes (including current) */
  totalScore?: number;
  /** Multi-scene: total max score across entire game */
  totalMaxScore?: number;
  taskProgress?: TaskProgressProps;
  gameplayMode?: GameplayMode;
}

export default function GameControls({
  showHints,
  onToggleHints,
  onReset,
  hasHints,
  score,
  maxScore,
  totalScore,
  totalMaxScore,
  taskProgress,
  gameplayMode = 'learn',
}: GameControlsProps) {
  const isMultiScene = totalScore !== undefined && totalMaxScore !== undefined;
  const isTestMode = gameplayMode === 'test';

  return (
    <div className="flex flex-col gap-2">
      {/* Task progress bar (only when scene has multiple tasks) */}
      {taskProgress && taskProgress.tasks.length > 1 && (
        <TaskProgressBar {...taskProgress} />
      )}

      <div className="flex items-center justify-between p-4 bg-white dark:bg-gray-800 rounded-lg shadow-sm dark:shadow-gray-900/20">
      <div className="flex items-center gap-4">
        {isMultiScene ? (
          /* Two-tier score display for multi-scene games */
          <div className="flex flex-col gap-1.5">
            {/* Total game score */}
            <div className="flex items-center gap-2">
              <span className="text-xs text-gray-500 dark:text-gray-400 w-12">Total:</span>
              <span className="text-base font-bold text-primary-600 dark:text-primary-400 min-w-[60px]">
                {totalScore} / {totalMaxScore}
              </span>
              <div className="w-28 h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-primary-500 to-secondary-500 transition-all duration-300"
                  style={{ width: `${totalMaxScore! > 0 ? (totalScore! / totalMaxScore!) * 100 : 0}%` }}
                />
              </div>
            </div>
            {/* Current scene score */}
            <div className="flex items-center gap-2">
              <span className="text-xs text-gray-500 dark:text-gray-400 w-12">Scene:</span>
              <span className="text-sm font-semibold text-gray-600 dark:text-gray-300 min-w-[60px]">
                {score} / {maxScore}
              </span>
              <div className="w-28 h-1.5 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-blue-400 to-blue-500 transition-all duration-300"
                  style={{ width: `${maxScore > 0 ? (score / maxScore) * 100 : 0}%` }}
                />
              </div>
            </div>
          </div>
        ) : (
          /* Single-scene score display (unchanged) */
          <>
            <div className="flex items-center gap-2">
              <span className="text-sm text-gray-500 dark:text-gray-400">Score:</span>
              <span className="text-lg font-bold text-primary-600 dark:text-primary-400">
                {score} / {maxScore}
              </span>
            </div>
            <div className="w-32 h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-primary-500 to-secondary-500 transition-all duration-300"
                style={{ width: `${maxScore > 0 ? (score / maxScore) * 100 : 0}%` }}
              />
            </div>
          </>
        )}
      </div>

      <div className="flex items-center gap-2">
        {/* Timer (test mode only) */}
        {isTestMode && <Timer running={true} />}

        {/* Mode badge */}
        <span className={`px-2 py-1 text-xs font-medium rounded-full ${
          isTestMode
            ? 'bg-orange-100 dark:bg-orange-900/30 text-orange-700 dark:text-orange-300'
            : 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300'
        }`}>
          {isTestMode ? 'Test' : 'Learn'}
        </span>

        {/* Hints toggle — learn mode only */}
        {!isTestMode && hasHints && (
          <button
            onClick={onToggleHints}
            className={`
              px-3 py-1.5 rounded-lg text-sm font-medium
              transition-colors duration-200
              flex items-center gap-1.5
              ${
                showHints
                  ? 'bg-yellow-100 dark:bg-yellow-900/50 text-yellow-700 dark:text-yellow-300 hover:bg-yellow-200 dark:hover:bg-yellow-900/70'
                  : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'
              }
            `}
          >
            <svg
              className="w-4 h-4"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"
              />
            </svg>
            {showHints ? 'Hide Hints' : 'Show Hints'}
          </button>
        )}

        {/* Reset button */}
        <button
          onClick={onReset}
          className="px-3 py-1.5 bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 rounded-lg text-sm font-medium hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors duration-200 flex items-center gap-1.5"
        >
          <svg
            className="w-4 h-4"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
            />
          </svg>
          Reset
        </button>
      </div>
    </div>
    </div>
  );
}
