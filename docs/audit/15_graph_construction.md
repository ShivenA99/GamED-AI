# Game State Graph Construction — Design Document

**Date**: 2026-02-14
**Core question**: How do we convert the game designer's creative vision into a valid game state graph?

---

## 1. The Problem

LLMs produce buggy graphs. Asking an LLM to generate:
- Consistent mechanic IDs (`s1_m1`, `s1_m2`) and reference them in connections
- Graph edges with correct `from_mechanic_id` → `to_mechanic_id`
- Score arithmetic (`points_per_item × item_count = max_score`, sum across scenes)
- Terminal node marking, starting node references
- Hierarchical parent-child ID linkage

...is unreliable. Even with retries, the LLM produces different structural bugs each time.

**Solution**: The game designer should output a SIMPLE creative plan. A DETERMINISTIC graph builder converts it to the formal graph. The graph is valid by construction.

---

## 2. Separation of Concerns

| Responsibility | Owner | Why |
|---------------|-------|-----|
| What game to make (scenes, mechanics, pedagogy) | **Game Designer (LLM)** | Creative decision-making |
| How to structure the graph (IDs, edges, scores) | **Graph Builder (code)** | Structural correctness |
| Is the graph valid? | **Graph Validator (code)** | Defense in depth |

The game designer thinks about LEARNING. The graph builder thinks about STRUCTURE.

---

## 3. Game Design Document (What the LLM Produces)

The game designer outputs a simple, ordered, hierarchical description of the game. No graph IDs. No edge definitions. No score arithmetic.

```python
class GameDesignDocument(BaseModel):
    """What the game designer produces. Simple, creative, no graph concerns."""

    title: str
    subject: str
    difficulty: Literal["beginner", "intermediate", "advanced"]
    estimated_duration_minutes: int = Field(ge=1, le=30)
    narrative_intro: str
    completion_message: str

    # Global labels
    all_zone_labels: List[str]
    distractor_labels: List[str] = []
    label_hierarchy: Optional[Dict[str, List[str]]] = None

    # Scenes in order (scene_1 is first, etc.)
    scenes: List[SceneDesign] = Field(min_length=1, max_length=6)


class SceneDesign(BaseModel):
    """One scene. Mechanics are listed in play order."""

    title: str
    learning_goal: str
    narrative_intro: str = ""
    zone_labels: List[str]

    # Visual
    needs_diagram: bool
    image_spec: Optional[ImageSpec] = None

    # Mechanics in PLAY ORDER (first = starting, last = terminal)
    # The graph builder creates connections based on order + triggers
    mechanics: List[MechanicDesign] = Field(min_length=1)

    # How to get to the next scene
    transition_to_next: str = "auto"  # "auto"|"button"|"score_gate"
    transition_min_score_pct: Optional[float] = None


class MechanicDesign(BaseModel):
    """One mechanic. The designer specifies WHAT, not graph structure."""

    mechanic_type: str                  # MechanicType enum value
    instruction_text: str               # What the player sees
    zone_labels_used: List[str] = []    # Which zones this mechanic uses (empty for content-only)

    # Content brief (creative direction for Phase 2)
    content_brief: ContentBrief

    # How many scoreable actions the designer expects
    expected_item_count: int
    points_per_item: int = 10

    # ─── Connection to NEXT mechanic (simple!) ───
    # How does the player move from this mechanic to the next one in the list?
    # Default: "completion" (finish this, move to next)
    advance_trigger: str = "completion"
    # "completion" — complete all items
    # "score_threshold" — reach a score percentage
    # "user_choice" — player clicks "Next"
    # "time_elapsed" — timer runs out
    advance_trigger_value: Optional[float] = None  # e.g., 0.8 for 80% score gate

    # ─── Modifiers (optional) ───
    is_timed: bool = False
    time_limit_seconds: Optional[int] = None

    # Nested/hierarchical children (optional)
    # These run INSIDE this mechanic (e.g., after completing parent zone → sub-task)
    children: Optional[List["MechanicDesign"]] = None
```

### What the Designer Does NOT Specify

