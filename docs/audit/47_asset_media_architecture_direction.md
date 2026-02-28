# 47. Asset & Media Architecture — Current State, Gaps, and Direction

**Date**: 2026-02-17
**Context**: Before fixing the assembler bugs (BUG-A through BUG-I), we need to rethink how assets and media flow through the pipeline, because the current asset pipeline is too narrow.

---

## Current State: 3 Layers of Assets/Media

### Layer 1: Diagram Assets (per-scene, zone-based)

**What exists:**
- `asset_send_router` dispatches `asset_worker` per scene where `needs_diagram=True`
- `asset_worker` does: Serper image search → Gemini Flash zone detection → SAM3 polygon refinement
- Produces: `{scene_id, diagram_url, zones: [{id, label, points}], match_quality}`
- Assembler maps diagram + zones into `diagram.assetUrl`, `diagram.zones[]`, `labels[]`
- All zone-based mechanics in a scene share the ONE diagram and its zones

**What works:**
- Zone-based mechanics (drag_drop, description_matching, trace_path, click_to_identify) all correctly consume the shared diagram/zones through `label_to_zone_id` mapping
- Per-mechanic configs correctly spread zone references into their own structures (e.g., `paths[].waypoints[].zoneId`, `descriptionMatchingConfig.descriptions[zone_id]`)

**What's missing:**
- `ImageSpec` has `style`, `annotation_preference`, `color_direction`, `spatial_guidance` — but `asset_worker._search_image()` only uses `description` and `must_include_structures`. Creative direction is dropped at the asset level.

### Layer 2: Per-Item Media (per-mechanic-item)

**What the backend schemas already support:**

| Mechanic | Schema | Image/Media Fields | Status |
|----------|--------|-------------------|--------|
| sequencing | `SequenceItemInput` | `image_url: Optional[str]`, `image_description: Optional[str]`, `icon: str` | Fields exist but never populated with actual URLs |
| memory_match | `MemoryPairInput` | `frontType: "text"\|"image"`, `backType: "text"\|"image"`, `front: str`, `back: str` | frontType/backType always "text", never "image" |
| branching | `DecisionNodeInput` | `image_description: Optional[str]`, `narrative_text: str` | image_description exists but no agent generates actual image URL |
| drag_drop | `DragDropContent` | `label_style: str` (supports "text_with_icon", "text_with_thumbnail") | Always "text", never "text_with_thumbnail" |
| sorting | `SortingItemInput` | No image field in schema | Missing entirely — frontend `SortingItem` has `image?: string` |

**The gap:** Content generator can produce `image_description` text, but there is NO agent that converts descriptions into actual image URLs. The pipeline ends with descriptions pointing to nothing.

**What the frontend already renders:**

| Mechanic | Frontend Component | Media Rendering |
|----------|-------------------|----------------|
| sequencing | `EnhancedSequenceBuilder` | `card_type: "image_with_caption"` → renders `item.image` as `<img>` + text below |
| sequencing | Same | `card_type: "icon_and_text"` → renders `item.icon` emoji + text |
| memory_match | `EnhancedMemoryMatch` | `card.type === 'image'` → renders `card.content` as `<img>` |
| branching | `BranchingScenario` | `node.imageUrl` → renders as `<img>` if present |
| sorting | `EnhancedSortingCategories` | `item_card_type: "image_with_caption"` → renders `item.image` |
| drag_drop | `EnhancedDragDropGame` | `label_style: "text_with_thumbnail"` → renders `label.thumbnail_url` as 40x40px img |
| drag_drop | Same | `label_style: "text_with_icon"` → renders `label.icon` emoji |

### Layer 3: Visual Config (per-mechanic styling)

**What the creative design captures:**

`MechanicCreativeDesign` has:
- `card_type: str` — "text_only", "image_with_caption", "icon_and_text", etc.
- `layout_mode: str` — "vertical_list", "flowchart", "grid", etc.
- `connector_style: str` — "arrow", "curved", "dotted", etc.
- `visual_style: str` — creative description of look/feel
- `color_direction: str` — color palette guidance
- `needs_item_images: bool` — flag that this mechanic needs per-item images
- `item_image_style: Optional[str]` — style guidance for item images

**What flows through:**

The content generator schemas have matching fields that the assembler correctly spreads into blueprint configs. For example:
- `DragDropContent` has 16 visual config fields → all flow through to `dragDropConfig`
- `SequencingContent` has `card_type`, `layout_mode`, `connector_style` → flow through to `sequenceConfig`
- `MemoryMatchContent` has `card_back_style`, `matched_card_behavior`, etc.

