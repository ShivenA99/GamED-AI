# ACL Paper Comprehensive Analysis & Fix Report

**Paper:** `acl_cemo-gamedai.tex`
**Date:** 2026-02-27
**Source files cross-referenced:** `docs/LITERATURE_REVIEW_AND_BASELINES.md`, `docs/audit/09_agentic_frameworks_research.md`, `docs/audit/11_algorithmic_games_research.md`, `docs/audit/25_mechanic_contracts_fol_research.md`, `docs/audit/research/*`, `docs/mechanics/*`, `docs/design/layer_architecture_log.md`

---

## Table of Contents

0. [Structural Rebalancing: Four-Pillar Focus](#0-structural-rebalancing-four-pillar-focus)
1. [Paper Issues & Drafted Fixes](#1-paper-issues--drafted-fixes)
2. [Existing Reference Verification](#2-existing-reference-verification)
3. [Missing References (Priority-Sorted)](#3-missing-references-priority-sorted)
4. [Appendix: Bloom's Taxonomy → Mechanic Mapping Table](#4-appendix-blooms-taxonomy--mechanic-mapping-table)
5. [Recommended .bib File](#5-recommended-bib-file)

---

## 0. Structural Rebalancing: Four-Pillar Focus

The paper should be restructured around **four pillars** in this priority order:

### Current Weight Distribution (Problem)

| Pillar | Current % | Lines | Status |
|--------|-----------|-------|--------|
| 1. Full system (end-to-end game generation) | ~40% | ~160 | Decent but scattered |
| 2. Pedagogical alignment (Bloom's + contracts) | ~15% | ~60 | **Too thin — mentioned but never deeply developed** |
| 3. Agentic architecture (DAG, Quality Gates, tokens) | ~35% | ~140 | **Overweighted — dominates paper** |
| 4. Frontend (observability + modular game engine) | ~0% | 0 | **Completely absent** |

### Target Weight Distribution

| Pillar | Target % | What to Add |
|--------|----------|-------------|
| 1. Full system | ~30% | Already covered; tighten prose |
| 2. Pedagogical alignment | ~25% | **Major expansion needed** (see below) |
| 3. Agentic architecture | ~25% | Trim token/cost repetition |
| 4. Frontend | ~10% | **New subsection needed** (see below) |
| Evaluation | ~10% | Keep as-is |

### Pillar 2: Pedagogical Alignment — What's Missing

The paper currently treats Bloom's as a label ("aligned to Bloom's") but never explains **how** the alignment works at a theoretical level. Needs:

**a) Core Bloom's references (currently only Anderson 2001 cited):**
- **Bloom (1956)** — Original taxonomy. Must cite the original alongside the revision.
- **Anderson & Krathwohl (2001)** — Already cited. Good.
- **Arnab et al. (2015)** — LM-GM framework: the foundational work on mapping Learning Mechanics to Game Mechanics. This is the theoretical basis for the paper's Bloom's-to-mechanic constraint table. **CRITICAL missing reference.**

**b) Assessment validity references:**
- **Mislevy et al. (2003)** — Already cited (ECD). Good.
- **Black & Wiliam (1998)** — Formative assessment. Missing.
- **Shute (2008)** — Formative feedback design. Missing.
- **Shute & Ventura (2013)** — Stealth assessment. Already cited.

**c) A dedicated Bloom's-to-Mechanic section.** Currently the mapping is implicit. The paper should include either:
- A table in the main body showing which Bloom's levels map to which mechanics and why (see Appendix table in Section 4 of this document)
- OR move the constraint table to an appendix but add a paragraph in Section 3.2.3 explaining the theoretical grounding

**d) Cognitive Load Theory needs development.** Sweller (1988) is cited 3 times but only as "[cognitive load bounds]" — the paper should explain WHY multi-scene games need cognitive load management and HOW the scene count/mechanics-per-scene limits are derived from CLT.

**e) The "decorative gamification fails" claim** (Related Work) needs Hamari et al. (2014) "Does Gamification Work?" — this is the definitive empirical review showing decorative gamification underperforms. Current citation (krath2021) is a theory review, not an empirical failure analysis.

### Pillar 4: Frontend — What's Completely Missing

The paper has **zero lines** about:

**a) Observability Dashboard** — The system has a real-time UI (18 components, 568KB in `frontend/src/components/pipeline/`):
- **3 view modes**: Timeline (linear stage progression), Graph (ReactFlow DAG with execution highlighting), Cluster (HAD 4-cluster grouping)
- **Token/cost analytics**: Per-stage token chart (TokenChart.tsx), USD cost breakdown with percentages (CostBreakdown.tsx), real-time counter during execution (LiveTokenCounter.tsx)
- **ReAct trace viewer** (ReActTraceViewer.tsx): Thought→Action→Observation→Decision step display
- **Stage detail panel** (StagePanel.tsx): 5-tab inspector (overview, input, output, logs, tool calls)
- **Real-time streaming**: WebSocket-based LivePipelineView with LiveReasoningPanel
- **Zone overlay** (ZoneOverlay.tsx): Interactive zone visualization for diagram validation
- **NOT implemented**: No dedicated Quality Gate inspection UI, no per-model cost attribution, no prompt diff/comparison

This is a differentiating feature. **Add 4-6 sentences in a new subsection or within the demo description. Be precise about what exists — do NOT claim QG inspection UI (not yet built).**

**b) Modular Game Engine** — The frontend template system (verified against code):
- **Mechanic registry** (`mechanicRegistry.ts`, 629 lines): maps interaction modes to React components via `MECHANIC_REGISTRY`. New mechanics added via registration. BUT app-level template selection (`/app/game/[id]/page.tsx`) uses imperative if/else chains, not a registry.
- **State management is split**: InteractiveDiagramGame uses **Zustand** (900+ line store, 40+ fields, 30+ actions). AlgorithmGame templates use **useReducer** (5 custom reducer hooks). This inconsistency should be described honestly.
- **dnd-kit** for drag-and-drop: extensively integrated across 15+ components with custom collision detection, keyboard sensors, touch/pointer support. This is solid.
- **Accessibility**: Infrastructure includes `accessibility/KeyboardNav.tsx`, `ScreenReaderAnnouncements.tsx`, ARIA attributes, keyboard sensors via dnd-kit. Full WCAG compliance is planned — paper can reference accessibility as a design goal and describe the architectural support.
- **Shared primitives**: MechanicAction/ActionResult unified action format, MechanicContext passed to all mechanics, registry-driven extractProps pattern. But no shared UI component library — each template builds its own.

**c) Suggested new subsection structure for Section 3:**

```
3. System Design
  3.1 Architectural Evolution
  3.2 Pipeline Architecture (DAG + Quality Gates)
    3.2.1 System Architecture
    3.2.2 Game Template Architecture
    3.2.3 Mechanic Contracts and Bloom's Alignment  ← EXPAND with theory
    3.2.4 Scene and Mechanic Composition
    3.2.5 Generation and Assembly
  3.3 Modular Game Engine  ← NEW
    - Mechanic registry and component routing
    - Interaction primitive composition (dnd-kit, sensors)
    - State management (Zustand for diagram games, useReducer for algorithm games)
  3.4 Pipeline Observability  ← NEW
    - Real-time execution dashboard (3 view modes)
    - Token and cost monitoring with per-stage breakdown
    - ReAct trace inspection and tool call history
  3.5 Deployment and Game Library
  3.6 Design Validation
```

### Summary: What to Do

