# Backend Audit: Hardcoded Values in Asset, Scene, and Validation Agents

Audited 13 files for hardcoded values that limit game design creativity.
Each finding: `- **[SEVERITY]** file:line -- What's hardcoded -> What it should be`

---

## 1. `backend/app/agents/asset_planner.py`

- **HIGH** `asset_planner.py:109` -- `max_generated_images_per_game` defaults to 5 from PRACTICAL_LIMITS -> Should be configurable per game plan or template
- **MED** `asset_planner.py:132` -- Fallback preferred_methods hardcoded `["url_fetch", "cached", "css_animation"]` -> Should come from config or capability manifest
- **MED** `asset_planner.py:137` -- AI method names hardcoded as `["nanobanana", "dalle", "stable_diffusion"]` for budget check -> Should iterate over a configured set of AI methods
- **HIGH** `asset_planner.py:213` -- Mechanic types matched via hardcoded strings `("drag_drop", "drag-drop", "label", "labeling")` -> Should use MechanicType enum or a centralized mapping
- **MED** `asset_planner.py:219-220` -- Drop zone glow color hardcoded `#3B82F6` (blue), duration 300ms -> Should come from game_plan theme or interaction_design
- **MED** `asset_planner.py:248-249` -- Correct feedback color hardcoded `#10B981` (green), duration 500ms -> Should come from scoring/feedback config
- **MED** `asset_planner.py:259` -- Incorrect feedback shake duration hardcoded 400ms -> Should come from animation config
- **HIGH** `asset_planner.py:267` -- Sequence mechanic types hardcoded `("order", "sequence", "ordering", "sequencing")` -> Should use MechanicType enum
- **MED** `asset_planner.py:279` -- Default sequence item count hardcoded to 8 when empty -> Should be derived from domain knowledge or question
- **MED** `asset_planner.py:293-294` -- Blood flow animation color hardcoded `#EF4444` (red), duration 2000ms -> Should come from theme/subject config, not assume blood flow
- **MED** `asset_planner.py:305` -- Default animation pulse duration hardcoded 500ms -> Should come from animation registry
- **MED** `asset_planner.py:320` -- Completion celebration confetti duration hardcoded 3000ms -> Should come from animation config
- **MED** `asset_planner.py:335` -- Hint pulse color hardcoded `#F59E0B` (amber), duration 600ms -> Should come from theme config
- **LOW** `asset_planner.py:378-379` -- Background prompt suffix hardcoded `"clean, professional"` -> Should come from visual theme
- **MED** `asset_planner.py:437` -- Default animation type fallback hardcoded to `"pulse"` -> Should be configurable
- **MED** `asset_planner.py:558` -- Animation intensity hardcoded `1.0` vs `0.7` based on hierarchy level -> Should be configurable
- **MED** `asset_planner.py:564` -- Hint animation duration hardcoded `400ms`/`300ms` by hierarchy level -> Should come from animation config
- **MED** `asset_planner.py:579` -- Feedback glow color hardcoded `#4CAF50` (green), duration 500ms -> Should come from theme/feedback config
- **MED** `asset_planner.py:716` -- Default workflow fallback hardcoded `"labeling_diagram"` -> Should raise error or infer from context

## 2. `backend/app/agents/asset_generator_orchestrator.py`

- **HIGH** `asset_generator_orchestrator.py:472-473` -- `max_retries=3` and `base_delay=1.0` hardcoded in function signature -> Should be configurable via state or config
- **MED** `asset_generator_orchestrator.py:596-600` -- Fallback chains hardcoded per method (only 3 methods) -> Should be dynamically built from capability manifest
- **MED** `asset_generator_orchestrator.py:616-617` -- Legacy mode retry `max_retries=3`, `base_delay=1.0` hardcoded -> Should match config-driven retries
- **LOW** `asset_generator_orchestrator.py:625` -- Inter-asset delay hardcoded `0.5` seconds -> Should be configurable
- **MED** `asset_generator_orchestrator.py:660` -- Cost estimate hardcoded `$0.02` per Gemini Imagen image -> Should come from cost config and support multiple providers
- **LOW** `asset_generator_orchestrator.py:62-63` -- Entity registry version hardcoded `"1.0"` -> Should come from app config
- **LOW** `asset_generator_orchestrator.py:385` -- Default priority hardcoded to `2` -> Should match asset_planner defaults consistently

