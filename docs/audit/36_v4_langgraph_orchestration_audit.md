# V4 LangGraph Orchestration Audit

**Date**: 2026-02-14
**LangGraph Version**: 1.0.6 (installed)
**langgraph-checkpoint-sqlite Version**: 3.0.3 (installed)
**Python Version**: 3.14
**Scope**: V4 pipeline implementation plan evaluated against actual LangGraph 1.0.6 behavior, existing V3 graph wiring, feasibility study (18c), and gap analysis (18).

---

## Executive Summary

The V4 implementation plan has **3 critical issues**, **6 significant issues**, and **4 minor issues**. The most severe:

1. **V4MainState is never defined** -- the plan references it but never specifies its TypedDict shape
2. **Nested Send API does not work as designed** -- Phase 2 proposes per-scene + per-mechanic nested Send, but LangGraph nodes cannot return Send lists
3. **SqliteSaver instantiation is wrong** -- `SqliteSaver.from_conn_string()` returns a context manager, not a saver instance

---

## 1. Sub-Graph State Isolation

### What the Plan Says

Per-phase state isolation with five per-phase TypedDicts and a thin `V4MainState` orchestrator. Each phase is a compiled sub-graph added as a node: `builder.add_node("phase0_context", create_phase0_graph())`.

### Actual LangGraph Behavior (Verified Empirically)

**Two patterns for sub-graphs with different state schemas:**

**Pattern A: Compiled sub-graph as direct node (shared keys only).** When you do `builder.add_node("phase0", create_phase0_graph())`, the compiled sub-graph receives the parent state filtered to only the keys the sub-graph's TypedDict declares. If the sub-graph's TypedDict has keys that do NOT exist in the parent state, LangGraph raises `KeyError` at runtime.

**Pattern B: Wrapper function (state transformation).** A regular node function manually invokes the sub-graph, transforming state before and after. This gives true schema isolation but loses built-in sub-graph checkpointing and streaming.

### CRITICAL ISSUE 1: V4MainState Shape Is Never Defined

The plan mentions `V4MainState` in `state/main_state.py` as a "thin orchestrator state" but never provides its TypedDict definition.

For Pattern A to work, V4MainState MUST contain a **superset of all keys from all per-phase states**. This means the "thin" orchestrator is not thin -- it must include every field that any phase reads or writes (~40-60 fields). The isolation is only conceptual (each phase only touches a subset), not enforced by the type system.

