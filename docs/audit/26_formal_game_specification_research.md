# Research Report: Generating Formal/Declarative Game Specifications from Natural Language using LLMs

**Date:** 2026-02-12
**Context:** GamED.AI v2 -- Moving from prose-based game specifications to formal, executable game rules

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Existing Formalisms for Game Specification](#2-existing-formalisms-for-game-specification)
3. [Key Papers and Projects](#3-key-papers-and-projects)
4. [Techniques for Reliable Structured Generation](#4-techniques-for-reliable-structured-generation)
5. [Multi-Scene and Multi-Mechanic Challenges](#5-multi-scene-and-multi-mechanic-challenges)
6. [Educational Game Specific Considerations](#6-educational-game-specific-considerations)
7. [Industry Case Studies](#7-industry-case-studies)
8. [Open-Source Tools and Frameworks](#8-open-source-tools-and-frameworks)
9. [Key Takeaways for GamED.AI](#9-key-takeaways-for-gamed-ai)

---

## 1. Executive Summary

The field of LLM-based game specification generation is rapidly evolving (2023-2025), with research converging on several key findings:

- **DSL intermediation is the dominant pattern**: The most successful systems do NOT have LLMs generate raw code or free-form prose. Instead, they translate natural language into a constrained Domain-Specific Language (DSL) or structured JSON schema, which is then validated and executed by a deterministic engine.
- **Constrained decoding achieves 100% structural validity**: OpenAI's Structured Outputs and tools like XGrammar guarantee that LLM outputs conform to JSON schemas via grammar-guided token masking. Anthropic has followed with constrained decoding for Claude.
- **Iterative validation is essential for semantic correctness**: Even with perfect structural compliance, logical/semantic correctness requires validation loops -- unit tests against gameplay traces, LLM-as-judge evaluation, or formal verification.
- **Multi-mechanic games remain an open challenge**: No existing system handles GamED.AI's level of mechanic diversity (10 types) with multi-scene transitions. This is a genuine research gap.
- **The neuro-symbolic split (Flavor vs. Mechanics) is the recommended architecture**: Let LLMs handle creative content generation while deterministic systems handle rule execution.

---

## 2. Existing Formalisms for Game Specification

### 2.1 Video Game Description Language (VGDL)

- **Source:** General Video Game AI (GVGAI) framework
- **URL:** Used extensively in academic research; see [GVGAI competition](http://gvgai.net/)
- **Structure:** Four mandatory blocks:
  - `SpriteSet`: Defines game objects and their types
  - `LevelMapping`: Maps characters to sprites
  - `InteractionSet`: Specifies collision/interaction behaviors
  - `TerminationSet`: Defines win/lose conditions
- **Strengths:** Concise, human-readable, well-studied in PCG research
- **Limitations:** Designed for simple 2D arcade games; no support for multi-scene, complex educational mechanics, or adaptive difficulty
- **Relevance to GamED.AI:** Low direct applicability due to simplicity, but the four-block decomposition pattern (objects, mappings, interactions, termination) is a useful structural template

### 2.2 Game Description Language (GDL)

- **Source:** Stanford General Game Playing project (Michael Genesereth)
- **URL:** [GDL at Stanford](http://ggp.stanford.edu/notes/gdl.html)
- **Structure:** First-order logic variant of Datalog using predicates: `role`, `init`, `legal`, `next`, `terminal`, `goal`
- **Strengths:** Mathematically rigorous, supports formal verification, universal (proven Turing-complete for finite games)
- **Limitations:** Only handles deterministic, perfect-information, turn-based games. Extensions (GDL-II, GDL-III) add incomplete information and epistemic reasoning but increase complexity significantly
- **Relevance to GamED.AI:** The predicate structure (`legal` actions, `next` state transitions, `terminal` conditions, `goal` scoring) maps well to educational game mechanics

### 2.3 Custom JSON DSLs (Emerging Pattern)

- **Examples:** Real-Time World Crafting DSL, G-KMS schema, json-rules-engine
- **Structure:** JSON-based specifications with typed fields for entities, components, rules, and state transitions
- **Strengths:** Directly consumable by web frontends (React), schema-validatable via JSON Schema, LLM-friendly
- **Limitations:** No standardization; each project invents its own
- **Relevance to GamED.AI:** **Highest relevance** -- this is the path GamED.AI should pursue, with a custom DSL tailored to its 10 mechanic types

### 2.4 State Machines (XState / FSM)

- **Source:** [XState](https://xstate.js.org/) / [Stately Agent](https://stately.ai/agent)
- **Structure:** States, transitions, guards, actions, context
- **Strengths:** Visual debugging, formal verification possible, natural fit for game flow (scene transitions, mechanic phases)
- **Limitations:** Can become complex for games with many parallel subsystems
- **Relevance to GamED.AI:** Excellent for modeling scene transitions and mechanic phase progression; could complement a JSON DSL

---

## 3. Key Papers and Projects

### 3.1 Game Generation via Large Language Models (VGDL)

- **Title:** "Game Generation via Large Language Models"
- **Authors:** Chengpeng Hu, Yunlong Zhao, Jialin Liu
- **Venue:** IEEE Conference on Games 2024
- **URL:** [arXiv:2404.08706](https://arxiv.org/abs/2404.08706)
- **What they generate:** Complete VGDL game specifications (rules + levels simultaneously)
- **Formalism:** VGDL (SpriteSet, LevelMapping, InteractionSet, TerminationSet)
- **Models tested:** GPT-4, GPT-3.5, Gemma 7B
- **Reliability metrics:**
  - GPT-4 with full prompt (P7): **10/10 correct** games (rules + levels)
  - GPT-3.5 best case: **4/10 correct**
  - Gemma 7B: **0/10** (failed to generate parsable games in all trials)
- **Correctness approach:** Three-tier validation -- parsability, logical completeness (all four VGDL blocks present), and mapping correctness
- **Key insight:** Providing grammar context and examples in prompts is essential. Syntax needed to be aligned with natural language word order (e.g., replacing `killSprite` with `removeSprite`) to match LLM expectations
- **Multi-scene support:** None
- **Relevance:** Demonstrates that structured game description languages dramatically improve LLM reliability vs. free-form generation, but simple games only

### 3.2 Boardwalk: Board Game Generation Framework

- **Title:** "Boardwalk: Towards a Framework for Creating Board Games with LLMs"
- **Authors:** Alvaro Guglielmin Becker, Gabriel Bauer de Oliveira, Lana Bertoldo Rossato, Anderson Rocha Tavares
- **Venue:** SBGames 2025 / arXiv
- **URL:** [arXiv:2508.16447](https://arxiv.org/abs/2508.16447)
- **GitHub:** [github.com/LabCRAIG/boardwalk](https://github.com/LabCRAIG/boardwalk)
- **What they generate:** Executable Python implementations of board games from natural language rules
- **Formalism:** Python code conforming to a standardized API (Board class + Game class with 4 mandatory methods: `validate_move`, `game_finished`, `get_winner`, `next_player`)
- **Models tested:** Claude 3.7 Sonnet, GPT-4o, DeepSeek V3
- **Reliability metrics:**
  - Claude 3.7 Sonnet: **55.6%** error-free games (best)
  - GPT-4o: **33.3%**
  - DeepSeek V3: **27.8%**
- **Key insight:** Constraining LLMs to a standardized API actually _increased_ error frequency (more API compliance errors) but reduced error _severity_. The API provides a safety net even when generation is imperfect.
- **Error types:** Move validation errors most common, followed by game ending conditions, additional effects (captures/promotions), and API compliance
- **Multi-scene support:** Single-game only
- **Relevance:** Shows that even state-of-the-art LLMs achieve only ~55% perfect generation for board games, reinforcing the need for validation loops

### 3.3 Real-Time World Crafting (DSL Approach)

- **Title:** "Real-Time World Crafting: Generating Structured Game Behaviors from Natural Language with Large Language Models"
- **Authors:** Austin Drake, Hang Dong
- **Year:** 2025
- **URL:** [arXiv:2510.16952](https://arxiv.org/abs/2510.16952)
- **What they generate:** Game entity behaviors from natural language via a constrained DSL
- **Formalism:** Custom JSON-based DSL consumed by an Entity-Component-System (ECS) framework
- **Architecture:** Three layers:
  1. LLM interface translates player requests into DSL
  2. Custom ECS framework parses DSL to instantiate game entities/components
  3. Commercial game engine renders ECS state
- **Models tested:** Gemini, GPT, and Claude families
- **Correctness approach:** DSL acts as a safety layer -- LLM cannot generate arbitrary code, only structured data matching the DSL schema. Chain-of-Thought prompting generates a plan first, then produces final JSON
- **Key insight:** Using a DSL as an intermediate layer provides safety (no arbitrary code execution) and verifiability (DSL can be validated against schema before execution). CoT improved creative alignment; few-shot examples were necessary for complex DSL scripts
- **Multi-scene support:** Limited (focused on single-scene entity behaviors)
- **Relevance:** **Highly relevant architecture pattern** for GamED.AI -- the three-layer approach (LLM -> DSL -> engine) maps directly to our pipeline (LLM agents -> game specification JSON -> React game templates)

### 3.4 Code World Models for General Game Playing

- **Title:** "Code World Models for General Game Playing"
- **Authors:** Wolfgang Lehrach, Daniel Hennes, et al. (Google DeepMind)
- **Year:** 2025
- **URL:** [arXiv:2510.04542](https://arxiv.org/abs/2510.04542)
- **What they generate:** Executable Python world models (transition functions, legal actions, observations, reward functions) from natural language game rules
- **Formalism:** Python code following the OpenSpiel API format
- **Models tested:** Gemini 2.5 Pro as both generator and baseline
- **Reliability metrics:** Matched or outperformed Gemini 2.5 Pro in 9/10 games; 4-7 orders of magnitude faster execution than direct LLM invocation
- **Correctness approach:** **Iterative refinement with auto-generated unit tests** -- unit tests are automatically generated from offline game trajectories, checking CWM predictions against trajectory data. Failed tests trigger regeneration
- **Key insight:** Separating "understanding rules" (LLM strength) from "executing rules" (code strength) via code synthesis creates verifiable, fast, and reliable game engines. The iterative unit-test loop is critical for convergence
- **Multi-scene support:** Supports multiple game types but not multi-scene within a game
- **Relevance:** The auto-generated unit test approach from gameplay traces is directly applicable to GamED.AI's validation pipeline

### 3.5 Cardiverse: Card Game Prototyping

- **Title:** "Cardiverse: Harnessing LLMs for Novel Card Game Prototyping"
- **Authors:** Danrui Li, Sen Zhang, Samuel S. Sohn, et al.
- **Venue:** EMNLP 2025
- **URL:** [ACL Anthology](https://aclanthology.org/2025.emnlp-main.1511/)
- **GitHub:** [github.com/danruili/Cardiverse](https://github.com/danruili/Cardiverse)
- **What they generate:** Novel card game implementations from mechanic descriptions
- **Formalism:** Structured markdown descriptions of game states, deck initialization, legal actions, and gameplay process, translated to executable code
- **Correctness approach:** **Gameplay record validation** -- sampled gameplay records are evaluated against structured game descriptions to identify rule violations, which are used to iteratively refine generated code
- **Key insight:** Graph-based mechanics indexing enables generating novel mechanic _combinations_ (not just single mechanics), directly relevant to GamED.AI's multi-mechanic needs. Supports 22 card games across 4 categories (Rummy, Casino, Trick-Taking, Other)
- **Multi-mechanic support:** Yes -- novel game mechanics are generated by combining/modifying existing mechanics via graph traversal
- **Relevance:** **Very high** -- demonstrates the feasibility of multi-mechanic game generation with validation, and the graph-based mechanics indexing pattern could model GamED.AI's 10 mechanic types and their combinations

### 3.6 Instruction-Driven Game Engine (IDGE)

- **Title:** "Instruction-Driven Game Engines on Large Language Models" / "Instruction-Driven Game Engine: A Poker Case Study"
- **Authors:** Various (see arXiv)
- **Venue:** arXiv 2024 / EMNLP 2024 Demo
- **URLs:** [arXiv:2404.00276](https://arxiv.org/abs/2404.00276), [arXiv:2410.13441](https://arxiv.org/abs/2410.13441)
- **What they generate:** The LLM _is_ the game engine, autoregressively predicting next game states from rules + current state + player action
- **Formalism:** Next State Prediction task; game scripts in natural language
- **Models tested:** CodeLLaMA, LLaMA2 (fine-tuned with LoRA)
- **Correctness approach:** Curriculum training with Segment Rephrasing (SR) technique for robustness
- **Key insight:** Fine-tuning enables LLMs to serve as game engines for specific game types (poker), but this approach requires training data per game type and struggles with precision of state computation
- **Multi-scene support:** No (single game type)
- **Relevance:** Low for GamED.AI's use case (we want to _generate specifications_, not use LLMs as runtime engines), but the training methodology informs fine-tuning strategies

### 3.7 Game Knowledge Management System (G-KMS)

- **Title:** "Game Knowledge Management System: Schema-Governed LLM Pipeline for Executable Narrative Generation in RPGs"
- **Venue:** MDPI Systems 2025
- **URL:** [MDPI](https://www.mdpi.com/2079-8954/14/2/175)
- **What they generate:** Engine-executable narrative knowledge artifacts for 2D Unity RPGs
- **Formalism:** Schema-governed structured pipeline with five stages: knowledge grounding, schema-governed generation, normalization-based repair, engine-aligned admission, and application
- **Correctness approach:** Multi-stage validation with explicit schema governance and normalization repair
- **Key insight:** Reformulating LLM generation as a "knowledge management process" rather than "text generation" dramatically improves reliability. The normalization-based repair stage catches and fixes schema violations before engine admission
- **Relevance:** **Very high** -- the five-stage pipeline pattern (ground -> generate -> normalize/repair -> validate -> execute) maps well to GamED.AI's agent pipeline architecture

### 3.8 Narrative-to-Scene Generation

- **Title:** "Narrative-to-Scene Generation: An LLM-Driven Pipeline for 2D Game Environments"
- **Year:** 2025
- **URL:** [arXiv:2509.04481](https://arxiv.org/abs/2509.04481)
- **What they generate:** Sequences of visual game scenes from narrative text
- **Structure:** Stories segmented into three temporal frames (beginning, middle, end) following Freytag's pyramid
- **Relevance:** Demonstrates multi-scene decomposition from narrative, similar to GamED.AI's `scene_breakdown` approach

### 3.9 Level Generation Through Large Language Models

- **Title:** "Level Generation Through Large Language Models"
- **Authors:** Graham Todd, Sam Earle, et al.
- **Venue:** FDG 2023
- **URL:** [arXiv:2302.05817](https://arxiv.org/abs/2302.05817)
- **GitHub:** [github.com/gdrtodd/lm-pcg](https://github.com/gdrtodd/lm-pcg)
- **What they generate:** Sokoban game levels
- **Key insight:** LLM performance scales dramatically with training dataset size for level generation. Early work that established LLMs as viable PCG tools
- **Relevance:** Foundational work, but focused on level layout rather than game rules/mechanics

---

## 4. Techniques for Reliable Structured Generation

### 4.1 Constrained Decoding / Grammar-Guided Generation

**What it is:** Modifying the LLM's token sampling process at inference time to only allow tokens that keep the output on a valid path according to a formal grammar (CFG, JSON Schema, regex).

**Key implementations:**
| Tool | Approach | Performance | URL |
|------|----------|-------------|-----|
| OpenAI Structured Outputs | Constrained sampling against JSON Schema | **100% schema compliance** on evals | [OpenAI Blog](https://openai.com/index/introducing-structured-outputs-in-the-api/) |
| Anthropic Structured Outputs | Constrained decoding for Claude (beta) | 100% schema compliance | [Claude Docs](https://platform.claude.com/docs/en/build-with-claude/structured-outputs) |
| XGrammar | Pushdown automaton (PDA) for CFG; context-independent pre-checks | Up to 100x speedup over alternatives | [arXiv:2411.15100](https://arxiv.org/abs/2411.15100), [GitHub](https://github.com/mlc-ai/xgrammar) |
| Outlines | FSM-based guided generation for any schema | Works with any model (OpenAI, Ollama, vLLM) | [GitHub](https://github.com/dottxt-ai/outlines) |
| JSONFormer | Schema-guided token delegation | Bulletproof structural validity | [GitHub](https://github.com/1rgs/jsonformer) |
| llguidance (Guidance) | Grammar-constrained generation | Super-fast structured outputs | [GitHub](https://github.com/guidance-ai/llguidance) |

**Key findings:**
- OpenAI's Structured Outputs achieves **100% reliability** in JSON schema conformance evaluations for gpt-4o-2024-08-06 and later
- Anthropic's Structured Outputs (public beta) guarantees JSON schema compliance for Claude Sonnet 4.5 and Opus 4.1 using constrained decoding at inference time
- XGrammar achieves up to 100x speedup through persistent parsing stacks and context-independent pre-checks
- Constrained decoding guarantees **structural** validity but NOT **semantic** correctness (a valid JSON can still contain wrong game logic)

**Relevance to GamED.AI:** Use OpenAI/Anthropic Structured Outputs or Pydantic-based validation (already in use) to guarantee schema compliance. The remaining challenge is semantic correctness.

### 4.2 Schema-Constrained Structured Output (Pydantic / Instructor)

**What it is:** Defining output schemas as Pydantic models and using libraries like Instructor to automatically handle validation, retries, and error recovery.

**Key tools:**
- **Pydantic AI:** Native output schema support for LLM responses -- [Pydantic AI Docs](https://ai.pydantic.dev/output/)
- **Instructor:** Multi-language library for structured LLM outputs with automatic validation and retries -- [python.useinstructor.com](https://python.useinstructor.com/)
- **LangChain Structured Output:** Integration with Pydantic for structured outputs -- [LangChain Docs](https://docs.langchain.com/oss/python/langchain/structured-output)

**Key findings:**
- Provider-native structured output (OpenAI/Anthropic JSON Schema mode) provides highest reliability
- Instructor adds automatic retry on validation failure, which is critical for complex nested schemas
- Pydantic supports nested models, lists, enums, and discriminated unions -- all needed for game spec schemas

**Relevance to GamED.AI:** GamED.AI already uses Pydantic schemas extensively. The recommendation is to adopt Instructor-style automatic retry loops and migrate to provider-native Structured Outputs where available.

### 4.3 Iterative Refinement with Validation Loops

**What it is:** Generate-validate-refine cycles where LLM output is tested against validators, and failures are fed back for correction.

**Key patterns from research:**
| Pattern | Source | Description |
|---------|--------|-------------|
| Unit test from traces | Code World Models (2025) | Auto-generate unit tests from gameplay trajectories; failed tests trigger regeneration |
| Gameplay record validation | Cardiverse (EMNLP 2025) | Sample gameplay, compare against rules, identify violations, refine code |
| Self-Refine | Wei et al. (2023) | LLM evaluates own output, identifies issues, revises |
| LLMLOOP | Ravi et al. (ICSME 2025) | Iterative loop: generate -> validate -> fix, with external tool feedback |
| Multi-agent roles | MapCoder (2024) | Analyst, designer, developer, tester agents collaborate iteratively |
| Schema normalization-repair | G-KMS (2025) | Normalization stage catches and repairs schema violations before engine admission |

**Key findings:**
- Single-pass generation is insufficient for complex game specifications (55% success at best for Boardwalk)
- Iterative refinement with automated test generation converges to high reliability
- Multi-agent approaches (analyst + generator + validator) outperform single-agent approaches

**Relevance to GamED.AI:** The pipeline already has validator agents (PlayabilityValidator, BlueprintValidator). The recommendation is to add gameplay simulation-based validation: generate a game spec, simulate player interactions programmatically, verify expected outcomes match.

### 4.4 DSL as Intermediate Layer

**What it is:** Instead of having LLMs generate raw code or prose, generate a constrained, domain-specific structured format that acts as a safe intermediary.

**Key findings from Real-Time World Crafting (2025):**
- DSL provides safety (no arbitrary code execution) and verifiability
- DSL can be validated against a schema before execution
- LLM role is strictly limited to generating structured data matching DSL schema
- Few-shot examples are critical for complex DSL generation

**Key findings from DSL-Xpert (MODELS 2024):**
- Grammar prompting (providing DSL grammar in context) combined with few-shot examples enables reliable DSL code generation
- Since many DSLs are not Turing Complete, formal verification is more tractable

**Relevance to GamED.AI:** Define a formal Game Specification DSL that is:
1. Expressive enough to cover all 10 mechanic types
2. Simple enough for reliable LLM generation
3. Validatable against a JSON Schema
4. Directly executable by React game templates

### 4.5 Fine-Tuning on Game Specifications

**What it is:** Training or fine-tuning LLMs on domain-specific game specification data.

**Key findings:**
- IDGE (2024) fine-tuned CodeLLaMA/LLaMA2 with LoRA for poker game engine tasks
- Curriculum training (progressively increasing complexity) improved robustness
- MarioGPT fine-tuned GPT-2 specifically for Super Mario Bros level generation
- Synthetic data generation from existing LLMs can create training datasets efficiently

**Limitations:**
- Requires significant labeled data in the target specification format
- Fine-tuned models may lose generalization
- Not practical for 10 different mechanic types without substantial data per type

**Relevance to GamED.AI:** Fine-tuning is likely premature. Focus on few-shot prompting with examples from each mechanic type first. Consider fine-tuning only after collecting sufficient gameplay data from production use.

### 4.6 Chain-of-Thought and Advanced Prompting

**Key findings:**
- CoT significantly improves complex rule generation by decomposing into intermediate steps
- Tree of Thoughts (ToT) enables systematic exploration of alternative rule formulations
- Real-Time World Crafting found CoT improved creative alignment but few-shot examples were more important for complex DSL scripts
- Few-shot prompting effectiveness varies with example ordering, wording, and style

**Relevance to GamED.AI:** Use a two-phase generation approach:
1. CoT phase: LLM reasons about mechanics, constraints, and educational objectives
2. Structured generation phase: LLM produces the formal specification

---

## 5. Multi-Scene and Multi-Mechanic Challenges

This is the area with the **least existing research** and where GamED.AI has the most opportunity for innovation.

### 5.1 State of the Art

**No existing system handles 10+ mechanic types with multi-scene transitions.** The closest are:
- **Cardiverse:** Handles multi-mechanic card games via graph-based mechanics indexing (4 categories, 22 games)
- **Narrative-to-Scene Generation:** Decomposes stories into 3 temporal frames (beginning/middle/end) but without mechanic variation
- **G-KMS:** Multi-stage pipeline for RPG narratives but single-mechanic-type

### 5.2 Key Challenges Identified in Literature

| Challenge | Description | Proposed Solutions |
|-----------|-------------|-------------------|
| Cross-scene state consistency | Game state must persist correctly between scenes with different mechanics | Shared state schema with typed fields; scene transition validators |
| Mechanic transition logic | How does game flow when mechanic changes between scenes? | State machine for scene flow; explicit transition rules in specification |
| Difficulty progression | Difficulty must increase across scenes in a pedagogically sound way | Formal difficulty parameters per scene; constraint propagation |
| Scene dependency graphs | Later scenes may depend on outcomes of earlier scenes | DAG of scene dependencies in specification; conditional branching rules |
| Shared entity references | Objects/concepts must maintain identity across scenes | Global entity registry in specification; reference-by-ID |

### 5.3 Recommended Architecture Pattern

Based on the research, a hierarchical specification structure:

```
GameSpecification
  |-- metadata (title, subject, learning_objectives)
  |-- global_state (entities, scores, difficulty_params)
  |-- scenes[] (ordered)
       |-- scene_metadata (mechanic_type, difficulty_level)
       |-- scene_state (local entities, scene-specific params)
       |-- rules[] (conditions, actions, scoring)
       |-- transitions (entry_conditions, exit_conditions, state_transforms)
  |-- scene_flow (DAG of scene transitions, branching conditions)
  |-- pedagogical_constraints (learning_objective_alignment, misconception_targets)
```

### 5.4 StateFlow Pattern for Scene Management

From the StateFlow paper ([arXiv:2403.11322](https://arxiv.org/html/2403.11322v1)):
- Model complex task-solving as state machines
- States represent scene phases; transitions represent mechanic switches
- Provides clear tracking and management of LLM responses
- Applicable to GamED.AI's scene progression

---

## 6. Educational Game Specific Considerations

### 6.1 Pedagogical Constraint Encoding

**Research findings:**
- Bloom's Taxonomy alignment can be encoded as metadata in game specifications (difficulty level mapping to cognitive levels: Remember -> Understand -> Apply -> Analyze -> Evaluate -> Create)
- Automated question generation studies show that 8-shot prompting improves Bloom's alignment significantly
- Backward design (start from learning objectives, then design assessments, then activities) should inform specification structure

**For GamED.AI:** Each rule in the game specification should carry a `pedagogical_purpose` field:
```json
{
  "rule_id": "r1",
  "condition": {"type": "drag_drop", "item": "mitochondria", "target": "cell_diagram_zone_3"},
  "outcome": {"correct": true, "score": 10},
  "pedagogical_purpose": {
    "learning_objective": "Identify organelles in a cell",
    "bloom_level": "remember",
    "misconception_addressed": "confusing_mitochondria_with_chloroplast"
  }
}
```

### 6.2 Misconception Modeling

**Research findings:**
- Two-tier testing (first tier: answer; second tier: reasoning) effectively detects misconceptions in game-based learning
- Game-based stealth assessment can track misconceptions without disrupting gameplay
- Feedback differentiated by misconception type improves learning outcomes

**For GamED.AI:** The game specification should include:
- A `misconceptions` registry mapping common errors to specific misconceptions
- Feedback rules triggered by specific wrong answers (not just "incorrect")
- Adaptive paths that provide targeted remediation for detected misconceptions

### 6.3 Adaptive Difficulty in Declarative Specs

**Research findings from PCG for educational games:**
- Genetic algorithms combined with difficulty measures can generate games targeting specific difficulty levels
- LLMs can communicate rules in different ways to adjust perceived difficulty
- Difficulty parameters should be explicit and tunable, not implicit in game content

**For GamED.AI:** Difficulty should be a first-class parameter in the specification:
```json
{
  "difficulty": {
    "level": 2,
    "parameters": {
      "num_distractors": 4,
      "time_limit_seconds": 60,
      "hint_available": true,
      "partial_credit": false
    }
  }
}
```

### 6.4 Learning Objective Alignment Verification

**Research findings:**
- Quality Matters rubric and backward design frameworks provide verification criteria
- MIRT (multidimensional item response theory) models can verify alignment at scale
- LLMs can assess alignment between objectives and assessment items (though imperfectly)

**For GamED.AI:** Add a verification step in the pipeline:
1. Extract learning objectives from input question
2. For each game rule, verify it tests the stated objective
3. Check coverage: are all objectives addressed by at least one rule?
4. Check specificity: does each rule test exactly one objective?

---

## 7. Industry Case Studies

### 7.1 Brilliant.org -- AI Learning Game Generation

- **URL:** [Blog post](https://blog.brilliant.org/hand-crafted-machine-made/)
- **Follow-up:** [Evals for AI learning games](https://blog.brilliant.org/when-almost-right-is-catastrophically-wrong-evals-for-ai-learning-games/)
- **What they do:** Use AI to generate interactive puzzle content (e.g., gear train puzzles)
- **Architecture:** Human learning designer defines puzzle type and constraints -> AI generates puzzle instances -> automated evaluation framework filters -> human review
- **Reliability:** Improved from 0% to 93% success rate for gear train puzzles in 48 hours of iteration; overall 80-90% across dimensions for foundational problems
- **Key principle:** "The human remains the creative director" -- AI handles technical implementation, humans handle learning objectives and progression
- **Evaluation:** Multi-dimensional evaluation framework that filters puzzles before human review; every generated problem goes through multiple rounds of human review
- **Lesson for GamED.AI:** The hybrid approach (AI generates + automated eval filters + human reviews) is the most practical production architecture. "Almost right" is catastrophically wrong in educational contexts.

### 7.2 One Trillion and One Nights (Dream JRPG)

- **URL:** [Medium article](https://awjuliani.medium.com/one-trillion-and-one-nights-e215d82f53e2)
- **GitHub:** [github.com/awjuliani/dream-jrpg](https://github.com/awjuliani/dream-jrpg)
- **What it does:** Browser-based JRPG procedurally generated by LLMs from player seed questions
- **Architecture:** Player answers seed questions -> LLM generates game world, characters, story via hand-crafted prompt chain -> browser game renders output
- **Relevance:** Demonstrates prompt chaining for multi-component game generation in a browser context

---

## 8. Open-Source Tools and Frameworks

### 8.1 Constrained Generation Tools

| Tool | Stars | Description | URL |
|------|-------|-------------|-----|
| Outlines | 10k+ | Structured generation for any LLM via FSM | [github.com/dottxt-ai/outlines](https://github.com/dottxt-ai/outlines) |
| XGrammar | 1k+ | Fast CFG-based constrained generation | [github.com/mlc-ai/xgrammar](https://github.com/mlc-ai/xgrammar) |
| JSONFormer | 4k+ | Schema-guided JSON generation | [github.com/1rgs/jsonformer](https://github.com/1rgs/jsonformer) |
| Instructor | 9k+ | Pydantic-based structured output with retries | [python.useinstructor.com](https://python.useinstructor.com/) |
| llguidance | 1k+ | Grammar-constrained generation by Guidance AI | [github.com/guidance-ai/llguidance](https://github.com/guidance-ai/llguidance) |

### 8.2 Game Generation Frameworks

| Project | Description | URL |
|---------|-------------|-----|
| Boardwalk | Board game API for LLM generation | [github.com/LabCRAIG/boardwalk](https://github.com/LabCRAIG/boardwalk) |
| Cardiverse | Card game prototyping with LLMs | [github.com/danruili/Cardiverse](https://github.com/danruili/Cardiverse) |
| Dream JRPG | LLM-generated browser RPGs | [github.com/awjuliani/dream-jrpg](https://github.com/awjuliani/dream-jrpg) |
| lm-pcg | LLM-based level generation | [github.com/gdrtodd/lm-pcg](https://github.com/gdrtodd/lm-pcg) |
| Stately Agent | XState-powered LLM agents | [github.com/statelyai/agent](https://github.com/statelyai/agent) |

### 8.3 Rules Engines

| Engine | Description | URL |
|--------|-------------|-----|
| json-rules-engine | Declarative JSON rules engine (JS) | [github.com/CacheControl/json-rules-engine](https://github.com/CacheControl/json-rules-engine) |
| Microsoft RulesEngine | JSON-based rules engine (.NET) | [microsoft.github.io/RulesEngine](https://microsoft.github.io/RulesEngine/) |

### 8.4 Surveys and Reference Lists

| Resource | Description | URL |
|----------|-------------|-----|
| GPT for Games: Scoping Review (2020-2024) | 131 papers surveyed | [arXiv:2411.00308](https://arxiv.org/abs/2411.00308) |
| LLMs and Games: Survey and Roadmap | IEEE Trans. on Games 2024 | [arXiv:2402.18659](https://arxiv.org/abs/2402.18659) |
| PCG Survey with LLM Integration | AIIDE 2024 | [arXiv:2410.15644](https://arxiv.org/abs/2410.15644) |
| Awesome LLM Constrained Decoding | Curated paper list | [github.com/Saibo-creator/Awesome-LLM-Constrained-Decoding](https://github.com/Saibo-creator/Awesome-LLM-Constrained-Decoding) |
| AI Game Dev Tools | Comprehensive tool list | [github.com/Yuan-ManX/ai-game-devtools](https://github.com/Yuan-ManX/ai-game-devtools) |

---

## 9. Key Takeaways for GamED.AI

### Recommendation 1: Define a Formal Game Specification DSL

Design a JSON-based Game Specification DSL that covers all 10 mechanic types. Based on the research, the specification should have these layers:

```
GameSpecification (top level)
  |-- metadata: title, subject, grade_level, learning_objectives[]
  |-- global_entities: shared objects/concepts across scenes
  |-- difficulty_config: base difficulty, progression curve
  |-- scenes[]: ordered array
  |    |-- id, mechanic_type (enum of 10 types)
  |    |-- entities[]: scene-specific items with typed properties
  |    |-- rules[]: declarative condition-action pairs (json-rules-engine format)
  |    |    |-- conditions: {fact, operator, value} trees (ALL/ANY nesting)
  |    |    |-- event: what happens when conditions met
  |    |    |-- scoring: points, feedback, pedagogical_tag
  |    |-- layout: spatial/visual arrangement specification
  |    |-- difficulty: scene-specific difficulty parameters
  |    |-- transitions: entry/exit conditions, state transforms
  |-- scene_flow: DAG defining valid scene transitions
  |-- pedagogical_metadata: bloom_levels, misconception_targets, alignment_map
```

The DSL should be:
- **Typed**: Every field has a strict type (use Pydantic models)
- **Mechanic-agnostic at the top level**: Mechanic-specific fields live in scene-level schemas
- **Executable**: React templates consume the specification directly without interpretation
- **Validatable**: Both structurally (JSON Schema) and semantically (game simulation)

### Recommendation 2: Adopt the Three-Layer Architecture

Following Real-Time World Crafting and G-KMS:

```
Layer 1: LLM Agent Pipeline (existing)
  - Input: natural language question
  - Output: Game Specification DSL (structured JSON)
  - Technique: Pydantic schemas + provider Structured Outputs (100% schema compliance)

Layer 2: Specification Validator (new)
  - Structural validation: JSON Schema compliance (guaranteed by Layer 1)
  - Semantic validation: rule consistency, completeness, playability
  - Pedagogical validation: learning objective alignment, misconception coverage
  - Simulation-based validation: programmatic gameplay to verify expected outcomes

Layer 3: Game Engine / React Templates (existing)
  - Input: validated Game Specification DSL
  - Output: playable interactive game
  - Deterministic execution of declarative rules
```

### Recommendation 3: Implement Gameplay Simulation Validation

Following Code World Models and Cardiverse:

1. For each generated game specification, automatically generate test scenarios (e.g., "if player drags mitochondria to zone_3, score should increase by 10")
2. Run these scenarios against the specification declaratively (no UI needed)
3. Verify: all correct answers are reachable, all incorrect answers produce appropriate feedback, the game is completable, difficulty parameters are within bounds
4. Feed failures back to the generation agent for refinement

### Recommendation 4: Use Provider-Native Structured Outputs

- For OpenAI models: Use `response_format: {type: "json_schema", json_schema: {...}}` for 100% schema compliance
- For Anthropic Claude: Use structured outputs beta with Pydantic schema definitions
- For local models: Use XGrammar or Outlines for grammar-constrained decoding
- Continue using Pydantic models as the source of truth for schemas (already in place)

### Recommendation 5: Two-Phase Generation with CoT

Based on findings from multiple papers:

**Phase 1 -- Planning (CoT):**
```
Given the question about [topic], plan the game:
1. Identify key concepts to assess
2. Map concepts to mechanic types
3. Design scene progression and difficulty curve
4. Identify potential misconceptions to target
5. Define success criteria per scene
```

**Phase 2 -- Specification (Structured Output):**
```
Based on the plan above, generate the formal game specification
conforming to the GameSpecification schema.
```

This separation ensures the LLM reasons before committing to structured output, improving semantic correctness.

### Recommendation 6: Graph-Based Mechanic Composition

Following Cardiverse's approach:

- Build a graph of mechanic types where nodes are mechanics and edges represent compatibility/combination patterns
- Use this graph to validate that multi-scene mechanic combinations are coherent
- Enable discovery of novel mechanic combinations for richer games
- Encode constraints (e.g., "memory_match should precede sorting_categories for scaffolding")

### Recommendation 7: Adopt json-rules-engine Format for Rules

The [json-rules-engine](https://github.com/CacheControl/json-rules-engine) format provides a well-tested, declarative rule specification:

```json
{
  "conditions": {
    "all": [
      {"fact": "item_placement", "operator": "equal", "value": {"item": "mitochondria", "zone": "zone_3"}},
      {"fact": "time_remaining", "operator": "greaterThan", "value": 0}
    ]
  },
  "event": {
    "type": "correct_placement",
    "params": {"score": 10, "feedback": "Correct! The mitochondria is the powerhouse of the cell."}
  }
}
```

Benefits:
- Executable in both Node.js (frontend) and Python (backend validation)
- Declarative and human-readable
- Composable (rules can reference other rules)
- Well-documented with existing npm package (5k+ GitHub stars)

### Recommendation 8: Start with High-Value Mechanic Types

Based on reliability data from the literature:

| Priority | Mechanic | Complexity | Expected LLM Reliability |
|----------|----------|-----------|-------------------------|
| 1 | drag_drop | Low | High (well-defined conditions) |
| 2 | click_to_identify | Low | High |
| 3 | sorting_categories | Medium | High (clear rules) |
| 4 | sequencing | Medium | Medium-High |
| 5 | description_matching | Medium | Medium |
| 6 | memory_match | Medium | Medium |
| 7 | trace_path | High | Medium (spatial reasoning) |
| 8 | compare_contrast | High | Medium (complex conditions) |
| 9 | branching_scenario | High | Lower (stateful, multi-path) |
| 10 | hierarchical | High | Lower (nested structures) |

Implement and validate the DSL for simpler mechanics first, building confidence in the schema before tackling complex mechanics.

### Recommendation 9: Do NOT Fine-Tune Yet

The research shows:
- Few-shot prompting with good examples outperforms fine-tuning for small-scale generation tasks
- Fine-tuning requires substantial training data per mechanic type (hundreds of examples minimum)
- Provider-native Structured Outputs + Pydantic validation + iterative refinement achieves high reliability without fine-tuning
- Consider fine-tuning only after collecting 100+ validated game specifications per mechanic type from production use

### Recommendation 10: Build an Evaluation Framework Early

Following Brilliant.org's approach:
- Define evaluation dimensions: structural validity, rule completeness, playability, pedagogical alignment, difficulty accuracy
- Automate evaluation for each dimension
- Track success rates per mechanic type and per LLM model
- Use evaluation failures to improve prompts and schemas iteratively
- Set a quality bar (e.g., 90% on all dimensions) before removing human review

---

## Appendix: Conference and Venue Reference

| Venue | Full Name | Relevance |
|-------|-----------|-----------|
| FDG | Foundations of Digital Games | Game generation, PCG, game AI |
| AIIDE | AAAI Conference on AI and Interactive Digital Entertainment | PCG with AI, game AI |
| CoG | IEEE Conference on Games | Game generation, VGDL research |
| CHI | ACM Conference on Human Factors in Computing Systems | Human-AI game design |
| EMNLP | Empirical Methods in NLP | NLP for game generation (Cardiverse) |
| NeurIPS | Neural Information Processing Systems | LLM techniques applicable to games |
| ICML | International Conference on Machine Learning | Constrained decoding (DOMINO) |
| AAAI | Association for Advancement of AI | Neuro-symbolic reasoning, game AI |

---

## Sources

### Academic Papers
- [Game Generation via Large Language Models (arXiv:2404.08706)](https://arxiv.org/abs/2404.08706) - Hu, Zhao, Liu, 2024
- [Boardwalk: Board Game Generation with LLMs (arXiv:2508.16447)](https://arxiv.org/abs/2508.16447) - Becker et al., 2025
- [Real-Time World Crafting (arXiv:2510.16952)](https://arxiv.org/abs/2510.16952) - Drake, Dong, 2025
- [Code World Models for General Game Playing (arXiv:2510.04542)](https://arxiv.org/abs/2510.04542) - Lehrach et al., 2025
- [Cardiverse: Card Game Prototyping (EMNLP 2025)](https://aclanthology.org/2025.emnlp-main.1511/) - Li et al., 2025
- [Instruction-Driven Game Engines (arXiv:2404.00276)](https://arxiv.org/abs/2404.00276) - 2024
- [IDGE Poker Case Study (arXiv:2410.13441)](https://arxiv.org/abs/2410.13441) - EMNLP 2024 Demo
- [G-KMS: Schema-Governed LLM Pipeline (MDPI)](https://www.mdpi.com/2079-8954/14/2/175) - 2025
- [Level Generation Through LLMs (FDG 2023)](https://arxiv.org/abs/2302.05817) - Todd et al., 2023
- [XGrammar (arXiv:2411.15100)](https://arxiv.org/abs/2411.15100) - CMU/NVIDIA, 2024
- [GPT for Games: Scoping Review (arXiv:2411.00308)](https://arxiv.org/abs/2411.00308) - 2024
- [LLMs and Games: Survey (arXiv:2402.18659)](https://arxiv.org/abs/2402.18659) - IEEE Trans. Games, 2024
- [PCG Survey with LLM Integration (AIIDE 2024)](https://arxiv.org/abs/2410.15644) - Farrokhi Maleki, Zhao, 2024
- [Narrative-to-Scene Generation (arXiv:2509.04481)](https://arxiv.org/abs/2509.04481) - 2025
- [StateFlow (arXiv:2403.11322)](https://arxiv.org/abs/2403.11322) - 2024
- [Enhancing FSM Design with LLMs (arXiv:2506.00001)](https://arxiv.org/abs/2506.00001) - 2025
- [Neuro-Symbolic Game AI (VeriPrajna)](https://veriprajna.com/technical-whitepapers/game-ai-neuro-symbolic-architecture)
- [LLMs are Neurosymbolic Reasoners (AAAI 2024)](https://arxiv.org/abs/2401.09334)
- [Supporting Serious Game Development with GenAI (MDPI)](https://www.mdpi.com/2076-3417/15/21/11606)
- [Procedurally Generating Rules for Adaptive Difficulty](https://arxiv.org/html/2307.05518)
- [LLM Agents for Education (EMNLP 2025 Findings)](https://aclanthology.org/2025.findings-emnlp.743.pdf)
- [Correctness-Guaranteed Code Generation via Constrained Decoding](https://arxiv.org/abs/2508.15866)
- [DSL-Xpert: LLM-driven Generic DSL Code Generation (MODELS 2024)](https://conf.researchr.org/details/models-2024/models-2024-tools-and-demonstrations/3/DSL-Xpert-LLM-driven-Generic-DSL-Code-Generation)

### Industry and Blog Posts
- [Brilliant.org: Hand-crafted, Machine-made](https://blog.brilliant.org/hand-crafted-machine-made/)
- [Brilliant.org: When "almost right" is catastrophically wrong](https://blog.brilliant.org/when-almost-right-is-catastrophically-wrong-evals-for-ai-learning-games/)
- [OpenAI: Introducing Structured Outputs](https://openai.com/index/introducing-structured-outputs-in-the-api/)
- [Anthropic: Structured Outputs for Claude](https://platform.claude.com/docs/en/build-with-claude/structured-outputs)
- [Constrained Decoding Guide (Brenndoerfer)](https://mbrenndoerfer.com/writing/constrained-decoding-structured-llm-output)
- [Constrained Decoding Guide (Cooper)](https://www.aidancooper.co.uk/constrained-decoding/)
- [Pydantic for LLMs Guide](https://pydantic.dev/articles/llm-intro)
- [vLLM Structured Decoding Introduction](https://blog.vllm.ai/2025/01/14/struct-decode-intro.html)

### GitHub Repositories
- [Boardwalk](https://github.com/LabCRAIG/boardwalk) - Board game generation framework
- [Cardiverse](https://github.com/danruili/Cardiverse) - Card game prototyping
- [Dream JRPG](https://github.com/awjuliani/dream-jrpg) - LLM-generated RPGs
- [lm-pcg](https://github.com/gdrtodd/lm-pcg) - LLM level generation
- [XGrammar](https://github.com/mlc-ai/xgrammar) - Fast structured generation
- [Outlines](https://github.com/dottxt-ai/outlines) - Structured outputs for any LLM
- [JSONFormer](https://github.com/1rgs/jsonformer) - Schema-guided JSON generation
- [Instructor](https://python.useinstructor.com/) - Pydantic-based LLM output validation
- [json-rules-engine](https://github.com/CacheControl/json-rules-engine) - Declarative JSON rules engine
- [Stately Agent](https://github.com/statelyai/agent) - XState-powered LLM agents
- [Awesome LLM Constrained Decoding](https://github.com/Saibo-creator/Awesome-LLM-Constrained-Decoding)
- [AI Game Dev Tools](https://github.com/Yuan-ManX/ai-game-devtools)
