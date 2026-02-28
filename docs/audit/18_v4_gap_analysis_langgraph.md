# V4 Gap Analysis: LangGraph 1.0.6 Capabilities

**Date**: 2026-02-14
**Status**: Research Complete
**LangGraph Version**: 1.0.6
**Python Version**: 3.14

---

## Executive Summary

LangGraph 1.0.6 **supports all V4 pipeline patterns**. The following capabilities are confirmed:

1. ✅ **Send API** — Native map-reduce with dynamic fan-out
2. ✅ **Parallel edges from START** — Multiple entry points via conditional edges
3. ✅ **Conditional retry loops** — Validator → retry or proceed
4. ✅ **Selective retry after fan-out** — Send + conditional routing per unit

**Critical finding**: Our current V3 graph uses `set_entry_point()` (single entry), but **V4 needs parallel Phase 0 nodes**. This requires a dispatcher pattern at START, NOT multiple edges from START.

---

## 1. Send API for Map-Reduce

### 1.1 Import Path

```python
# CORRECT (LangGraph 1.0+)
from langgraph.types import Send

# DEPRECATED (will be removed in V2.0)
from langgraph.constants import Send  # triggers deprecation warning
```

**Source**: `/Users/shivenagarwal/GamifyAssessment/backend/venv/lib/python3.14/site-packages/langgraph/types.py:285-358`

### 1.2 Usage Pattern

```python
from langgraph.types import Send
from langgraph.graph import StateGraph, END

class OverallState(TypedDict):
    scenes: list[dict]
    scene_results: Annotated[list[dict], operator.add]  # reducer field

def fan_out_scenes(state: OverallState):
    """Dispatch function that returns list of Send objects"""
    return [Send("process_scene", {"scene": s}) for s in state["scenes"]]

graph = StateGraph(OverallState)
graph.add_node("process_scene", process_scene_node)

# Conditional edge from START can return Send list
graph.add_conditional_edges(
    START,
    fan_out_scenes,  # returns list[Send]
)

# Automatically merges when process_scene completes
graph.add_edge("process_scene", "merge_results")
```

**How it works**:
- `Send(node_name, arg)` creates a "packet" to dispatch to a specific node
- `arg` can be a **different state shape** than the main graph state
- LangGraph detects `list[Send]` return and executes all targets **in parallel** (same superstep)
- Results are merged via **reducer annotations** (e.g., `Annotated[list, operator.add]`)

**Official example**: From LangGraph types.py docstring (lines 302-327)

### 1.3 Merge Pattern

When a node is targeted by Send, its return value is merged into the parent state using the **reducer** defined in the parent state's TypedDict:

```python
from typing import Annotated
import operator

class ParentState(TypedDict):
    scene_ids: list[str]
    generated_assets: Annotated[list[dict], operator.add]  # APPEND results

class ChildState(TypedDict):
    scene_id: str
    asset: dict

def process_scene(state: ChildState) -> dict:
    # Returns asset for THIS scene only
    return {"generated_assets": [state["asset"]]}

# LangGraph automatically:
# 1. Calls process_scene N times in parallel
# 2. Collects all returned {"generated_assets": [asset]} dicts
# 3. Uses operator.add to merge: [asset1] + [asset2] + ... → [asset1, asset2, ...]
```

**Key insight**: The **reducer annotation** (line 313 in types.py) controls merge behavior. Without it, last write wins.

---

## 2. Parallel Edges from START

### 2.1 Current Pattern (V3)

All our graphs use **single entry point**:

```python
# From graph.py lines 1150, 1969, etc.
graph.set_entry_point("input_enhancer")
graph.add_edge("input_enhancer", "domain_knowledge_retriever")
```

This is **sequential**: `START → input_enhancer → domain_knowledge_retriever → ...`

### 2.2 V4 Requirement (Parallel Phase 0)

V4 architecture diagram shows:

