# V4 Schema Completeness Audit

**Date**: 2026-02-14
**Scope**: Compare the V4 implementation plan schemas against the frontend source of truth (`types.ts`, `mechanicRegistry.ts`, `sceneManager.ts`)
**Status**: COMPLETE -- 43 gaps identified, 8 CRITICAL

---

## 1. GameSpecification vs InteractiveDiagramBlueprint

The plan defines `GameSpecification` as the frontend contract with ~12 fields. The frontend's `InteractiveDiagramBlueprint` has 40+ fields. **24 fields the frontend reads are MISSING from GameSpecification.**

The most critical missing fields:

| Field | Severity | Why |
|-------|----------|-----|
| `templateType: 'INTERACTIVE_DIAGRAM'` | CRITICAL | Hard-coded check in rendering |
| `narrativeIntro: string` | CRITICAL | Used by `sceneToBlueprint()` and display |
| `diagram: { assetPrompt, assetUrl?, zones[], width?, height? }` | CRITICAL | Every mechanic's `extractProps()` reads `bp.diagram.zones`, `bp.diagram.assetUrl` |
| `labels: Label[]` with `correctZoneId` | CRITICAL | drag_drop validation, scoring, completion |
| `animationCues` | CRITICAL | Non-optional `correctPlacement`/`incorrectPlacement` strings |
| `mechanics: Mechanic[]` | CRITICAL | MechanicRouter, engine, registry all depend on this |
| `interactionMode` | HIGH | Starting mode shorthand used throughout state hooks |
| `modeTransitions: ModeTransition[]` | HIGH | Transition evaluator |
| `identificationPrompts: IdentificationPrompt[]` | HIGH | click_to_identify reads this directly (NOT from config) |
| `paths: TracePath[]` | HIGH | trace_path reads this directly (NOT from config) |

Four fields in GameSpecification have NO frontend consumer: `subject`, `question_text`, `learning_objectives`, `pipeline_version`.

**Recommendation**: Abandon `GameSpecification` as a new type. V4's output schema should BE `InteractiveDiagramBlueprint` / `MultiSceneInteractiveDiagramBlueprint`. Reuse existing Pydantic models in `backend/app/agents/schemas/interactive_diagram.py`.

---

## 2. Per-Mechanic Config Schemas

All 9 mechanic config models are listed by name only -- zero field definitions. Key issues per mechanic:

- **click_to_identify**: Needs BOTH `clickToIdentifyConfig` AND separate root-level `identificationPrompts[]`. The registry's `extractProps()` reads `ctx.blueprint.identificationPrompts` directly.
- **trace_path**: Same pattern -- needs `tracePathConfig` AND separate root-level `paths[]`.
- **memory_match**: Field name mismatch. Frontend reads `front`/`back` on pairs. Backend V3 design uses `term`/`definition`. V3 assembler converts at lines 820-821 of `blueprint_assembler_tools.py`.
- **branching_scenario**: Multiple field name mismatches. Frontend reads `question`/`options`/`nextNodeId`/`startNodeId`. Backend uses `prompt`/`choices`/`next_node_id`/`start_node_id`. V3 assembler normalizes at lines 846-898.
- **compare_contrast**: Requires TWO complete `CompareDiagram` objects each with their own `imageUrl` and rect-format zones (`x`, `y`, `width`, `height`).
- **sorting_categories**: Backend `SortingCategoryDesign.name` must become frontend `SortingCategory.label`.
- **description_matching**: Needs BOTH `descriptionMatchingConfig.descriptions` AND `zones[].description` fields populated.

---

## 3. GamePlan Schema Sufficiency

**`ContentBrief` is undefined.** It is referenced as a field on `MechanicPlan` and as input to `content_generator`, but has no schema. Without this, the content_generator has no structured input contract.

ContentBrief must contain per-mechanic guidance. For example, sequencing needs items/correct_order/sequence_type. Branching needs scenario description/node count/structure. Compare_contrast needs two subjects and expected similarities/differences.

