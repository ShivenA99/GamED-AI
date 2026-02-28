/**
 * Unified Stage Status Resolution
 *
 * This module provides a single source of truth for stage status resolution,
 * addressing GAP-1 from the Observability UI Audit.
 *
 * ## Problem Statement
 *
 * Previously, stage status was determined differently across components:
 * - PipelineView used stageStatusMap OR executionPath OR run.status inference
 * - TimelineView used stage.status directly
 * - ClusterView used stage.status directly
 * - Edge coloring used its own inference logic
 *
 * This led to potential inconsistencies where the same stage could show
 * different statuses in different views.
 *
 * ## Resolution Approach
 *
 * We establish a clear priority order for status sources:
 *
 * ### Priority 1: Direct Stage Data (stageStatusMap)
 * The stages[] array from GET /runs/{id} contains actual execution records
 * from the database. This is the most authoritative source because:
 * - It reflects real execution state
 * - It includes timing, tokens, validation results
 * - It's the same data shown in StagePanel details
 *
 * ### Priority 2: Execution Path (executionPath.executedStages)
 * The execution path from GET /runs/{id}/execution-path tells us which
 * stages were actually executed. If a stage is in executedStages but not
 * in stageStatusMap, it means:
 * - The stage ran but wasn't recorded (instrumentation gap)
 * - We can infer it completed if the run succeeded
 *
 * ### Priority 3: Run Status Inference
 * If a stage has no direct data AND isn't in execution path, we fall back to:
 * - If run.status === 'success': The stage likely succeeded (pipeline completed)
 * - Otherwise: The stage is 'pending' (hasn't run yet)
 *
 * This is the LEAST reliable source and we flag it as inferred.
 *
 * ## Usage
 *
 * ```typescript
 * import { resolveStageStatus, createStatusResolver } from '@/lib/stageStatus'
 *
 * // Simple usage
 * const result = resolveStageStatus('game_planner', {
 *   stageStatusMap,
 *   executionPath,
 *   runStatus: run.status
 * })
 *
 * // Use the status
 * const color = STATUS_COLORS[result.status]
 *
 * // Check if inferred (for warning display)
 * if (result.isInferred) {
 *   console.warn(`Status for ${stageName} was inferred from ${result.source}`)
 * }
 * ```
 *
 * ## Design Decisions
 *
 * 1. **Always return a status**: Never return undefined. Default to 'pending'.
 * 2. **Track source attribution**: Every result includes where the status came from.
 * 3. **Flag inferred statuses**: Components can show warnings for inferred data.
 * 4. **Include confidence level**: High (direct), medium (execution path), low (inference).
 * 5. **Memoization-friendly**: Pure function, deterministic output.
 */

import { StageExecution, ExecutionPath } from '@/components/pipeline/types'

// Valid stage statuses
export type StageStatus = 'pending' | 'running' | 'success' | 'failed' | 'skipped' | 'degraded'

// Source of the status determination
export type StatusSource =
  | 'stage_data'       // From stages[] array (highest confidence)
  | 'execution_path'   // From executionPath.executedStages
  | 'run_inference'    // Inferred from run.status
  | 'default'          // No data available, using default

// Confidence level for the status
export type StatusConfidence = 'high' | 'medium' | 'low'

// Result of status resolution
export interface StageStatusResult {
  /** The resolved status */
  status: StageStatus
  /** Where the status was determined from */
  source: StatusSource
  /** Confidence level */
  confidence: StatusConfidence
  /** Whether this status was inferred (not from direct data) */
  isInferred: boolean
  /** The full stage data if available */
  stageData?: StageExecution
  /** Additional context about the resolution */
  reasoning: string
}

// Input context for status resolution
export interface StatusResolutionContext {
  /** Map of stage name to stage execution data */
  stageStatusMap: Record<string, StageExecution>
  /** Execution path data (optional) */
  executionPath?: ExecutionPath | null
  /** Overall run status */
  runStatus: string
  /** Whether the run is still in progress */
  isRunning?: boolean
}

/**
 * Resolve the status of a single stage using the unified priority system.
 *
 * @param stageName - The name of the stage to resolve
 * @param context - The resolution context with all data sources
 * @returns StageStatusResult with status, source, and confidence
 */
