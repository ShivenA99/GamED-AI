# Rich Demo Games — Asset Generation & Full Frontend Showcase

**Date**: 2026-02-12
**Context**: Phase A components are built (6 enhanced mechanics). Now we need rich, image-based demo games that showcase each mechanic at its best, using real generated/searched assets, rendered through the actual game frontend (`/game/[id]`) with scoring, feedback, and completion.

**APIs available**: GOOGLE_API_KEY (Gemini vision + Imagen) + SERPER_API_KEY (web image search)

---

## Architecture

### What We're Building

1. **Asset Generation Service** — Reusable module for searching/generating/caching game assets
2. **Demo Game Creator Script** — Creates 6 rich demo games (one per mechanic), inserts into DB
3. **Demo Gallery Page** — Frontend page listing all demo games with thumbnails
4. **Each game renders via `/game/[id]`** → InteractiveDiagramGame → MechanicRouter → Enhanced components

### Data Flow

```
Script (create_demo_games.py)
  ├─ Serper image search → find educational diagrams/illustrations
  ├─ Download & cache → backend/assets/demo/{mechanic}/
  ├─ Gemini vision → detect zones on diagram images
  ├─ Build rich blueprint JSON (exercises ALL component features)
  └─ Insert into DB: Question + Process(completed) + Visualization(blueprint)
       ↓
Frontend: /game/{process_id}
  ├─ Polls /api/status/{id} → sees "completed"
  ├─ Fetches blueprint from DB
  └─ Renders InteractiveDiagramGame with full scoring/feedback
```

---

## Step 1: Asset Generation Service

**File**: `backend/app/services/demo_asset_service.py`

A utility module with these functions:

```python
class DemoAssetService:
    async def search_educational_image(topic: str, style: str = "diagram") -> str:
        """Search Serper for educational images, score by quality, download best."""
        # Uses existing image_retrieval.py scoring logic
        # Filters: wikimedia, nih.gov, khanacademy, .edu preferred
        # Returns: local file path (cached in backend/assets/demo/)

    async def search_item_images(items: list[str], category: str) -> dict[str, str]:
        """Search for individual item images (for sequencing/sorting/memory cards)."""
        # One search per item, downloads best result
        # Returns: {item_name: local_file_path}

    async def detect_zones(image_path: str, expected_labels: list[str]) -> list[Zone]:
        """Use Gemini vision to detect zone positions on a diagram image."""
        # Calls gemini_service.detect_zones_with_polygons()
        # Returns: list of zones with id, label, x, y, radius, shape

    async def generate_image(prompt: str, filename: str) -> str:
        """Generate an image via Gemini Imagen (with fallback to search)."""
        # Try: google.generativeai Imagen 3
        # Fallback: Serper image search for the prompt
        # Returns: local file path
```

**Key files to reuse**:
- `backend/app/services/image_retrieval.py` — `ImageRetrievalService.search_images()`, scoring logic
- `backend/app/services/gemini_service.py` — `detect_zones_with_polygons()`
- `backend/app/services/gemini_diagram_service.py` — Gemini diagram operations

**Asset storage**: `backend/assets/demo/{mechanic_name}/` — served via existing `/api/assets/` proxy

---

## Step 2: Demo Game Creator Script

**File**: `backend/scripts/create_demo_games.py`

```bash
cd backend && PYTHONPATH=. python scripts/create_demo_games.py [--mechanic drag_drop]
```

For each mechanic, the script:
1. Calls DemoAssetService to get/generate images
2. Builds a complete InteractiveDiagramBlueprint JSON
3. Inserts into DB (Question + Process + Visualization)
4. Prints the game URL: `http://localhost:3000/game/{process_id}`

---

## Step 3: Six Demo Games (Mechanic by Mechanic)

### Game 1: drag_drop — "Human Heart Anatomy"

**Educational goal**: Label the chambers, valves, and vessels of the heart
**Image source**: Serper search for "human heart anatomy diagram labeled educational"
**Zone detection**: Gemini vision on the found diagram

**Blueprint features exercised**:
- `dragDropConfig.leader_line_style: 'curved'` — curved leader lines
- `dragDropConfig.label_style: 'text_with_description'` — labels show function text
- `dragDropConfig.tray_layout: 'grouped'` — labels grouped by category
- `dragDropConfig.tray_show_categories: true` — "Chambers", "Valves", "Vessels" groups
- `dragDropConfig.placement_animation: 'spring'` — spring physics snap
- `dragDropConfig.show_placement_particles: true` — sparkles on correct
- `dragDropConfig.zoom_enabled: true` — zoom into dense areas
- `dragDropConfig.show_distractors: true` — 2 distractor labels
- `dragDropConfig.pin_marker_shape: 'circle'` — pin markers at zone anchors
- 8 labels: Right Atrium, Left Atrium, Right Ventricle, Left Ventricle, Aorta, Pulmonary Artery, Tricuspid Valve, Mitral Valve
- 2 distractors: "Coronary Sinus" (with explanation), "Pericardium" (with explanation)
- Categories: Chambers (4), Valves (2), Vessels (2)
- Hints per zone with educational content
- `scoringStrategy: { type: 'per_zone', base_points_per_zone: 10, max_score: 80 }`

