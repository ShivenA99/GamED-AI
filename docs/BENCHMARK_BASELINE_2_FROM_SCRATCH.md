# BASELINE 2: From-Scratch Prompt
## "Label the Parts of the Heart and Order the Flow" – Pure React Implementation

**Objective:** Build a complete, fully-functional educational game "Label the Parts of the Heart and Order the Flow" using **only standard web technologies**. No custom game engines, no proprietary frameworks, no infrastructure dependencies.

---

## OVERVIEW

You are building an interactive educational game that teaches heart anatomy and blood flow. The game has **two distinct phases**:

1. **Phase 1: Label Identification** — Students drag anatomical labels onto a heart diagram to identify each part.
2. **Phase 2: Blood Flow Sequencing** — Students reorder the steps of blood circulation through the heart.

The game must be fully self-contained, visually polished, and pedagogically effective.

---

## TECHNICAL REQUIREMENTS

### Tech Stack (ONLY)
- **React 18** — Component framework
- **TypeScript** — Type safety
- **Tailwind CSS** — Styling
- **HTML5 Canvas** or **SVG** — For the heart diagram
- **Vanilla drag-and-drop APIs** OR a **lightweight library** (e.g., react-beautiful-dnd, @dnd-kit/core)
- **Framer Motion** (optional) — For smooth animations
- **Zustand or Context API** — For state management

### What You CAN Use
- Standard React hooks (useState, useEffect, useCallback, useRef, useMemo, useContext)
- HTML5 Drag-and-Drop API (native, no external deps required)
- CSS Flexbox / Grid
- SVG native elements
- HTML5 Canvas (with vanilla JS)
- localStorage or sessionStorage for persistence
- requestAnimationFrame for animations
- setTimeout/setInterval for timing
- Any **npm package** from popular, well-maintained sources (React ecosystem)

### What You CANNOT Use
- Custom game engines (Phaser, Babylon.js, Three.js, etc.)
- Proprietary internal components or infrastructure
- Hard-coded fixed dimensions (must be responsive)
- External game state management schemes (use Zustand or Context)
- Pre-built game templates or boilerplates

---

## FEATURE SPECIFICATION

### Phase 1: Label the Heart Parts

**Objective:** Students must drag 8 anatomical labels onto the correct regions of a heart diagram.

#### Heart Anatomy (8 Structures)
1. **Right Atrium** — Upper right chamber; receives deoxygenated blood from the body
2. **Right Ventricle** — Lower right chamber; pumps deoxygenated blood to the lungs
3. **Pulmonary Artery** — Vessel carrying blood from right ventricle to lungs
4. **Left Atrium** — Upper left chamber; receives oxygenated blood from the lungs
5. **Left Ventricle** — Lower left chamber; strongest chamber; pumps blood to the entire body
6. **Pulmonary Vein** — Carries oxygenated blood from lungs to left atrium
7. **Aorta** — Main artery; carries oxygenated blood from left ventricle to the body
8. **Vena Cava** — Large vein; brings deoxygenated blood back to the right atrium

#### Interaction UX

**Label Tray** (Bottom of screen):
- Display 8 draggable label cards (text-only or with icons)
- Include 2-3 distractor labels (e.g., "Brain", "Lung Tissue", "Liver")
- Animate labels (fade/scale) to draw attention
- Show a counter: "Correct: X/8"

**Heart Diagram** (Center/Top):
- Render a **high-quality anatomical illustration** of the heart (SVG or Canvas)
- Overlay **interactive zones** (clickable/droppable regions) for each structure
- Color-code zones subtly (light blue = deoxygenated, light red = oxygenated, gray = vessels)
- Animate zone hover states (glow, scale, highlight border)
- Show zone name on hover or when hovered

