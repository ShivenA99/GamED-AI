# LangGraph 1.0.6 Feasibility Analysis for V4 Pipeline

**Date:** 2026-02-14
**LangGraph Version:** 1.0.6
**Purpose:** Validate that V4 graph design patterns are compatible with our installed LangGraph version

---

## Executive Summary

**✅ ALL V4 PATTERNS ARE SUPPORTED** — LangGraph 1.0.6 fully supports all patterns required by the V4 pipeline design:

1. ✅ **Send API** (dynamic fan-out)
2. ✅ **Parallel edges from START**
3. ✅ **Conditional edges for retry loops**
4. ✅ **Selective retry** (merge node re-sends only failed units)

**⚠️ CRITICAL CORRECTIONS NEEDED** — V4 graph design (Section 6) has **architectural errors** that will cause runtime crashes. These must be fixed before implementation.

---

## 1. Send API Support

### Question
Does LangGraph 1.0.6 support the `Send` API for dynamic fan-out? What's the import path?

### Answer
✅ **YES — Fully supported**

**Correct import path (LangGraph 1.0+):**
```python
from langgraph.types import Send
```

**Deprecated paths (still work but emit warnings):**
```python
from langgraph.constants import Send  # Deprecated since V1.0
from langgraph.graph import Send      # Never worked
```

**Usage pattern:**
```python
from langgraph.types import Send

def router_function(state: MyState):
    """Router function returns list of Send objects."""
    return [Send("worker_node", {"task": t}) for t in state["tasks"]]

graph.add_conditional_edges("dispatch_node", router_function)
```

**Key constraints:**
- **ONLY conditional_edges router functions can return Send lists**
- **Node functions CANNOT return Send lists** (will crash with `InvalidUpdateError`)
- Send objects specify: `Send(node="target_node_name", arg={"custom": "state"})`
- Worker nodes receive custom state dict (not full graph state)

**Verified with test:** `/tmp/test_send_with_dispatch_node.py` — ✅ PASSED

---

## 2. Parallel Edges from START

### Question
Does LangGraph 1.0.6 support parallel edges from START?

### Answer
✅ **YES — V3 pipeline already uses this pattern**

**Evidence from V3 graph (graph.py:1969):**
```python
graph.set_entry_point("input_enhancer")
```

V3 uses single entry point, but LangGraph supports multiple edges from START:

**Pattern:**
```python
from langgraph.graph import START

graph.add_edge(START, "node_a")
graph.add_edge(START, "node_b")
graph.add_edge("node_a", "merge")
graph.add_edge("node_b", "merge")
```

**Execution:**
- `node_a` and `node_b` execute **in parallel**
- Both must complete before `merge` runs
- LangGraph's Pregel runtime handles synchronization automatically

**Verified with test:** `/tmp/test_parallel_start.py` — ✅ PASSED

**V4 usage (Section 6, lines 1338-1341):**
```python
graph.add_edge(START, "v4_input_analyzer")
graph.add_edge(START, "v4_dk_retriever")
graph.add_edge("v4_input_analyzer", "v4_merge_phase0")
graph.add_edge("v4_dk_retriever", "v4_merge_phase0")
```

This is **valid** and will execute `v4_input_analyzer` and `v4_dk_retriever` in parallel.

---

## 3. Conditional Edges for Retry

### Question
Can conditional_edges route back to a previous node for retry?

### Answer
✅ **YES — V3 already uses this extensively**

**Evidence from V3 graph (graph.py:1978-1985):**
```python
graph.add_edge("game_designer_v3", "design_validator")
graph.add_conditional_edges(
    "design_validator",
    _v3_design_validation_router,
    {
        "game_designer_v3": "game_designer_v3",  # ← RETRY LOOP
        "scene_architect_v3": "scene_architect_v3",
    },
)
```

