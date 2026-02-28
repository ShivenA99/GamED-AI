"""
Gemini Service for HAD v3 (Hierarchical Agentic DAG)

Provides direct Gemini API calls for:
1. Zone Detection with polygon output and self-validation
2. Unified Game Design with visual context
3. Blueprint Generation with structured output
4. Model selection per task (cost optimization)

Model Selection (January 2026):
- gemini-2.5-flash-lite: Fast routing, validation ($0.10/1M in, $0.40/1M out)
- gemini-2.5-flash: Zone detection, vision ($0.30/1M in, $2.50/1M out)
- gemini-3-flash: Complex reasoning, game design ($0.50/1M in, $3.00/1M out)
- gemini-2.5-pro: Reserved for critical failures ($1.25/1M in, $10.00/1M out)

Requires: GOOGLE_API_KEY in environment

Usage:
    from app.services.gemini_service import get_gemini_service, GeminiModel

    service = get_gemini_service()

    # Zone detection with polygon output
    result = await service.detect_zones_with_polygons(
        image_path="/path/to/diagram.png",
        canonical_labels=["petal", "stamen", "pistil"],
        relationships=[{"parent": "flower", "children": ["petal", "stamen"]}],
    )

    # Unified game design
    result = await service.design_game(
        image_path="/path/to/diagram.png",
        zones=[...],
        pedagogical_context={...},
    )
"""

import asyncio
import base64
import io
import json
import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from PIL import Image
from pydantic import BaseModel, Field

logger = logging.getLogger("gamed_ai.services.gemini")


class GeminiModel(str, Enum):
    """Available Gemini models with cost tiers."""
    FLASH_LITE = "gemini-2.5-flash-lite-preview-06-17"  # Fast, cheap
    FLASH = "gemini-2.5-flash"  # Balanced, vision capable
    FLASH_3 = "gemini-3-flash-preview"  # Complex reasoning
    PRO = "gemini-2.5-pro"  # Premium quality


# Cost per 1M tokens (January 2026 pricing)
MODEL_COSTS = {
    GeminiModel.FLASH_LITE: {"input": 0.10, "output": 0.40},
    GeminiModel.FLASH: {"input": 0.30, "output": 2.50},
    GeminiModel.FLASH_3: {"input": 0.50, "output": 3.00},
    GeminiModel.PRO: {"input": 1.25, "output": 10.00},
}


@dataclass
class GeminiCallMetrics:
    """Metrics for a single Gemini API call."""
    call_id: str
    model: str
    task: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_ms: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    estimated_cost_usd: float = 0.0
    success: bool = False
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "call_id": self.call_id,
            "model": self.model,
            "task": self.task,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_ms": self.duration_ms,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "estimated_cost_usd": self.estimated_cost_usd,
            "success": self.success,
            "error": self.error,
        }


class ZoneShape(str, Enum):
    """Supported zone shape types."""
    POLYGON = "polygon"
    CIRCLE = "circle"
    ELLIPSE = "ellipse"
    RECT = "rect"


class Zone(BaseModel):
    """Zone detection result with polygon support."""
    id: str
    label: str
    shape: ZoneShape = ZoneShape.POLYGON
    points: Optional[List[List[float]]] = None  # For polygon: [[x1,y1], [x2,y2], ...]
    x: Optional[float] = None  # For circle/ellipse/rect: center x
    y: Optional[float] = None  # For circle/ellipse/rect: center y
    radius: Optional[float] = None  # For circle
    width: Optional[float] = None  # For ellipse/rect
    height: Optional[float] = None  # For ellipse/rect
    center: Optional[Dict[str, float]] = None  # Computed center for polygon
    hierarchy_level: int = 1  # 1=main, 2=child, 3+=nested
    parent_zone_id: Optional[str] = None
    confidence: float = 0.9
    hint: Optional[str] = None
    visible: bool = True


class ZoneGroup(BaseModel):
    """Hierarchical zone grouping."""
    parent_zone_id: str
    child_zone_ids: List[str]
    relationship_type: str  # "composed_of", "contains", "subdivided_into", "has_part"


