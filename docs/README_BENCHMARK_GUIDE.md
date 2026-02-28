# Game Generation Benchmark Guide
## Using the Heart Game Prompts with Claude Code

**Date**: February 12, 2026  
**Project**: GamifyAssessment – Claude Code Benchmarking  
**Task**: "Label the Parts of the Heart and Order the Flow"  

---

## Overview

This folder contains **three comprehensive documents** designed to benchmark Claude Code's ability to generate educational games under two distinct constraints:

1. **BENCHMARK_BASELINE_1_INFRASTRUCTURE_AWARE.md** — Uses your existing custom game engine
2. **BENCHMARK_BASELINE_2_FROM_SCRATCH.md** — Pure React/vanilla web technologies
3. **BENCHMARK_CLAUDE_CODE_CONSTRAINTS_AND_LIMITATIONS.md** — Research on expected errors and limitations

Combined, these documents form a **complete specification** for generating the same game two different ways, allowing you to:
- Measure Claude Code's infrastructure utilization capability
- Measure Claude Code's raw coding ability
- Compare and analyze performance across different constraint levels

---

## Quick Start

### For Baseline 1 (Infrastructure-Aware)

**Step 1**: Open `BENCHMARK_BASELINE_1_INFRASTRUCTURE_AWARE.md`  
**Step 2**: Paste the entire document into Claude Code with this preamble:

```
You are an expert TypeScript/React developer who deeply understands the GamifyAssessment 
custom game engine.

[PASTE ENTIRE BASELINE 1 PROMPT HERE]

Your task: Generate a complete, production-ready InteractiveDiagramBlueprint JSON object 
(or TypeScript const) for the "Label the Parts of the Heart and Order the Flow" game.

Requirements:
- Output MUST be valid JSON
- Must strictly conform to the InteractiveDiagramBlueprint TypeScript interface
- NO external libraries; use ONLY existing custom components
- Include comprehensive configuration for both labeling (drag-drop) and sequencing mechanics
- Blood flow sequence must be anatomically accurate

Output format: 
```typescript
export const heartGameBlueprint: InteractiveDiagramBlueprint = {
  // your JSON here
};
```
```

**Step 3**: Copy the generated blueprint  
**Step 4**: Test by importing into your Next.js app:
```tsx
import { heartGameBlueprint } from './generated-blueprint';

export default function HeartGame() {
  return <InteractiveDiagramGame blueprint={heartGameBlueprint} />;
}
```

### For Baseline 2 (From-Scratch)

**Step 1**: Open `BENCHMARK_BASELINE_2_FROM_SCRATCH.md`  
**Step 2**: Paste the entire document into Claude Code with this preamble:

```
You are an expert React developer. You will build a complete, production-ready educational 
game from scratch using ONLY standard web technologies (React, TypeScript, Tailwind CSS, 
SVG, native drag-and-drop APIs).

[PASTE ENTIRE BASELINE 2 PROMPT HERE]

Your task: Implement the complete "Label the Parts of the Heart and Order the Flow" game.

Requirements:
- Use ONLY React 18, TypeScript, Tailwind CSS, SVG, and standard browser APIs
- NO custom game engines, NO external game libraries, NO Keras/TensorFlow, NO Phaser
- Must be fully playable in a single Next.js page component
- Include Phase 1 (label identification) and Phase 2 (blood flow sequencing)
- Implement scoring, feedback, animations, and accessibility features

Output format: A complete, runnable React component that can be dropped into a Next.js app.
```

**Step 3**: Copy the generated code  
**Step 4**: Create a test file:
```tsx
// src/app/heart-game/page.tsx
import { HeartGame } from '@/components/HeartGame';

export default function Page() {
  return <HeartGame />;
}
```

---

## Expected Outcomes

### Baseline 1 (Infrastructure-Aware)

**Best Case Scenario (80-90% of outcomes)**:
- ✅ Valid JSON blueprint generated
- ✅ All 8 heart parts labeled with realistic coordinates
- ✅ Drag-drop and sequencing mechanics configured
- ✅ Blood flow order is anatomically accurate
- ✅ Scoring is consistent (80 + 20 = 100 points)
- ✅ Can be immediately dropped into `<InteractiveDiagramGame blueprint={...} />`

