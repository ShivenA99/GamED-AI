# V4 3-Stage Creative Cascade — Complete Data Flow Specification

**Date**: 2026-02-16
**Status**: DESIGN SPEC — Every field traced from LLM output → blueprint → frontend
**Prerequisite**: `16_v4_implementation_plan.md` (architecture), `types.ts` (frontend contract)

---

## 1. End-to-End Field Flow: What the Frontend Actually Reads

For each mechanic, this traces EXACTLY what the frontend reads from the blueprint, where each field must be produced in the pipeline, and how it flows through the 3 stages.

### Legend
- **S1a** = Game Concept Designer (WHAT mechanics, WHY)
- **S1b** = Scene Designer (HOW it looks/feels — `MechanicCreativeDesign`)
- **GB** = Graph Builder (deterministic — assigns IDs, computes scores, copies creative design)
- **S2a** = Content Generator (generates items/pairs/nodes WITH visual config)
- **S2b** = Interaction Designer (scoring, feedback, zone hints, transitions)
- **ASM** = Blueprint Assembler (deterministic — maps to frontend keys)

---

## 2. Per-Mechanic Field Map

### 2.1 drag_drop

**Frontend reads from**: `blueprint.dragDropConfig`, `blueprint.labels[]`, `blueprint.diagram.zones[]`, `blueprint.distractorLabels[]`, `blueprint.mechanics[].scoring/feedback`

| Frontend Field | Source Stage | Pipeline Path |
|---|---|---|
| `labels[].id` | ASM | `generate_label_id(scene_number, index)` |
| `labels[].text` | S1a | `GameConcept.scenes[].zone_labels[]` |
| `labels[].correctZoneId` | ASM | `label_to_zone_id` mapping from zone matcher |
| `zones[].id` | ASM | `generate_zone_id(scene_number, label)` |
| `zones[].points` | Asset Pipeline | Zone detection → postprocess_zones |
| `zones[].x/y/radius/width/height` | Asset Pipeline | Zone detection |
| `zones[].description` | S2b | Interaction designer → zone_specs |
| `zones[].hint` | S2b | Interaction designer → zone_specs |
| `distractorLabels[]` | S1a | `GameConcept.distractor_labels` |
| `dragDropConfig.interaction_mode` | S1b→S2a | Creative design → content generator emits |
| `dragDropConfig.leader_line_style` | S1b→S2a | `MechanicCreativeDesign.connector_style` → content generator maps |
| `dragDropConfig.leader_line_color` | S1b→S2a | `MechanicCreativeDesign.color_direction` |
| `dragDropConfig.leader_line_animate` | S1b→S2a | Creative → content |
| `dragDropConfig.pin_marker_shape` | S1b→S2a | Creative → content |
| `dragDropConfig.label_anchor_side` | S1b→S2a | Creative → content |
| `dragDropConfig.tray_position` | S1b→S2a | `MechanicCreativeDesign.layout_mode` → mapped |
| `dragDropConfig.tray_layout` | S1b→S2a | Creative → content |
| `dragDropConfig.label_style` | S1b→S2a | `MechanicCreativeDesign.card_type` → mapped |
| `dragDropConfig.placement_animation` | S1b→S2a | Creative → content |
| `dragDropConfig.incorrect_animation` | S1b→S2a | Creative → content |
| `dragDropConfig.zone_idle_animation` | S1b→S2a | Creative → content |
| `dragDropConfig.zone_hover_effect` | S1b→S2a | Creative → content |
| `dragDropConfig.max_attempts` | S1b→S2a | Creative → content |
| `dragDropConfig.shuffle_labels` | S1b→S2a | Creative → content |
| `dragDropConfig.feedback_timing` | S1b→S2a | `MechanicCreativeDesign.feedback_style` → mapped |
| `mechanics[].scoring.strategy` | S2b | Interaction designer |
| `mechanics[].scoring.points_per_correct` | GB | Computed: `points_per_item` |
| `mechanics[].scoring.max_score` | GB | Computed: `expected_item_count × points_per_item` |
| `mechanics[].scoring.partial_credit` | S2b | Interaction designer |
| `mechanics[].feedback.on_correct` | S2b | Interaction designer |
| `mechanics[].feedback.on_incorrect` | S2b | Interaction designer |
| `mechanics[].feedback.on_completion` | S2b | Interaction designer |
| `mechanics[].feedback.misconceptions[]` | S2b | Interaction designer |

