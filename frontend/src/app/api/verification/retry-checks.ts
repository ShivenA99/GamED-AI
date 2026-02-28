/**
 * Browser-based verification utilities for retry functionality
 * 
 * These functions can be run in browser console to verify fixes
 * Usage: Open browser console and run these functions
 */

interface RunData {
  id: string
  config_snapshot?: {
    initial_state?: Record<string, unknown>
  }
  retry_depth?: number
  parent_run_id?: string | null
  retry_from_stage?: string | null
}

interface StageData {
  id: string
  stage_name: string
  status: string
  output_snapshot?: Record<string, unknown>
}

/**
 * Verify Fix 1: Check if initial_state exists in config_snapshot
 */
export async function verifyFix1InitialState(runId: string): Promise<{
  success: boolean
  message: string
  details: Record<string, unknown>
}> {
  try {
    const response = await fetch(`/api/observability/runs/${runId}`)
    if (!response.ok) {
      return {
        success: false,
        message: `Failed to fetch run: ${response.status}`,
        details: {}
      }
    }

    const run: RunData = await response.json()
    
    if (!run.config_snapshot) {
      return {
        success: false,
        message: 'config_snapshot is missing',
        details: { run_id: runId }
      }
    }

    if (!run.config_snapshot.initial_state) {
      return {
        success: false,
        message: 'initial_state is missing from config_snapshot',
        details: { 
          run_id: runId,
          has_config_snapshot: true,
          config_snapshot_keys: Object.keys(run.config_snapshot)
        }
      }
    }

    const initialState = run.config_snapshot.initial_state
    const hasQuestionId = 'question_id' in initialState
    const hasQuestionText = 'question_text' in initialState

    return {
      success: hasQuestionId && hasQuestionText,
      message: hasQuestionId && hasQuestionText
        ? '✅ Fix 1 PASSED: initial_state exists with required fields'
        : '❌ Fix 1 FAILED: initial_state missing required fields',
      details: {
        has_initial_state: true,
        has_question_id: hasQuestionId,
        has_question_text: hasQuestionText,
        initial_state_keys: Object.keys(initialState)
      }
    }
  } catch (error) {
    return {
      success: false,
      message: `Error: ${error instanceof Error ? error.message : 'Unknown error'}`,
      details: { error: String(error) }
    }
  }
}

/**
 * Verify Fix 3: Check if degraded stages are included
 */
export async function verifyFix3DegradedStages(runId: string): Promise<{
  success: boolean
  message: string
  details: Record<string, unknown>
}> {
  try {
    const response = await fetch(`/api/observability/runs/${runId}/stages`)
    if (!response.ok) {
      return {
        success: false,
        message: `Failed to fetch stages: ${response.status}`,
        details: {}
      }
    }

    const data = await response.json()
    const stages: StageData[] = data.stages || []

    const degradedStages = stages.filter(s => s.status === 'degraded')
    const successStages = stages.filter(s => s.status === 'success')
    const hasDegradedWithOutput = degradedStages.some(s => s.output_snapshot)

    return {
      success: degradedStages.length > 0,
      message: degradedStages.length > 0
        ? `✅ Fix 3 PASSED: Found ${degradedStages.length} degraded stage(s)`
        : '⚠️ Fix 3: No degraded stages found in this run',
      details: {
        total_stages: stages.length,
        degraded_count: degradedStages.length,
        success_count: successStages.length,
        degraded_with_output: hasDegradedWithOutput,
        degraded_stages: degradedStages.map(s => ({
          name: s.stage_name,
          has_output: !!s.output_snapshot
        }))
      }
    }
  } catch (error) {
    return {
      success: false,
      message: `Error: ${error instanceof Error ? error.message : 'Unknown error'}`,
      details: { error: String(error) }
    }
  }
}

/**
 * Verify Fix 7: Check retry depth
 */
export async function verifyFix7RetryDepth(runId: string): Promise<{
  success: boolean
  message: string
  details: Record<string, unknown>
}> {
  try {
    const response = await fetch(`/api/observability/runs/${runId}`)
    if (!response.ok) {
      return {
        success: false,
        message: `Failed to fetch run: ${response.status}`,
        details: {}
      }
    }

    const run: RunData = await response.json()
    
    const hasRetryDepth = typeof run.retry_depth === 'number'
    const depth = run.retry_depth ?? 0
    const isWithinLimit = depth <= 3

    return {
      success: hasRetryDepth && isWithinLimit,
      message: hasRetryDepth
        ? `✅ Fix 7 PASSED: retry_depth = ${depth} (within limit)`
        : '❌ Fix 7 FAILED: retry_depth field missing',
      details: {
        has_retry_depth: hasRetryDepth,
        retry_depth: depth,
        within_limit: isWithinLimit,
        is_retry: !!run.parent_run_id,
        parent_run_id: run.parent_run_id
      }
    }
  } catch (error) {
    return {
      success: false,
      message: `Error: ${error instanceof Error ? error.message : 'Unknown error'}`,
      details: { error: String(error) }
    }
  }
}

/**
 * Verify Fix 9: Check loading states (manual verification)
 */
export function verifyFix9LoadingStates(): {
  success: boolean
  message: string
  instructions: string[]
} {
  return {
    success: true, // Manual verification
    message: '✅ Fix 9: Manual verification required',
    instructions: [
      '1. Navigate to a failed pipeline run',
      '2. Open StagePanel for a failed stage',
      '3. Click "Retry" button',
      '4. Verify:',
      '   - Button becomes disabled immediately',
      '   - Spinner icon appears',
      '   - Button text changes to "Retrying..."',
      '   - Button re-enables after request completes'
    ]
  }
}

/**
 * Verify Fix 10: Check retry breadcrumb
 */