**Router function (graph.py:1862-1872):**
```python
def _v3_design_validation_router(state: AgentState) -> Literal["game_designer_v3", "scene_architect_v3"]:
    validation = state.get("design_validation_v3", {})
    if validation.get("passed", False):
        return "scene_architect_v3"
    retry = state.get("_v3_design_retries", 0)
    if retry >= 3:
        logger.warning("V3: Design validation failed after 3 retries, proceeding anyway")
        return "scene_architect_v3"
    logger.info(f"V3: Design validation failed, retrying (attempt {retry + 1})")
    return "game_designer_v3"  # ← ROUTES BACK
```

**Pattern:**
- Validator checks output quality
- Returns node name as string
- LangGraph follows edge to that node
- Works for both forward progress and backward retry

**V4 usage:** All validation loops use this pattern (concept, scene, content, interaction, art direction)

---

## 4. Selective Retry (Fan-Out + Merge + Re-Send)

### Question
For selective retry (only re-dispatch failing units), what's the pattern? Does the merge node need to use Send again?

### Answer
✅ **YES — Merge router returns Send list for selective retry**

**CRITICAL PATTERN:**
```python
def merge_and_validate(state: MyState):
    """Merge node: collect results, update state."""
    failed = state.get("failed_items", [])
    retry_count = state.get("retry_count", 0)

    print(f"Collected {len(state['results'])} results, {len(failed)} failed")

    if failed:
        return {"retry_count": retry_count + 1}

    return state

def retry_router(state: MyState):
    """Router: decide retry (Send) or proceed (END/next node)."""
    failed = list(set(state.get("failed_items", [])))  # Deduplicate
    retry_count = state.get("retry_count", 0)

    if failed and retry_count <= 2:
        # Selective retry — only re-send failed items
        return [Send("worker", {"item": item, "attempt": retry_count}) for item in failed]

    # All passed or max retries reached
    return END  # Or return "next_node_name"

graph.add_node("worker", worker_fn)
graph.add_node("merge", merge_and_validate)

# Initial dispatch
graph.add_conditional_edges(START, lambda s: [Send("worker", {"item": i}) for i in s["items"]])
graph.add_edge("worker", "merge")

# Retry loop: merge → retry_router → (Send back to worker) OR (END)
graph.add_conditional_edges("merge", retry_router)
```

**Verified with test:** `/tmp/test_correct_retry.py` — ✅ PASSED
**Results:**
- Initial: 4 items dispatched, 2 succeeded, 2 failed
- Retry 1: Only 2 failed items re-sent, both failed again (wrong attempt number)
- Retry 2: Same 2 failed items re-sent, both succeeded
- Final: All 4 items succeeded

**Key insights:**
1. **Merge node updates state** (stores results, increments retry_count)
2. **Router function returns Send list** (only failed items)
3. **Router can also return END or a node name** (conditional routing)
4. **State accumulation uses Annotated reducers** (`Annotated[List[str], operator.add]`)

---

## 5. Existing Codebase Patterns

### Question
Does our existing codebase already use any of these patterns?

### Answer
**V3 pipeline uses:**
- ✅ **Conditional edges for retry** — 3 validation loops (design, scene, interaction)
- ✅ **Routing back to previous node** — All validators route back on failure
- ❌ **Send API** — NOT USED (V3 is fully sequential)
- ❌ **Parallel edges from START** — NOT USED (V3 uses single entry point)
- ❌ **Fan-out/Map-Reduce** — NOT USED (asset_generator_v3 loops through scenes sequentially)

**Audit doc 09 (lines 237-242) shows Send pattern:**
```python
def route_assets(state):
    return [Send("generate_asset", {"task": t}) for t in state["asset_tasks"]]
```

But this was **research**, not implemented code.

---

## 6. V4 Graph Design Issues

### ❌ CRITICAL ERROR 1: Dispatch Node Returns Send List

**Location:** Section 6, lines 1356-1368