**Common Imperfections (10-20% of outcomes)**:
- ⚠️ Zone positioning needs fine-tuning (coordinates off by 5-10%)
- ⚠️ Some optional fields missing (e.g., `temporalConstraints`, `hints`)
- ⚠️ Feedback messages lack template variables (`{{label}}`, `{{zone}}`)
- ⚠️ Distractor explanations are generic instead of pedagogical
- ⚠️ Minor schema property naming inconsistencies

**How to Debug**:
1. Check JSON validity: `JSON.parse(blueprint)`
2. Validate schema: Run TypeScript type-check
3. Test ID references: Ensure all `correctZoneId` values exist in `zones[]`
4. Verify anatomical accuracy: Cross-check blood flow order against medical references
5. Calculate scores: Verify `mechanic.scoring.points_per_correct × count = max_score`

### Baseline 2 (From-Scratch)

**Best Case Scenario (60-75% of outcomes)**:
- ✅ Code runs without errors
- ✅ Drag-and-drop labels snap to zones
- ✅ Phase 1 → Phase 2 transition works
- ✅ Scoring calculated correctly
- ✅ Animations smooth (no jank)
- ✅ Responsive on mobile/tablet/desktop

**Common Issues (25-40% of outcomes)**:
- ⚠️ Drag-drop sometimes doesn't register (event handler bugs)
- ⚠️ Responsiveness breaks at certain screen sizes
- ⚠️ Animations are jerky or cause layout thrashing
- ⚠️ State management uses excessive prop drilling
- ⚠️ Missing error handling (e.g., what if label placed twice?)
- ⚠️ Accessibility not implemented (no keyboard nav, no screen reader support)
- ⚠️ Performance issues on slower devices (re-renders, memory leaks)

**How to Debug**:
1. Check for TypeScript errors: `tsc --noEmit`
2. Test functionality: Manually play through both phases
3. Check responsiveness: Resize browser, test on mobile
4. Verify animations: Use DevTools to inspect for layout thrashing
5. Validate accessibility: Use axe DevTools browser extension
6. Performance profile: Use Lighthouse or React DevTools Profiler

---

## Comparison: Which Baseline Is Better?

| Metric | Baseline 1 | Baseline 2 | Winner |
|--------|-----------|-----------|--------|
| **Schema Accuracy** | High (90%+) | N/A | Baseline 1 |
| **Raw Coding** | N/A | Medium (75%) | Baseline 2 |
| **Infrastructure Knowledge** | Required | None | Baseline 1 |
| **Lines of Code** | ~200-300 JSON | ~1000-1500 TSX | Baseline 2 |
| **Debugging Difficulty** | Easy (schema validation) | Hard (runtime errors) | Baseline 1 |
| **Time to Playable** | Minutes (if valid) | Hours (with fixes) | Baseline 1 |
| **Long-term Maintenance** | Easy (engine evolves) | Hard (custom code) | Baseline 1 |

**Conclusion**: Baseline 1 tests Claude Code's ability to use existing infrastructure (faster, more reliable). Baseline 2 tests raw coding ability (slower, more error-prone).

---

## Detailed Evaluation Rubric

### Baseline 1 Evaluation (Out of 100 Points)

**Schema Compliance (40 points)**:
- Valid JSON structure: 10 pts
- All required fields present: 10 pts
- Correct field types/names: 10 pts
- ID reference consistency: 10 pts

**Content Quality (40 points)**:
- Heart anatomy accurate: 10 pts
- Zone positioning realistic: 10 pts
- Blood flow sequence correct: 10 pts
- Feedback messages pedagogical: 10 pts

**Advanced Features (20 points)**:
- Multi-mechanic transitions logic: 5 pts
- Hierarchical zone grouping (optional): 5 pts
- Temporal constraints (optional): 5 pts
- Distractor explanations thoughtful: 5 pts

**Scoring Example**:
- Schema: 35/40 (minor typos, 1 field missing)
- Content: 38/40 (zone positioning off, hints generic)
- Advanced: 12/20 (transitions good, but no hierarchical grouping)
- **Total: 85/100 — Good, needs polish**

### Baseline 2 Evaluation (Out of 100 Points)

