# V4 Pipeline Architecture — Refined Design

**Date**: 2026-02-14
**Status**: DESIGN — pending approval
**Supersedes**: `13_pipeline_v4_brainstorm.md` (incorporated feedback)

---

## 1. Core Principles

### 1.1 The Game Designer is Free

The game designer is a creative agent. It should:
- Design any number of scenes (1-N)
- Use any number of mechanics per scene (1-M)
- Connect mechanics however makes pedagogical sense (sequential, hierarchical, timed wrapper, nested)
- NOT be constrained by our pipeline's limitations

The pipeline's job is to **faithfully realize** whatever the game designer creates — not to limit it.

### 1.2 Game State Graph = Central Artifact

Every game is a DAG with three levels:

```
GameStateGraph
  ├── SceneGraph (Level 1): scene_1 → scene_2 → ... → game_complete
  │     Linear for now (branching deferred)
  │
  ├── MechanicGraph per scene (Level 2):
  │     Mechanics connected via transitions
  │     Supported patterns:
  │       Sequential:   A → B → C → scene_complete
  │       Hierarchical: A contains [A1, A2] → A.complete → B
  │       Timed:        Timer wraps mechanic A → timeout/complete → B
  │       Nested:       A → (on zone X complete) → sub_mechanic A' → A.continue
  │
  └── InteractionGraph per mechanic (Level 3 — frontend-handled):
        Items, zones, prompts, scoring, feedback
        Frontend components know how to run these
```

### 1.3 Pre-Built Asset Tool Chains (No Planning)

Every visual asset the frontend needs maps to exactly ONE pre-tested tool chain. No LLM decides "how" to generate an asset — the chain is selected deterministically by asset type.

### 1.4 Retry = Retry WITH Feedback

Every retry loop passes the validator's specific failure reasons back to the generating stage. No blind retries.

---

## 2. Frontend Asset Catalog

Based on comprehensive audit of all 13 visual asset categories in the frontend:

### 2.1 Asset Types & Tool Chains

| Asset Type | When Needed | Tool Chain | Input | Output |
|-----------|------------|------------|-------|--------|
| **Diagram with zones** | drag_drop, click_to_identify, trace_path, hierarchical, description_matching | `serper → gemini_regen → gemini_flash_bbox → SAM3` | search_query, must_include_labels[], style | `{image_url, zones[{label, shape, coordinates, confidence}]}` |
| **Dual diagrams** | compare_contrast | 2× diagram_with_zones chain (parallel) | subject_a spec, subject_b spec | `{diagram_a: {image_url, zones[]}, diagram_b: {image_url, zones[]}}` |
| **Scene illustration** | branching_scenario node images, narrative backgrounds | `serper → gemini_imagen` | description, style | `{image_url}` |
| **Item card image** | memory_match (frontType=image), sequence items (card_type=image_*), sorting items (image field) | `serper → gemini_imagen` | item_description, size_hint | `{image_url}` |
| **Label thumbnail** | enhanced drag_drop labels (thumbnail_url) | `serper → gemini_imagen` | label_text, context | `{image_url}` |
| **Color palette** | sorting category colors, compare category colors | Deterministic algorithm | count, theme, subject | `{colors: [hex_string]}` |
| **SVG element** | trace_path particles, connector styles | Deterministic SVG gen | element_type, params | `{svg_data}` |

### 2.2 Chain Definitions

```
CHAIN: diagram_with_zones
  Step 1: serper_image_search(query, fallback_queries[]) → reference_image_url
  Step 2: gemini_regenerate(reference_image, style_prompt) → clean_diagram_bytes
          OR imagen_generate(prompt) if no reference found
  Step 3: gemini_flash_bbox(diagram_bytes, labels_to_find[]) → bounding_boxes[]
  Step 4: sam3_segment(diagram_bytes, bounding_boxes[]) → precise_zones[]
  Step 5: zone_matcher(detected_zones[], expected_labels[]) → matched_zones[]
  Output: {image_url, image_path, zones[], match_report}

CHAIN: simple_image
  Step 1: serper_image_search(query) → reference_image_url
  Step 2: gemini_regenerate(reference_image, prompt) → custom_image_bytes
          OR imagen_generate(prompt) if no reference found
  Step 3: save_to_storage(bytes) → image_url
  Output: {image_url, image_path}

CHAIN: color_palette
  Step 1: generate_palette(count, theme) → colors[]
  (deterministic: HSL rotation with subject-aware hue selection)
  Output: {colors: ["#hex", ...]}

CHAIN: svg_particles
  Step 1: select_template(particle_theme) → svg_template
  (deterministic: predefined SVG shapes for dots/arrows/droplets/cells/electrons)
  Output: {svg_data}
```

### 2.3 Per-Mechanic Asset Needs Matrix

| Mechanic | Primary Asset | Optional Assets | Notes |
|----------|--------------|----------------|-------|
| `drag_drop` | diagram_with_zones | label_thumbnails (if enhanced) | Core mechanic |
| `click_to_identify` | diagram_with_zones | — | Zones = clickable targets |
| `trace_path` | diagram_with_zones | svg_particles | Zones = waypoints on path |
| `description_matching` | diagram_with_zones | — | Zones = things to describe |
| `hierarchical` | diagram_with_zones | — | Zones include parent/child |
| `sequencing` | NONE (content-only) | item_card_images (optional) | Cards are text by default |
| `sorting_categories` | NONE (content-only) | item_card_images (optional), color_palette | Buckets are colored |
| `memory_match` | NONE (content-only) | card_images (if frontType/backType = image) | Cards can be text or image |
| `branching_scenario` | NONE (content-only) | scene_illustrations (per node, optional) | Narrative-driven |
| `compare_contrast` | dual_diagrams (REQUIRED) | color_palette | Two different subjects |
| `timed_challenge` | (inherits from wrapped mechanic) | — | Wrapper, no own assets |

---

## 3. Pipeline Architecture

### 3.1 Overview

```
Phase 0: Understanding
  ├── input_analyzer (single LLM call)     ─┐ PARALLEL
  └── dk_retriever (ReAct — web search)     ─┘
              │
Phase 1: Game Design
  ├── game_designer (single structured LLM call — UNRESTRICTED)
  └── game_plan_validator (deterministic → retry with feedback)
              │
Phase 2: Content Build (per scene, per mechanic — Map-Reduce)
  ├── scene_context_builder (deterministic — shared context for scene)
  ├── mechanic_content_generators (parallel, scene-aware)
  ├── mechanic_content_validators (deterministic → retry with feedback)
  └── scene_interaction_designer (scoring + feedback + transitions)
              │
Phase 3: Asset Pipeline (per scene — Map-Reduce)
  ├── scene_asset_orchestrator (deterministic — builds asset manifest)
  ├── asset_dispatchers (parallel — one per asset need, using pre-built chains)
  └── asset_validator (deterministic — zone matching, completeness)
              │
Phase 4: Assembly
  ├── blueprint_assembler (deterministic)
  └── blueprint_validator (deterministic → warnings)
```

### 3.2 Phase 0: Understanding