### 2.2 click_to_identify

**Frontend reads from**: `blueprint.clickToIdentifyConfig`, `blueprint.identificationPrompts[]` (AT ROOT), `blueprint.diagram.zones[]`

| Frontend Field | Source Stage | Pipeline Path |
|---|---|---|
| `identificationPrompts[].zoneId` | ASM | `label_to_zone_id[target_label]` |
| `identificationPrompts[].prompt` | S2a | Content generator → `ClickToIdentifyContent.prompts[].text` |
| `identificationPrompts[].order` | S2a | Content generator → `prompts[].order` |
| `clickToIdentifyConfig.promptStyle` | S1b→S2a | `MechanicCreativeDesign.prompt_style` |
| `clickToIdentifyConfig.selectionMode` | S1b→S2a | Creative → content |
| `clickToIdentifyConfig.highlightStyle` | S1b→S2a | Creative → content |
| `clickToIdentifyConfig.magnificationEnabled` | S1b→S2a | Creative → content |
| `clickToIdentifyConfig.magnificationFactor` | S1b→S2a | Creative → content |
| `clickToIdentifyConfig.exploreModeEnabled` | S1b→S2a | Creative → content |
| `clickToIdentifyConfig.showZoneCount` | S1b→S2a | Creative → content |
| `clickToIdentifyConfig.instructions` | S1b | `MechanicCreativeDesign.instruction_text` |

### 2.3 trace_path

**Frontend reads from**: `blueprint.tracePathConfig`, `blueprint.paths[]` (AT ROOT), `blueprint.diagram.zones[]`

| Frontend Field | Source Stage | Pipeline Path |
|---|---|---|
| `paths[].id` | ASM | `path_s{scene}_{index}` |
| `paths[].waypoints[].zoneId` | ASM | `label_to_zone_id[waypoint.label]` |
| `paths[].waypoints[].order` | S2a | Content generator |
| `paths[].description` | S2a | Content generator |
| `paths[].requiresOrder` | S2a | Content generator |
| `tracePathConfig.pathType` | S1b→S2a | Creative → content |
| `tracePathConfig.drawingMode` | S1b→S2a | Creative → content |
| `tracePathConfig.particleTheme` | S1b→S2a | `MechanicCreativeDesign` → content |
| `tracePathConfig.particleSpeed` | S1b→S2a | Creative → content (string enum!) |
| `tracePathConfig.colorTransitionEnabled` | S1b→S2a | Creative → content |
| `tracePathConfig.showDirectionArrows` | S1b→S2a | Creative → content |
| `tracePathConfig.showWaypointLabels` | S1b→S2a | Creative → content |
| `tracePathConfig.showFullFlowOnComplete` | S1b→S2a | Creative → content |
| `tracePathConfig.submitMode` | S1b→S2a | Creative → content |
| `tracePathConfig.instructions` | S1b | instruction_text |

### 2.4 sequencing

**Frontend reads from**: `blueprint.sequenceConfig`

| Frontend Field | Source Stage | Pipeline Path |
|---|---|---|
| `sequenceConfig.items[].id` | S2a | Content generator |
| `sequenceConfig.items[].text` | S2a | Content generator (`content` field) |
| `sequenceConfig.items[].description` | S2a | Content generator |
| `sequenceConfig.items[].image` | S2a/Asset | Optional item images |
| `sequenceConfig.items[].icon` | S2a | Content generator |
| `sequenceConfig.correctOrder` | S2a | Content generator (item IDs in order) |
| `sequenceConfig.sequenceType` | S2a | Content generator |
| `sequenceConfig.layout_mode` | S1b→S2a | `MechanicCreativeDesign.layout_mode` |
| `sequenceConfig.interaction_pattern` | S1b→S2a | Creative → content |
| `sequenceConfig.card_type` | S1b→S2a | `MechanicCreativeDesign.card_type` |
| `sequenceConfig.connector_style` | S1b→S2a | `MechanicCreativeDesign.connector_style` |
| `sequenceConfig.show_position_numbers` | S1b→S2a | Creative → content |
| `sequenceConfig.allowPartialCredit` | S2b | Interaction designer |
| `sequenceConfig.instructionText` | S1b | `MechanicCreativeDesign.instruction_text` |

### 2.5 sorting_categories

