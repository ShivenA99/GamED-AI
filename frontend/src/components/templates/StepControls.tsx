'use client'

import { useEffect, useCallback } from 'react'

interface StepControlsProps {
  currentStep: number
  totalSteps: number
  isPlaying: boolean
  speed: number
  onPrev: () => void
  onNext: () => void
  onPlay: () => void
  onPause: () => void
  onReset: () => void
  onSpeedChange: (speed: number) => void
  disabled?: boolean
  theme?: 'dark' | 'light'
}

const SPEED_OPTIONS = [0.5, 1, 1.5, 2]

export default function StepControls({
  currentStep,
  totalSteps,
  isPlaying,
  speed,
  onPrev,
  onNext,
  onPlay,
  onPause,
  onReset,
  onSpeedChange,
  disabled = false,
  theme = 'dark',
}: StepControlsProps) {
  // Keyboard shortcuts
  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (disabled) return

      switch (e.key) {
        case 'ArrowLeft':
          e.preventDefault()
          onPrev()
          break
        case 'ArrowRight':
          e.preventDefault()
          onNext()
          break
        case ' ':
          e.preventDefault()
          isPlaying ? onPause() : onPlay()
          break
        case 'r':
        case 'R':
          if (!e.metaKey && !e.ctrlKey) {
            e.preventDefault()
            onReset()
          }
          break
      }
    },
    [disabled, isPlaying, onPrev, onNext, onPlay, onPause, onReset]
  )

  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [handleKeyDown])

  const progress = totalSteps > 0 ? ((currentStep + 1) / totalSteps) * 100 : 0

  const buttonClass = (active?: boolean) => `
    p-2 rounded-lg transition-all duration-200
    ${
      disabled
        ? theme === 'dark'
          ? 'bg-gray-700 text-gray-500 cursor-not-allowed'
          : 'bg-gray-200 text-gray-400 cursor-not-allowed'
        : active
        ? theme === 'dark'
          ? 'bg-primary-500 text-white hover:bg-primary-600'
          : 'bg-primary-500 text-white hover:bg-primary-600'
        : theme === 'dark'
        ? 'bg-gray-700 text-gray-300 hover:bg-gray-600'
        : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
    }
  `

  return (
    <div
      className={`rounded-lg p-4 ${
        theme === 'dark' ? 'bg-[#2d2d2d]' : 'bg-gray-100'
      }`}
    >
      {/* Progress bar */}
      <div className="mb-4">
        <div className="flex justify-between text-xs mb-1">
          <span className={theme === 'dark' ? 'text-gray-400' : 'text-gray-600'}>
            Step {currentStep + 1} of {totalSteps}
          </span>
          <span className={theme === 'dark' ? 'text-gray-400' : 'text-gray-600'}>
            {Math.round(progress)}%
          </span>
        </div>
        <div
          className={`h-2 rounded-full overflow-hidden ${
            theme === 'dark' ? 'bg-gray-700' : 'bg-gray-300'
          }`}
        >
          <div
            className="h-full bg-gradient-to-r from-primary-500 to-secondary-500 transition-all duration-300"
            style={{ width: `${progress}%` }}
          />
        </div>
      </div>

      {/* Controls */}
      <div className="flex items-center justify-between">
        {/* Left: Reset */}
        <button
          onClick={onReset}
          disabled={disabled}
          className={buttonClass()}
          title="Reset (R)"
        >
          <svg
            className="w-5 h-5"
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
        </button>

        {/* Center: Navigation */}
        <div className="flex items-center space-x-2">
          {/* Previous */}
          <button
            onClick={onPrev}
            disabled={disabled || currentStep === 0}
            className={buttonClass()}
            title="Previous Step (Left Arrow)"
          >
            <svg
              className="w-5 h-5"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M15 19l-7-7 7-7"
              />
            </svg>
          </button>

          {/* Play/Pause */}
          <button
            onClick={isPlaying ? onPause : onPlay}
            disabled={disabled}
            className={`${buttonClass(isPlaying)} px-4`}
            title={isPlaying ? 'Pause (Space)' : 'Play (Space)'}
          >
            {isPlaying ? (
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
                  d="M10 9v6m4-6v6m7-3a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
            ) : (
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
                  d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z"
                />
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
            )}
          </button>

          {/* Next */}
          <button
            onClick={onNext}
            disabled={disabled || currentStep >= totalSteps - 1}
            className={buttonClass()}
            title="Next Step (Right Arrow)"
          >
            <svg
              className="w-5 h-5"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M9 5l7 7-7 7"
              />
            </svg>
          </button>
        </div>

        {/* Right: Speed selector */}
        <div className="flex items-center space-x-2">
          <span
            className={`text-xs ${
              theme === 'dark' ? 'text-gray-400' : 'text-gray-600'
            }`}
          >
            Speed:
          </span>
          <div className="flex rounded-lg overflow-hidden">
            {SPEED_OPTIONS.map((s) => (
              <button
                key={s}
                onClick={() => onSpeedChange(s)}
                disabled={disabled}
                className={`
                  px-2 py-1 text-xs font-medium transition-all
                  ${
                    speed === s
                      ? theme === 'dark'
                        ? 'bg-primary-500 text-white'
                        : 'bg-primary-500 text-white'
                      : theme === 'dark'
                      ? 'bg-gray-700 text-gray-400 hover:bg-gray-600'
                      : 'bg-gray-200 text-gray-600 hover:bg-gray-300'
                  }
                  ${disabled ? 'cursor-not-allowed opacity-50' : ''}
                `}
              >
                {s}x
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Keyboard hints */}
      <div
        className={`mt-3 pt-3 border-t text-xs text-center ${
          theme === 'dark' ? 'border-gray-700 text-gray-500' : 'border-gray-300 text-gray-400'
        }`}
      >
        Keyboard: <kbd className="px-1 rounded bg-gray-700 text-gray-300 mx-1">←</kbd>
        <kbd className="px-1 rounded bg-gray-700 text-gray-300 mx-1">→</kbd> navigate,
        <kbd className="px-1 rounded bg-gray-700 text-gray-300 mx-1">Space</kbd> play/pause,
        <kbd className="px-1 rounded bg-gray-700 text-gray-300 mx-1">R</kbd> reset
      </div>
    </div>
  )
}
