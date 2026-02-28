# Backend Core Pipeline Hardcoded Values Audit

Audit Date: 2026-02-07
Scope: 6 core pipeline agents
Severity: HIGH = blocks game diversity, MED = limits flexibility, LOW = minor default

---

## 1. `game_planner.py`

- **[MED]** `game_planner.py:145` — Confidence formula `min(0.5 + (match_count * 0.15), 1.0)` hardcoded → Should be configurable base/increment/cap per mechanic
- **[HIGH]** `game_planner.py:153` — Default mechanic fallback always `DRAG_DROP` at 0.5 confidence → Should infer from template_type or pedagogical context
- **[HIGH]** `game_planner.py:174` — Hardcoded mitosis stage names `prophase|metaphase|anaphase|telophase` for scene count detection → Should be LLM-inferred, not biology-specific regex
- **[MED]** `game_planner.py:174` — Fallback scene count `4` when no stage patterns match → Should be dynamic based on content complexity
- **[MED]** `game_planner.py:178` — Compare questions always yield exactly 2 scenes → Should support 3+ way comparisons
- **[MED]** `game_planner.py:181` — "from...to" questions always yield exactly 3 scenes → Should be content-dependent
- **[MED]** `game_planner.py:183` — Generic multi-scene fallback always 2 scenes → Should be configurable
- **[LOW]** `game_planner.py:189` — Progression type always `"linear"` in all branches → Should support "branching", "cyclic", etc.
- **[MED]** `game_planner.py:230` — Asset query truncated to first 100 chars `question_text[:100]` → Should use intelligent extraction, not arbitrary truncation
- **[MED]** `game_planner.py:248` — Sequence config always `"linear"` → Should come from content analysis
- **[MED]** `game_planner.py:264` — Sorting category_count hardcoded to `2` → Should be inferred from question content
- **[LOW]** `game_planner.py:641` — Hierarchy threshold: `len(parent_children) >= 2 or len(all_children) >= 3` → Should be configurable
- **[LOW]** `game_planner.py:661` — Default reveal_trigger always `"complete_parent"` → Should vary by content type
- **[MED]** `game_planner.py:728` — Default template fallback always `"PARAMETER_PLAYGROUND"` → Should be context-aware
- **[HIGH]** `game_planner.py:1082-1089` — Fallback mechanic hardcoded to single `interact`/`click` with weight 1.0 → Should use template-specific defaults
- **[MED]** `game_planner.py:1099-1104` — Fallback feedback messages hardcoded: "Correct! Great job!" / "Not quite. Try again." → Should be topic-aware
- **[HIGH]** `game_planner.py:1138` — Scoring rubric defaults: `max_score=100`, `hint_penalty=0.1`, `time_bonus=False` → Should adapt to difficulty and template
- **[MED]** `game_planner.py:1144` — Default duration hardcoded to `10` minutes → Should scale with content complexity
- **[MED]** `game_planner.py:1161-1168` — Bloom's complexity map has fixed mechanic counts and durations (e.g., remember=1/5min, create=4/20min) → Should be configurable per subject
- **[HIGH]** `game_planner.py:1195` — Fallback max_attempts always `3` → Should vary by difficulty level
- **[MED]** `game_planner.py:1203-1228` — Fallback scoring rubric hardcoded: Correctness=0.7, Efficiency=0.3 with fixed levels → Should be template-specific
- **[MED]** `game_planner.py:1344` — Preset 2 max_attempts always `3` → Same as above
- **[MED]** `game_planner.py:1352-1377` — Preset 2 scoring rubric hardcoded: Accuracy=0.7, Completion=0.3 → Should adapt to game type
- **[LOW]** `game_planner.py:1356` — hint_penalty always `0.1` in Preset 2 → Should be configurable
- **[MED]** `game_planner.py:1378` — Duration formula `max(5, len(scenes) * 4)` → Arbitrary multiplier; should factor in mechanic complexity
- **[MED]** `game_planner.py:697` — Percentage trigger value hardcoded to `80` in auto-generated transitions → Should be configurable

## 2. `interaction_designer.py`