**Frontend reads from**: `blueprint.sortingConfig`

| Frontend Field | Source Stage | Pipeline Path |
|---|---|---|
| `sortingConfig.categories[].id` | S2a | Content generator |
| `sortingConfig.categories[].label` | S2a | Content generator (NOT `name`!) |
| `sortingConfig.categories[].description` | S2a | Content generator |
| `sortingConfig.categories[].color` | S1b→S2a | `MechanicCreativeDesign.color_direction` or content generator |
| `sortingConfig.items[].id` | S2a | Content generator |
| `sortingConfig.items[].text` | S2a | Content generator (`content` field) |
| `sortingConfig.items[].correctCategoryId` | S2a | Content generator (camelCase!) |
| `sortingConfig.items[].correct_category_ids` | S2a | Multi-category support |
| `sortingConfig.items[].description` | S2a | Content generator |
| `sortingConfig.items[].difficulty` | S2a | Content generator |
| `sortingConfig.sort_mode` | S1b→S2a | `MechanicCreativeDesign.layout_mode` → mapped |
| `sortingConfig.item_card_type` | S1b→S2a | `MechanicCreativeDesign.card_type` |
| `sortingConfig.container_style` | S1b→S2a | Creative → content |
| `sortingConfig.submit_mode` | S1b→S2a | `MechanicCreativeDesign.feedback_style` → mapped |
| `sortingConfig.allow_multi_category` | S1b→S2a | Creative → content |
| `sortingConfig.showCategoryHints` | S1b→S2a | `MechanicCreativeDesign.hint_strategy` → mapped |
| `sortingConfig.instructions` | S1b | instruction_text |

### 2.6 memory_match

**Frontend reads from**: `blueprint.memoryMatchConfig`

| Frontend Field | Source Stage | Pipeline Path |
|---|---|---|
| `memoryMatchConfig.pairs[].id` | S2a | Content generator |
| `memoryMatchConfig.pairs[].front` | S2a | Content generator (NOT `term`!) |
| `memoryMatchConfig.pairs[].back` | S2a | Content generator (NOT `definition`!) |
| `memoryMatchConfig.pairs[].frontType` | S2a | Content generator |
| `memoryMatchConfig.pairs[].backType` | S2a | Content generator |
| `memoryMatchConfig.pairs[].explanation` | S2a | Content generator |
| `memoryMatchConfig.gridSize` | S2a/ASM | Content generator or auto-computed |
| `memoryMatchConfig.game_variant` | S1b→S2a | `MechanicCreativeDesign.match_type` → mapped |
| `memoryMatchConfig.match_type` | S1b→S2a | Creative → content |
| `memoryMatchConfig.card_back_style` | S1b→S2a | Creative → content |
| `memoryMatchConfig.matched_card_behavior` | S1b→S2a | Creative → content |
| `memoryMatchConfig.show_explanation_on_match` | S1b→S2a | Creative → content |
| `memoryMatchConfig.flipDurationMs` | S1b→S2a | Creative → content |
| `memoryMatchConfig.showAttemptsCounter` | S1b→S2a | Creative → content |
| `memoryMatchConfig.instructions` | S1b | instruction_text |

### 2.7 branching_scenario

**Frontend reads from**: `blueprint.branchingConfig`

| Frontend Field | Source Stage | Pipeline Path |
|---|---|---|
| `branchingConfig.nodes[].id` | S2a | Content generator |
| `branchingConfig.nodes[].question` | S2a | Content generator (NOT `prompt`!) |
| `branchingConfig.nodes[].description` | S2a | Content generator |
| `branchingConfig.nodes[].options[].id` | S2a | Content generator |
| `branchingConfig.nodes[].options[].text` | S2a | Content generator |
| `branchingConfig.nodes[].options[].nextNodeId` | S2a | Content generator (camelCase!) |
| `branchingConfig.nodes[].options[].isCorrect` | S2a | Content generator (camelCase!) |
| `branchingConfig.nodes[].options[].consequence` | S2a | Content generator |
| `branchingConfig.nodes[].options[].points` | S2a | Content generator |
| `branchingConfig.nodes[].options[].quality` | S2a | Content generator |
| `branchingConfig.nodes[].isEndNode` | S2a | Content generator (camelCase!) |
| `branchingConfig.nodes[].endMessage` | S2a | Content generator (camelCase!) |
| `branchingConfig.nodes[].node_type` | S2a | Content generator |
| `branchingConfig.nodes[].narrative_text` | S2a | Content generator |
| `branchingConfig.nodes[].ending_type` | S2a | Content generator |
| `branchingConfig.nodes[].imageUrl` | Asset Pipeline | Optional node illustrations |
| `branchingConfig.startNodeId` | S2a | Content generator (camelCase!) |
| `branchingConfig.showPathTaken` | S1b→S2a | Creative → content |
| `branchingConfig.allowBacktrack` | S1b→S2a | Creative → content |
| `branchingConfig.showConsequences` | S1b→S2a | Creative → content |
| `branchingConfig.multipleValidEndings` | S1b→S2a | Creative → content |
| `branchingConfig.narrative_structure` | S1b | `MechanicCreativeDesign` |
| `branchingConfig.instructions` | S1b | instruction_text |