class ZoneDetectionResult(BaseModel):
    """Result from zone detection with validation."""
    zones: List[Zone]
    zone_groups: List[ZoneGroup] = []
    validation: Dict[str, Any] = {}
    collision_metadata: Dict[str, Any] = {}
    parts_not_found: List[str] = []
    image_description: str = ""


class GameDesignResult(BaseModel):
    """Result from unified game design."""
    game_plan: Dict[str, Any]
    scene_structure: Dict[str, Any]
    scene_assets: Dict[str, Any]
    scene_interactions: Dict[str, Any]
    game_sequence: Optional[Dict[str, Any]] = None  # For multi-scene
    is_multi_scene: bool = False


class GeminiService:
    """
    Unified Gemini service for HAD v3 pipeline.

    Features:
    - Direct vision calls with polygon zone detection
    - Model selection per task (cost optimization)
    - Self-validation in prompts (reduces retries)
    - Token tracking and cost estimation
    """

    # Telemetry directory
    TELEMETRY_DIR = Path("pipeline_outputs/gemini_telemetry")

    def __init__(self):
        self.api_key = os.environ.get("GOOGLE_API_KEY")
        if not self.api_key:
            logger.warning("GOOGLE_API_KEY not set - Gemini calls will fail")

        self._client = None
        self._call_history: List[GeminiCallMetrics] = []

        # Ensure telemetry directory exists
        self.TELEMETRY_DIR.mkdir(parents=True, exist_ok=True)

    def _get_client(self):
        """Lazy-load the Gemini client."""
        if self._client is None:
            if not self.api_key:
                raise ValueError("GOOGLE_API_KEY environment variable not set")
            try:
                from google import genai
                self._client = genai.Client(api_key=self.api_key)
                logger.info("Gemini client initialized successfully")
            except ImportError:
                raise ImportError("google-genai package not installed. Run: pip install google-genai")
        return self._client

    def _generate_call_id(self, task: str) -> str:
        """Generate unique call ID."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        return f"{task}_{timestamp}"

    def _calculate_cost(self, model: GeminiModel, input_tokens: int, output_tokens: int) -> float:
        """Calculate estimated cost in USD."""
        costs = MODEL_COSTS.get(model, {"input": 0, "output": 0})
        return (input_tokens / 1_000_000 * costs["input"]) + (output_tokens / 1_000_000 * costs["output"])

    def _save_telemetry(self, metrics: GeminiCallMetrics):
        """Save telemetry to file and history."""
        self._call_history.append(metrics)

        telemetry_file = self.TELEMETRY_DIR / f"{metrics.call_id}.json"
        with open(telemetry_file, "w") as f:
            json.dump(metrics.to_dict(), f, indent=2)

        logger.info(
            f"Gemini API: {metrics.task} | Model: {metrics.model} | "
            f"Duration: {metrics.duration_ms}ms | Cost: ${metrics.estimated_cost_usd:.4f}"
        )

    def _load_image(self, image_path: str) -> "Image.Image":
        """Load image from path or URL."""
        if image_path.startswith("http://") or image_path.startswith("https://"):
            import io
            import urllib.request
            req = urllib.request.Request(image_path, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                return Image.open(io.BytesIO(resp.read()))
        return Image.open(image_path)

    def _parse_json_response(self, response_text: str) -> Dict[str, Any]:
        """Parse JSON from response, handling markdown code blocks."""
        cleaned = response_text.strip()

        # Remove markdown code blocks
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            # Remove first line (```json or ```)
            lines = lines[1:]
            # Remove last line if it's just ```
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            cleaned = "\n".join(lines)

        # Handle nested code blocks
        if "```json" in cleaned:
            start = cleaned.find("```json") + 7
            end = cleaned.rfind("```")
            if end > start:
                cleaned = cleaned[start:end]

        return json.loads(cleaned)

    async def detect_zones_with_polygons(
        self,
        image_path: str,
        canonical_labels: List[str],
        relationships: Optional[List[Dict[str, Any]]] = None,
        query_intent: Optional[Dict[str, Any]] = None,
        model: GeminiModel = GeminiModel.FLASH,
    ) -> ZoneDetectionResult:
        """
        Detect zones with polygon boundaries using Gemini Vision.

        This is the core zone detection for HAD v3 - returns polygons instead of circles
        for precise boundary detection.

        Args:
            image_path: Path to the diagram image
            canonical_labels: Labels to detect
            relationships: Hierarchical relationships between labels
            query_intent: Query context for detection strategy
            model: Gemini model to use (default: FLASH for vision)

        Returns:
            ZoneDetectionResult with polygon zones and validation
        """
        call_id = self._generate_call_id("detect_zones_polygon")
        metrics = GeminiCallMetrics(
            call_id=call_id,
            model=model.value,
            task="detect_zones_polygon",
            started_at=datetime.now(),
        )

        # Build hierarchy context for prompt
        hierarchy_context = self._build_hierarchy_context(relationships or [])

        # Load prompt template
        prompt = self._build_zone_detection_prompt(
            canonical_labels=canonical_labels,
            hierarchy_context=hierarchy_context,
            query_intent=query_intent or {},
        )

        try:
            client = self._get_client()
            from google.genai import types

            img = self._load_image(image_path)

            start_time = time.time()

            response = client.models.generate_content(
                model=model.value,
                contents=[prompt, img],
                config=types.GenerateContentConfig(
                    temperature=0.1,  # Low for precision
                    response_mime_type="application/json",
                )
            )

            metrics.duration_ms = int((time.time() - start_time) * 1000)
            metrics.completed_at = datetime.now()

            # Parse response
            response_text = response.text if hasattr(response, 'text') else str(response)
            logger.info(f"Gemini zone detection raw response ({len(response_text)} chars): {response_text}")
            result = self._parse_json_response(response_text)
            logger.info(f"Parsed zones: {len(result.get('zones', []))}, groups: {len(result.get('zone_groups', []))}")

            # Log parts_not_found if any
            if result.get("parts_not_found"):
                logger.warning(f"Parts not found: {result.get('parts_not_found')}")
            if result.get("image_description"):
                logger.info(f"Image description: {result.get('image_description')}")

            # Extract token counts if available
            if hasattr(response, 'usage_metadata'):
                metrics.input_tokens = getattr(response.usage_metadata, 'prompt_token_count', 0)
                metrics.output_tokens = getattr(response.usage_metadata, 'candidates_token_count', 0)

            metrics.estimated_cost_usd = self._calculate_cost(model, metrics.input_tokens, metrics.output_tokens)
            metrics.success = True
            self._save_telemetry(metrics)

            # Convert to Zone objects
            zones = []
            for z in result.get("zones", []):
                zone = Zone(
                    id=z.get("id", f"zone_{z.get('label', '').lower().replace(' ', '_')}"),
                    label=z.get("label", ""),
                    shape=ZoneShape(z.get("shape", "polygon")),
                    points=z.get("points"),
                    x=z.get("x") if z.get("shape") != "polygon" else None,
                    y=z.get("y") if z.get("shape") != "polygon" else None,
                    radius=z.get("radius"),
                    width=z.get("width"),
                    height=z.get("height"),
                    center=z.get("center"),
                    hierarchy_level=z.get("hierarchyLevel", z.get("hierarchy_level", 1)),
                    parent_zone_id=z.get("parentZoneId", z.get("parent_zone_id")),
                    confidence=z.get("confidence", 0.9),
                    hint=z.get("hint"),
                    visible=z.get("visible", True),
                )

                # Compute center for polygon if not provided
                if zone.shape == ZoneShape.POLYGON and zone.points and not zone.center:
                    xs = [p[0] for p in zone.points]
                    ys = [p[1] for p in zone.points]
                    zone.center = {
                        "x": sum(xs) / len(xs),
                        "y": sum(ys) / len(ys),
                    }

                zones.append(zone)

            # Convert zone groups
            zone_groups = []
            for g in result.get("zone_groups", []):
                zone_groups.append(ZoneGroup(
                    parent_zone_id=g.get("parentZoneId", g.get("parent_zone_id", "")),
                    child_zone_ids=g.get("childZoneIds", g.get("child_zone_ids", [])),
                    relationship_type=g.get("relationshipType", g.get("relationship_type", "contains")),
                ))

            return ZoneDetectionResult(
                zones=zones,
                zone_groups=zone_groups,
                validation=result.get("validation", {}),
                collision_metadata=self._calculate_collision_metadata(zones),
                parts_not_found=result.get("parts_not_found", []),
                image_description=result.get("image_description", ""),
            )

        except Exception as e:
            metrics.completed_at = datetime.now()
            metrics.error = str(e)
            metrics.success = False
            self._save_telemetry(metrics)

            logger.error(f"Zone detection failed: {e}")
            raise

    def _build_hierarchy_context(self, relationships: List[Dict[str, Any]]) -> str:
        """Build hierarchy context string for zone detection prompt."""
        if not relationships:
            return "No hierarchical relationships provided."

        lines = ["Hierarchical Relationships:"]
        for rel in relationships:
            parent = rel.get("parent", "")
            children = rel.get("children", [])
            rel_type = rel.get("relationship_type", "contains")

            if rel_type in ("composed_of", "subdivided_into"):
                lines.append(f"  - {parent} is COMPOSED OF (layered): {', '.join(children)}")
                lines.append(f"    → Children are LAYERS within parent - overlapping is expected")
            else:
                lines.append(f"  - {parent} CONTAINS (discrete): {', '.join(children)}")
                lines.append(f"    → Children are SEPARATE parts - should NOT overlap")

        return "\n".join(lines)

    def _build_zone_detection_prompt(
        self,
        canonical_labels: List[str],
        hierarchy_context: str,
        query_intent: Dict[str, Any],
    ) -> str:
        """Build the zone detection prompt with polygon requirements."""

        labels_str = json.dumps(canonical_labels)

        return f"""You are an expert diagram analyzer for educational labeling games.

