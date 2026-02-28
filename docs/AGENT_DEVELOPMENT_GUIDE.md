# Agent Development Guide

Complete reference for adding new agents to the GamED.AI v2 pipeline.

---

## Agent Function Pattern

Every agent follows this signature and structure:

**File:** `backend/app/agents/my_new_agent.py`

```python
from typing import Optional
from app.agents.state import AgentState
from app.agents.instrumentation import InstrumentedAgentContext

async def my_new_agent(
    state: AgentState,
    ctx: Optional[InstrumentedAgentContext] = None
) -> dict:
    """
    Brief description of agent purpose.

    Inputs: input_key_1, input_key_2
    Outputs: output_key_1, output_key_2
    """
    # 1. Extract inputs from state
    input_1 = state.get("input_key_1")
    input_2 = state.get("input_key_2")

    # 2. Perform agent logic
    result = await do_work(input_1, input_2)

    # 3. Track LLM metrics if applicable
    if ctx and llm_response:
        ctx.set_llm_metrics(
            model=llm_response.model,
            prompt_tokens=llm_response.usage.input_tokens,
            completion_tokens=llm_response.usage.output_tokens,
            latency_ms=int(llm_response.latency * 1000)
        )

    # 4. Track fallback usage if applicable
    if ctx and used_fallback:
        ctx.set_fallback_used("Reason for fallback")

    # 5. Return state update dict (partial — NOT full state)
    return {
        "output_key_1": result.field1,
        "output_key_2": result.field2,
    }
```

Key rules:
- Always accept `state: AgentState` and `ctx: Optional[InstrumentedAgentContext]`
- Return a **partial** state update dict — only the keys this agent produces
- Never return the full state object
- Use `ctx.set_llm_metrics()` for any LLM calls
- Use `ctx.set_fallback_used()` if a fallback path was taken

---

## Step-by-Step Registration

### 1. Define Agent Input/Output Keys

**File:** `backend/app/agents/instrumentation.py`

Add your agent to BOTH `extract_input_keys()` and `extract_output_keys()`:

```python
def extract_input_keys(state: Dict, agent_name: str) -> List[str]:
    agent_inputs = {
        # ... existing agents ...
        "my_new_agent": ["input_key_1", "input_key_2"],  # ADD THIS
    }
    return agent_inputs.get(agent_name, [])

def extract_output_keys(result: Dict, agent_name: str) -> List[str]:
    agent_outputs = {
        # ... existing agents ...
        "my_new_agent": ["output_key_1", "output_key_2"],  # ADD THIS
    }
    return agent_outputs.get(agent_name, [])
```

Also add to `AGENT_METADATA_REGISTRY` in the same file:

```python
AGENT_METADATA_REGISTRY = {
    # ... existing agents ...
    "my_new_agent": {
        "name": "My New Agent",
        "description": "Brief description",
        "category": "generation",  # input | routing | image | generation | validation | output | react | decision | orchestrator | workflow
        "toolOrModel": "LLM (configurable)",
        "icon": "icon-name"
    },
}
```

### 2. Register in Graph

**File:** `backend/app/agents/graph.py`

```python
from app.agents.my_new_agent import my_new_agent
from app.agents.instrumentation import wrap_agent_with_instrumentation

# In create_game_generation_graph() or relevant graph function:
graph.add_node("my_new_agent", wrap_agent_with_instrumentation(my_new_agent, "my_new_agent"))
graph.add_edge("previous_agent", "my_new_agent")
graph.add_edge("my_new_agent", "next_agent")
```

For conditional routing, use `add_conditional_edges()`:

```python
graph.add_conditional_edges(
    "my_new_agent",
    my_routing_function,
    {
        "path_a": "agent_a",
        "path_b": "agent_b",
    }
)
```

### 3. Add Agent Metadata (Frontend)

**File:** `frontend/src/components/pipeline/PipelineView.tsx`

Add to `AGENT_METADATA`:

```typescript
export const AGENT_METADATA: Record<string, {...}> = {
  // ... existing agents ...
  my_new_agent: {
    name: 'My New Agent',
    description: 'Brief description of what this agent does',
    category: 'generation',  // 'input' | 'routing' | 'image' | 'generation' | 'validation' | 'output'
    toolOrModel: 'LLM (configurable)',
    color: '#8B5CF6',  // Unique hex color
    icon: '...'
  },
}
```

### 4. Add to Graph Layout (Frontend)

**File:** `frontend/src/components/pipeline/PipelineView.tsx`

Add to `GRAPH_LAYOUT` in the correct position:

```typescript
const GRAPH_LAYOUT = [
  ['input_enhancer'],
  ['domain_knowledge_retriever'],
  // ... add your agent in the correct row ...
  ['my_new_agent'],  // Or add to existing row: ['existing_agent', 'my_new_agent']
]
```