**Functionality (40 points)**:
- Runs without runtime errors: 10 pts
- Drag-and-drop works correctly: 10 pts
- Phase transitions function: 10 pts
- Scoring calculates accurately: 10 pts

**Quality (40 points)**:
- Responsive design works: 10 pts
- Animations smooth (60fps): 10 pts
- State management clean: 10 pts
- Code organization/readability: 10 pts

**Polish & Accessibility (20 points)**:
- Error handling comprehensive: 5 pts
- Accessibility features (a11y): 5 pts
- Performance optimized: 5 pts
- Visual design polished: 5 pts

**Scoring Example**:
- Functionality: 38/40 (minor drag-drop bug)
- Quality: 32/40 (responsive OK, animations jerky, state messy)
- Polish: 8/20 (no a11y, no error handling)
- **Total: 78/100 — Functional, needs significant work**

---

## How to Iterate & Improve

### If Baseline 1 Output Is Poor (< 70/100)

1. **Identify the core issue**:
   - Schema errors? → Ask Claude Code to validate against TypeScript definitions
   - Anatomical errors? → Provide the correct blood flow sequence explicitly in follow-up
   - Missing fields? → List required fields and ask for re-generation

2. **Iterative refinement**:
   ```
   I generated a blueprint, but the zone coordinates are unrealistic. 
   Please regenerate ONLY the zones array with proper coordinates:
   - Right Atrium: x=20, y=25, radius=35
   - Right Ventricle: x=20, y=70, radius=40
   - [etc.]
   
   Ensure zones don't overlap and fit within the 0-100% scale.
   ```

3. **Validate before moving to Baseline 2**:
   - Ensure the Baseline 1 blueprint is > 80/100 before benchmarking Baseline 2
   - A broken Baseline 1 is a unfair comparison to Baseline 2

### If Baseline 2 Output Is Poor (< 70/100)