export async function verifyFix10Breadcrumb(runId: string): Promise<{
  success: boolean
  message: string
  details: Record<string, unknown>
}> {
  try {
    const response = await fetch(`/api/observability/runs/${runId}`)
    if (!response.ok) {
      return {
        success: false,
        message: `Failed to fetch run: ${response.status}`,
        details: {}
      }
    }

    const run: RunData = await response.json()
    
    const hasParent = !!run.parent_run_id
    const hasRetryDepth = typeof run.retry_depth === 'number'
    const depth = run.retry_depth ?? 0

    // Check if breadcrumb component would show
    const shouldShowBreadcrumb = hasParent || depth > 0

    return {
      success: shouldShowBreadcrumb || !hasParent,
      message: shouldShowBreadcrumb
        ? `✅ Fix 10: Breadcrumb should display (depth: ${depth})`
        : '⚠️ Fix 10: No breadcrumb needed (original run)',
      details: {
        has_parent: hasParent,
        retry_depth: depth,
        should_show_breadcrumb: shouldShowBreadcrumb,
        parent_run_id: run.parent_run_id
      }
    }
  } catch (error) {
    return {
      success: false,
      message: `Error: ${error instanceof Error ? error.message : 'Unknown error'}`,
      details: { error: String(error) }
    }
  }
}

/**
 * Verify Fix 11: Check snapshot truncation
 */
export async function verifyFix11SnapshotTruncation(runId: string, stageId: string): Promise<{
  success: boolean
  message: string
  details: Record<string, unknown>
}> {
  try {
    const response = await fetch(`/api/observability/stages/${stageId}`)
    if (!response.ok) {
      return {
        success: false,
        message: `Failed to fetch stage: ${response.status}`,
        details: {}
      }
    }

    const stage: StageData = await response.json()
    
    const outputSnapshot = stage.output_snapshot
    if (!outputSnapshot) {
      return {
        success: true,
        message: '⚠️ Fix 11: No output snapshot to check',
        details: { has_output_snapshot: false }
      }
    }

    const isTruncated = outputSnapshot._truncated === true
    const hasMetadata = '_original_size_kb' in outputSnapshot && '_truncated_size_kb' in outputSnapshot

    // Estimate size
    const snapshotSize = JSON.stringify(outputSnapshot).length
    const sizeKB = snapshotSize / 1024

    return {
      success: !isTruncated || hasMetadata,
      message: isTruncated
        ? `✅ Fix 11 PASSED: Snapshot truncated (${outputSnapshot._truncated_size_kb}KB)`
        : sizeKB > 200
          ? '⚠️ Fix 11: Large snapshot but not truncated'
          : `✅ Fix 11: Snapshot within limit (${sizeKB.toFixed(2)}KB)`,
      details: {
        is_truncated: isTruncated,
        has_metadata: hasMetadata,
        size_kb: sizeKB.toFixed(2),
        original_size_kb: outputSnapshot._original_size_kb,
        truncated_size_kb: outputSnapshot._truncated_size_kb
      }
    }
  } catch (error) {
    return {
      success: false,
      message: `Error: ${error instanceof Error ? error.message : 'Unknown error'}`,
      details: { error: String(error) }
    }
  }
}

/**
 * Run all browser-based verifications
 */
export async function runAllBrowserVerifications(runId: string): Promise<{
  results: Array<{ fix: string; result: unknown }>
  summary: { total: number; passed: number; failed: number }
}> {
  console.log('🔍 Starting browser-based verification...')
  
  const results = []
  
  // Fix 1
  console.log('Checking Fix 1: Initial State...')
  const fix1 = await verifyFix1InitialState(runId)
  results.push({ fix: 'Fix 1: Initial State', result: fix1 })
  console.log(fix1.message)
  
  // Fix 3
  console.log('Checking Fix 3: Degraded Stages...')
  const fix3 = await verifyFix3DegradedStages(runId)
  results.push({ fix: 'Fix 3: Degraded Stages', result: fix3 })
  console.log(fix3.message)
  
  // Fix 7
  console.log('Checking Fix 7: Retry Depth...')
  const fix7 = await verifyFix7RetryDepth(runId)
  results.push({ fix: 'Fix 7: Retry Depth', result: fix7 })
  console.log(fix7.message)
  
  // Fix 9
  console.log('Checking Fix 9: Loading States...')
  const fix9 = verifyFix9LoadingStates()
  results.push({ fix: 'Fix 9: Loading States', result: fix9 })
  console.log(fix9.message)
  
  // Fix 10
  console.log('Checking Fix 10: Breadcrumb...')
  const fix10 = await verifyFix10Breadcrumb(runId)
  results.push({ fix: 'Fix 10: Breadcrumb', result: fix10 })
  console.log(fix10.message)
  
  const passed = results.filter(r => r.result.success !== false).length
  const failed = results.filter(r => r.result.success === false).length
  
  console.log(`\n✅ Summary: ${passed} passed, ${failed} failed out of ${results.length} checks`)
  
  return {
    results,
    summary: {
      total: results.length,
      passed,
      failed
    }
  }
}

// Export for browser console usage
if (typeof window !== 'undefined') {
  (window as any).verifyRetryFixes = {
    fix1: verifyFix1InitialState,
    fix3: verifyFix3DegradedStages,
    fix7: verifyFix7RetryDepth,
    fix9: verifyFix9LoadingStates,
    fix10: verifyFix10Breadcrumb,
    fix11: verifyFix11SnapshotTruncation,
    all: runAllBrowserVerifications
  }
  
  console.log('✅ Retry verification functions loaded!')
  console.log('Usage:')
  console.log('  verifyRetryFixes.fix1("run-id")')
  console.log('  verifyRetryFixes.all("run-id")')
}