---

## 4. SceneSpec and Zone/Label Models

**Zone coordinates**: The plan does not specify format. Frontend expects flat top-level fields (`x`, `y`, `radius` for circle; `points` for polygon; `x`, `y`, `width`, `height` for rect). The V3 assembler stores in nested `coordinates` dict then flattens via `_postprocess_zones()`. V4 must document this normalization.

**`SceneSpec` (assembled scene)**: Never defined. Must match frontend `GameScene` interface which has 30+ fields including all 9 per-mechanic configs in BOTH camelCase and snake_case. The `sceneToBlueprint()` function in `engine/sceneManager.ts` reads both conventions (e.g., `scene.sequenceConfig || scene.sequence_config`).

**Labels**: `correctZoneId` must be a valid zone ID (not label text). Distractor labels must be in a SEPARATE `distractorLabels` array.

---

## 5. Mode Transitions

`MechanicConnection` schema is referenced in `ScenePlan` but never defined. The `from` field in frontend's `ModeTransition` is a Python reserved word; the existing backend uses `from_mode` with `alias="from"` for serialization. `triggerValue` population is not documented (number for `percentage_complete`, `string[]` for `specific_zones`).

---

## 6. Score Models

`ScoringRules` and `FeedbackRules` (outputs of `interaction_designer`) are never defined. Must match frontend `Mechanic.scoring` (`strategy`, `points_per_correct`, `max_score`, `partial_credit`) and `Mechanic.feedback` (`on_correct`, `on_incorrect`, `on_completion`, `misconceptions[]`).

`CompletionRules` is unnecessary -- the frontend handles completion detection via `mechanicRegistry.isComplete()` functions.

---

## 7. Hierarchical Mode Handling

The plan says "hierarchical is a MODE on drag_drop, not a standalone mechanic." But the frontend registers `hierarchical` as a full mechanic in `MECHANIC_REGISTRY` with its own component (`HierarchyController`), `needsDndContext: true`, and a `configKey: null`. It CAN appear as `mechanics[].type` and works as the current mode.

**Recommendation**: Keep `hierarchical` as a valid mechanic type the pipeline can emit. The game_designer says "this scene uses hierarchical" and the assembler emits `mechanics: [{ type: 'hierarchical' }]` with `zoneGroups` populated.

---

## 8. Missing Intermediate Schemas

12 schemas referenced in the plan but never defined:

1. **`ContentBrief`** -- content_generator input (CRITICAL)
2. **`MechanicContent` x9** -- content_generator output per mechanic (CRITICAL)
3. **`ScoringRules`** -- interaction_designer output (HIGH)
4. **`FeedbackRules`** -- interaction_designer output (HIGH)
5. **`CompletionRules`** -- unnecessary, drop from plan (LOW)
6. **`ModeTransitionOutput`** -- interaction_designer output (MEDIUM)
7. **`ImageSpec`** -- referenced in ScenePlan (MEDIUM)
8. **`SceneTransition`** -- referenced in GameSpecification (MEDIUM)
9. **`ThemeConfig`** -- referenced in GameSpecification (MEDIUM)
10. **`TimedConfig`** -- referenced in GameSpecification (MEDIUM)
11. **`HierarchicalConfig`** -- referenced in GameSpecification (MEDIUM)
12. **`SceneContext`** -- internal helper (LOW)

---

## 9. Prioritized Gap List

### CRITICAL (8 items -- must fix before implementation)

| # | Gap | Fix |
|---|-----|-----|
| C1 | `GameSpecification` incompatible with `InteractiveDiagramBlueprint` -- 20+ missing fields | Make output match existing Pydantic models or define complete adapter |
| C2 | `ContentBrief` undefined | Define with per-mechanic content_hints |
| C3 | `MechanicContent` x9 undefined | Define all 9 subclasses |
| C4 | `SceneSpec` (assembled scene) undefined, must match `GameScene` | Define Pydantic model |
| C5 | Per-mechanic config models have zero field definitions | Reuse existing `interactive_diagram.py` models |
| C6 | `animationCues` required but missing from GameSpecification | Add or ensure assembler populates |
| C7 | `diagram` object required at root but missing | Add to output schema |
| C8 | `labels[]` with `correctZoneId` required at root but missing | Add to output schema |