**No changes from v4 brainstorm.** Two parallel stages:

```
┌─────────────────────────────────┐
│  input_analyzer                  │
│  Model: gemini-2.5-flash         │
│  Type: single structured call    │
│  Output: pedagogical_context     │
│    + content_structure           │
│    {primary_type, has_labels,    │
│     has_sequence, has_comparison, │
│     has_hierarchy, visual_needs}  │
└──────────┬──────────────────────┘
           │                        ← PARALLEL
┌──────────┴──────────────────────┐
│  dk_retriever                    │
│  Model: gemini-2.5-flash         │
│  Type: ReAct (web search)        │
│  Output: domain_knowledge        │
│    + canonical_labels            │
│  Enhanced: reads content_structure│
│    to know what to search for    │
│  Always populates ALL fields     │
└─────────────────────────────────┘
```

**Retry**: dk_retriever has internal retry (search fails → try alternate queries). No external retry needed.

### 3.3 Phase 1: Game Design — THE CREATIVE STAGE

This is where the magic happens. The game designer has FULL CREATIVE FREEDOM.

```
┌─────────────────────────────────┐
│  game_designer                   │
│  Model: gemini-2.5-pro           │
│  Temp: 0.7                       │
│  Type: single structured call    │
│                                  │
│  Input:                          │
│    - question_text               │
│    - pedagogical_context         │
│    - domain_knowledge            │
│    - canonical_labels            │
│    - CAPABILITY SPEC (injected)  │
│    - EXAMPLE GAMES (injected)    │
│                                  │
│  Output: GamePlan                │
│    (complete game state graph)   │
└──────────┬──────────────────────┘
           │
┌──────────▼──────────────────────┐
│  game_plan_validator             │
│  Type: deterministic             │
│  Checks: graph validity,         │
│    mechanic compatibility,       │
│    score arithmetic,             │
│    asset need derivability       │
│                                  │
│  On failure:                     │
│    → sends feedback to           │
│      game_designer (max 2 retry) │
│    Feedback includes:            │
│      - which checks failed       │
│      - why they failed           │
│      - what to fix               │
└─────────────────────────────────┘
```

#### What Makes the Game Designer "Free"

The prompt includes a **Capability Spec** — a menu of everything the game engine supports:

```
CAPABILITY SPEC (injected into prompt):
{
  "available_mechanics": [
    {
      "type": "drag_drop",
      "description": "Player drags labels onto zones in a diagram",
      "needs_diagram": true,
      "content_needs": "zone_labels + optional distractor_labels",
      "best_for": "labeling, identifying parts, spatial relationships",
      "scoring": "per correct label placement"
    },
    {
      "type": "sequencing",
      "description": "Player arranges items in correct order",
      "needs_diagram": false,
      "content_needs": "3-10 items with text, descriptions, correct order",
      "best_for": "processes, timelines, step-by-step procedures",
      "scoring": "per correct position"
    },
    {
      "type": "branching_scenario",
      "description": "Player makes decisions in a narrative tree",
      "needs_diagram": false,
      "content_needs": "4-8 decision nodes with options and consequences",
      "best_for": "clinical reasoning, ethical dilemmas, problem-solving",
      "scoring": "per optimal decision"
    },
    // ... all 10 mechanics
  ],
  "connection_patterns": [
    {
      "type": "sequential",
      "description": "Complete mechanic A, then move to mechanic B",
      "trigger": "completion",
      "example": "First label the heart, then trace blood flow"
    },
    {
      "type": "hierarchical",
      "description": "Complete parent task, then unlock child sub-tasks",
      "trigger": "parent_completion",
      "example": "Label major organs, then for each organ label its parts"
    },
    {
      "type": "timed_wrapper",
      "description": "Wrap any mechanic with a countdown timer",
      "trigger": "time_elapsed OR wrapped_complete",
      "example": "Label all parts within 60 seconds"
    },
    {
      "type": "score_gated",
      "description": "Must score above threshold to proceed",
      "trigger": "score_threshold",
      "example": "Score 80% on labeling to unlock the sorting challenge"
    }
  ],
  "scene_rules": {
    "max_scenes": 6,
    "mechanics_per_scene": "1-4 recommended",
    "scene_transitions": ["auto", "button", "score_gate"],
    "content_only_mechanics_dont_need_diagram": true
  }
}
```

The game designer sees this menu and creates whatever game design best serves the learning objective. It's not choosing from templates — it's composing mechanics, scenes, and connections creatively.

#### GamePlan Schema (What the Designer Outputs)

```python
class GamePlan(BaseModel):
    """The complete game design. This IS the game state graph."""

    title: str
    subject: str
    difficulty: Literal["beginner", "intermediate", "advanced"]
    estimated_duration_minutes: int = Field(ge=1, le=30)
    narrative_intro: str
    completion_message: str

    # The game structure
    scenes: List[ScenePlan] = Field(min_length=1, max_length=6)

    # Global label pool
    all_zone_labels: List[str]          # Every label used across all scenes
    distractor_labels: List[str] = []   # Wrong answers
    label_hierarchy: Optional[Dict[str, List[str]]] = None  # parent → children

    # Scoring
    total_max_score: int


class ScenePlan(BaseModel):
    """One scene in the game graph."""

    scene_id: str
    scene_number: int
    title: str
    learning_goal: str
    narrative_intro: str = ""

    # Zone labels in this scene
    zone_labels: List[str]

    # Visual needs
    needs_diagram: bool
    image_spec: Optional[ImageSpec] = None     # null if needs_diagram=False

    # Mechanic graph (Level 2)
    mechanics: List[MechanicPlan] = Field(min_length=1)
    mechanic_connections: List[MechanicConnection] = []
    starting_mechanic_id: str

    # Scene transition
    transition_to_next: Optional[SceneTransition] = None  # null for last scene
    scene_max_score: int


class MechanicPlan(BaseModel):
    """One mechanic node in the scene's mechanic graph."""

    mechanic_id: str
    mechanic_type: str                  # MechanicType enum value
    zone_labels_used: List[str] = []    # Which zones this mechanic uses
    instruction_text: str               # What the player sees

    # What Phase 2 must generate
    content_brief: ContentBrief

    # Scoring expectation
    expected_item_count: int            # How many scoreable actions
    points_per_item: int = 10
    max_score: int                      # expected_item_count * points_per_item

    # Connection modifiers
    is_timed: bool = False
    time_limit_seconds: Optional[int] = None
    parent_mechanic_id: Optional[str] = None  # For hierarchical nesting
    is_terminal: bool = False           # Last mechanic in scene


class ContentBrief(BaseModel):
    """
    What the game designer wants Phase 2 to create.
    This is a CREATIVE BRIEF, not a rigid spec.
    The content generator uses this + DK to produce the actual content.
    """

    # What to generate (high-level direction)
    generation_goal: str               # "Create 5 steps showing mitosis progression"
    key_concepts: List[str] = []       # Concepts that must appear in the content
    pedagogical_focus: str = ""        # "Emphasize the role of chromosomes"

    # Mechanic-specific hints (the designer's creative vision)
    # These are HINTS, not rigid requirements — content generator can adapt
    sequence_topic: Optional[str] = None         # "stages of cell division"
    category_names: Optional[List[str]] = None   # ["Prokaryotic", "Eukaryotic"]
    comparison_subjects: Optional[List[str]] = None  # ["Plant cell", "Animal cell"]
    narrative_premise: Optional[str] = None      # "You are a doctor examining..."
    description_source: Optional[str] = None     # "zone_descriptions" | "custom"
    path_process: Optional[str] = None           # "blood flow through the heart"
    prompt_style: Optional[str] = None           # "naming" | "function" | "location"

    # Visual hints
    card_type: Optional[str] = None              # For sequencing/sorting
    layout_preference: Optional[str] = None      # "horizontal_timeline", "bucket", etc.
    needs_item_images: bool = False              # Whether items should have images


class MechanicConnection(BaseModel):
    """Edge in the mechanic graph."""
    from_mechanic_id: str              # "scene_start" for the first edge
    to_mechanic_id: str                # "scene_end" for the last edge
    trigger: str                       # "completion"|"score_threshold"|"user_choice"|"time_elapsed"|"parent_completion"
    trigger_value: Optional[Any] = None


class SceneTransition(BaseModel):
    """How one scene connects to the next."""
    transition_type: str               # "auto"|"button"|"score_gate"
    min_score_pct: Optional[float] = None  # For score_gate


class ImageSpec(BaseModel):
    """Structured image requirements."""
    description: str                   # "Cross-section of human heart showing all four chambers"
    must_include_structures: List[str] # Labels that MUST be visible in the image
    style: str = "clean_educational"   # "anatomical"|"flowchart"|"comparison"|"schematic"
    annotation_preference: str = "clean_unlabeled"  # "clean_unlabeled"|"lightly_labeled"|"fully_labeled"
```

