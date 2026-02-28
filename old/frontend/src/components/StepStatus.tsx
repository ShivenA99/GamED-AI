'use client'

import React from 'react'
import { CheckCircle2, XCircle, Clock, Loader2, AlertCircle } from 'lucide-react'

interface StepStatusProps {
  stepName: string
  stepNumber: number
  status: 'pending' | 'processing' | 'completed' | 'error' | 'skipped'
  errorMessage?: string
  retryCount?: number
  startedAt?: string
  completedAt?: string
  validationResult?: {
    is_valid: boolean
    errors?: string[]
    warnings?: string[]
  }
  onRetry?: () => void
}

type StatusConfig = {
  icon: React.ComponentType<{ className?: string }>
  color: string
  bgColor: string
  label: string
  animate?: boolean
}

const statusConfig: Record<string, StatusConfig> = {
  pending: {
    icon: Clock,
    color: 'text-gray-400',
    bgColor: 'bg-gray-100',
    label: 'Pending',
  },
  processing: {
    icon: Loader2,
    color: 'text-blue-500',
    bgColor: 'bg-blue-100',
    label: 'Processing',
    animate: true,
  },
  completed: {
    icon: CheckCircle2,
    color: 'text-green-500',
    bgColor: 'bg-green-100',
    label: 'Completed',
  },
  error: {
    icon: XCircle,
    color: 'text-red-500',
    bgColor: 'bg-red-100',
    label: 'Error',
  },
  skipped: {
    icon: AlertCircle,
    color: 'text-yellow-500',
    bgColor: 'bg-yellow-100',
    label: 'Skipped',
  },
}

export default function StepStatus({
  stepName,
  stepNumber,
  status,
  errorMessage,
  retryCount,
  startedAt,
  completedAt,
  validationResult,
  onRetry,
}: StepStatusProps) {
  const config = statusConfig[status]
  const Icon = config.icon
  const isAnimated = config.animate ?? false

  const formatTime = (timeStr?: string) => {
    if (!timeStr) return null
    try {
      const date = new Date(timeStr)
      return date.toLocaleTimeString()
    } catch {
      return null
    }
  }

  const getDuration = () => {
    if (!startedAt || !completedAt) return null
    try {
      const start = new Date(startedAt)
      const end = new Date(completedAt)
      const seconds = Math.round((end.getTime() - start.getTime()) / 1000)
      return `${seconds}s`
    } catch {
      return null
    }
  }

  return (
    <div className="flex items-start gap-4 p-4 bg-white rounded-lg border border-gray-200">
      <div className={`flex-shrink-0 w-10 h-10 rounded-full ${config.bgColor} flex items-center justify-center`}>
        <Icon
          className={`w-5 h-5 ${config.color} ${isAnimated ? 'animate-spin' : ''}`}
        />
      </div>
      
      <div className="flex-1 min-w-0">
        <div className="flex items-center justify-between mb-1">
          <div>
            <span className="text-sm font-medium text-gray-500">Step {stepNumber}</span>
            <h3 className="text-base font-semibold text-gray-900">{stepName}</h3>
          </div>
          <span className={`text-sm font-medium ${config.color}`}>{config.label}</span>
        </div>
        
        {errorMessage && (
          <div className="mt-2 p-2 bg-red-50 border border-red-200 rounded text-sm text-red-700">
            {errorMessage}
            {onRetry && (
              <button
                onClick={onRetry}
                className="mt-2 text-red-600 hover:text-red-800 underline"
              >
                Retry
              </button>
            )}
          </div>
        )}
        
        {validationResult && (
          <div className="mt-2">
            {!validationResult.is_valid && validationResult.errors && (
              <div className="text-sm text-red-600">
                Validation errors: {validationResult.errors.join(', ')}
              </div>
            )}
            {validationResult.warnings && validationResult.warnings.length > 0 && (
              <div className="text-sm text-yellow-600">
                Warnings: {validationResult.warnings.join(', ')}
              </div>
            )}
          </div>
        )}
        
        <div className="mt-2 flex items-center gap-4 text-xs text-gray-500">
          {startedAt && <span>Started: {formatTime(startedAt)}</span>}
          {completedAt && <span>Completed: {formatTime(completedAt)}</span>}
          {getDuration() && <span>Duration: {getDuration()}</span>}
          {retryCount !== undefined && retryCount > 0 && (
            <span>Retries: {retryCount}</span>
          )}
        </div>
      </div>
    </div>
  )
}

