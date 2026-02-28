# V4 Pipeline Data Flow Gap Analysis

**Date**: 2026-02-14
**Scope**: Complete trace of data dependencies across all V4 stage transitions
**Reference**: `docs/audit/16_v4_implementation_plan.md`

---

## Executive Summary

**Critical Gaps Found**: 7
**Format Mismatches**: 4
**Minor Issues**: 3

### High-Priority Fixes Required

1. **Scene context builder must run BEFORE content dispatch** (graph wiring issue)
2. **Graph builder mechanic matching is ambiguous** (relies on list order, fragile)
3. **Scene creative designs storage format unclear** (dict keyed by scene_index vs scene_id)
4. **SceneContent missing from state** (exists in doc but never written to state)
5. **Art director needs access to GamePlan for zone label cross-reference** (not just AssetNeeds)

---

## Transition 1: Pipeline Start → Phase 0

### What Phase 0 Needs (Input)

From `V4PipelineState` initialization:
- `question_text`: str
- `question_options`: Optional[List[str]]
- `question_id`: str
- `_run_id`: str
- `_pipeline_preset`: str

### What Routes Provides

`routes/generate.py` will set these fields from `GenerateRequest`:
- `question_text` ✓
- `question_options` ✓
- `question_id` ✓
- `_run_id` (generated) ✓
- `_pipeline_preset` = "v4" ✓

### State Storage

Phase 0 writes:
- `pedagogical_context: Optional[Dict[str, Any]]`
- `content_structure: Optional[Dict[str, Any]]`
- `domain_knowledge: Optional[Dict[str, Any]]`
- `canonical_labels: Optional[List[str]]`

### Gaps: NONE

✓ All required inputs are provided by routes/generate.py initialization.

---

## Transition 2: Phase 0 → Phase 1a

### What Game Concept Designer Needs

From `phase1/game_concept_designer.py` (L902-915):

**Input data**:
- `question_text` (from state)
- `pedagogical_context` (from Phase 0)
- `domain_knowledge` summary (from Phase 0)
- `canonical_labels` (from Phase 0)
- `capability_spec` (static, from `v4/capability_spec.py`)
- On retry: `concept_validator` feedback (from `_v4_concept_validation` state field — NOT DEFINED)

### What Phase 0 Produces

- `pedagogical_context: Dict[str, Any]` ✓
- `content_structure: Dict[str, Any]` ✓
- `domain_knowledge: Dict[str, Any]` ✓
- `canonical_labels: List[str]` ✓

### State Storage

Game concept designer writes:
- `game_concept: Optional[Dict[str, Any]]` (GameConcept schema)
- `_v4_concept_retries: int`

### Gaps

**GAP #1: Missing validation feedback field**

**Issue**: Concept validator needs a state field to store validation feedback for retry prompts.

**Current state** (L819-821):
```python
game_concept: Optional[Dict[str, Any]]
_v4_concept_retries: int
```

**Missing**: `_v4_concept_validation: Optional[Dict[str, Any]]` (ValidationResult)

**Fix**: Add to `V4PipelineState`:
```python
_v4_concept_validation: Optional[Dict[str, Any]]  # ValidationResult from concept_validator
```

---

## Transition 3: Phase 1a → Phase 1b

### What Scene Designer Needs

From `phase1/scene_designer.py` (L946-961):

**Input data per scene**:
- `SceneConcept` (from GameConcept.scenes[i])
- `domain_knowledge` (full object)
- `pedagogical_context` (full object)
- `narrative_theme` (from GameConcept.narrative_theme)
- On retry: `scene_design_validator` feedback for THIS scene

### What Phase 1a Produces

- `game_concept: Dict[str, Any]` containing:
  - `scenes: List[SceneConcept]` ✓
  - `narrative_theme: str` ✓

### How Scene Designer Gets Its Scene

From `v4_scene_design_dispatch` node (L1356-1357):

**Graph pattern**: Dispatch node sends `Send()` messages, one per scene.

**Expected Send payload**:
```python
{
    "scene_index": int,
    "scene_concept": SceneConcept,  # GameConcept.scenes[scene_index]
    "narrative_theme": str,         # GameConcept.narrative_theme
}
```