#### Game Plan Validator — What It Checks

```python
def validate_game_plan(plan: GamePlan) -> ValidationResult:
    """
    Structural validation of the game state graph.
    Returns specific feedback for each failure.
    """
    issues = []

    for scene in plan.scenes:
        # 1. Graph connectivity
        reachable = compute_reachable(scene.starting_mechanic_id, scene.mechanic_connections)
        for mech in scene.mechanics:
            if mech.mechanic_id not in reachable:
                issues.append(f"Scene {scene.scene_id}: mechanic {mech.mechanic_id} "
                            f"is unreachable from starting_mechanic_id={scene.starting_mechanic_id}. "
                            f"Add a connection to it or remove it.")

        # 2. Terminal nodes exist
        terminals = [m for m in scene.mechanics if m.is_terminal]
        if not terminals:
            issues.append(f"Scene {scene.scene_id}: no mechanic has is_terminal=True. "
                        f"Mark the last mechanic in the sequence as terminal.")

        # 3. Zone label references
        for mech in scene.mechanics:
            for label in mech.zone_labels_used:
                if label not in scene.zone_labels:
                    issues.append(f"Scene {scene.scene_id}, mechanic {mech.mechanic_id}: "
                                f"references zone label '{label}' not in scene.zone_labels. "
                                f"Add it to zone_labels or remove the reference.")

        # 4. Diagram requirement
        visual_mechanics = [m for m in scene.mechanics
                          if m.mechanic_type in DIAGRAM_MECHANICS]
        if visual_mechanics and not scene.needs_diagram:
            issues.append(f"Scene {scene.scene_id}: has visual mechanics "
                        f"{[m.mechanic_type for m in visual_mechanics]} but needs_diagram=False. "
                        f"Set needs_diagram=True and provide image_spec.")

        if scene.needs_diagram and not scene.image_spec:
            issues.append(f"Scene {scene.scene_id}: needs_diagram=True but image_spec is null. "
                        f"Provide image_spec with description and must_include_structures.")

        # 5. Score arithmetic
        mech_score_sum = sum(m.max_score for m in scene.mechanics)
        if mech_score_sum != scene.scene_max_score:
            issues.append(f"Scene {scene.scene_id}: scene_max_score={scene.scene_max_score} "
                        f"but sum of mechanic max_scores={mech_score_sum}. Make them equal.")

        for mech in scene.mechanics:
            expected = mech.expected_item_count * mech.points_per_item
            if expected != mech.max_score:
                issues.append(f"Mechanic {mech.mechanic_id}: max_score={mech.max_score} "
                              f"but expected_item_count * points_per_item = {expected}. Fix arithmetic.")

        # 6. Content brief completeness
        for mech in scene.mechanics:
            check_content_brief(mech, issues)

        # 7. Timed wrapper validity
        for mech in scene.mechanics:
            if mech.is_timed and not mech.time_limit_seconds:
                issues.append(f"Mechanic {mech.mechanic_id}: is_timed=True but "
                            f"time_limit_seconds is null. Set a time limit.")

        # 8. Hierarchical parent validity
        for mech in scene.mechanics:
            if mech.parent_mechanic_id:
                parent = next((m for m in scene.mechanics
                             if m.mechanic_id == mech.parent_mechanic_id), None)
                if not parent:
                    issues.append(f"Mechanic {mech.mechanic_id}: parent_mechanic_id="
                                f"'{mech.parent_mechanic_id}' does not exist in this scene.")

        # 9. Compare contrast needs dual diagram
        for mech in scene.mechanics:
            if mech.mechanic_type == "compare_contrast":
                if not mech.content_brief.comparison_subjects or len(mech.content_brief.comparison_subjects) < 2:
                    issues.append(f"Mechanic {mech.mechanic_id}: compare_contrast requires "
                                f"comparison_subjects with at least 2 entries.")

    # 10. Global score
    scene_score_sum = sum(s.scene_max_score for s in plan.scenes)
    if scene_score_sum != plan.total_max_score:
        issues.append(f"total_max_score={plan.total_max_score} but sum of "
                    f"scene_max_scores={scene_score_sum}. Make them equal.")

    # 11. All zone_labels exist in all_zone_labels
    for scene in plan.scenes:
        for label in scene.zone_labels:
            if label not in plan.all_zone_labels:
                issues.append(f"Scene {scene.scene_id}: zone_label '{label}' "
                            f"not in all_zone_labels. Add it.")

    return ValidationResult(
        passed=len(issues) == 0,
        score=max(0, 1.0 - len(issues) * 0.1),
        issues=issues,
    )
```

### 3.4 Phase 2: Content Build — Scene-Aware, Per-Mechanic

The key design: **content is generated per mechanic, but each generator receives the full scene context** so two mechanics in the same scene can reference shared content.