**Current V4 design:**
```python
graph.add_node("v4_scene_design_dispatch", scene_design_dispatch_node)
graph.add_node("v4_scene_designer", scene_designer_node)
graph.add_node("v4_scene_design_merge", scene_design_merge_node)

graph.add_edge("v4_scene_design_dispatch", "v4_scene_designer")  # ← WRONG
graph.add_edge("v4_scene_designer", "v4_scene_design_merge")
graph.add_conditional_edges(
    "v4_scene_design_merge",
    v4_scene_design_router,
    {"retry": "v4_scene_design_dispatch", "proceed": "v4_graph_builder"},  # ← WRONG
)
```

**Problem:**
- `graph.add_edge("v4_scene_design_dispatch", "v4_scene_designer")` is a **static edge**
- Static edges cannot do fan-out
- If `scene_design_dispatch_node` returns a list of Send objects, it will crash with `InvalidUpdateError`

**Correct pattern:**
```python
# Option A: Dispatch node is just a router function (no node)
graph.add_node("v4_scene_designer", scene_designer_node)
graph.add_node("v4_scene_design_merge", scene_design_merge_node)

graph.add_conditional_edges(
    "v4_concept_validator",
    scene_design_dispatch_router,  # ← Router function, not node
    # Returns: [Send("v4_scene_designer", {...}) for scene in scenes]
)
graph.add_edge("v4_scene_designer", "v4_scene_design_merge")

# Option B: Dispatch node + conditional_edges
graph.add_node("v4_scene_design_dispatch", scene_design_dispatch_node)  # Updates state, doesn't return Send
graph.add_node("v4_scene_designer", scene_designer_node)
graph.add_node("v4_scene_design_merge", scene_design_merge_node)

graph.add_edge("v4_concept_validator", "v4_scene_design_dispatch")
graph.add_conditional_edges(
    "v4_scene_design_dispatch",
    lambda s: [Send("v4_scene_designer", {"scene": sc}) for sc in s["scenes"]],
)
graph.add_edge("v4_scene_designer", "v4_scene_design_merge")
```

**Affected nodes in V4:**
- ❌ `v4_scene_design_dispatch` (line 1356)
- ❌ `v4_content_dispatch` (line 1372)
- ❌ `v4_interaction_dispatch` (line 1385)
- ❌ `v4_art_direction_dispatch` (line 1399)
- ❌ `v4_asset_chain_dispatch` (line 1413)

All 5 dispatch nodes have the same error.

---

### ❌ CRITICAL ERROR 2: Retry Routes to Dispatch Node

**Location:** Section 6, lines 1364-1368

**Current V4 design:**
```python
graph.add_conditional_edges(
    "v4_scene_design_merge",
    v4_scene_design_router,
    {"retry": "v4_scene_design_dispatch", "proceed": "v4_graph_builder"},
)
```

**Problem:**
- Merge router is supposed to do **selective retry** (only failed scenes)
- Routing to `"v4_scene_design_dispatch"` node means:
  1. Merge router returns string `"retry"`
  2. Graph routes to `v4_scene_design_dispatch` node
  3. Node cannot return Send list (will crash)
  4. Even if it could, it would re-dispatch ALL scenes, not just failed ones

**Correct pattern:**
```python
def v4_scene_design_router(state: V4PipelineState):
    """Router decides: retry failed scenes OR proceed to next phase."""
    failed_scenes = state.get("failed_scene_ids", [])
    retry_count = state.get("scene_retry_count", 0)

    if failed_scenes and retry_count < 2:
        # Selective retry — return Send list for only failed scenes
        return [
            Send("v4_scene_designer", {
                "scene_id": scene_id,
                "attempt": retry_count + 1,
            })
            for scene_id in failed_scenes
        ]

    # All passed or max retries reached
    return "v4_graph_builder"

graph.add_conditional_edges("v4_scene_design_merge", v4_scene_design_router)
# No path dict needed — router returns Send list OR node name
```

