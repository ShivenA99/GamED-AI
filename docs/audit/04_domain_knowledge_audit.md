# 04 - Domain Knowledge Retrieval Audit

**Scope:** `backend/app/agents/domain_knowledge_retriever.py`, `backend/app/agents/schemas/domain_knowledge.py`, downstream consumers
**Date:** 2026-02-09
**Status:** Audit complete -- per-mechanic data gaps identified

---

## Executive Summary

The domain knowledge retrieval system provides foundational data (canonical labels, hierarchical relationships, sources) that feeds the entire downstream pipeline. It works well for the **drag_drop** mechanic, which only needs labels and relationships, but has significant gaps for six of the seven supported mechanic types. The root cause is twofold: (1) the retriever collects some mechanic-specific data (sequence_flow_data, query_intent) that downstream agents never read, and (2) it does not collect data required by newer mechanics (comparison sets, functional descriptions, category taxonomies, difficulty hints).

The agent is a simple sequential LLM call, not a ReAct agent. Converting it to a ReAct architecture with per-mechanic tools would close the data gaps and allow the retriever to adapt its search strategy based on the mechanic types selected by the router.

**Key numbers:**
- 1 of 7 mechanics fully served (drag_drop)
- 2 of 7 partially served (trace_path, sequencing -- data retrieved but not propagated)
- 4 of 7 not served (click_to_identify partial, description_matching, comparison, sorting)
- 3 schema fields written but never read by any downstream agent

---

## 1. Current Schema Analysis

**File:** `backend/app/agents/schemas/domain_knowledge.py`

### Core Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `query` | `str` | Yes | Original question text |
| `canonical_labels` | `List[str]` | Yes (min 1) | Authoritative label strings for the diagram |
| `acceptable_variants` | `Dict[str, List[str]]` | No | Synonym map keyed by canonical label |
| `hierarchical_relationships` | `List[HierarchicalRelationship]` | No | Parent-child structural relationships |
| `sources` | `List[DomainKnowledgeSource]` | Yes | Web sources used for retrieval |

### Intent and Progression Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `query_intent` | `QueryIntent` | No | Contains `learning_focus`, `depth_preference`, `suggested_progression` |
| `suggested_reveal_order` | `List[str]` | No | Pedagogical ordering of labels for progressive reveal |

### Scene and Sequence Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `scene_hints` | `List[SceneHint]` | No | Suggestions for how to split content into scenes |
| `sequence_flow_data` | `SequenceFlowData` | No | Ordered sequence information for process/cycle questions |
| `content_characteristics` | `ContentCharacteristics` | No | Flags: `needs_labels`, `needs_sequence`, `needs_comparison`, `sequence_type` |

### SequenceFlowData Sub-Schema

| Field | Type | Description |
|-------|------|-------------|
| `flow_type` | `str` | One of: `linear`, `cyclic`, `branching` |
| `sequence_items` | `List[SequenceItem]` | Each item has `id`, `text`, `order_index`, `description`, `connects_to` |
| `flow_description` | `str` | Natural language summary of the flow |

### ContentCharacteristics Sub-Schema

| Field | Type | Description |
|-------|------|-------------|
| `needs_labels` | `bool` | Whether the question requires label identification |
| `needs_sequence` | `bool` | Whether the question involves ordered processes |
| `needs_comparison` | `bool` | Whether the question involves comparing two things |
| `sequence_type` | `Optional[str]` | Type hint if sequence detected (e.g., "cycle", "process") |

---

## 2. Agent Architecture

**Type:** Sequential LLM call (NOT a ReAct agent)

### Execution Phases

