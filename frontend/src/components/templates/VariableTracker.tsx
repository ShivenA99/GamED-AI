'use client'

import { useState, useEffect } from 'react'

interface VariableTrackerProps {
  variables: Record<string, any>
  previousVariables?: Record<string, any>
  highlightChanges?: boolean
  showHistory?: boolean
  maxHistoryItems?: number
  theme?: 'dark' | 'light'
}

interface VariableHistory {
  [key: string]: (string | number | boolean | null)[]
}

export default function VariableTracker({
  variables,
  previousVariables = {},
  highlightChanges = true,
  showHistory = true,
  maxHistoryItems = 3,
  theme = 'dark',
}: VariableTrackerProps) {
  const [history, setHistory] = useState<VariableHistory>({})
  const [animatingVars, setAnimatingVars] = useState<Set<string>>(new Set())

  // Track history when variables change
  useEffect(() => {
    const newHistory: VariableHistory = { ...history }

    Object.entries(variables).forEach(([key, value]) => {
      if (!newHistory[key]) {
        newHistory[key] = []
      }

      const lastValue = newHistory[key][newHistory[key].length - 1]
      if (lastValue !== value) {
        newHistory[key] = [...newHistory[key], value].slice(-maxHistoryItems)

        // Trigger animation
        setAnimatingVars((prev) => new Set([...prev, key]))
        setTimeout(() => {
          setAnimatingVars((prev) => {
            const next = new Set(prev)
            next.delete(key)
            return next
          })
        }, 500)
      }
    })

    setHistory(newHistory)
  }, [variables])

  const hasChanged = (key: string): boolean => {
    if (!highlightChanges) return false
    return previousVariables[key] !== variables[key]
  }

  const formatValue = (value: any, truncate = true): string => {
    if (value === null) return 'null'
    if (value === undefined) return 'undefined'
    if (typeof value === 'string') return `"${value}"`
    if (Array.isArray(value)) {
      const full = `[${value.map(v => typeof v === 'object' ? JSON.stringify(v) : String(v)).join(', ')}]`
      if (truncate && full.length > 30) return full.slice(0, 27) + '...'
      return full
    }
    if (typeof value === 'object') {
      const full = JSON.stringify(value)
      if (truncate && full.length > 30) return full.slice(0, 27) + '...'
      return full
    }
    return String(value)
  }

  const getTypeColor = (value: any): string => {
    if (value === null || value === undefined) {
      return theme === 'dark' ? 'text-gray-400' : 'text-gray-500'
    }
    if (typeof value === 'number') {
      return theme === 'dark' ? 'text-blue-400' : 'text-blue-600'
    }
    if (typeof value === 'string') {
      return theme === 'dark' ? 'text-green-400' : 'text-green-600'
    }
    if (typeof value === 'boolean') {
      return theme === 'dark' ? 'text-purple-400' : 'text-purple-600'
    }
    if (Array.isArray(value)) {
      return theme === 'dark' ? 'text-orange-400' : 'text-orange-600'
    }
    return theme === 'dark' ? 'text-yellow-400' : 'text-yellow-600'
  }

  const variableKeys = Object.keys(variables)

  if (variableKeys.length === 0) {
    return (
      <div
        className={`rounded-lg p-4 ${
          theme === 'dark' ? 'bg-[#2d2d2d]' : 'bg-gray-100'
        }`}
      >
        <h3
          className={`text-sm font-semibold mb-2 ${
            theme === 'dark' ? 'text-gray-300' : 'text-gray-700'
          }`}
        >
          Variables
        </h3>
        <p
          className={`text-sm italic ${
            theme === 'dark' ? 'text-gray-500' : 'text-gray-400'
          }`}
        >
          No variables in scope
        </p>
      </div>
    )
  }

  return (
    <div
      className={`rounded-lg p-4 ${
        theme === 'dark' ? 'bg-[#2d2d2d]' : 'bg-gray-100'
      }`}
    >
      <h3
        className={`text-sm font-semibold mb-3 flex items-center ${
          theme === 'dark' ? 'text-gray-300' : 'text-gray-700'
        }`}
      >
        <svg
          className="w-4 h-4 mr-2"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4"
          />
        </svg>
        Variables
      </h3>

      <div className="grid grid-cols-1 gap-2">
        {variableKeys.map((key) => {
          const value = variables[key]
          const changed = hasChanged(key)
          const isAnimating = animatingVars.has(key)
          const varHistory = history[key] || []

          return (
            <div
              key={key}
              className={`
                p-3 rounded-lg border transition-all duration-300
                ${
                  changed
                    ? theme === 'dark'
                      ? 'border-yellow-500/50 bg-yellow-500/10'
                      : 'border-yellow-400 bg-yellow-50'
                    : theme === 'dark'
                    ? 'border-gray-700 bg-[#1e1e1e]'
                    : 'border-gray-200 bg-white'
                }
                ${isAnimating ? 'scale-105 shadow-lg' : 'scale-100'}
              `}
            >
              {/* Variable name and current value */}
              <div className="flex items-start justify-between gap-2 min-w-0">
                <span
                  className={`font-mono text-sm font-medium shrink-0 ${
                    theme === 'dark' ? 'text-pink-400' : 'text-pink-600'
                  }`}
                >
                  {key}
                </span>
                <span
                  className={`font-mono text-sm font-bold text-right break-all ${getTypeColor(value)} ${
                    isAnimating ? 'animate-pulse' : ''
                  }`}
                  title={formatValue(value, false)}
                >
                  {formatValue(value)}
                </span>
              </div>

              {/* History */}
              {showHistory && varHistory.length > 1 && (
                <div
                  className={`mt-2 pt-2 border-t ${
                    theme === 'dark' ? 'border-gray-700' : 'border-gray-200'
                  }`}
                >
                  <div className="flex items-center space-x-2 overflow-x-auto">
                    {varHistory.slice(0, -1).map((histValue, idx) => (
                      <span
                        key={idx}
                        className={`
                          font-mono text-xs px-2 py-1 rounded line-through
                          ${
                            theme === 'dark'
                              ? 'bg-gray-800 text-gray-500'
                              : 'bg-gray-100 text-gray-400'
                          }
                        `}
                      >
                        {formatValue(histValue)}
                      </span>
                    ))}
                    <svg
                      className={`w-4 h-4 flex-shrink-0 ${
                        theme === 'dark' ? 'text-gray-500' : 'text-gray-400'
                      }`}
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M13 7l5 5m0 0l-5 5m5-5H6"
                      />
                    </svg>
                  </div>
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