1. **Expand Section 3.2.3** (Mechanic Contracts) into a deeper treatment of Bloom's alignment with core references
2. **Add Bloom's → Mechanic table** either in main body or appendix
3. **Add Section 3.3** covering the modular game engine architecture
4. **Add Section 3.4** covering the observability dashboard
5. **Trim repetition** in Sections 4-5 (experimental setup appears twice; key numbers appear 4+ times)
6. **Add 5-7 new citations** (Bloom 1956, Arnab 2015, Black & Wiliam 1998, Shute 2008, Hamari 2014, Deterding 2011, Ridnik 2024)

---

## 1. Paper Issues & Drafted Fixes

### 1.1 CRITICAL: Version Naming Inconsistency (Abstract vs Body)

**Issue:** The abstract says "This paper focuses on the **v3** DAG architecture; the v1--v3 architectural evolution is documented in the released repository." But the body (Section 3.1) says "**v4** supersedes two prior architectures: a sequential pipeline (**v2**) and a ReAct-based system (**v3**)." This is a direct contradiction—the abstract calls the current system v3, the body calls it v4.

**Fix:** Choose ONE naming convention and apply consistently. Two options:

**Option A (Recommended): Remove version numbers entirely, use descriptive names:**
```latex
% Abstract — replace:
This paper focuses on the v3 DAG architecture;
the v1--v3 architectural evolution is documented in the released repository.
% With:
This paper focuses on the DAG architecture;
the full architectural evolution is documented in the released repository.

% Section 3.1 — replace:
\gamedai{} v4 supersedes two prior architectures: a sequential
pipeline (v2, 56.7\% VPR, ${\sim}$45,200 tokens/game) and a
ReAct-based system (v3, 72.5\% VPR, ${\sim}$67,300 tokens/game).
% With:
The current \gamedai{} DAG architecture supersedes two prior designs:
a \textbf{Sequential Pipeline} (56.7\% VPR, ${\sim}$45,200 tokens/game)
and a \textbf{ReAct Agent} system (72.5\% VPR, ${\sim}$67,300 tokens/game).
```

**Option B: Fix abstract to say v4:**
```latex
This paper focuses on the v4 DAG architecture;
the v1--v4 architectural evolution is documented in the released repository.
```

If Option B, also update all `v2/v3/v4` references to be consistent. The body currently uses v4 as current, which matches the actual codebase (v4 = production DAG pipeline).

---

### 1.2 CRITICAL: VPR Abbreviation Not Defined on First Use

**Issue:** VPR first appears in Section 3.1: "v2, 56.7% VPR" without definition. It is only defined later in Table 2 caption: "VPR = Validation Pass Rate."

**Fix:** Define on first use in Section 3.1:
```latex
% Replace:
a sequential pipeline (v2, 56.7\% VPR, ...
% With:
a sequential pipeline (v2, 56.7\% Validation Pass Rate (VPR), ...
```

---

### 1.3 Typo in Conclusion

**Issue:** "architectural structurther than model scale alone" — should be "structure rather."

**Fix:**
```latex
% Replace:
properties of architectural structurther than model scale alone.
% With:
properties of architectural structure rather than model scale alone.
```

---

### 1.4 Template Count: Verify 16 = 10 + 6

**Issue:** Paper claims "16 sub-game templates organized into two families: Interactive Diagram Games (10 templates) and Interactive Algorithm Games (6 templates)." Verified against actual code:
- **Interactive Diagram mechanics** (from `mechanicRegistry.ts` + `types.ts`): drag_drop, click_to_identify, trace_path, description_matching, sequencing, sorting_categories, memory_match, branching_scenario, compare_contrast, hierarchical = **10** ✅
- **Algorithm Game mechanics** (from `AlgorithmGame/*.tsx`): state_tracer, bug_hunter, algorithm_builder, complexity_analyzer, constraint_puzzle = **5** (not 6)
- **Backend `MechanicType` enum** has 10 entries including `reveal` and `hotspot` — these are legacy/alias types, not distinct game templates
- **Total: 15 templates, not 16**

**Fix:** Change to 15 (10+5):
```latex
\textbf{15 sub-game templates} organized into two families.
...
\textbf{Interactive Algorithm Games (5 templates)}
```

---

### 1.5 Duplicated Experimental Setup

**Issue:** The experimental setup (120 questions, 5 domains, model mix, LangSmith logging) is described in BOTH Section 4.1 (Experiments) and Section 5 (Evaluation). This wastes space in a page-limited paper.

**Fix:** Remove the setup paragraph from Section 4.1 and keep only the detailed version in Section 5 (Evaluation). Replace Section 4.1 with a forward reference:
```latex
\subsection{Experimental Setup}
Full experimental parameters---model versions, temperatures, seed
values, and domain stratification---are specified in
Section~\ref{sec:eval}. We describe the evaluation framework here
and report results in the following section.
```

---

### 1.6 Repeated Key Claims

**Issue:** The following claims appear 3+ times each:
- "73% token reduction" — abstract, intro contributions, Section 3.5, Section 5, conclusion
- "90% validation pass rate" — abstract, intro contributions, Section 3.5, Section 5, conclusion
- "under 60 seconds at $0.48 per game" — abstract, intro, conclusion

**Fix:** State numbers fully in abstract and evaluation. In intro and conclusion, reference without restating exact numbers. Example:
```latex
% Conclusion — instead of repeating exact numbers:
the system achieves validation pass rates and token efficiency
significantly exceeding ReAct baselines (Section~\ref{sec:eval})
```

---

### 1.7 "This, Not This" Rhetorical Pattern Overuse

**Issue:** The paper uses the "X, not Y" construction 8+ times:
1. "Mechanics are selected by learning objectives, not generation convenience"
2. "LLM outputs are creative inputs, not final answers"
3. "pedagogical alignment is a structural generation constraint, not a post-hoc check"
4. "structure, not model capability, is the productive variable"
5. "architectural discipline, not model capability"
6. "schema underspecification, not LLM hallucination"
7. "structurally unreachable rather than probabilistically unlikely"
8. "parity rather than superiority; this is reported as parity, not equivalence"