**Drop Logic**:
- Zones accept labels via drag-and-drop (HTML5 Drag API or dnd-kit)
- **Correct placement** → Label snaps to zone, plays success animation (pulse, confetti), +10 points
- **Incorrect placement** → Label bounces back with error message, -0 points (no penalty)
- **Distractor labels** → Show explanation when a distractor is attempted: "The [Distractor] is not part of the heart..."
- **Partial placement** (label dropped nearby) → Snap to nearest zone if within threshold, else bounce back

**Feedback**:
- Real-time feedback per label: "✓ Correct!" or "Try again, [Label] goes in a different location"
- Progress indicator: "3/8 labeled"
- Hint system: Click a zone to reveal hint text (e.g., "Strongest chamber; pumps blood to the body" for left ventricle)

**Phase 1 Completion**:
- When all 8 labels are correctly placed → Transition animation to Phase 2
- Display phase 1 score (e.g., "80/80 points")
- Show triumphant feedback: "Great! Now let's trace the blood flow..."

---

### Phase 2: Blood Flow Sequencing

**Objective:** Students must order the 10 steps of blood circulation through the heart.

#### Blood Flow Steps (Correct Sequence)
1. **Body (Systemic Circulation)** — Deoxygenated blood in tissues
2. **Superior/Inferior Vena Cava** — Deoxygenated blood returns to heart
3. **Right Atrium** — Receives deoxygenated blood
4. **Right Ventricle** — Pumps deoxygenated blood
5. **Pulmonary Artery** — Carries blood to lungs
6. **Lungs (Gas Exchange)** — Blood becomes oxygenated
7. **Pulmonary Vein** — Returns oxygenated blood to heart
8. **Left Atrium** — Receives oxygenated blood
9. **Left Ventricle** — Pumps oxygenated blood
10. **Aorta → Body** — Oxygenated blood distributed to body (cycle repeats)

#### Interaction UX

**Sequencing Cards** (Displayed in shuffled order):
- Render 10 reorderable cards (150-200px wide, text + optional icon)
- Display in a **horizontal timeline** or **vertical list**
- Support drag-to-reorder OR click-to-swap UI patterns
- Highlight the current order numerically (1, 2, 3, ... shown on each card)

**Visual Feedback**:
- Correct placement → Card locks in place, shows checkmark
- Total score shown at bottom: "X/10 correct"
- "Submit Order" button at the bottom

**Reordering Mechanics**:
- Drag cards left/right (timeline) or up/down (vertical list) to reorder
- Cards smoothly animate to new positions (spring physics or ease)
- Show visual connectors (arrows or lines) between cards to suggest flow

**Validation & Submission**:
- When student clicks "Submit Order":
  - Compare their order against the correct sequence
  - Calculate score: full credit for perfect order, partial credit for partially correct steps
  - Show which steps are correct (✓) and which are wrong (✗)
  - Display success/retry message

**Phase 2 Completion**:
- Show final score for Phase 2 (e.g., "18/20 points" with explanation)
- Combined score from Phase 1 + Phase 2

---

## VISUAL DESIGN