---

### Game 2: sequencing — "Blood Flow Through the Heart"

**Educational goal**: Order the steps of blood circulation through the heart
**Image source**: Individual step illustrations via Serper (or icons)
**No diagram image needed** — sequence cards with images

**Blueprint features exercised**:
- `sequenceConfig.layout_mode: 'horizontal_timeline'`
- `sequenceConfig.card_type: 'image_and_text'` — cards with step images
- `sequenceConfig.connector_style: 'arrow'` — animated arrows between cards
- `sequenceConfig.show_position_numbers: true` — numbered positions
- `sequenceConfig.interaction_pattern: 'drag_to_reorder'`
- `sequenceConfig.instructionText` — "Arrange the steps of blood flow..."
- 6 items with images, descriptions, and icons:
  1. "Deoxygenated blood enters right atrium" (icon: "🫀")
  2. "Blood passes through tricuspid valve" (icon: "🚪")
  3. "Right ventricle pumps to lungs" (icon: "🫁")
  4. "Gas exchange in lung capillaries" (icon: "💨")
  5. "Oxygenated blood returns to left atrium" (icon: "❤️")
  6. "Left ventricle pumps to body" (icon: "💪")
- Each item has an illustration image (searched or generated)
- `sequenceType: 'cyclic'` — blood flow is a cycle

---

### Game 3: sorting_categories — "Plant vs Animal Cell Organelles"

**Educational goal**: Sort organelles into Plant Cell Only, Animal Cell Only, or Both
**Image source**: Individual organelle images via Serper
**No diagram needed** — card-based sorting