## 3. `backend/app/agents/scene_stage1_structure.py`

- **HIGH** `scene_stage1_structure.py:26-29` -- RegionSchema field lengths hardcoded (`min_length=10, max_length=200` for purpose, `max_length=50` for size, `max_length=30` for position) -> Should be more generous or configurable
- **MED** `scene_stage1_structure.py:32` -- `hierarchy_level` max hardcoded to 5 -> May need deeper nesting for complex subjects
- **HIGH** `scene_stage1_structure.py:47-48` -- Valid positions hardcoded to 9 fixed values (`left, right, top, bottom, center...`) -> Should allow arbitrary or percentage-based positioning
- **HIGH** `scene_stage1_structure.py:67` -- `layout_type` regex restricts to exactly 4 types (`center_focus|split_panel|grid|stack`) -> Should be extensible for new layout types
- **MED** `scene_stage1_structure.py:68` -- Max regions hardcoded to 10 -> Complex games may need more regions
- **MED** `scene_stage1_structure.py:64` -- `visual_theme` max_length hardcoded to 50 chars -> Could be limiting for compound themes
- **LOW** `scene_stage1_structure.py:186` -- Default template_type fallback hardcoded `"LABEL_DIAGRAM"` -> Should be explicit or raise
- **MED** `scene_stage1_structure.py:234-247` -- Visual theme suggestions hardcoded per subject (e.g., biology -> "botanical_explorer") in prompt -> Should be driven by theme registry
- **MED** `scene_stage1_structure.py:383-384` -- Fallback structure uses hardcoded visual_theme `"educational"` and layout `"center_focus"` -> Should vary by template type
- **LOW** `scene_stage1_structure.py:457` -- Region purpose minimum length check hardcoded to 15 chars -> Arbitrary threshold

## 4. `backend/app/agents/scene_stage2_assets.py`

- **MED** `scene_stage2_assets.py:26-27` -- Asset width/height capped at 0-100 as percentage -> Locks to percentage-only sizing
- **HIGH** `scene_stage2_assets.py:35` -- Asset type regex restricts to 4 types `(component|animation|image|ui_element)` -> Missing types like `video`, `sprite`, `svg`
- **MED** `scene_stage2_assets.py:42` -- Asset hierarchy_level max hardcoded to 5 -> Should match scene_stage1
- **MED** `scene_stage2_assets.py:57` -- `z_index` capped at 0-100 -> Arbitrary upper bound
- **MED** `scene_stage2_assets.py:62` -- layout_type regex same 4 fixed types -> Should match scene_stage1 enum
- **MED** `scene_stage2_assets.py:85` -- `max_items=50` for required_assets -> Complex games may exceed this
- **HIGH** `scene_stage2_assets.py:113` -- Label asset IDs hardcoded to pattern `label_target_{slug}`, max 8 labels -> Should support unlimited labels
- **HIGH** `scene_stage2_assets.py:201-216` -- `MECHANIC_TO_WORKFLOW_MAP` hardcoded with 13 fixed entries -> Should be auto-derived from MechanicType/WorkflowType enums
- **HIGH** `scene_stage2_assets.py:219-260` -- `MECHANIC_ASSET_PATTERNS` fully hardcoded per mechanic type -> Should be data-driven or in config file
- **MED** `scene_stage2_assets.py:855-856` -- Fallback missing label asset size hardcoded `width=8, height=8` -> Should come from layout calculation
- **LOW** `scene_stage2_assets.py:994-998` -- Warnings for `<3` and `<4+` label targets are hardcoded thresholds -> Should be configurable per game complexity
- **LOW** `scene_stage2_assets.py:1002-1005` -- Asset count warnings hardcoded at `<3` and `>30` -> Arbitrary thresholds