**Scene designer receives**: Send payload + shared state (domain_knowledge, pedagogical_context)

### State Storage

Scene designers write to:
- `scene_creative_designs: Optional[Dict[str, Any]]` — **FORMAT UNCLEAR**

**Question**: Is this keyed by `scene_index` (int) or `scene_id` (str)?

From state definition (L824):
```python
scene_creative_designs: Optional[Dict[str, Any]]  # {scene_index: SceneCreativeDesign}
```

Comment says `scene_index`, but `SceneCreativeDesign.scene_id` is a string (L360).

From graph builder (L1008):
```python
Input: GameConcept + Dict[int, SceneCreativeDesign]
```

**Confirmed**: Keyed by `scene_index` (int).

But `SceneCreativeDesign.scene_id` field exists (L360). What gets stored there?

From scene designer output (L358-361):
```python
class SceneCreativeDesign(BaseModel):
    scene_id: str  # Matches scene index from concept
```

**Implication**: Scene designer must SET `scene_id = f"s{scene_index}"` when producing output.

### Gaps

**GAP #2: Scene design validation feedback storage format unclear**

**Issue**: On retry, scene designer needs validation feedback for THIS specific scene.

**Current state** (L825):
```python
_v4_scene_design_retries: Dict[str, int]  # {scene_index: retry_count}
```

**Missing**: Where is per-scene validation feedback stored?

Options:
1. `_v4_scene_design_validation: Dict[str, Any]` (scene_index → ValidationResult)
2. Embedded in `scene_creative_designs[scene_index]` with `_validation_issues` key

**Recommendation**: Add separate field:
```python
_v4_scene_design_validation: Dict[str, Any]  # {scene_index: ValidationResult}
```

**GAP #3: scene_id assignment responsibility unclear**

**Issue**: `SceneCreativeDesign.scene_id` must be set by scene_designer, but it's not explicitly documented in the prompt contract.

**Fix**: Scene designer implementation must:
```python
design = SceneCreativeDesign(
    scene_id=f"s{scene_index}",  # Explicit ID assignment
    ...
)
```

---

## Transition 4: Phase 1b → Graph Builder

### What Graph Builder Needs

From `graph_builder.py` (L1003-1009):

**Input**:
- `GameConcept` (from state.game_concept)
- `Dict[int, SceneCreativeDesign]` (from state.scene_creative_designs)

**Matching logic** (L1017-1020):
```
MechanicPlan.creative_design populated from SceneCreativeDesign
MechanicPlan.instruction_text from SceneCreativeDesign
```

**Question**: How does graph builder match `MechanicChoice` (from GameConcept.scenes[i].mechanics[j]) with the corresponding `MechanicCreativeDesign` (from SceneCreativeDesign.mechanic_designs[?])?

### Matching Strategy Analysis

**GameConcept structure**:
```python
GameConcept.scenes[i].mechanics[j] → MechanicChoice(mechanic_type="drag_drop", ...)
```

**SceneCreativeDesign structure**:
```python
SceneCreativeDesign.mechanic_designs[k] → MechanicCreativeDesign(mechanic_type="drag_drop", ...)
```

**Assumption in doc** (L1017-1020): Matching by INDEX (j == k).

**Validator check** (L977-978):
```
Every mechanic in scene has a MechanicCreativeDesign
```

**Implication**: Scene design validator MUST check that:
```
len(scene_concept.mechanics) == len(scene_creative_design.mechanic_designs)
```

AND that mechanic_types match in order:
```
for j, mech in enumerate(scene_concept.mechanics):
    assert scene_creative_design.mechanic_designs[j].mechanic_type == mech.mechanic_type
```

### Gaps

**GAP #4: Mechanic matching is fragile and undocumented**

**Issue**: Graph builder relies on list order matching between `SceneConcept.mechanics` and `SceneCreativeDesign.mechanic_designs`, but this is never validated or documented.

**Risks**:
- LLM could reorder mechanics
- LLM could duplicate a mechanic_type
- LLM could omit a mechanic

