# Observability UI Audit Report

**Date:** February 2026
**Scope:** Pipeline Dashboard - Timeline, Graph, Cluster Views
**Focus:** Consistency, Accuracy, Agentic Workflow Visibility

---

## Executive Summary

Comprehensive audit of the pipeline observability UI reveals **23 gaps** across 5 categories:
- **Data Consistency Issues** (7): Multiple sources of truth create divergent displays
- **Missing Visualizations** (6): Backend data not surfaced in UI
- **Agentic Workflow Gaps** (5): Limited visibility into multi-turn reasoning
- **Real-time Limitations** (3): SSE events missing critical metrics
- **Edge Case Handling** (2): Silent failures and invalid states

---

## Part 1: Current Architecture Analysis

### View Components

| Component | Purpose | Data Source |
|-----------|---------|-------------|
| **TimelineView** | Gantt-style duration bars | `stages[]` array |
| **PipelineView/Graph** | DAG visualization with React Flow | `graphStructure` + `executionPath` APIs |
| **ClusterView** | Grouped agent display for HAD | `stages[]` + cluster definitions |
| **StagePanel** | Detailed stage inspection | Single `StageExecution` object |
| **LivePipelineView** | Real-time progress | SSE stream + polling |

### Data Flow

```
Backend DB
    │
    ├─ GET /runs/{id}           → run + stages[] array
    ├─ GET /graph/structure     → static topology (nodes, edges)
    ├─ GET /runs/{id}/exec-path → execution path taken
    └─ SSE /runs/{id}/stream    → real-time status updates
                │
                ▼
    ┌─────────────────────────────────────────────┐
    │              Frontend State                  │
    │  ┌─────────┐  ┌─────────────┐  ┌─────────┐ │
    │  │   run   │  │   stages[]  │  │execPath │ │
    │  └────┬────┘  └──────┬──────┘  └────┬────┘ │
    │       │              │              │       │
    │       ▼              ▼              ▼       │
    │  ┌─────────────────────────────────────┐   │
    │  │         Status Inference            │   │
    │  │  (3 sources → potential conflicts)  │   │
    │  └─────────────────────────────────────┘   │
    └─────────────────────────────────────────────┘
```

---

## Part 2: Gap Analysis

### Category 1: Data Consistency Issues (7 gaps)

#### GAP-1: Multiple Sources of Truth for Stage Status
**Severity:** High
**Location:** `PipelineView.tsx` lines 945, 1180-1186, 1444

**Problem:** Stage status is inferred from 3 different sources:
1. `stageStatusMap[agentId]` - from stages array
2. `executionPath.executedStages` - from execution path API
3. Inference from `run.status` - when no direct data

**Impact:** Same stage can show different status in Graph vs Timeline vs StagePanel

**Current Code:**
```typescript
// PipelineView.tsx:945 - Inference fallback
if (!stage && run.status === 'success') {
  agentStatus = 'success'  // Inferred - may not be accurate
}

// PipelineView.tsx:1444 - Edge coloring uses different logic
const toStatus = toStage?.status || (
  run.status === 'success' && executedStageNames.has(edge.to)
    ? 'success' : 'pending'
)
```

**Fix:** Create single `getStageStatus()` utility used by all components.

---

#### GAP-2: Cost/Token Values from Multiple Sources
**Severity:** Medium
**Location:** `PipelineView.tsx` header display

**Problem:** Cost displayed as:
```typescript
executionPath?.totals?.totalCost ?? runWithTotals.total_cost_usd
```
These can diverge if calculation differs between APIs.

**Fix:** Use single authoritative source (prefer run-level denormalized values).

---

#### GAP-3: Stage Count Mismatch
**Severity:** Medium
**Location:** `PipelineView.tsx` lines 805-807

**Problem:** Progress bar uses `graphStructure?.nodes.length` OR `GRAPH_LAYOUT.flat().length`.
Backend graph may have different node count than hardcoded layout.

**Fix:** Always use `graphStructure.nodes.length` when available; remove hardcoded fallback.

---

#### GAP-4: Retry Edge Definition Conflict
**Severity:** Low
**Location:** `PipelineView.tsx` line 1449