## 5. `backend/app/agents/scene_stage3_interactions.py`

- **MED** `scene_stage3_interactions.py:36` -- Animation duration max hardcoded `le=10000` (10s) -> Some animations may need longer
- **MED** `scene_stage3_interactions.py:42` -- Animation sequence max steps hardcoded to 20 -> Complex sequences may need more
- **MED** `scene_stage3_interactions.py:51` -- Animation duration tolerance hardcoded to 100ms -> Should be proportional
- **MED** `scene_stage3_interactions.py:97-98` -- Max asset_interactions=50, animation_sequences=30, state_transitions=20 -> Arbitrary caps
- **MED** `scene_stage3_interactions.py:169-171` -- Default animation names hardcoded (`glow`, `shake`, `confetti`, `pulse`) -> Should come from animation registry
- **MED** `scene_stage3_interactions.py:179-182` -- Default scoring values hardcoded (base=10, hint_penalty=20, max_score=100) -> Should come from scoring strategy
- **HIGH** `scene_stage3_interactions.py:398-434` -- `transition_patterns` dict fully hardcoded for 7 mechanic pairs -> Should be data-driven or configurable
- **MED** `scene_stage3_interactions.py:405-406` -- Score threshold for drag_drop->sequencing hardcoded to `0.8` -> Should come from game_plan
- **MED** `scene_stage3_interactions.py:417` -- Score threshold for drag_drop->matching hardcoded to `0.7` -> Should come from game_plan
- **LOW** `scene_stage3_interactions.py:248` -- Default reveal_animation hardcoded `"fade_in"` -> Should come from animation config

## 6. `backend/app/agents/playability_validator.py`

- **HIGH** `playability_validator.py:137-141` -- `VALID_INTERACTION_MODES` hardcoded to 11 fixed strings -> Should be derived from InteractionMode Literal or interaction_patterns registry
- **MED** `playability_validator.py:144` -- `VALID_PROGRESSION_TYPES` hardcoded to 4 strings -> Should match ProgressionType enum
- **MED** `playability_validator.py:148-150` -- `VALID_MODE_TRANSITION_TRIGGERS` hardcoded to 7 strings -> Should match TransitionTrigger enum
- **MED** `playability_validator.py:238` -- Minimum valid score threshold hardcoded `0.6` -> Should be configurable
- **HIGH** `playability_validator.py:286` -- Scoring weights tolerance hardcoded to 10% (`abs > 0.1`) -> Should be configurable
- **MED** `playability_validator.py:322` -- Accuracy > 0.95 flagged as "too strict" -> Arbitrary and subject-dependent
- **HIGH** `playability_validator.py:504-506` -- Multi-scene minimum hardcoded to 2 scenes -> Single-scene games should still validate
- **MED** `playability_validator.py:549` -- Zone-based modes hardcoded set `{"drag_drop", "hierarchical", "click_to_identify", "description_matching"}` -> Should derive from pattern registry
- **HIGH** `playability_validator.py:687` -- Zone overlap threshold hardcoded `0.5` of `min_distance` -> Should be configurable based on diagram density
- **HIGH** `playability_validator.py:704-707` -- Minimum labels for playability hardcoded to 3 -> Some games legitimately have 2 labels
- **MED** `playability_validator.py:729-730` -- Semantic coverage thresholds hardcoded `<0.3` fatal, `<0.6` warning -> Should be configurable
- **LOW** `playability_validator.py:1034` -- Generic playability threshold hardcoded `0.5` -> Should match other thresholds

## 7. `backend/app/agents/evaluation.py`

