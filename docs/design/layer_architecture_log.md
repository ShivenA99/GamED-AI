# Layer Architecture Design Log

## Overview

Bottom-up rebuild of the InteractiveDiagramGame frontend engine + backend pipeline.
Each layer builds on the one below it. Conversations and decisions documented per-layer.

## Layer Stack

| Layer | Name | Scope | Status |
|-------|------|-------|--------|
| 7 | Frontend Game Components | React interaction components (10 mechanics) | DONE |
| 6 | Game Library | Game sequence renderer, scene management | DONE |
| 5 | Game Engine | Pure-function engine (scoring, feedback, transitions, completion) | DONE |
| 4 | Game Data Config | Zod validation + normalization boundary | DONE |
| 3 | State Management | Zustand store: per-mechanic progress, scores, transitions | PLANNING |
| 2 | Per-Mechanic Registry | Frontend mechanic → component/rules/validation mapping | TODO |
| 1 | Backend Pipeline | Backend context registry + per-agent scoping | TODO |
| 0 | Infrastructure | Shared contracts, LangGraph state channels, typed sub-states | TODO |

---

## Layer 4: Game Data Config (Feb 13, 2026)

### What was built
- Zod schemas for root blueprint + 10 mechanic configs + scoring + feedback
- Case normalizer: snake_case → camelCase for backend compatibility
- Misconception normalizer: Dict → Array format conversion
- `parseBlueprint()` single entry point: parse → validate → default-fill → surface errors
- Validation error UI overlay (red panel with error/warning list)
- Wired into `index.tsx` (useMemo before normalize) and `game/[id]/page.tsx`

### Files created
- `engine/schemas/mechanicConfigSchemas.ts` (~220 lines)
- `engine/schemas/blueprintSchema.ts` (~160 lines)
- `engine/schemas/gameSequenceSchema.ts` (~110 lines)
- `engine/schemas/caseNormalizer.ts` (~80 lines)
- `engine/schemas/parseBlueprint.ts` (~170 lines)
- `engine/schemas/index.ts` (barrel export)

### Key decisions
- Used Zod 4.x (installed fresh, `z.record()` requires 2 args)
- `.passthrough()` on all object schemas to tolerate unknown backend fields
- `.default()` on required fields for graceful degradation
- Validation runs in `useMemo` — no runtime cost on re-renders
- Errors block game rendering; warnings are console-logged only

### What this enables
- Layer 3 (State Management) can trust that blueprint data is structurally valid
- No more defensive `??` fallbacks needed in store initialization
- Backend schema changes caught at parse time, not during gameplay

---

## Context Registry Discussion (Feb 13, 2026)

### Problem
Backend agents suffer context bloat. `AgentState` has 160+ fields. Every agent gets the full state even though most need only 5-10 fields. This wastes tokens, degrades LLM reasoning quality, and prevents parallelization.

### Goal
Per backend agent, per mechanic, per asset type, per asset: provide **exactly** the context needed, nothing more.

### Options Discussed

**Option 1 (CHOSEN)**: Keep Layer 2 frontend-only. Add parallel backend context registry in Layer 1. Layer 0 provides shared schema contracts.
- Incremental path
- Frontend and backend registries evolve independently
- Can converge to Option 2 later

**Option 2 (DEFERRED)**: Promote Layer 2 to shared layer consumed by both frontend and backend.
- Cleaner architecture
- Bigger scope, more coupling
- Better for long-term but premature now

### Where anti-bloat lives
- **Layer 1**: Each agent declares `reads: [...]` and `writes: [...]`. Context builder assembles only declared inputs. Tools get scoped context.
- **Layer 0**: Typed sub-states (design context, scene context, asset context). LangGraph channel isolation enforces read/write boundaries.
- **Target**: `game_designer_v3` gets 8 fields, not 160.

---

## Layer 3: State Management (Feb 13, 2026)

### Key Discovery: Store Already Well-Built
The Zustand store was explored in depth. Findings:
- 41 state fields, 34+ actions, all 7 known MEMORY.md bugs FIXED
- Full engine integration (8 modules: scoring, feedback, completion, transitions, init, scene mgmt, correctness, flow graph)
- All 10 mechanics have progress tracking (5 new + 4 legacy + 1 wrapper)
- Delta-based scoring throughout — no overwrites

### The REAL Problem: Component ↔ Store Sync Gap
The store is correct, but **components don't use it properly**:

| Component | Calls onAction | Consumes storeProgress | Computes Score Locally |
|-----------|---------------|----------------------|----------------------|
| Sequencing | YES | YES | YES (problem) |
| Sorting | YES | PARTIAL | NO |
| MemoryMatch | YES | NO (defined, unused) | YES (problem) |
| Branching | YES | NO (defined, unused) | YES (problem) |
| Compare | YES | NO (defined, unused) | YES (problem) |
| Description | YES | YES | NO |

### Solution: Bidirectional Action Feedback
1. **ActionResult type** — `useMechanicDispatch` returns `{ isCorrect, scoreDelta, message?, data? }` instead of void
2. **storeProgress restoration** — 4 components initialize from storeProgress on mount (MemoryMatch, Branching, Compare, Sorting)
3. **Remove local scoring** — 4 components stop computing scores locally (Sequencing, MemoryMatch, Branching, Compare)
4. **Remove deprecated callbacks** — `onPairMatched`, `onChoiceMade`, `onCategorizationChange`, `onStoreMatch` deleted

### Scope
- ~11 files, ~+175 net lines
- Store itself: NO changes needed (already correct)
- Non-breaking Phase 1 (type+hook changes), then per-component fixes
- Verification: storeProgress restore on refresh, score consistency, tsc 0 errors