```
Phase 0: Understanding
  ├── input_analyzer (single LLM call)     ─┐ PARALLEL
  └── dk_retriever (ReAct — web search)     ─┘
```

**Problem**: LangGraph StateGraph does **NOT support multiple edges from START**. The `START` node is a singleton that can only have ONE edge.

### 2.3 Solution: Dispatcher Pattern

Use a **no-op dispatcher node** that immediately routes to parallel nodes:

```python
def dispatch_phase_0(state: AgentState) -> list[Send]:
    """No-op dispatcher — returns Send objects for parallel execution"""
    return [
        Send("input_analyzer", state),
        Send("dk_retriever", state),
    ]

graph = StateGraph(AgentState)
graph.add_node("input_analyzer", input_analyzer_node)
graph.add_node("dk_retriever", dk_retriever_node)

# Option A: Conditional edge from START
graph.add_conditional_edges(START, dispatch_phase_0)

# Option B: Explicit dispatcher node (cleaner for observability)
graph.add_node("phase_0_dispatcher", lambda s: s)  # passthrough
graph.set_entry_point("phase_0_dispatcher")
graph.add_conditional_edges("phase_0_dispatcher", dispatch_phase_0)

# Both nodes complete, then merge
graph.add_edge("input_analyzer", "merge_phase_0")
graph.add_edge("dk_retriever", "merge_phase_0")
```

**Alternative (simpler but sequential)**:

If true parallelism isn't critical, use conditional edge with **state check**:

```python
def route_phase_0(state: AgentState):
    if not state.get("input_analyzer_complete"):
        return "input_analyzer"
    elif not state.get("dk_retriever_complete"):
        return "dk_retriever"
    else:
        return "game_designer"

graph.add_conditional_edges("input_enhancer", route_phase_0, {
    "input_analyzer": "input_analyzer",
    "dk_retriever": "dk_retriever",
    "game_designer": "game_designer"
})
```

But this is **NOT parallel** — it runs sequentially in a loop.

**Recommendation**: Use **Send dispatcher pattern** (Option B above) for Phase 0.

### 2.4 Why Not Multiple set_entry_point Calls?

```python
# THIS DOES NOT WORK
graph.set_entry_point("input_analyzer")
graph.set_entry_point("dk_retriever")  # Overwrites previous entry point
```

`set_entry_point()` is a setter, not an adder. The graph can only have **one** START edge.

**Source**: All our current graphs (lines 1150, 1580, 1648, 1696, 1821, 1969) use single `set_entry_point()`.

---

## 3. Conditional Edges with Retry

### 3.1 Current V3 Pattern (Working)

We already use this pattern extensively:

```python
# From graph.py lines 1978-1985
graph.add_edge("game_designer_v3", "design_validator")
graph.add_conditional_edges(
    "design_validator",
    _v3_design_validation_router,  # returns "game_designer_v3" or "scene_architect_v3"
    {
        "game_designer_v3": "game_designer_v3",  # RETRY
        "scene_architect_v3": "scene_architect_v3",  # PROCEED
    },
)
```

The routing function checks retry count and validation result:

```python
def _v3_design_validation_router(state: AgentState) -> str:
    validation = state.get("design_validation_v3", {})
    if validation.get("is_valid"):
        return "scene_architect_v3"  # proceed

    retry_count = state.get("retry_counts", {}).get("game_designer_v3", 0)
    if retry_count < state.get("max_retries", 2):
        return "game_designer_v3"  # retry

    raise Exception("Max retries exceeded")  # fail
```

**Status**: ✅ Already implemented correctly in V3. **No changes needed for V4.**

---

## 4. Fan-Out with Per-Unit Retry

### 4.1 V4 Requirement

**Phase 2: Content Build** uses map-reduce per scene/mechanic:

```
Phase 2: Content Build (per scene, per mechanic — Map-Reduce)
  ├── scene_context_builder (deterministic)
  ├── mechanic_content_generators (parallel, scene-aware)
  ├── mechanic_content_validators (deterministic → retry with feedback)
  └── scene_interaction_designer
```

