# V4 Prompt & Context Design Audit

**Date**: 2026-02-14
**Scope**: Evaluate the V4 plan's prompt architecture, context scoping, DK integration, structured output reliability, example design, and retry strategies.
**Status**: COMPLETE -- 17 prioritized decisions, risk matrix

---

## 1. Game Designer Prompt Analysis

### Estimated Token Budget: ~5500-8000 tokens

| Section | Tokens | Notes |
|---------|--------|-------|
| System prompt (role, scope, principles) | ~300 | V3's DO/DON'T list must carry forward |
| Capability spec (9 mechanics) | ~1550 | Structured JSON per mechanic |
| Domain knowledge injection | ~1000-3000 | Variable based on DK retrieval |
| Example game plans (2-3) | ~1000-1500 | Few-shot examples |
| Negative constraints | ~150 | "NEVER default to drag_drop", etc. |
| Output format docs | ~200 | Brief field descriptions |
| Retry feedback (if applicable) | ~500 | Validator issues + condensed output |

### Key Design Decisions

1. **Score arithmetic MUST be deterministic**. LLMs cannot do math reliably. V3 had constant score mismatch bugs. Remove `max_score` from GamePlan LLM output. LLM outputs `points_per_item` + `expected_item_count`. Validator computes the rest.

2. **ContentBrief MUST be structured**, not freeform prose. Content_generator needs machine-readable seeds: `{description, key_concepts, expected_complexity, mechanic_specific_hints}`.

3. **Zone label referential integrity** across 3 levels (global -> scene -> mechanic) is the hardest constraint for the LLM to follow.

---

## 2. Content Generator Per-Mechanic Prompts

### 9 Templates Needed (~4500 tokens total, ~500 per mechanic)

Each template has:
1. **Context header** (~50 tokens): "Generate content for {mechanic_type} in scene {N}"
2. **Mechanic-specific instructions** (~150-300 tokens): What fields to produce, quality criteria
3. **DK injection slot** (~100-500 tokens): Filled with projected DK at runtime
4. **Fallback instructions** (~50-100 tokens): "If no {dk_field} is available, generate from question"
5. **Output schema hint** (~50-100 tokens): Brief field list (full schema via response_format)

### Per-Mechanic Token Budgets

| Mechanic | Input Tokens | Risk Level | Notes |
|----------|-------------|------------|-------|
| drag_drop | ~700 | LOW | Simplest -- just labels |
| click_to_identify | ~800 | LOW | Prompts + zone references |
| trace_path | ~1200 | MEDIUM | Waypoints need ordering |
| sequencing | ~1500 | MEDIUM | Items need correct order |
| sorting_categories | ~1500 | MEDIUM | Categories + items |
| memory_match | ~1200 | MEDIUM | Pairs need coherence |
| branching_scenario | ~2500 | HIGH | Valid DAG with nextNodeId |
| compare_contrast | ~2000 | HIGH | Cross-diagram mapping |
| description_matching | ~900 | LOW | Zone descriptions |

### Model Routing (Critical for Success)

| Agent | Model | Rationale |
|-------|-------|-----------|
| game_designer | gemini-2.5-pro (always) | Complex structured output |
| content_generator (branching, compare, sorting, sequencing) | gemini-2.5-pro | Flash fails on complex schemas |
| content_generator (drag_drop, click, trace, description, memory) | gemini-2.5-flash | Simpler output, cost savings |
| interaction_designer | gemini-2.5-flash | Simpler output per scene |

---

## 3. Interaction Designer Prompt

### Token Budget: ~2750-4350 per scene

- One call PER SCENE (not all scenes) -- correct per plan
- Must explicitly count mechanics: "There are exactly N mechanics in this scene"
- Per-mechanic feedback templates (~200-400 tokens each) from V3 should carry forward
- Mode transitions need scoped compatibility matrix injection

### Outputs Must Match Frontend

- `ScoringRules` -> `Mechanic.scoring` (`strategy`, `points_per_correct`, `max_score`, `partial_credit`)
- `FeedbackRules` -> `Mechanic.feedback` (`on_correct`, `on_incorrect`, `on_completion`, `misconceptions[]`)
- `ModeTransitions` -> `modeTransitions[]` (`from`, `to`, `trigger`, `triggerValue`, `animation`, `message`)

---

## 4. Context Scoping via Contracts -- CRITICAL GAP

### DK Field Name Mismatch

**12 DK field names in mechanic contracts DO NOT exist in the DomainKnowledge schema:**