- `mechanic_id` — The graph builder assigns these
- `mechanic_connections` / edges — Derived from list order + `advance_trigger`
- `starting_mechanic_id` — Always the first mechanic in the list
- `is_terminal` — Always the last mechanic (or last child of last mechanic)
- `max_score` — Computed as `expected_item_count × points_per_item`
- `scene_max_score` — Sum of mechanic max_scores
- `total_max_score` — Sum of scene_max_scores
- `scene_id`, `scene_number` — Derived from list position

### What the Designer DOES Specify

- Scene order (list position)
- Mechanic order within scene (list position)
- How to advance between mechanics (`advance_trigger`)
- Hierarchical nesting (via `children`)
- Timing modifiers (`is_timed`, `time_limit_seconds`)
- Creative content briefs
- Label assignments per mechanic

---

## 4. Graph Builder (Deterministic Code)

The graph builder takes a `GameDesignDocument` and produces a `GamePlan` (the formal game state graph). It's ~200 lines of deterministic Python. No LLM.

```python
def build_game_graph(design: GameDesignDocument) -> GamePlan:
    """
    Deterministically convert a creative design document into a
    formal, valid game state graph.

    The graph is valid BY CONSTRUCTION — not by validation-and-retry.
    """

    scenes: List[ScenePlan] = []

    for scene_idx, scene_design in enumerate(design.scenes):
        scene_number = scene_idx + 1
        scene_id = f"scene_{scene_number}"

        # Build mechanic nodes (flatten hierarchy)
        mechanics: List[MechanicPlan] = []
        connections: List[MechanicConnection] = []

        _build_mechanic_graph(
            scene_id=scene_id,
            scene_number=scene_number,
            mechanic_designs=scene_design.mechanics,
            mechanics_out=mechanics,
            connections_out=connections,
            parent_id=None,
        )

        # Starting mechanic is always the first
        starting_id = mechanics[0].mechanic_id

        # Terminal mechanic is always the last (at the top level)
        mechanics[-1] = mechanics[-1].copy(update={"is_terminal": True})

        # Connect last mechanic to scene_end
        connections.append(MechanicConnection(
            from_mechanic_id=mechanics[-1].mechanic_id,
            to_mechanic_id="scene_end",
            trigger="completion",
        ))

        # Scene max score
        scene_max_score = sum(m.max_score for m in mechanics)

        # Scene transition
        transition = None
        if scene_idx < len(design.scenes) - 1:
            transition = SceneTransition(
                transition_type=scene_design.transition_to_next,
                min_score_pct=scene_design.transition_min_score_pct,
            )

        scenes.append(ScenePlan(
            scene_id=scene_id,
            scene_number=scene_number,
            title=scene_design.title,
            learning_goal=scene_design.learning_goal,
            narrative_intro=scene_design.narrative_intro,
            zone_labels=scene_design.zone_labels,
            needs_diagram=scene_design.needs_diagram,
            image_spec=scene_design.image_spec,
            mechanics=mechanics,
            mechanic_connections=connections,
            starting_mechanic_id=starting_id,
            transition_to_next=transition,
            scene_max_score=scene_max_score,
        ))

    # Global score
    total_max_score = sum(s.scene_max_score for s in scenes)

    return GamePlan(
        title=design.title,
        subject=design.subject,
        difficulty=design.difficulty,
        estimated_duration_minutes=design.estimated_duration_minutes,
        narrative_intro=design.narrative_intro,
        completion_message=design.completion_message,
        all_zone_labels=design.all_zone_labels,
        distractor_labels=design.distractor_labels,
        label_hierarchy=design.label_hierarchy,
        total_max_score=total_max_score,
        scenes=scenes,
    )


def _build_mechanic_graph(
    scene_id: str,
    scene_number: int,
    mechanic_designs: List[MechanicDesign],
    mechanics_out: List[MechanicPlan],
    connections_out: List[MechanicConnection],
    parent_id: Optional[str],
    counter: List[int] = None,  # mutable counter for unique IDs
):
    """
    Recursively build mechanic nodes and connections from a list of designs.
    Handles sequential ordering, hierarchical nesting, and timed wrappers.
    """
    if counter is None:
        counter = [0]

    prev_mechanic_id = "scene_start" if parent_id is None else parent_id

    for i, design in enumerate(mechanic_designs):
        counter[0] += 1
        mechanic_id = f"s{scene_number}_m{counter[0]}"

        # Compute max_score
        max_score = design.expected_item_count * design.points_per_item

        # Create the mechanic node
        mechanic = MechanicPlan(
            mechanic_id=mechanic_id,
            mechanic_type=design.mechanic_type,
            zone_labels_used=design.zone_labels_used,
            instruction_text=design.instruction_text,
            content_brief=design.content_brief,
            expected_item_count=design.expected_item_count,
            points_per_item=design.points_per_item,
            max_score=max_score,
            is_timed=design.is_timed,
            time_limit_seconds=design.time_limit_seconds,
            parent_mechanic_id=parent_id,
            is_terminal=False,  # Set later for the very last mechanic
        )
        mechanics_out.append(mechanic)

        # Create connection from previous mechanic (or scene_start)
        if i == 0 and parent_id is None:
            # First top-level mechanic: connect from scene_start
            connections_out.append(MechanicConnection(
                from_mechanic_id="scene_start",
                to_mechanic_id=mechanic_id,
                trigger="auto",
            ))
        elif i == 0 and parent_id is not None:
            # First child mechanic: connect from parent via parent_completion
            connections_out.append(MechanicConnection(
                from_mechanic_id=parent_id,
                to_mechanic_id=mechanic_id,
                trigger="parent_completion",
            ))
        else:
            # Subsequent mechanics: connect from previous via its advance_trigger
            prev_design = mechanic_designs[i - 1]
            connections_out.append(MechanicConnection(
                from_mechanic_id=prev_mechanic_id,
                to_mechanic_id=mechanic_id,
                trigger=prev_design.advance_trigger,
                trigger_value=prev_design.advance_trigger_value,
            ))

        # Handle children (hierarchical nesting)
        if design.children:
            _build_mechanic_graph(
                scene_id=scene_id,
                scene_number=scene_number,
                mechanic_designs=design.children,
                mechanics_out=mechanics_out,
                connections_out=connections_out,
                parent_id=mechanic_id,
                counter=counter,
            )

        prev_mechanic_id = mechanic_id
```