- **[LOW]** `interaction_designer.py:308` — Default zone_count fallback is `5` when no labels → Should be template-specific
- **[MED]** `interaction_designer.py:503-509` — Difficulty multiplier map hardcoded: beginner=0.5, easy=0.75, intermediate=1.0, advanced=1.5, expert=2.0 → Should be configurable
- **[LOW]** `interaction_designer.py:538` — Default animation on_correct always `"glow"` → Should vary by interaction mode
- **[LOW]** `interaction_designer.py:540` — Default animation on_incorrect always `"shake"` → Should vary by interaction mode
- **[LOW]** `interaction_designer.py:542` — Default animation on_reveal always `"fade"` → Should vary by content type
- **[LOW]** `interaction_designer.py:544` — Default animation on_complete always `"confetti"` → Should have alternatives like "fanfare", "summary"
- **[MED]** `interaction_designer.py:578` — Default hint_penalty always `20` (percentage) → Should vary by difficulty
- **[LOW]** `interaction_designer.py:585` — Default transition_trigger always `"scene_complete"` → Should be mechanic-dependent
- **[MED]** `interaction_designer.py:629` — Default transition trigger fallback `"all_zones_labeled"` → Should match interaction mode
- **[MED]** `interaction_designer.py:697` — Percentage-based transition trigger value hardcoded to `80` → Should scale with difficulty
- **[LOW]** `interaction_designer.py:691` — Transition animation always `"fade"` → Should vary by mode pair
- **[MED]** `interaction_designer.py:762-768` — Fallback base_points map hardcoded per difficulty: beginner=5, easy=8, intermediate=10, advanced=15, expert=20 → Should be configurable
- **[LOW]** `interaction_designer.py:788` — Fallback hint_progression always `["structural", "functional", "direct"]` → Should adapt to subject domain
- **[LOW]** `interaction_designer.py:804` — Fallback on_complete animation is `"bounce"` (differs from normalize's `"confetti"`) → Inconsistent defaults

## 3. `blueprint_generator.py`

- **[MED]** `blueprint_generator.py:1515-1516` — Fallback diagram dimensions `width=800, height=600` → Should be configurable or aspect-ratio aware
- **[HIGH]** `blueprint_generator.py:1749` — Default zone radius always `10` → Should adapt to diagram complexity and zone count
- **[MED]** `blueprint_generator.py:1473` — Default interactionMode fallback always `"drag_drop"` → Should use interaction_design or pedagogical context
- **[MED]** `blueprint_generator.py:1907-1908` — Default base_points_per_zone `10`, fallback maxScore `100` → Should be configurable
- **[HIGH]** `blueprint_generator.py:2119-2121` — PARAMETER_PLAYGROUND fallback slider: min=0, max=100, default=50 → Completely meaningless for actual parameters
- **[HIGH]** `blueprint_generator.py:2156-2159` — BUCKET_SORT fallback: only 2 buckets with generic "Category A"/"Category B" → Should derive from question content
- **[HIGH]** `blueprint_generator.py:2179-2182` — LABEL_DIAGRAM fallback: only 2 zones at fixed (30,30) and (70,50) with generic "Part 1"/"Part 2" → Useless for real diagrams
- **[MED]** `blueprint_generator.py:2354-2358` — Zone radius validation: warning range 5-15, error range 1-50 → Arbitrary bounds; should scale with zone count
- **[MED]** `blueprint_generator.py:2462-2466` — Minimum label count `6` for anatomy topics → Hardcoded threshold; should be question-dependent
- **[MED]** `blueprint_generator.py:2508` — Valid interaction modes limited to 4: `{"drag_drop", "click_to_identify", "trace_path", "hierarchical"}` → Blocks new mode types
- **[LOW]** `blueprint_generator.py:2487-2488` — Valid animation types and easings are fixed sets → Blocks custom animations
- **[MED]** `blueprint_generator.py:2631-2638` — Bloom's task count ranges hardcoded (e.g., remember: 1-3, create: 4-10) → Should be configurable
- **[MED]** `blueprint_generator.py:2714-2717` — Difficulty task complexity limits hardcoded: beginner max_steps=4, advanced max_steps=10 → Should be configurable
- **[LOW]** `blueprint_generator.py:1082-1087` — Default animation durations: quick=200ms, default=400ms, slow=600ms → Should be configurable
- **[LOW]** `blueprint_generator.py:1070-1079` — Animation colors hardcoded: green=#22c55e, red=#ef4444, blue=#3b82f6, yellow=#eab308 → Should be theme-configurable
- **[LOW]** `blueprint_generator.py:1115-1116` — Completion animation duration always 2000ms with intensity 1.5 → Should be configurable

## 4. `router.py`

- **[HIGH]** `blueprint_generator.py:502` / `router.py:517-522` — Unknown template falls back to `"PARAMETER_PLAYGROUND"` → Should use best-match or raise error
- **[MED]** `router.py:525` — Default confidence fallback `0.7` → Arbitrary; may mask poor routing
- **[MED]** `router.py:536-538` — Default alignment scores all `0.7` → Meaningless; should reflect actual analysis
- **[MED]** `router.py:557` — Fallback base confidence `0.5` → Arbitrary
- **[MED]** `router.py:565` — Keyword-matched fallback confidence `0.6` → Same confidence for very different match qualities
- **[LOW]** `router.py:432` — Forced template confidence `0.95` and scores all `0.9` → Arbitrary high scores for forced selection
- **[MED]** `router.py:673` — Human review threshold `confidence < 0.7` → Should be configurable per deployment
- **[HIGH]** `router.py:556` — Fallback default template is `"PARAMETER_PLAYGROUND"` regardless of question → Should at least use subject heuristics
- **[MED]** `router.py:596-602` — PhET keywords hardcoded: "projectile", "circuit", "pendulum", etc. → New simulations require code changes

## 5. `input_enhancer.py`

- **[MED]** `input_enhancer.py:26-33` — Bloom's levels list hardcoded → Should be loaded from config
- **[MED]** `input_enhancer.py:35-48` — Subjects list hardcoded to 12 items → New subjects require code changes
- **[MED]** `input_enhancer.py:311` — Invalid Bloom's level defaults to `"understand"` → Should use LLM confidence or raise
- **[MED]** `input_enhancer.py:315` — Difficulty levels limited to `["beginner", "intermediate", "advanced"]` → Missing "easy" and "expert" that interaction_designer supports
- **[LOW]** `input_enhancer.py:382` — Fallback Bloom's always `"understand"` when no keywords match → Should use probabilistic fallback
- **[LOW]** `input_enhancer.py:398` — Fallback subject `"General Science"` → Overly specific; should be "General"
- **[LOW]** `input_enhancer.py:405` — Fallback difficulty always `"intermediate"` → Should vary based on question length/complexity
- **[LOW]** `input_enhancer.py:411` — Fallback question_intent always `"General understanding"` → Uninformative

## 6. `domain_knowledge_retriever.py`

- **[MED]** `domain_knowledge_retriever.py:58-62` — Sequence detection keywords hardcoded list of 16 terms → New process types require code changes
- **[MED]** `domain_knowledge_retriever.py:80` — Comparison detection keywords hardcoded list of 6 terms → Limited set
- **[LOW]** `domain_knowledge_retriever.py:77` — Default sequence type `"linear"` when no cyclic/branching keywords match → Should use LLM inference
- **[MED]** `domain_knowledge_retriever.py:138` — Search results limited to top 5 → Should be configurable based on query complexity
- **[MED]** `domain_knowledge_retriever.py:227` — Fallback search query suffix `"list of parts"` when no pedagogical context → Too narrow for non-anatomy topics
- **[MED]** `domain_knowledge_retriever.py:234-251` — Bloom's-to-search-suffix mapping hardcoded (e.g., "remember" -> "list of parts labeled diagram") → Should be configurable per subject
- **[MED]** `domain_knowledge_retriever.py:254-263` — Subject-to-search-terms mapping hardcoded for 8 subjects → New subjects require code changes
- **[MED]** `domain_knowledge_retriever.py:384-394` — Label count guidance hardcoded in prompt: remember=4-8, analyze=10-15, evaluate/create=15+ → Should be configurable
- **[LOW]** `domain_knowledge_retriever.py:344` — Serper cost estimate hardcoded `$0.01` → Should be read from config
- **[MED]** `domain_knowledge_retriever.py:492-496` — Minimum label threshold `< 4` → Should vary by question type (some valid questions have 2-3 labels)

---

## Summary


| Severity  | Count  |
| --------- | ------ |
| HIGH      | 10     |
| MED       | 46     |
| LOW       | 22     |
| **Total** | **78** |


### Top 5 Systemic Issues

1. **Fallback templates default to PARAMETER_PLAYGROUND** (router.py, blueprint_generator.py) -- Every failed routing produces an irrelevant parameter playground game.
2. **Scoring rubrics are copy-pasted identical defaults** (game_planner.py x3) -- Accuracy=0.7/Completion=0.3 appears in three fallback paths; max_score=100, hint_penalty=0.1 are universal defaults regardless of template or difficulty.
3. **Multi-scene counts are pattern-matched to biology terms** (game_planner.py:174) -- Mitosis phase names are hardcoded, making multi-scene detection biology-specific rather than universal.
4. **Difficulty/Bloom's mappings duplicate across agents** -- game_planner, interaction_designer, blueprint_generator, and domain_knowledge_retriever each maintain independent hardcoded mappings for the same pedagogical concepts.
5. **Input validation levels are inconsistent** -- input_enhancer supports 3 difficulty levels (beginner/intermediate/advanced), while interaction_designer supports 5 (adding easy/expert), causing silent mismatches.