**Alternative (if dispatch node is needed for state prep):**
```python
def v4_scene_design_router(state: V4PipelineState):
    failed = state.get("failed_scene_ids", [])
    retry_count = state.get("scene_retry_count", 0)

    if failed and retry_count < 2:
        return "retry"  # String — route to dispatch node
    return "proceed"

graph.add_conditional_edges(
    "v4_scene_design_merge",
    v4_scene_design_router,
    {
        "retry": "v4_scene_design_dispatch",  # Dispatch prepares state
        "proceed": "v4_graph_builder",
    }
)

# Dispatch node prepares state, then uses conditional_edges to Send
graph.add_node("v4_scene_design_dispatch", scene_design_dispatch_node)  # Returns dict
graph.add_conditional_edges(
    "v4_scene_design_dispatch",
    lambda s: [Send("v4_scene_designer", {...}) for scene in s["failed_scenes"]],
)
```

**Recommendation:** Use first pattern (router returns Send directly) to avoid extra node.

---

### ❌ ERROR 3: Note Says "Fallback: asyncio.gather()"

**Location:** Section 6, line 1431

**Quote:**
> **Note on LangGraph parallelism**: Phase 0 parallel execution and all fan-out patterns use LangGraph's `Send` API or parallel edges. **Fallback: `asyncio.gather()` inside dispatch nodes if Send API unavailable.**

**Problem:**
- This note implies Send API might not be available in LangGraph 1.0.6
- **This is FALSE** — Send API is fully available
- `asyncio.gather()` inside a node cannot replace Send API (different execution model)
- Keeping this note will mislead implementers

**Recommendation:** Delete this note. Replace with:
> **Note on LangGraph parallelism**: Phase 0 parallel execution uses parallel edges from START. All fan-out patterns use LangGraph's `Send` API via conditional_edges routers. LangGraph 1.0.6 fully supports both patterns.

---

## 7. Correct V4 Graph Wiring Pattern

### Corrected Phase 1b: Scene Design

```python
# ── Phase 1b: Scene Design ──
graph.add_node("v4_scene_designer", scene_designer_node)  # Receives Send
graph.add_node("v4_scene_design_merge", scene_design_merge_node)  # Collects + validates
graph.add_node("v4_graph_builder", graph_builder_node)

# Initial dispatch from concept_validator
def scene_design_initial_dispatch(state: V4PipelineState):
    """Router after concept validation — fan out to scene designers."""
    if state.get("concept_validation", {}).get("passed"):
        scenes = state.get("game_concept", {}).get("scenes", [])
        return [
            Send("v4_scene_designer", {
                "scene_id": scene.get("scene_id"),
                "scene_concept": scene,
                "game_concept": state["game_concept"],
                "domain_knowledge": state["domain_knowledge"],
                "attempt": 1,
            })
            for scene in scenes
        ]
    # Concept validation failed, skip to next phase (shouldn't happen)
    return "v4_graph_builder"

graph.add_conditional_edges("v4_concept_validator", scene_design_initial_dispatch)
graph.add_edge("v4_scene_designer", "v4_scene_design_merge")

# Retry loop
def scene_design_retry_router(state: V4PipelineState):
    """After merge: retry failed scenes OR proceed to graph builder."""
    failed_scene_ids = state.get("failed_scene_ids", [])
    retry_count = state.get("scene_design_retry_count", 0)

    if failed_scene_ids and retry_count < 2:
        # Selective retry
        return [
            Send("v4_scene_designer", {
                "scene_id": scene_id,
                # Lookup scene concept from state
                "scene_concept": next(
                    s for s in state["game_concept"]["scenes"] if s["scene_id"] == scene_id
                ),
                "game_concept": state["game_concept"],
                "domain_knowledge": state["domain_knowledge"],
                "attempt": retry_count + 1,
                "validation_feedback": state.get("scene_validation_feedback", {}).get(scene_id, ""),
            })
            for scene_id in failed_scene_ids
        ]

    return "v4_graph_builder"

graph.add_conditional_edges("v4_scene_design_merge", scene_design_retry_router)
graph.add_edge("v4_graph_builder", "v4_content_dispatch_router")
```

**Key changes:**
1. **No `v4_scene_design_dispatch` node** — replaced with router functions
2. **Router returns Send list directly** — no intermediate node
3. **Selective retry** — only failed scenes re-sent
4. **Validation feedback injected** — retry includes validator issues