```
Phase 0a: _detect_query_intent(question)
    Deterministic keyword matching against question text.
    Sets learning_focus, depth_preference, suggested_progression.
    No LLM call.

Phase 0b: _build_search_query(question, pedagogical_context)
    Customizes the web search query by Bloom's taxonomy level.
    Adjusts search terms based on depth_preference from Phase 0a.

Phase 1: Web Search (Serper API)
    Single API call to Serper.
    Returns top search results as context for the LLM.

Phase 2: LLM Call (guided decoding)
    Single LLM call with search results as context.
    Outputs full DomainKnowledge JSON via structured/guided decoding.
    Populates canonical_labels, acceptable_variants, hierarchical_relationships,
    sources, query_intent, suggested_reveal_order, scene_hints.

Phase 3 (conditional): _search_for_sequence()
    Triggered only if content_characteristics.needs_sequence is true.
    Performs a second web search specifically for sequence/process data.
    Second LLM call extracts SequenceFlowData from results.
```

### Error Handling

- If Serper API fails, the agent falls back to LLM-only generation (no web context).
- If fewer than 4 labels are retrieved, a validation warning is set but execution continues.
- Phase 3 sequence search is wrapped in try/except; failure does not block the pipeline.

---

## 3. What Gets Written to State

| State Field | Value | Condition |
|-------------|-------|-----------|
| `domain_knowledge` | Full dict with all schema fields + `retrieved_at` timestamp + `sequence_flow_data` + `content_characteristics` | Always |
| `current_agent` | `"domain_knowledge_retriever"` | Always |
| `current_validation_errors` | List of validation messages | Only if fewer than 4 canonical labels retrieved |

---

## 4. Downstream Consumer Analysis

### What Downstream Agents Read

| Consumer Agent | Fields Read | Fields Ignored |
|----------------|-------------|----------------|
| `game_planner` | `canonical_labels`, `hierarchical_relationships` | `sequence_flow_data`, `query_intent`, `suggested_reveal_order`, `content_characteristics`, `scene_hints` |
| `blueprint_generator` | `canonical_labels`, `acceptable_variants`, `hierarchical_relationships`, `sequence_flow_data` (FALLBACK ONLY -- used when game_plan lacks sequence data) | `query_intent`, `suggested_reveal_order`, `content_characteristics` |
| V3 tools (context injection) | `domain_knowledge` (as string), `canonical_labels` via `v3_context.py` | Structured sub-fields not individually accessible |
| `scene_generator` (stages 1-3) | `canonical_labels` (indirectly via game_plan) | Direct domain_knowledge access not used |

### Fields Written but Never Read

| Field | Written By | Read By |
|-------|-----------|---------|
| `query_intent` | domain_knowledge_retriever | **Nobody** |
| `suggested_reveal_order` | domain_knowledge_retriever | **Nobody** |
| `content_characteristics` | domain_knowledge_retriever | **Nobody** (only used internally for Phase 3 conditional) |

---

## 5. Per-Mechanic Data Gap Analysis

### Gap Matrix

| Mechanic | Data Needed | Currently Retrieved? | Gap Severity | Details |
|----------|-------------|---------------------|--------------|---------|
| `drag_drop` | canonical_labels, hierarchical_relationships | Yes | **None** | Fully served by existing retrieval |
| `trace_path` | sequence_flow_data (waypoints, connections, flow_type) | Partial | **High** | Data retrieved in Phase 3 but game_planner does not inject it into mechanic spec; blueprint_generator only uses it as fallback |
| `sequencing` | sequence_flow_data (ordered items with order_index) | Partial | **High** | Same as trace_path -- data exists in state but game_planner does not populate `mechanic.sequence_items` |
| `click_to_identify` | labels + difficulty hints + visual cue descriptions | Partial | **Medium** | Labels retrieved; no difficulty gradation or visual cue metadata |
| `description_matching` | functional descriptions per structure/label | No | **Critical** | Retriever does not extract per-label functional descriptions; no schema field for this |
| `comparison` | dual label sets, similarities list, differences list | No | **Critical** | Retriever operates on a single domain; no mechanism to retrieve or structure comparative data |
| `sorting` | categories, classification rules, category membership | No | **Critical** | No category detection or taxonomy extraction in the retriever |

### Detailed Gap Descriptions

**drag_drop (No Gap)**