### What the Graph Builder Guarantees (By Construction)

| Property | How It's Guaranteed |
|----------|-------------------|
| **Every node has a unique ID** | Counter-based: `s{scene}_m{counter}` |
| **Every node is reachable** | Sequential connections from list order |
| **Exactly one start node per scene** | Always `mechanics[0]` |
| **Exactly one terminal node per scene** | Always the last top-level mechanic |
| **All paths lead to scene_end** | Last mechanic → scene_end connection always added |
| **Score arithmetic is correct** | `max_score = expected_item_count × points_per_item` (computed, not LLM-specified) |
| **Scene max score is correct** | `sum(m.max_score for m in mechanics)` (computed) |
| **Total max score is correct** | `sum(s.scene_max_score for s in scenes)` (computed) |
| **Parent-child references are valid** | Set during recursive traversal |
| **Scene IDs are unique** | Counter-based: `scene_{number}` |
| **Scene transitions exist for all non-final scenes** | Loop skips the last scene |

**The graph doesn't need to be "validated into correctness" — it IS correct by the way it's built.**

---

## 5. Graph Validator (Defense in Depth)

The validator is a safety net. If the graph builder has a bug, the validator catches it. It also catches semantic issues that the builder can't check (e.g., zone labels that don't exist in the design).

```python
def validate_game_graph(plan: GamePlan, design: GameDesignDocument) -> ValidationResult:
    """
    Defense-in-depth validation. Should ALWAYS pass if the graph builder
    is correct. If it fails, the builder has a bug — don't retry the LLM,
    fix the builder.
    """
    issues = []

    # Structural checks (should always pass if builder is correct)
    for scene in plan.scenes:
        reachable = compute_reachable(scene.starting_mechanic_id, scene.mechanic_connections)
        for mech in scene.mechanics:
            if mech.mechanic_id not in reachable:
                issues.append(f"BUG IN BUILDER: {mech.mechanic_id} unreachable")

        terminals = [m for m in scene.mechanics if m.is_terminal]
        if len(terminals) != 1:
            issues.append(f"BUG IN BUILDER: scene {scene.scene_id} has {len(terminals)} terminals")

    # Semantic checks (catches design issues)
    for scene in plan.scenes:
        for mech in scene.mechanics:
            for label in mech.zone_labels_used:
                if label not in scene.zone_labels:
                    issues.append(f"Mechanic {mech.mechanic_id} references zone label "
                                f"'{label}' not in scene zone_labels. "
                                f"This is a game designer error — retry game_designer.")

            if mech.mechanic_type in DIAGRAM_MECHANICS and not scene.needs_diagram:
                issues.append(f"Mechanic {mech.mechanic_id} is {mech.mechanic_type} "
                            f"(needs diagram) but scene has needs_diagram=False. "
                            f"This is a game designer error — retry game_designer.")

    # Content brief checks
    for scene in plan.scenes:
        for mech in scene.mechanics:
            brief_issues = check_content_brief(mech)
            issues.extend(brief_issues)

    return ValidationResult(
        passed=len(issues) == 0,
        score=max(0, 1.0 - len(issues) * 0.1),
        issues=issues,
        # Distinguish builder bugs from design issues
        is_builder_bug=any("BUG IN BUILDER" in i for i in issues),
        is_design_issue=any("game designer error" in i for i in issues),
    )
```