### 2.8 compare_contrast

**Frontend reads from**: `blueprint.compareConfig`

| Frontend Field | Source Stage | Pipeline Path |
|---|---|---|
| `compareConfig.diagramA.id` | ASM | `"diagramA"` |
| `compareConfig.diagramA.name` | S2a | Content generator → `CompareSubject.name` |
| `compareConfig.diagramA.imageUrl` | Asset Pipeline | Primary diagram URL |
| `compareConfig.diagramA.zones[]` | Asset Pipeline | Zone detection on diagram A |
| `compareConfig.diagramB.id` | ASM | `"diagramB"` |
| `compareConfig.diagramB.name` | S2a | Content generator |
| `compareConfig.diagramB.imageUrl` | Asset Pipeline | Second diagram URL |
| `compareConfig.diagramB.zones[]` | Asset Pipeline | Zone detection on diagram B |
| `compareConfig.expectedCategories{}` | S2a | Content generator → `{zone_label: category}` |
| `compareConfig.comparison_mode` | S1b→S2a | `MechanicCreativeDesign.layout_mode` → mapped |
| `compareConfig.category_types[]` | S1b→S2a | Creative → content |
| `compareConfig.category_labels{}` | S1b→S2a | Creative → content |
| `compareConfig.category_colors{}` | S1b→S2a | Creative → content / art director |
| `compareConfig.highlightMatching` | S1b→S2a | Creative → content |
| `compareConfig.exploration_enabled` | S1b→S2a | Creative → content |
| `compareConfig.zoom_enabled` | S1b→S2a | Creative → content |
| `compareConfig.instructions` | S1b | instruction_text |

### 2.9 description_matching

**Frontend reads from**: `blueprint.descriptionMatchingConfig`, `blueprint.diagram.zones[].description`

| Frontend Field | Source Stage | Pipeline Path |
|---|---|---|
| `descriptionMatchingConfig.descriptions{}` | ASM | Rekeyed: zone_label → zone_id using `label_to_zone_id` |
| `descriptionMatchingConfig.mode` | S1b→S2a | Creative → content |
| `descriptionMatchingConfig.show_connecting_lines` | S1b→S2a | Creative → content |
| `descriptionMatchingConfig.defer_evaluation` | S1b→S2a | Creative → content |
| `descriptionMatchingConfig.description_panel_position` | S1b→S2a | Creative → content |
| `zones[].description` | S2a→ASM | Content descriptions copied to zones |

### 2.10 hierarchical

**Frontend reads from**: `blueprint.zoneGroups[]`, `blueprint.labels[]`, `blueprint.diagram.zones[]`

| Frontend Field | Source Stage | Pipeline Path |
|---|---|---|
| `zoneGroups[].id` | ASM | `zg_{scene}_{index}` |
| `zoneGroups[].parentZoneId` | ASM | `label_to_zone_id[parent_label]` |
| `zoneGroups[].childZoneIds[]` | ASM | `label_to_zone_id[child_label]` for each |
| `zoneGroups[].revealTrigger` | S1b→S2a | Creative → content |

---

## 3. Inter-Mechanic Scoring Flow

### 3.1 Score Computation Chain (ALL deterministic)