The retriever's core output (canonical_labels + acceptable_variants + hierarchical_relationships) maps directly to what drag_drop needs: a set of labels and their correct zone assignments. This is the only mechanic with complete coverage.

**trace_path (High Gap)**

The retriever's Phase 3 conditional search produces `sequence_flow_data` with `flow_type`, `sequence_items` (including `connects_to` fields), and `flow_description`. This data describes paths and connections. However, the game_planner agent reads `canonical_labels` and `hierarchical_relationships` but does NOT read `sequence_flow_data`. As a result, when the game_planner creates a trace_path mechanic, it cannot populate waypoint data, connection sequences, or flow directionality. The data exists in state but is stranded.

**sequencing (High Gap)**

Same structural problem as trace_path. The `sequence_flow_data.sequence_items` list contains `order_index` fields that define correct ordering. The game_planner does not consume this data, so `mechanic.sequence_items` in the game plan is never populated from domain knowledge. The blueprint_generator has a fallback path that reads `sequence_flow_data` directly, but this bypasses the game_planner's mechanic-level architecture.

**click_to_identify (Medium Gap)**

Labels are retrieved, but there is no difficulty metadata (e.g., which labels are harder to identify visually) and no visual cue descriptions (e.g., "the mitochondria appears as an oval with inner folds"). The retriever could extract this information from web sources but currently does not.

**description_matching (Critical Gap)**

This mechanic requires mapping each label to a functional description (e.g., "mitochondria" -> "powerhouse of the cell that produces ATP through cellular respiration"). The retriever does not extract per-label descriptions. The `acceptable_variants` field captures synonyms but not functional descriptions. No schema field exists for this data.

**comparison (Critical Gap)**

This mechanic requires two related domains with explicit similarities and differences (e.g., plant cell vs animal cell). The retriever operates on a single question and produces a single set of canonical_labels. There is no mechanism to: (a) detect that a comparison is needed (content_characteristics.needs_comparison exists but is never acted on), (b) retrieve data for two domains, or (c) structure the output as similarity/difference pairs.

**sorting (Critical Gap)**

This mechanic requires items grouped into categories with classification rules (e.g., "classify these organisms as producers, consumers, or decomposers"). The retriever has no category detection, no taxonomy extraction, and no schema field for category membership data.

---

## 6. Critical Disconnects

### Disconnect 1: Game Planner Does Not Use sequence_flow_data

**Impact:** trace_path and sequencing mechanics lack ordered data at the mechanic level.

The domain_knowledge_retriever writes `sequence_flow_data` to state. The game_planner reads `canonical_labels` and `hierarchical_relationships` from domain_knowledge but ignores `sequence_flow_data`. When the game_planner creates mechanics of type `trace_path` or `sequencing`, it cannot populate the mechanic-specific fields (`sequence_items`, `waypoints`, `connections`) because it never reads the source data.

The blueprint_generator partially compensates by reading `sequence_flow_data` directly from domain_knowledge as a fallback, but this bypasses the game_planner's per-mechanic architecture and creates an inconsistency: mechanic specs are incomplete in the game_plan, and the blueprint must reconstruct data that should have been provided upstream.

### Disconnect 2: query_intent Detected but Unused

**Impact:** Pedagogical depth customization is lost.

Phase 0a performs deterministic keyword matching to detect `learning_focus` (e.g., "identify", "explain", "analyze"), `depth_preference` (surface/moderate/deep), and `suggested_progression`. These values are written to state but no downstream agent reads them. This means:

- A question asking students to "analyze" the differences between two cell types gets the same treatment as one asking them to "identify" parts.
- The `depth_preference` could inform how many labels to include, how detailed descriptions should be, or how many scenes to generate, but this information is discarded.
- The `suggested_progression` could feed directly into the game_planner's scene_breakdown, but it does not.

### Disconnect 3: Context Injection Inconsistency (V3 Pipeline)

**Impact:** V3 tools receive domain_knowledge as a flat string, losing structured sub-fields.