**Required pattern**:
1. Fan out to N mechanic generators (one per mechanic in the scene)
2. Validate each mechanic's output independently
3. If some fail, **re-dispatch ONLY the failing ones** (not all N)
4. Merge when all succeed

### 4.2 Solution: Send + Conditional State Filtering

```python
class ContentState(TypedDict):
    mechanics: list[dict]  # {mechanic_id, type, config}
    generated_content: Annotated[list[dict], operator.add]  # accumulator
    failed_mechanics: list[str]  # IDs that need retry

def fan_out_mechanics(state: ContentState):
    """Initial fan-out: generate content for all mechanics"""
    mechanics = state.get("mechanics", [])
    return [
        Send("generate_mechanic_content", {"mechanic": m})
        for m in mechanics
    ]

def validate_and_retry(state: ContentState):
    """Validate all, re-dispatch only failures"""
    generated = state.get("generated_content", [])
    failed_ids = []

    for content in generated:
        is_valid, errors = validate_content(content)
        if not is_valid:
            failed_ids.append(content["mechanic_id"])

    if not failed_ids:
        return "scene_interaction_designer"  # ALL valid, proceed

    # Re-dispatch ONLY failed mechanics
    failed_mechanics = [m for m in state["mechanics"] if m["id"] in failed_ids]
    return [
        Send("generate_mechanic_content", {
            "mechanic": m,
            "retry_feedback": get_feedback(m["id"])  # include validator feedback
        })
        for m in failed_mechanics
    ]

graph.add_node("generate_mechanic_content", generate_node)
graph.add_conditional_edges("fan_out_node", fan_out_mechanics)
graph.add_edge("generate_mechanic_content", "validate_node")
graph.add_conditional_edges(
    "validate_node",
    validate_and_retry,
    {
        "scene_interaction_designer": "scene_interaction_designer",
        # Send list is returned directly (not in path dict)
    }
)
```

**How it works**:
- Conditional edge can return **EITHER** a string (route to single node) **OR** a list of Send objects (fan out again)
- If validation finds 2 of 5 mechanics failed, it returns `[Send(...), Send(...)]` for just those 2
- LangGraph executes the 2 retries in parallel
- Results are merged back into `generated_content` via the reducer
- Validation runs again — if all pass, routes to next phase

**Key pattern**: The validator node has **dual return mode** (string for proceed, list[Send] for selective retry).

### 4.3 Retry Count Tracking

Track retries **per mechanic**, not globally:

```python
class ContentState(TypedDict):
    mechanics: list[dict]
    generated_content: Annotated[list[dict], operator.add]
    retry_counts: dict[str, int]  # {mechanic_id: count}

def validate_and_retry(state: ContentState):
    failed = validate_all(state["generated_content"])
    retry_counts = state.get("retry_counts", {})

    retryable = [
        m for m in failed
        if retry_counts.get(m["mechanic_id"], 0) < 2  # max 2 retries
    ]

    if not retryable:
        if failed:
            raise Exception(f"Mechanics {failed} exceeded retries")
        return "proceed"

    # Increment retry counts
    new_counts = {**retry_counts}
    for m in retryable:
        new_counts[m["mechanic_id"]] = new_counts.get(m["mechanic_id"], 0) + 1

    return [
        Send("generate_mechanic_content", {
            "mechanic": m,
            "retry_count": new_counts[m["mechanic_id"]],
            "feedback": get_feedback(m["mechanic_id"])
        })
        for m in retryable
    ]
```

**Status**: ✅ Pattern supported. Requires careful state design.

---

## 5. Patterns That WON'T Work

### 5.1 ❌ Multiple Edges from START

```python
# DOES NOT WORK
graph.add_edge(START, "input_analyzer")
graph.add_edge(START, "dk_retriever")
```