```
S1a: GameConcept
  └── MechanicChoice.expected_item_count = N
  └── MechanicChoice.points_per_item = P

GB: Graph Builder (deterministic)
  └── MechanicPlan.max_score = N × P
  └── ScenePlan.scene_max_score = Σ(mechanic.max_score) for all mechanics in scene
  └── GamePlan.total_max_score = Σ(scene.scene_max_score) for all scenes

S2b: Interaction Designer (LLM, but validator enforces arithmetic)
  └── MechanicScoring.max_score MUST == MechanicPlan.max_score
  └── MechanicScoring.points_per_correct MUST == MechanicPlan.points_per_item
  └── If LLM gets it wrong → validator fixes deterministically

ASM: Blueprint Assembler
  └── blueprint.totalMaxScore = GamePlan.total_max_score
  └── blueprint.scoringStrategy.max_score = total_max_score
  └── blueprint.scoringStrategy.base_points_per_zone = first mechanic's points_per_item
  └── blueprint.mechanics[i].scoring = MechanicScoring from interaction designer
  └── For multi-scene: GameScene.max_score = ScenePlan.scene_max_score
```

### 3.2 Score Validation Rules (Interaction Validator)

```python
for each mechanic in scene:
    assert scoring.max_score == game_plan.mechanic.max_score
    assert scoring.points_per_correct == game_plan.mechanic.points_per_item
    assert scoring.strategy in ["per_item", "per_correct", "weighted", "binary"]
    assert feedback.on_correct non-empty
    assert feedback.on_incorrect non-empty
    assert feedback.on_completion non-empty
    assert len(feedback.misconceptions) >= 1
```

### 3.3 How Frontend Uses Scoring

The mechanic registry's `getMaxScore()` reads:
- `drag_drop`: `labels.length × points` (from `scoringStrategy.base_points_per_zone`)
- `sequencing`: `sequenceConfig.items.length × points`
- `sorting`: `sortingConfig.items.length × points`
- `memory_match`: `memoryMatchConfig.pairs.length × points`
- `branching`: `branchingConfig.nodes.filter(!isEndNode).length × points`
- `compare`: `Object.keys(compareConfig.expectedCategories).length × points`
- `click_to_identify`: `identificationPrompts.length × points`
- `trace_path`: `paths.reduce(sum waypoints) × points`
- `description_matching`: `zones.filter(z.description).length × points`

**Critical**: The `× points` uses `scoringStrategy.base_points_per_zone` from the blueprint root. This MUST be consistent with `mechanics[].scoring.points_per_correct`.

---

## 4. Inter-Mechanic Transitions

### 4.1 Transition Data Flow

```
S1a: GameConcept
  └── MechanicChoice.advance_trigger = "completion" | "score_threshold" | "time_elapsed" | "user_choice"
  └── MechanicChoice.advance_trigger_value = optional threshold value
  └── SceneConcept.mechanics[] list order defines the progression

GB: Graph Builder (deterministic)
  └── MechanicConnection{from_id, to_id, trigger: resolve_trigger(advance_trigger, from_type)}
  └── resolve_trigger("completion", "drag_drop") → "all_zones_labeled"
  └── resolve_trigger("completion", "sequencing") → "sequence_complete"
  └── etc. (from TRIGGER_MAP in contracts.py)

ASM: Blueprint Assembler
  └── blueprint.modeTransitions[] = [{
        from: from_mechanic_type,      // e.g., "drag_drop"
        to: to_mechanic_type,          // e.g., "sequencing"
        trigger: resolved_trigger,      // e.g., "all_zones_labeled"
        trigger_value: optional,
        animation: "fade",
        message: optional
      }]
```

### 4.2 Frontend Transition Handling

The engine (`mechanicRegistry.ts`) uses `checkTrigger()` per mechanic:
- After each action, checks if the current mechanic's trigger is satisfied
- If satisfied, finds matching `modeTransition` where `from === currentMode`
- Transitions to `modeTransition.to`
- Shows `modeTransition.message` if present
- Uses `modeTransition.animation` for visual transition

**Supported triggers** (from `ModeTransitionTrigger` type):
```
all_zones_labeled, path_complete, percentage_complete, specific_zones,
time_elapsed, user_choice, hierarchy_level_complete,
identification_complete, sequence_complete, sorting_complete,
memory_complete, branching_complete, compare_complete, description_complete
```

### 4.3 What's Missing in Current Implementation

The current assembler hardcodes `animation: "fade"` and `message: None`. The S1b scene designer should specify:
- Transition animation style (contextual to the game narrative)
- Transition message (bridges the narrative between mechanics)

---

## 5. Inter-Scene Transitions