- **HIGH** `evaluation.py:46` -- Pedagogical alignment weight hardcoded `0.30` -> Should be configurable per evaluation run
- **HIGH** `evaluation.py:103` -- Game engagement weight hardcoded `0.25` -> Should be configurable
- **HIGH** `evaluation.py:161` -- Technical quality weight hardcoded `0.25` -> Should be configurable
- **HIGH** `evaluation.py:217` -- Narrative quality weight hardcoded `0.15` -> Should be configurable
- **HIGH** `evaluation.py:275` -- Asset quality weight hardcoded `0.05` -> Should be configurable
- **MED** `evaluation.py:520` -- Artifact JSON truncation hardcoded to 6000 chars -> Should be model context-aware
- **MED** `evaluation.py:554-558` -- Default quality scores on LLM failure hardcoded to `3/5 = 0.6` for all dimensions -> Should clearly indicate evaluation failure
- **MED** `evaluation.py:572-582` -- Fallback scores all hardcoded to `0.5` -> Should be explicitly marked as "not evaluated"

## 8. `backend/app/agents/story_generator.py`

- **HIGH** `story_generator.py:162-193` -- `SUBJECT_THEMES` dict hardcoded with 6 subjects and 4 settings/characters/metaphors each -> Should be extensible or LLM-driven
- **MED** `story_generator.py:288-289` -- Default success/failure narratives hardcoded (`"Excellent work!"`, `"Let's try again."`) -> Should be LLM-generated or template-driven
- **MED** `story_generator.py:324-328` -- Default audio cues hardcoded (`"ambient learning music"`, `"triumphant chime"`) -> Should come from theme config
- **LOW** `story_generator.py:346-347` -- Fallback setting always first item `[0]` from theme -> Should be randomly selected
- **MED** `story_generator.py:351-358` -- `template_frames` dict hardcoded with 7 action frames -> Should be extensible for new templates
- **LOW** `story_generator.py:374` -- Fallback question text truncated at 100 chars -> Arbitrary cutoff

## 9. `backend/app/agents/scene_generator.py`

- **MED** `scene_generator.py:108-109` -- Animation color hardcoded `#FFD700` (gold) for line highlight -> Should come from theme
- **MED** `scene_generator.py:118-119` -- Animation effect `flip_fade` and easing hardcoded -> Should come from animation registry
- **MED** `scene_generator.py:128-130` -- Color range hardcoded `["#4A90E2", "#7B68EE"]` for search range highlight -> Should come from theme
- **HIGH** `scene_generator.py:539-568` -- `_get_default_assets` returns hardcoded assets with string dimensions (`"60%"`, `"400px"`) violating own numeric constraint rules -> Should return numeric values and vary by template
- **MED** `scene_generator.py:581-589` -- Fallback theme selection hardcoded (`"detective"` for CS, `"laboratory"` for science, `"educational"` for other) -> Should be richer or use theme registry

## 10. `backend/app/agents/schemas/game_plan_schemas.py`

- **HIGH** `game_plan_schemas.py:15-26` -- `MechanicType` enum has exactly 10 fixed types -> Adding new mechanics requires code change
- **HIGH** `game_plan_schemas.py:28-35` -- `WorkflowType` enum has exactly 7 fixed types -> Adding new workflows requires code change
- **MED** `game_plan_schemas.py:38-41` -- `ProgressionType` enum has only 3 types (missing `depth_first` that exists elsewhere) -> Inconsistent with playability validator
- **MED** `game_plan_schemas.py:44-50` -- `TransitionTrigger` enum has 6 fixed triggers -> Inconsistent with playability validator's 7 triggers
- **MED** `game_plan_schemas.py:55` -- `scoring_weight` default is `1.0` not normalized -> Multi-mechanic scenes won't sum to 1.0
- **MED** `game_plan_schemas.py:82` -- `ModeTransition.animation` default hardcoded `"fade"` -> Should come from animation config
- **MED** `game_plan_schemas.py:106` -- `SceneTransition.animation` default hardcoded `"slide"` -> Should come from animation config
- **MED** `game_plan_schemas.py:113-117` -- `ScoringRubric` defaults: `max_score=100`, `passing_score=70`, `points_per_correct=10` -> Should be template/difficulty aware
- **LOW** `game_plan_schemas.py:89` -- `SceneBreakdown.scene_number` minimum is 1 -> Precludes zero-indexed scenes

