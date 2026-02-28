'use client';

import { useEffect, useState, useCallback } from 'react';
import { SceneProgressionType, SceneResult } from './types';

type TransitionAnimation = 'zoom_in' | 'slide_left' | 'slide_right' | 'fade' | 'reveal';

interface TransitionConfig {
  animation: TransitionAnimation;
  duration_ms?: number;
  delay_ms?: number;
}

interface SceneTransitionProps {
  /**
   * Whether the transition is currently active
   */
  isTransitioning: boolean;

  /**
   * Transition configuration
   */
  transition?: TransitionConfig;

  /**
   * Scene progression type for default animation selection
   */
  progressionType?: SceneProgressionType;

  /**
   * Callback when transition starts
   */
  onTransitionStart?: () => void;

  /**
   * Callback when transition ends
   */
  onTransitionEnd?: () => void;

  /**
   * Current scene content (will animate out)
   */
  currentScene: React.ReactNode;

  /**
   * Next scene content (will animate in)
   */
  nextScene?: React.ReactNode;

  /**
   * Optional focal point for zoom animations (percentage coordinates)
   */
  zoomFocalPoint?: { x: number; y: number };
}

/**
 * SceneTransition Component
 *
 * HAD v3: Handles smooth transitions between multi-scene games.
 * Supports various animation types based on progression_type.
 */
export default function SceneTransition({
  isTransitioning,
  transition,
  progressionType = 'linear',
  onTransitionStart,
  onTransitionEnd,
  currentScene,
  nextScene,
  zoomFocalPoint = { x: 50, y: 50 },
}: SceneTransitionProps) {
  const [phase, setPhase] = useState<'idle' | 'out' | 'in' | 'complete'>('idle');
  const [showNext, setShowNext] = useState(false);

  // Determine animation based on transition config or progression type
  const animation = transition?.animation ?? getDefaultAnimation(progressionType);
  const duration = transition?.duration_ms ?? 500;
  const delay = transition?.delay_ms ?? 0;

  // Handle transition lifecycle
  useEffect(() => {
    if (isTransitioning && phase === 'idle') {
      // Start transition
      setPhase('out');
      onTransitionStart?.();

      // After delay + out animation, switch to 'in' phase
      const outTimer = setTimeout(() => {
        setShowNext(true);
        setPhase('in');
      }, delay + duration);

      // After in animation, complete
      const completeTimer = setTimeout(() => {
        setPhase('complete');
        onTransitionEnd?.();
      }, delay + duration * 2);

      return () => {
        clearTimeout(outTimer);
        clearTimeout(completeTimer);
      };
    } else if (!isTransitioning && phase === 'complete') {
      // Reset for next transition
      setPhase('idle');
      setShowNext(false);
    }
  }, [isTransitioning, phase, delay, duration, onTransitionStart, onTransitionEnd]);

  // Get CSS classes for current scene based on animation and phase
  const getCurrentSceneClasses = useCallback(() => {
    const baseClasses = 'absolute inset-0 transition-all';
    const durationClass = `duration-${Math.round(duration / 100) * 100}`;

    if (phase === 'idle') {
      return `${baseClasses} opacity-100`;
    }

    switch (animation) {
      case 'zoom_in':
        return phase === 'out'
          ? `${baseClasses} ${durationClass} transform scale-150 opacity-0`
          : `${baseClasses} opacity-0`;

      case 'slide_left':
        return phase === 'out'
          ? `${baseClasses} ${durationClass} transform -translate-x-full opacity-0`
          : `${baseClasses} opacity-0`;

      case 'slide_right':
        return phase === 'out'
          ? `${baseClasses} ${durationClass} transform translate-x-full opacity-0`
          : `${baseClasses} opacity-0`;

      case 'fade':
        return phase === 'out'
          ? `${baseClasses} ${durationClass} opacity-0`
          : `${baseClasses} opacity-0`;

      case 'reveal':
        return phase === 'out'
          ? `${baseClasses} ${durationClass} opacity-0 scale-95`
          : `${baseClasses} opacity-0`;

      default:
        return `${baseClasses} ${phase === 'out' ? 'opacity-0' : ''}`;
    }
  }, [animation, phase, duration]);

  // Get CSS classes for next scene based on animation and phase
  const getNextSceneClasses = useCallback(() => {
    const baseClasses = 'absolute inset-0 transition-all';
    const durationClass = `duration-${Math.round(duration / 100) * 100}`;

    if (!showNext) {
      return `${baseClasses} opacity-0`;
    }

    switch (animation) {
      case 'zoom_in':
        return phase === 'in'
          ? `${baseClasses} ${durationClass} transform scale-100 opacity-100`
          : `${baseClasses} transform scale-75 opacity-0`;

      case 'slide_left':
        return phase === 'in'
          ? `${baseClasses} ${durationClass} transform translate-x-0 opacity-100`
          : `${baseClasses} transform translate-x-full opacity-0`;

      case 'slide_right':
        return phase === 'in'
          ? `${baseClasses} ${durationClass} transform translate-x-0 opacity-100`
          : `${baseClasses} transform -translate-x-full opacity-0`;

      case 'fade':
        return phase === 'in'
          ? `${baseClasses} ${durationClass} opacity-100`
          : `${baseClasses} opacity-0`;

      case 'reveal':
        return phase === 'in'
          ? `${baseClasses} ${durationClass} opacity-100 scale-100`
          : `${baseClasses} opacity-0 scale-105`;

      default:
        return `${baseClasses} ${phase === 'in' ? 'opacity-100' : 'opacity-0'}`;
    }
  }, [animation, phase, duration, showNext]);

  // Get transform origin for zoom animations
  const getZoomOrigin = useCallback(() => {
    if (animation === 'zoom_in') {
      return `${zoomFocalPoint.x}% ${zoomFocalPoint.y}%`;
    }
    return 'center center';
  }, [animation, zoomFocalPoint]);

  return (
    <div className="relative w-full h-full overflow-hidden">
      {/* Current scene */}
      <div
        className={getCurrentSceneClasses()}
        style={{
          transformOrigin: getZoomOrigin(),
          transitionDuration: `${duration}ms`,
        }}
      >
        {currentScene}
      </div>

      {/* Next scene (appears during transition) */}
      {nextScene && (
        <div
          className={getNextSceneClasses()}
          style={{
            transformOrigin: 'center center',
            transitionDuration: `${duration}ms`,
          }}
        >
          {nextScene}
        </div>
      )}

      {/* Transition overlay effects */}
      {isTransitioning && animation === 'zoom_in' && phase === 'out' && (
        <div
          className="absolute pointer-events-none"
          style={{
            left: `${zoomFocalPoint.x}%`,
            top: `${zoomFocalPoint.y}%`,
            transform: 'translate(-50%, -50%)',
          }}
        >
          {/* Zoom focus indicator */}
          <div
            className="w-24 h-24 rounded-full border-4 border-primary-500 animate-ping opacity-50"
            style={{ animationDuration: `${duration}ms` }}
          />
        </div>
      )}
    </div>
  );
}