| Contract Field | Actual DK Field | Mapping |
|---------------|-----------------|---------|
| canonical_labels | canonical_labels | Direct match |
| visual_description | (none) | Derived from question |
| key_relationships | hierarchical_relationships | Rename |
| functions | label_descriptions | Approximation |
| processes | sequence_flow_data.flow_description | Nested |
| flow_sequences | sequence_flow_data.sequence_items | Nested |
| temporal_order | sequence_flow_data.sequence_items | Nested |
| categories | comparison_data.sorting_categories | Nested |
| classifications | comparison_data.groups | Nested |
| definitions | label_descriptions | Approximation |
| cause_effect | (none) | Not retrieved |
| misconceptions | (none) | Not retrieved |
| similarities_differences | comparison_data | Approximation |
| hierarchy | hierarchical_relationships | Rename |

**Fix**: Create a `dk_field_resolver.py` (~20 lines) with a mapping dict:

```python
DK_FIELD_MAP = {
    "canonical_labels": "canonical_labels",
    "visual_description": None,
    "key_relationships": "hierarchical_relationships",
    "functions": "label_descriptions",
    "processes": "sequence_flow_data.flow_description",
    # ...
}
```

### Empty DK Fallback Behavior

| Mechanic | Critical DK Field | If Empty |
|----------|-------------------|----------|
| drag_drop | canonical_labels | FATAL -- cannot create game |
| click_to_identify | label_descriptions | DEGRADED -- falls back to generic prompts |
| trace_path | sequence_flow_data | DEGRADED -- LLM generates from question |
| sequencing | sequence_flow_data | DEGRADED -- LLM generates from question |
| sorting_categories | comparison_data | DEGRADED -- LLM generates from question |
| memory_match | label_descriptions | DEGRADED -- LLM generates pairs |
| branching_scenario | (none critical) | OK -- LLM generates decision tree |
| compare_contrast | comparison_data | DEGRADED -- LLM identifies subjects |
| description_matching | label_descriptions | DEGRADED -- LLM generates descriptions |

Only drag_drop has a truly FATAL empty-DK scenario. All others can fall back to LLM generation.

---

## 5. Structured Output Reliability

### Gemini Structured Output Gotchas

| Issue | Severity | Mitigation |
|-------|----------|------------|
| `additionalProperties` not supported | HIGH | Use `ConfigDict(extra="forbid")` |
| Union types (`str \| int`) | MEDIUM | Avoid; use separate fields |
| Deeply nested objects (4+ levels) | MEDIUM | Flatten where possible |
| Flash truncates complex output | HIGH | Route complex mechanics to Pro |
| Optional fields with complex defaults | MEDIUM | Use `None` defaults |
| Self-referencing models | HIGH | Branching uses string IDs, not self-ref -- SAFE |

### Schema Strategy

- Use `extra="allow"` (permissive) on Pydantic models in `response_format` -- strict schemas cause total failure when LLM adds unexpected fields
- Validate strictly in deterministic validators AFTER the LLM call
- Include BOTH schema docs in prompt text AND `response_format` parameter -- LLMs produce better output with both

---

## 6. Example Game Plans

### 3 Examples Needed (~1500 tokens total)

| Example | Tokens | Key Feature |
|---------|--------|-------------|
| Example 1: Single-scene drag_drop | ~300 | Minimal valid GamePlan |
| Example 2: Multi-scene, 3 mechanics | ~700 | Scene transitions, different mechanics |
| Example 3: Non-visual mechanics | ~500 | needs_diagram=false, mechanic connections |

### Example Design Rules

- Use real-ish data (heart anatomy, plant cell) -- well-known topics
- Do NOT include computed `max_score` -- teach LLM to let validator compute it
- Show full ContentBrief with 1-2 sentences of mechanic-specific seed data
- Include `"max_score": "COMPUTED_BY_VALIDATOR"` comment

---

## 7. Retry Prompts

### Pattern (same as V3)

```
## Retry: Previous Output Was Invalid (Attempt {N} of {max_retries})

Your previous output had the following issues:
- [{severity}] {message}
- ...

Your previous output (condensed):
{condensed_previous_output}

Fix ONLY the issues listed above. Do not change parts that were valid.
```

### Key Decisions

- Include CONDENSED previous output (~500 tokens) NOT full (~3000 tokens)
- Max retries: 2 for game_designer, 2 for content_generator, 1 for interaction_designer
- Same V3 pattern: validator issues as bullet list

---

## 8. New Prompt Files Needed