**Error**: `StateGraph` does not have an `add_edge(START, ...)` method. Only `set_entry_point()` exists, which accepts a single node name.

**Solution**: Use Send dispatcher pattern (Section 2.3).

### 5.2 ❌ Send Without Reducer Annotation

```python
class BadState(TypedDict):
    results: list[dict]  # NO reducer annotation

def fan_out(state):
    return [Send("worker", {"task": t}) for t in state["tasks"]]

# Worker returns {"results": [result]}
# LangGraph behavior: LAST worker's result overwrites all previous results
# Final state.results = [last_result] only
```

**Fix**: Use `Annotated[list, operator.add]` for accumulator fields.

### 5.3 ❌ Conditional Edge Returning Both String and Send

```python
def bad_router(state):
    if state["condition"]:
        return "next_node"  # string
    else:
        return [Send("worker", {...})]  # list[Send]
```

**Error**: Type checker will fail. LangGraph expects **consistent return type**.

**Fix**: Return list[Send] in both branches, or use separate conditional edges.

---

## 6. V4 Graph Design Recommendations

### 6.1 Phase 0 (Parallel Understanding)

```python
from langgraph.types import Send
from langgraph.graph import StateGraph, START, END

class V4State(TypedDict):
    question_text: str
    pedagogical_context: dict
    domain_knowledge: dict
    phase_0_complete: bool

def phase_0_dispatcher(state: V4State):
    """Fan out to parallel understanding nodes"""
    return [
        Send("input_analyzer", state),
        Send("dk_retriever", state),
    ]

def merge_phase_0(state: V4State):
    """Check both nodes completed"""
    if state.get("pedagogical_context") and state.get("domain_knowledge"):
        return {"phase_0_complete": True}
    raise Exception("Phase 0 incomplete")

graph = StateGraph(V4State)
graph.add_node("input_analyzer", input_analyzer_node)
graph.add_node("dk_retriever", dk_retriever_node)
graph.add_node("merge_phase_0", merge_phase_0)

graph.set_entry_point("phase_0_dispatcher")
graph.add_node("phase_0_dispatcher", lambda s: s)
graph.add_conditional_edges("phase_0_dispatcher", phase_0_dispatcher)

# Both parallel nodes converge to merge
graph.add_edge("input_analyzer", "merge_phase_0")
graph.add_edge("dk_retriever", "merge_phase_0")

# Merge proceeds to Phase 1
graph.add_edge("merge_phase_0", "game_designer")
```

**Key**: The dispatcher is a **passthrough node** (`lambda s: s`) that immediately returns Send list.

### 6.2 Phase 2 (Map-Reduce Content Build)

```python
class V4State(TypedDict):
    scenes: list[dict]
    mechanic_content: Annotated[list[dict], operator.add]  # accumulator
    content_validation_status: dict[str, bool]

def fan_out_per_scene(state: V4State):
    """Dispatch one content builder per scene"""
    return [
        Send("build_scene_content", {"scene": scene})
        for scene in state["scenes"]
    ]

def build_scene_content(scene_state: dict) -> dict:
    """Generates content for all mechanics in one scene"""
    scene = scene_state["scene"]
    mechanics = scene["mechanics"]

    content = []
    for mechanic in mechanics:
        generated = generate_mechanic_content(mechanic)
        content.append({
            "scene_id": scene["id"],
            "mechanic_id": mechanic["id"],
            "content": generated
        })

    return {"mechanic_content": content}

graph.add_node("build_scene_content", build_scene_content)
graph.add_conditional_edges("game_designer", fan_out_per_scene)

# All scene content builders merge automatically
graph.add_edge("build_scene_content", "validate_content")
```

**Pattern**: Send per **scene**, each scene builds **all its mechanics** sequentially. This is simpler than nested fan-out (scene → mechanic).

**Alternative**: Nested fan-out (fan to scenes, each scene fans to mechanics) requires **sub-graphs**.