### 5.1 Scene Progression Data Flow

```
S1a: GameConcept
  └── SceneConcept.transition_to_next = "auto" | "score_gated"
  └── SceneConcept.transition_min_score_pct = optional (e.g., 0.7)

GB: Graph Builder (deterministic)
  └── ScenePlan.transition_to_next = SceneTransition{type, min_score_pct}

S1b: Scene Designer
  └── SceneCreativeDesign.transition_narrative = narrative bridge text

ASM: Blueprint Assembler
  └── game_sequence.scenes[].prerequisite_scene = previous scene_id (if score_gated)
  └── game_sequence.scenes[].reveal_trigger = "all_correct" | "percentage"
  └── game_sequence.scenes[].reveal_threshold = min_score_pct × 100
```

### 5.2 Currently Missing in Assembler

The current `_scene_to_game_scene()` doesn't set:
- `prerequisite_scene`
- `reveal_trigger`
- `reveal_threshold`
- `max_score` (per-scene)
- `mechanics[]` per scene
- `mode_transitions[]` per scene

These must be populated from the `ScenePlan` and `SceneCreativeDesign`.

---

## 6. Asset Spec Building Per Mechanic

### 6.1 Which Mechanics Need What Assets

| Mechanic | Primary Diagram | Second Diagram | Item Images | Node Illustrations | Color Palettes |
|---|---|---|---|---|---|
| drag_drop | ✅ (zones) | ❌ | ❌ | ❌ | ❌ |
| click_to_identify | ✅ (zones) | ❌ | ❌ | ❌ | ❌ |
| trace_path | ✅ (zones) | ❌ | ❌ | ❌ | ❌ |
| description_matching | ✅ (zones) | ❌ | ❌ | ❌ | ❌ |
| hierarchical | ✅ (zones) | ❌ | ❌ | ❌ | ❌ |
| sequencing | ❌ (optional bg) | ❌ | ✅ (optional) | ❌ | ❌ |
| sorting_categories | ❌ | ❌ | ✅ (optional) | ❌ | ✅ (category colors) |
| memory_match | ❌ | ❌ | ✅ (card faces, optional) | ❌ | ❌ |
| branching_scenario | ❌ | ❌ | ❌ | ✅ (per-node scenes, optional) | ❌ |
| compare_contrast | ✅ (diagram A) | ✅ (diagram B) | ❌ | ❌ | ✅ (category colors) |

### 6.2 Asset Needs Analysis (Deterministic Node)

```python
def analyze_asset_needs(scene_plan: ScenePlan, scene_content: SceneContent) -> AssetNeeds:
    needs = AssetNeeds(scene_id=scene_plan.scene_id)

    if scene_plan.needs_diagram:
        needs.primary_diagram = DiagramAssetNeed(
            asset_id=f"diagram_{scene_plan.scene_id}",
            scene_id=scene_plan.scene_id,
            expected_labels=scene_plan.zone_labels,
            image_description=scene_plan.image_spec.description if scene_plan.image_spec else "",
            needs_zone_detection=True,
        )

    for mech in scene_plan.mechanics:
        content = scene_content.mechanic_contents.get(mech.mechanic_id)
        if not content: continue

        if mech.mechanic_type == "compare_contrast":
            # Needs TWO diagrams
            needs.second_diagram = DiagramAssetNeed(
                asset_id=f"diagram_{scene_plan.scene_id}_b",
                scene_id=scene_plan.scene_id,
                expected_labels=content.compare_contrast.subject_b.zone_labels,
                image_description=scene_plan.second_image_spec.description if scene_plan.second_image_spec else "",
                needs_zone_detection=True,
            )

        if mech.mechanic_type == "sorting_categories":
            # Category color palette
            categories = content.sorting.categories
            needs.color_palettes.append(ColorPaletteNeed(
                asset_id=f"palette_{mech.mechanic_id}",
                count=len(categories),
                category_labels=[c.label for c in categories],
                mechanic_id=mech.mechanic_id,
            ))

        if mech.mechanic_type == "compare_contrast":
            # Comparison category colors
            needs.color_palettes.append(ColorPaletteNeed(
                asset_id=f"palette_{mech.mechanic_id}",
                count=len(set(content.compare_contrast.expected_categories.values())),
                category_labels=list(set(content.compare_contrast.expected_categories.values())),
                mechanic_id=mech.mechanic_id,
            ))

        # Optional item images
        if mech.mechanic_type == "sequencing" and mech.creative_design.needs_item_images:
            for item in content.sequencing.items:
                if item.image_description:
                    needs.item_images.append(ItemImageNeed(
                        asset_id=f"item_{item.id}",
                        item_id=item.id,
                        description=item.image_description,
                        mechanic_id=mech.mechanic_id,
                    ))

        if mech.mechanic_type == "branching_scenario":
            for node in content.branching.nodes:
                if node.image_description:
                    needs.node_illustrations.append(NodeImageNeed(
                        asset_id=f"node_{node.id}",
                        node_id=node.id,
                        description=node.image_description,
                        mechanic_id=mech.mechanic_id,
                    ))

    return needs
```