```
game_plan + domain_knowledge
        │
        ▼
  [FOR EACH SCENE — via LangGraph Send API]
        │
        ▼
  ┌──────────────────────────────────────────────────────────┐
  │  SCENE CONTENT SUB-GRAPH                                  │
  │                                                           │
  │  Step 1: scene_context_builder (deterministic)            │
  │    Builds shared context for all mechanics in this scene: │
  │    - zone_labels and their DK descriptions                │
  │    - relevant DK data (sequence_flow, comparison, etc.)   │
  │    - what OTHER mechanics exist in this scene             │
  │    - shared terminology / naming conventions              │
  │                                                           │
  │  Step 2: [FOR EACH MECHANIC — parallel Send]              │
  │    ┌──────────────────────────────────────────┐           │
  │    │  mechanic_content_generator               │           │
  │    │  Input:                                   │           │
  │    │    - content_brief (from game_plan)        │           │
  │    │    - scene_context (shared zone info, DK)  │           │
  │    │    - other_mechanics_in_scene (awareness)  │           │
  │    │  Model: pro for complex, flash for simple  │           │
  │    │  Type: single structured call              │           │
  │    │  Output: MechanicContent                   │           │
  │    └──────────┬───────────────────────────────┘           │
  │               │                                           │
  │    ┌──────────▼───────────────────────────────┐           │
  │    │  mechanic_content_validator (deterministic)│           │
  │    │  Checks per-mechanic rules                 │           │
  │    │  On failure: retry content_generator       │           │
  │    │    with specific feedback                  │           │
  │    │    (max 2 retries)                         │           │
  │    └──────────────────────────────────────────┘           │
  │                                                           │
  │  Step 3: scene_content_merger (deterministic)             │
  │    - Merges all mechanic contents                         │
  │    - Checks cross-mechanic consistency                    │
  │      (shared labels use same descriptions,                │
  │       no ID collisions, zone references valid)            │
  │                                                           │
  │  Step 4: scene_interaction_designer                       │
  │    Model: gemini-2.5-flash                                │
  │    Type: single structured call                           │
  │    Input: all mechanic contents + pedagogical_context     │
  │    Output: per-mechanic scoring + feedback +              │
  │            misconceptions + mode_transitions              │
  │                                                           │
  │  Step 5: scene_interaction_validator (deterministic)       │
  │    - Score arithmetic (pts * count = max)                 │
  │    - Transition trigger validity                          │
  │    - On failure: retry interaction_designer with feedback  │
  │                                                           │
  └──────────────────────────────────────────────────────────┘
```

#### Scene-Awareness: How It Works

When generating content for `sequencing` in a scene that also has `drag_drop`, the content generator prompt includes:

```
You are generating content for a SEQUENCING mechanic in Scene 2: "Blood Flow Through the Heart".

SCENE CONTEXT (shared with other mechanics in this scene):
- Zone labels: ["Right Atrium", "Right Ventricle", "Pulmonary Artery", "Lungs",
                "Pulmonary Vein", "Left Atrium", "Left Ventricle", "Aorta"]
- This scene also has a DRAG_DROP mechanic that uses these same zone labels
  for labeling parts on the heart diagram.
- Use the SAME terminology as the zone labels for consistency.

YOUR TASK (sequencing):
Content brief: "Create 8 steps showing blood flow through the heart"
Key concepts: blood flow, oxygenation, circulation

Generate sequence items where each step references the zone labels above.
The items should use the exact same names so the player sees consistency
between the labeling task and the sequencing task.
```

This ensures that `sequencing` items say "Right Atrium" (not "right atrium" or "RA") because they know the `drag_drop` mechanic in the same scene uses "Right Atrium" as a zone label.

#### Content Generator — Per-Mechanic Prompts

Each mechanic type gets a tailored prompt template:

```python
MECHANIC_PROMPTS = {
    "sequencing": """Generate {brief.expected_item_count} sequence items for: {brief.generation_goal}

Use domain knowledge: {dk_context}
Use these zone labels for consistency: {scene_context.zone_labels}

Each item must have:
- id: unique string (e.g., "seq_1")
- text: short label (2-6 words)
- description: 1-2 sentence explanation
- icon: relevant emoji
- order_index: correct position (0-based)
- is_distractor: false for real items

Also generate correct_order: list of item IDs in correct sequence.

{retry_feedback if retry}""",

    "branching_scenario": """Design a decision tree for: {brief.generation_goal}

Narrative premise: {brief.narrative_premise}
Structure: {brief.narrative_structure or "branching"}
Target: {brief.expected_item_count} decision nodes

Each node must have:
- id: unique string
- question: the decision prompt
- description: context/narrative text
- node_type: "decision" | "info" | "ending"
- is_end_node: true for terminal nodes
- end_message: text shown at endings (if end node)
- ending_type: "good" | "neutral" | "bad" (if end node)
- options: list of choices, each with:
  - id, text, next_node_id (null for end paths), is_correct, consequence, points

Rules:
- start_node_id must be the first node
- Every path must reach an end node
- At least one "good" ending
- At least one "bad" or "neutral" ending

{retry_feedback if retry}""",

    "compare_contrast": """Design comparison data for: {brief.comparison_subjects[0]} vs {brief.comparison_subjects[1]}

Use domain knowledge: {dk_context}
Zone labels for {brief.comparison_subjects[0]}: {subject_a_labels}
Zone labels for {brief.comparison_subjects[1]}: {subject_b_labels}

Generate:
- subject_a: name, description, zone_labels[]
- subject_b: name, description, zone_labels[]
- expected_categories: for each zone label, classify as:
  "similar" | "different" | "unique_a" | "unique_b"
- comparison_mode: {brief.layout_preference or "side_by_side"}

Also generate second_image_spec:
- description: what the second diagram should show
- must_include_structures: structures to label in second diagram
- style: should match the first diagram's style

{retry_feedback if retry}""",

    # ... templates for all 10 mechanics
}
```

#### Content Validators — Per-Mechanic

```python
MECHANIC_VALIDATORS = {
    "sequencing": lambda content, brief: [
        *([] if len(content.items) >= 2 else
          [f"Need at least 2 items, got {len(content.items)}"]),
        *([] if set(content.correct_order) == {i.id for i in content.items if not i.is_distractor} else
          [f"correct_order IDs don't match non-distractor item IDs"]),
        *([] if all(i.order_index is not None for i in content.items if not i.is_distractor) else
          [f"All non-distractor items need order_index"]),
        *([] if len(content.items) == brief.expected_item_count else
          [f"Expected {brief.expected_item_count} items, got {len(content.items)}"]),
    ],

    "branching_scenario": lambda content, brief: [
        *([] if content.start_node_id in {n.id for n in content.nodes} else
          [f"start_node_id '{content.start_node_id}' not found in nodes"]),
        *([] if any(n.is_end_node for n in content.nodes) else
          [f"No end nodes found — at least one node must have is_end_node=True"]),
        *validate_branching_graph_connectivity(content),
        *([] if any(n.ending_type == "good" for n in content.nodes if n.is_end_node) else
          [f"No 'good' ending — add at least one optimal outcome"]),
    ],

    "sorting_categories": lambda content, brief: [
        *([] if len(content.categories) >= 2 else
          [f"Need at least 2 categories, got {len(content.categories)}"]),
        *([] if all(i.correct_category_id in {c.id for c in content.categories}
                   for i in content.items) else
          [f"Some items reference non-existent category IDs"]),
    ],

    "compare_contrast": lambda content, brief: [
        *([] if content.subject_a and content.subject_b else
          [f"Both subject_a and subject_b must be populated"]),
        *([] if len(content.subject_a.zone_labels) >= 1 else
          [f"subject_a needs at least 1 zone_label"]),
        *([] if len(content.subject_b.zone_labels) >= 1 else
          [f"subject_b needs at least 1 zone_label"]),
        *([] if content.expected_categories else
          [f"expected_categories must be populated"]),
        *([] if content.second_image_spec else
          [f"compare_contrast MUST have second_image_spec for the second diagram"]),
    ],

    "memory_match": lambda content, brief: [
        *([] if len(content.pairs) >= 3 else
          [f"Need at least 3 pairs, got {len(content.pairs)}"]),
        *([] if all(p.front and p.back for p in content.pairs) else
          [f"Every pair must have non-empty front and back"]),
        *([] if len({p.id for p in content.pairs}) == len(content.pairs) else
          [f"Duplicate pair IDs found"]),
    ],

    # ... validators for all 10 mechanics
}
```