**Recommendation**: Use Pattern A with a complete V4MainState using `total=False`. Accept ~37 fields (still far fewer than V3's 160+). Document which fields each phase reads/writes.

### Field Conflict: Retry Count

All three LLM phases (1, 2, 3) need retry counters. A generic `retry_count` field would be ambiguous. **Fix**: Use phase-specific names: `design_retry_count`, `content_retry_count`, `asset_retry_count`.

---

## 2. Send API for Map-Reduce

### What the Plan Says

Phase 2 uses nested fan-out:
```
FOR EACH scene (via Send):
    FOR EACH mechanic (via Send):
        content_generator -> content_validator -> [retry or pass]
```

### CRITICAL ISSUE 2: Nested Send Does Not Work

LangGraph's Send API has a fundamental constraint: **only conditional edge router functions can return Send lists**. Node functions cannot. This means:

- The outer fan-out (per-scene) works via a router function
- The inner fan-out (per-mechanic WITHIN a scene worker) **does not work** -- the scene worker node cannot return Send objects

**Recommended Alternative (Flatten to Single-Level Send):**

```python
def content_dispatch_router(state):
    sends = []
    for scene in state["game_plan"]["scenes"]:
        scene_context = build_scene_context(scene, state["domain_knowledge"])
        for mechanic in scene["mechanics"]:
            sends.append(Send("content_generator", {
                "scene_id": scene["scene_id"],
                "mechanic_id": mechanic["mechanic_id"],
                "scene_context": scene_context,
                "domain_knowledge": state["domain_knowledge"],
            }))
    return sends
```

This gives maximum parallelism (all mechanics across all scenes simultaneously).

**Alternative: Sequential content with parallel assets only** (recommended for resource constraints):
- Process content sequentially in a single node (loops internally)
- Use Send API only for asset pipeline (biggest time savings)
- Simpler graph, rate-limit safe, easier debugging

### State Merging: Reducer Annotations Required

Without `Annotated[list, operator.add]` on accumulator fields, LangGraph raises `InvalidUpdateError`. **Fields requiring reducers**: `mechanic_contents`, `generated_assets`, `failed_mechanic_ids`, `failed_asset_ids`, all `*_raw` accumulator fields.

### Risk: Duplicate Accumulation on Retry

`operator.add` appends retried results rather than replacing failures. The merge node must deduplicate by ID. However, the merge node's output to a field with `operator.add` reducer will itself be appended. **Fix**: Use a raw accumulator field (with reducer) and a separate deduplicated field (without reducer):

```python
mechanic_contents_raw: Annotated[list[dict], operator.add]  # accumulator
mechanic_contents: list[dict]  # deduplicated, no reducer
```

---

## 3. Retry Loops

### SIGNIFICANT ISSUE 1: Retry Counter Increment Location Unspecified

Router functions should NOT modify state. If the retry counter is only in the router's logic and never written to state, it resets every invocation (infinite loop risk).

**Fix**: Validators increment the counter. Routers only read it.

### SIGNIFICANT ISSUE 2: Max Retries Exceeded Behavior Unspecified

The plan says "max 2 retries" but does not define what happens when exhausted. **Recommendation**: Proceed with warnings. Set `design_validation_override: bool = True` in state so downstream agents know the plan was not fully validated.

### Retry with Send API: Re-entrant Merge

When the retry router returns `[Send("content_generator", {...})]`, the generator runs again and results flow to the merge node AGAIN. The merge node receives ALL PREVIOUS RESULTS + the retry result. It must deduplicate by mechanic_id.

---

## 4. Checkpointing

### CRITICAL ISSUE 3: SqliteSaver Instantiation Is Wrong

The plan shows:
```python
memory = SqliteSaver.from_conn_string(checkpoint_db)
```

`SqliteSaver.from_conn_string()` returns an `Iterator[SqliteSaver]` (context manager), NOT a `SqliteSaver` instance. Passing it directly to `compile(checkpointer=...)` raises:
```
TypeError: Invalid checkpointer provided. Expected BaseCheckpointSaver.
Received _GeneratorContextManager.
```

**Correct patterns:**
```python
# Context manager
with SqliteSaver.from_conn_string("v4.db") as memory:
    graph = builder.compile(checkpointer=memory)

# Direct constructor
import sqlite3
conn = sqlite3.connect("v4.db", check_same_thread=False)
memory = SqliteSaver(conn)
```

### SIGNIFICANT ISSUE 3: Must Use AsyncSqliteSaver

`SqliteSaver` does NOT support async methods. In an async FastAPI handler using `graph.ainvoke()`, LangGraph calls the checkpointer's async methods, which raise `NotImplementedError` with `SqliteSaver`. Must use `AsyncSqliteSaver` from `langgraph.checkpoint.sqlite.aio`.

Neither SQLite checkpointer is recommended for production (use PostgreSQL). Acceptable for V4 prototype.

### Checkpointing + Send API: Verified Working

Checkpointing with Send API works in LangGraph 1.0.6. The checkpointer records initial, intermediate (superstep), and final states. Resume-from-checkpoint replays from last successful checkpoint.

**Caveat**: Send workers are a single superstep. If 2 of 5 fail, the entire superstep fails. On resume, ALL 5 re-run. Selective retry requires the merge-node retry loop pattern (Section 3).

---

## 5. Phase 0 Parallelism

### Contradiction in Existing Documents

The gap analysis (18_v4_gap_analysis) states: "LangGraph StateGraph does NOT support multiple edges from START."

**This is WRONG for LangGraph 1.0.6.** Verified empirically:

```python
g.add_edge(START, "node_a")
g.add_edge(START, "node_b")
g.add_edge("node_a", "merge")
g.add_edge("node_b", "merge")
```

This works. Both nodes run in the same superstep (parallel). `set_entry_point()` only supports one entry, but `add_edge(START, ...)` supports multiple.

**Recommended Phase 0 wiring**: Simple fan-out/fan-in with parallel edges from START. No dispatcher node or Send API needed.

---

## 6. Error Propagation

### SIGNIFICANT ISSUE 4: Per-Scene Failure Kills All

In the Send API model, if one worker raises an exception, the entire superstep fails. One scene's asset failure kills ALL asset generation.

**Fix**: Workers must catch exceptions and return error status in state. The merge node separates successes from failures and feeds failures to the retry router.

### SIGNIFICANT ISSUE 5: Error State Schema Missing

The plan's states do not include error tracking fields. Each phase needs `phase_errors`, `phase_warnings`, and `is_degraded` fields. Without these, error information is lost between phases.

---

## 7. Streaming / Observability

### SIGNIFICANT ISSUE 6: No Streaming Architecture Defined

The plan says nothing about frontend progress updates. LangGraph 1.0.6 supports `astream_events(version="v2")` for granular real-time events (node start/end, LLM tokens, tool calls). These can be delivered via SSE (Server-Sent Events).

**Recommendation**: Implement SSE streaming endpoint from the start. Map LangGraph events to the existing PipelineView observability UI.

---

## 8. Concurrency

**No race conditions** exist in LangGraph's Pregel model. Nodes in a superstep receive the same immutable state snapshot. Updates are batched and merged deterministically via reducers. The only risk is missing reducer annotations, which causes a deterministic `InvalidUpdateError`, not a race condition.

Nodes can safely use `asyncio.gather()` internally for I/O parallelism.

---

## 9. Additional Minor Issues

1. **Gap analysis (18) is wrong about START edges** -- needs correction
2. **SqliteSaver code sample** in plan needs context manager pattern
3. **Inconsistent state name**: plan uses `V4MainState`, gap analysis uses `V4PipelineState` -- standardize
4. **scene_context_builder as graph node is wasteful** -- should be an inline helper call in the dispatch router

---

## 10. Prioritized Issue List

### Critical (Must Fix Before Implementation)

| # | Issue | Impact | Fix |
|---|-------|--------|-----|
| C1 | V4MainState never defined | Cannot compile graph | Define complete TypedDict (~37 fields) with Annotated reducers |
| C2 | Nested Send does not work | Phase 2 broken | Flatten to single-level per-mechanic Send or use sequential content |
| C3 | SqliteSaver instantiation wrong | Compile fails | Use context manager or direct constructor; use AsyncSqliteSaver |

### Significant (Must Fix During Implementation)

| # | Issue | Impact | Fix |
|---|-------|--------|-----|
| S1 | Retry counter location unspecified | Infinite loop risk | Validators increment, routers read |
| S2 | Max retries behavior unspecified | Pipeline hangs | Proceed with warnings + override flag |
| S3 | Must use AsyncSqliteSaver | Async ops fail | Switch from SqliteSaver |
| S4 | One scene failure kills all | Pipeline crash | Catch errors in workers, return status |
| S5 | Error state schema missing | Error info lost | Add phase_errors, is_degraded fields |
| S6 | No streaming architecture | No frontend progress | Implement SSE with astream_events |

### Minor (Can Fix Later)

| # | Issue | Impact | Fix |
|---|-------|--------|-----|
| M1 | Gap analysis wrong about START | Misleading docs | Update 18_v4_gap_analysis.md |
| M2 | SqliteSaver code sample wrong | Copy-paste errors | Update plan |
| M3 | Inconsistent state name | Confusion | Standardize to V4MainState |
| M4 | scene_context_builder as node | Unnecessary overhead | Make inline helper |

---

## 11. V4MainState Draft (~37 Fields)

```python
from typing import TypedDict, Optional, Annotated
import operator

class V4MainState(TypedDict, total=False):
    # Input (immutable)
    question_text: str
    question_id: str
    question_options: Optional[list[str]]
    _run_id: str
    _pipeline_preset: str

    # Phase 0
    pedagogical_context: Optional[dict]
    domain_knowledge: Optional[dict]

    # Phase 1
    game_plan: Optional[dict]
    design_validation: Optional[dict]
    design_retry_count: int
    design_validation_override: bool

    # Phase 2 (Send API accumulation)
    mechanic_contents_raw: Annotated[list[dict], operator.add]
    mechanic_contents: Optional[list[dict]]
    interaction_results: Optional[list[dict]]
    failed_mechanic_ids: Annotated[list[str], operator.add]
    content_retry_count: int

    # Phase 3 (Send API accumulation)
    generated_assets_raw: Annotated[list[dict], operator.add]
    generated_assets: Optional[list[dict]]
    zone_coordinates: Optional[dict]
    failed_asset_ids: Annotated[list[str], operator.add]
    asset_retry_count: int

    # Phase 4
    game_specification: Optional[dict]
    assembly_warnings: Optional[list[str]]

    # Metadata
    generation_complete: bool
    error_message: Optional[str]
    phase_errors: Annotated[list[dict], operator.add]
    is_degraded: bool
    _stage_order: int
    started_at: str
    last_updated_at: str
```

---

## Key Files Referenced

- `docs/v4_implementation_plan_final.md` -- V4 plan (audited)
- `backend/app/agents/graph.py` -- V3 graph wiring
- `backend/app/agents/state.py` -- V3 AgentState (160+ fields)
- `docs/audit/18c_langgraph_feasibility.md` -- Feasibility study
- `docs/audit/18_v4_gap_analysis_langgraph.md` -- Gap analysis
- `docs/audit/18b_data_flow_gaps.md` -- Data flow gaps