In the V3 pipeline, `v3_context.py` injects `domain_knowledge` as a string and `canonical_labels` as a list into the tool context. However, structured sub-fields (`sequence_flow_data`, `query_intent`, `hierarchical_relationships`) are not individually accessible to V3 tools. A V3 game_designer tool that needs to check whether sequence data exists must parse the domain_knowledge string rather than accessing a structured field.

### Disconnect 4: Multi-Mechanic Architecture Incomplete

**Impact:** Game plan mechanics lack type-specific data fields.

The game_planner creates mechanics with a `mechanic_type` field and generic parameters, but there is no mechanism to populate type-specific data. For example:

- A `trace_path` mechanic should have `waypoints` and `connections` but these are not populated.
- A `sequencing` mechanic should have `sequence_items` with `order_index` but these are not populated.
- A `description_matching` mechanic should have `descriptions` per label but these do not exist in the schema.

The game_plan mechanic schema (`MechanicSpec` or equivalent) needs per-type data fields, and the game_planner needs access to the corresponding domain knowledge to fill them.

---

## 7. Proposed Improvements

### Option A: Per-Mechanic Tools (ReAct Conversion)

Convert the domain_knowledge_retriever from a sequential LLM call to a ReAct agent with specialized tools. The agent would receive the question and the router's selected mechanic types, then invoke the appropriate tools.

#### Proposed Tool Set

| Tool | Signature | Returns | Used By Mechanics |
|------|-----------|---------|-------------------|
| `retrieve_sequence_data` | `(question, labels, sequence_type)` | `SequenceFlowData` | trace_path, sequencing |
| `retrieve_comparison_data` | `(question, primary_domain, secondary_domain)` | `ComparisonData` (similarities, differences, dual label sets) | comparison |
| `retrieve_functional_descriptions` | `(labels, subject, blooms_level)` | `Dict[str, str]` (label -> description) | description_matching |
| `retrieve_category_taxonomy` | `(question, items)` | `CategoryData` (categories, rules, membership) | sorting |
| `retrieve_concept_pairs` | `(question, subject)` | `PairData` (paired concepts with relationships) | comparison, description_matching |
| `retrieve_difficulty_hints` | `(labels, visual_context)` | `Dict[str, int]` (label -> difficulty 1-5) | click_to_identify |

#### Execution Flow (ReAct)

```
1. Agent receives question + mechanic_types from router
2. Always: web search + base label extraction (existing Phase 1-2)
3. Conditional tool calls based on mechanic_types:
   - If trace_path or sequencing: call retrieve_sequence_data
   - If comparison: call retrieve_comparison_data
   - If description_matching: call retrieve_functional_descriptions
   - If sorting: call retrieve_category_taxonomy
   - If click_to_identify: call retrieve_difficulty_hints
4. Submit consolidated DomainKnowledge with all mechanic-specific data populated
```

#### New Schema Fields Required

```python
class DomainKnowledge(BaseModel):
    # ... existing fields ...

    # New per-mechanic fields
    functional_descriptions: Dict[str, str] = {}  # label -> description
    comparison_data: Optional[ComparisonData] = None
    category_data: Optional[CategoryData] = None
    difficulty_hints: Dict[str, int] = {}  # label -> difficulty 1-5
    concept_pairs: List[ConceptPair] = []
```

### Option B: Minimal Fix (No ReAct Conversion)

If ReAct conversion is deferred, the following minimal changes would close the highest-severity gaps:

1. **Wire sequence_flow_data to game_planner:** Have the game_planner read `domain_knowledge.sequence_flow_data` and populate mechanic-level sequence fields.
2. **Wire query_intent to game_planner:** Use `depth_preference` to adjust label count and scene count. Use `learning_focus` to inform mechanic selection.
3. **Add functional_descriptions to LLM prompt:** Expand the Phase 2 LLM prompt to extract a one-sentence functional description per canonical label. Add `functional_descriptions: Dict[str, str]` to the schema.
4. **V3 context injection:** Pass structured sub-fields (`sequence_flow_data`, `query_intent`, `hierarchical_relationships`) as individual context variables instead of a single string.