| File | Purpose | Est. Tokens |
|------|---------|-------------|
| `v4/prompts/game_designer.py` | System + task prompt builder | ~800 |
| `v4/prompts/content_generator.py` | 9 per-mechanic templates | ~4500 |
| `v4/prompts/interaction_designer.py` | Scoring/feedback/transitions | ~600 |
| `v4/contracts/capability_spec.py` | JSON capability menu | ~1550 |
| `v4/prompts/input_analyzer.py` | Pedagogical context extraction | ~300 |
| `v4/prompts/examples/` | 3 handcrafted example GamePlans | ~1500 |
| `v4/prompts/retry_templates.py` | Retry prompt templates | ~400 |
| **Total** | | **~9650** |

### Files NOT Needed

- `asset_dispatcher.py` prompt -- executes tool chains, no LLM prompt
- `dk_retriever.py` prompt -- reuses existing with slim modifications
- `blueprint_assembler.py` prompt -- 100% deterministic, no LLM

---

## 9. Prioritized Prompt Design Decisions

### P0: Must Decide Before Writing ANY Code

| # | Decision | Recommendation | Rationale |
|---|----------|----------------|-----------|
| 1 | Score computation: LLM or deterministic? | **Deterministic** | LLMs can't do arithmetic. V3 had constant bugs. |
| 2 | ContentBrief structure | **Structured** (~5 fields) | Content_generator needs machine-readable seeds |
| 3 | DK field name reconciliation | **Mapping layer** (20-line dict) | Least disruptive, no schema changes |
| 4 | Capability spec format | **Structured JSON** per mechanic | More token-efficient than prose |

### P1: Must Decide Before Writing Prompts

| # | Decision | Recommendation | Rationale |
|---|----------|----------------|-----------|
| 5 | Example count and scope | **3 examples** (~1500 tokens) | Cover single/multi-scene/non-visual |
| 6 | Retry: include previous output? | **Condensed** (~500 tokens) | Full doubles cost without proportional benefit |
| 7 | Per-scene vs all-scenes interaction | **Per scene** | Already in plan. Manageable token budget. |
| 8 | Flash vs Pro routing | **Routed by complexity** | V3 proved Flash fails on complex structured output |
| 9 | System prompt caching strategy | **Separated** (static + dynamic) | Token optimization via cache hits |

### P2: Can Decide During Implementation

| # | Decision | Recommendation |
|---|----------|----------------|
| 10 | DK truncation strategy | Hard char limit (4000 chars, V3 pattern) |
| 11 | Empty DK fallback text | Per-mechanic specific instructions |
| 12 | Scoring templates in interaction_designer | Dynamic per-scene (only inject relevant mechanics) |
| 13 | Pydantic response_format strictness | Permissive for LLM, strict in validators |
| 14 | Schema docs in prompt vs response_format | Both (prompt gives semantic understanding) |

### P3: Long-term / Can Defer

| # | Decision | Recommendation |
|---|----------|----------------|
| 15 | TOON/compact serialization | Compact JSON (30-40% whitespace savings) |
| 16 | Cross-run prompt caching | Per-run only (~3000-4500 cacheable tokens) |
| 17 | DSPy prompt optimization | Deferred (need 50+ training runs first) |

---

## Appendix: Risk Matrix

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| LLM produces invalid mechanic_connections graph | HIGH | MEDIUM | Validator catches + retries; include connection example |
| LLM score arithmetic is wrong | VERY HIGH | LOW (after mitigation) | Compute deterministically |
| Empty DK causes degraded content | MEDIUM | MEDIUM | Per-mechanic fallback prompts |
| Flash truncates complex output | MEDIUM | HIGH | Route complex mechanics to Pro |
| Retry prompt exceeds budget | LOW | MEDIUM | Condensed previous output; max 2 retries |
| Example plans bias mechanic selection | MEDIUM | LOW | Diverse examples; negative constraint |
| Branching scenario graph is invalid | HIGH | HIGH | Explicit graph example + connectivity validator |
| DK field names don't match contracts | CERTAIN | MEDIUM | dk_field_resolver mapping |

---

## V3 Learnings to Carry Forward

1. **Gemini Flash cannot follow complex multi-step structured output** -- always use Pro for complex schemas
2. **InteractionSpecV3 scoring/feedback are LISTS, not dicts** -- V4 should use consistent types from start
3. **`additionalProperties` not supported in Gemini** -- use plain `type: "object"` with description
4. **`generation_complete` flag must be set explicitly** -- V4 assembly must set this
5. **Model validators on Pydantic schemas are essential** -- `@model_validator(mode="before")` fixes common LLM errors
6. **Process ordering in system prompt matters** -- context first, constraints second, output format last
7. **State field propagation is #1 failure cause** -- every field must be explicitly written upstream and read downstream