/**
 * Get default animation based on progression type
 */
function getDefaultAnimation(progressionType: SceneProgressionType): TransitionAnimation {
  switch (progressionType) {
    case 'zoom_in':
      return 'zoom_in';
    case 'depth_first':
      return 'reveal';
    case 'branching':
      return 'fade';
    case 'linear':
    default:
      return 'slide_left';
  }
}

/**
 * Hook for managing scene transitions
 */
export function useSceneTransition(
  onTransitionComplete: () => void,
  progressionType: SceneProgressionType = 'linear'
) {
  const [isTransitioning, setIsTransitioning] = useState(false);
  const [transitionConfig, setTransitionConfig] = useState<TransitionConfig | undefined>();

  const startTransition = useCallback(
    (config?: TransitionConfig) => {
      setTransitionConfig(config);
      setIsTransitioning(true);
    },
    []
  );

  const handleTransitionEnd = useCallback(() => {
    setIsTransitioning(false);
    onTransitionComplete();
  }, [onTransitionComplete]);

  return {
    isTransitioning,
    transitionConfig,
    startTransition,
    handleTransitionEnd,
    defaultAnimation: getDefaultAnimation(progressionType),
  };
}

/**
 * Scene transition indicator component
 * Shows numbered circles with connecting lines and per-scene scores
 */
export function SceneIndicator({
  totalScenes,
  currentScene,
  completedScenes,
  sceneResults,
  sceneNames,
}: {
  totalScenes: number;
  currentScene: number;
  completedScenes: number[];
  sceneResults?: SceneResult[];
  sceneNames?: string[];
}) {
  return (
    <div className="flex items-center justify-center py-4">
      {Array.from({ length: totalScenes }, (_, i) => {
        const sceneNum = i + 1;
        const isCompleted = completedScenes.includes(sceneNum);
        const isCurrent = currentScene === sceneNum;
        const result = sceneResults?.[i];
        const sceneName = sceneNames?.[i];
        const tooltipText = sceneName
          ? `${sceneName}${isCompleted ? ' (completed)' : isCurrent ? ' (current)' : ''}`
          : `Scene ${sceneNum}${isCompleted ? ' (completed)' : isCurrent ? ' (current)' : ''}`;

        return (
          <div key={sceneNum} className="flex items-center">
            {/* Connecting line before (skip for first) */}
            {i > 0 && (
              <div
                className={`w-8 h-0.5 transition-all duration-300 ${
                  isCompleted || isCurrent ? 'bg-primary-400' : 'bg-gray-300 dark:bg-gray-600'
                }`}
              />
            )}
            {/* Scene circle + score */}
            <div className="flex flex-col items-center gap-1">
              <div
                className={`
                  w-7 h-7 rounded-full flex items-center justify-center
                  text-xs font-bold transition-all duration-300
                  ${isCompleted
                    ? 'bg-green-500 text-white'
                    : isCurrent
                      ? 'bg-primary-500 text-white ring-2 ring-primary-300 ring-offset-1 dark:ring-offset-gray-900'
                      : 'bg-gray-200 dark:bg-gray-600 text-gray-500 dark:text-gray-400'
                  }
                `}
                title={tooltipText}
              >
                {isCompleted ? (
                  <svg className="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                  </svg>
                ) : (
                  sceneNum
                )}
              </div>
              {/* Per-scene score under completed circles */}
              {isCompleted && result && (
                <span className="text-[10px] font-medium text-green-600 dark:text-green-400 whitespace-nowrap">
                  {result.score}/{result.max_score}
                </span>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