---

## 8. Priority Recommendations

### P0 -- Fix Propagation (No New Data, Just Wiring)

| Action | Files | Impact |
|--------|-------|--------|
| Game planner reads `sequence_flow_data` and populates mechanic-level sequence fields | `game_planner.py`, `game_plan_schemas.py` | Unblocks trace_path and sequencing mechanics |
| Game planner reads `query_intent` for depth/focus decisions | `game_planner.py` | Uses existing data that is currently discarded |
| V3 context injection passes structured sub-fields individually | `v3_context.py` | V3 tools can access sequence_flow_data, query_intent without string parsing |

### P1 -- Extend Existing Retrieval (Schema + Prompt Changes)

| Action | Files | Impact |
|--------|-------|--------|
| Add `functional_descriptions: Dict[str, str]` to DomainKnowledge schema | `domain_knowledge.py` | Enables description_matching mechanic |
| Expand Phase 2 LLM prompt to extract per-label descriptions | `domain_knowledge_retriever.py` | Populates functional_descriptions field |
| Add `difficulty_hints: Dict[str, int]` to schema and prompt | `domain_knowledge.py`, `domain_knowledge_retriever.py` | Enables difficulty-aware click_to_identify |

### P2 -- New Retrieval Capabilities (New Tools or Search Calls)

| Action | Files | Impact |
|--------|-------|--------|
| Add comparison data retrieval (dual-domain search) | `domain_knowledge_retriever.py`, `domain_knowledge.py` | Enables comparison mechanic |
| Add category taxonomy retrieval | `domain_knowledge_retriever.py`, `domain_knowledge.py` | Enables sorting mechanic |

### P3 -- ReAct Conversion (Architecture Change)

| Action | Files | Impact |
|--------|-------|--------|
| Convert domain_knowledge_retriever to ReAct agent | `domain_knowledge_retriever.py`, `graph.py`, `instrumentation.py` | Adaptive retrieval based on mechanic types |
| Implement 6 per-mechanic tools | `backend/app/tools/domain_knowledge_tools.py` (new file) | Full per-mechanic coverage |
| Add validator for domain knowledge completeness per mechanic | `backend/app/agents/domain_knowledge_validator.py` (new file) | Retry loop if mechanic-specific data missing |

---

## Appendix A: State Field Reference

### Fields Written by domain_knowledge_retriever

```python
# In AgentState TypedDict
domain_knowledge: dict  # Full DomainKnowledge schema as dict
current_agent: str      # "domain_knowledge_retriever"
current_validation_errors: list  # Set if < 4 labels
```

### Fields Read by Downstream Agents

```python
# game_planner reads:
state["domain_knowledge"]["canonical_labels"]
state["domain_knowledge"]["hierarchical_relationships"]

# blueprint_generator reads:
state["domain_knowledge"]["canonical_labels"]
state["domain_knowledge"]["acceptable_variants"]
state["domain_knowledge"]["hierarchical_relationships"]
state["domain_knowledge"]["sequence_flow_data"]  # FALLBACK ONLY

# V3 tools read (via context injection):
context.domain_knowledge  # str
context.canonical_labels  # List[str]
```

## Appendix B: Proposed New Schema Types

```python
class ComparisonData(BaseModel):
    """Data for comparison mechanics."""
    primary_domain: str
    secondary_domain: str
    primary_labels: List[str]
    secondary_labels: List[str]
    similarities: List[str]
    differences: List[str]

class CategoryData(BaseModel):
    """Data for sorting/classification mechanics."""
    categories: List[str]
    classification_rules: Dict[str, str]  # category -> rule description
    item_membership: Dict[str, str]       # item -> category

class ConceptPair(BaseModel):
    """A paired concept relationship."""
    concept_a: str
    concept_b: str
    relationship_type: str  # e.g., "structure-function", "cause-effect"
    description: str
```
