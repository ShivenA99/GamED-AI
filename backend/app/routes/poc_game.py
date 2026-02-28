"""POC Game API Routes

Serves the pre-generated POC Interactive Diagram game data and assets.
"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pathlib import Path
import json

router = APIRouter(prefix="/poc-game", tags=["poc-game"])

# Directory containing POC data
POC_DIR = Path(__file__).parent.parent.parent / "pipeline_outputs" / "poc_flower_game"


@router.get("/blueprint")
async def get_poc_blueprint():
    """Get the POC game blueprint in frontend-compatible format."""
    blueprint_file = POC_DIR / "game_blueprint.json"

    if not blueprint_file.exists():
        raise HTTPException(status_code=404, detail="POC blueprint not found")

    try:
        with open(blueprint_file, "r") as f:
            data = json.load(f)

        # Transform the data to match InteractiveDiagramBlueprint format
        # The frontend expects specific structure
        zones = []
        for zone in data.get("zones", []):
            # Convert width/height to radius (use average)
            width = zone.get("width", 10)
            height = zone.get("height", 10)
            radius = (width + height) / 4  # Average divided by 2

            zones.append({
                "id": zone["id"],
                "label": zone["label"],
                "x": zone["x"],
                "y": zone["y"],
                "radius": radius,
                "description": zone.get("hint", ""),
            })

        # Build labels from the data
        labels = []
        for label_data in data.get("labels", []):
            labels.append({
                "id": label_data["id"],
                "text": label_data["text"],
                "correctZoneId": label_data["zone_id"],
            })

        # Determine interaction mode (hierarchical if zoneGroups present)
        raw_interaction_mode = data.get("interactionMode") or ""
        raw_zone_groups = data.get("zoneGroups", [])

        # Use hierarchical mode if zoneGroups are defined
        interaction_mode = raw_interaction_mode if raw_zone_groups else raw_interaction_mode

        # Determine task type based on interaction mode
        task_type = "hierarchical_label" if interaction_mode == "hierarchical" else "interactive_diagram"
        task_question = (
            "Label the main parts of the flower. Click on parent parts to reveal their sub-components."
            if interaction_mode == "hierarchical"
            else "Drag each label to the correct part of the flower."
        )

        # Build the blueprint in frontend format
        blueprint = {
            "templateType": "INTERACTIVE_DIAGRAM",
            "title": data.get("title", "Parts of a Flower"),
            "narrativeIntro": data.get("educational_content", {}).get("description",
                "Learn to identify the parts of a flower by dragging labels to the correct locations."),
            "diagram": {
                "assetPrompt": "Flower anatomy diagram",
                "assetUrl": "/api/poc-game/image",  # Backend serves the image
                "width": data.get("diagram", {}).get("width", 800),
                "height": data.get("diagram", {}).get("height", 600),
                "zones": zones,
            },
            "labels": labels,
            "tasks": [
                {
                    "id": "task_label_all",
                    "type": task_type,
                    "questionText": task_question,
                    "requiredToProceed": True,
                }
            ],
            "interactionMode": interaction_mode,
            "zoneGroups": raw_zone_groups,
            "animationCues": {
                "correctPlacement": "pulse",
                "incorrectPlacement": "shake",
                "allLabeled": "confetti",
            },
            "hints": [
                {"zoneId": zone["id"], "hintText": zone.get("hint", "")}
                for zone in data.get("zones", [])
                if zone.get("hint")
            ],
            "feedbackMessages": {
                "perfect": "Excellent! You correctly labeled all parts of the flower!",
                "good": "Good job! You identified most flower parts correctly.",
                "retry": "Keep trying! Use the hints to help identify each part.",
            },
        }

        return blueprint
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading blueprint: {str(e)}")


@router.get("/image")
async def get_poc_image():
    """Serve the cleaned diagram image."""
    image_file = POC_DIR / "diagram_cleaned.png"

    if not image_file.exists():
        raise HTTPException(status_code=404, detail="Diagram image not found")

    return FileResponse(
        image_file,
        media_type="image/png",
        headers={"Cache-Control": "max-age=3600"}
    )


@router.get("/raw-data")
async def get_raw_poc_data():
    """Get the raw POC data for debugging."""
    blueprint_file = POC_DIR / "game_blueprint.json"

    if not blueprint_file.exists():
        raise HTTPException(status_code=404, detail="POC data not found")

    with open(blueprint_file, "r") as f:
        return json.load(f)