export function resolveStageStatus(
  stageName: string,
  context: StatusResolutionContext
): StageStatusResult {
  const { stageStatusMap, executionPath, runStatus, isRunning } = context

  // Priority 1: Check stageStatusMap (direct stage data)
  const stageData = stageStatusMap[stageName]
  if (stageData) {
    return {
      status: stageData.status as StageStatus,
      source: 'stage_data',
      confidence: 'high',
      isInferred: false,
      stageData,
      reasoning: `Direct stage data available with status '${stageData.status}'`
    }
  }

  // Priority 2: Check execution path
  const wasExecuted = executionPath?.executedStages?.some(
    s => s.stageName === stageName
  )

  if (wasExecuted) {
    // Stage was executed but no detailed data
    // Infer success if run succeeded, otherwise unknown
    const inferredStatus: StageStatus =
      runStatus === 'success' || runStatus === 'completed' ? 'success' :
      runStatus === 'failed' ? 'failed' :
      'pending'

    return {
      status: inferredStatus,
      source: 'execution_path',
      confidence: 'medium',
      isInferred: true,
      reasoning: `Stage appears in execution path but no detailed data. Run status is '${runStatus}'.`
    }
  }

  // Priority 3: Run status inference
  // Only infer success if run completed successfully
  if (runStatus === 'success' || runStatus === 'completed') {
    return {
      status: 'success',
      source: 'run_inference',
      confidence: 'low',
      isInferred: true,
      reasoning: `No stage data or execution path entry. Inferred success because run completed successfully.`
    }
  }

  // Default: Stage hasn't run yet
  const defaultStatus: StageStatus = isRunning ? 'pending' : 'pending'

  return {
    status: defaultStatus,
    source: 'default',
    confidence: 'low',
    isInferred: true,
    reasoning: `No data available for stage. Run status is '${runStatus}'.`
  }
}

/**
 * Create a memoized status resolver for a specific context.
 * Useful when resolving many stages with the same context.
 *
 * @param context - The resolution context
 * @returns A function that resolves status for any stage name
 */
export function createStatusResolver(context: StatusResolutionContext) {
  // Cache results to avoid recomputation
  const cache = new Map<string, StageStatusResult>()

  return function resolve(stageName: string): StageStatusResult {
    if (cache.has(stageName)) {
      return cache.get(stageName)!
    }

    const result = resolveStageStatus(stageName, context)
    cache.set(stageName, result)
    return result
  }
}

/**
 * Batch resolve status for multiple stages.
 * More efficient than resolving one at a time.
 *
 * @param stageNames - Array of stage names to resolve
 * @param context - The resolution context
 * @returns Map of stage name to status result
 */
export function resolveMultipleStageStatuses(
  stageNames: string[],
  context: StatusResolutionContext
): Map<string, StageStatusResult> {
  const resolver = createStatusResolver(context)
  const results = new Map<string, StageStatusResult>()

  for (const name of stageNames) {
    results.set(name, resolver(name))
  }

  return results
}

/**
 * Get just the status string (convenience function).
 * Use when you only need the status, not the full result.
 */
export function getStageStatus(
  stageName: string,
  context: StatusResolutionContext
): StageStatus {
  return resolveStageStatus(stageName, context).status
}

/**
 * Check if a stage status was inferred rather than direct data.
 */
export function isStatusInferred(
  stageName: string,
  context: StatusResolutionContext
): boolean {
  return resolveStageStatus(stageName, context).isInferred
}

/**
 * Build a stageStatusMap from a stages array.
 * Utility for converting API response to the map format.
 */
export function buildStageStatusMap(
  stages: StageExecution[]
): Record<string, StageExecution> {
  const map: Record<string, StageExecution> = {}
  for (const stage of stages) {
    map[stage.stage_name] = stage
  }
  return map
}

/**
 * React hook for using stage status in components.
 * Memoizes the resolver for performance.
 */
export function useStageStatusResolver(context: StatusResolutionContext) {
  // This would use useMemo in actual React code
  // For now, just create the resolver
  return createStatusResolver(context)
}

// Export types for consumers
export type { StageExecution, ExecutionPath }