### 6.3 Art Direction → Asset Chain → Blueprint

```
Art Director (LLM per scene):
  ├── ArtDirectedDiagram (search_queries, style_prompt, spatial_guidance, negative_prompt)
  ├── ArtDirectedItemImage (search_query, style_prompt, size_hint)
  └── ArtDirectedColorPalette (theme, colors{label→hex}, rationale)

Asset Chains (pre-built, parallel):
  ├── diagram_with_zones chain → DiagramAssetResult (image_url, zones[], zone_match_report)
  ├── simple_image chain → ItemImageResult (image_url)
  └── color_palette chain → ColorPaletteResult (colors{label→hex}) [pass-through]

Blueprint Assembler:
  ├── diagram.assetUrl = DiagramAssetResult.image_url
  ├── diagram.zones = processed detected zones
  ├── compareConfig.diagramA.imageUrl = primary DiagramAssetResult.image_url
  ├── compareConfig.diagramB.imageUrl = second DiagramAssetResult.image_url
  ├── sortingConfig.categories[].color = ColorPaletteResult.colors[label]
  ├── compareConfig.category_colors = ColorPaletteResult.colors
  ├── sequenceConfig.items[].image = ItemImageResult.image_url
  └── branchingConfig.nodes[].imageUrl = NodeImageResult.image_url
```

---

## 7. GameScene Blueprint Structure (Multi-Scene)

Each `GameScene` in `game_sequence.scenes[]` must contain:

```typescript
{
  scene_id: string,                    // From ScenePlan
  scene_number: number,                // 1-indexed
  title: string,                       // From ScenePlan
  narrative_intro: string,             // From SceneCreativeDesign.scene_narrative
  diagram: {
    assetUrl: string | null,           // From asset pipeline
    assetPrompt: string,               // From ImageSpec.description
    zones: Zone[],                     // From zone detection
  },
  labels: Label[],                     // zone_labels → label objects
  max_score: number,                   // ScenePlan.scene_max_score

  // Per-scene mechanics + transitions
  mechanics: Mechanic[],               // All mechanics for this scene with scoring/feedback
  mode_transitions: ModeTransition[],  // Intra-scene mechanic transitions

  // Per-scene tasks (mechanic phases)
  tasks: SceneTask[],                  // One task per mechanic in this scene

  // Per-mechanic configs
  sequenceConfig?: SequenceConfig,     // If scene has sequencing mechanic
  sortingConfig?: SortingConfig,       // If scene has sorting mechanic
  memoryMatchConfig?: MemoryMatchConfig, // etc.
  branchingConfig?: BranchingConfig,
  compareConfig?: CompareConfig,
  clickToIdentifyConfig?: ClickToIdentifyConfig,
  tracePathConfig?: TracePathConfig,
  dragDropConfig?: DragDropConfig,
  descriptionMatchingConfig?: DescriptionMatchingConfig,
  identificationPrompts?: IdentificationPrompt[],
  paths?: TracePath[],
  zoneGroups?: ZoneGroup[],

  // Scene transition
  prerequisite_scene?: string,         // Previous scene_id if score-gated
  reveal_trigger?: string,             // "all_correct" | "percentage"
  reveal_threshold?: number,           // Min score percentage

  // Distractor labels for this scene
  distractorLabels?: DistractorLabel[],

  // Scene scoring
  scoringStrategy?: {
    type: string,
    base_points_per_zone: number,
    max_score: number,
  },
}
```

### 7.1 SceneTask Generation (per mechanic in scene)

Each mechanic in a scene becomes a `SceneTask`:

```python
for mi, mech in enumerate(scene_plan.mechanics):
    task = SceneTask(
        task_id=f"{scene_plan.scene_id}_task_{mi}",
        title=mech.instruction_text[:50],
        mechanic_type=mech.mechanic_type,
        zone_ids=[label_to_zone_id[l] for l in mech.zone_labels_used if l in label_to_zone_id],
        label_ids=[generate_label_id(scene_number, zone_labels.index(l))
                   for l in mech.zone_labels_used if l in zone_labels],
        instructions=mech.instruction_text,
        scoring_weight=mech.max_score / scene_plan.scene_max_score if scene_plan.scene_max_score > 0 else 1.0,
    )
```

---

## 8. Content Schema Expansion Needed

The current `mechanic_content.py` schemas are too thin. They need to include frontend visual config fields that the content generator populates from `MechanicCreativeDesign`.

### What to add per content schema:

**DragDropContent** — add 16 fields:
```python
interaction_mode, feedback_timing, label_style, leader_line_style, leader_line_color,
leader_line_animate, pin_marker_shape, label_anchor_side, tray_position, tray_layout,
placement_animation, incorrect_animation, zone_idle_animation, zone_hover_effect,
max_attempts, shuffle_labels
```

**ClickToIdentifyContent** — add 6 fields:
```python
prompt_style, selection_mode, highlight_style, magnification_enabled,
explore_mode_enabled, show_zone_count
```

**TracePathContent** — add 8 fields:
```python
path_type, drawing_mode, particle_theme, color_transition_enabled,
show_direction_arrows, show_waypoint_labels, show_full_flow_on_complete, submit_mode
```

**SequencingContent** — add 3 fields:
```python
interaction_pattern, card_type, connector_style, show_position_numbers
```
(layout_mode already exists)

**SortingContent** — add 6 fields:
```python
sort_mode, item_card_type, container_style, submit_mode,
allow_multi_category, show_category_hints
```

**MemoryMatchContent** — add 5 fields:
```python
match_type, card_back_style, matched_card_behavior,
show_explanation_on_match, flip_duration_ms, show_attempts_counter
```

**BranchingContent** — add 4 fields:
```python
show_path_taken, allow_backtrack, show_consequences, narrative_structure
```

**DescriptionMatchingContent** — add 3 fields:
```python
show_connecting_lines, defer_evaluation, description_panel_position
```

**CompareContrastContent** (NEW — currently doesn't exist in content schemas):
```python
subject_a: {name, zone_labels}, subject_b: {name, zone_labels},
expected_categories: {label→category}, comparison_mode, category_types,
category_labels, category_colors, highlight_matching, exploration_enabled, zoom_enabled
```

---

## 9. Summary: Changes Needed for Option B

### New Files (~18 files):
1. `phase1/game_concept_designer.py` — replaces `game_designer.py`
2. `phase1/concept_validator.py` — structural validation
3. `phase1/scene_designer.py` — per-scene creative direction (NEW)
4. `phase1/scene_design_validator.py` — validates creative completeness
5. `graph_builder.py` — deterministic Concept + Designs → GamePlan (NEW)
6. Updated `schemas/game_plan.py` — add `GameConcept`, `SceneCreativeDesign`, `MechanicCreativeDesign`
7. Updated `schemas/mechanic_content.py` — add frontend visual config fields
8. `phase3/asset_needs_analyzer.py` — deterministic asset analysis (NEW)
9. `phase3/asset_art_director.py` — LLM art direction (NEW)
10. `phase3/art_direction_validator.py` — art direction validation
11. Updated `prompts/` — concept designer, scene designer, art director prompts
12. Updated `graph.py` — rewired for 3-stage cascade
13. Updated `helpers/blueprint_assembler.py` — copy ALL content fields, populate GameScene fully
14. Updated `routers.py` — concept retry, scene retry, content dispatch, art direction dispatch

### Modified Files:
1. `state.py` — add creative design state fields
2. `contracts.py` — update capability spec for concept designer prompt
3. `validators/content_validator.py` — validate visual config fields present
4. `validators/game_plan_validator.py` — validate graph builder output

### No Changes Needed:
1. Frontend `types.ts` — already has all config interfaces
2. Frontend `mechanicRegistry.ts` — already reads all config keys
3. Frontend `extractTaskConfig.ts` — already resolves from registry
4. Existing services (LLM, Gemini, SAM3, etc.)