### Retry Logic

```
If validator.is_builder_bug:
    → This means our code has a bug. Log it, don't retry LLM.
    → Fall back to simple sequential graph.

If validator.is_design_issue:
    → Retry game_designer with specific feedback:
      "Your design has these issues: [list].
       Please fix them in your next attempt."
    → Max 2 retries.

If validator.passed:
    → Proceed to Phase 2.
```

**Key insight**: We almost never retry the LLM for graph structure issues — the builder handles structure. We only retry for SEMANTIC issues (wrong label references, missing content briefs).

---

## 6. Examples

### Example 1: Simple Sequential (2 mechanics, 1 scene)

**Game Designer outputs:**
```json
{
  "title": "Heart Anatomy",
  "scenes": [
    {
      "title": "Label the Heart",
      "zone_labels": ["Left Ventricle", "Right Ventricle", "Left Atrium", "Right Atrium"],
      "needs_diagram": true,
      "image_spec": {"description": "Cross-section of human heart", "must_include_structures": ["Left Ventricle", "Right Ventricle", "Left Atrium", "Right Atrium"]},
      "mechanics": [
        {
          "mechanic_type": "drag_drop",
          "instruction_text": "Drag each label to the correct chamber.",
          "zone_labels_used": ["Left Ventricle", "Right Ventricle", "Left Atrium", "Right Atrium"],
          "content_brief": {"generation_goal": "Labels for 4 heart chambers"},
          "expected_item_count": 4,
          "advance_trigger": "completion"
        },
        {
          "mechanic_type": "click_to_identify",
          "instruction_text": "Click the chamber described.",
          "zone_labels_used": ["Left Ventricle", "Right Ventricle", "Left Atrium", "Right Atrium"],
          "content_brief": {"generation_goal": "Functional prompts for 4 chambers", "prompt_style": "function"},
          "expected_item_count": 4
        }
      ]
    }
  ]
}
```

**Graph Builder produces:**
```
Mechanics:
  s1_m1: drag_drop, max_score=40, is_terminal=False
  s1_m2: click_to_identify, max_score=40, is_terminal=True

Connections:
  scene_start → s1_m1 (auto)
  s1_m1 → s1_m2 (completion)
  s1_m2 → scene_end (completion)

Scene: scene_1, starting=s1_m1, max_score=80
Total: 80
```

No IDs, no connections, no arithmetic from the LLM. All derived.

### Example 2: Hierarchical (parent + children)

**Game Designer outputs:**
```json
{
  "scenes": [
    {
      "title": "Body Systems",
      "zone_labels": ["Heart", "Lungs", "Brain", "Left Ventricle", "Right Ventricle", "Bronchi", "Alveoli"],
      "mechanics": [
        {
          "mechanic_type": "drag_drop",
          "instruction_text": "Label the major organs.",
          "zone_labels_used": ["Heart", "Lungs", "Brain"],
          "content_brief": {"generation_goal": "Labels for 3 major organs"},
          "expected_item_count": 3,
          "advance_trigger": "completion",
          "children": [
            {
              "mechanic_type": "click_to_identify",
              "instruction_text": "Now identify the parts of the heart.",
              "zone_labels_used": ["Left Ventricle", "Right Ventricle"],
              "content_brief": {"generation_goal": "Prompts for heart sub-parts"},
              "expected_item_count": 2,
              "advance_trigger": "completion"
            },
            {
              "mechanic_type": "click_to_identify",
              "instruction_text": "Now identify the parts of the lungs.",
              "zone_labels_used": ["Bronchi", "Alveoli"],
              "content_brief": {"generation_goal": "Prompts for lung sub-parts"},
              "expected_item_count": 2
            }
          ]
        }
      ]
    }
  ]
}
```