### Corrected Phase 2a: Content Build

```python
# ── Phase 2a: Content Build ──
graph.add_node("v4_content_generator", content_generator_node)  # Receives Send
graph.add_node("v4_content_merge", content_merge_node)  # Validates per mechanic

def content_dispatch_router(state: V4PipelineState):
    """Fan out to per-mechanic content generators."""
    game_plan = state.get("game_plan")  # From graph_builder

    return [
        Send("v4_content_generator", {
            "mechanic_id": mech.mechanic_id,
            "mechanic_type": mech.mechanic_type,
            "scene_id": mech.scene_id,
            "scene_context": state["scene_contexts"][mech.scene_id],
            "domain_knowledge": state["domain_knowledge"],
            "attempt": 1,
        })
        for mech in game_plan.mechanics
    ]

def content_retry_router(state: V4PipelineState):
    """Selective retry for failed mechanics."""
    failed = state.get("failed_mechanic_ids", [])
    retry_count = state.get("content_retry_count", 0)

    if failed and retry_count < 2:
        game_plan = state["game_plan"]
        return [
            Send("v4_content_generator", {
                "mechanic_id": mech_id,
                "mechanic_type": next(m.mechanic_type for m in game_plan.mechanics if m.mechanic_id == mech_id),
                "scene_id": next(m.scene_id for m in game_plan.mechanics if m.mechanic_id == mech_id),
                "scene_context": state["scene_contexts"][...],
                "domain_knowledge": state["domain_knowledge"],
                "attempt": retry_count + 1,
                "validation_feedback": state["content_validation_feedback"][mech_id],
            })
            for mech_id in failed
        ]

    return "v4_interaction_dispatch_router"

graph.add_edge("v4_graph_builder", "v4_content_dispatch_router")
graph.add_conditional_edges("v4_graph_builder", content_dispatch_router)  # Actually this is wrong, see below
graph.add_edge("v4_content_generator", "v4_content_merge")
graph.add_conditional_edges("v4_content_merge", content_retry_router)
```

**Wait, there's a problem:** `graph.add_edge("v4_graph_builder", "v4_content_dispatch_router")` — there's no node called `v4_content_dispatch_router`.

**Correct pattern:**
```python
# Option A: Router after graph_builder (no dispatch node)
graph.add_edge("v4_graph_builder", "v4_content_generator")  # Will fail — no Send
# WRONG — static edge can't fan out

# Option B: Conditional edge after graph_builder
def graph_builder_router(state: V4PipelineState):
    """After graph_builder, fan out to content generators."""
    game_plan = state["game_plan"]
    return [
        Send("v4_content_generator", {...})
        for mech in game_plan.mechanics
    ]

graph.add_conditional_edges("v4_graph_builder", graph_builder_router)
graph.add_edge("v4_content_generator", "v4_content_merge")
graph.add_conditional_edges("v4_content_merge", content_retry_router)
```

**This is the correct pattern for all 5 dispatch points.**

---

## 8. Summary of Required Fixes

### Fix 1: Remove All Dispatch Nodes

**Files to modify:** `docs/audit/16_v4_implementation_plan.md` Section 6

**Changes:**
```diff
- graph.add_node("v4_scene_design_dispatch", scene_design_dispatch_node)
  graph.add_node("v4_scene_designer", scene_designer_node)
  graph.add_node("v4_scene_design_merge", scene_design_merge_node)

- graph.add_edge("v4_scene_design_dispatch", "v4_scene_designer")
+ # Initial dispatch after concept validator
+ graph.add_conditional_edges("v4_concept_validator", scene_design_dispatch_router)
  graph.add_edge("v4_scene_designer", "v4_scene_design_merge")

- graph.add_conditional_edges(
-     "v4_scene_design_merge",
-     v4_scene_design_router,
-     {"retry": "v4_scene_design_dispatch", "proceed": "v4_graph_builder"},
- )
+ # Retry loop (router returns Send list OR next node name)
+ graph.add_conditional_edges("v4_scene_design_merge", scene_design_retry_router)
```

