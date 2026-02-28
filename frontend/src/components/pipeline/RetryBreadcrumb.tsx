'use client'

import React, { useState, useEffect } from 'react'
import Link from 'next/link'

interface RunInfo {
  id: string
  run_number: number
  retry_depth?: number
  retry_from_stage?: string | null
  parent_run_id?: string | null
}

interface RetryBreadcrumbProps {
  currentRunId: string
  currentRunNumber: number
  parentRunId?: string | null
  retryDepth?: number
}

export function RetryBreadcrumb({
  currentRunId,
  currentRunNumber,
  parentRunId,
  retryDepth = 0
}: RetryBreadcrumbProps) {
  const [retryChain, setRetryChain] = useState<RunInfo[]>([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!parentRunId) {
      // No parent, this is the original run
      setRetryChain([])
      return
    }

    // Fetch the retry chain by walking up parent_run_id
    const fetchRetryChain = async () => {
      setLoading(true)
      try {
        const chain: RunInfo[] = []
        let currentParentId: string | null = parentRunId

        // Walk up the parent chain (max depth to prevent infinite loops)
        while (currentParentId && chain.length < 10) {
          const response = await fetch(`/api/observability/runs/${currentParentId}`)
          if (!response.ok) break

          const run: RunInfo = await response.json()
          chain.unshift(run) // Add to beginning to maintain order

          currentParentId = run.parent_run_id || null
        }

        setRetryChain(chain)
      } catch (err) {
        console.error('Error fetching retry chain:', err)
      } finally {
        setLoading(false)
      }
    }

    fetchRetryChain()
  }, [parentRunId])

  // Don't show breadcrumb if this is not a retry
  if (!parentRunId && retryDepth === 0) {
    return null
  }

  if (loading) {
    return (
      <div className="text-sm text-gray-500">
        Loading retry chain...
      </div>
    )
  }

  return (
    <nav className="text-sm mb-4">
      <div className="flex items-center gap-2 flex-wrap">
        <span className="text-gray-500">Retry Chain:</span>
        
        {/* Original run */}
        {retryChain.length > 0 && (
          <>
            <Link
              href={`/pipeline/runs/${retryChain[0].id}`}
              className="text-blue-600 hover:text-blue-800 font-medium"
            >
              Original Run #{retryChain[0].run_number}
            </Link>
          </>
        )}

        {/* Retry runs in chain */}
        {retryChain.slice(1).map((run, index) => (
          <React.Fragment key={run.id}>
            <span className="text-gray-400">→</span>
            <Link
              href={`/pipeline/runs/${run.id}`}
              className="text-blue-600 hover:text-blue-800 font-medium"
            >
              Retry #{index + 1}
              {run.retry_from_stage && (
                <span className="text-gray-500 text-xs ml-1">
                  (from {run.retry_from_stage.replace(/_/g, ' ')})
                </span>
              )}
            </Link>
          </React.Fragment>
        ))}

        {/* Current run */}
        {retryChain.length > 0 && (
          <>
            <span className="text-gray-400">→</span>
            <span className="text-gray-900 font-semibold">
              Current Run #{currentRunNumber}
            </span>
          </>
        )}

        {/* Retry depth badge */}
        {retryDepth > 0 && (
          <span className="ml-2 px-2 py-0.5 bg-yellow-100 text-yellow-700 rounded-full text-xs font-medium">
            Depth: {retryDepth}
          </span>
        )}
      </div>
    </nav>
  )
}