**Graph Builder produces:**
```
Mechanics:
  s1_m1: drag_drop, max_score=30, parent=None
  s1_m2: click_to_identify, max_score=20, parent=s1_m1
  s1_m3: click_to_identify, max_score=20, parent=s1_m1, is_terminal=True

Connections:
  scene_start → s1_m1 (auto)
  s1_m1 → s1_m2 (parent_completion)
  s1_m2 → s1_m3 (completion)
  s1_m3 → scene_end (completion)

Scene: scene_1, starting=s1_m1, max_score=70
```

The designer just nested `children` inside the parent mechanic. The builder handled all the graph wiring.

### Example 3: Score-Gated + Timed

**Game Designer outputs:**
```json
{
  "scenes": [
    {
      "title": "Speed Round",
      "mechanics": [
        {
          "mechanic_type": "drag_drop",
          "instruction_text": "Label as many parts as you can!",
          "expected_item_count": 8,
          "is_timed": true,
          "time_limit_seconds": 60,
          "advance_trigger": "score_threshold",
          "advance_trigger_value": 0.75
        },
        {
          "mechanic_type": "sequencing",
          "instruction_text": "Now sequence the process.",
          "expected_item_count": 5
        }
      ]
    }
  ]
}
```

**Graph Builder produces:**
```
Mechanics:
  s1_m1: drag_drop, max_score=80, timed=60s
  s1_m2: sequencing, max_score=50, is_terminal=True

Connections:
  scene_start → s1_m1 (auto)
  s1_m1 → s1_m2 (score_threshold, 0.75)
  s1_m2 → scene_end (completion)
```

### Example 4: Multi-Scene with Content-Only Mechanics

**Game Designer outputs:**
```json
{
  "scenes": [
    {
      "title": "Learn the Parts",
      "needs_diagram": true,
      "mechanics": [
        {"mechanic_type": "drag_drop", "expected_item_count": 6}
      ],
      "transition_to_next": "auto"
    },
    {
      "title": "Test Your Memory",
      "needs_diagram": false,
      "mechanics": [
        {"mechanic_type": "memory_match", "expected_item_count": 6}
      ],
      "transition_to_next": "score_gate",
      "transition_min_score_pct": 0.6
    },
    {
      "title": "Clinical Scenario",
      "needs_diagram": false,
      "mechanics": [
        {"mechanic_type": "branching_scenario", "expected_item_count": 4}
      ]
    }
  ]
}
```

**Graph Builder produces:**
```
Scene 1: scene_1, s1_m1(drag_drop, 60pts), transition=auto
Scene 2: scene_2, s2_m1(memory_match, 60pts), transition=score_gate(0.6)
Scene 3: scene_3, s3_m1(branching, 40pts), transition=None (final)
Total: 160pts
```

---

## 7. What This Means for the Pipeline

### Phase 1 becomes TWO steps:

```
Phase 1a: Game Designer (LLM)
  Input: question + pedagogical_context + domain_knowledge + capability_spec
  Output: GameDesignDocument (simple, ordered, no graph concerns)

Phase 1b: Graph Builder (DETERMINISTIC)
  Input: GameDesignDocument
  Output: GamePlan (formal game state graph, valid by construction)
  + Graph Validator (defense in depth)
  On semantic failure → retry Phase 1a with feedback
```

### Updated Phase Flow:

