/**
 * Types for Pipeline Observability Dashboard
 */

export interface PipelineRun {
  id: string
  process_id: string | null
  run_number: number
  topology: string
  status: 'pending' | 'running' | 'success' | 'failed' | 'cancelled' | 'awaiting_review'
  started_at: string | null
  finished_at: string | null
  duration_ms: number | null
  error_message: string | null
  error_traceback?: string | null
  retry_from_stage: string | null
  parent_run_id: string | null
  retry_depth?: number
  question_text?: string | null
  template_type?: string | null
  stages_completed?: number
  total_stages?: number
  // Cost and token tracking (rolled up from stages)
  total_cost_usd?: number
  total_tokens?: number
  total_llm_calls?: number
  config_snapshot?: Record<string, unknown>
  final_state_summary?: Record<string, unknown>
  stages?: StageExecution[]
  child_runs?: PipelineRunSummary[]
}

export interface PipelineRunSummary {
  id: string
  run_number: number
  status: string
  retry_from_stage: string | null
  started_at: string | null
}

export interface StageExecution {
  id: string
  stage_name: string
  stage_order: number
  status: 'pending' | 'running' | 'success' | 'failed' | 'skipped' | 'degraded'
  started_at: string | null
  finished_at: string | null
  duration_ms: number | null
  model_id: string | null
  prompt_tokens: number | null
  completion_tokens: number | null
  total_tokens: number | null
  estimated_cost_usd: number | null
  latency_ms: number | null
  error_message: string | null
  error_traceback?: string | null
  retry_count: number
  validation_passed: boolean | null
  validation_score: number | null
  validation_errors?: string[] | null
  checkpoint_id?: string | null  // LangGraph checkpoint_id for retry functionality
  run_id?: string  // Parent run ID (always set for real stages, set for synthetic sub-stages)
  input_snapshot?: Record<string, unknown>
  output_snapshot?: Record<string, unknown>
  input_state_keys?: string[]
  output_state_keys?: string[]
  logs?: ExecutionLog[]
}

export interface ExecutionLog {
  id: string
  stage_execution_id: string | null
  level: 'debug' | 'info' | 'warn' | 'error'
  message: string
  timestamp: string
  metadata?: Record<string, unknown>
}

export interface AgentInfo {
  id: string
  display_name: string
  description: string | null
  category: string | null
  default_model: string | null
  default_temperature: number | null
  default_max_tokens: number | null
  typical_inputs: string[] | null
  typical_outputs: string[] | null
  icon: string | null
  color: string | null
}

export interface GraphNode {
  id: string
  type: string
  data: {
    id: string
    displayName: string
    category: string | null
    icon: string | null
    color: string | null
    inputs: string[] | null
    outputs: string[] | null
  }
  position?: { x: number; y: number }
}

export interface GraphEdge {
  id: string
  source: string
  target: string
  type: string
}

export interface RunAnalytics {
  period_days: number
  total_runs: number
  successful_runs: number
  success_rate_percent: number
  average_duration_ms: number
  runs_by_status: Record<string, number>
  runs_by_topology: Record<string, number>
}

export interface AgentAnalytics {
  period_days: number
  agents: {
    agent_name: string
    total_executions: number
    successful_executions: number
    success_rate_percent: number
    average_duration_ms: number
    total_tokens: number
    total_cost_usd: number
  }[]
}

// SSE update event types
export interface RunUpdateEvent {
  run_id: string
  status: string
  current_stage: string | null
  stages_completed: number
  total_stages: number
  progress_percent: number
  duration_ms: number | null
  // Aggregate metrics (NEW)
  total_tokens?: number
  total_cost_usd?: number
  // Per-stage data with metrics
  stages: {
    stage_name: string
    status: string
    duration_ms: number | null
    // Per-stage metrics (NEW)
    tokens?: number | null
    cost?: number | null
    model_id?: string | null
  }[]
}

export interface RunCompleteEvent {
  run_id: string
  status: string
  duration_ms: number | null
  error_message: string | null
  // Final metrics (NEW)
  total_tokens?: number
  total_cost_usd?: number
}

// Live step event for streaming reasoning steps (NEW)
export type LiveStepType = 'thought' | 'action' | 'observation' | 'decision'

export interface LiveStep {
  type: LiveStepType
  content: string
  tool?: string
  timestamp?: string | null
}

export interface LiveStepEvent {
  type: 'live_step'
  stage_name: string
  step: LiveStep
}

// Status helpers
export const STATUS_COLORS = {
  pending: { bg: 'bg-gray-200', text: 'text-gray-700', border: 'border-gray-300' },
  running: { bg: 'bg-blue-200', text: 'text-blue-700', border: 'border-blue-400' },
  success: { bg: 'bg-green-200', text: 'text-green-700', border: 'border-green-400' },
  failed: { bg: 'bg-red-200', text: 'text-red-700', border: 'border-red-400' },
  cancelled: { bg: 'bg-yellow-200', text: 'text-yellow-700', border: 'border-yellow-400' },
  skipped: { bg: 'bg-gray-100', text: 'text-gray-500', border: 'border-gray-200' },
  degraded: { bg: 'bg-orange-100', text: 'text-orange-800', border: 'border-orange-300' },
  awaiting_review: { bg: 'bg-purple-200', text: 'text-purple-700', border: 'border-purple-400' },
}