### Color Scheme
- **Deoxygenated blood (Right side)**: Light blue (#93c5fd), darker blue (#1e40af) for emphasis
- **Oxygenated blood (Left side)**: Light red (#fca5a5), darker red (#991b1b) for emphasis
- **Vessels & SA nodes**: Gray (#9ca3af)
- **Background**: White or light gray (#f9fafb)
- **Accent colors**: Green (#10b981) for correct, Red (#ef4444) for errors
- **Text**: Dark gray (#1f2937) or black

### Typography
- **Title**: Large, bold (e.g., 32px, font-bold)
- **Phase instructions**: Medium, readable (18-24px)
- **Label text**: 14-16px, clear and easy to read
- **Feedback messages**: 16px, color-coded (green for correct, orange/red for feedback)

### Responsive Design
- **Desktop (1024px+)**: Full-size diagram (500-600px), tray below or to the right
- **Tablet (768px-1023px)**: Medium diagram (400px), labels in responsive grid
- **Mobile (< 768px)**: Stacked layout, smaller diagram (250-300px), labels in vertical stack
- All interactive zones scale proportionally

### Animations
- **Label drag**: Slight scale-up (1.05x), shadow beneath label
- **Correct placement**: Pulse animation (1.0 → 1.15 → 1.0 over 600ms), confetti particles, green checkmark
- **Incorrect placement**: Shake animation (left ↔ right), quick red X icon, bounce back to tray
- **Distractor label**: Tooltip/popover explanation appears on hover/attempt
- **Zone hover**: Subtle glow, border highlight, name tooltip
- **Phase transition**: Fade out Phase 1, 500ms pause, fade in Phase 2 with intro text
- **Card reordering**: Smooth slide animation (spring physics, 400-600ms)

---

## COMPONENT STRUCTURE

```
App.tsx (Main container)
├── Header (title, instructions, progress)
├── ScoreDisplay (current score, target score)
├── Phase1Container (Phase 1 logic)
│   ├── HeartDiagram (SVG/Canvas rendering)
│   │   ├── DiagramBase (heart illustration)
│   │   ├── InteractiveZones (draggable regions)
│   │   └── ZoneHints (hover tooltips)
│   ├── LabelTray (draggable labels)
│   │   ├── LabelCard (individual label)
│   │   ├── DistractorLabel (wrong answer with explanation)
│   │   └── ProgressCounter (X/8 labels placed)
│   └── FeedbackPanel (success/error messages)
├── TransitionCard (Phase 1 → Phase 2 animation)
├── Phase2Container (Phase 2 logic)
│   ├── InstructionPanel ("Order the blood flow...")
│   ├── SequenceCardsDisplay (reorderable list/timeline)
│   │   ├── SequenceCard (draggable reorderable item)
│   │   └── Connectors (visual arrows between cards)
│   ├── SubmitButton
│   └── ResultsPanel (score breakdown)
└── GameResults (overall score, certificate, replay button)
```

---

## State Management

Use **Zustand** (recommended) or **Context API** to manage:

```typescript
interface GameState {
  // Phase 1: Labeling
  phase: 'intro' | 'phase1' | 'transition' | 'phase2' | 'results';
  placedLabels: {
    labelId: string;
    zoneId: string;
    isCorrect: boolean;
  }[];
  phase1Score: number;
  phase1MaxScore: number;

  // Phase 2: Sequencing
  sequenceOrder: string[];  // Current order (mutable during reordering)
  correctSequenceOrder: string[];  // Expected order (immutable)
  phase2Score: number;
  phase2MaxScore: number;

  // UI state
  selectedHintZoneId: string | null;
  showFeedback: boolean;
  feedbackMessage: string;
  feedbackColor: 'green' | 'red' | 'info';

  // Actions
  placeLabel: (labelId: string, zoneId: string) => void;
  removeLabel: (labelId: string) => void;
  updateSequenceOrder: (newOrder: string[]) => void;
  submitSequence: () => void;
  toggleHint: (zoneId: string) => void;
  restartGame: () => void;
  nextPhase: () => void;
}
```

---

## Data Model

### Labels (Phase 1)

```typescript
interface Label {
  id: string;  // unique identifier
  text: string;  // display name
  correctZoneId: string;  // zone where it should be placed
  icon?: string;  // optional emoji (e.g., "❤️")
  category?: 'chamber' | 'vessel';  // for visual grouping
}

const LABELS: Label[] = [
  { id: 'label_1', text: 'Right Atrium', correctZoneId: 'zone_ra', category: 'chamber' },
  { id: 'label_2', text: 'Right Ventricle', correctZoneId: 'zone_rv', category: 'chamber' },
  // ... 6 more
];

const DISTRACTORS: Label[] = [
  { id: 'distractor_1', text: 'Brain', explanation: 'The brain is not part of the heart...' },
  { id: 'distractor_2', text: 'Lung Tissue', explanation: 'The lungs connect to the heart...' },
];
```

### Zones (Interactive Regions)

```typescript
interface Zone {
  id: string;  // unique identifier
  label: string;  // display name
  x: number;  // center X in percentage (0-100)
  y: number;  // center Y in percentage (0-100)
  width: number;  // zone width (% or px)
  height: number;  // zone height (% or px)
  shape: 'circle' | 'polygon' | 'rect';  // interaction shape
  points?: [number, number][];  // polygon coordinates if shape='polygon'
  color: 'blue' | 'red' | 'gray';  // for visual coding (deoxy/oxy/vessel)
  hint: string;  // hint text revealed on click/hover
  description: string;  // full description shown on correct placement
}

const ZONES: Zone[] = [
  { id: 'zone_ra', label: 'Right Atrium', x: 25, y: 30, width: 80, height: 60, shape: 'circle', color: 'blue', hint: 'Upper right chamber', description: 'Receives deoxygenated blood from the body.' },
  // ... 7 more
];
```

### Blood Flow Sequence (Phase 2)

```typescript
interface SequenceItem {
  id: string;  // unique identifier
  text: string;  // display text
  icon?: string;  // optional emoji
  description?: string;  // pedagogical explanation
}

const BLOOD_FLOW_SEQUENCE: SequenceItem[] = [
  { id: 'seq_1', text: 'Body (Systemic Circulation)', icon: '🫀' },
  { id: 'seq_2', text: 'Superior/Inferior Vena Cava', icon: '🩸' },
  // ... 8 more in correct order
];
```

---

## Implementation Details

### Heart Diagram Rendering

**Option A: SVG (Recommended for accuracy)**
- Use an anatomically correct SVG of the heart (can be sourced from Wikimedia Commons, custom created, or AI-generated)
- Render using React `<svg>` elements
- Overlay interactive zones as `<circle>` or `<polygon>` elements with `onDragOver`, `onDrop` handlers
- Style zones with low opacity, animate on hover

**Option B: Canvas**
- Use HTML5 Canvas API to draw the heart (programmatically or from image background)
- Track interactive zones with coordinate math (point-in-polygon detection)
- Redraw on drag events to show visual feedback

**Option C: Image + Overlay Divs**
- Use a static heart image (PNG/JPG) as background
- Absolutely position transparent `<div>` elements for each zone
- Attach drag listeners to divs

**Recommendation**: Use **SVG** for accuracy and scalability. Include color coding (light blue left, light red right) for oxygenation clarity.

### Drag-and-Drop Implementation

**Option A: Native HTML5 Drag API**
```typescript
// Label card
<div draggable={true} onDragStart={(e) => setDraggedLabel(e.target.id)}>
  {label.text}
</div>

// Zone drop area
<div onDragOver={(e) => e.preventDefault()} onDrop={(e) => handleDrop(e, zone.id)}>
  {/* zone visual */}
</div>
```

**Option B: @dnd-kit Library** (more polished)
```typescript
import { DndContext, DragEndEvent } from '@dnd-kit/core';

<DndContext onDragEnd={handleDragEnd}>
  <Draggable id={label.id}>
    <LabelCard {...label} />
  </Draggable>
  <Droppable id={zone.id}>
    <ZoneOverlay {...zone} />
  </Droppable>
</DndContext>
```

### Collision & Snap Logic

When a label is dropped near a zone:
1. Calculate distance from drop point to nearest zone
2. If distance < threshold (e.g., 50px):
   - Snap label to zone center
   - Trigger placement validation
3. If distance > threshold:
   - Bounce label back to tray

```typescript
const snapLabelToZone = (labelPos, nearestZone) => {
  const dx = labelPos.x - nearestZone.centerX;
  const dy = labelPos.y - nearestZone.centerY;
  const distance = Math.sqrt(dx * dx + dy * dy);
  
  if (distance < SNAP_THRESHOLD) {
    return {
      x: nearestZone.centerX,
      y: nearestZone.centerY,
      snappedToZone: nearestZone.id,
    };
  }
  return null;  // Bounce back
};
```

### Scoring Logic

**Phase 1**:
- 10 points per correct label placement
- 0 points for incorrect (no penalty, just no credit)
- Max: 80 points (8 labels × 10)

**Phase 2**:
- Check submitted sequence against correct order
- Scoring method:
  - **Perfect order**: 20 points
  - **Partial credit**: Points for each correct consecutive pair (e.g., 4-5 correct pairs = 16 points out of 20)
  - Alternative: Points per correctly placed item: 2 points × 10 items = 20 points
- Formula: `correctItems / totalItems × maxPoints`

**Total**: 80 + 20 = 100 points max

### Persistence (Optional)

Save game state to localStorage:
```typescript
const saveGameState = (state: GameState) => {
  localStorage.setItem('game_state', JSON.stringify(state));
};

const loadGameState = (): GameState | null => {
  const saved = localStorage.getItem('game_state');
  return saved ? JSON.parse(saved) : null;
};
```

Allow students to resume incomplete games on return.

---

## Accessibility Requirements

1. **Keyboard Navigation**:
   - Tab through all interactive elements
   - Space/Enter to select or place labels
   - Arrow keys to reorder sequence items

2. **Screen Reader Support**:
   - ARIA labels on all zones and labels
   - Feedback messages announced via `aria-live`
   - Instructions read aloud

3. **Color Contrast**:
   - Text color: dark gray or black on light backgrounds (WCAG AA minimum)
   - Zone colors: sufficient contrast between blue and red regions

4. **Font Size**:
   - Minimum 14px for body text
   - 18px+ for important labels

5. **Animation Preferences**:
   - Respect `prefers-reduced-motion` media query
   - Disable confetti/particles for users with vestibular disorders

---

## Edge Cases & Error Handling

1. **Label placed multiple times**: Only keep the most recent placement; remove from tray until dropped correctly
2. **Zone drops zone**: Invalid (disallow); provide feedback
3. **Empty sequence submission**: Flash warning; don't accept
4. **Refresh/reload during game**: Restore from localStorage (if implemented)
5. **Mobile touch support**: Use Touch Events API (touchstart, touchmove, touchend) alongside drag API
6. **Zoom/scale issues**: Use `event.clientX/Y` and account for canvas `getBoundingClientRect()`

---

## Success Criteria

When a student completes the game:

1. ✅ All 8 labels correctly placed (visual + score confirmation)
2. ✅ Blood flow sequence ordered correctly (visual + score confirmation)
3. ✅ Final score displayed: "88/100 points" (example)
4. ✅ Celebratory feedback: "Excellent! You've mastered the heart!"
5. ✅ Certificate/badge shown (optional): "You've earned the 'Heart Master' badge!"
6. ✅ Replay button visible: "Play Again"

---

## Example Deliverables

### File Structure
```
src/
├── components/
│   ├── HeartDiagram.tsx
│   ├── LabelTray.tsx
│   ├── InteractiveZone.tsx
│   ├── SequenceCard.tsx
│   ├── FeedbackPanel.tsx
│   ├── ResultsPanel.tsx
│   └── GameContainer.tsx
├── hooks/
│   ├── useGameState.ts (Zustand store or Context)
│   └── useDragDrop.ts (shared drag-drop logic)
├── data/
│   ├── labels.ts
│   ├── zones.ts
│   └── bloodFlow.ts
├── styles/
│   ├── globals.css
│   └── animations.css
├── assets/
│   ├── heart-diagram.svg
│   └── icons/
└── App.tsx
```

### Sample Component (HeartDiagram.tsx)

```tsx
import React, { useState } from 'react';
import { useGameState } from '../hooks/useGameState';
import { ZONES } from '../data/zones';

interface HeartDiagramProps {
  onDragOver: (e: React.DragEvent, zoneId: string) => void;
  onDrop: (e: React.DragEvent, zoneId: string) => void;
  placedLabels: Record<string, string>;  // zoneId -> labelId
}

export const HeartDiagram: React.FC<HeartDiagramProps> = ({
  onDragOver,
  onDrop,
  placedLabels,
}) => {
  const [hoveredZoneId, setHoveredZoneId] = useState<string | null>(null);

  return (
    <div className="flex justify-center items-center w-full h-full bg-gray-50 rounded-lg p-4">
      <svg width="500" height="500" viewBox="0 0 500 500" className="drop-shadow-lg">
        {/* Heart diagram SVG path or image background */}
        <image href="/heart-diagram.svg" width="500" height="500" />

        {/* Interactive zones */}
        {ZONES.map((zone) => (
          <g
            key={zone.id}
            onDragOver={(e) => {
              e.preventDefault();
              onDragOver(e, zone.id);
            }}
            onDrop={(e) => onDrop(e, zone.id)}
            onMouseEnter={() => setHoveredZoneId(zone.id)}
            onMouseLeave={() => setHoveredZoneId(null)}
            className="cursor-drop"
          >
            {/* Visual feedback circle */}
            <circle
              cx={zone.x}
              cy={zone.y}
              r={zone.width / 2}
              fill={zone.color === 'blue' ? '#dbeafe' : '#fecaca'}
              opacity={hoveredZoneId === zone.id ? 0.5 : 0.2}
              className="transition-opacity duration-200"
            />

            {/* Zone label (on hover) */}
            {hoveredZoneId === zone.id && (
              <text
                x={zone.x}
                y={zone.y}
                textAnchor="middle"
                dominantBaseline="middle"
                className="text-sm font-semibold fill-gray-800 pointer-events-none"
              >
                {zone.label}
              </text>
            )}

            {/* Placed label indicator */}
            {placedLabels[zone.id] && (
              <g>
                <circle
                  cx={zone.x}
                  cy={zone.y}
                  r={zone.width / 2 + 5}
                  fill="none"
                  stroke="#10b981"
                  strokeWidth="3"
                  className="animate-pulse"
                />
                <text
                  x={zone.x}
                  y={zone.y + zone.width}
                  textAnchor="middle"
                  className="text-xs fill-green-600 font-bold pointer-events-none"
                >
                  ✓
                </text>
              </g>
            )}
          </g>
        ))}
      </svg>
    </div>
  );
};
```

---

## Testing Recommendations

1. **Unit Tests**: Scoring logic, collision detection, sequence validation
2. **Integration Tests**: Drag-and-drop flow, phase transitions, state persistence
3. **E2E Tests**: Complete game flow (label → sequence → results)
4. **Accessibility Tests**: Keyboard navigation, screen reader compatibility, WCAG compliance
5. **Performance Tests**: Smooth 60fps animations, no jank on drag, responsive under load

---

## Additional Notes

- **Educational Efficacy**: Research shows interactive games improve retention by 40-60% vs. static flashcards.
- **Pedagogical Flow**: Label identification (recognition memory) → Blood flow ordering (recall + procedural memory) matches Bloom's taxonomy progression.
- **Engagement**: Scoring, progress indicators, and celebratory feedback maintain learner motivation.
- **Reusability**: The component structure allows easy adaptation for other anatomical systems (respiratory, skeletal, etc.).

---

## Summary

You now have a **complete specification** for building "Label the Parts of the Heart and Order the Flow" from scratch using only:
- React 18 + TypeScript
- Tailwind CSS
- Standard drag-and-drop APIs
- SVG for diagram rendering
- Zustand for state management

**Success Metric**: A fully functional, visually polished, pedagogically sound educational game that runs in the browser with no external dependencies beyond the React ecosystem.

**Your task**: Write clean, well-organized React code that implements this specification. The final deliverable should be a production-ready game component that can be embedded in any React app.
