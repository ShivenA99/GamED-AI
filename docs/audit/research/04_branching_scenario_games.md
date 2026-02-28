# Branching Scenario / Decision Tree Games: Component & Asset Research

**Date**: 2026-02-11
**Purpose**: Define what components, assets, interactions, and configurable properties make branching scenario games feel like real, engaging assessment games -- not quizzes with arrows.
**Scope**: NEW components/assets/interactions the mechanic needs. Excludes scoring, hints, combos, and post-game review (covered elsewhere).
**Assessment framing**: This is a TESTING mechanic that tests decision-making. The game must NOT reveal the correct path; it tests whether the learner can find it.

---

## Table of Contents

1. [Reference Systems Analysis](#1-reference-systems-analysis)
2. [Narrative Structures](#2-narrative-structures)
3. [Visual Components & Assets](#3-visual-components--assets)
4. [Node Types & Decision Architecture](#4-node-types--decision-architecture)
5. [State Displays & Consequence Visualization](#5-state-displays--consequence-visualization)
6. [Configurable Properties](#6-configurable-properties)
7. [Pipeline Generation Schema](#7-pipeline-generation-schema)
8. [Current Codebase Gap Analysis](#8-current-codebase-gap-analysis)

---

## 1. Reference Systems Analysis

### 1.1 Body Interact (Medical Simulation)

Body Interact is a virtual patient simulator where every decision has real-time consequences. Key design elements relevant to branching scenarios:

- **Real-time vital parameter monitors**: Vitals update continuously as the learner makes decisions (heart rate, blood pressure, SpO2), creating urgency and consequence visibility.
- **Time-stamped decision logging**: After every case, a report lists all user actions with timestamps, health conditions left untreated, and vital signs at each moment.
- **Branching under time pressure**: Decisions must be made while vitals deteriorate -- the patient's condition changes based on what you do AND what you fail to do.
- **Consequence accumulation**: Not just "right/wrong" at each node, but accumulated state. Ordering the wrong test wastes time while the patient worsens.

**Design lesson for our pipeline**: State variables (vitals, resources, evidence) that change per-decision are what transform a quiz into a simulation. The state display IS the consequence visualization.

### 1.2 Oxford Medical Simulation (VR Clinical Simulation)

Oxford Medical Simulation immerses learners in clinical environments with dynamic virtual patients across 240+ scenarios. Key design elements:

- **Multi-modal interaction**: Learners converse with AI-driven patients, assess, manage, and engage with interdisciplinary teams -- not just click buttons.
- **Scoring matrices**: Actions are logged and automatically matched against clinically-weighted scoring criteria, providing transparent performance breakdowns.
- **Guided debrief with performance metrics**: Automated intelligent feedback shows what was done vs. what should have been done.
- **Faculty-independent scenarios**: Designed for self-directed learning with embedded assessment.

**Design lesson**: The key differentiator is that OMS scenarios feel like practicing in a real clinical environment because the interaction surface is broad (examine, order tests, consult, treat) rather than narrow (pick A/B/C).

### 1.3 H5P Branching Scenario

H5P provides the most widely-deployed open-source branching scenario content type. Key architectural elements:

- **Visual flowchart authoring**: Drag-and-drop canvas resembling a flowchart; authors place nodes and connect them with edges.
- **Mixed content node types**: Each node can contain text, images, video, or other H5P content types (interactive video, course presentation, etc.).
- **Branching question nodes**: A question with multiple response alternatives, where each alternative routes to a different branch.
- **Custom end scenarios**: Each terminal node has its own feedback, score, and optionally a retry path.
- **Zoom navigation**: As the tree grows, a zoom function lets authors see the full structure.
- **Start and end screens**: Configurable introduction and conclusion frames.

**Design lesson**: H5P proves that branching scenarios work even without rich visual assets, but they feel educational rather than game-like. The missing piece is visual immersion -- scene backgrounds, character art, and state displays.

### 1.4 Ren'Py (Visual Novel Engine)

Ren'Py is the dominant engine for visual novels, which are essentially branching scenarios with rich visual presentation. Key architectural elements:

- **Layered character sprites**: Characters are composed of layers -- base body, outfit, expression (eyes, mouth, eyebrows). Ren'Py's `LayeredImage` system lets you swap expression layers without replacing the entire sprite.
- **Scene backgrounds**: Full-screen images that establish location. Loaded via `scene` statements, typically JPG/PNG/WEBP.
- **Branching via `menu` statements**: Choices presented as a list of buttons; each branches to a label (code block). `jump` for one-way branching, `call` for branching that returns.
- **Variable tracking**: Python variables track state (relationship points, inventory items, flags). Conditions check these variables to unlock/lock choices or change dialogue.
- **Transitions**: Dissolve, fade, slide, and custom transitions between scenes create cinematic flow.
- **Save/load system**: Players can save state at any point and reload to explore different branches.
- **Screen language**: Full UI customization -- menus, status bars, inventory displays, character relationship charts.

**Design lesson**: Ren'Py demonstrates that the visual novel model (background + sprites + choices + transitions) is the gold standard for making branching scenarios feel immersive. Expression variants on characters are cheap (just swap eye/mouth layers) and create enormous emotional engagement.

### 1.5 Twine (Interactive Fiction Engine)

Twine is the most accessible tool for building branching narratives. Key architectural elements:

- **Passage-based architecture**: The story is a graph of passages (nodes), connected by links (edges). Each passage contains content and links to other passages.
- **Visual story map**: The authoring interface shows all passages as boxes with connecting lines -- effectively a minimap of the entire narrative.
- **Variables and conditional logic**: Track player state with variables (booleans, numbers, strings). Display different content or enable/disable links based on state.
- **No-code linking**: Double square brackets `[[text]]` create links to new passages. Multiple links in one passage create branching.
- **CSS/HTML customization**: Full control over visual presentation via CSS. Images, audio, video can be embedded.
- **Macro systems**: Harlowe and SugarCube story formats provide macros for inventory, cycling links, timed events, etc.

**Design lesson**: Twine's visual story map (the author-facing passage graph) is exactly what a player-facing minimap should look like -- nodes and edges showing the narrative topology with the current position highlighted and unexplored paths dimmed (fog-of-war).

---

## 2. Narrative Structures

Based on Sam Kabo Ashwell's taxonomy of standard patterns in choice-based games and supplementary research:

### 2.1 Branch-and-Bottleneck (Recommended Default)

```
    [Start]
   /   |   \
  A    B    C     <- diverge: player explores different approaches
   \   |   /
  [Bottleneck 1]  <- converge: critical learning point all paths reach
   /   |   \
  D    E    F     <- diverge again
   \   |   /
  [Bottleneck 2]
      |
   [Ending]
```

- Branches diverge at decision points, but regularly rejoin at "bottleneck" events common to all story versions.
- Requires state-tracking to maintain consequence of past choices even after reconvergence.
- **Best for assessment**: Ensures all learners encounter the same critical learning moments while testing their approach to getting there. The path between bottlenecks is what's being assessed.

### 2.2 Foldback Structure

```
    [Start]
   /       \
  A         B       <- free exploration
   \       /
  [Inevitable Event] <- forced convergence
   /       \
  C         D       <- more exploration
   \       /
   [Climax]
   /   |   \
  E1   E2   E3     <- multiple endings
```

- Built around a series of inevitable events that the story MUST pass through.
- Player has freedom between inevitable events but is "folded back" to the main thread.
- **Best for assessment**: Tests how the learner approaches each phase (diagnosis, treatment planning, execution) while ensuring they encounter all critical phases.

### 2.3 Gauntlet

```
  [Start]
     |
  [Node 1] --fail--> [Bad End 1]
     |
  [Node 2] --fail--> [Bad End 2]
     |
  [Node 3] --fail--> [Bad End 3]
     |
  [Good End]
```

- Linear central thread with branches that lead to failure/death/bad endings.
- Player must make the correct choice at each point to survive to the end.
- One "anointed" path to success; failures prune branches.
- **Best for assessment**: Tests whether the learner can identify the correct action at each critical decision point. Every wrong turn ends the scenario -- high stakes.

### 2.4 Time Cave (Full Branching)

```
         [Start]
        /       \
       A         B
      / \       / \
    A1   A2   B1   B2
   /  \        |
  A1a A1b     B1a
```

- Heavily branching with no re-merging. Every choice leads to a completely different sub-tree.
- Many, many endings. No state tracking needed (the path IS the state).
- Exponential content growth makes this impractical for large scenarios.
- **Best for assessment**: Only suitable for short scenarios (3-4 decision points) where every permutation is educationally distinct. Good for ethical dilemma scenarios where every combination of choices leads to a meaningfully different outcome.

### 2.5 Parallel Paths

```
  [Start]
  /    |    \
 A     B     C     <- three parallel storylines
 |     |     |
 A2    B2    C2
 |     |     |
 A3    B3    C3
  \    |    /
  [Shared End]
```

- Branches run in parallel without crossing.
- Often uses a "sorting hat" early choice to assign the player to a path.
- Each path tells a complete story.
- **Best for assessment**: Tests whether the learner can execute a chosen strategy consistently. Different paths represent different valid approaches (e.g., conservative treatment vs. aggressive intervention).

### 2.6 Loop-and-Grow (Time Loop)

```
  [Start]
     |
  [Loop Entry]  <--------+
   /    |    \            |
  A     B     C           |
   \    |    /            |
  [Outcome Check] --fail--+
     |
  [Success]
```

- The game loops back to the same starting point, but state accumulated from previous loops unlocks new options.
- Each loop iteration reveals new information or options.
- **Best for assessment**: Tests iterative reasoning -- can the learner learn from consequences and improve their approach? Good for troubleshooting scenarios where the learner refines their diagnosis.

### 2.7 Recommended Structure for Pipeline

For educational assessment branching scenarios, **Branch-and-Bottleneck** is the recommended default:

1. It ensures all learners encounter critical learning checkpoints (bottleneck nodes).
2. It tests the APPROACH (which path between bottlenecks) rather than just the final answer.
3. It is content-efficient: branches share bottleneck content, reducing the total node count.
4. State tracking at bottlenecks enables nuanced assessment: "you arrived at the right conclusion but via a suboptimal path."

The pipeline should support configuring the narrative structure type so the LLM can generate appropriate topology.

---

## 3. Visual Components & Assets

### 3.1 Scene Backgrounds

Scene backgrounds establish location and context. They are the single most impactful visual asset for making a branching scenario feel like a game rather than a quiz.

**What they do:**
- Establish where the action takes place (exam room, laboratory, forest, courtroom).
- Change as the player moves through the scenario (background swap = scene transition).
- Create emotional atmosphere (bright vs. dark, sterile vs. organic, calm vs. chaotic).

**Requirements for pipeline generation:**
- 3-6 unique backgrounds per scenario (one per distinct location in the decision tree).
- Consistent art style across all backgrounds in a scenario.
- Aspect ratio: 16:9 or 4:3, minimum 1280x720.
- Multiple nodes can share the same background (e.g., multiple decisions in the same "exam room").

**Configurable properties:**
```typescript
interface SceneBackground {
  id: string;
  location_name: string;           // "Emergency Room", "Laboratory"
  image_url: string;               // Generated image URL
  description: string;             // For alt text and regeneration
  mood: 'calm' | 'tense' | 'neutral' | 'urgent' | 'celebratory';
  time_of_day?: 'morning' | 'afternoon' | 'evening' | 'night';
}
```

### 3.2 Character Sprites with Expressions

Characters give the scenario a human element. They are the primary vehicle for emotional engagement.

**What they do:**
- Represent people the learner interacts with (patient, mentor, colleague, authority figure).
- Express emotional reactions to the learner's decisions via expression changes.
- Appear overlaid on scene backgrounds, positioned left/right/center.

**Expression variants needed per character:**
| Expression | Use Case |
|-----------|----------|
| neutral | Default state, information delivery |
| concerned / worried | When learner chooses a suboptimal path |
| approving / smiling | When learner makes a good decision |
| distressed / pain | Patient deteriorating, urgent situation |
| relieved | After correct intervention |
| surprised | Unexpected choice or outcome |
| serious / stern | Authority figure delivering consequences |

**Requirements for pipeline generation:**
- 1-3 characters per scenario.
- 4-6 expression variants per character (minimum: neutral, concerned, approving, distressed).
- Consistent character design across all expressions (same clothing, hair, etc.).
- Transparent PNG with consistent positioning anchor point.
- Characters should match the art style of scene backgrounds.

**Configurable properties:**
```typescript
interface CharacterSprite {
  id: string;
  name: string;                    // "Dr. Patel", "Patient"
  role: 'subject' | 'mentor' | 'authority' | 'peer' | 'narrator';
  position: 'left' | 'center' | 'right';
  expressions: Record<string, string>;  // expression_name -> image_url
  default_expression: string;
}
```

### 3.3 Decision Node UI

The decision node UI is the core interaction surface. It must present the scenario context, choices, and (optionally) consequences clearly.

**Layout structure (per node):**
```
+--------------------------------------------------+
|  [Scene Background - full width]                  |
|                                                   |
|  [Character Sprite]          [State Display]      |
|                                                   |
|  +--------------------------------------------+  |
|  | [Narrative Text / Question]                 |  |
|  +--------------------------------------------+  |
|                                                   |
|  +--------------------------------------------+  |
|  | [Choice A]  ← button                       |  |
|  +--------------------------------------------+  |
|  | [Choice B]  ← button                       |  |
|  +--------------------------------------------+  |
|  | [Choice C]  ← button (optional)            |  |
|  +--------------------------------------------+  |
|                                                   |
|  [Path Breadcrumbs]          [Confirm Button]     |
+--------------------------------------------------+
```

**Key UI elements:**
1. **Narrative text panel**: Semi-transparent overlay on the background displaying the situation description and question. Should feel like a dialogue box in a visual novel.
2. **Choice buttons**: 2-4 options per node. Styled as prominent cards, not small radio buttons. Each should have enough space for 1-2 sentences.
3. **Confirm button**: Separate from selection. Player selects an option (highlight) then confirms (commit). This prevents accidental choices.
4. **Character dialogue integration**: Character sprite + speech bubble or dialogue box pattern for NPC dialogue.

### 3.4 Consequence Visualization

When a choice leads to a consequence, the player needs to SEE it, not just read about it. This is what separates a game from a quiz.

**Types of consequence visualization:**

| Type | Description | Example |
|------|-------------|---------|
| **State change animation** | A state bar visually changes (goes up/down, changes color) | Patient vitals drop; trust meter decreases |
| **Scene transition** | Background changes to reflect new situation | Move from exam room to ICU |
| **Character expression change** | Character's expression updates to reflect their reaction | Patient looks relieved after correct treatment |
| **Narrative consequence text** | Brief text describing what happened as a result | "The patient's condition stabilizes" |
| **Environment indicator** | Visual cue in the background that something changed | Warning light turns on, weather changes |
| **Inventory/evidence update** | A new item appears in the learner's collection | Test results arrive, new evidence found |

**Important assessment constraint**: In testing mode, consequence visualization must show the EFFECT of the decision without revealing whether it was correct. For example, "The patient's heart rate drops to 45 bpm" (observable consequence) rather than "Wrong! You should have chosen option B" (correctness feedback). The learner must interpret whether the consequence is good or bad.

### 3.5 State Displays

State displays are persistent UI elements showing tracked variables that change based on decisions. They create the feeling of consequence accumulation over time.

**State display types:**

| Display Type | Visual | Use Case |
|-------------|--------|----------|
| **Vital signs monitor** | Animated bars/numbers with colors (green/yellow/red) | Medical scenarios -- heart rate, BP, SpO2, temperature |
| **Resource meter** | Horizontal bar that depletes/fills | Time remaining, budget, energy, credibility |
| **Inventory panel** | Grid or list of collected items | Evidence collected, tests ordered, tools available |
| **Relationship gauge** | Named meters showing NPC attitudes | Trust, respect, cooperation levels |
| **Status indicators** | Small icons with labels | Active conditions, applied treatments, environmental flags |
| **Evidence board** | Pinboard-style layout with gathered clues | Investigation/diagnosis scenarios |
| **Timeline** | Horizontal progression showing time elapsed | Time-sensitive scenarios, project management |

**Configurable properties:**
```typescript
interface StateDisplay {
  type: 'vital_signs' | 'resource_meter' | 'inventory' | 'relationship'
      | 'status_indicators' | 'evidence_board' | 'timeline';
  position: 'top_right' | 'top_left' | 'sidebar' | 'bottom';
  variables: StateVariable[];
  show_changes: boolean;          // Animate changes when state updates
  compact_mode: boolean;          // Collapsed vs expanded
}

interface StateVariable {
  id: string;
  label: string;                  // "Heart Rate", "Budget Remaining"
  type: 'number' | 'percentage' | 'boolean' | 'text' | 'list';
  initial_value: number | string | boolean;
  display_format?: string;        // "{{value}} bpm", "${{value}}"
  thresholds?: {                  // Color coding
    danger: number;               // Red below this
    warning: number;              // Yellow below this
    // Green above warning
  };
  icon?: string;                  // Icon identifier
}
```

### 3.6 Decision Tree Minimap

A minimap shows the player's position within the overall decision tree structure. This creates spatial awareness and a sense of progress.

**Minimap behaviors:**

| Mode | Description | Assessment Suitability |
|------|-------------|----------------------|
| **Fog-of-war** | Only visited nodes visible; unvisited nodes hidden or dimmed | Best for testing -- does not reveal the structure |
| **Full reveal** | Entire tree visible from the start | Bad for testing -- reveals how many choices exist |
| **Progressive reveal** | Adjacent nodes visible, deeper nodes hidden | Good compromise -- shows immediate options without revealing the full tree |
| **Post-game reveal** | Hidden during play, shown in debrief | Best for pure assessment -- no minimap during play |

**Visual elements:**
- Current node: Highlighted (pulsing border or bright color).
- Visited nodes: Solid color, connected by visible edges.
- Unvisited but adjacent nodes: Semi-transparent or outlined.
- Hidden nodes: Not rendered or shown as question marks.
- Edges between nodes: Lines with directional arrows.
- End nodes: Distinct shape (diamond or star) to indicate they are terminal.

**Configurable properties:**
```typescript
interface MinimapConfig {
  enabled: boolean;
  position: 'bottom_left' | 'bottom_right' | 'sidebar';
  reveal_mode: 'fog_of_war' | 'full' | 'progressive' | 'post_game_only';
  show_node_labels: boolean;      // Show node names or just shapes
  show_correctness: boolean;      // Color visited nodes by correctness (TESTING: set false)
  clickable: boolean;             // Can player click minimap to navigate (only if backtrack allowed)
  size: 'small' | 'medium' | 'large';
}
```

### 3.7 Ending Illustrations

Endings are the culmination of the branching path. Different endings should feel distinct and memorable.

**Ending types:**

| Ending Type | Description | Visual Treatment |
|-------------|-------------|-----------------|
| **Optimal** | Best possible outcome; learner made all/most correct decisions | Bright, positive illustration; characters happy/healthy |
| **Acceptable** | Reasonable outcome with some suboptimal choices | Neutral illustration; situation resolved but imperfectly |
| **Suboptimal** | Poor outcome due to critical mistakes | Somber illustration; consequences visible |
| **Failure** | Worst outcome; scenario fails | Dark/urgent illustration; situation unresolved or worsened |

**Requirements for pipeline generation:**
- 2-4 ending illustrations per scenario (minimum: optimal + failure).
- Each ending has a distinct illustration and summary text.
- Ending illustration matches the art style of scene backgrounds.
- Ending text should describe the OUTCOME without explicitly labeling it as "correct" or "wrong" (assessment mode).

### 3.8 Transition Effects

Transitions between nodes create flow and prevent the experience from feeling like a slideshow.

**Transition types:**
| Transition | When Used |
|-----------|-----------|
| **Dissolve/crossfade** | Default between nodes in the same location |
| **Slide left/right** | Moving to a new location |
| **Fade to black + fade in** | Major scene change or time skip |
| **Quick cut** | Urgent or surprising event |
| **Blur + refocus** | Flashback or memory |

---

## 4. Node Types & Decision Architecture

### 4.1 Node Types

Not every node in a branching scenario is a decision point. A rich scenario uses multiple node types:

| Node Type | Description | Player Action |
|-----------|-------------|--------------|
| **Decision** | Present a situation and 2-4 choices | Select and confirm a choice |
| **Information** | Present new information (test results, observation, dialogue) | Click "Continue" to proceed |
| **Dialogue** | Character speaks, optionally with player dialogue choices | Read and respond or continue |
| **State Check** | Gate based on accumulated state (e.g., "if trust > 50, unlock option") | Automatic -- route changes based on state |
| **Event** | Something happens regardless of player choice (interrupt, emergency) | Observe and continue |
| **End** | Terminal node with ending illustration and summary | View results |

### 4.2 Decision Quality Spectrum

For assessment, choices should not be obviously "right" or "wrong." Instead, they should test nuanced decision-making:

| Choice Quality | Description | Points |
|---------------|-------------|--------|
| **Optimal** | Best available action given the context | Full points |
| **Acceptable** | Reasonable but not ideal; leads to a longer/harder path | Partial points |
| **Suboptimal** | Plausible but incorrect; leads to negative consequences | Minimal/no points |
| **Harmful** | Clearly wrong; leads to significant negative consequences | Negative points or scenario failure |

The 3-4 options per decision point should span this spectrum. Crucially, the labels "optimal/acceptable/suboptimal/harmful" are INTERNAL to the pipeline -- the player never sees these labels. They only see the consequences.

### 4.3 Choice Design Principles (from Game Design Research)

Based on analysis of Articulate, game design research, and interactive fiction best practices:

1. **All choices should be plausible.** If one option is obviously absurd, it is not testing decision-making.
2. **Choices should require domain knowledge.** The correct choice should be identifiable only by someone who understands the subject matter.
3. **Avoid the "one great, one okay, one terrible" pattern** where the quality gradient is obvious from the text alone.
4. **Consequences should be delayed when possible.** Immediate feedback on every choice turns the scenario into a quiz. Some consequences should only become apparent 2-3 nodes later.
5. **Show observable consequences, not correctness judgments.** "The patient's condition worsens" (observable) vs. "Wrong answer!" (judgment). The learner must interpret the consequence.
6. **Choices should feel like real decisions a practitioner would face**, not trick questions or gotchas.

---

## 5. State Displays & Consequence Visualization

### 5.1 The State-Consequence Loop

The core engagement loop in a branching scenario game is:

```
[Observe State] -> [Make Decision] -> [See Consequence] -> [State Updates] -> [Observe New State] -> ...
```

Without state displays, the player cannot observe the cumulative effect of their decisions. Without consequence visualization, individual decisions feel weightless.

### 5.2 State Variable Categories

| Category | Example Variables | Display Style |
|----------|------------------|---------------|
| **Health/Vitals** | Heart rate, blood pressure, temperature, pain level | Animated monitors with threshold colors |
| **Resources** | Time, budget, energy, supplies | Depleting horizontal bars |
| **Relationships** | Trust, rapport, authority, credibility | Named gauges (0-100) |
| **Evidence/Knowledge** | Collected data, observations, test results | Inventory list or pinboard |
| **Environment** | Location, time of day, weather, alert level | Status icons or background changes |
| **Progress** | Decisions made, nodes visited, percentage complete | Progress bar or step counter |

### 5.3 Per-Node State Changes

Each decision node in the pipeline should specify what state changes occur for each choice:

```typescript
interface NodeStateChange {
  variable_id: string;           // "heart_rate", "trust_level"
  operation: 'set' | 'add' | 'subtract' | 'multiply' | 'toggle';
  value: number | string | boolean;
  display_effect?: 'flash' | 'pulse' | 'shake' | 'none';
}
```

### 5.4 Consequence Delivery Timing

| Timing | Description | Use Case |
|--------|-------------|----------|
| **Immediate** | Shown right after choice confirmation | Obvious cause-and-effect (give medication -> vitals change) |
| **Delayed (next node)** | Consequence appears at the START of the next node | Effects that take time (test results arrive, patient responds) |
| **Accumulated (bottleneck)** | Multiple past choices compound at a checkpoint | Summary effect of approach quality over several decisions |
| **Hidden** | State changes silently; player must notice via state display | Subtle consequences that reward careful observation |

---

## 6. Configurable Properties

These properties should be configurable at the scenario level to support different subject domains, visual styles, and assessment requirements.

### 6.1 Visual Style Configuration

```typescript
interface BranchingVisualConfig {
  visual_style: 'illustrated' | 'photorealistic' | 'pixel_art' | 'comic'
              | 'minimalist' | 'medical' | 'nature' | 'corporate';
  color_palette: 'warm' | 'cool' | 'neutral' | 'high_contrast' | 'pastel' | 'dark';
  layout: 'visual_novel' | 'card_based' | 'fullscreen_immersive';

  // Visual novel layout options
  dialogue_box_style: 'bottom_panel' | 'speech_bubble' | 'side_panel' | 'overlay';
  dialogue_box_opacity: number;   // 0.0 - 1.0

  // Character display
  character_display: 'sprites_on_background' | 'portrait_panel' | 'avatar_only' | 'none';
  character_position_count: 1 | 2 | 3;  // How many character slots

  // Transition effects
  transition_style: 'dissolve' | 'slide' | 'fade' | 'cut' | 'none';
  transition_duration_ms: number;
}
```

### 6.2 Navigation & Interaction Configuration

```typescript
interface BranchingInteractionConfig {
  // Navigation
  allow_backtrack: boolean;            // Can player undo last choice
  backtrack_depth: number;             // How many steps back (0 = unlimited)

  // Choice presentation
  choice_style: 'buttons' | 'cards' | 'dialogue_options' | 'action_list';
  confirm_required: boolean;           // Require explicit confirm after selection
  shuffle_choices: boolean;            // Randomize choice order

  // Minimap
  show_minimap: boolean;
  minimap_reveal_mode: 'fog_of_war' | 'progressive' | 'full' | 'post_game_only';
  minimap_position: 'bottom_left' | 'bottom_right' | 'sidebar';

  // Consequences
  show_consequences: boolean;          // Show consequence text after choices
  consequence_delay_ms: number;        // How long to show consequence
  consequence_style: 'text' | 'animation' | 'state_change' | 'narrative';

  // Path display
  show_path_breadcrumbs: boolean;      // Show path taken so far
  show_decision_count: boolean;        // "Decision 3 of ~8"

  // Timer (optional pressure)
  time_limit_per_decision_s: number | null;  // null = no timer
  time_limit_total_s: number | null;         // null = no total timer
}
```

### 6.3 State Display Configuration

```typescript
interface StateDisplayConfig {
  enabled: boolean;
  type: 'vital_signs' | 'resource_meters' | 'inventory' | 'relationship_gauges'
      | 'status_board' | 'evidence_board' | 'custom';
  position: 'top_right' | 'top_left' | 'sidebar' | 'bottom' | 'overlay';
  compact_mode: boolean;               // Collapsed by default, expand on hover
  animate_changes: boolean;            // Flash/pulse when values change
  show_change_delta: boolean;          // Show "+5" or "-10" next to value
  variables: StateVariable[];          // List of tracked variables
}
```

### 6.4 Narrative Configuration

```typescript
interface NarrativeConfig {
  structure: 'branch_and_bottleneck' | 'foldback' | 'gauntlet' | 'time_cave'
           | 'parallel_paths' | 'loop_and_grow';
  tone: 'clinical' | 'dramatic' | 'casual' | 'urgent' | 'investigative' | 'educational';
  narrator_voice: 'second_person' | 'third_person' | 'first_person' | 'none';

  // Ending configuration
  ending_count: number;                // Target number of distinct endings
  multiple_valid_endings: boolean;     // More than one "correct" ending
  show_ending_type: boolean;           // Label endings as "optimal", "acceptable", etc.

  // Scenario framing
  scenario_context: string;            // "You are a junior doctor on night shift..."
  role_description: string;            // "Emergency Medicine Resident"
  setting_description: string;         // "City Hospital Emergency Department"
}
```

---

## 7. Pipeline Generation Schema

### 7.1 Decision Node Schema

The LLM pipeline must generate a complete decision tree. Each node requires:

```typescript
interface PipelineDecisionNode {
  id: string;                          // "node_1", "node_2", etc.
  type: 'decision' | 'information' | 'dialogue' | 'state_check' | 'event' | 'end';

  // Content
  narrative_text: string;              // Situation description / dialogue
  question?: string;                   // Question posed to the learner (decision nodes)

  // Visual
  scene_background_id: string;         // Reference to a SceneBackground
  characters_present: Array<{
    character_id: string;
    expression: string;                // "neutral", "concerned", etc.
    position: 'left' | 'center' | 'right';
  }>;

  // Choices (for decision and dialogue nodes)
  choices: PipelineChoice[];

  // State changes (applied when entering this node)
  state_changes_on_enter?: NodeStateChange[];

  // End node properties
  is_end_node: boolean;
  ending_type?: 'optimal' | 'acceptable' | 'suboptimal' | 'failure';
  ending_illustration_id?: string;     // Reference to ending illustration
  ending_summary?: string;             // Summary text for this ending

  // Metadata
  is_bottleneck: boolean;              // True for convergence points
  estimated_difficulty: 'easy' | 'medium' | 'hard';
}
```

### 7.2 Choice Schema

```typescript
interface PipelineChoice {
  id: string;                          // "choice_1a", "choice_1b", etc.
  text: string;                        // Choice text shown to the learner
  next_node_id: string | null;         // Where this choice leads (null for end)

  // Assessment (INTERNAL -- not shown to learner during play)
  quality: 'optimal' | 'acceptable' | 'suboptimal' | 'harmful';
  points: number;                      // Score for this choice

  // Consequence (shown to learner)
  consequence_text?: string;           // Observable consequence description
  consequence_timing: 'immediate' | 'delayed' | 'hidden';

  // State changes triggered by this choice
  state_changes: NodeStateChange[];

  // Character reactions
  character_reactions?: Array<{
    character_id: string;
    new_expression: string;
    dialogue?: string;                 // Character speaks in response
  }>;
}
```

### 7.3 Complete Scenario Schema

```typescript
interface PipelineBranchingScenario {
  // Metadata
  scenario_title: string;
  scenario_description: string;
  subject_domain: string;              // "medicine", "ecology", "ethics", etc.
  learning_objective: string;

  // Structure
  narrative_structure: 'branch_and_bottleneck' | 'foldback' | 'gauntlet'
                     | 'time_cave' | 'parallel_paths' | 'loop_and_grow';
  start_node_id: string;
  nodes: PipelineDecisionNode[];

  // Characters
  characters: CharacterSprite[];

  // Scenes (backgrounds)
  scene_backgrounds: SceneBackground[];

  // Ending illustrations
  ending_illustrations: Array<{
    id: string;
    ending_type: 'optimal' | 'acceptable' | 'suboptimal' | 'failure';
    description: string;               // For image generation prompt
    image_url?: string;                // Populated after asset generation
  }>;

  // State system
  state_variables: StateVariable[];
  initial_state: Record<string, number | string | boolean>;

  // Configuration
  visual_config: BranchingVisualConfig;
  interaction_config: BranchingInteractionConfig;
  state_display_config: StateDisplayConfig;
  narrative_config: NarrativeConfig;
}
```

### 7.4 Asset Generation Requirements

The pipeline must generate these assets for a complete branching scenario:

| Asset Type | Generation Method | Count per Scenario |
|-----------|-------------------|-------------------|
| Scene backgrounds | AI image generation (per unique location) | 3-6 |
| Character sprites | AI image generation (per character per expression) | 1-3 characters x 4-6 expressions = 4-18 images |
| Ending illustrations | AI image generation (per ending type) | 2-4 |
| Decision tree structure | LLM generation (nodes + edges + choices) | 1 graph with 5-15 nodes |
| Narrative text per node | LLM generation | 5-15 passages |
| Consequence text per choice | LLM generation | 10-45 consequence descriptions |
| State variable definitions | LLM generation | 3-8 variables |
| Per-choice state changes | LLM generation | 10-45 state change sets |
| Character dialogue | LLM generation (per character per node) | Variable |

### 7.5 Example: Medical Diagnosis Scenario

**Topic**: "A patient presents with chest pain. Diagnose and treat."

```json
{
  "scenario_title": "Emergency Chest Pain Assessment",
  "subject_domain": "medicine",
  "narrative_structure": "branch_and_bottleneck",
  "start_node_id": "node_1",

  "characters": [
    {
      "id": "patient",
      "name": "Mr. Thompson",
      "role": "subject",
      "expressions": {
        "neutral": "patient_neutral.png",
        "pain": "patient_pain.png",
        "distressed": "patient_distressed.png",
        "relieved": "patient_relieved.png"
      },
      "default_expression": "pain"
    },
    {
      "id": "nurse",
      "name": "Nurse Patel",
      "role": "peer",
      "expressions": {
        "neutral": "nurse_neutral.png",
        "concerned": "nurse_concerned.png",
        "approving": "nurse_approving.png"
      },
      "default_expression": "neutral"
    }
  ],

  "scene_backgrounds": [
    { "id": "bg_triage", "location_name": "Triage Area", "mood": "urgent" },
    { "id": "bg_exam", "location_name": "Examination Room", "mood": "tense" },
    { "id": "bg_icu", "location_name": "ICU", "mood": "urgent" },
    { "id": "bg_recovery", "location_name": "Recovery Ward", "mood": "calm" }
  ],

  "state_variables": [
    {
      "id": "heart_rate",
      "label": "Heart Rate",
      "type": "number",
      "initial_value": 110,
      "display_format": "{{value}} bpm",
      "thresholds": { "danger": 40, "warning": 60 }
    },
    {
      "id": "patient_stability",
      "label": "Patient Stability",
      "type": "percentage",
      "initial_value": 60,
      "thresholds": { "danger": 20, "warning": 40 }
    },
    {
      "id": "time_elapsed",
      "label": "Time Elapsed",
      "type": "number",
      "initial_value": 0,
      "display_format": "{{value}} min"
    }
  ],

  "nodes": [
    {
      "id": "node_1",
      "type": "decision",
      "scene_background_id": "bg_triage",
      "narrative_text": "A 55-year-old male presents to the emergency department with severe chest pain radiating to his left arm. He is diaphoretic and anxious. Vitals show elevated heart rate and blood pressure.",
      "question": "What is your first action?",
      "characters_present": [
        { "character_id": "patient", "expression": "pain", "position": "center" },
        { "character_id": "nurse", "expression": "concerned", "position": "right" }
      ],
      "choices": [
        {
          "id": "c1a",
          "text": "Order a 12-lead ECG immediately",
          "next_node_id": "node_2a",
          "quality": "optimal",
          "points": 10,
          "consequence_text": "The ECG is performed within 2 minutes. Results are on their way.",
          "state_changes": [
            { "variable_id": "time_elapsed", "operation": "add", "value": 2 }
          ]
        },
        {
          "id": "c1b",
          "text": "Take a detailed patient history first",
          "next_node_id": "node_2b",
          "quality": "acceptable",
          "points": 5,
          "consequence_text": "You spend 8 minutes gathering history. The patient's pain intensifies during the interview.",
          "state_changes": [
            { "variable_id": "time_elapsed", "operation": "add", "value": 8 },
            { "variable_id": "patient_stability", "operation": "subtract", "value": 10 }
          ]
        },
        {
          "id": "c1c",
          "text": "Administer pain medication immediately",
          "next_node_id": "node_2c",
          "quality": "suboptimal",
          "points": 2,
          "consequence_text": "The patient's pain decreases, but you have not yet identified the cause.",
          "state_changes": [
            { "variable_id": "time_elapsed", "operation": "add", "value": 5 },
            { "variable_id": "heart_rate", "operation": "subtract", "value": 10 }
          ]
        }
      ],
      "is_end_node": false,
      "is_bottleneck": false
    }
  ]
}
```

---

## 8. Current Codebase Gap Analysis

### 8.1 What Exists

The current codebase has skeletal support for branching scenarios:

**Backend schemas** (`backend/app/agents/schemas/`):
- `BranchingDesign` in `game_design_v3.py` -- minimal: `nodes: List[Dict]`, `start_node_id`, `show_path_taken`, `allow_backtrack`, `show_consequences`, `multiple_valid_endings`.
- `DecisionNode` and `DecisionOption` in `interactive_diagram.py` -- basic: id, question, description, imageUrl, options, isEndNode, endMessage.
- `BranchingConfig` in `interactive_diagram.py` -- nodes list, startNodeId, showPathTaken, allowBacktrack, showConsequences, multipleValidEndings.

**Frontend types** (`frontend/src/components/templates/InteractiveDiagramGame/types.ts`):
- `DecisionNode`, `DecisionOption`, `BranchingConfig`, `BranchingProgress` interfaces.
- `BranchingProgress` tracks: `currentNodeId`, `pathTaken[]`.

**Frontend component** (`frontend/src/components/templates/InteractiveDiagramGame/interactions/BranchingScenario.tsx`):
- Functional but visually minimal -- white cards with text buttons.
- No scene backgrounds, no character sprites, no state displays, no minimap, no transitions.
- Basic path breadcrumbs (green/red pills showing step correctness).
- Consequence text shown inline after choice.
- Backtrack support exists.
- Store integration props (`storeProgress`, `onChoiceMade`, `onUndo`) exist but component uses internal state.

**Pipeline status** (from `12_v3_mechanic_general_redesign.md`):
- `branching_scenario` is listed as **BROKEN** across ALL pipeline stages (Game Designer, Scene Architect, Interaction Designer, Asset Generator, Blueprint Assembler).
- No agent generates decision tree structures, scene images, or character art.
- `generate_mechanic_content` has NO handler for `branching_scenario`.

### 8.2 What Is Missing

| Gap | Category | Priority |
|-----|----------|----------|
| **No scene backgrounds** | Visual Assets | P0 -- Critical |
| **No character sprites or expressions** | Visual Assets | P0 -- Critical |
| **No ending illustrations** | Visual Assets | P1 -- High |
| **No state display system** | UI Component | P0 -- Critical |
| **No state variables in node schema** | Data Model | P0 -- Critical |
| **No per-choice state changes** | Data Model | P0 -- Critical |
| **No node type differentiation** | Data Model | P1 -- High |
| **No minimap component** | UI Component | P1 -- High |
| **No consequence visualization (beyond text)** | UI Component | P1 -- High |
| **No transition effects between nodes** | UI Component | P2 -- Medium |
| **No narrative structure configuration** | Config | P2 -- Medium |
| **No visual style configuration** | Config | P2 -- Medium |
| **No character dialogue integration** | UI Component | P2 -- Medium |
| **No decision tree generation tool** | Pipeline | P0 -- Critical |
| **No scene image generation workflow** | Pipeline | P0 -- Critical |
| **No character sprite generation workflow** | Pipeline | P0 -- Critical |
| **No timer/pressure mechanics** | UI Component | P3 -- Low |

### 8.3 Schema Enhancement Requirements

The existing `DecisionNode` interface needs these additions:

```typescript
// Current (minimal)
interface DecisionNode {
  id: string;
  question: string;
  description?: string;
  imageUrl?: string;
  options: DecisionOption[];
  isEndNode?: boolean;
  endMessage?: string;
}

// Enhanced (what this research recommends)
interface DecisionNode {
  id: string;
  type: 'decision' | 'information' | 'dialogue' | 'state_check' | 'event' | 'end';

  // Content
  narrative_text: string;
  question?: string;

  // Visual
  scene_background_id: string;
  characters_present: CharacterPresence[];

  // Choices
  options: DecisionOption[];

  // State
  state_changes_on_enter?: NodeStateChange[];

  // End properties
  isEndNode: boolean;
  ending_type?: 'optimal' | 'acceptable' | 'suboptimal' | 'failure';
  ending_illustration_id?: string;
  endMessage?: string;

  // Structure metadata
  is_bottleneck?: boolean;
}
```

The existing `DecisionOption` interface needs these additions:

```typescript
// Current (minimal)
interface DecisionOption {
  id: string;
  text: string;
  nextNodeId: string | null;
  isCorrect?: boolean;
  consequence?: string;
  points?: number;
}

// Enhanced
interface DecisionOption {
  id: string;
  text: string;
  nextNodeId: string | null;

  // Assessment (internal, not shown to player)
  quality: 'optimal' | 'acceptable' | 'suboptimal' | 'harmful';
  points: number;

  // Consequence (shown to player)
  consequence_text?: string;
  consequence_timing: 'immediate' | 'delayed' | 'hidden';

  // State changes
  state_changes: NodeStateChange[];

  // Character reactions
  character_reactions?: CharacterReaction[];
}
```

The existing `BranchingConfig` interface needs these additions:

```typescript
// Current (minimal)
interface BranchingConfig {
  nodes: DecisionNode[];
  startNodeId: string;
  showPathTaken?: boolean;
  allowBacktrack?: boolean;
  showConsequences?: boolean;
  multipleValidEndings?: boolean;
  instructions?: string;
}

// Enhanced
interface BranchingConfig {
  // Core structure
  nodes: DecisionNode[];
  startNodeId: string;

  // Characters & scenes
  characters: CharacterSprite[];
  scene_backgrounds: SceneBackground[];
  ending_illustrations: EndingIllustration[];

  // State system
  state_variables: StateVariable[];
  initial_state: Record<string, number | string | boolean>;
  state_display: StateDisplayConfig;

  // Navigation
  showPathTaken: boolean;
  allowBacktrack: boolean;
  backtrack_depth: number;
  showConsequences: boolean;

  // Minimap
  minimap: MinimapConfig;

  // Visual
  visual_config: BranchingVisualConfig;

  // Narrative
  narrative_structure: string;
  multipleValidEndings: boolean;
  instructions: string;

  // Transitions
  transition_style: string;
  transition_duration_ms: number;
}
```

### 8.4 New Frontend Components Needed

| Component | Purpose | Estimated Complexity |
|-----------|---------|---------------------|
| `SceneBackgroundLayer` | Render full-width background image with transition effects | Medium |
| `CharacterSpriteLayer` | Position 1-3 character sprites with expression swapping | Medium |
| `DialogueBox` | Visual novel-style text panel (bottom panel, speech bubble, or side panel modes) | Medium |
| `StateDisplay` | Render state variables as vital signs, meters, inventory, etc. | High |
| `DecisionMinimap` | Graph visualization of decision tree with fog-of-war | High |
| `ConsequenceOverlay` | Animated consequence display (state change animation, narrative text) | Medium |
| `EndingScreen` | Full-screen ending illustration with summary and outcome description | Low |
| `ChoicePanel` | Enhanced choice buttons (cards, dialogue options, action list styles) | Medium |
| `PathBreadcrumbs` | Enhanced path display showing node labels and decision quality indicators | Low |

### 8.5 Pipeline Tool Additions

| Tool | Agent | Purpose |
|------|-------|---------|
| `generate_decision_tree` | scene_architect_v3 | Generate complete node graph with choices, consequences, state changes |
| `generate_scenario_characters` | scene_architect_v3 | Define characters with roles, expressions, and visual descriptions |
| `generate_state_system` | scene_architect_v3 | Define state variables and per-choice state changes |
| `generate_scene_descriptions` | scene_architect_v3 | Define scene backgrounds with location, mood, and image prompts |
| `enrich_branching_content` | interaction_designer_v3 | Add consequence timing, character reactions, transition effects |
| `generate_character_sprite` | asset_generator_v3 | Generate character image with specific expression |
| `generate_scene_background` | asset_generator_v3 | Generate location background image |
| `generate_ending_illustration` | asset_generator_v3 | Generate ending-specific illustration |
| `assemble_branching_blueprint` | blueprint_assembler_v3 | Combine all assets into BranchingConfig for frontend |

---

## Sources

- [Body Interact Virtual Patient Simulator](https://bodyinteract.com/)
- [Oxford Medical Simulation Platform](https://oxfordmedicalsimulation.com/platform/)
- [H5P Branching Scenario](https://h5p.org/branching-scenario)
- [H5P Branching Scenario Guide](https://help.h5p.com/hc/en-us/articles/7506761308957-Branching-Scenario-Guide)
- [Ren'Py Visual Novel Engine](https://www.renpy.org/)
- [Ren'Py Branching & Recombining](https://www.renpy.org/wiki/renpy/doc/tutorials/Branching_&_Recombining_the_Story)
- [Twine Interactive Fiction Tool](https://twinery.org/)
- [Standard Patterns in Choice-Based Games (Sam Kabo Ashwell)](https://heterogenoustasks.wordpress.com/2015/01/26/standard-patterns-in-choice-based-games/)
- [Branching Narratives Explained (Pominis)](https://www.pominis.com/blog/branching-narratives-explained-designing-choices-that-matter)
- [Articulate: Craft Branched Scenario Choices Like a Game Designer](https://community.articulate.com/blog/articles/how-to-craft-branched-scenario-choices-like-a-game-designer/1092335)
- [Branch and Bottleneck Scenario Structure (Christy Tucker)](https://christytuckerlearning.com/branch-and-bottleneck-scenario-structure/)
- [Beyond Branching: Quality-Based and Salience-Based Narrative Structures (Emily Short)](https://emshort.blog/2016/04/12/beyond-branching-quality-based-and-salience-based-narrative-structures/)
- [Setting Up Visual Novel Sprites (Crystal Game Works)](https://crystalgameworks.com/setting-up-visual-novel-sprites/)
- [VNDev Wiki: Sprites](https://vndev.wiki/Sprite)
- [VNDev Wiki: Endings](https://vndev.wiki/Ending)
- [VNCCS Visual Novel Character Creation Suite](https://apatero.com/blog/vnccs-visual-novel-character-creation-suite-comfyui-2025)
- [Branching Scenarios in E-Learning (eLearning Industry)](https://elearningindustry.com/branching-scenarios-need-know)
- [Branching Scenarios Best Practices (iSpring)](https://www.ispringsolutions.com/blog/branching-scenarios)
- [Gamified Assessments 2025 (Practice Aptitude Tests)](https://www.practiceaptitudetests.com/resources/gamified-assessments-how-to-pass-them-in-2023/)
- [Visual Novel UI Design Anatomy (Fuwanovel)](https://forums.fuwanovel.moe/blogs/entry/4226-ui-design-%E2%80%93-an-anatomy-of-visual-novels/)
- [Choice and Consequence System (TV Tropes)](https://tvtropes.org/pmwiki/pmwiki.php/Main/ChoiceAndConsequenceSystem)
- [Multiple Endings (TV Tropes)](https://tvtropes.org/pmwiki/pmwiki.php/Main/MultipleEndings)
- [Game Narrative Design Principles and Flow (PulseGeek)](https://pulsegeek.com/articles/game-narrative-design-principles-patterns-and-flow/)
- [Interactive Story Structures (Handwritten Games)](https://www.handwrittengames.com/interactive-structures)