**Apply same fix to:**
- `v4_content_dispatch` → Remove node, use router after `v4_graph_builder`
- `v4_interaction_dispatch` → Remove node, use router after `v4_content_merge`
- `v4_art_direction_dispatch` → Remove node, use router after `v4_art_direction_merge`
- `v4_asset_chain_dispatch` → Remove node, use router after `v4_art_direction_merge`

### Fix 2: Update Agent Count

**Before:** 27 agents (including 5 dispatch nodes)
**After:** 22 agents (dispatch nodes removed)

**Instrumentation update:**
```diff
 V4_AGENTS = [
     "v4_input_analyzer", "v4_dk_retriever",
     "v4_game_concept_designer", "v4_concept_validator",
-    "v4_scene_design_dispatch", "v4_scene_designer", "v4_scene_design_merge",
+    "v4_scene_designer", "v4_scene_design_merge",
     "v4_graph_builder",
-    "v4_content_dispatch", "v4_content_generator", "v4_content_merge",
+    "v4_content_generator", "v4_content_merge",
-    "v4_interaction_dispatch", "v4_interaction_designer", "v4_interaction_merge",
+    "v4_interaction_designer", "v4_interaction_merge",
     "v4_asset_needs_analyzer",
-    "v4_art_direction_dispatch", "v4_asset_art_director", "v4_art_direction_merge",
+    "v4_asset_art_director", "v4_art_direction_merge",
-    "v4_asset_chain_dispatch", "v4_asset_chain_runner", "v4_asset_merge",
+    "v4_asset_chain_runner", "v4_asset_merge",
     "v4_blueprint_assembler", "v4_blueprint_validator",
 ]
```

### Fix 3: Update Fallback Note

**Line 1431:**
```diff
- **Note on LangGraph parallelism**: Phase 0 parallel execution and all fan-out patterns use LangGraph's `Send` API or parallel edges. Fallback: `asyncio.gather()` inside dispatch nodes if Send API unavailable.
+ **Note on LangGraph parallelism**: Phase 0 parallel execution uses parallel edges from START. All fan-out patterns use LangGraph's `Send` API via conditional_edges routers. LangGraph 1.0.6 fully supports both patterns — no fallback needed.
```

### Fix 4: Add Router Function Signature Docs

**Add to Section 6:**
```markdown
### Router Function Patterns

**Initial Dispatch Router:**
```python
def dispatch_router(state: V4PipelineState) -> List[Send]:
    """Fan out to worker nodes."""
    return [
        Send("worker_node", {
            "task_id": task.id,
            "task_data": task,
            "domain_knowledge": state["domain_knowledge"],
            "attempt": 1,
        })
        for task in state["tasks"]
    ]
```

**Retry Router:**
```python
def retry_router(state: V4PipelineState) -> Union[List[Send], str]:
    """Selective retry OR proceed to next phase."""
    failed = state.get("failed_task_ids", [])
    retry_count = state.get("retry_count", 0)

    if failed and retry_count < 2:
        # Selective retry — only failed tasks
        return [
            Send("worker_node", {
                "task_id": task_id,
                "task_data": state["tasks_by_id"][task_id],
                "domain_knowledge": state["domain_knowledge"],
                "attempt": retry_count + 1,
                "validation_feedback": state["validation_feedback"][task_id],
            })
            for task_id in failed
        ]

    # All passed or max retries
    return "next_phase_node"
```

**Static Router (no Send):**
```python
def static_router(state: V4PipelineState) -> Literal["retry", "proceed"]:
    """Simple string routing."""
    if state.get("validation_passed"):
        return "proceed"
    return "retry"

graph.add_conditional_edges(
    "validator",
    static_router,
    {
        "retry": "designer",
        "proceed": "next_phase",
    }
)
```
```

---

## 9. Recommendations

### Immediate Actions (Before Wave 1)