## INPUT
- Image: [attached]
- Labels to detect: {labels_str}
- {hierarchy_context}
- Query intent: {json.dumps(query_intent)}

## OUTPUT FORMAT
Return JSON with zones for ALL labels. POLYGON format is REQUIRED.

### Zone Schema
{{
  "zones": [
    {{
      "id": "zone_label_name",
      "label": "Human-readable Label",
      "shape": "polygon",
      "points": [
        [x1, y1],
        [x2, y2],
        [x3, y3]
      ],
      "center": {{
        "x": centroid_x,
        "y": centroid_y
      }},
      "hierarchyLevel": 1,
      "parentZoneId": null,
      "confidence": 0.95,
      "hint": "Short hint for learners",
      "visible": true
    }}
  ],
  "zone_groups": [
    {{
      "parentZoneId": "parent_zone",
      "childZoneIds": ["child1", "child2"],
      "relationshipType": "composed_of"
    }}
  ],
  "validation": {{
    "all_labels_found": true,
    "discrete_overlaps": 0,
    "parent_child_containment": true,
    "centers_inside_polygons": true
  }},
  "parts_not_found": [],
  "image_description": "Brief description of the diagram"
}}

## POLYGON REQUIREMENTS

1. **Trace actual boundaries** - NOT bounding boxes
   - Follow the visual contour of each structure
   - 6-12 points for simple shapes
   - 12-20 points for complex irregular shapes