**Problem:** Retry edges determined by both:
- `edge.isRetryEdge` from graph structure API
- `stage.retry_count > 0` on stage data

No reconciliation if they contradict.

---

#### GAP-5: Timeline Timestamp Validation Missing
**Severity:** Medium
**Location:** `TimelineView.tsx` lines 67-74

**Problem:** No validation that `started_at <= finished_at`. Negative durations possible if timestamps are incorrect.

**Current:**
```typescript
const startTime = stage.started_at ? new Date(stage.started_at).getTime() : 0
const endTime = stage.finished_at ? new Date(stage.finished_at).getTime() : maxTime
// No validation: endTime could be < startTime
```

---

#### GAP-6: Hardcoded Layout vs Dynamic Graph
**Severity:** Medium
**Location:** `PipelineView.tsx` GRAPH_LAYOUT constant

**Problem:** Multiple hardcoded layouts (GRAPH_LAYOUT, HAD_GRAPH_LAYOUT, PHET_GRAPH_LAYOUT) may not match actual backend graph for custom topologies.

**Fix:** Derive layout from `graphStructure` API response instead of hardcoding.

---

#### GAP-7: Execution Path vs Stages Array Divergence
**Severity:** Medium
**Location:** `PipelineView.tsx` lines 719-721

**Problem:** Run can complete successfully but have empty stages array. Currently logs warning but doesn't surface to user.

---

### Category 2: Missing Visualizations (6 gaps)

#### GAP-8: Tool Metrics Not Displayed
**Severity:** High
**Location:** Backend tracks via `ctx.set_tool_metrics()` but not shown in UI

**Backend Data Available:**
```python
# instrumentation.py:1021-1041
self._tool_metrics = {
    "tool_calls": [...],
    "total_tool_calls": N,
    "successful_calls": N,
    "failed_calls": N,
    "total_tool_latency_ms": N
}
```

**UI Status:** Not displayed anywhere. StagePanel only shows LLM metrics.

---

#### GAP-9: ReActTraceViewer Not Integrated
**Severity:** High
**Location:** `ReActTraceViewer.tsx` exists but not used in `StagePanel.tsx`

**Problem:** Full ReAct trace viewer component exists with:
- Thought/Action/Observation/Decision/Error/Result step types
- Tool call arguments and results
- Duration per step
- Collapsible detail views

But it's **never rendered** in StagePanel's `AgentOutputRenderer` for HAD agents.

---

#### GAP-10: No Live Tool Call Streaming
**Severity:** High
**Location:** `LivePipelineView.tsx` SSE handling

**Problem:** SSE events only contain:
```typescript
interface RunUpdateEvent {
  status, current_stage, progress_percent, duration_ms, stages[]
}
```
No tool calls, no reasoning steps, no intermediate outputs.

Users cannot see what agentic agents are "thinking" during execution.

---

#### GAP-11: ClusterView Tools Display Incomplete
**Severity:** Medium
**Location:** `ClusterView.tsx` lines 278-307

**Problem:** `getToolsUsed()` function only extracts tools from:
- `output.detection_trace`
- `output.design_trace`
- `output.zone_detection_metadata.tools_used`

Missing extraction from:
- `output._tool_metrics.tool_calls`
- `output._react_metrics`
- Standard output patterns

---

#### GAP-12: No Iteration/Turn Counter for Agentic Agents
**Severity:** Medium
**Location:** Missing from StagePanel

**Problem:** For multi-turn agents, no display of:
- Current iteration number
- Max iterations allowed
- Token growth across iterations

Backend tracks via `set_react_metrics(iterations, max_iterations, tool_calls, ...)` but UI doesn't show it.

---

#### GAP-13: No Agent Graph Visualization (Langfuse-style)
**Severity:** Medium
**Location:** Missing feature

**Problem:** No visual representation of agent reasoning flow as a graph.
Industry standard (Langfuse, LangSmith) shows agent traces as interactive graphs with:
- Nodes for each reasoning step
- Edges showing flow
- Expandable details per node

---

### Category 3: Agentic Workflow Gaps (5 gaps)