1. **Check the error type**:
   - Runtime errors (code doesn't run)? → Fix TypeScript, hooks violations
   - Logic errors (drag-drop broken)? → Refactor event handling
   - Product issues (not responsive)? → Add media queries, test on devices

2. **Ask for specific fixes**:
   ```
   The drag-and-drop isn't working. The issue is likely in the onDrop handler.
   Please fix:
   1. Ensure e.preventDefault() is called in dragover
   2. Verify dropEffect is set correctly
   3. Ensure the dropped label updates state correctly
   
   Provide only the fixed HeartDiagram.tsx component.
   ```

3. **Request improvements by priority**:
   ```
   Phase 1: Make the code run without errors (priority: high)
   Phase 2: Make it responsive on mobile (priority: high)
   Phase 3: Add accessibility features like ARIA labels (priority: medium)
   Phase 4: Optimize performance with useMemo/useCallback (priority: low)
   ```

---

## Benchmark Variations (Advanced)

To test additional dimensions, try these variations:

### Variation 1: Shorter Prompt (Token Budget)
**Hypothesis**: Can Claude Code generate quality code with fewer tokens?

- Remove detailed explanations (Part 9 in Baseline 2)
- Remove examples
- Keep only requirements + constraints

**Expected Result**: Baseline 2 quality drops 10-15%, Baseline 1 quality drops 5-10%

### Variation 2: Add Reference Implementation
**Hypothesis**: Providing an example improves quality

- Include a minimal valid example (e.g., 2 zones, 2 labels, 1 mechanic) in the prompt
- Ask model to pattern-match against example

**Expected Result**: Quality improves 10-20% across both baselines

### Variation 3: Request Code Review First
**Hypothesis**: Having the model review its own output catches errors

- Generate the blueprint/code
- Ask: "Review your output. List any potential issues (missing fields, anatomical errors, schema violations)."
- Ask: "Fix the issues you identified."

**Expected Result**: Quality improves 15-25% (especially Baseline 2)

### Variation 4: Split Baseline 1 Into Sub-Tasks
**Hypothesis**: Breaking schema generation into steps improves accuracy

- Step 1: Generate zones only
- Step 2: Generate labels (with validation against zones)
- Step 3: Generate mechanics and transitions
- Step 4: Combine into final blueprint

**Expected Result**: Quality improves 20-30% (schema errors drop significantly)

---

## Capturing Results

### Recommended Metrics to Track

```markdown
## Benchmark Run: Baseline 1, 2026-02-12

**Model**: Claude Haiku 4.5
**Temperature**: 0.7
**Max Tokens**: 4000

### Baseline 1 Results
- Schema Compliance: 35/40 (missing feedback messages field)
- Content Quality: 38/40 (zone positioning off, blood flow correct)
- Advanced Features: 12/20 (no hierarchical grouping)
- **Total: 85/100**

### Baseline 2 Results
- Functionality: 38/40 (drag-drop has minor bug)
- Quality: 32/40 (animations jerky, prop drilling)
- Polish: 8/20 (no accessibility, basic error handling)
- **Total: 78/100**

### Key Observations
1. Baseline 1 outperformed Baseline 2 by 7 points (expected)
2. Main weakness in Baseline 1: Missing optional fields
3. Main weakness in Baseline 2: Missing accessibility, performance
4. Blood flow sequence was anatomically accurate (model did well with domain knowledge)
5. Zone coordinate positioning was unrealistic (model over-simplified geometry)

### Actionable Feedback
- For Baseline 1: Add explicit requirement to include ALL optional fields
- For Baseline 2: Request accessibility + performance as Phase 1, not Phase 3
- For both: Provide anatomical reference + coordinate system explanation upfront
```

---

## FAQ

**Q: How long does generation take?**  
A: Baseline 1 (~5-10 min for blueprint, ~2 min for model to generate)  
A: Baseline 2 (~15-30 min for full code, ~5-10 min for model to generate)

**Q: Can I use these prompts with other models (GPT-4, Mistral)?**  
A: Yes! The prompts are model-agnostic. Expect similar quality across Claude, GPT-4, and other strong models.

**Q: What if the generated code violates my design system?**  
A: Add CSS/Tailwind constraints to the prompt. Example: "Use colors from our design tokens: primary-blue (#3b82f6), primary-red (#ef4444), etc."

**Q: Can I extend Baseline 2 to multiple scenes?**  
A: Yes. Add to the prompt: "Extend the game to 3 scenes: (1) Label parts, (2) Identify blood flow direction, (3) Trace the complete circulatory path."

**Q: How do I ensure anatomical accuracy?**  
A: Include a reference table in the prompt. Example:
```
Blood flow sequence (MUST be exact):
1. Deoxygenated blood arrives at right atrium from body (via vena cava)
2. Blood moves to right ventricle
3. [... continue for all 10 steps]
```

**Q: What if the model hallucinates a non-existent component?**  
A: Add a constraint: "Do NOT use any components not listed in the 'Available Components' section. If you need a component not listed, explain why and ask before using it."

---

## Further Resources

- **TypeScript Docs**: https://www.typescriptlang.org/docs/
- **React Hooks**: https://react.dev/reference/react/hooks
- **Tailwind CSS**: https://tailwindcss.com/docs
- **Zustand**: https://github.com/pmndrs/zustand
- **Drag-and-Drop**: https://developer.mozilla.org/en-US/docs/Web/API/HTML5_Drag_and_Drop_API
- **SVG Reference**: https://developer.mozilla.org/en-US/docs/Web/SVG

---

## Summary

You now have everything needed to:

1. ✅ **Generate a schema-driven game (Baseline 1)** — Test Claude Code's infrastructure utilization
2. ✅ **Generate a from-scratch game (Baseline 2)** — Test Claude Code's raw coding ability
3. ✅ **Evaluate quality** — Using detailed rubrics and metrics
4. ✅ **Iterate & improve** — Using structured refinement techniques
5. ✅ **Compare performance** — Across baselines and variations

Good luck with your benchmark! Document your findings and share them with your team.

---

**Generated**: February 12, 2026  
**Location**: `/GamifyAssessment/docs/`  
**Files**:
- `BENCHMARK_BASELINE_1_INFRASTRUCTURE_AWARE.md`
- `BENCHMARK_BASELINE_2_FROM_SCRATCH.md`
- `BENCHMARK_CLAUDE_CODE_CONSTRAINTS_AND_LIMITATIONS.md`
- `README_BENCHMARK_GUIDE.md` (this file)