**What's dropped (BUG-H):** Content generator prompt doesn't inject `color_direction`, `instruction_tone`, `narrative_hook`, `difficulty_curve` from creative design.

---

## The Gap: No Item-Level Asset Agent

The pipeline has a clear structural gap:

```
Scene Designer → "this mechanic needs item images" (needs_item_images=True)
     │
Content Generator → "here are items with image_description text"
     │
     ▼
  ??? NOTHING ??? → No agent converts image_description → actual image URL
     │
     ▼
Assembler → items have image_description but image_url=null
     │
     ▼
Frontend → card_type="image_with_caption" but no image to show
```

The existing `asset_worker` only handles **scene-level diagrams for zone detection**. It cannot:
- Generate/search per-item images (sequencing step illustrations, memory card images)
- Generate label thumbnails for drag_drop
- Generate node images for branching scenarios
- Generate category images for sorting

---

## Direction: Reorganized Asset Architecture

### Principle: Creative Design Decides, Content Describes, Assets Generate

```
┌─────────────────────────────────────────────────────────────────┐
│ Scene Designer (LLM)                                            │
│ Decides FOR EACH MECHANIC:                                      │
│   needs_diagram: bool        — scene needs a diagram image      │
│   needs_item_images: bool    — items need individual images     │
│   item_image_style: str      — "realistic photo" / "icon" / etc│
│   card_type: str             — "image_with_caption" / "text"   │
│   label_style: str           — "text_with_thumbnail" / "text"  │
│   match_type: str            — "image_to_label" / "term_to_def"│
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│ Content Generator (LLM, per-mechanic)                           │
│ Produces content WITH image_description when instructed:        │
│   sequencing: items[].image_description = "heart in diastole"   │
│   memory: pairs[].frontType = "image",                          │
│           pairs[].front = "image:cell_membrane_diagram"         │
│   branching: nodes[].image_description = "patient showing..."   │
│   drag_drop: labels with icon/description fields                │
│   sorting: items with image_description                         │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│ Asset Pipeline (expanded)                                       │
│                                                                 │
│ 1. DIAGRAM ASSET WORKER (existing, per-scene)                   │
│    For needs_diagram=True scenes:                               │
│    Image search → Gemini zone detection → SAM3 refinement       │
│    Produces: diagram_url + zones[]                              │
│                                                                 │
│ 2. ITEM ASSET WORKER (NEW, per-mechanic)                        │
│    For needs_item_images=True mechanics:                        │
│    Reads image_description from content items                   │
│    Generates/searches images per item                           │
│    Writes image_url back into content items                     │
│    Produces: updated content items with resolved image URLs     │
│                                                                 │
│ Strategy options for item images:                               │
│   a. Serper image search (fast, free, but less control)         │
│   b. AI image generation (slow, costly, but precise)            │
│   c. Icon/emoji mapping (instant, for card_type="icon_and_text")│
│   d. Sprite sheet generation (batch, for memory_match grids)    │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│ Assembler (deterministic)                                       │
│ Wires ALL assets into blueprint:                                │
│   diagram.assetUrl + diagram.zones[] (existing)                 │
│   sequenceConfig.items[].image (NEW from item asset worker)     │
│   memoryMatchConfig.pairs[].front = image_url (NEW)             │
│   labels[].thumbnail_url (NEW)                                  │
│   branchingConfig.nodes[].imageUrl (NEW)                        │
│   sortingConfig.items[].image (NEW)                             │
│   + all visual config fields from creative design               │
└─────────────────────────────────────────────────────────────────┘
```

### What Changes at Each Level

#### Game Concept Designer
- No changes needed. Already outputs the WHAT (mechanic choices, learning goals).

#### Scene Creative Designer
- Already has `needs_item_images` and `item_image_style` on `MechanicCreativeDesign`.
- **Needs prompt update**: Ensure the scene designer actually USES these fields. Currently it may default `needs_item_images=False` always. The prompt should consider the mechanic type and learning context to decide:
  - Sequencing about a visual process → `needs_item_images=True, card_type="image_with_caption"`
  - Memory match of terms vs definitions → `needs_item_images=False, card_type="text_only"`
  - Memory match of structures vs names → `needs_item_images=True, match_type="image_to_label"`
  - Drag_drop with simple text labels → `needs_item_images=False, label_style="text"`
  - Drag_drop where labels are cell types → `needs_item_images=True, label_style="text_with_thumbnail"`

#### Content Generator
- **Needs prompt update**: When `needs_item_images=True`, the content generator prompt should instruct the LLM to:
  - Fill `image_description` on each item (sequencing, sorting)
  - Set `frontType: "image"` and write descriptive `front` text for image search (memory_match)
  - Fill `image_description` on branching nodes