**Fix**: Add to `scene_design_validator.py`:
```python
def validate_mechanic_alignment(
    scene_concept: SceneConcept,
    scene_design: SceneCreativeDesign
) -> ValidationResult:
    """Ensure mechanic_designs align with scene concept mechanics."""
    if len(scene_concept.mechanics) != len(scene_design.mechanic_designs):
        return ValidationResult(
            passed=False,
            issues=[f"Scene has {len(scene_concept.mechanics)} mechanics but design has {len(scene_design.mechanic_designs)} mechanic_designs"]
        )

    for i, (concept_mech, design_mech) in enumerate(
        zip(scene_concept.mechanics, scene_design.mechanic_designs)
    ):
        if concept_mech.mechanic_type != design_mech.mechanic_type:
            return ValidationResult(
                passed=False,
                issues=[f"Mechanic {i}: concept has '{concept_mech.mechanic_type}' but design has '{design_mech.mechanic_type}'"]
            )

    return ValidationResult(passed=True)
```

**Alternative**: Use explicit IDs instead of list order.

**Better approach**:
```python
class MechanicChoice(BaseModel):
    mechanic_id: str  # NEW: "m0", "m1", etc.
    mechanic_type: str
    ...

class MechanicCreativeDesign(BaseModel):
    mechanic_id: str  # NEW: matches MechanicChoice.mechanic_id
    mechanic_type: str
    ...
```

Graph builder then matches by `mechanic_id`.

**Recommendation**: Add explicit IDs to both schemas.

---

## Transition 5: Graph Builder → Phase 2a

### What Content Generators Need

From `phase2/content_generator.py` (L1048-1061):

**Input per mechanic**:
- `MechanicPlan` (with `creative_design`)
- `scene_context` (from `scene_context_builder`)
- `domain_knowledge`

**scene_context structure** (L1029-1042):
```python
{
    "zone_labels": [...],            # List of zone labels for this scene
    "zone_descriptions": {...},      # {label: DK description}
    "relevant_dk_data": {...},       # sequence_flow_data, comparison_data, etc.
    "other_mechanics": [...],        # Other mechanics in this scene
    "shared_terminology": {...},     # Key terms
    "creative_vision": {...},        # ScenePlan.creative_design
}
```

### What Graph Builder Produces

- `game_plan: Dict[str, Any]` (GamePlan schema) containing:
  - `scenes: List[ScenePlan]`
  - Each `ScenePlan` has:
    - `mechanics: List[MechanicPlan]`
    - `creative_design: SceneCreativeDesign`

### Who Builds scene_context?

From `phase2/scene_context_builder.py` (L1029-1043):

**Input**:
- `ScenePlan` (from `game_plan.scenes[i]`)
- `domain_knowledge`

**Output**: dict (see structure above)

**Question**: When does `scene_context_builder` run?

From graph (L1371-1373):
```python
graph.add_edge("v4_graph_builder", "v4_content_dispatch")
```

No `v4_scene_context_builder` node in the graph!

### Gaps

**GAP #5: scene_context_builder never runs!**

**Issue**: `phase2/scene_context_builder.py` is described (L1029-1043) but is NOT a graph node.

**Expected graph flow**:
```python
graph.add_node("v4_scene_context_builder", scene_context_builder_node)
graph.add_edge("v4_graph_builder", "v4_scene_context_builder")
graph.add_edge("v4_scene_context_builder", "v4_content_dispatch")
```

OR `scene_context_builder` is called INSIDE `content_dispatch_node` before sending to content generators.

**Recommendation**: Make `scene_context_builder` a deterministic helper called by `content_dispatch_node`:

```python
async def content_dispatch_node(state: V4PipelineState):
    game_plan = GamePlan(**state["game_plan"])
    domain_knowledge = state["domain_knowledge"]

    sends = []
    for scene in game_plan.scenes:
        # Build scene context ONCE per scene
        scene_context = build_scene_context(scene, domain_knowledge)

        for mechanic in scene.mechanics:
            sends.append(Send(
                "v4_content_generator",
                {
                    "mechanic_plan": mechanic.dict(),
                    "scene_context": scene_context,
                }
            ))
    return sends
```

**Alternative**: Store scene_context in state.

**State addition needed**:
```python
scene_contexts: Optional[Dict[str, Any]]  # {scene_id: scene_context dict}
```