### 3.5 Phase 3: Asset Pipeline — Per-Scene Orchestrator + Dispatched Chains

This is the key redesign. Instead of a ReAct agent deciding how to generate assets, we have:

1. **Scene Asset Orchestrator** (deterministic) — analyzes scene needs, produces asset manifest
2. **Asset Dispatchers** (parallel) — execute pre-built tool chains per asset need
3. **Asset Validator** (deterministic) — verifies zone matching, completeness

```
game_plan.scenes + scene_contents
        │
        ▼
  [FOR EACH SCENE — via Send API]
        │
        ▼
  ┌──────────────────────────────────────────────────────────┐
  │  SCENE ASSET SUB-GRAPH                                    │
  │                                                           │
  │  Step 1: scene_asset_orchestrator (DETERMINISTIC)         │
  │    Reads scene plan + mechanic contents                   │
  │    Produces: AssetManifest                                │
  │                                                           │
  │  Step 2: [FOR EACH ASSET NEED — parallel Send]            │
  │    Dispatches to the correct pre-built tool chain:        │
  │                                                           │
  │    Need: diagram_with_zones                               │
  │      → CHAIN: serper → gemini_regen → gemini_bbox → SAM3  │
  │                                                           │
  │    Need: second_diagram (compare_contrast)                │
  │      → CHAIN: serper → gemini_regen → gemini_bbox → SAM3  │
  │      (runs in PARALLEL with first diagram)                │
  │                                                           │
  │    Need: item_images (if content_brief.needs_item_images) │
  │      → CHAIN: serper → gemini_imagen (per item)           │
  │      (batch: up to 10 images in parallel)                 │
  │                                                           │
  │    Need: node_illustrations (branching, optional)         │
  │      → CHAIN: serper → gemini_imagen (per node)           │
  │                                                           │
  │    Need: color_palette (sorting categories)               │
  │      → CHAIN: deterministic HSL rotation                  │
  │                                                           │
  │  Step 3: asset_validator (DETERMINISTIC)                  │
  │    - Zone matching: detected zones vs expected labels     │
  │    - Completeness: all mandatory assets generated         │
  │    - On zone mismatch: retry zone detection with          │
  │      specific labels as guidance                          │
  │    - Reports: match_quality score per scene               │
  │                                                           │
  └──────────────────────────────────────────────────────────┘
```

#### Asset Manifest Schema

```python
@dataclass
class AssetManifest:
    """What assets this scene needs, derived from game_plan + content."""
    scene_id: str

    # Primary diagram (if needed)
    primary_diagram: Optional[DiagramAssetNeed]

    # Second diagram (for compare_contrast)
    second_diagram: Optional[DiagramAssetNeed]

    # Item images (for mechanics that need them)
    item_images: List[ItemImageNeed]

    # Node illustrations (for branching, optional)
    node_illustrations: List[NodeImageNeed]

    # Color palettes (for sorting, compare)
    color_palettes: List[ColorPaletteNeed]

@dataclass
class DiagramAssetNeed:
    """Specification for one diagram asset to generate."""
    asset_id: str
    chain: str = "diagram_with_zones"   # Which pre-built chain to use
    search_query: str                   # For serper
    fallback_queries: List[str]         # If first search fails
    style_prompt: str                   # For gemini regeneration
    expected_labels: List[str]          # For zone detection + matching
    annotation_preference: str          # clean_unlabeled, etc.

@dataclass
class ItemImageNeed:
    """Specification for one item image to generate."""
    asset_id: str
    chain: str = "simple_image"
    item_id: str                        # Which content item this is for
    description: str                    # What to search/generate
    size_hint: str = "thumbnail"        # "thumbnail"|"card"|"full"

@dataclass
class NodeImageNeed:
    """Specification for a branching node illustration."""
    asset_id: str
    chain: str = "simple_image"
    node_id: str
    description: str
    style: str = "illustration"

@dataclass
class ColorPaletteNeed:
    """Specification for a color palette."""
    asset_id: str
    chain: str = "color_palette"
    count: int
    theme: str                          # "warm"|"cool"|"categorical"|"sequential"
    category_labels: List[str]          # For labeling colors
```

#### Scene Asset Orchestrator Logic (Deterministic)