#### GAP-14: No Streaming Reasoning Steps
**Severity:** Critical
**Location:** Missing feature

**Problem:** Users see nothing while agentic agents (zone_planner, game_orchestrator) think.
Only see "running" status, then final output.

**Industry Standard:** Stream Thought → Action → Observation steps in real-time.

---

#### GAP-15: No Sub-Task Visibility
**Severity:** High
**Location:** StagePanel only shows flat input/output

**Problem:** HAD orchestrator agents spawn sub-tasks but UI shows single stage.
No way to see:
- Sub-task breakdown
- Which sub-tasks succeeded/failed
- Sub-task token usage

---

#### GAP-16: No Tool Call History View
**Severity:** High
**Location:** Missing from StagePanel

**Problem:** When agent makes multiple tool calls, no UI to:
- See chronological tool call history
- View arguments passed to each tool
- See results returned
- Identify which call failed

---

#### GAP-17: No Retry Loop Visualization in Graph
**Severity:** Medium
**Location:** Graph view shows retry edges but not retry state

**Problem:** Graph shows edges exist but not:
- How many times loop was traversed
- Token cost per iteration
- What changed between iterations

---

#### GAP-18: No Agent Memory/State View
**Severity:** Low
**Location:** Missing feature

**Problem:** For stateful agents with memory, no way to inspect:
- What's in the agent's memory
- How memory evolved across turns
- Memory retrieval decisions

---

### Category 4: Real-time Limitations (3 gaps)

#### GAP-19: SSE Events Missing Metrics
**Severity:** High
**Location:** `LivePipelineView.tsx` lines 62-80

**Problem:** Live stage updates create minimal objects:
```typescript
{
  id, stage_name, stage_order, status, duration_ms,
  // ALL THESE ARE NULL:
  model_id: null, prompt_tokens: null, completion_tokens: null,
  total_tokens: null, estimated_cost_usd: null, ...
}
```

Requires full refetch on completion to get metrics.

---

#### GAP-20: No Live Cost Accumulator
**Severity:** Medium
**Location:** `LiveTokenCounter.tsx` exists but requires polling

**Problem:** `LiveTokenCounter` polls every 3 seconds. Not true real-time.
SSE events should include running cost total.

---

#### GAP-21: Connection Loss Handling Incomplete
**Severity:** Medium
**Location:** `LivePipelineView.tsx` lines 106-118

**Problem:** On SSE error:
1. Sets `isConnected = false`
2. Waits 2 seconds
3. Refetches full run

No exponential backoff, no max retry limit, no user notification of persistent failure.

---

### Category 5: Edge Case Handling (2 gaps)

#### GAP-22: Silent Image Load Failures
**Severity:** Low
**Location:** `StagePanel.tsx` line 1024-1030

**Problem:** Image load errors hidden via `onError` setting `display: none`.
User sees nothing, no error message.

---

#### GAP-23: Inferred Stages Warning Hidden
**Severity:** Medium
**Location:** `StagePanel.tsx` lines 527-543

**Problem:** Stages with `id.startsWith('inferred-')` show warning banner but:
- No explanation of why stage is inferred
- No action to resolve
- Confusing UX

---

## Part 3: Research Findings - Industry Best Practices