### 6.3 Phase 3 (Map-Reduce Asset Generation)

```python
class V4State(TypedDict):
    asset_manifest: list[dict]  # {asset_id, type, chain, spec}
    generated_assets: Annotated[list[dict], operator.add]

def fan_out_assets(state: V4State):
    """Dispatch one generator per asset"""
    return [
        Send("generate_asset", {
            "asset_id": asset["id"],
            "chain": asset["chain"],
            "spec": asset["spec"]
        })
        for asset in state["asset_manifest"]
    ]

def generate_asset(asset_state: dict) -> dict:
    """Runs the appropriate chain (diagram_with_zones, simple_image, etc.)"""
    chain = asset_state["chain"]
    spec = asset_state["spec"]

    if chain == "diagram_with_zones":
        result = run_diagram_chain(spec)
    elif chain == "simple_image":
        result = run_simple_image_chain(spec)
    # ... etc

    return {
        "generated_assets": [{
            "asset_id": asset_state["asset_id"],
            "result": result
        }]
    }

graph.add_conditional_edges("asset_orchestrator", fan_out_assets)
graph.add_edge("generate_asset", "asset_validator")
```

**Key**: Each asset gets its own Send with **only the data it needs** (not full state). This reduces memory and enables parallel execution.

---

## 7. Observability Implications

### 7.1 Instrumentation Challenges

Our current instrumentation (`app/agents/instrumentation.py`) wraps each agent with input/output key extraction. With Send API:

**Problem**: The child state passed to Send is **NOT the same shape** as AgentState.

**Example**:
```python
Send("generate_asset", {
    "asset_id": "scene_1_diagram",
    "chain": "diagram_with_zones",
    "spec": {...}
})
```

This dict has NO `question_text`, `domain_knowledge`, etc. — it's a **minimal task-specific state**.

**Impact**:
- `extract_input_keys()` will fail if it expects AgentState fields
- `extract_output_keys()` must handle partial state updates

**Solution**: Update instrumentation to handle **union state types**:

```python
def extract_input_keys(agent_name: str, state: Union[AgentState, dict]) -> list[str]:
    """Extract keys that this agent reads from state (any shape)"""
    # Use try/except or type checking
    if agent_name == "generate_asset":
        return ["asset_id", "chain", "spec"]  # minimal state
    else:
        return standard_agent_keys(agent_name)  # full AgentState
```

### 7.2 Frontend Visualization

Send API creates **dynamic node instances**. If we fan out to 5 scenes:

```
generate_asset (instance 1)
generate_asset (instance 2)
generate_asset (instance 3)
generate_asset (instance 4)
generate_asset (instance 5)
```

**Current frontend** (`PipelineView.tsx`) assumes **static node graph** with fixed positions.

**Required change**: Render dynamic node instances in a **sub-panel** or **accordion**:

```tsx
{nodeId === "generate_asset" && stageData.instances && (
  <div className="dynamic-instances">
    {stageData.instances.map((inst, idx) => (
      <MiniStageCard key={idx} data={inst} />
    ))}
  </div>
)}
```

**Data source**: LangGraph's checkpointer logs include `task_path` for each Send execution. We need to capture this in our instrumentation.

---

## 8. Verification Checklist

Before implementing V4, verify these LangGraph patterns work in our environment:

### 8.1 Unit Tests

- [ ] Test Send import from `langgraph.types` (not `.constants`)
- [ ] Test dispatcher returning `list[Send]`
- [ ] Test reducer annotation with `operator.add`
- [ ] Test conditional edge returning Send list (selective retry)
- [ ] Test nested Send (sub-graph as Send target)
- [ ] Test Send with minimal state (not full AgentState)

### 8.2 Integration Tests

- [ ] Phase 0 parallel execution (input_analyzer + dk_retriever)
- [ ] Phase 2 map-reduce per scene
- [ ] Phase 3 map-reduce per asset with selective retry
- [ ] Instrumentation captures Send instances correctly
- [ ] Frontend renders dynamic node instances

