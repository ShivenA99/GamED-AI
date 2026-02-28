'use client'

import React, { useEffect, useState } from 'react'
import { usePipelineStore } from '@/stores/pipelineStore'
import axios from 'axios'
import { Zap } from 'lucide-react'

interface PipelineProgressProps {
  processId: string
  onComplete?: (visualizationId: string) => void
  onError?: (error: string) => void
}

const PROCESS_STEPS = [
  'Data Extraction',
  'Prompt Selection',
  'Content Analysis',
  'Template Matching',
  'Story Generation',
  'Blueprint Creation',
  'Asset Planning',
  'Final Assembly'
]

// Map backend step names to frontend step indices
const STEP_NAME_MAP: Record<string, number> = {
  'document_parsing': 0,
  'question_extraction': 0,
  'question_analysis': 1,
  'template_routing': 2,
  'strategy_creation': 3,
  'story_generation': 4,
  'blueprint_generation': 5,
  'asset_planning': 6,
  'asset_generation': 7
}

export default function PipelineProgress({
  processId,
  onComplete,
  onError,
}: PipelineProgressProps) {
  const [currentStepIndex, setCurrentStepIndex] = useState(0)
  const [stepProgress, setStepProgress] = useState(0)
  const [isPaused, setIsPaused] = useState(false)
  const [isCompleted, setIsCompleted] = useState(false)
  const [showAnalysis, setShowAnalysis] = useState(false)
  const [backendProgress, setBackendProgress] = useState(0)
  const [cachedSteps, setCachedSteps] = useState<Set<string>>(new Set())
  const [currentStepName, setCurrentStepName] = useState<string>('')
  
  // Faster durations when cache is used (1-2 seconds instead of 10-12)
  const getStepDuration = (stepIndex: number, stepName: string) => {
    const isCached = cachedSteps.has(stepName)
    if (isCached) {
      // Cached steps complete much faster
      return 1000 + Math.random() * 1000 // 1-2 seconds
    }
    // Normal durations
    if (stepIndex === PROCESS_STEPS.length - 1) {
      return 14000 + Math.random() * 8000
    }
    return 10000 + Math.random() * 2000
  }

  useEffect(() => {
    if (!processId) return

    let progressInterval: NodeJS.Timeout
    let pauseTimeout: NodeJS.Timeout
    let isCancelled = false
    let backendCompleted = false

    // Poll for completion in the background
    const pollForCompletion = async () => {
      try {
        const response = await axios.get(`/api/progress/${processId}`, { timeout: 5000 })
        const data = response.data

        // Update backend progress
        setBackendProgress(data.progress || 0)
        setCurrentStepName(data.current_step || '')

        // Track cached steps
        if (data.steps) {
          const cached = new Set<string>()
          data.steps.forEach((step: any) => {
            if (step.cached && step.status === 'completed') {
              cached.add(step.step_name)
            }
          })
          setCachedSteps(cached)
        }

        // Map backend step to frontend step index
        if (data.current_step) {
          const mappedIndex = STEP_NAME_MAP[data.current_step]
          if (mappedIndex !== undefined) {
            setCurrentStepIndex(mappedIndex)
          }
        }

        if (data.status === 'completed' && data.visualization_id) {
          backendCompleted = true
          setIsCompleted(true)
          // Complete the animation if not already done
          setCurrentStepIndex(PROCESS_STEPS.length - 1)
          setStepProgress(100)
          if (onComplete) {
            setTimeout(() => onComplete(data.visualization_id), 500)
          }
        } else if (data.status === 'error' && onError) {
          onError(data.error_message || 'Processing failed')
        }
      } catch (error) {
        // Silently handle errors - just continue polling
      }
    }

    const completionInterval = setInterval(pollForCompletion, 2000)

    // Animate through steps with random durations and pauses
    const startStepAnimation = (stepIndex: number) => {
      if (isCancelled || stepIndex >= PROCESS_STEPS.length) {
        return
      }

      // If completed by backend, finish the animation
      if (backendCompleted) {
        setCurrentStepIndex(PROCESS_STEPS.length - 1)
        setStepProgress(100)
        return
      }

      setCurrentStepIndex(stepIndex)
      setStepProgress(0)
      setIsPaused(false)

      // Get step name for cache check
      const stepName = Object.keys(STEP_NAME_MAP).find(
        key => STEP_NAME_MAP[key] === stepIndex
      ) || ''

      // Animate progress within this step
      const duration = getStepDuration(stepIndex, stepName)
      const startTime = Date.now()
      
      progressInterval = setInterval(() => {
        if (isCancelled || backendCompleted) {
          clearInterval(progressInterval)
          if (backendCompleted) {
            setCurrentStepIndex(PROCESS_STEPS.length - 1)
            setStepProgress(100)
          }
          return
        }

        const elapsed = Date.now() - startTime
        const progress = Math.min(100, (elapsed / duration) * 100)
        setStepProgress(progress)

        if (progress >= 100) {
          clearInterval(progressInterval)
          
          // Check if backend completed while this step was running
          if (backendCompleted) {
            setCurrentStepIndex(PROCESS_STEPS.length - 1)
            setStepProgress(100)
            return
          }
          
          // Add pause before next step
          setIsPaused(true)
          const pauseDuration = 500 + Math.random() * 1000 // 0.5-1.5 seconds
          
          pauseTimeout = setTimeout(() => {
            if (!isCancelled && !backendCompleted) {
              startStepAnimation(stepIndex + 1)
            } else if (backendCompleted) {
              setCurrentStepIndex(PROCESS_STEPS.length - 1)
              setStepProgress(100)
            }
          }, pauseDuration)
        }
      }, 50)
    }

    // Start animation
    startStepAnimation(0)

    return () => {
      isCancelled = true
      clearInterval(completionInterval)
      clearInterval(progressInterval)
      clearTimeout(pauseTimeout)
    }
  }, [processId, onComplete, onError])

  // Show Analysis section after Data Extraction completes (when moving to Prompt Selection)
  useEffect(() => {
    if (currentStepIndex >= 1) {
      setShowAnalysis(true)
    }
  }, [currentStepIndex])

  // Use backend progress if available, otherwise use animated progress
  const overallProgress = isCompleted 
    ? 100 
    : backendProgress > 0
    ? backendProgress
    : ((currentStepIndex + stepProgress / 100) / PROCESS_STEPS.length) * 100

  // Check if current step is cached
  const isCurrentStepCached = currentStepName && cachedSteps.has(currentStepName)

  return (
    <div className="w-full max-w-4xl mx-auto">
      <div className="bg-white rounded-lg shadow-sm p-6">
        {/* Simple horizontal line with progress */}
        <div className="relative w-full h-2 bg-gray-300 rounded-full overflow-hidden">
          <div
            className={`absolute left-0 top-0 h-full rounded-full transition-all duration-300 ${
              isPaused ? 'ease-in-out' : 'ease-linear'
            } ${
              isCurrentStepCached 
                ? 'bg-gradient-to-r from-yellow-400 to-yellow-600' 
                : 'bg-gray-600'
            }`}
            style={{ width: `${overallProgress}%` }}
          />
        </div>

        {/* Current step text with cache indicator */}
        {currentStepIndex < PROCESS_STEPS.length && !isCompleted && (
          <div className="mt-4 flex items-center justify-center gap-2">
            <p className="text-sm text-gray-600">
              {PROCESS_STEPS[currentStepIndex]}...
            </p>
            {isCurrentStepCached && (
              <div className="flex items-center gap-1 text-xs text-yellow-600 font-semibold">
                <Zap className="w-3 h-3" />
                <span>Cached</span>
              </div>
            )}
          </div>
        )}
        {isCompleted && (
          <p className="mt-4 text-sm text-green-600 text-center font-medium">
            Processing complete!
          </p>
        )}
      </div>

      {/* Analysis Section - Rendered after Data Extraction */}
      {showAnalysis && (
        <div className="bg-blue-50 rounded-lg shadow-sm p-6 mt-4">
          <h2 className="text-xl font-bold text-black mb-4">Analysis</h2>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <p className="text-sm text-gray-700 mb-1">
                <span className="font-medium">Type:</span> coding
              </p>
              <p className="text-sm text-gray-700 mb-1">
                <span className="font-medium">Difficulty:</span> advanced
              </p>
            </div>
            <div>
              <p className="text-sm text-gray-700 mb-1">
                <span className="font-medium">Subject:</span> Computer Science
              </p>
            </div>
          </div>
          <p className="text-sm text-gray-700 mt-2">
            <span className="font-medium">Key Concepts:</span> Array, Indexing, Searching, Target
          </p>
        </div>
      )}
    </div>
  )
}