```python
def build_asset_manifest(scene: ScenePlan, content: SceneContent) -> AssetManifest:
    """Deterministically derive all asset needs from scene plan + content."""

    manifest = AssetManifest(scene_id=scene.scene_id)

    # 1. Primary diagram
    if scene.needs_diagram and scene.image_spec:
        manifest.primary_diagram = DiagramAssetNeed(
            asset_id=f"{scene.scene_id}_diagram",
            search_query=f"{scene.image_spec.description} educational diagram",
            fallback_queries=[
                f"{scene.image_spec.description} labeled",
                f"{' '.join(scene.image_spec.must_include_structures)} diagram",
            ],
            style_prompt=build_style_prompt(scene.image_spec),
            expected_labels=scene.image_spec.must_include_structures,
            annotation_preference=scene.image_spec.annotation_preference,
        )

    # 2. Second diagram (compare_contrast)
    for mech_id, mech_content in content.mechanic_contents.items():
        if mech_content.mechanic_type == "compare_contrast" and mech_content.compare_contrast:
            cc = mech_content.compare_contrast
            if cc.second_image_spec:
                manifest.second_diagram = DiagramAssetNeed(
                    asset_id=f"{scene.scene_id}_diagram_b",
                    search_query=f"{cc.second_image_spec.description} educational diagram",
                    fallback_queries=[...],
                    style_prompt=build_style_prompt(cc.second_image_spec),
                    expected_labels=cc.second_image_spec.must_include_structures,
                    annotation_preference=cc.second_image_spec.annotation_preference,
                )

    # 3. Item images
    for mech_id, mech_content in content.mechanic_contents.items():
        if mech_content.mechanic_type == "sequencing" and mech_content.sequencing:
            for item in mech_content.sequencing.items:
                if item.image:  # Content generator indicated image wanted
                    manifest.item_images.append(ItemImageNeed(
                        asset_id=f"{mech_id}_{item.id}_img",
                        item_id=item.id,
                        description=f"{item.text}: {item.description}",
                    ))

        if mech_content.mechanic_type == "memory_match" and mech_content.memory_match:
            for pair in mech_content.memory_match.pairs:
                if pair.front_type == "image":
                    manifest.item_images.append(ItemImageNeed(
                        asset_id=f"{mech_id}_{pair.id}_front",
                        item_id=f"{pair.id}_front",
                        description=pair.front,  # front field = description when type=image
                    ))
                if pair.back_type == "image":
                    manifest.item_images.append(ItemImageNeed(
                        asset_id=f"{mech_id}_{pair.id}_back",
                        item_id=f"{pair.id}_back",
                        description=pair.back,
                    ))

        if mech_content.mechanic_type == "sorting_categories" and mech_content.sorting:
            for item in mech_content.sorting.items:
                if item.image:
                    manifest.item_images.append(ItemImageNeed(
                        asset_id=f"{mech_id}_{item.id}_img",
                        item_id=item.id,
                        description=f"{item.text}: {item.description or ''}",
                    ))

    # 4. Node illustrations (branching, optional)
    for mech_id, mech_content in content.mechanic_contents.items():
        if mech_content.mechanic_type == "branching_scenario" and mech_content.branching:
            for node in mech_content.branching.nodes:
                # Only generate images for decision nodes with descriptions
                if node.node_type == "decision" and node.description:
                    manifest.node_illustrations.append(NodeImageNeed(
                        asset_id=f"{mech_id}_{node.id}_img",
                        node_id=node.id,
                        description=node.description,
                    ))

    # 5. Color palettes
    for mech_id, mech_content in content.mechanic_contents.items():
        if mech_content.mechanic_type == "sorting_categories" and mech_content.sorting:
            manifest.color_palettes.append(ColorPaletteNeed(
                asset_id=f"{mech_id}_palette",
                count=len(mech_content.sorting.categories),
                theme="categorical",
                category_labels=[c.label for c in mech_content.sorting.categories],
            ))

        if mech_content.mechanic_type == "compare_contrast" and mech_content.compare_contrast:
            manifest.color_palettes.append(ColorPaletteNeed(
                asset_id=f"{mech_id}_palette",
                count=4,  # similar, different, unique_a, unique_b
                theme="categorical",
                category_labels=["Similar", "Different",
                                f"Only {mech_content.compare_contrast.subject_a.name}",
                                f"Only {mech_content.compare_contrast.subject_b.name}"],
            ))

    return manifest
```

### 3.6 Phase 4: Assembly (Deterministic)

Same as brainstorm. Pure translation from enriched game state graph to frontend blueprint JSON.

```
game_plan + scene_contents + scene_assets
        │
        ▼
  blueprint_assembler (deterministic)
        │
        ▼
  blueprint_validator (deterministic)
        │ on failure: return blueprint with _warnings array
        │ (no retry — assembler is deterministic)
        ▼
  final blueprint
```

Key assembly decisions:
- **Single scene**: Mechanic configs at blueprint root
- **Multi scene**: Mechanic configs per scene in game_sequence.scenes[]
- **Zone IDs**: `zone_{scene_number}_{index}`
- **Scoring**: Keyed by `mechanic_id` (not mechanic_type) — no collision
- **Mode transitions**: Directly from game_plan's mechanic_connections
- **Asset URLs**: From scene_assets, matched by asset_id

---

## 4. Mechanic Connection Patterns

### 4.1 Sequential (Current — Simplest)

```
Game Designer creates:
  Scene 1: [drag_drop → click_to_identify]
  mechanic_connections: [
    {from: "scene_start", to: "mech_1_1", trigger: "auto"},
    {from: "mech_1_1", to: "mech_1_2", trigger: "completion"},
    {from: "mech_1_2", to: "scene_end", trigger: "completion"},
  ]

Frontend receives:
  modeTransitions: [
    {from_mode: "drag_drop", to_mode: "click_to_identify", trigger: "completion"}
  ]
  mechanics[0].type = "drag_drop"  (starting mode)
```

### 4.2 Hierarchical

```
Game Designer creates:
  Scene 1: [drag_drop (parent) → click_to_identify (child of drag_drop)]
  mechanics: [
    {mechanic_id: "mech_parent", type: "drag_drop", zone_labels: ["Heart", "Lungs", "Brain"]},
    {mechanic_id: "mech_child_1", type: "click_to_identify",
     parent_mechanic_id: "mech_parent",
     zone_labels: ["Left Ventricle", "Right Ventricle", "Septum"]},  # Sub-zones of Heart
  ]
  mechanic_connections: [
    {from: "scene_start", to: "mech_parent", trigger: "auto"},
    {from: "mech_parent", to: "mech_child_1", trigger: "parent_completion"},
    {from: "mech_child_1", to: "scene_end", trigger: "completion"},
  ]

Frontend receives:
  zoneGroups: [{parentZoneId: "zone_heart", childZoneIds: ["zone_lv", "zone_rv", "zone_sep"],
                revealTrigger: "complete_parent"}]
  modeTransitions: [
    {from_mode: "drag_drop", to_mode: "click_to_identify",
     trigger: "specific_zones", trigger_value: ["zone_heart"]}
  ]
```

### 4.3 Timed Wrapper

```
Game Designer creates:
  Scene 1: [drag_drop (timed, 60s)]
  mechanics: [
    {mechanic_id: "mech_1", type: "drag_drop", is_timed: true, time_limit_seconds: 60},
  ]

Frontend receives:
  timedChallengeWrappedMode: "drag_drop"
  timeLimitSeconds: 60
  mechanics[0].type = "drag_drop"
```

### 4.4 Score-Gated

```
Game Designer creates:
  Scene 1: [drag_drop → (if score >= 80%) sequencing]
  mechanic_connections: [
    {from: "mech_1", to: "mech_2", trigger: "score_threshold", trigger_value: 0.8},
  ]

Frontend receives:
  modeTransitions: [
    {from_mode: "drag_drop", to_mode: "sequencing",
     trigger: "score_threshold", trigger_value: 0.8}
  ]
```

### 4.5 Future: Nested Mechanics

```
Game Designer creates (future):
  Scene 1: [drag_drop → on_zone_complete("Heart") → memory_match(heart parts) → continue drag_drop]

This would require frontend changes to support "sub-mechanic" interruptions.
For now, we model this as a hierarchical connection.
```

---

## 5. Example: Complete Data Flow for a 2-Scene Game

### Input
```
Question: "Explain the differences between plant and animal cells, including their organelles and functions"
```

### Phase 0 Output