2. **Point ordering** - Clockwise from top-left

3. **Coordinate format** - Percentage (0-100) of image dimensions
   - x: percentage from left edge
   - y: percentage from top edge

4. **Center validation** - Center MUST be geometrically inside polygon
   - Calculate centroid
   - If centroid is outside (concave shape), find interior point

5. **Relationship-aware detection**
   - `composed_of` / `subdivided_into`: Children may overlap (layers)
   - `contains` / `has_part`: Children must NOT overlap (discrete)
   - Parent zones must encompass all children

6. **Self-validation before returning**
   - Count detected zones vs expected labels
   - Check discrete zone pairs for overlap
   - Verify parent contains all children
   - Ensure all centers are inside their polygons

## HIERARCHY LEVELS
Based on reveal order (pedagogical sequence):
- Level 1: Main structures (shown first)
- Level 2: Direct children
- Level 3+: Deeper nested structures

Return ONLY valid JSON, no markdown code blocks or explanation."""

    def _calculate_collision_metadata(self, zones: List[Zone]) -> Dict[str, Any]:
        """Calculate collision/overlap metadata for zones."""
        overlaps = []

        for i, zone_a in enumerate(zones):
            for zone_b in zones[i + 1:]:
                # Simple bounding box overlap check
                if zone_a.shape == ZoneShape.POLYGON and zone_b.shape == ZoneShape.POLYGON:
                    if zone_a.points and zone_b.points:
                        a_xs = [p[0] for p in zone_a.points]
                        a_ys = [p[1] for p in zone_a.points]
                        b_xs = [p[0] for p in zone_b.points]
                        b_ys = [p[1] for p in zone_b.points]

                        # Bounding box intersection
                        if (max(a_xs) > min(b_xs) and min(a_xs) < max(b_xs) and
                            max(a_ys) > min(b_ys) and min(a_ys) < max(b_ys)):
                            overlaps.append({
                                "zone_a": zone_a.id,
                                "zone_b": zone_b.id,
                                "type": "bounding_box_overlap",
                            })

        return {
            "total_zones": len(zones),
            "polygon_zones": sum(1 for z in zones if z.shape == ZoneShape.POLYGON),
            "overlapping_pairs": overlaps,
            "discrete_overlaps": len(overlaps),
        }

    async def design_game(
        self,
        image_path: str,
        zones: List[Zone],
        zone_groups: List[ZoneGroup],
        pedagogical_context: Dict[str, Any],
        domain_knowledge: Dict[str, Any],
        needs_multi_scene: bool = False,
        model: GeminiModel = GeminiModel.FLASH_3,
    ) -> GameDesignResult:
        """
        Unified game design with visual context.

        Replaces: game_orchestrator + game_planner + scene_stage1/2/3

        Single Gemini call returns complete game design:
        - game_plan: Game mechanics and objectives
        - scene_structure: Layout and regions
        - scene_assets: Visual asset specifications
        - scene_interactions: Behaviors and animations
        - game_sequence: Multi-scene progression (if needed)

        Args:
            image_path: Path to diagram image (provides visual context)
            zones: Detected zones from zone_planner
            zone_groups: Zone groupings
            pedagogical_context: Bloom's level, subject, etc.
            domain_knowledge: Canonical labels, relationships
            needs_multi_scene: Whether multi-scene design is needed
            model: Gemini model (default: FLASH_3 for complex reasoning)

        Returns:
            GameDesignResult with complete game design
        """
        call_id = self._generate_call_id("design_game")
        metrics = GeminiCallMetrics(
            call_id=call_id,
            model=model.value,
            task="design_game",
            started_at=datetime.now(),
        )

        prompt = self._build_game_design_prompt(
            zones=zones,
            zone_groups=zone_groups,
            pedagogical_context=pedagogical_context,
            domain_knowledge=domain_knowledge,
            needs_multi_scene=needs_multi_scene,
        )

        try:
            client = self._get_client()
            from google.genai import types

            img = self._load_image(image_path)

            start_time = time.time()

            response = client.models.generate_content(
                model=model.value,
                contents=[prompt, img],
                config=types.GenerateContentConfig(
                    temperature=0.3,  # Slightly higher for creativity
                    response_mime_type="application/json",
                )
            )

            metrics.duration_ms = int((time.time() - start_time) * 1000)
            metrics.completed_at = datetime.now()

            response_text = response.text if hasattr(response, 'text') else str(response)
            result = self._parse_json_response(response_text)

            if hasattr(response, 'usage_metadata'):
                metrics.input_tokens = getattr(response.usage_metadata, 'prompt_token_count', 0)
                metrics.output_tokens = getattr(response.usage_metadata, 'candidates_token_count', 0)

            metrics.estimated_cost_usd = self._calculate_cost(model, metrics.input_tokens, metrics.output_tokens)
            metrics.success = True
            self._save_telemetry(metrics)

            return GameDesignResult(
                game_plan=result.get("game_plan", {}),
                scene_structure=result.get("scene_structure", {}),
                scene_assets=result.get("scene_assets", {}),
                scene_interactions=result.get("scene_interactions", {}),
                game_sequence=result.get("game_sequence"),
                is_multi_scene=result.get("is_multi_scene", needs_multi_scene),
            )

        except Exception as e:
            metrics.completed_at = datetime.now()
            metrics.error = str(e)
            metrics.success = False
            self._save_telemetry(metrics)

            logger.error(f"Game design failed: {e}")
            raise

    def _build_game_design_prompt(
        self,
        zones: List[Zone],
        zone_groups: List[ZoneGroup],
        pedagogical_context: Dict[str, Any],
        domain_knowledge: Dict[str, Any],
        needs_multi_scene: bool,
    ) -> str:
        """Build the unified game design prompt."""

        zones_json = json.dumps([z.model_dump() for z in zones], indent=2)
        groups_json = json.dumps([g.model_dump() for g in zone_groups], indent=2)

        blooms_level = pedagogical_context.get("blooms_level", "UNDERSTAND")
        subject = pedagogical_context.get("subject", "Biology")

        multi_scene_instruction = ""
        if needs_multi_scene:
            multi_scene_instruction = """