## 11. `backend/app/agents/schemas/label_diagram.py`

- **MED** `label_diagram.py:48` -- Animation duration range hardcoded `ge=50, le=3000` -> Max 3 seconds may be too short for complex animations
- **MED** `label_diagram.py:51` -- Animation intensity range hardcoded `ge=0.1, le=3.0` -> Arbitrary max
- **MED** `label_diagram.py:52` -- Animation delay max hardcoded `le=1000` (1 second) -> May need longer delays for staggered reveals
- **MED** `label_diagram.py:65-66` -- Zone radius range hardcoded `ge=1, le=50` -> Very small or very large zones blocked
- **MED** `label_diagram.py:78` -- `hierarchyLevel` has no upper bound validation (only default=1) -> Inconsistent with RegionSchema's `le=5`
- **MED** `label_diagram.py:84` -- Zone difficulty range hardcoded `ge=1, le=5` -> Five levels may not be granular enough
- **HIGH** `label_diagram.py:158-163` -- Default animation colors hardcoded: correct=`#22c55e`, incorrect=`#ef4444` -> Should come from theme config
- **MED** `label_diagram.py:239` -- `flipDurationMs` default hardcoded to 300ms -> Should come from animation config
- **MED** `label_diagram.py:313` -- MediaAsset `layer` range hardcoded `ge=-10, le=10` -> Arbitrary bounds
- **MED** `label_diagram.py:358-361` -- Temporal constraint priority levels hardcoded (100, 50, 10, 1) -> Should be documented config, not inline magic numbers
- **LOW** `label_diagram.py:393` -- MotionKeyframe scale range `ge=0.1, le=5.0` -> May need 0 scale for hide effects
- **LOW** `label_diagram.py:394` -- Rotation range `ge=-360, le=360` -> Cannot do multi-spin animations
- **MED** `label_diagram.py:527-530` -- Undo max depth hardcoded `ge=1, le=100`, default 20 -> Should be app-level config
- **MED** `label_diagram.py:636` -- `GameScene.scene_number` max hardcoded to 10 -> Limits game complexity
- **MED** `label_diagram.py:676` -- `GameSequence.total_scenes` max hardcoded to 10 -> Same limit
- **LOW** `label_diagram.py:926-928` -- Grid fallback layout uses hardcoded 4 columns -> Should adapt to zone count
- **LOW** `label_diagram.py:938` -- Default zone radius hardcoded to 10 -> Should be relative to diagram size

## 12. `backend/app/agents/workflows/labeling_diagram_workflow.py`

- **MED** `labeling_diagram_workflow.py:157-159` -- Image search params hardcoded: `max_results=5`, `max_queries=4` -> Should be configurable
- **LOW** `labeling_diagram_workflow.py:168` -- `prefer_unlabeled=False` hardcoded -> Should depend on pipeline preset
- **LOW** `labeling_diagram_workflow.py:209` -- HTTP timeout hardcoded `30.0` seconds -> Should come from config
- **MED** `labeling_diagram_workflow.py:448` -- Default zone radius hardcoded `5.0` -> Should come from diagram analysis
- **MED** `labeling_diagram_workflow.py:444` -- Default confidence hardcoded `0.8` for normalized zones -> May over-represent accuracy
- **MED** `labeling_diagram_workflow.py:481` -- Max columns for placeholder grid hardcoded to 3 -> Should adapt to zone count
- **MED** `labeling_diagram_workflow.py:499` -- Placeholder zone radius hardcoded `5.0`, confidence `0.3` -> Should be clearly flagged as unreliable