```python
pedagogical_context = {
    "blooms_level": "analyze",
    "subject": "Biology",
    "difficulty": "intermediate",
    "learning_objectives": [
        "Identify organelles unique to plant/animal cells",
        "Compare structural differences",
        "Explain organelle functions"
    ],
    "common_misconceptions": [
        {"misconception": "Plant cells don't have mitochondria", "correction": "Both have mitochondria"},
        {"misconception": "Cell wall and cell membrane are the same", "correction": "Plants have both; animals only membrane"},
    ],
}

content_structure = {
    "primary_type": "comparative",
    "has_labels": True,
    "has_sequence": False,
    "has_comparison": True,
    "has_hierarchy": False,
    "has_categories": True,    # Organelles can be sorted
    "visual_needs": "dual_diagram",
}

domain_knowledge = {
    "canonical_labels": ["Cell Wall", "Cell Membrane", "Nucleus", "Mitochondria",
                        "Chloroplast", "Vacuole", "Ribosome", "ER", "Golgi", "Lysosome"],
    "label_descriptions": {
        "Cell Wall": "Rigid outer layer providing structural support, found only in plant cells",
        "Chloroplast": "Organelle for photosynthesis, contains chlorophyll, unique to plant cells",
        # ...
    },
    "comparison_data": {
        "groups": [
            {"name": "Plant Cell", "members": ["Cell Wall", "Chloroplast", "Large Vacuole"], "key_traits": ["rigid", "photosynthetic"]},
            {"name": "Animal Cell", "members": ["Lysosome", "Centriole"], "key_traits": ["flexible", "heterotrophic"]},
            {"name": "Both", "members": ["Nucleus", "Mitochondria", "Ribosome", "ER", "Golgi", "Cell Membrane"]}
        ],
    },
}
```

### Phase 1 Output (Game Designer — Creative!)

```python
game_plan = GamePlan(
    title="Cell Explorer: Plant vs Animal",
    subject="Biology",
    difficulty="intermediate",
    estimated_duration_minutes=8,
    narrative_intro="Explore the fascinating world of cells! First learn the parts, then discover what makes plant and animal cells unique.",
    completion_message="Excellent work! You now understand the key differences between plant and animal cells.",
    all_zone_labels=["Cell Wall", "Cell Membrane", "Nucleus", "Mitochondria",
                    "Chloroplast", "Vacuole", "Ribosome", "ER", "Golgi", "Lysosome", "Centriole"],
    distractor_labels=["Flagellum", "Pilus"],
    total_max_score=120,
    scenes=[
        ScenePlan(
            scene_id="scene_1",
            scene_number=1,
            title="Know Your Cell Parts",
            learning_goal="Identify and label organelles in a typical cell",
            narrative_intro="Let's start by learning the organelles found in cells.",
            zone_labels=["Cell Wall", "Cell Membrane", "Nucleus", "Mitochondria",
                        "Chloroplast", "Vacuole", "Ribosome", "ER", "Golgi"],
            needs_diagram=True,
            image_spec=ImageSpec(
                description="Cross-section of a generic eukaryotic cell showing major organelles",
                must_include_structures=["Nucleus", "Mitochondria", "Cell Membrane", "ER", "Golgi"],
                style="clean_educational",
                annotation_preference="clean_unlabeled",
            ),
            mechanics=[
                MechanicPlan(
                    mechanic_id="s1_drag",
                    mechanic_type="drag_drop",
                    zone_labels_used=["Cell Wall", "Cell Membrane", "Nucleus", "Mitochondria",
                                     "Chloroplast", "Vacuole", "Ribosome", "ER", "Golgi"],
                    instruction_text="Drag each label to the correct organelle in the cell diagram.",
                    content_brief=ContentBrief(
                        generation_goal="Create labels for 9 organelles with descriptions",
                        key_concepts=["organelle identification", "spatial relationships"],
                    ),
                    expected_item_count=9,
                    points_per_item=5,
                    max_score=45,
                ),
                MechanicPlan(
                    mechanic_id="s1_describe",
                    mechanic_type="description_matching",
                    zone_labels_used=["Cell Wall", "Cell Membrane", "Nucleus", "Mitochondria",
                                     "Chloroplast", "Vacuole", "Ribosome", "ER", "Golgi"],
                    instruction_text="Read each description and click the matching organelle.",
                    content_brief=ContentBrief(
                        generation_goal="Write functional descriptions for each organelle",
                        key_concepts=["organelle functions"],
                        description_source="zone_descriptions",
                        mode="click_zone",
                    ),
                    expected_item_count=9,
                    points_per_item=5,
                    max_score=45,
                    is_terminal=True,
                ),
            ],
            mechanic_connections=[
                MechanicConnection(from_mechanic_id="scene_start", to_mechanic_id="s1_drag", trigger="auto"),
                MechanicConnection(from_mechanic_id="s1_drag", to_mechanic_id="s1_describe", trigger="completion"),
                MechanicConnection(from_mechanic_id="s1_describe", to_mechanic_id="scene_end", trigger="completion"),
            ],
            starting_mechanic_id="s1_drag",
            transition_to_next=SceneTransition(transition_type="auto"),
            scene_max_score=90,
        ),
        ScenePlan(
            scene_id="scene_2",
            scene_number=2,
            title="Plant vs Animal: Spot the Differences",
            learning_goal="Compare and categorize organelles by cell type",
            narrative_intro="Now that you know the parts, let's see what makes plant and animal cells different!",
            zone_labels=["Cell Wall", "Cell Membrane", "Nucleus", "Mitochondria",
                        "Chloroplast", "Vacuole", "Lysosome", "Centriole"],
            needs_diagram=True,
            image_spec=ImageSpec(
                description="Side-by-side comparison diagram of plant cell and animal cell",
                must_include_structures=["Cell Wall", "Chloroplast", "Nucleus", "Lysosome"],
                style="comparison",
                annotation_preference="lightly_labeled",
            ),
            mechanics=[
                MechanicPlan(
                    mechanic_id="s2_sort",
                    mechanic_type="sorting_categories",
                    zone_labels_used=[],  # Content-only, doesn't use diagram zones
                    instruction_text="Sort each organelle into the correct category: Plant Only, Animal Only, or Both.",
                    content_brief=ContentBrief(
                        generation_goal="Sort 10 organelles into Plant Only / Animal Only / Both categories",
                        key_concepts=["cell type differences", "organelle distribution"],
                        category_names=["Plant Cell Only", "Animal Cell Only", "Found in Both"],
                        layout_preference="bucket",
                    ),
                    expected_item_count=10,
                    points_per_item=3,
                    max_score=30,
                    is_terminal=True,
                ),
            ],
            mechanic_connections=[
                MechanicConnection(from_mechanic_id="scene_start", to_mechanic_id="s2_sort", trigger="auto"),
                MechanicConnection(from_mechanic_id="s2_sort", to_mechanic_id="scene_end", trigger="completion"),
            ],
            starting_mechanic_id="s2_sort",
            transition_to_next=None,  # Last scene
            scene_max_score=30,
        ),
    ],
)
```

### Phase 2 Output (Content Build)

Scene 1 runs two parallel content generators (drag_drop + description_matching), both receiving the scene context with shared zone labels.

Scene 2 runs one content generator (sorting), receiving DK's comparison_data.

### Phase 3 Output (Asset Pipeline)

Scene 1 asset manifest:
```python
AssetManifest(
    scene_id="scene_1",
    primary_diagram=DiagramAssetNeed(
        chain="diagram_with_zones",
        search_query="eukaryotic cell organelles cross-section educational diagram",
        expected_labels=["Nucleus", "Mitochondria", "Cell Membrane", "ER", "Golgi"],
    ),
    second_diagram=None,
    item_images=[],
    color_palettes=[],
)
```

