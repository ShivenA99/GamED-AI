'use client'

import React, { useState, useEffect, useCallback, useMemo } from 'react'
import { StageExecution } from './types'

interface LiveTokenCounterProps {
  runId: string
  stages?: StageExecution[]
  pollInterval?: number
  compact?: boolean
}

interface TokenMetrics {
  promptTokens: number
  completionTokens: number
  totalTokens: number
  estimatedCost: number
  stageCount: number
  llmCalls: number
}

/**
 * Real-Time Token Counter
 *
 * Displays live token accumulation during pipeline execution.
 * Updates as stages complete, showing:
 * - Prompt tokens (input)
 * - Completion tokens (output)
 * - Total tokens
 * - Estimated cost
 * - Active LLM call indicator
 */
export function LiveTokenCounter({
  runId,
  stages: externalStages,
  pollInterval = 3000,
  compact = false,
}: LiveTokenCounterProps) {
  const [metrics, setMetrics] = useState<TokenMetrics>({
    promptTokens: 0,
    completionTokens: 0,
    totalTokens: 0,
    estimatedCost: 0,
    stageCount: 0,
    llmCalls: 0,
  })
  const [isPolling, setIsPolling] = useState(false)
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null)

  // Calculate metrics from stages
  const calculateMetrics = useCallback((stages: StageExecution[]): TokenMetrics => {
    let promptTokens = 0
    let completionTokens = 0
    let totalTokens = 0
    let estimatedCost = 0
    let stageCount = 0
    let llmCalls = 0

    for (const stage of stages) {
      if (stage.status === 'success') {
        if (stage.prompt_tokens) promptTokens += stage.prompt_tokens
        if (stage.completion_tokens) completionTokens += stage.completion_tokens
        if (stage.total_tokens) {
          totalTokens += stage.total_tokens
        } else if (stage.prompt_tokens || stage.completion_tokens) {
          totalTokens += (stage.prompt_tokens || 0) + (stage.completion_tokens || 0)
        }
        if (stage.estimated_cost_usd) estimatedCost += stage.estimated_cost_usd
        if (stage.prompt_tokens || stage.total_tokens) {
          stageCount++
          llmCalls++
        }
      }
    }

    return {
      promptTokens,
      completionTokens,
      totalTokens,
      estimatedCost,
      stageCount,
      llmCalls,
    }
  }, [])

  // Update from external stages prop
  useEffect(() => {
    if (externalStages && externalStages.length > 0) {
      const newMetrics = calculateMetrics(externalStages)
      setMetrics(newMetrics)
      setLastUpdate(new Date())
    }
  }, [externalStages, calculateMetrics])

  // Poll for updates if no external stages provided
  useEffect(() => {
    if (externalStages || !runId) return

    const fetchMetrics = async () => {
      try {
        setIsPolling(true)
        const response = await fetch(`/api/observability/runs/${runId}`)
        if (!response.ok) return

        const data = await response.json()
        if (data.stages) {
          const newMetrics = calculateMetrics(data.stages)
          setMetrics(newMetrics)
          setLastUpdate(new Date())
        }
      } catch (err) {
        // Silent fail on polling
      } finally {
        setIsPolling(false)
      }
    }

    fetchMetrics()
    const interval = setInterval(fetchMetrics, pollInterval)

    return () => clearInterval(interval)
  }, [runId, externalStages, pollInterval, calculateMetrics])

  // Format numbers with commas
  const formatNumber = (n: number): string => {
    return n.toLocaleString()
  }

  // Format cost with appropriate precision
  const formatCost = (cost: number): string => {
    if (cost === 0) return '$0.00'
    if (cost < 0.01) return `$${cost.toFixed(4)}`
    return `$${cost.toFixed(2)}`
  }

  // Animated counter effect
  const AnimatedValue = ({ value, format = formatNumber }: { value: number; format?: (n: number) => string }) => {
    const [displayValue, setDisplayValue] = useState(0)

    useEffect(() => {
      // Animate from current to target
      const duration = 500
      const startValue = displayValue
      const diff = value - startValue
      if (diff === 0) return

      const startTime = Date.now()
      const animate = () => {
        const elapsed = Date.now() - startTime
        const progress = Math.min(elapsed / duration, 1)
        // Ease out
        const eased = 1 - Math.pow(1 - progress, 3)
        setDisplayValue(Math.round(startValue + diff * eased))

        if (progress < 1) {
          requestAnimationFrame(animate)
        }
      }

      requestAnimationFrame(animate)
    }, [value])

    return <span className="font-mono tabular-nums">{format(displayValue)}</span>
  }

  if (compact) {
    return (
      <div className="flex items-center gap-4 text-sm">
        <div className="flex items-center gap-1.5">
          <svg className="w-4 h-4 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16V4m0 0L3 8m4-4l4 4m6 0v12m0 0l4-4m-4 4l-4-4" />
          </svg>
          <span className="text-gray-500">Tokens:</span>
          <AnimatedValue value={metrics.totalTokens} />
        </div>
        <div className="flex items-center gap-1.5">
          <svg className="w-4 h-4 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <span className="text-gray-500">Cost:</span>
          <span className="font-mono text-green-600">{formatCost(metrics.estimatedCost)}</span>
        </div>
        {isPolling && (
          <div className="w-2 h-2 bg-blue-500 rounded-full animate-pulse" />
        )}
      </div>
    )
  }

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-gray-700 flex items-center gap-2">
          <svg className="w-4 h-4 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
          </svg>
          Live Token Usage
        </h3>
        {isPolling && (
          <div className="flex items-center gap-1 text-xs text-blue-600">
            <div className="w-1.5 h-1.5 bg-blue-500 rounded-full animate-pulse" />
            Updating...
          </div>
        )}
      </div>

      {/* Main metrics grid */}
      <div className="grid grid-cols-2 gap-4 mb-4">
        {/* Total Tokens */}
        <div className="bg-gradient-to-br from-blue-50 to-indigo-50 rounded-lg p-3">
          <div className="text-xs text-blue-600 font-medium mb-1">Total Tokens</div>
          <div className="text-2xl font-bold text-blue-700">
            <AnimatedValue value={metrics.totalTokens} />
          </div>
        </div>

        {/* Estimated Cost */}
        <div className="bg-gradient-to-br from-green-50 to-emerald-50 rounded-lg p-3">
          <div className="text-xs text-green-600 font-medium mb-1">Estimated Cost</div>
          <div className="text-2xl font-bold text-green-700">
            {formatCost(metrics.estimatedCost)}
          </div>
        </div>
      </div>

      {/* Breakdown */}
      <div className="space-y-2">
        {/* Input/Output breakdown */}
        <div className="flex items-center justify-between text-sm">
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-purple-400" />
            <span className="text-gray-600">Prompt (Input)</span>
          </div>
          <span className="font-mono text-purple-700">
            <AnimatedValue value={metrics.promptTokens} />
          </span>
        </div>

        <div className="flex items-center justify-between text-sm">
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-orange-400" />
            <span className="text-gray-600">Completion (Output)</span>
          </div>
          <span className="font-mono text-orange-700">
            <AnimatedValue value={metrics.completionTokens} />
          </span>
        </div>

        {/* Progress bar showing input/output ratio */}
        {metrics.totalTokens > 0 && (
          <div className="mt-2">
            <div className="h-2 bg-gray-100 rounded-full overflow-hidden flex">
              <div
                className="h-full bg-purple-400 transition-all duration-500"
                style={{
                  width: `${(metrics.promptTokens / metrics.totalTokens) * 100}%`,
                }}
              />
              <div
                className="h-full bg-orange-400 transition-all duration-500"
                style={{
                  width: `${(metrics.completionTokens / metrics.totalTokens) * 100}%`,
                }}
              />
            </div>
          </div>
        )}

        {/* LLM calls count */}
        <div className="flex items-center justify-between text-sm pt-2 border-t border-gray-100 mt-2">
          <span className="text-gray-500">LLM Stages Completed</span>
          <span className="font-mono text-gray-700">{metrics.stageCount}</span>
        </div>
      </div>

      {/* Last update timestamp */}
      {lastUpdate && (
        <div className="mt-3 pt-2 border-t border-gray-100 text-xs text-gray-400">
          Last updated: {lastUpdate.toLocaleTimeString()}
        </div>
      )}
    </div>
  )
}

export default LiveTokenCounter