// Category colors - consistent across the application
// These match CATEGORY_INFO in PipelineView.tsx
export const CATEGORY_COLORS: Record<string, string> = {
  input: '#8B5CF6',      // Purple - Input Processing
  routing: '#10B981',    // Green - Routing/Decision making
  decision: '#14B8A6',   // Teal - Decision/Conditional Routing Nodes
  orchestrator: '#7C3AED', // Violet - Orchestrator Agents
  image: '#06B6D4',      // Cyan - Image Processing
  generation: '#F59E0B', // Amber - Content Generation
  validation: '#EF4444', // Red - Validation
  output: '#6366F1',     // Indigo - Output/Final packaging
  react: '#7C3AED',      // Violet - ReAct Multi-step Reasoning Agents
}

// =============================================================================
// Graph Structure API Types (dynamic graph from backend)
// =============================================================================

export interface GraphStructureNode {
  id: string
  name: string
  description: string
  category: 'input' | 'routing' | 'image' | 'generation' | 'validation' | 'output' | 'react' | 'decision' | 'orchestrator'
  toolOrModel: string
  icon: string
  isDecisionNode?: boolean
  isOrchestrator?: boolean
}

export interface GraphStructureEdge {
  from: string
  to: string
  type: 'direct' | 'conditional'
  condition?: string
  conditionValue?: string
  isRetryEdge?: boolean
  isEscalation?: boolean
}

export interface ConditionalFunction {
  name: string
  description: string
  outcomes: string[]
}

export interface GraphStructure {
  topology: string
  preset: string
  nodes: GraphStructureNode[]
  edges: GraphStructureEdge[]
  conditionalFunctions: ConditionalFunction[]
}

// =============================================================================
// Execution Path API Types (actual path taken in a run)
// =============================================================================

export interface ExecutedStage {
  stageName: string
  stageOrder: number
  status: string
  retryCount: number
  executionNumber: number
  durationMs: number | null
  tokens: number
  cost: number
  model: string | null
  startedAt: string | null
  finishedAt: string | null
}

export interface EdgeTaken {
  from: string
  to: string
  type: 'direct' | 'conditional'
  condition: string | null
  isRetryEdge: boolean
}

export interface ConditionalDecision {
  function: string
  decision: string
  confidence?: number
  atStage: string
}

export interface StageWithRetries {
  stageName: string
  executions: number
}

export interface ExecutionPathTotals {
  totalCost: number
  totalTokens: number
  totalDurationMs: number
  retryCount: number
  stagesExecuted: number
  uniqueStages: number
}

export interface ExecutionPath {
  runId: string
  runStatus: string
  executedStages: ExecutedStage[]
  edgesTaken: EdgeTaken[]
  conditionalDecisions: ConditionalDecision[]
  stagesWithRetries: StageWithRetries[]
  totals: ExecutionPathTotals
}

// Extended PipelineRun with aggregated totals
export interface PipelineRunWithTotals extends PipelineRun {
  total_cost_usd?: number
  total_tokens?: number
  total_prompt_tokens?: number
  total_completion_tokens?: number
  total_retries?: number
  stages_completed?: number
  stages_failed?: number
  total_stages?: number
}

// =============================================================================
// ReAct Trace Types (for HAD Orchestrator UI)
// =============================================================================

export type StepType = 'thought' | 'action' | 'observation' | 'decision' | 'error' | 'result'

export interface ReActStep {
  type: StepType
  content: string
  tool?: string
  tool_args?: Record<string, unknown>
  result?: unknown
  duration_ms?: number
  timestamp: string
  metadata?: Record<string, unknown>
}

export interface ReActTrace {
  phase: string
  iterations: number
  max_iterations: number
  steps: ReActStep[]
  final_result?: unknown
  success: boolean
  total_duration_ms: number
  started_at: string
  completed_at?: string
}

// =============================================================================
// HAD Cluster Layout Types (for Unified UI)
// =============================================================================

export interface ClusterDefinition {
  id: string
  name: string
  description?: string
  color: string
  agents: string[]
  layout: 'horizontal' | 'vertical' | 'single'
  showTools?: boolean
  showSubPipeline?: boolean
  showRetryLoop?: boolean
}

export interface HADClusterLayout {
  clusters: ClusterDefinition[]
}

// Zone overlay types for diagram visualization
export interface ZoneOverlayData {
  id: string
  label: string
  zone_type: 'circle' | 'ellipse' | 'bounding_box' | 'polygon' | 'path'
  // Circle/ellipse fields
  x?: number
  y?: number
  radius?: number
  rx?: number
  ry?: number
  rotation?: number
  // Bounding box fields
  width?: number
  height?: number
  // Polygon fields
  points?: [number, number][]
  // Path fields
  d?: string
  // Metadata
  confidence?: number
  hierarchy_level?: number
  parent_label?: string
}

export interface ZoneGroup {
  id: string
  parent: string
  children: string[]
  relationship_type: 'composed_of' | 'subdivided_into' | 'contains' | 'has_part'
}

// Output renderer detail level
export type DetailLevel = 'summary' | 'full'