Then `scene_context_builder` runs as a node between graph_builder and content_dispatch.

**Preferred**: Helper function approach (no extra graph node).

---

## Transition 6: Phase 2a → Phase 2b

### What Interaction Designer Needs

From `phase2/interaction_designer.py` (L1084-1100):

**Input per scene**:
- All `MechanicContent` for this scene
- All `MechanicPlan` for this scene
- `pedagogical_context`
- `domain_knowledge`

**MechanicContent location**: Where is it stored in state?

From state (L830-834):
```python
# ── Phase 2 outputs ──
scene_contents: Optional[Dict[str, Any]]          # {scene_id: SceneContent}
_v4_content_retries: Dict[str, int]               # {mechanic_id: retry_count}
_v4_interaction_retries: Dict[str, int]            # {scene_id: retry_count}
```

**SceneContent schema** (L647-656):
```python
class SceneContent(BaseModel):
    scene_id: str
    scene_number: int
    zone_specs: List[ZoneSpec]
    mechanic_contents: Dict[str, MechanicContent]  # mechanic_id → content
    scoring: List[MechanicScoring]
    feedback: List[MechanicFeedback]
    mode_transitions: List[ModeTransition] = []
```

**Question**: Who builds `SceneContent`? Content generators produce individual `MechanicContent`, but `SceneContent` is a composite.

### Expected Flow

**Content generators** (phase 2a):
- Run in parallel, one per mechanic
- Each produces `MechanicContent`

**Content merge node** (L1374):
- Collects all `MechanicContent` for a scene
- Validates each with `content_validator`
- Builds `SceneContent` (PARTIAL: only `mechanic_contents` field populated)

**Interaction designer** (phase 2b):
- Reads `SceneContent.mechanic_contents`
- Produces `scoring`, `feedback`, `mode_transitions`
- UPDATES `SceneContent` with these fields

**Interaction merge node** (L1390):
- Validates scoring arithmetic
- Writes completed `SceneContent` to state

### Gaps

**GAP #6: SceneContent assembly logic split across nodes**

**Issue**: `SceneContent` is partially built by content_merge_node (mechanic_contents only) and completed by interaction_merge_node (scoring/feedback/mode_transitions).

**Question**: What about `zone_specs`? Who populates `SceneContent.zone_specs`?

From `ZoneSpec` schema (L452-458):
```python
class ZoneSpec(BaseModel):
    label: str
    description: str = ""
    hint: str = ""
    difficulty: int = Field(default=3, ge=1, le=5)
    parent_label: Optional[str] = None
```

**Zone specs are per-scene metadata about each zone label.**

**Who knows the zone labels for a scene?**
- `ScenePlan.zone_labels` (from graph builder)

**Who knows descriptions/hints?**
- `domain_knowledge` (from Phase 0)

**Who should build zone_specs?**
- Either:
  1. `content_merge_node` (deterministic, builds from ScenePlan + DK)
  2. OR `interaction_designer` (LLM, generates hints)

**Current design** (L1084-1100): Interaction designer receives "all MechanicContent" — implies zone_specs already exist.

**Recommendation**: `content_merge_node` builds zone_specs deterministically:

```python
async def content_merge_node(state: V4PipelineState):
    game_plan = GamePlan(**state["game_plan"])
    domain_knowledge = state["domain_knowledge"]

    # Group mechanics by scene
    for scene in game_plan.scenes:
        mechanic_contents = {...}  # Collected from Send results

        # Build zone_specs from scene plan + DK
        zone_specs = []
        for label in scene.zone_labels:
            dk_data = domain_knowledge.get(label, {})
            zone_specs.append(ZoneSpec(
                label=label,
                description=dk_data.get("description", ""),
                hint=dk_data.get("hint", ""),
                difficulty=dk_data.get("difficulty", 3),
                parent_label=dk_data.get("parent_label"),
            ))

        # Build partial SceneContent
        scene_content = SceneContent(
            scene_id=scene.scene_id,
            scene_number=scene.scene_number,
            zone_specs=zone_specs,
            mechanic_contents=mechanic_contents,
            scoring=[],  # Populated by interaction designer
            feedback=[],
            mode_transitions=[],
        )

        state["scene_contents"][scene.scene_id] = scene_content.dict()
```