### 8.3 Performance Tests

- [ ] 5 scenes × 3 mechanics = 15 parallel content builds (latency reduction?)
- [ ] 20 asset generations in parallel (memory usage? timeout handling?)
- [ ] Retry only 2 of 15 mechanics (overhead compared to retry all?)

---

## 9. Migration Path from V3 → V4

### 9.1 Incremental Adoption

**Week 1: Phase 0 parallelization**
- Add dispatcher node
- Convert input_enhancer + domain_knowledge_retriever to parallel Send pattern
- Add merge node
- Verify observability still works

**Week 2: Phase 2 content map-reduce**
- Design per-scene state shape
- Implement fan-out per scene
- Add validator with selective retry
- Test with 3-scene game

**Week 3: Phase 3 asset map-reduce**
- Design per-asset state shape
- Implement pre-built chain dispatcher
- Add zone validator with retry
- Test with 10+ assets

**Week 4: Full pipeline integration**
- Wire all 5 phases
- Update frontend for dynamic instances
- E2E testing

### 9.2 Backward Compatibility

**Option**: Support V3 and V4 graphs simultaneously via `pipeline_version` flag:

```python
def get_compiled_graph(pipeline_version: str = "v3"):
    if pipeline_version == "v4":
        return create_v4_graph().compile()
    elif pipeline_version == "v3":
        return create_v3_graph().compile()
    else:
        return create_game_generation_graph().compile()  # legacy
```

This allows gradual rollout and A/B testing.

---

## 10. Conclusion

### 10.1 Key Findings

1. ✅ **Send API is production-ready** — import from `langgraph.types`, use with conditional edges
2. ✅ **Parallel Phase 0** — requires dispatcher pattern, NOT multiple START edges
3. ✅ **Conditional retry** — already working in V3, no changes needed
4. ✅ **Selective retry** — supported via Send list returned from validator

### 10.2 Critical Gaps to Address

1. **Instrumentation** — must handle partial state (Send targets)
2. **Frontend visualization** — must render dynamic node instances
3. **State design** — per-phase TypedDicts (not monolithic AgentState)
4. **Testing** — unit tests for all Send patterns before production use

### 10.3 Recommended Next Steps

1. **Prototype Phase 0 dispatcher** — 1 day, verify parallel execution works
2. **Design V4 state schemas** — 2 days, define per-phase TypedDicts
3. **Update instrumentation** — 1 day, handle union state types
4. **Build Phase 2 map-reduce** — 3 days, per-scene content build with retry
5. **Frontend dynamic nodes** — 2 days, render Send instances

**Total estimated effort**: 9 days for core graph patterns, excluding agent logic migration.

---

## References

### LangGraph Documentation
- [Use the graph API](https://docs.langchain.com/oss/python/langgraph/use-graph-api) — Official docs
- [Map-Reduce with Send API](https://medium.com/ai-engineering-bootcamp/map-reduce-with-the-send-api-in-langgraph-29b92078b47d) — Medium article
- [Parallel Nodes in LangGraph](https://medium.com/@gmurro/parallel-nodes-in-langgraph-managing-concurrent-branches-with-the-deferred-execution-d7e94d03ef78) — Deferred execution

### Codebase References
- `/Users/shivenagarwal/GamifyAssessment/backend/app/agents/graph.py` — Current V3 graph
- `/Users/shivenagarwal/GamifyAssessment/docs/audit/14_v4_architecture_refined.md` — V4 design
- `/Users/shivenagarwal/GamifyAssessment/docs/audit/09_agentic_frameworks_research.md` — LangGraph research
- `/Users/shivenagarwal/GamifyAssessment/backend/venv/lib/python3.14/site-packages/langgraph/types.py:285-358` — Send class definition

---

**END OF REPORT**