Add edge definitions:

```typescript
const edgeDefinitions = [
  // ... existing edges ...
  { from: 'previous_agent', to: 'my_new_agent' },
  { from: 'my_new_agent', to: 'next_agent' },
]
```

### 5. Add Output Renderer (Optional)

**File:** `frontend/src/components/pipeline/StagePanel.tsx`

Add a custom renderer in `AgentOutputRenderer` for rich output display:

```typescript
if (stageName === 'my_new_agent' && output.my_output_key) {
  const data = output.my_output_key as { field1?: string; field2?: number }
  return (
    <div className="space-y-3">
      <div className="bg-blue-50 p-2 rounded-lg">
        <span className="text-xs text-blue-600 font-medium">Field 1</span>
        <p className="text-sm font-semibold text-blue-800">{data.field1}</p>
      </div>
      <JsonViewer data={output} title="Full Output" />
    </div>
  )
}
```

---

## Validation Agent Pattern

Validators return a tuple: `(success: bool, score: float, message: str)`

```python
async def validate_something(data: dict) -> tuple[bool, float, str]:
    errors = []

    if not data.get("required_field"):
        errors.append("Missing required_field")

    if len(data.get("items", [])) < 3:
        errors.append("Need at least 3 items")

    if errors:
        return False, 0.0, "; ".join(errors)
    return True, 1.0, "Validation passed"
```

Validators that wrap retry logic should use the `retry_counts` and `max_retries` state fields to track attempts.

---

## Workflow Agent Pattern

For agents that participate in the workflow system (`backend/app/agents/workflows/`):

```python
from app.agents.workflows.types import MechanicType, WorkflowType
from app.agents.workflows.base import BaseWorkflow

class MyWorkflow(BaseWorkflow):
    workflow_type = WorkflowType.MY_WORKFLOW

    async def execute(self, state: AgentState) -> dict:
        # Workflow-specific logic
        return {"workflow_generated_assets": results}
```

Supported MechanicTypes: `drag_drop`, `trace_path`, `sequencing`, `sorting`, `memory_match`, `comparison`, `branching_scenario`, `click_to_identify`, `reveal`, `hotspot`.

---

## HAD Agent Pattern

For agents in the HAD (Hierarchical Agentic DAG) architecture (`backend/app/agents/had/`):

HAD uses a 4-cluster architecture:
1. **RESEARCH** — Input processing (shared with default pipeline)
2. **VISION** — Zone planner with worker agents
3. **DESIGN** — Game orchestrator with structured tool calls
4. **OUTPUT** — Output orchestrator with validation retry loop

HAD agents use the ReAct loop pattern (`react_loop.py`) and structured tools from `backend/app/tools/`.

---

## Agent Development Checklist

- [ ] Agent function accepts `state: AgentState` and `ctx: Optional[InstrumentedAgentContext]`
- [ ] Agent returns partial state update dict (not full state)
- [ ] Input keys added to `extract_input_keys()` in `instrumentation.py`
- [ ] Output keys added to `extract_output_keys()` in `instrumentation.py`
- [ ] Agent metadata added to `AGENT_METADATA_REGISTRY` in `instrumentation.py`
- [ ] Agent metadata added to `AGENT_METADATA` in `PipelineView.tsx`
- [ ] Agent added to `GRAPH_LAYOUT` in `PipelineView.tsx`
- [ ] Edge definitions added in `PipelineView.tsx`
- [ ] Agent wrapped with `wrap_agent_with_instrumentation()` in `graph.py`
- [ ] Custom output renderer added to `StagePanel.tsx` (if meaningful output visualization)
- [ ] LLM metrics tracked via `ctx.set_llm_metrics()` if agent uses LLM
- [ ] Fallback usage tracked via `ctx.set_fallback_used()` if applicable
- [ ] State fields added to `AgentState` TypedDict if new fields introduced
- [ ] Pydantic schema created in `backend/app/agents/schemas/` if structured output needed

---

## Coding Standards Quick Reference

### Python (Backend)

1. **Always use `PYTHONPATH=.`** when running scripts from `backend/` directory
2. **Type hints required** for all function parameters and returns
3. **Async/await** for all I/O operations (LLM calls, DB, HTTP)
4. **Structured logging** via `logger = logging.getLogger("gamed_ai.agents.{name}")`
5. **Pydantic schemas** for all agent outputs in `app/agents/schemas/`

### TypeScript (Frontend)

1. **Strict mode** — no `any` types without justification
2. **Named exports** preferred over default exports
3. **Component files** should export types alongside components
4. **Use utility classes** from `globals.css` (e.g., `card`, `badge-success`, `btn-primary`)