1. **✅ Update V4 implementation plan** — Fix all 5 dispatch node patterns
2. **✅ Verify state schema** — Add `failed_*_ids` fields to `V4PipelineState` for all retry loops
3. **✅ Add reducer annotations** — Use `Annotated[List[X], operator.add]` for all list fields that accumulate across parallel workers
4. **✅ Write router function templates** — Standardize dispatch/retry router signatures

### State Schema Requirements

**Required fields for each retry loop:**
```python
from typing import Annotated
from operator import add

class V4PipelineState(TypedDict):
    # Scene design retry
    failed_scene_ids: Annotated[List[str], add]
    scene_design_retry_count: int
    scene_validation_feedback: Dict[str, str]  # scene_id → feedback

    # Content generation retry
    failed_mechanic_ids: Annotated[List[str], add]
    content_retry_count: int
    content_validation_feedback: Dict[str, str]  # mechanic_id → feedback

    # Interaction design retry
    failed_interaction_scene_ids: Annotated[List[str], add]
    interaction_retry_count: int
    interaction_validation_feedback: Dict[str, str]

    # Art direction retry
    failed_art_direction_scene_ids: Annotated[List[str], add]
    art_direction_retry_count: int
    art_direction_validation_feedback: Dict[str, str]

    # Asset chain retry
    failed_asset_ids: Annotated[List[str], add]
    asset_retry_count: int
    asset_validation_feedback: Dict[str, str]  # asset_id → feedback
```

**Why `Annotated[List[str], add]`?**
- Parallel workers write to state concurrently
- Without reducer, LangGraph raises `InvalidUpdateError: Can receive only one value per step`
- `operator.add` reducer merges all writes: `["a"] + ["b"] + ["c"] = ["a", "b", "c"]`

### Testing Strategy

**Before implementing V4:**
1. ✅ Test Send API pattern (DONE — `/tmp/test_send_with_dispatch_node.py`)
2. ✅ Test parallel START edges (DONE — `/tmp/test_parallel_start.py`)
3. ✅ Test selective retry (DONE — `/tmp/test_correct_retry.py`)
4. ⚠️ Test with Annotated reducers for failed_ids accumulation
5. ⚠️ Test validation feedback propagation to retry

---

## 10. Final Verification Checklist

Before Wave 4 (graph wiring):

- [ ] All dispatch nodes removed from Section 6
- [ ] All dispatch routers return `List[Send]` or node name string
- [ ] All retry routers return `List[Send]` (selective) or node name
- [ ] `V4PipelineState` has all `failed_*_ids` fields with `Annotated[List, add]`
- [ ] All retry routers increment `*_retry_count`
- [ ] All retry routers inject `validation_feedback` into Send arg
- [ ] Fallback note removed (line 1431)
- [ ] Agent count updated (27 → 22)
- [ ] Instrumentation list updated (5 dispatch nodes removed)
- [ ] Router function signature docs added to Section 6

---

## Appendix: Test Scripts

All test scripts verified on LangGraph 1.0.6:

1. **`/tmp/test_send_with_dispatch_node.py`** — Send API basic pattern ✅
2. **`/tmp/test_parallel_start.py`** — Parallel edges from START ✅
3. **`/tmp/test_correct_retry.py`** — Selective retry with Send ✅

**Runtime:** Python 3.14, LangGraph 1.0.6, backend venv
**Warnings:** Pydantic v1 compatibility (expected, not blocking)

---

## Conclusion

**LangGraph 1.0.6 fully supports V4 architecture** — Send API, parallel edges, conditional retry, selective re-dispatch all work as designed.

**However, V4 graph design has critical errors** that will cause runtime crashes:
1. Dispatch nodes cannot return Send lists (must use router functions)
2. Retry loops route to dispatch nodes (should route directly via Send or use routers)
3. Fallback note implies Send API unavailable (it's fully available)

**All issues are fixable** by removing dispatch nodes and using conditional_edges routers that return Send lists.

**Estimated fix effort:** ~2 hours to update Section 6, ~30 minutes to update state schema.

**Recommendation:** Fix these issues in `docs/audit/16_v4_implementation_plan.md` **before** starting Wave 1 implementation to avoid rework.