```
Phase 0: Understanding
  ├── input_analyzer ─┐ PARALLEL
  └── dk_retriever    ─┘

Phase 1: Game Design
  ├── game_designer (LLM → GameDesignDocument)
  ├── graph_builder (deterministic → GamePlan)
  └── graph_validator (deterministic → pass/fail with feedback)
      └── on SEMANTIC failure → retry game_designer with feedback

Phase 2: Content Build (per scene, per mechanic)
  ├── scene_context_builder (deterministic)
  ├── mechanic_content_generators (parallel, scene-aware)
  ├── mechanic_content_validators (deterministic → retry with feedback)
  └── scene_interaction_designer (scoring + feedback)

Phase 3: Asset Pipeline (per scene)
  ├── scene_asset_orchestrator (deterministic → AssetManifest)
  ├── asset_dispatchers (parallel pre-built chains)
  └── asset_validator (deterministic → retry chain on zone mismatch)

Phase 4: Assembly (deterministic)
  ├── blueprint_assembler
  └── blueprint_validator
```

---

## 8. Token Savings from This Approach

### LLM Output Reduction

The game designer no longer produces:
- `mechanic_id` strings (saved ~50 tokens per mechanic)
- `mechanic_connections` array (saved ~100 tokens per scene)
- `starting_mechanic_id` (saved ~20 tokens per scene)
- `is_terminal` flags (saved ~10 tokens per mechanic)
- `max_score` per mechanic (saved ~15 tokens per mechanic)
- `scene_max_score` (saved ~15 tokens per scene)
- `total_max_score` (saved ~15 tokens)
- `scene_id` / `scene_number` (saved ~20 tokens per scene)

For a 2-scene, 4-mechanic game: **~400 fewer output tokens** from the game designer.

More importantly: **fewer structural constraints = fewer errors = fewer retries = much bigger savings**.

### Retry Reduction

| Scenario | With LLM graph | With graph builder |
|----------|----------------|-------------------|
| 2 scenes, 3 mechanics | ~40% chance of graph error → retry | ~5% chance of semantic error → retry |
| 3 scenes, 6 mechanics | ~70% chance of graph error → retry | ~10% chance of semantic error → retry |
| Complex hierarchical | ~90% chance of graph error → retry | ~10% chance of semantic error → retry |

Each avoided retry saves ~4000 tokens (full prompt + output).

---

## 9. Implications for Content Generation (Phase 2)

Since the graph builder assigns mechanic IDs, Phase 2 content generators receive:
- `mechanic_id` (from graph builder, not LLM)
- `content_brief` (from game designer)
- `scene_context` (from scene_context_builder)

The content generator doesn't need to worry about graph structure at all. It just fills in the content for one mechanic node.

---

## 10. Implications for Blueprint Assembly (Phase 4)

The blueprint assembler reads the GamePlan graph and translates it directly:

| GamePlan field | Blueprint field |
|---------------|----------------|
| `scene.mechanic_connections[trigger=completion]` | `modeTransitions[{from_mode, to_mode, trigger: "completion"}]` |
| `scene.mechanic_connections[trigger=score_threshold]` | `modeTransitions[{..., trigger: "score_threshold", trigger_value}]` |
| `scene.mechanics[0].mechanic_type` | `mechanics[0].type` (starting mode) |
| `mechanic.is_timed` | `timedChallengeWrappedMode` + `timeLimitSeconds` |
| `mechanic.parent_mechanic_id` | `zoneGroups[{parentZoneId, childZoneIds}]` |
| `scene.transition_to_next` | `sceneTransitions[{type, condition}]` |

The graph → blueprint mapping is deterministic and mechanical.

---

## 11. Summary

| Component | Owner | Type | Produces |
|-----------|-------|------|----------|
| Game Designer | LLM (gemini-2.5-pro) | Creative | GameDesignDocument (simple, no graph IDs) |
| Graph Builder | Code (deterministic) | Structural | GamePlan (formal graph, valid by construction) |
| Graph Validator | Code (deterministic) | Safety net | Pass/fail + categorized feedback |
| Content Generators | LLM (per mechanic) | Creative | MechanicContent (items, prompts, etc.) |
| Asset Orchestrator | Code (deterministic) | Routing | AssetManifest (what chains to run) |
| Asset Chains | Code (pre-built) | Execution | Images, zones, colors |
| Blueprint Assembler | Code (deterministic) | Translation | InteractiveDiagramBlueprint JSON |

**The LLM does the creative work. Code does the structural work. Neither does the other's job.**