Scene 2 asset manifest:
```python
AssetManifest(
    scene_id="scene_2",
    primary_diagram=DiagramAssetNeed(
        chain="diagram_with_zones",
        search_query="plant cell animal cell comparison side by side educational",
        expected_labels=["Cell Wall", "Chloroplast", "Nucleus", "Lysosome"],
    ),
    second_diagram=None,  # Using one comparison image, not dual
    item_images=[],
    color_palettes=[
        ColorPaletteNeed(
            count=3,
            theme="categorical",
            category_labels=["Plant Cell Only", "Animal Cell Only", "Found in Both"],
        ),
    ],
)
```

### Phase 4 Output (Blueprint)

Deterministic assembly produces the complete `InteractiveDiagramBlueprint` JSON matching the frontend contract.

---

## 6. Token & Latency Budget

### Token Budget

| Phase | Stage | Calls | Tokens/Call | Total |
|-------|-------|-------|------------|-------|
| 0 | input_analyzer | 1 | ~700 | 700 |
| 0 | dk_retriever | ~4 turns | ~1200 | 5000 |
| 1 | game_designer | 1 | ~4000 | 4000 |
| 1 | game_plan_validator | 0 (deterministic) | 0 | 0 |
| 2 | scene_context_builder (×2) | 0 (deterministic) | 0 | 0 |
| 2 | mechanic_content_gen (×3) | 3 | ~1400 | 4200 |
| 2 | mechanic_content_validator (×3) | 0 (deterministic) | 0 | 0 |
| 2 | scene_interaction_designer (×2) | 2 | ~1500 | 3000 |
| 3 | scene_asset_orchestrator (×2) | 0 (deterministic) | 0 | 0 |
| 3 | diagram_with_zones chain (×2) | 2 | ~1500 | 3000 |
| 3 | color_palette (×1) | 0 (deterministic) | 0 | 0 |
| 4 | blueprint_assembler | 0 (deterministic) | 0 | 0 |
| 4 | blueprint_validator | 0 (deterministic) | 0 | 0 |
| | **TOTAL** | | | **~19,900** |

vs Current V3: **~67,200 tokens** → **70% reduction**

### Latency Budget (Critical Path)

```
Phase 0: max(input_analyzer ~2s, dk_retriever ~8s)     = ~8s
Phase 1: game_designer ~5s + validator ~0.1s            = ~5s
         (+ retry if needed: +5s)
Phase 2: max(3 content generators ~4s each)             = ~4s
         + scene_interaction_designer ~3s                = ~3s
         (+ retry if needed: +4s)
Phase 3: max(2 diagram pipelines ~15s each)             = ~15s
         + asset_validator ~0.1s
Phase 4: assembler + validator ~0.2s                    = ~0.2s
                                                 TOTAL = ~35s
         (with retries: ~45-50s)
```

vs Current V3: **~120-180s** → **70-75% reduction**

Key gains:
- Phase 0: parallel (saves ~5s)
- Phase 2: parallel content gen (saves ~10-15s)
- Phase 3: parallel asset pipelines (saves ~15s)
- No ReAct overhead (saves ~30-40s of back-and-forth LLM turns)

---

## 7. Retry Strategy (Every Retry Has Feedback)

| Stage | Validator | Max Retries | Feedback Format |
|-------|-----------|-------------|-----------------|
| game_designer | game_plan_validator | 2 | List of specific issues: "Scene 1 mechanic mech_1_2 is unreachable. Add a connection from mech_1_1." |
| mechanic_content_gen | mechanic_content_validator | 2 per mechanic | Per-mechanic issues: "correct_order IDs don't match item IDs. Items: [a,b,c], correct_order: [a,d,c]" |
| scene_interaction_designer | scene_interaction_validator | 1 | Arithmetic issues: "mechanic s1_drag: max_score=50 but points_per_item(5) * count(9) = 45" |
| diagram_with_zones chain | asset_validator (zone matching) | 1 | Unmatched labels: "Labels ['Golgi', 'ER'] not found in detected zones. Retry detection with these as specific prompts." |

Every retry includes:
1. The original input
2. The previous (failed) output
3. The specific validation failures
4. What to fix

---

## 8. Files to Create/Modify

### New Files

| File | Purpose |
|------|---------|
| `backend/app/agents/v4/schemas.py` | GamePlan, ScenePlan, MechanicPlan, ContentBrief, MechanicContent, AssetManifest |
| `backend/app/agents/v4/phase0.py` | input_analyzer + dk_retriever sub-graph |
| `backend/app/agents/v4/phase1.py` | game_designer + game_plan_validator sub-graph |
| `backend/app/agents/v4/phase2.py` | Content build sub-graph with scene-level map-reduce |
| `backend/app/agents/v4/phase3.py` | Asset pipeline sub-graph with manifest + dispatch |
| `backend/app/agents/v4/phase4.py` | Blueprint assembler + validator |
| `backend/app/agents/v4/graph.py` | Main orchestrator graph wiring all phases |
| `backend/app/agents/v4/validators.py` | All validators (game_plan, content, interaction, asset, blueprint) |
| `backend/app/agents/v4/prompts.py` | All prompt templates (game_designer, content generators, interaction designer) |
| `backend/app/agents/v4/asset_chains.py` | Pre-built tool chain definitions + dispatch logic |
| `backend/app/agents/v4/capability_spec.py` | The capability menu injected into game_designer prompt |

### Modified Files

| File | Changes |
|------|---------|
| `backend/app/agents/graph.py` | Add `create_v4_graph()` factory |
| `backend/app/agents/state.py` | Add V4 per-phase state types |
| `backend/app/routes/generate.py` | Support `pipeline_preset: "v4"` |
| `backend/app/config/agent_models.py` | Model assignments for V4 agents |
| `frontend/src/components/pipeline/PipelineView.tsx` | V4 pipeline visualization |

### Unchanged

| Component | Why |
|-----------|-----|
| Frontend game engine | Blueprint format is the same |
| Frontend mechanic components | They consume the same config keys |
| Database schema | Blueprint stored as JSON blob — format compatible |
| Asset serving routes | Same `/api/assets/` endpoints |

---

## 9. Open Design Decisions

| Decision | Options | Recommendation |
|----------|---------|---------------|
| Game designer output mode | Gemini structured output vs submit-tool | Structured output (cleaner, faster) with retry on parse failure |
| Content gen model per mechanic | All pro vs smart routing | Pro for branching+compare+sequencing, flash for the rest |
| DK retriever: keep ReAct? | Yes (needs web search) vs pre-search then single call | Keep ReAct — web search is inherently iterative |
| Phase 2+3 parallelism | LangGraph Send vs asyncio.gather | LangGraph Send (native support, better observability) |
| V4 as new preset vs replace V3? | New "v4" preset alongside | New preset — V3 kept for comparison/fallback |
| Asset chain failure handling | Retry chain vs skip asset | Retry once, then generate placeholder + warning |