### HIGH (10 items)

| # | Gap | Fix |
|---|-----|-----|
| H1 | `identificationPrompts[]` must be at root, not inside config | Document |
| H2 | `paths[]` must be at root, not inside config | Document |
| H3 | `ScoringRules`/`FeedbackRules` undefined | Define matching frontend shapes |
| H4 | `MechanicConnection` undefined | Define |
| H5 | Memory match `term/definition` vs `front/back` | Output frontend names |
| H6 | Branching `prompt/choices` vs `question/options` | Output frontend names |
| H7 | Zone coordinate format unspecified | Document flat fields |
| H8 | Hierarchical mode vs mechanic reconciliation | Allow as mechanic type |
| H9 | `interactionMode` missing from output | Add or derive |
| H10 | camelCase vs snake_case dual-field pattern | Document |

### MEDIUM (13 items)

| # | Gap | Fix |
|---|-----|-----|
| M1 | `SceneTransition` schema undefined | Define |
| M2 | `ImageSpec` schema undefined | Define |
| M3 | `ThemeConfig` and `TimedConfig` schemas undefined | Define |
| M4 | `HierarchicalConfig` schema undefined | Define |
| M5 | Sorting `name` vs `label` field mismatch | Use `label` |
| M6 | `timedChallengeWrappedMode` and `timeLimitSeconds` missing | Add or emit via timed_config |
| M7 | `distractorLabels` must be separate array at root | Document |
| M8 | compare_contrast zones need `width`/`height` (rect), not circle `radius` | Document per mechanic |
| M9 | `tasks: Task[]` at blueprint root not in GameSpecification | Add |
| M10 | `CompletionRules` unnecessary -- drop from plan | Drop |
| M11 | `scoringStrategy` at root needs `base_points_per_zone` | Ensure assembler populates |
| M12 | `ModeTransitionOutput` schema undefined | Define with 13 trigger types |
| M13 | `description_matching` requires dual sources | Document |

### LOW (5 items)

| # | Gap | Fix |
|---|-----|-----|
| L1 | `mediaAssets`, `motionPaths`, `revealOrder` missing | Add as optional |
| L2 | `hints`, `feedbackMessages` missing | Add as optional |
| L3 | `animations` (StructuredAnimations) missing | Add as optional |
| L4 | `selectionMode` for click_to_identify missing | Add or embed in config |
| L5 | `SceneContext` schema undefined (internal) | Define for clarity |

---

**Total**: 43 gaps. Root cause: The plan designs a "clean" schema without mapping against the 1200-line frontend type system. The frontend's `InteractiveDiagramBlueprint` is the immovable contract.

**Key files referenced**:
- `docs/v4_implementation_plan_final.md` (the plan)
- `frontend/src/components/templates/InteractiveDiagramGame/types.ts` (frontend types -- source of truth)
- `backend/app/agents/schemas/interactive_diagram.py` (existing backend schemas)
- `backend/app/agents/schemas/game_design_v3.py` (V3 design schemas)
- `backend/app/tools/blueprint_assembler_tools.py` (current assembler with all normalizations)
- `frontend/src/components/templates/InteractiveDiagramGame/mechanicRegistry.ts` (registry)
- `frontend/src/components/templates/InteractiveDiagramGame/engine/sceneManager.ts` (sceneToBlueprint)
- `frontend/src/components/templates/InteractiveDiagramGame/utils/extractTaskConfig.ts` (config resolution)
- `docs/v4_formal_graph_rules.html` (FOL validity rules)