## MULTI-SCENE DESIGN
Design multiple scenes with progressive reveal:
1. Scene 1: Main structures (hierarchy level 1)
2. Scene 2: Child structures (hierarchy level 2)
3. Scene 3+: Deeper structures as needed

Include scene transitions with animation type:
- "fade": Simple fade between scenes
- "zoom_in": Zoom into focused area
- "slide": Slide transition
- "reveal": Progressive reveal animation
"""

        return f"""You are an expert educational game designer specializing in anatomy and biology.

## TASK
Design a complete INTERACTIVE_DIAGRAM game using the provided diagram and detected zones.

## INPUT
- Image: [attached diagram - use for visual context]
- Detected Zones: {zones_json}
- Zone Groups: {groups_json}
- Bloom's Level: {blooms_level}
- Subject: {subject}
- Domain Knowledge: {json.dumps(domain_knowledge, indent=2)}
- Multi-Scene Required: {needs_multi_scene}

{multi_scene_instruction}

## OUTPUT FORMAT
Return a single JSON object with ALL of these sections:

{{
  "game_plan": {{
    "title": "Game title",
    "objectives": ["Learning objective 1", "Learning objective 2"],
    "mechanics": {{
      "type": "drag_and_drop",
      "interactions": ["drag", "drop", "reveal"],
      "feedback_mode": "immediate",
      "scoring": {{
        "correct": 10,
        "incorrect": -5,
        "hint_penalty": -2
      }}
    }},
    "difficulty": {{
      "level": "intermediate",
      "time_limit": null,
      "hints_available": 3
    }},
    "completion_criteria": {{
      "required_correct": 0.8,
      "bonus_objectives": []
    }}
  }},

  "scene_structure": {{
    "theme": "scientific_clean",
    "layout": {{
      "diagram_area": {{"x": 10, "y": 10, "width": 60, "height": 80}},
      "label_bank": {{"x": 75, "y": 10, "width": 20, "height": 80}}
    }},
    "regions": [
      {{
        "id": "main_diagram",
        "type": "diagram_display",
        "bounds": {{"x": 10, "y": 10, "width": 60, "height": 80}}
      }},
      {{
        "id": "label_bank",
        "type": "draggable_labels",
        "bounds": {{"x": 75, "y": 10, "width": 20, "height": 80}}
      }}
    ]
  }},

  "scene_assets": {{
    "background": {{"type": "solid", "color": "#ffffff"}},
    "diagram": {{
      "source": "provided_image",
      "display_mode": "fit_contain"
    }},
    "labels": [
      {{
        "id": "label_petal",
        "text": "Petal",
        "zone_id": "zone_petal",
        "style": {{"font_size": 14, "color": "#333333"}}
      }}
    ],
    "drop_zones": [
      {{
        "id": "drop_petal",
        "zone_id": "zone_petal",
        "accepts": ["label_petal"],
        "visual": {{"highlight_color": "#4CAF50", "indicator": "dotted_outline"}}
      }}
    ]
  }},

  "scene_interactions": {{
    "drag_behavior": {{
      "snap_to_zone": true,
      "return_on_wrong": true,
      "magnetic_radius": 15
    }},
    "feedback": {{
      "correct": {{"animation": "pulse_green", "sound": "success"}},
      "incorrect": {{"animation": "shake_red", "sound": "error"}}
    }},
    "hints": {{
      "type": "zone_highlight",
      "trigger": "button_click",
      "progressive": true
    }},
    "completion": {{
      "animation": "confetti",
      "show_results": true,
      "allow_retry": true
    }}
  }}

  {"," if needs_multi_scene else ""}
  {'"game_sequence": ' + '{"scenes": [...], "progression_type": "linear", "transitions": [...]}' if needs_multi_scene else ""}
}}