### Sources Consulted
- [Langfuse Agent Graphs](https://langfuse.com/docs/observability/features/agent-graphs)
- [Portkey LLM Observability Guide](https://portkey.ai/blog/the-complete-guide-to-llm-observability/)
- [Datadog LLM Observability](https://www.datadoghq.com/product/llm-observability/)
- [LangSmith Tracing](https://docs.langchain.com/oss/python/langgraph/observability)
- [AI Agent Observability Tools 2026](https://research.aimultiple.com/agentic-monitoring/)

### Key Patterns from Industry Leaders

#### 1. Hierarchical Trace Visualization
**Pattern:** Session → Trace → Span → Event → Generation/Retrieval/Tool Call

**Langfuse Implementation:**
- Agent graphs auto-generated from trace structure
- Nesting inferred from observation timings
- Interactive expansion of each level

**Our Gap:** We have flat stages, no hierarchical nesting.

#### 2. Real-time Streaming
**Pattern:** Stream reasoning steps as they occur

**LangSmith Implementation:**
- WebSocket connection for live traces
- Each Thought/Action/Observation streamed immediately
- Token counter updates in real-time

**Our Gap:** SSE only sends status changes, not reasoning steps.

#### 3. Tool Call Visibility
**Pattern:** Dedicated tool call panel showing:
- Tool name, arguments, result, latency
- Success/failure status
- Retry count per tool

**Portkey Recommendation:**
> "Capture tool name, latency, success/failure status, retry counts, and error categories"

**Our Gap:** tool_metrics tracked but never displayed.

#### 4. Cost Attribution Dimensions
**Pattern:** Connect cost to multiple dimensions:
- Model type
- Provider
- Workspace/User
- Tool vs Generation

**Our Gap:** Only show total cost, no breakdown by dimension.

#### 5. Agent Graph Visualization
**Pattern:** Visual DAG of reasoning flow

**Langfuse Implementation:**
- Nodes for each step type (Thought, Action, etc.)
- Edges showing flow direction
- Color coding by step type
- Expandable node details

**Our Gap:** No agent-level graph, only pipeline-level graph.

---

## Part 4: Recommendations

### Priority 1: Critical (Fix within 1 sprint)

| ID | Gap | Recommendation | Effort |
|----|-----|----------------|--------|
| GAP-10 | No live streaming | Add SSE events for tool calls and reasoning steps | High |
| GAP-8 | Tool metrics hidden | Add Tool Calls tab to StagePanel | Medium |
| GAP-9 | ReActTraceViewer unused | Integrate into StagePanel for HAD agents | Low |
| GAP-14 | No streaming reasoning | Backend: emit step events; Frontend: show live | High |

### Priority 2: High (Fix within 2 sprints)

| ID | Gap | Recommendation | Effort |
|----|-----|----------------|--------|
| GAP-1 | Multiple status sources | Create `getStageStatus()` utility | Medium |
| GAP-15 | No sub-task visibility | Add sub-task panel for orchestrator agents | Medium |
| GAP-16 | No tool call history | Create ToolCallHistory component | Medium |
| GAP-19 | SSE missing metrics | Include token/cost in SSE events | Medium |

### Priority 3: Medium (Backlog)

| ID | Gap | Recommendation | Effort |
|----|-----|----------------|--------|
| GAP-6 | Hardcoded layouts | Derive layouts from graph API | High |
| GAP-12 | No iteration counter | Add iteration display for agentic agents | Low |
| GAP-13 | No agent graph | Build agent-level graph visualization | High |
| GAP-17 | No retry loop viz | Enhance graph to show retry state | Medium |

---

## Part 5: Proposed Architecture Changes

### 1. Enhanced SSE Event Schema

```typescript
// Current (limited)
interface RunUpdateEvent {
  status: string
  current_stage: string
  progress_percent: number
  duration_ms: number
  stages: { stage_name, status, duration_ms }[]
}

// Proposed (comprehensive)
interface EnhancedRunUpdateEvent {
  status: string
  current_stage: string
  progress_percent: number
  duration_ms: number

  // Metrics (NEW)
  total_tokens: number
  total_cost_usd: number

  // Stages with metrics (ENHANCED)
  stages: {
    stage_name: string
    status: string
    duration_ms: number
    tokens?: number
    cost?: number
  }[]

  // Live reasoning steps (NEW)
  live_step?: {
    stage_name: string
    step_type: 'thought' | 'action' | 'observation' | 'decision'
    content: string
    tool?: string
    timestamp: string
  }

  // Tool call events (NEW)
  tool_call?: {
    stage_name: string
    tool_name: string
    arguments: Record<string, unknown>
    status: 'started' | 'completed' | 'failed'
    result?: unknown
    latency_ms?: number
  }
}
```

### 2. Unified Status Resolution

```typescript
// New utility: frontend/src/lib/stageStatus.ts
export function getStageStatus(
  stageName: string,
  stages: StageExecution[],
  executionPath: ExecutionPath | null,
  runStatus: string
): StageStatus {
  // Priority 1: Direct stage data
  const stage = stages.find(s => s.stage_name === stageName)
  if (stage) return stage.status

  // Priority 2: Execution path
  if (executionPath?.executedStages.includes(stageName)) {
    return 'success'  // Was executed
  }

  // Priority 3: Inference (with warning)
  if (runStatus === 'success') {
    console.warn(`Inferring status for ${stageName} from run status`)
    return 'success'
  }

  return 'pending'
}
```

### 3. StagePanel Tool Calls Tab

```typescript
// Add to StagePanel tabs
{/* Tool Calls Tab */}
<Tab label="Tools" count={toolCalls?.length}>
  <ToolCallHistory calls={stage.output_snapshot?._tool_metrics?.tool_calls || []} />
</Tab>

// New component: ToolCallHistory.tsx
function ToolCallHistory({ calls }: { calls: ToolCall[] }) {
  return (
    <div className="space-y-2">
      {calls.map((call, i) => (
        <div key={i} className="border rounded-lg p-3">
          <div className="flex items-center justify-between">
            <code className="font-mono text-sm">{call.name}</code>
            <span className={call.status === 'success' ? 'text-green-600' : 'text-red-600'}>
              {call.latency_ms}ms
            </span>
          </div>
          {call.arguments && (
            <pre className="text-xs mt-2 bg-gray-50 p-2 rounded">
              {JSON.stringify(call.arguments, null, 2)}
            </pre>
          )}
          {call.result && (
            <pre className="text-xs mt-2 bg-green-50 p-2 rounded">
              {JSON.stringify(call.result, null, 2)}
            </pre>
          )}
        </div>
      ))}
    </div>
  )
}
```

### 4. Live Reasoning Panel

```typescript
// New component: LiveReasoningPanel.tsx
function LiveReasoningPanel({ runId, stageName }: Props) {
  const [steps, setSteps] = useState<LiveStep[]>([])

  useEffect(() => {
    const eventSource = new EventSource(`/api/runs/${runId}/stream`)

    eventSource.addEventListener('live_step', (event) => {
      const step = JSON.parse(event.data)
      if (step.stage_name === stageName) {
        setSteps(prev => [...prev, step])
      }
    })

    return () => eventSource.close()
  }, [runId, stageName])

  return (
    <div className="space-y-2 max-h-96 overflow-y-auto">
      {steps.map((step, i) => (
        <StepBubble key={i} step={step} />
      ))}
      {isRunning && <TypingIndicator />}
    </div>
  )
}
```

---

## Part 6: Implementation Checklist

### Phase 1: Data Consistency
- [ ] Create `getStageStatus()` utility
- [ ] Remove hardcoded layout fallbacks
- [ ] Add timestamp validation in TimelineView
- [ ] Unify cost/token source

### Phase 2: Tool Visibility
- [ ] Add Tool Calls tab to StagePanel
- [ ] Integrate ReActTraceViewer for HAD agents
- [ ] Enhance ClusterView tool extraction
- [ ] Add iteration counter to StagePanel

### Phase 3: Real-time Enhancements
- [ ] Enhance SSE events with metrics
- [ ] Add live_step events for reasoning
- [ ] Add tool_call events
- [ ] Implement LiveReasoningPanel

### Phase 4: Advanced Visualization
- [ ] Build agent-level graph view
- [ ] Add retry loop state to graph
- [ ] Sub-task panel for orchestrators
- [ ] Cost breakdown by dimension

---

## Appendix: Component File Locations

| Component | Path |
|-----------|------|
| TimelineView | `frontend/src/components/pipeline/TimelineView.tsx` |
| PipelineView | `frontend/src/components/pipeline/PipelineView.tsx` |
| ClusterView | `frontend/src/components/pipeline/ClusterView.tsx` |
| StagePanel | `frontend/src/components/pipeline/StagePanel.tsx` |
| LivePipelineView | `frontend/src/components/pipeline/LivePipelineView.tsx` |
| ReActTraceViewer | `frontend/src/components/pipeline/ReActTraceViewer.tsx` |
| Types | `frontend/src/components/pipeline/types.ts` |
| Backend Instrumentation | `backend/app/agents/instrumentation.py` |