**Blueprint features exercised**:
- `sortingConfig.sort_mode: 'bucket'` — three colored buckets
- `sortingConfig.item_card_type: 'image_with_caption'` — items with organelle images
- `sortingConfig.container_style: 'bucket'` — labeled buckets with category colors
- 3 categories:
  - "Plant Cell Only" (color: #22c55e/green)
  - "Animal Cell Only" (color: #ef4444/red)
  - "Both Cells" (color: #6366f1/indigo)
- 9 items with images and descriptions:
  - Plant only: Cell Wall, Chloroplast, Central Vacuole
  - Animal only: Centrioles, Lysosomes, Flagella
  - Both: Nucleus, Mitochondria, Endoplasmic Reticulum
- Each item has difficulty rating (easy/medium/hard)
- `submit_mode: 'batch_submit'` — submit all at once, staggered reveal

---

### Game 4: memory_match — "Human Body Systems"

**Educational goal**: Match body systems to their functions
**Image source**: Organ/system images via Serper (front) + text definitions (back)
**No diagram needed** — card grid

**Blueprint features exercised**:
- `memoryMatchConfig.card_back_style: 'gradient'` — indigo→purple gradient backs
- `memoryMatchConfig.flipDurationMs: 500` — smooth 3D flip
- `memoryMatchConfig.matched_card_behavior: 'checkmark'` — green checkmark
- `memoryMatchConfig.show_explanation_on_match: true` — educational popup
- `memoryMatchConfig.match_type: 'image_to_label'`
- 6 pairs (12 cards, 4×3 grid):
  - Heart image ↔ "Pumps blood throughout the body"
  - Lungs image ↔ "Exchange of oxygen and carbon dioxide"
  - Brain image ↔ "Controls body functions and processes information"
  - Stomach image ↔ "Breaks down food with acids and enzymes"
  - Kidneys image ↔ "Filters blood and produces urine"
  - Liver image ↔ "Detoxifies blood and produces bile"
- Front: organ image (frontType: 'image'), Back: function text (backType: 'text')
- Explanation on each match (e.g., "The heart is a muscular organ that pumps...")

---

### Game 5: click_to_identify — "Parts of a Flower"

**Educational goal**: Identify flower structures from functional descriptions
**Image source**: Serper search for "flower anatomy diagram educational"
**Zone detection**: Gemini vision on flower diagram

**Blueprint features exercised**:
- `clickToIdentifyConfig.promptStyle: 'functional'` — "Click the structure that produces pollen"
- `clickToIdentifyConfig.highlightStyle: 'subtle'` — zones nearly invisible
- `clickToIdentifyConfig.magnificationEnabled: true` — zoom lens on hover
- `clickToIdentifyConfig.magnificationFactor: 2.5`
- `clickToIdentifyConfig.exploreModeEnabled: true` — explore first, then test
- `clickToIdentifyConfig.selectionMode: 'sequential'` — ordered by difficulty
- 6 zones with prompts:
  1. "Click the structure that produces pollen" → Anther (easy)
  2. "Click the colorful part that attracts pollinators" → Petal (easy)
  3. "Click the green leaf-like structures protecting the bud" → Sepal (medium)
  4. "Click the structure where pollen lands during pollination" → Stigma (medium)
  5. "Click the structure that connects stigma to the ovary" → Style (hard)
  6. "Click the structure containing the ovules" → Ovary (hard)

---

### Game 6: trace_path — "The Digestive System Journey"

**Educational goal**: Trace the path food takes through the digestive system
**Image source**: Serper search for "digestive system diagram educational labeled"
**Zone detection**: Gemini vision to find organ waypoints

**Blueprint features exercised**:
- `tracePathConfig.particleTheme: 'droplets'` — food particle animation
- `tracePathConfig.particleSpeed: 'medium'`
- `tracePathConfig.colorTransitionEnabled: true` — food changes color as digested
- `tracePathConfig.showDirectionArrows: true` — flow direction indicators
- `tracePathConfig.showWaypointLabels: true` — organ names at each stop
- `tracePathConfig.showFullFlowOnComplete: true` — full animation on completion
- `tracePathConfig.pathType: 'linear'`
- 1 path with 7 waypoints (ordered):
  1. Mouth (type: 'standard') — food enters
  2. Esophagus (type: 'standard') — muscular contractions
  3. Stomach (type: 'gate') — acid digestion gate
  4. Small Intestine (type: 'standard') — nutrient absorption
  5. Large Intestine (type: 'standard') — water absorption
  6. Rectum (type: 'standard') — waste storage
  7. End (type: 'terminus')
- Color transitions: brown→yellow→green (food→chyme→bile-mixed)

---

## Step 4: Demo Gallery Page

**File**: `frontend/src/app/demo/page.tsx`

A simple gallery page that:
1. Fetches all demo game process IDs (stored in a JSON config or from DB query)
2. Shows a card per game: mechanic icon, title, description, thumbnail
3. Links to `/game/{process_id}`
4. Badge showing mechanic type

---

## Step 5: Backend API Additions

**File**: `backend/app/routes/generate.py` (or new `demo.py`)

Add endpoint to list/serve demo games:
```python
@router.get("/demo/games")
async def list_demo_games():
    """List all demo games with their process IDs and metadata."""
```

Also ensure the existing `/api/assets/` proxy correctly serves `backend/assets/demo/` files.

---

## Execution Order

Do ONE mechanic at a time. For each:

1. **Generate assets** — Run script for that mechanic
2. **Verify assets** — Check images downloaded, zones detected
3. **Build blueprint** — Ensure all config fields populated
4. **Insert into DB** — Create Question + Process + Visualization
5. **Test in browser** — Play at `/game/{process_id}`, verify scoring/feedback/completion
6. **Fix issues** — Iterate if component doesn't render correctly
7. **Move to next mechanic**

**Order**: drag_drop → sequencing → sorting → memory_match → click_to_identify → trace_path

---

## Critical Files to Modify/Create

| Action | File | Purpose |
|--------|------|---------|
| CREATE | `backend/app/services/demo_asset_service.py` | Asset search/generate/cache utility |
| CREATE | `backend/scripts/create_demo_games.py` | Script to create all 6 demo games |
| CREATE | `frontend/src/app/demo/page.tsx` | Demo gallery page |
| MAYBE CREATE | `backend/app/routes/demo.py` | Demo games API endpoint |
| REUSE | `backend/app/services/image_retrieval.py` | Image search + scoring |
| REUSE | `backend/app/services/gemini_service.py` | Zone detection |
| REUSE | `backend/app/db/models.py` | DB models (Question, Process, Visualization) |
| REUSE | `frontend/src/app/game/[id]/page.tsx` | Game rendering (no changes needed) |
| REUSE | `frontend/src/components/templates/InteractiveDiagramGame/` | All enhanced components |

---

## Verification

For each demo game:
- [ ] Game loads at `/game/{process_id}` without errors
- [ ] Diagram/card images display (not broken/placeholder)
- [ ] All interactive elements work (drag, click, flip, reorder)
- [ ] Scoring increments correctly on correct actions
- [ ] Feedback shows (correct/incorrect animations)
- [ ] Game completes with final score screen
- [ ] Enhanced features visible (leader lines, particles, 3D flip, etc.)

Final check:
- [ ] Demo gallery page lists all 6 games
- [ ] Each game playable end-to-end with real educational content
- [ ] Asset generation script is reusable for future game topics