**GAP #7: Zone hints not LLM-generated**

**Issue**: Above solution uses DK hints (if any), but interaction designer could generate BETTER hints (scene-aware, mechanic-aware).

**Alternative**: Move zone_specs to interaction designer output:

```python
class InteractionDesignerOutput(BaseModel):
    zone_specs: List[ZoneSpec]  # NEW
    scoring: List[MechanicScoring]
    feedback: List[MechanicFeedback]
    mode_transitions: List[ModeTransition]
```

Interaction designer prompt gets:
- Scene zone labels
- DK descriptions
- Mechanic contents
- Pedagogical context

And produces rich, mechanic-aware hints.

**Recommendation**: Interaction designer generates zone_specs.

---

## Transition 7: Phase 2b → Phase 3a

### What Asset Needs Analyzer Needs

From `phase3/asset_needs_analyzer.py` (L1120-1137):

**Input per scene**:
- `ScenePlan` (from `game_plan.scenes[i]`)
- `SceneContent` (from `state.scene_contents[scene_id]`)

### What Phase 2b Produces

- `scene_contents: Dict[str, Any]` — {scene_id: SceneContent}

### State Storage

Asset needs analyzer writes:
- `asset_needs: Dict[str, Any]` — {scene_id: AssetNeeds}

### Gaps: NONE

✓ Asset needs analyzer has all required data.