## DESIGN GUIDELINES

1. **Bloom's Level Alignment**
   - REMEMBER: Simple identification, minimal hints
   - UNDERSTAND: Include hints with relationships
   - APPLY: Add problem-solving elements
   - ANALYZE: Require comparison between structures

2. **Visual Design**
   - Clean, uncluttered layout
   - High contrast for accessibility
   - Clear visual feedback on interactions

3. **Pedagogical Progression**
   - Start with obvious structures
   - Progress to challenging ones
   - Use zone_groups for logical grouping

4. **Zone Integration**
   - Each zone becomes a drop target
   - Each label links to exactly one zone
   - Validate all zone_ids exist in provided zones

Return ONLY valid JSON, no markdown or explanation."""

    async def generate_text(
        self,
        prompt: str,
        model: GeminiModel = GeminiModel.FLASH_LITE,
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> Tuple[str, GeminiCallMetrics]:
        """
        Generate text using Gemini (no vision).

        For simple tasks like routing, validation, etc.

        Args:
            prompt: Text prompt
            model: Gemini model (default: FLASH_LITE for speed)
            temperature: Generation temperature
            max_tokens: Maximum output tokens

        Returns:
            Tuple of (response_text, metrics)
        """
        call_id = self._generate_call_id("generate_text")
        metrics = GeminiCallMetrics(
            call_id=call_id,
            model=model.value,
            task="generate_text",
            started_at=datetime.now(),
        )

        try:
            client = self._get_client()
            from google.genai import types

            start_time = time.time()

            response = client.models.generate_content(
                model=model.value,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=temperature,
                    max_output_tokens=max_tokens,
                )
            )

            metrics.duration_ms = int((time.time() - start_time) * 1000)
            metrics.completed_at = datetime.now()

            response_text = response.text if hasattr(response, 'text') else str(response)

            if hasattr(response, 'usage_metadata'):
                metrics.input_tokens = getattr(response.usage_metadata, 'prompt_token_count', 0)
                metrics.output_tokens = getattr(response.usage_metadata, 'candidates_token_count', 0)

            metrics.estimated_cost_usd = self._calculate_cost(model, metrics.input_tokens, metrics.output_tokens)
            metrics.success = True
            self._save_telemetry(metrics)

            return response_text, metrics

        except Exception as e:
            metrics.completed_at = datetime.now()
            metrics.error = str(e)
            metrics.success = False
            self._save_telemetry(metrics)

            logger.error(f"Text generation failed: {e}")
            raise

    def get_call_history(self) -> List[Dict[str, Any]]:
        """Get history of all API calls."""
        return [m.to_dict() for m in self._call_history]

    def get_total_cost(self) -> float:
        """Get total estimated cost of all calls."""
        return sum(m.estimated_cost_usd for m in self._call_history)

    def get_token_summary(self) -> Dict[str, int]:
        """Get total token usage summary."""
        return {
            "total_input_tokens": sum(m.input_tokens for m in self._call_history),
            "total_output_tokens": sum(m.output_tokens for m in self._call_history),
            "total_tokens": sum(m.input_tokens + m.output_tokens for m in self._call_history),
            "num_calls": len(self._call_history),
        }


# Singleton instance
_service: Optional[GeminiService] = None


def get_gemini_service() -> GeminiService:
    """Get the singleton Gemini service instance."""
    global _service
    if _service is None:
        _service = GeminiService()
    return _service
