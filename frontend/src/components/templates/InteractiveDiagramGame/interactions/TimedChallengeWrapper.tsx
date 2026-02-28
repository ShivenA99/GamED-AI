'use client'

import React, { useState, useEffect, useCallback, useRef } from 'react'

/**
 * TimedChallengeWrapper - Adds time pressure to any interaction component
 *
 * Wraps other interaction components with a countdown timer.
 * Supports time bonuses and automatic submission on timeout.
 *
 * Uses requestAnimationFrame with delta accumulator for accurate timing
 * that doesn't drift on slow frames (unlike setInterval).
 */

export interface TimedChallengeProps {
  timeLimitSeconds: number
  showTimer?: boolean
  timeBonusScoring?: boolean
  timeBonusMaxPercent?: number
  timerWarningThreshold?: number
  timerCautionThreshold?: number
  pauseAllowed?: boolean
  onTimeUp: (timeElapsed: number) => void
  onComplete?: (timeRemaining: number) => void
  children: React.ReactNode
}

export interface TimedChallengeResult {
  completed: boolean
  timeElapsed: number
  timeRemaining: number
  timeBonus: number
}

export function TimedChallengeWrapper({
  timeLimitSeconds,
  showTimer = true,
  timeBonusScoring = true,
  timeBonusMaxPercent = 20,
  timerWarningThreshold = 10,
  timerCautionThreshold = 30,
  pauseAllowed = false,
  onTimeUp,
  onComplete,
  children,
}: TimedChallengeProps) {
  const [timeRemaining, setTimeRemaining] = useState(timeLimitSeconds)
  const [isPaused, setIsPaused] = useState(false)
  const [isCompleted, setIsCompleted] = useState(false)

  // RAF-based timer state (using refs to avoid re-renders during animation loop)
  const rafRef = useRef<number | null>(null)
  const lastTimeRef = useRef<number>(0)
  const accumulatorRef = useRef<number>(0)
  const timeRemainingRef = useRef<number>(timeLimitSeconds)

  // Keep ref in sync with state
  useEffect(() => {
    timeRemainingRef.current = timeRemaining
  }, [timeRemaining])

  // RAF-based timer logic for frame-rate independent timing
  useEffect(() => {
    if (isPaused || isCompleted || timeRemaining <= 0) {
      if (rafRef.current) {
        cancelAnimationFrame(rafRef.current)
        rafRef.current = null
      }
      return
    }

    // Initialize timing on start
    lastTimeRef.current = performance.now()
    accumulatorRef.current = 0

    const tick = (currentTime: number) => {
      // Calculate delta time in seconds
      const deltaMs = currentTime - lastTimeRef.current
      lastTimeRef.current = currentTime

      // Accumulate time (convert to seconds)
      accumulatorRef.current += deltaMs / 1000

      // Update once per second for display (but track precise time internally)
      if (accumulatorRef.current >= 1) {
        const secondsToSubtract = Math.floor(accumulatorRef.current)
        accumulatorRef.current -= secondsToSubtract

        setTimeRemaining((prev) => {
          const newTime = Math.max(0, prev - secondsToSubtract)
          if (newTime <= 0) {
            onTimeUp(timeLimitSeconds)
            return 0
          }
          return newTime
        })
      }

      // Continue the loop if time remains
      if (timeRemainingRef.current > 0) {
        rafRef.current = requestAnimationFrame(tick)
      }
    }

    rafRef.current = requestAnimationFrame(tick)

    return () => {
      if (rafRef.current) {
        cancelAnimationFrame(rafRef.current)
      }
    }
  }, [isPaused, isCompleted, timeLimitSeconds, onTimeUp])

  const handlePause = useCallback(() => {
    if (pauseAllowed && !isCompleted) {
      setIsPaused((prev) => !prev)
    }
  }, [pauseAllowed, isCompleted])

  const handleComplete = useCallback(() => {
    setIsCompleted(true)
    if (rafRef.current) {
      cancelAnimationFrame(rafRef.current)
      rafRef.current = null
    }
    onComplete?.(timeRemaining)
  }, [timeRemaining, onComplete])

  // Format time display
  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }

  // Calculate progress percentage
  const progress = (timeRemaining / timeLimitSeconds) * 100

  // Color based on time remaining
  const getTimerColor = () => {
    if (timeRemaining <= timerWarningThreshold) return 'text-red-600 bg-red-50'
    if (timeRemaining <= timerCautionThreshold) return 'text-amber-600 bg-amber-50'
    return 'text-blue-600 bg-blue-50'
  }

  // Calculate time bonus (if enabled)
  const timeBonus = timeBonusScoring
    ? Math.round((timeRemaining / timeLimitSeconds) * timeBonusMaxPercent)
    : 0

  return (
    <div className="relative">
      {/* Timer display */}
      {showTimer && (
        <div className="sticky top-0 z-10 mb-4">
          <div
            className={`
              flex items-center justify-between p-3 rounded-lg border-2
              ${getTimerColor()}
              ${timeRemaining <= timerWarningThreshold ? 'animate-pulse' : ''}
            `}
          >
            <div className="flex items-center gap-3">
              {/* Timer icon */}
              <svg
                className="w-6 h-6"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>

              {/* Time display */}
              <span className="text-2xl font-bold font-mono">
                {formatTime(timeRemaining)}
              </span>

              {/* Pause button */}
              {pauseAllowed && !isCompleted && (
                <button
                  onClick={handlePause}
                  className="p-1 rounded hover:bg-white/50 transition-colors"
                  title={isPaused ? 'Resume' : 'Pause'}
                >
                  {isPaused ? (
                    <svg
                      className="w-5 h-5"
                      fill="currentColor"
                      viewBox="0 0 20 20"
                    >
                      <path
                        fillRule="evenodd"
                        d="M10 18a8 8 0 100-16 8 8 0 000 16zM9.555 7.168A1 1 0 008 8v4a1 1 0 001.555.832l3-2a1 1 0 000-1.664l-3-2z"
                        clipRule="evenodd"
                      />
                    </svg>
                  ) : (
                    <svg
                      className="w-5 h-5"
                      fill="currentColor"
                      viewBox="0 0 20 20"
                    >
                      <path
                        fillRule="evenodd"
                        d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zM7 8a1 1 0 012 0v4a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v4a1 1 0 102 0V8a1 1 0 00-1-1z"
                        clipRule="evenodd"
                      />
                    </svg>
                  )}
                </button>
              )}
            </div>

            {/* Time bonus indicator */}
            {timeBonusScoring && timeRemaining > 0 && !isCompleted && (
              <div className="text-right">
                <p className="text-xs opacity-75">Time Bonus</p>
                <p className="text-lg font-bold">+{timeBonus}%</p>
              </div>
            )}
          </div>

          {/* Progress bar */}
          <div className="h-1 bg-gray-200 rounded-full overflow-hidden mt-1">
            <div
              className={`h-full transition-all duration-1000 ease-linear
                ${timeRemaining <= timerWarningThreshold ? 'bg-red-500' : ''}
                ${timeRemaining > timerWarningThreshold && timeRemaining <= timerCautionThreshold ? 'bg-amber-500' : ''}
                ${timeRemaining > timerCautionThreshold ? 'bg-blue-500' : ''}
              `}
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>
      )}

      {/* Paused overlay */}
      {isPaused && (
        <div className="absolute inset-0 bg-white/90 flex items-center justify-center z-20 rounded-lg">
          <div className="text-center">
            <p className="text-2xl font-bold text-gray-700 mb-4">Paused</p>
            <button
              onClick={handlePause}
              className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium"
            >
              Resume
            </button>
          </div>
        </div>
      )}

      {/* Time's up overlay */}
      {timeRemaining === 0 && !isCompleted && (
        <div className="absolute inset-0 bg-red-50/90 flex items-center justify-center z-20 rounded-lg border-2 border-red-300">
          <div className="text-center">
            <p className="text-3xl font-bold text-red-600 mb-2">Time&apos;s Up!</p>
            <p className="text-gray-600">Your answers have been submitted.</p>
          </div>
        </div>
      )}

      {/* Content */}
      <div className={isPaused ? 'opacity-30 pointer-events-none' : ''}>
        {children}
      </div>
    </div>
  )
}

export default TimedChallengeWrapper