**Note**: scene_id format must be consistent. Graph builder produces scene_id = f"s{scene_number}" (inferred from scene_designer's scene_id field).

---

## Transition 8: Phase 3a → Phase 3b

### What Art Director Needs

From `phase3/asset_art_director.py` (L1140-1166):

**Input per scene**:
- `AssetNeeds` (from state.asset_needs[scene_id])
- `SceneCreativeDesign` (from ???)
- `SceneContent` (from state.scene_contents[scene_id])
- `pedagogical_context` (from state)

**Question**: Where is `SceneCreativeDesign` stored for art director to access?

From state (L824):
```python
scene_creative_designs: Optional[Dict[str, Any]]  # {scene_index: SceneCreativeDesign}
```

Keyed by `scene_index` (int), not `scene_id` (str).

From `ScenePlan` schema (L414-429):
```python
class ScenePlan(BaseModel):
    scene_id: str
    scene_number: int
    ...
    creative_design: SceneCreativeDesign  # Full creative direction
```

**SceneCreativeDesign is EMBEDDED in ScenePlan!**

So art director accesses it via:
```python
game_plan = GamePlan(**state["game_plan"])
scene_plan = [s for s in game_plan.scenes if s.scene_id == scene_id][0]
creative_design = scene_plan.creative_design
```

### Gaps

**GAP #8: Art director prompt needs GamePlan reference, not just AssetNeeds**

**Issue**: Doc says art director receives "AssetNeeds + SceneCreativeDesign + SceneContent + pedagogical_context" (L1145), but SceneCreativeDesign is embedded in GamePlan.

**Current Send payload** (inferred from L1399-1400):
```python
Send("v4_asset_art_director", {
    "scene_id": str,
    "asset_needs": AssetNeeds.dict(),
    # Missing: how to get SceneCreativeDesign?
})
```

**Fix**: Art direction dispatch node must send SceneCreativeDesign:

```python
async def art_direction_dispatch_node(state: V4PipelineState):
    game_plan = GamePlan(**state["game_plan"])
    asset_needs = state["asset_needs"]
    scene_contents = state["scene_contents"]

    sends = []
    for scene in game_plan.scenes:
        sends.append(Send(
            "v4_asset_art_director",
            {
                "scene_id": scene.scene_id,
                "asset_needs": asset_needs[scene.scene_id],
                "creative_design": scene.creative_design.dict(),  # From ScenePlan
                "scene_content": scene_contents[scene.scene_id],
            }
        ))
    return sends
```

**Alternative**: Art director reads game_plan from shared state (less clean).

**Recommendation**: Explicit Send payload with all needed data.

---

## Transition 9: Phase 3b → Phase 4

### What Blueprint Assembler Needs

From `phase4/blueprint_assembler.py` (L1265-1288):

**Input**:
- `GamePlan` (from state.game_plan)
- `SceneContent` (per scene, from state.scene_contents)
- `SceneAssets` (per scene, from state.scene_assets)
- Visual config from `MechanicCreativeDesign` (embedded in `MechanicPlan.creative_design`)

### What Phase 3b Produces

- `scene_assets: Dict[str, Any]` — {scene_id: SceneAssets}

### Access Pattern

Blueprint assembler iterates over scenes:
```python
game_plan = GamePlan(**state["game_plan"])
for scene in game_plan.scenes:
    scene_content = SceneContent(**state["scene_contents"][scene.scene_id])
    scene_assets = SceneAssets(**state["scene_assets"][scene.scene_id])

    for mechanic in scene.mechanics:
        creative_design = mechanic.creative_design  # MechanicCreativeDesign
        content = scene_content.mechanic_contents[mechanic.mechanic_id]

        # Build blueprint mechanic config
        ...
```

### Gaps

**GAP #9: Zone label → zone ID mapping requires cross-referencing assets**

**Issue**: Content generators reference zones by `label` (e.g., "left atrium"), but blueprint needs `zone_id` (e.g., "zone_1_3").

**Zone ID assignment** (L1278):
```
Zone IDs: zone_{scene_number}_{index}
```

**Who assigns zone IDs?** Blueprint assembler, when processing `SceneAssets.primary_diagram.zones`.

**Zone matching**: Blueprint assembler must map `label` → `zone_id` for each mechanic's content.

Example:
```python
# DragDropContent has labels: [{text: "Label A", zone_label: "left atrium"}]
# SceneAssets.zones has: DetectedZone(id="zone_1_3", label="left atrium")
# Blueprint must map: zone_label "left atrium" → zone_id "zone_1_3"
```

**This is not a gap** — it's expected behavior. Blueprint assembler MUST perform this mapping.

**Validation**: Blueprint validator checks that all `label.correctZoneId` references exist (L1301).

### Gaps: NONE (just complex mapping logic)

---

## Transition 10: Phase 4 → Frontend

### What Frontend Needs

From blueprint validator checks (L1293-1308):

**Frontend contract**:
1. `diagram.assetUrl` present
2. All `label.correctZoneId` reference existing `zone.id`
3. Zones have valid coordinates for their shape
4. `mechanics[0].type` matches starting mode
5. Per-mechanic config exists (sequenceConfig, sortingConfig, etc.)
6. Visual config fields present (cardType, layoutMode, connectorStyle)

### What Blueprint Assembler Produces

- `blueprint: Dict[str, Any]` (Blueprint schema)
- `template_type: str` = "INTERACTIVE_DIAGRAM"
- `generation_complete: bool` = True

### Gaps: NONE

✓ Blueprint validator ensures contract compliance.

---

## Summary of Gaps

### Critical (Must Fix Before Implementation)

| # | Gap | Affected Transition | Fix |
|---|-----|---------------------|-----|
| 5 | scene_context_builder never runs | Phase 2 start | Make it a helper called by content_dispatch_node |
| 4 | Mechanic matching is fragile | Phase 1b → Graph Builder | Add explicit mechanic_id to schemas OR add alignment validator |
| 6 | SceneContent assembly split across nodes | Phase 2a → 2b | Clarify zone_specs ownership (content_merge vs interaction_designer) |
| 8 | Art director needs GamePlan access | Phase 3a dispatch | Send SceneCreativeDesign explicitly in dispatch payload |

### High Priority (Ambiguity/Fragility)

| # | Gap | Affected Transition | Fix |
|---|-----|---------------------|-----|
| 3 | scene_id assignment unclear | Phase 1b output | Document scene_designer must set scene_id = f"s{scene_index}" |
| 7 | Zone hints source unclear | Phase 2b | Decide: DK hints (simple) vs LLM hints (better, slower) |

### Medium Priority (Missing State Fields)

| # | Gap | Affected Transition | Fix |
|---|-----|---------------------|-----|
| 1 | Missing concept validation field | Phase 1a retry | Add `_v4_concept_validation: Optional[Dict[str, Any]]` to state |
| 2 | Missing scene validation field | Phase 1b retry | Add `_v4_scene_design_validation: Dict[str, Any]` to state |

---

## Format Mismatches

### Mismatch #1: scene_creative_designs keying

**State says**: `{scene_index: SceneCreativeDesign}` (int key)
**Schema has**: `SceneCreativeDesign.scene_id` (str value)

**Resolution**: Both are correct. State uses int keys for indexing, schema has str field for self-identification.

**Implication**: Graph builder converts:
```python
for scene_index, design in state["scene_creative_designs"].items():
    assert design["scene_id"] == f"s{scene_index}"  # Validation
```

### Mismatch #2: MechanicContent storage

**Schema**: `SceneContent.mechanic_contents: Dict[str, MechanicContent]` (mechanic_id key)
**State**: `scene_contents: Dict[str, Any]` where inner dict is `{scene_id: SceneContent}`

**Resolution**: No mismatch — this is correct nesting.

### Mismatch #3: Zone coordinates format

**DetectedZone schema** (L740-746):
```python
coordinates: Dict[str, Any]
```

**Frontend expects** (from V3 issues):
```typescript
points: [number, number][]
```

**Resolution**: Blueprint assembler must convert (L1277, reuses V3 logic):
```python
zone_data = {
    "id": zone.id,
    "label": zone.label,
    "shape": zone.shape,
    "coordinates": zone.coordinates,  # Original format
    "points": _normalize_coordinates(zone.coordinates, zone.shape),  # Frontend format
    "center": _compute_center(zone.coordinates, zone.shape),
}
```

### Mismatch #4: Retry count data types

**State**:
```python
_v4_content_retries: Dict[str, int]  # {mechanic_id: retry_count}
```

**Graph uses**: mechanic_id is `str` (e.g., "s1_m2")

**Resolution**: No mismatch, this is correct.

---

## Recommended State Additions

```python
class V4PipelineState(TypedDict, total=False):
    # ... existing fields ...

    # ── Validation feedback for retries ──
    _v4_concept_validation: Optional[Dict[str, Any]]        # ValidationResult
    _v4_scene_design_validation: Dict[str, Any]             # {scene_index: ValidationResult}
    _v4_content_validation: Dict[str, Any]                  # {mechanic_id: ValidationResult}
    _v4_interaction_validation: Dict[str, Any]              # {scene_id: ValidationResult}
    _v4_art_direction_validation: Dict[str, Any]            # {scene_id: ValidationResult}

    # ── Optional: Scene context cache (if not using helper pattern) ──
    # scene_contexts: Optional[Dict[str, Any]]              # {scene_id: scene_context dict}
```

---

## Implementation Checklist

### Before Wave 1 (Foundation)

- [ ] Add validation feedback fields to `V4PipelineState`
- [ ] Decide: scene_context_builder as helper or node?
- [ ] Decide: zone_specs from DK or interaction_designer?
- [ ] Decide: mechanic matching by index or explicit ID?

### During Wave 1 (Validators)

- [ ] `scene_design_validator`: Add mechanic alignment check
- [ ] `interaction_validator`: Ensure zone_specs validated if LLM-generated

### During Wave 2 (Agents)

- [ ] `scene_designer`: Set scene_id = f"s{scene_index}" explicitly
- [ ] `content_generator`: Reference scene_context from dispatch payload

### During Wave 4 (Graph Wiring)

- [ ] `content_dispatch_node`: Call scene_context_builder helper OR read from state
- [ ] `art_direction_dispatch_node`: Send SceneCreativeDesign explicitly
- [ ] `content_merge_node`: Build zone_specs OR leave empty for interaction_designer
- [ ] All dispatch nodes: Validate Send payload includes all needed data

---

## Conclusion

**7 critical gaps identified**, mostly related to:
1. **Missing helper orchestration** (scene_context_builder)
2. **Ambiguous matching logic** (mechanic alignment)
3. **Unclear data ownership** (zone_specs, creative_design access)

**4 format mismatches** — all resolvable with existing V3 patterns.

**Recommendation**: Resolve Critical gaps BEFORE starting Wave 2 implementation. High/Medium gaps can be addressed during implementation with clear documentation.