## 13. `backend/app/config/interaction_patterns.py`

- **MED** `interaction_patterns.py:98` -- `drag_drop` config option `max_attempts` hardcoded to 3 -> Should be game-plan driven
- **MED** `interaction_patterns.py:131` -- `hierarchical` config `max_depth` hardcoded to 5 -> Should come from domain knowledge
- **MED** `interaction_patterns.py:406-409` -- `memory_match` grid_size hardcoded `[4, 4]`, flip_duration `500ms` -> Should adapt to pair count and theme
- **MED** `interaction_patterns.py:439-442` -- `timed_challenge` time_limit hardcoded `60` seconds -> Should come from difficulty config
- **MED** `interaction_patterns.py:616-617` -- Standard scoring `base_points_per_zone=10`, `hint_penalty_percentage=20` hardcoded -> Should come from game plan
- **MED** `interaction_patterns.py:626-628` -- Time-based scoring `base=15`, `time_bonus_max=50`, `hint_penalty=25` hardcoded -> Should come from game plan
- **MED** `interaction_patterns.py:637-638` -- Mastery mode `hint_penalty_percentage=50` hardcoded -> Should be configurable
- **MED** `interaction_patterns.py:647-649` -- Progressive scoring `base=5`, `streak_multiplier=1.5`, `max_multiplier=3.0` hardcoded -> Should come from game plan
- **HIGH** `interaction_patterns.py:891` -- Combined complexity threshold hardcoded `> 8` for warning -> Arbitrary, should be adaptive
- **MED** `interaction_patterns.py:923` -- `suggest_secondary_modes` returns hardcoded `[:3]` top results -> Should be configurable
- **HIGH** `interaction_patterns.py:926-933` -- Bloom's taxonomy to cognitive demands mapping hardcoded with 6 fixed levels -> Should be in a config file or research-backed registry

---

## Summary


| File                            | HIGH   | MED    | LOW    | Total   |
| ------------------------------- | ------ | ------ | ------ | ------- |
| asset_planner.py                | 3      | 12     | 1      | 16      |
| asset_generator_orchestrator.py | 1      | 3      | 3      | 7       |
| scene_stage1_structure.py       | 3      | 4      | 2      | 9       |
| scene_stage2_assets.py          | 4      | 4      | 2      | 10      |
| scene_stage3_interactions.py    | 1      | 8      | 1      | 10      |
| playability_validator.py        | 5      | 3      | 1      | 9       |
| evaluation.py                   | 5      | 3      | 0      | 8       |
| story_generator.py              | 1      | 3      | 2      | 6       |
| scene_generator.py              | 1      | 3      | 0      | 4       |
| game_plan_schemas.py            | 2      | 5      | 1      | 8       |
| label_diagram.py                | 1      | 10     | 4      | 15      |
| labeling_diagram_workflow.py    | 0      | 5      | 2      | 7       |
| interaction_patterns.py         | 2      | 7      | 0      | 9       |
| **TOTAL**                       | **29** | **70** | **19** | **118** |


### Top Priority Fixes (HIGH severity)

1. **Mechanic type matching** -- 5 files use hardcoded string lists instead of `MechanicType` enum
2. **Evaluation weights** -- 5 fixed weights in `evaluation.py` prevent per-run customization
3. **Validation thresholds** -- Playability validator has 5 hardcoded thresholds that prevent varied game designs
4. **Asset type restrictions** -- `scene_stage2_assets.py` restricts to 4 asset types
5. **Layout type restrictions** -- `scene_stage1_structure.py` restricts to 4 layout types
6. **Enum rigidity** -- `MechanicType` (10) and `WorkflowType` (7) require code changes to extend
7. **Image generation budget** -- Hard cap of 5 AI images per game in `asset_planner.py`
8. **Label minimum** -- Playability validator rejects games with fewer than 3 labels