- The content schemas already support all these fields — no schema changes needed.

#### Asset Pipeline (NEW: Item Asset Worker)
- New `item_asset_worker` node after content_merge, before interaction_designer
- Reads: mechanic contents where `needs_item_images=True`
- For each item with `image_description`:
  - Searches for image (Serper) or generates (AI)
  - Writes resolved `image_url` back
- Writes: updated `mechanic_contents` with image URLs populated
- Falls back gracefully: if image not found, keeps `image_url=null` and logs warning

#### Assembler
- Already spreads content fields into blueprint configs.
- Needs: `image` field mapped for sorting items (missing from `SortingItemInput` schema).
- The rest should flow through automatically once content items have `image_url` populated.

---

## Implementation Status (Updated 2026-02-17)

### NOW (fix the broken pipeline): ✅ ALL DONE

1. ✅ **BUG-B** (P0): `_resolve_transition_types()` converts mechanic IDs → types
2. ✅ **BUG-C/D/E/F** (P1): `_scene_to_game_scene()` rewritten with all fields
3. ✅ **BUG-I** (P1): `instruction_text` propagated to mechanic config
4. ✅ **BUG-A** (P2): `advance_trigger_value` wired through graph_builder
5. ✅ **BUG-G** (P2): Game-level fields added to blueprint root + game_sequence

### NEXT (creative config propagation): ✅ ALL DONE

6. ✅ **BUG-H**: 7 creative design fields + 4 scene context fields added to content generator prompt
7. ✅ `card_type`, `label_style`, `layout_mode` flow through content schemas → blueprint
8. ✅ Silent fallbacks removed across 7 routers + merge_nodes + assembler_node

### FUTURE (item-level assets): ✅ ALL DONE

9. ✅ `item_asset_worker` node added to graph (between content_merge and interaction_dispatch)
10. ✅ Scene designer prompt updated with `needs_item_images` decision guidance
11. ✅ Content generator prompts updated for sequencing, branching, memory_match, sorting
12. ✅ `image` + `image_description` fields added to `SortingItemInput` schema
13. ✅ Item asset worker writes correct frontend field names:
    - sequencing: `item.image` (not image_url)
    - branching: `node.imageUrl` (camelCase)
    - memory_match: replaces `pair.front` with URL (card.content in frontend)
    - sorting: `item.image`

### Remaining lower-priority gaps:

- `asset_worker._search_image()` doesn't use ImageSpec's `style`, `annotation_preference` fields (only matters for AI generation, not Serper search)
- `drag_drop` label thumbnails (`label_style: "text_with_thumbnail"`) not generated by any agent — would need a separate thumbnail worker
- `compare_contrast` dual-diagram support not fully tested

---

## Per-Mechanic Asset Matrix (Complete)

| Mechanic | Scene Diagram | Zone Detection | Item Images | Config Style Fields |
|----------|:---:|:---:|:---:|:---:|
| drag_drop | Yes | Yes | Optional (thumbnails) | label_style, tray_position, leader_line_style, 12+ more |
| description_matching | Yes | Yes | No | mode, description_panel_position, show_connecting_lines |
| trace_path | Yes | Yes | No | particleTheme, particleSpeed, drawing_mode, path_type, 5+ more |
| click_to_identify | Yes | Yes | No | prompt_style, selection_mode, highlight_style, 4+ more |
| sequencing | No | No | Optional (step illustrations) | card_type, layout_mode, interaction_pattern, connector_style, 2+ more |
| sorting_categories | No | No | Optional (item images) | item_card_type, sort_mode, container_style, 3+ more |
| memory_match | No | No | Optional (card images) | match_type, card_back_style, matched_card_behavior, game_variant, 4+ more |
| branching_scenario | No | No | Optional (node images) | narrative_structure, show_path_taken, allow_backtrack, 2+ more |
| compare_contrast | Yes (×2) | Yes (×2) | No | comparison_mode, highlight_matching, zoom_enabled, 3+ more |

---

## Key Invariant: Creative Design Is the Source of Truth

The scene designer's `MechanicCreativeDesign` is the single source of truth for:
1. **What media to generate** — `needs_item_images`, `item_image_style`
2. **How to display it** — `card_type`, `label_style`, `layout_mode`
3. **What content to create** — `generation_goal`, `key_concepts`, `pedagogical_focus`
4. **How it should feel** — `visual_style`, `color_direction`, `instruction_tone`, `feedback_style`

Every downstream agent should READ these fields and act on them. Nothing should be hardcoded. The assembler should NEVER inject defaults that contradict the creative design.
