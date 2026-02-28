'use client'

import { useState, useEffect, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Play, Pause, StepForward, StepBack, RotateCcw, Gauge } from 'lucide-react'

export interface AlgorithmStep {
  stepNumber: number
  left?: number
  right?: number
  mid?: number
  comparison?: string
  decision?: string
  explanation?: string
  variables?: Record<string, any>
  highlightIndices?: number[]
  sortedRanges?: Array<{ start: number; end: number }>
}

interface AlgorithmStepperProps {
  steps: AlgorithmStep[]
  onStepChange?: (step: AlgorithmStep, stepIndex: number) => void
  autoPlay?: boolean
  speed?: number // milliseconds per step
  onComplete?: () => void
}

export function AlgorithmStepper({
  steps,
  onStepChange,
  autoPlay = false,
  speed = 1500,
  onComplete
}: AlgorithmStepperProps) {
  const [currentStepIndex, setCurrentStepIndex] = useState(0)
  const [isPlaying, setIsPlaying] = useState(autoPlay)
  const [playbackSpeed, setPlaybackSpeed] = useState(speed)

  const currentStep = steps[currentStepIndex]

  useEffect(() => {
    if (onStepChange && currentStep) {
      onStepChange(currentStep, currentStepIndex)
    }
  }, [currentStepIndex, currentStep, onStepChange])

  useEffect(() => {
    if (isPlaying && currentStepIndex < steps.length - 1) {
      const timer = setTimeout(() => {
        setCurrentStepIndex(prev => {
          const next = prev + 1
          if (next >= steps.length - 1 && onComplete) {
            setIsPlaying(false)
            onComplete()
          }
          return next
        })
      }, playbackSpeed)
      return () => clearTimeout(timer)
    } else if (currentStepIndex >= steps.length - 1) {
      setIsPlaying(false)
    }
  }, [isPlaying, currentStepIndex, steps.length, playbackSpeed, onComplete])

  const handlePrevious = () => {
    setIsPlaying(false)
    setCurrentStepIndex(prev => Math.max(0, prev - 1))
  }

  const handleNext = () => {
    setIsPlaying(false)
    setCurrentStepIndex(prev => Math.min(steps.length - 1, prev + 1))
  }

  const handlePlay = () => {
    if (currentStepIndex >= steps.length - 1) {
      setCurrentStepIndex(0)
    }
    setIsPlaying(true)
  }

  const handlePause = () => {
    setIsPlaying(false)
  }

  const handleReset = () => {
    setIsPlaying(false)
    setCurrentStepIndex(0)
  }

  const progress = ((currentStepIndex + 1) / steps.length) * 100

  return (
    <div className="w-full space-y-4">
      {/* Progress Bar */}
      <div className="w-full bg-gray-200 rounded-full h-2 overflow-hidden">
        <motion.div
          className="bg-[#00A67E] h-2 rounded-full"
          initial={{ width: 0 }}
          animate={{ width: `${progress}%` }}
          transition={{ duration: 0.3 }}
        />
      </div>

      {/* Controls */}
      <div className="flex items-center justify-between gap-4">
        <div className="flex items-center gap-2">
          <button
            onClick={handleReset}
            className="p-2 rounded-lg bg-gray-100 hover:bg-gray-200 transition-colors"
            title="Reset"
          >
            <RotateCcw className="w-5 h-5" />
          </button>
          
          <button
            onClick={handlePrevious}
            disabled={currentStepIndex === 0}
            className="p-2 rounded-lg bg-gray-100 hover:bg-gray-200 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            title="Previous Step"
          >
            <StepBack className="w-5 h-5" />
          </button>

          {isPlaying ? (
            <button
              onClick={handlePause}
              className="p-2 rounded-lg bg-[#00A67E] text-white hover:bg-[#008F6B] transition-colors"
              title="Pause"
            >
              <Pause className="w-5 h-5" />
            </button>
          ) : (
            <button
              onClick={handlePlay}
              disabled={currentStepIndex >= steps.length - 1}
              className="p-2 rounded-lg bg-[#00A67E] text-white hover:bg-[#008F6B] transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              title="Play"
            >
              <Play className="w-5 h-5" />
            </button>
          )}

          <button
            onClick={handleNext}
            disabled={currentStepIndex >= steps.length - 1}
            className="p-2 rounded-lg bg-gray-100 hover:bg-gray-200 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            title="Next Step"
          >
            <StepForward className="w-5 h-5" />
          </button>
        </div>

        {/* Speed Control */}
        <div className="flex items-center gap-2">
          <Gauge className="w-4 h-4 text-gray-500" />
          <input
            type="range"
            min="300"
            max="3000"
            step="100"
            value={playbackSpeed}
            onChange={(e) => {
              setPlaybackSpeed(Number(e.target.value))
              setIsPlaying(false)
            }}
            className="w-24"
          />
          <span className="text-sm text-gray-600 w-16">
            {playbackSpeed < 1000 ? `${playbackSpeed}ms` : `${playbackSpeed / 1000}s`}
          </span>
        </div>

        {/* Step Counter */}
        <div className="text-sm text-gray-600">
          Step {currentStepIndex + 1} of {steps.length}
        </div>
      </div>

      {/* Current Step Info */}
      <AnimatePresence mode="wait">
        {currentStep && (
          <motion.div
            key={currentStepIndex}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            transition={{ duration: 0.2 }}
            className="p-4 bg-blue-50 rounded-lg border border-blue-200"
          >
            {currentStep.explanation && (
              <p className="text-sm text-gray-700 mb-2">{currentStep.explanation}</p>
            )}
            {currentStep.comparison && (
              <p className="text-sm font-mono text-gray-800 mb-1">
                <span className="font-semibold">Comparison:</span> {currentStep.comparison}
              </p>
            )}
            {currentStep.decision && (
              <p className="text-sm font-mono text-gray-800">
                <span className="font-semibold">Decision:</span> {currentStep.decision}
              </p>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