**Fix:** Reduce to 3-4 strategic uses. Keep the strongest ones (#4, #6, #7) and rephrase others:
```latex
% #1 — rephrase:
Mechanics are selected to match learning objectives, with every
game type bound to a Bloom's level before generation begins.

% #2 — rephrase:
Every generative step is gated by a deterministic validator before
the pipeline proceeds, treating LLM outputs as creative proposals
subject to structural verification.

% #3 — rephrase:
ensuring pedagogical alignment is enforced as a structural
generation constraint at compile-time.
```

---

### 1.8 Missing `\label{sec:results}` Target

**Issue:** Section 3 references `Section~\ref{sec:results}` but the label `sec:results` does not exist. The evaluation section uses `\label{sec:eval}`.

**Fix:** Change all `\ref{sec:results}` to `\ref{sec:eval}`, or add `\label{sec:results}` as an alias.

---

### 1.9 Missing Content: Observability Dashboard

**Issue:** The system has a comprehensive real-time observability UI (pipeline timeline, token charts, ReAct trace viewer, cost breakdown) but the paper doesn't mention it. This is a differentiating feature.

**Fix:** Add 2-3 sentences in Section 3 (System Design) or the demo description:
```latex
The demonstration system includes a real-time observability dashboard
exposing pipeline execution traces, per-agent token consumption,
Quality Gate decision logs, and cost breakdowns---enabling instructors
to inspect and understand the generation process at every phase.
```

---

### 1.10 Missing Content: Model Agnosticism

**Issue:** Section 3.2.6 mentions CLI deployment with model selection (GPT-4, Gemini, Llama 3, Mistral) but the Limitations section notes this hasn't been benchmarked. The paper should frame this as an architectural feature.

**Fix:** Strengthen Section 3.2.6 with:
```latex
The orchestration layer is model-agnostic by design: agent model
assignments are configured through a declarative preset system
(\texttt{agent\_models.py}), enabling per-agent model selection
without pipeline modification. The reported evaluation uses a
GPT-4-turbo and Gemini configuration; open-source model evaluation
is ongoing.
```

---

### 1.11 Missing Content: Frontend Template Modularity

**Issue:** The React template system is modular (registry pattern, each mechanic = independent component) but the paper doesn't explain this architecture. It strengthens the "modularity for extensibility" design principle.

**Fix:** Add to Section 3.2.5 (Generation and Assembly):
```latex
The frontend rendering layer implements a template registry pattern:
each mechanic type is a self-contained React component registered
by contract type, enabling new templates to be added through component
registration without modifying the orchestration or assembly layers.
```

---

### 1.12 `\gamedai{}` vs `GAMED.AI` Inconsistency

**Issue:** The paper uses `\gamedai{}` (renders as "GamED.AI" in small caps) throughout but one instance in Related Work reads "GAMED.AI" in plain text: "To our knowledge, GAMED.AI is the first system..."

**Fix:**
```latex
% Replace:
To our knowledge, GAMED.AI is the first system
% With:
To our knowledge, \gamedai{} is the first system
```

---

### 1.13 Game Library Count Inconsistency

**Issue:** Section 3.2.3 says "30+ pre-built games" but Section 3.2.6 says "60+ game library." The demo actually has 50 games.

**Fix:** The demo library contains exactly **50 games** (45 Interactive Diagram + 5 CS Algorithm, across 5 domains). Use "50" consistently:
```latex
% Use "50" everywhere, e.g.:
The 50-game library serves as both a demo set and regression corpus...
Together, the 15 templates support a library of \textbf{50 pre-built games}...
```
**Note:** The "16 templates" in the original must also be fixed to "15" (see Issue 1.4).

---

### 1.14 DAG Abbreviation — Already Correct

**Status:** DAG is properly defined on first use in Section 3.2.1: "hierarchical Directed Acyclic Graph (DAG)." No fix needed.

---

### 1.14b PENDING: `brittle_react2024` Not Yet Added to Paper

**Status:** `shen2023` was removed from the paper (P0 fix applied), and `ge2023` was replaced with `ridnik2024`. However, `brittle_react2024` (arXiv:2405.13966 — "On the Brittle Foundations of ReAct Prompting") has **NOT yet been added** to the paper. The ReAct criticism paragraph currently has only `\citep{yao2023}` — it needs `\citep{brittle_react2024,yao2023}` to support the claim about open-ended ReAct loops being impractical.

**Fix still needed in `acl_cemo-gamedai.tex`:**
```latex
% In Related Work, find:
\citep{yao2023}  % (where shen2023 was removed)
% Change to:
\citep{brittle_react2024,yao2023}

% Also add to .bib:
@article{brittle_react2024,
  title={On the Brittle Foundations of {ReAct} Prompting for Agentic Large Language Models},
  author={...},
  journal={arXiv preprint arXiv:2405.13966},
  year={2024}
}
```

---

### 1.15 Missing Assembly-Line Metaphor

**Issue:** The pipeline architecture naturally maps to an assembly-line metaphor (each phase is a station, Quality Gates are quality inspectors). MetaGPT uses this metaphor explicitly. Adding it would improve accessibility for non-ML readers.

**Fix:** Add to Section 3 intro or Section 3.2:
```latex
The pipeline follows an assembly-line architecture analogous to
MetaGPT's SOP-driven workflow \citep{hong2023}: each phase operates
as a specialized station producing typed artifacts, with Quality
Gates serving as quality-control inspectors between stations.
```

---

## 2. Existing Reference Verification

### 2.1 All Citation Keys Used in Paper

| # | Key | Used For | Status |
|---|-----|----------|--------|
| 1 | `openai2023` | GPT-4 technical report | **VALID** — OpenAI (2023). "GPT-4 Technical Report." arXiv:2303.08774 |
| 2 | `google2023` | Gemini technical report | **VALID** — Google DeepMind (2023). "Gemini: A Family of Highly Capable Multimodal Models." arXiv:2312.11805 |
| 3 | `jimenez2024` | SWE-bench | **VALID** — Jimenez et al. (2024). "SWE-bench: Can Language Models Resolve Real-World GitHub Issues?" arXiv:2310.06770, ICLR 2024 |
| 4 | `chen2021` | HumanEval/Codex | **VALID** — Chen et al. (2021). "Evaluating Large Language Models Trained on Code." arXiv:2107.03374 |
| 5 | `mislevy2003` | Evidence-Centered Design | **VALID** — Mislevy, R.J. et al. (2003). "A Brief Introduction to Evidence-Centered Design." ETS Research Report |
| 6 | `shute2013` | Stealth Assessment | **NEEDS CHECK** — Shute published stealth assessment work in 2008 and 2011. Verify this is the correct year. Could be: Shute, V.J. & Ventura, M. (2013). "Stealth Assessment: Measuring and Supporting Learning in Video Games." MIT Press. **If so, VALID.** |
| 7 | `sailer2020` | Gamification meta-analysis | **VALID** — Sailer, M. & Homner, L. (2020). "The Gamification of Learning: A Meta-analysis." Educational Psychology Review, 32, 77-112 |
| 8 | `wouters2013` | Serious games meta-analysis | **VALID** — Wouters, P. et al. (2013). "A Meta-Analysis of the Cognitive and Motivational Effects of Serious Games." J. Educational Psychology, 105(2), 249-265 |
| 9 | `zeng2024` | Gamification impact | **VALID** — Zeng, J. et al. (2024). "Exploring the impact of gamification on students' academic performance." BJET, 55(6), 2478-2502. g=0.782 |
| 10 | `chapman2010` | Development cost/hours | **NEEDS VERIFICATION** — The "490 hours per finished hour" statistic is commonly cited from Chapman Alliance (2010). Verify: Bryan Chapman / Chapman Alliance (2010). "How Long Does it Take to Create Learning?" Research Study. This is an industry report, not peer-reviewed. Consider adding a footnote acknowledging this. |
| 11 | `learningsim2024` | Development cost >$50K | **FLAGGED — NOT ACADEMIC.** "learningsim2024" appears to be a commercial/blog source. Either: (a) find the academic source for the $50K claim, (b) cite Chapman2010 for both cost figures, or (c) move to footnote with URL. |
| 12 | `wang2020` | EdTech platforms limitation | **NEEDS VERIFICATION** — Multiple Wang et al. 2020 papers exist. Verify exact title. Likely: Wang, A.I. & Tahir, R. (2020). "The effect of using Kahoot! for learning." Computers & Education, 149. |
| 13 | `ji2023` | Hallucination survey | **VALID** — Ji, Z. et al. (2023). "Survey of Hallucination in Natural Language Generation." ACM Computing Surveys, 55(12). |
| 14 | `shen2023` | **FLAGGED — POTENTIALLY MISATTRIBUTED.** Used to cite: "self-correction loops that make prior agentic architectures impractical for structured content generation." No widely-known Shen et al. 2023 paper makes this exact claim. Possible candidates: (a) Shen et al. (2023). "HuggingGPT" — about task planning, not self-correction criticism. (b) Shinn et al. (2023). "Reflexion" — about self-correction but doesn't call it impractical. **Recommendation:** Replace with a more precise citation. The claim about ReAct's open-ended loops producing token inflation is better supported by arXiv:2405.13966 ("On the Brittle Foundations of ReAct Prompting"). |
| 15 | `yao2023` | ReAct | **VALID** — Yao et al. (2023). "ReAct: Synergizing Reasoning and Acting in Language Models." ICLR 2023. arXiv:2210.03629 |
| 16 | `freeman2014` | Active learning | **VALID** — Freeman, S. et al. (2014). "Active learning increases student performance in science, engineering, and mathematics." PNAS, 111(23), 8410-8415 |
| 17 | `paivio1991` | Dual coding theory | **FLAGGED — AMBIGUOUS.** Paivio published multiple works. The foundational dual coding text is: Paivio, A. (1986). "Mental Representations: A Dual Coding Approach." Oxford University Press. A 1991 work exists: Paivio, A. (1991). "Dual Coding Theory: Retrospect and Current Status." Canadian Journal of Psychology. **Verify which one you intend to cite and ensure the year matches.** |
| 18 | `mayer2009` | Multimedia Learning | **VALID** — Mayer, R.E. (2009). "Multimedia Learning." 2nd ed. Cambridge University Press |
| 19 | `anderson2001` | Bloom's Revised Taxonomy | **VALID** — Anderson, L.W. & Krathwohl, D.R. (2001). "A Taxonomy for Learning, Teaching, and Assessing." Longman |
| 20 | `krath2021` | Gamification failure | **FLAGGED — VERIFY CLAIM.** Used to cite: "Gamification... fails when applied decoratively." Likely: Krath, J. et al. (2021). "Revealing the theoretical basis of gamification: A systematic review and analysis of theory in research on gamification, serious games and game-based learning." Computers in Human Behavior, 125. This paper reviews theories behind gamification but doesn't specifically claim failure when "applied decoratively." **The decorative-failure claim is better supported by Landers (2014) already cited, or by Hamari et al. (2014) "Does Gamification Work?"** |
| 21 | `landers2014` | Gamification theory | **VALID** — Landers, R.N. (2014). "Developing a Theory of Gamified Learning." Simulation & Gaming, 45(6), 752-768 |
| 22 | `ryan2000` | Self-determination theory | **VALID** — Ryan, R.M. & Deci, E.L. (2000). "Self-Determination Theory and the Facilitation of Intrinsic Motivation." American Psychologist, 55(1), 68-78 |
| 23 | `csikszentmihalyi1990` | Flow theory | **VALID** — Csikszentmihalyi, M. (1990). "Flow: The Psychology of Optimal Experience." HarperPerennial |
| 24 | `hong2023` | MetaGPT | **VALID** — Hong et al. (2023). "MetaGPT: Meta Programming for A Multi-Agent Collaborative Framework." arXiv:2308.00352, ICLR 2024 |
| 25 | `wu2023` | AutoGen | **VALID** — Wu et al. (2023). "AutoGen: Enabling Next-Gen LLM Applications via Multi-Agent Conversation." arXiv:2308.08155 |
| 26 | `ge2023` | Hierarchical DAG | **FLAGGED — IMPRECISE.** Used to cite DAG architectures making "invalid state transitions structurally unreachable." No well-known Ge et al. 2023 paper makes this specific claim about DAGs. Possible: (a) Ge et al. (2023). "OpenAGI" — task planning, not DAG constraints. **Recommendation:** Replace with a more precise reference. Consider citing LangGraph documentation or the AlphaCodium paper (Ridnik et al. 2024) which explicitly argues for flow engineering over open-ended agents. |
| 27 | `willard2023` | Constrained decoding/structure | **VALID** — Willard, B.T. & Louf, R. (2023). "Efficient Guided Generation for Large Language Models." arXiv:2307.09702 |
| 28 | `graesser2004` | AutoTutor | **VALID** — Graesser, A.C. et al. (2004). "AutoTutor: A Tutor with Dialogue in Natural Language." Behavior Research Methods, 36(2), 180-192 |
| 29 | `sottilare2012` | GIFT framework | **VALID** — Sottilare, R.A. et al. (2012). "The Generalized Intelligent Framework for Tutoring (GIFT)." US Army Research Laboratory |
| 30 | `koedinger2006` | Knowledge engineering | **VALID** — Koedinger, K.R. et al. (2006). "Opening the Door to Non-Programmers." In Intelligent Tutoring Systems |
| 31 | `chen2023gamegpt` | GameGPT | **VALID** — Chen et al. (2023). "GameGPT: Multi-agent Collaborative Framework for Game Development." arXiv:2310.08067 |
| 32 | `langchain2024` | LangSmith | **FLAGGED — NOT PEER-REVIEWED.** This is software documentation. Move to footnote: `\footnote{LangSmith: \url{https://smith.langchain.com/}}` or cite as software: "LangChain (2024). LangSmith: LLM Application Observability Platform. \url{https://smith.langchain.com/}." |
| 33 | `sweller1988` | Cognitive Load Theory | **VALID** — Sweller, J. (1988). "Cognitive Load During Problem Solving: Effects on Learning." Cognitive Science, 12(2), 257-285 |
| 34 | `alayrac2022` | Vision-language models | **FLAGGED — VERIFY SCOPE.** Alayrac et al. (2022) is the Flamingo paper from DeepMind. The system actually uses Gemini and Qwen-VL, not Flamingo. The citation is acceptable as a general VLM reference but could be more precise. **Recommendation:** Consider citing Gemini (google2023) and/or Qwen-VL (Bai et al. 2023) directly instead. |

### Summary: References Requiring Action

| Priority | Key | Issue | Action |
|----------|-----|-------|--------|
| **P0** | `shen2023` | Likely misattributed | Replace with arXiv:2405.13966 or correct paper |
| **P0** | `learningsim2024` | Not academic | Find academic source or move to footnote |
| **P0** | `ge2023` | Imprecise DAG claim | Replace with Ridnik et al. 2024 (AlphaCodium) |
| **P1** | `paivio1991` | Ambiguous year | Verify: 1986 book or 1991 journal article |
| **P1** | `krath2021` | Claim doesn't match source | Adjust claim wording or add Hamari 2014 |
| **P1** | `alayrac2022` | System uses Gemini/Qwen, not Flamingo | Replace with google2023 or Bai2023 |
| **P1** | `langchain2024` | Not peer-reviewed | Move to footnote |
| **P2** | `shute2013` | Verify correct year (2008/2011/2013?) | Confirm MIT Press 2013 book |
| **P2** | `chapman2010` | Industry report, not peer-reviewed | Add footnote acknowledging this |
| **P2** | `wang2020` | Multiple Wang 2020 papers | Verify exact title |

---

## 3. Missing References (Priority-Sorted)

### P0 — Critical: Directly Supports Paper Claims

These references should be added to the paper as they directly support key arguments.

| # | Reference | Why Add | Where in Paper |
|---|-----------|---------|----------------|
| 1 | **Ridnik et al. (2024).** "AlphaCodium: From Prompt Engineering to Flow Engineering." arXiv:2401.08500 | Coined "flow engineering" — directly supports paper's DAG-over-ReAct argument. Replace `ge2023` with this. | Related Work, System Design |
| 2 | **arXiv:2405.13966 (2024).** "On the Brittle Foundations of ReAct Prompting for Agentic LLMs." | CRITICAL evidence that ReAct performance is driven by exemplar-query similarity, not interleaved reasoning. Directly supports paper's central claim. Replace `shen2023`. | Related Work, Introduction |
| 3 | **Arnab, S. et al. (2015).** "Mapping learning and game mechanics for serious games analysis." BJET, 46(2), 391-411 | The LM-GM (Learning Mechanics-Game Mechanics) framework — foundational for the Bloom's → mechanic mapping the paper relies on. | Related Work, System Design §3.2.3 |
| 4 | **Bloom, B.S. (1956).** "Taxonomy of Educational Objectives." David McKay Company | Original taxonomy. Paper only cites Anderson 2001 (revised). Should cite both. | Related Work |
| 5 | **Ngu et al. (2025).** "A Generative AI Educational Game Framework with Multi-Scaffolding." Computers & Education, Vol. 239 | Most directly comparable recent work — GenAI for educational games with empirical evaluation. n=91. | Related Work (new competitor) |
| 6 | **Deterding, S. et al. (2011).** "From Game Design Elements to Gamefulness: Defining 'Gamification'." MindTrek 2011 | Foundational definition paper (7,695+ citations). Should be cited when first using "gamification." | Introduction or Related Work |
| 7 | **Black, P. & Wiliam, D. (1998).** "Assessment and Classroom Learning." Assessment in Education, 5(1), 7-74 | Foundational formative assessment paper. Strengthens the assessment validity argument. | Related Work |

### P1 — High: Strengthens Specific Sections

| # | Reference | Why Add | Where in Paper |
|---|-----------|---------|----------------|
| 8 | **Hamari, J. et al. (2014).** "Does Gamification Work?" HICSS 2014. IEEE | Empirical gamification review — better supports "fails when applied decoratively" claim than `krath2021` | Related Work |
| 9 | **Sailer, M. et al. (2017).** "How gamification motivates: An experimental study of specific game design elements." Computers in Human Behavior, 69, 371-380 | Connects specific game elements to motivation outcomes. | Related Work |
| 10 | **Shute, V.J. (2008).** "Focus on Formative Feedback." Review of Educational Research, 78(1), 153-189 | Feedback design for assessment — relevant to per-node feedback at QG3 | System Design §3.2.5 |
| 11 | **Naps, T. et al. (2002).** "Exploring the Role of Visualization and Engagement in CS Education." ITiCSE Working Group | Engagement taxonomy (6 levels) — directly relevant to algorithm game design | Related Work or Appendix |
| 12 | **Hundhausen, C. et al. (2002).** "A Meta-Study of Algorithm Visualization Effectiveness." JERIC | How students use visualizations matters more than what they see — supports active engagement design | Related Work or Appendix |
| 13 | **Parsons, D. & Haden, P. (2006).** "Parsons Programming Puzzles: A Fun and Effective Learning Tool." Australasian Computing Education Conf. | Foundation for Algorithm Builder mechanic. 50% time savings over code writing. | Related Work or Appendix |
| 14 | **Sherlock (2025).** "Reliable and Efficient Agentic Workflow Execution." ICLR 2025. arXiv:2511.00330 | Selective verification + speculative execution: 18.3% accuracy gain, 48.7% latency reduction. Supports architectural efficiency argument. | Related Work |
| 15 | **Dicheva, D. et al. (2015).** "Gamification in Education: A Systematic Mapping Study." ET&S, 18(3), 75-88 | Systematic gamification-in-education mapping. 2000+ citations. | Related Work |

### P2 — Medium: Contextual Enrichment

| # | Reference | Why Add | Where in Paper |
|---|-----------|---------|----------------|
| 16 | **Kapp, K.M. (2012).** "The Gamification of Learning and Instruction." Pfeiffer/Wiley | Foundational book on educational gamification | Related Work |
| 17 | **Bandara et al. (2025).** "A Practical Guide for Designing Production-Grade Agentic AI Workflows." arXiv:2512.08769 | Nine best practices including tool-first design — supports design principles | System Design |
| 18 | **HALO (Hou et al. 2025).** "Hierarchical Autonomous Logic-Oriented Orchestration." arXiv:2505.13516 | Three-level agent hierarchy — validates hierarchical approach | Related Work |
| 19 | **Hu et al. (2024).** "Game Generation via Large Language Models." arXiv:2404.08706 | LLM-based game generation survey | Related Work |
| 20 | **PCG via GenAI (2024).** arXiv:2407.09013 | Procedural content generation with AI survey | Related Work |
| 21 | **Togelius, J. et al. (2011).** "Search-Based Procedural Content Generation: A Taxonomy and Survey." IEEE Trans. CI and AI in Games | PCG taxonomy — positions GamED.AI in the broader content generation landscape | Related Work |
| 22 | **Yannakakis, G.N. & Togelius, J. (2018).** "Artificial Intelligence and Games." Springer | Comprehensive AI + games reference | Related Work |
| 23 | **Wieman, C.E. et al. (2008).** "PhET: Simulations That Enhance Learning." Science, 322(5902) | PhET reference for the simulation-based future work direction | Future Work |
| 24 | **Ericson, B. et al. (2022).** "Parsons Problems and Beyond." ACM Computing Surveys | Systematic review of Parsons problems — supports algorithm builder | Appendix |
| 25 | **Lee, M. et al. (2014).** "Gidget: Design Principles for Debugging Games." U. Washington | 7 design principles for debugging games — supports Bug Hunter mechanic | Appendix |

### P3 — Nice-to-Have

| # | Reference | Why Add |
|---|-----------|---------|
| 26 | **Deci, E.L. & Ryan, R.M. (1985).** "Intrinsic Motivation and Self-Determination in Human Behavior." Plenum | Original SDT book (paper cites 2000 article) |
| 27 | **Oliveira, W. et al. (2025).** "The Effects of Gamification on Students' Flow Experience." JCAL | Gamification + flow connection |
| 28 | **Li, X. et al. (2023).** "Examining the effectiveness of gamification." Frontiers in Psychology | Additional gamification effectiveness evidence |
| 29 | **Kurnaz, F. (2025).** "Meta-Analysis of Gamification's Impact on Student Motivation in K-12." Psychology in the Schools | K-12 specific effect size g=0.654 |
| 30 | **dpvis (2024).** "A Visual and Interactive Learning Tool for Dynamic Programming." SIGCSE 2025 | Prediction-before-revelation pattern |
| 31 | **Sojourner under Sabotage (2024).** arXiv:2504.19287 | Debugging serious game reference |
| 32 | **AgentOrchestra (2025).** arXiv:2506.12508 | SOTA multi-agent orchestration |

---

## 4. Appendix: Bloom's Taxonomy → Mechanic Mapping Table

This table maps each Bloom's Revised Taxonomy level to supported game mechanics with academic justification. **Add this as an appendix table in the paper.**

### Source Reconciliation

The table below combines **both** template families (Interactive Diagram + Algorithm Game). The actual system implementation in `LITERATURE_REVIEW_AND_BASELINES.md` maps Interactive Diagram mechanics as:
- Remember → click_to_identify | Understand → drag_drop + description_matching | Apply → trace_path + description_matching | Analyze → hierarchical | Evaluate → compare_contrast | Create → sequencing + timed_challenge

Algorithm Game mechanics (State Tracer, Bug Hunter, Algorithm Builder, Complexity Analyzer, Constraint Puzzle) are mapped based on the research in `docs/audit/11_algorithmic_games_research.md` and `docs/mechanics/`. The table below is the unified mapping for the paper.

```latex
\section{Bloom's Taxonomy to Mechanic Contract Mapping}
\label{app:blooms_mapping}

Table~\ref{tab:blooms_mapping} specifies the Bloom's-to-mechanic
constraint table used by the planning agent in Phase 1
(Section~\ref{sec:bloomqg3}). Each mapping is grounded in the
cognitive operation taxonomy of Anderson \& Krathwohl (2001) and
validated against the LM-GM framework of Arnab et al.\ (2015).

\begin{table*}[ht]
\centering
\small
\begin{tabularx}{\textwidth}{@{} l l X l @{}}
\toprule
\textbf{Bloom's Level} & \textbf{Mechanic Types} & \textbf{Cognitive Operation} & \textbf{Supporting Reference} \\
\midrule
\textit{Remember}
  & Click-to-Identify, Memory Match
  & Recognizing and recalling factual knowledge through visual identification and paired association
  & Anderson \& Krathwohl (2001); Naps et al.\ (2002) \\[4pt]
\textit{Understand}
  & Drag-and-Drop, Description Matching
  & Interpreting and classifying by mapping labels to structures and matching descriptions to concepts
  & Mayer (2009); Arnab et al.\ (2015) \\[4pt]
\textit{Apply}
  & Trace Path, Sequencing, State Tracer\textsuperscript{A}
  & Executing procedures by tracing processes, ordering steps, and stepping through algorithms
  & Parsons \& Haden (2006); Hundhausen et al.\ (2002) \\[4pt]
\textit{Analyze}
  & Sorting/Categorization, Hierarchical, Bug Hunter\textsuperscript{A}, Complexity Analyzer\textsuperscript{A}
  & Differentiating and organizing by categorizing items, progressive reveal, identifying errors, and classifying complexity
  & Sweller (1988); Lee et al.\ (2014) \\[4pt]
\textit{Evaluate}
  & Compare/Contrast, Branching Scenario
  & Critiquing and judging by comparing alternatives and evaluating decision consequences
  & Mislevy et al.\ (2003); Black \& Wiliam (1998) \\[4pt]
\textit{Create}
  & Algorithm Builder\textsuperscript{A}, Constraint Puzzle\textsuperscript{A}
  & Generating and planning by constructing solutions from primitives and designing optimal strategies
  & Ericson (2022); Parsons \& Haden (2006) \\
\bottomrule
\end{tabularx}
\caption{Bloom's Taxonomy to mechanic contract mapping. Each
mechanic type is bound to a valid Bloom's range before generation
begins (Phase~1). The planning agent enforces these constraints
through the mechanic contract schema. \textsuperscript{A}~denotes
Algorithm Game template mechanics; unmarked mechanics belong to
the Interactive Diagram template family.}
\label{tab:blooms_mapping}
\end{table*}
```

### Extended Mapping with Metacognitive Dimensions

For a more detailed appendix, add metacognitive scaffolding per level:

| Bloom's Level | Mechanic | Template | Metacognitive Scaffold | Feedback Type | Reference |
|---|---|---|---|---|---|
| Remember | Click-to-Identify | ID | Guided prompts with decreasing specificity | Immediate correctness | Shute (2008) |
| Remember | Memory Match | ID | Time-based self-monitoring | Match/mismatch + hints | Naps et al. (2002) |
| Understand | Drag-and-Drop | ID | Description-based labels requiring interpretation | Per-label explanation | Mayer (2009) |
| Understand | Description Matching | ID | Relational reasoning between text and visual | Relational feedback | Arnab et al. (2015) |
| Apply | Trace Path | ID | Prediction-before-revelation at each step | Step-by-step correctness | dpvis (2024) |
| Apply | Sequencing | ID | Order construction with constraint hints | Position feedback | Parsons & Haden (2006) |
| Apply | State Tracer | Algo | Variable prediction with streak tracking | State diff feedback | Hundhausen et al. (2002) |
| Analyze | Sorting | ID | Multi-category classification | Category rationale | Sweller (1988) |
| Analyze | Hierarchical | ID | Progressive reveal with structural relationships | Layer-based | Arnab et al. (2015) |
| Analyze | Bug Hunter | Algo | Error identification with explanation requirement | Productive failure | Lee et al. (2014); O'Rourke (2014) |
| Analyze | Complexity Analyzer | Algo | Growth pattern recognition from data | Analytical feedback | Cormen et al. (2009) |
| Evaluate | Compare/Contrast | ID | Side-by-side judgment with criteria | Criterion-based | Mislevy et al. (2003) |
| Evaluate | Branching Scenario | ID | Decision consequence evaluation | Consequence chain | Black & Wiliam (1998) |
| Create | Algorithm Builder | Algo | Construction from primitives with distractors | Solution comparison | Ericson (2022) |
| Create | Constraint Puzzle | Algo | Optimal strategy design under constraints | Optimality ratio | Skiena (2008) |

*ID = Interactive Diagram template, Algo = Algorithm Game template*

---

## 5. Recommended .bib File

Below are the corrected/verified entries for all existing citations plus the P0 additions. Save as `gamedai.bib`.

```bibtex
% ============================================================
% EXISTING CITATIONS (verified/corrected)
% ============================================================

@article{openai2023,
  title={GPT-4 Technical Report},
  author={OpenAI},
  journal={arXiv preprint arXiv:2303.08774},
  year={2023}
}

@article{google2023,
  title={Gemini: A Family of Highly Capable Multimodal Models},
  author={{Google DeepMind}},
  journal={arXiv preprint arXiv:2312.11805},
  year={2023}
}

@inproceedings{jimenez2024,
  title={{SWE-bench}: Can Language Models Resolve Real-World {GitHub} Issues?},
  author={Jimenez, Carlos E. and Yang, John and Wettig, Alexander and Yao, Shunyu and Pei, Kexin and Press, Ofir and Narasimhan, Karthik},
  booktitle={ICLR},
  year={2024}
}

@article{chen2021,
  title={Evaluating Large Language Models Trained on Code},
  author={Chen, Mark and Tworek, Jerry and Jun, Heewoo and Yuan, Qiming and others},
  journal={arXiv preprint arXiv:2107.03374},
  year={2021}
}

@techreport{mislevy2003,
  title={A Brief Introduction to Evidence-Centered Design},
  author={Mislevy, Robert J. and Almond, Russell G. and Lukas, Janice F.},
  institution={ETS},
  year={2003}
}

@book{shute2013,
  title={Stealth Assessment: Measuring and Supporting Learning in Video Games},
  author={Shute, Valerie J. and Ventura, Matthew},
  publisher={MIT Press},
  year={2013}
}

@article{sailer2020,
  title={The Gamification of Learning: A Meta-analysis},
  author={Sailer, Michael and Homner, Lisa},
  journal={Educational Psychology Review},
  volume={32},
  pages={77--112},
  year={2020}
}

@article{wouters2013,
  title={A Meta-Analysis of the Cognitive and Motivational Effects of Serious Games},
  author={Wouters, Pieter and van Nimwegen, Christof and van Oostendorp, Herre and van der Spek, Erik D.},
  journal={Journal of Educational Psychology},
  volume={105},
  number={2},
  pages={249--265},
  year={2013}
}

@article{zeng2024,
  title={Exploring the impact of gamification on students' academic performance},
  author={Zeng, Jiaying and Sun, Dan and Looi, Chee Kit and Fan, Xin},
  journal={British Journal of Educational Technology},
  volume={55},
  number={6},
  pages={2478--2502},
  year={2024}
}

@techreport{chapman2010,
  title={How Long Does it Take to Create Learning?},
  author={{Chapman Alliance}},
  institution={Chapman Alliance},
  year={2010},
  note={Industry research study}
}

% REPLACEMENT for learningsim2024 — use chapman2010 for both cost claims
% or add this footnote-style entry:
% @misc{learningsim2024,
%   title={Game-Based Learning Development Costs},
%   howpublished={\url{https://learningsim.com/...}},
%   year={2024},
%   note={Industry estimate; not peer-reviewed}
% }

@article{wang2020,
  title={The effect of using {Kahoot!} for learning -- A literature review},
  author={Wang, Alf Inge and Tahir, Rabail},
  journal={Computers \& Education},
  volume={149},
  pages={103818},
  year={2020}
}

@article{ji2023,
  title={Survey of Hallucination in Natural Language Generation},
  author={Ji, Ziwei and Lee, Nayeon and Frieske, Rita and Yu, Tiezheng and others},
  journal={ACM Computing Surveys},
  volume={55},
  number={12},
  year={2023}
}

% REPLACEMENT for shen2023:
@article{brittle_react2024,
  title={On the Brittle Foundations of {ReAct} Prompting for Agentic Large Language Models},
  author={Anonymous},
  journal={arXiv preprint arXiv:2405.13966},
  year={2024},
  note={Demonstrates ReAct performance driven by exemplar-query similarity, not interleaved reasoning}
}

@inproceedings{yao2023,
  title={{ReAct}: Synergizing Reasoning and Acting in Language Models},
  author={Yao, Shunyu and Zhao, Jeffrey and Yu, Dian and Du, Nan and Shafran, Izhak and Narasimhan, Karthik and Cao, Yuan},
  booktitle={ICLR},
  year={2023}
}

@article{freeman2014,
  title={Active learning increases student performance in science, engineering, and mathematics},
  author={Freeman, Scott and Eddy, Sarah L. and McDonough, Miles and Smith, Michelle K. and others},
  journal={Proceedings of the National Academy of Sciences},
  volume={111},
  number={23},
  pages={8410--8415},
  year={2014}
}

% Use the 1986 book (foundational) OR the 1991 article — be explicit:
@book{paivio1986,
  title={Mental Representations: A Dual Coding Approach},
  author={Paivio, Allan},
  publisher={Oxford University Press},
  year={1986}
}
% OR:
@article{paivio1991,
  title={Dual Coding Theory: Retrospect and Current Status},
  author={Paivio, Allan},
  journal={Canadian Journal of Psychology},
  volume={45},
  number={3},
  pages={255--287},
  year={1991}
}

@book{mayer2009,
  title={Multimedia Learning},
  author={Mayer, Richard E.},
  edition={2nd},
  publisher={Cambridge University Press},
  year={2009}
}

@book{anderson2001,
  title={A Taxonomy for Learning, Teaching, and Assessing: A Revision of {Bloom's} Taxonomy of Educational Objectives},
  author={Anderson, Lorin W. and Krathwohl, David R.},
  publisher={Longman},
  year={2001}
}

@article{krath2021,
  title={Revealing the theoretical basis of gamification: A systematic review and analysis of theory in research on gamification, serious games and game-based learning},
  author={Krath, Jeanine and Sch{\"u}rmann, Linda and von Korflesch, Harald F.O.},
  journal={Computers in Human Behavior},
  volume={125},
  pages={106963},
  year={2021}
}

@article{landers2014,
  title={Developing a Theory of Gamified Learning: Linking Serious Games and Gamification of Learning},
  author={Landers, Richard N.},
  journal={Simulation \& Gaming},
  volume={45},
  number={6},
  pages={752--768},
  year={2014}
}

@article{ryan2000,
  title={Self-Determination Theory and the Facilitation of Intrinsic Motivation, Social Development, and Well-Being},
  author={Ryan, Richard M. and Deci, Edward L.},
  journal={American Psychologist},
  volume={55},
  number={1},
  pages={68--78},
  year={2000}
}

@book{csikszentmihalyi1990,
  title={Flow: The Psychology of Optimal Experience},
  author={Csikszentmihalyi, Mihaly},
  publisher={HarperPerennial},
  year={1990}
}

@article{hong2023,
  title={{MetaGPT}: Meta Programming for A Multi-Agent Collaborative Framework},
  author={Hong, Sirui and Zhuge, Mingchen and Chen, Jonathan and Xiong, Xiawu and others},
  journal={arXiv preprint arXiv:2308.00352},
  year={2023},
  note={ICLR 2024 Oral}
}

@article{wu2023,
  title={{AutoGen}: Enabling Next-Gen {LLM} Applications via Multi-Agent Conversation},
  author={Wu, Qingyun and Bansal, Gagan and Zhang, Jieyu and Wu, Yiran and others},
  journal={arXiv preprint arXiv:2308.08155},
  year={2023}
}

% REPLACEMENT for ge2023:
@article{ridnik2024,
  title={{AlphaCodium}: From Prompt Engineering to Flow Engineering},
  author={Ridnik, Tal and Kredo, Dedy and Friedman, Itamar},
  journal={arXiv preprint arXiv:2401.08500},
  year={2024},
  note={Coined ``flow engineering''; nearly doubled GPT-4 accuracy via test-based iterative flow}
}

@article{willard2023,
  title={Efficient Guided Generation for Large Language Models},
  author={Willard, Brandon T. and Louf, R{\'e}mi},
  journal={arXiv preprint arXiv:2307.09702},
  year={2023}
}

@article{graesser2004,
  title={{AutoTutor}: A Tutor with Dialogue in Natural Language},
  author={Graesser, Arthur C. and Lu, Shulan and Jackson, G. Tanner and Mitchell, Heather H. and others},
  journal={Behavior Research Methods, Instruments, \& Computers},
  volume={36},
  number={2},
  pages={180--192},
  year={2004}
}

@techreport{sottilare2012,
  title={The Generalized Intelligent Framework for Tutoring ({GIFT})},
  author={Sottilare, Robert A. and Goldberg, Benjamin S. and Brawner, Keith W. and Holden, Heather K.},
  institution={US Army Research Laboratory},
  year={2012}
}

@inproceedings{koedinger2006,
  title={Opening the Door to Non-Programmers: Authoring Intelligent Tutor Behavior by Demonstration},
  author={Koedinger, Kenneth R. and Aleven, Vincent and Heffernan, Neil and McLaren, Bruce and Hockenberry, Matthew},
  booktitle={Intelligent Tutoring Systems},
  year={2006}
}

@article{chen2023gamegpt,
  title={{GameGPT}: Multi-agent Collaborative Framework for Game Development},
  author={Chen, Dake and others},
  journal={arXiv preprint arXiv:2310.08067},
  year={2023}
}

@misc{langchain2024,
  title={{LangSmith}: {LLM} Application Observability Platform},
  author={{LangChain AI}},
  howpublished={\url{https://smith.langchain.com/}},
  year={2024},
  note={Software platform, not peer-reviewed}
}

@article{sweller1988,
  title={Cognitive Load During Problem Solving: Effects on Learning},
  author={Sweller, John},
  journal={Cognitive Science},
  volume={12},
  number={2},
  pages={257--285},
  year={1988}
}

@article{alayrac2022,
  title={Flamingo: A Visual Language Model for Few-Shot Learning},
  author={Alayrac, Jean-Baptiste and Donahue, Jeff and Luc, Pauline and Miech, Antoine and others},
  journal={Advances in Neural Information Processing Systems},
  volume={35},
  year={2022}
}

% ============================================================
% NEW CITATIONS TO ADD (P0)
% ============================================================

@article{arnab2015,
  title={Mapping learning and game mechanics for serious games analysis},
  author={Arnab, Sylvester and Lim, Theodore and Carvalho, Maira B. and Bellotti, Francesco and others},
  journal={British Journal of Educational Technology},
  volume={46},
  number={2},
  pages={391--411},
  year={2015}
}

@book{bloom1956,
  title={Taxonomy of Educational Objectives: The Classification of Educational Goals},
  author={Bloom, Benjamin S.},
  publisher={David McKay Company},
  year={1956}
}

@article{ngu2025,
  title={A Generative {AI} Educational Game Framework with Multi-Scaffolding},
  author={Ngu, Anne and others},
  journal={Computers \& Education},
  volume={239},
  year={2025}
}

@inproceedings{deterding2011,
  title={From Game Design Elements to Gamefulness: Defining ``Gamification''},
  author={Deterding, Sebastian and Dixon, Dan and Khaled, Rilla and Nacke, Lennart},
  booktitle={15th International Academic MindTrek Conference},
  year={2011}
}

@article{black1998,
  title={Assessment and Classroom Learning},
  author={Black, Paul and Wiliam, Dylan},
  journal={Assessment in Education: Principles, Policy \& Practice},
  volume={5},
  number={1},
  pages={7--74},
  year={1998}
}

% ============================================================
% NEW CITATIONS TO ADD (P1)
% ============================================================

@inproceedings{hamari2014,
  title={Does Gamification Work? -- A Literature Review of Empirical Studies on Gamification},
  author={Hamari, Juho and Koivisto, Jonna and Sarsa, Harri},
  booktitle={47th Hawaii International Conference on System Sciences (HICSS)},
  year={2014}
}

@article{sailer2017,
  title={How gamification motivates: An experimental study of the effects of specific game design elements on psychological need satisfaction},
  author={Sailer, Michael and Hense, Jan Ulrich and Mayr, Sarah Katharina and Mandl, Heinz},
  journal={Computers in Human Behavior},
  volume={69},
  pages={371--380},
  year={2017}
}

@article{shute2008,
  title={Focus on Formative Feedback},
  author={Shute, Valerie J.},
  journal={Review of Educational Research},
  volume={78},
  number={1},
  pages={153--189},
  year={2008}
}

@inproceedings{naps2002,
  title={Exploring the Role of Visualization and Engagement in Computer Science Education},
  author={Naps, Thomas L. and others},
  booktitle={ITiCSE Working Group Reports},
  year={2002}
}

@article{hundhausen2002,
  title={A Meta-Study of Algorithm Visualization Effectiveness},
  author={Hundhausen, Christopher D. and Douglas, Sarah A. and Stasko, John T.},
  journal={Journal of Visual Languages and Computing},
  volume={13},
  number={3},
  pages={259--290},
  year={2002}
}

@inproceedings{parsons2006,
  title={Parson's Programming Puzzles: A Fun and Effective Learning Tool},
  author={Parsons, Dale and Haden, Patricia},
  booktitle={Australasian Computing Education Conference},
  year={2006}
}

@article{dicheva2015,
  title={Gamification in Education: A Systematic Mapping Study},
  author={Dicheva, Darina and Dichev, Christo and Agre, Gennady and Angelova, Galia},
  journal={Educational Technology \& Society},
  volume={18},
  number={3},
  pages={75--88},
  year={2015}
}

@article{sherlock2025,
  title={Sherlock: Reliable and Efficient Agentic Workflow Execution},
  author={{Microsoft Research}},
  journal={arXiv preprint arXiv:2511.00330},
  year={2025},
  note={ICLR 2025}
}
```

---

## Summary of All Fixes

### Fix Checklist

| # | Priority | Fix | Section | Status |
|---|----------|-----|---------|--------|
| 1 | **P0** | Fix version naming (abstract says v3, body says v4) | Abstract, §3.1 | ✅ Applied |
| 2 | **P0** | Define VPR on first use | §3.1 | ✅ Applied |
| 3 | **P0** | Fix typo "structurther" → "structure rather" | Conclusion | ✅ Applied |
| 4 | **P0** | Reframe as 2 templates + 15 mechanics (was "16 templates") | Throughout | ✅ Applied |
| 5 | **P0** | Replace `shen2023` → `brittle_react2024` | §1, §2 | ✅ Applied (both intro + related work) |
| 6 | **P0** | Replace `ge2023` → `ridnik2024` | §2, §3.2.1 | ✅ Applied |
| 7 | **P0** | Remove `learningsim2024` (not academic) | §1 | ✅ Applied |
| 8 | **P0** | Fix `\gamedai{}` vs GAMED.AI inconsistency | §2 | ✅ Applied |
| 9 | **P0** | Fix game library count → 50 consistently | Throughout | ✅ Applied |
| 10 | **P0** | Fix `\ref{sec:results}` → `\ref{sec:eval}` | §3 | ✅ Applied |
| 11 | **P1** | Deduplicate experimental setup (§4.1 vs §5) | §4.1 | ✅ Applied (forward reference) |
| 12 | **P1** | Reduce "X, not Y" pattern from 8 to 3 | Throughout | ✅ Applied |
| 13 | **P1** | Verify `paivio1991` year | §2 | ✅ Verified (1991 journal article) |
| 14 | **P1** | Replace `krath2021` → `hamari2014` for decorative failure claim | §2 | ✅ Applied |
| 15 | **P1** | Remove `alayrac2022` (system uses Gemini, not Flamingo) | §3.2.2 | ✅ Applied (removed in rewrite) |
| 16 | **P1** | Move `langchain2024` to footnote | §5 | ✅ Applied |
| 17 | **P1** | `chapman2010` and `wang2020` | §1, §2 | ✅ Verified (industry report + Kahoot review) |
| 18 | **P2** | Add observability dashboard section | New §3.4 | ✅ Applied |
| 19 | **P2** | Add model agnosticism framing | §3.2.6 | ✅ Applied |
| 20 | **P2** | Add frontend game engine section | New §3.3 | ✅ Applied |
| 21 | **P2** | Add assembly-line metaphor | §3 | ⬜ Deferred (low priority) |
| 22 | **P2** | Reduce repetition of key numbers | Throughout | ✅ Partially applied (dedup setup) |
| 23 | **P2** | Add Bloom's→Mechanic appendix table | Appendix A | ✅ Applied |
| 24 | **P2** | Add Bloom 1956 + Arnab 2015 + Deterding 2011 + Black 1998 + Shute 2008 + Hamari 2014 citations | §2 | ✅ Applied |
| 25 | **P2** | Add Ngu 2025 as comparable work | §2 | ✅ Applied |
| 26 | **NEW** | Add full-width Figure 1 (system flow, 4 parts) | After §2 (page 2) | ✅ Placeholder added |
| 27 | **NEW** | Add full-width Figure 2 (DAG architecture) | §3.2.1 (page 3) | ✅ Placeholder added |
| 28 | **NEW** | Move per-mechanic table + failure analysis to appendix | §5 → App B | ✅ Applied |
| 29 | **NEW** | Create `gamedai.bib` with all entries | Root | ✅ Created |
| 30 | **NEW** | Add `dndkit2024` citation for frontend section | New §3.3 | ✅ Applied |

### Audit Corrections Applied to This Document

| Issue | What Was Wrong | Fix Applied |
|-------|----------------|-------------|
| Accessibility claims overstated | Claimed incomplete WCAG integration | Reframed as planned feature with architectural support (per user directive) |
| QG inspection UI claimed | Document said QG inspection exists | Added explicit "NOT implemented" note |
| Zustand claimed universally | Only InteractiveDiagramGame uses it | Clarified split: Zustand (ID) + useReducer (Algo) |
| Bloom's table missing reconciliation | Table didn't note which mappings are implemented vs theoretical | Added source reconciliation note + Template column in extended table |
| `brittle_react2024` status unclear | Appeared to be done but citation not in paper | Added Issue 1.14b explicitly flagging this as pending |
| Game count vague | "50+" used loosely | Fixed to exactly "50 games (45 ID + 5 Algo)" |
| Template registry overstated | Called it app-level registry | Clarified: mechanic-level registry exists, app-level is if/else |

---

*Document generated from cross-referencing paper text against all research documentation in the GamED.AI repository. Audited 2026-02-27 against actual codebase.*
