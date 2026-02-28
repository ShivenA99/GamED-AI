#!/usr/bin/env python3
"""
Create 9 rich demo games — one per mechanic — with real AI-generated assets.

Every web image goes through Gemini 2.5 Flash Image for cleaning/regeneration
before use. Nothing is served directly from the web.

Usage:
    cd backend && source venv/bin/activate
    PYTHONPATH=. python scripts/create_demo_games.py [--mechanic drag_drop] [--skip-assets]

Mechanics: drag_drop, click_to_identify, sequencing, sorting_categories,
           memory_match, trace_path, description_matching, branching_scenario, compare_contrast
"""

import argparse
import asyncio
import json
import logging
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

# Setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("demo_games")
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("google_genai").setLevel(logging.WARNING)


# ─── DB helpers ───────────────────────────────────────────────────

# Track all demo game titles for cleanup
DEMO_GAME_TITLES = [
    "Human Heart Anatomy",
    "Parts of a Flower",
    "Blood Flow Through the Heart",
    "Plant vs Animal Cell Organelles",
    "Human Body Systems",
    "The Digestive System Journey",
    "The Skeletal System",
    "Emergency Room Triage",
    "Plant Cell vs Animal Cell",
]


def cleanup_old_demo_games():
    """Delete all previous demo game records from the DB."""
    from app.db.database import SessionLocal, init_db
    from app.db.models import Question, Process, Visualization

    init_db()
    session = SessionLocal()
    try:
        deleted = 0
        for title in DEMO_GAME_TITLES:
            questions = session.query(Question).filter(
                Question.text.like(f"%{title.split()[0]}%")
            ).all()
            for q in questions:
                processes = session.query(Process).filter(Process.question_id == q.id).all()
                for p in processes:
                    session.query(Visualization).filter(Visualization.process_id == p.id).delete()
                    session.delete(p)
                    deleted += 1
                session.delete(q)
        session.commit()
        if deleted:
            logger.info(f"Cleaned up {deleted} old demo game records")
    except Exception as e:
        session.rollback()
        logger.warning(f"Cleanup failed (non-fatal): {e}")
    finally:
        session.close()


def insert_demo_game(title: str, question_text: str, blueprint: dict) -> str:
    """Insert Question + Process + Visualization into DB. Returns process_id."""
    from app.db.database import SessionLocal, init_db
    from app.db.models import Question, Process, Visualization

    init_db()
    session = SessionLocal()

    try:
        # Create question
        question = Question(
            id=str(uuid.uuid4()),
            text=question_text,
        )
        session.add(question)

        # Create completed process
        process = Process(
            id=str(uuid.uuid4()),
            question_id=question.id,
            status="completed",
            progress_percent=100,
            completed_at=datetime.now(timezone.utc),
        )
        session.add(process)

        # Create visualization with blueprint
        viz = Visualization(
            id=str(uuid.uuid4()),
            process_id=process.id,
            template_type="INTERACTIVE_DIAGRAM",
            blueprint=blueprint,
        )
        session.add(viz)
        session.commit()

        logger.info(f"Inserted demo game: {title}")
        logger.info(f"  Process ID: {process.id}")
        logger.info(f"  Game URL:   http://localhost:3000/game/{process.id}")
        return process.id

    except Exception as e:
        session.rollback()
        raise
    finally:
        session.close()


# ─── Asset URL helper ─────────────────────────────────────────────

def asset_url(game_id: str, filename: str, subdir: str = "") -> str:
    """Build a /api/assets/ URL for a locally stored asset."""
    if subdir:
        return f"/api/assets/demo/{game_id}/{subdir}/{filename}"
    return f"/api/assets/demo/{game_id}/{filename}"


# ─── Game 1: drag_drop — Human Heart Anatomy ─────────────────────

async def create_drag_drop_game(svc) -> str:
    game_id = "demo_drag_drop"
    logger.info("Creating drag_drop demo: Human Heart Anatomy")

    # Generate assets
    result = await svc.generate_diagram(
        game_id=game_id,
        subject="human heart cross-section anatomy",
        structures=[
            "Right Atrium", "Left Atrium",
            "Right Ventricle", "Left Ventricle",
            "Aorta", "Pulmonary Artery",
            "Tricuspid Valve", "Mitral Valve",
        ],
        style="clean educational cross-section illustration, colorful, anatomically accurate",
    )
    zones = result["zones"]
    diagram_url = result["diagram_url"]

    # Build labels from detected zones
    labels = []
    for z in zones:
        labels.append({
            "id": f"label_{z['id']}",
            "text": z["label"],
            "correctZoneId": z["id"],
        })

    # Distractor labels
    distractors = [
        {
            "id": "distractor_coronary_sinus",
            "text": "Coronary Sinus",
            "explanation": "The coronary sinus is a vein that collects blood from the heart muscle itself, not one of the main chambers or valves.",
        },
        {
            "id": "distractor_pericardium",
            "text": "Pericardium",
            "explanation": "The pericardium is the protective sac surrounding the heart, not an internal structure visible in this cross-section.",
        },
    ]

    # Enhanced zone objects with hints and categories
    blueprint_zones = []
    category_map = {
        "Right Atrium": "Chambers", "Left Atrium": "Chambers",
        "Right Ventricle": "Chambers", "Left Ventricle": "Chambers",
        "Aorta": "Vessels", "Pulmonary Artery": "Vessels",
        "Tricuspid Valve": "Valves", "Mitral Valve": "Valves",
    }
    hints_map = {
        "Right Atrium": "This upper-right chamber receives deoxygenated blood from the body via the superior and inferior vena cava.",
        "Left Atrium": "This upper-left chamber receives oxygenated blood returning from the lungs via the pulmonary veins.",
        "Right Ventricle": "This lower-right chamber pumps deoxygenated blood to the lungs through the pulmonary artery.",
        "Left Ventricle": "The thickest-walled chamber — it pumps oxygenated blood to the entire body through the aorta.",
        "Aorta": "The largest artery in the body, carrying oxygenated blood from the left ventricle to systemic circulation.",
        "Pulmonary Artery": "The only artery that carries deoxygenated blood — from the right ventricle to the lungs.",
        "Tricuspid Valve": "Located between the right atrium and right ventricle, this valve has three leaflets.",
        "Mitral Valve": "Also called the bicuspid valve, it sits between the left atrium and left ventricle with two leaflets.",
    }

    for z in zones:
        zone_data = {
            "id": z["id"],
            "label": z["label"],
            "x": z["x"],
            "y": z["y"],
            "radius": z["radius"],
            "shape": z.get("shape", "circle"),
            "description": z.get("description", ""),
            "hint": hints_map.get(z["label"], ""),
            "zone_type": "area",
        }
        # Forward polygon data if present
        if "points" in z:
            zone_data["points"] = z["points"]
        if "center" in z:
            zone_data["center"] = z["center"]
        blueprint_zones.append(zone_data)

    hints = [{"zoneId": z["id"], "hintText": hints_map.get(z["label"], "")} for z in zones]

    blueprint = {
        "templateType": "INTERACTIVE_DIAGRAM",
        "title": "Human Heart Anatomy",
        "narrativeIntro": "The human heart is a muscular organ divided into four chambers that work together to pump blood throughout the body. Can you identify each chamber, valve, and major vessel in this cross-section?",
        "diagram": {
            "assetPrompt": "Human heart cross-section anatomy diagram",
            "assetUrl": diagram_url,
            "zones": blueprint_zones,
        },
        "labels": labels,
        "distractorLabels": distractors,
        "tasks": [{"id": "task_label", "type": "label_diagram", "questionText": "Drag each label to the correct structure on the heart diagram.", "requiredToProceed": True}],
        "interactionMode": "drag_drop",
        "mechanics": [{
            "type": "drag_drop",
            "scoring": {"strategy": "per_zone", "points_per_correct": 10, "max_score": 80, "partial_credit": False},
            "feedback": {
                "on_correct": "Correct! Well done identifying that structure.",
                "on_incorrect": "Not quite — look at the position and think about the blood flow direction.",
                "on_completion": "Excellent! You've correctly labeled all parts of the heart.",
            },
        }],
        "dragDropConfig": {
            "leader_line_style": "curved",
            "label_style": "text_with_description",
            "tray_layout": "grouped",
            "tray_show_categories": True,
            "placement_animation": "spring",
            "show_placement_particles": True,
            "zoom_enabled": True,
            "show_distractors": True,
            "pin_marker_shape": "circle",
            "feedback_timing": "immediate",
            "zone_idle_animation": "pulse",
            "zone_hover_effect": "glow",
            "shuffle_labels": True,
        },
        "scoringStrategy": {"type": "per_zone", "base_points_per_zone": 10, "max_score": 80},
        "hints": hints,
        "feedbackMessages": {
            "perfect": "Outstanding! You know the heart anatomy perfectly!",
            "good": "Good work! Review the structures you missed.",
            "retry": "Keep trying — focus on the direction of blood flow to distinguish chambers.",
        },
        "animationCues": {
            "correctPlacement": "pulse",
            "incorrectPlacement": "shake",
            "allLabeled": "confetti",
        },
    }

    return insert_demo_game("Human Heart Anatomy", "Label the parts of the human heart", blueprint)


# ─── Game 2: click_to_identify — Parts of a Flower ───────────────

async def create_click_to_identify_game(svc) -> str:
    game_id = "demo_click_identify"
    logger.info("Creating click_to_identify demo: Parts of a Flower")

    result = await svc.generate_diagram(
        game_id=game_id,
        subject="flower anatomy cross-section",
        structures=["Petal", "Sepal", "Anther", "Stigma", "Style", "Ovary"],
        style="clean botanical illustration, colorful, educational, detailed cross-section",
    )
    zones = result["zones"]
    diagram_url = result["diagram_url"]

    blueprint_zones = []
    for z in zones:
        zone_data = {
            "id": z["id"],
            "label": z["label"],
            "x": z["x"],
            "y": z["y"],
            "radius": z["radius"],
            "shape": z.get("shape", "circle"),
            "description": z.get("description", ""),
            "zone_type": "area",
        }
        if "points" in z:
            zone_data["points"] = z["points"]
        if "center" in z:
            zone_data["center"] = z["center"]
        blueprint_zones.append(zone_data)

    # Labels (needed for scoring even in click mode)
    labels = [{"id": f"label_{z['id']}", "text": z["label"], "correctZoneId": z["id"]} for z in zones]

    # Functional prompts — don't give away the answer
    prompts = [
        {"zoneId": "zone_petal", "prompt": "Click the colorful structures that attract pollinators to the flower.", "order": 1},
        {"zoneId": "zone_sepal", "prompt": "Click the green leaf-like structures that protected the flower bud before it opened.", "order": 2},
        {"zoneId": "zone_anther", "prompt": "Click the structure at the tip of the stamen where pollen grains are produced.", "order": 3},
        {"zoneId": "zone_stigma", "prompt": "Click the sticky surface at the top of the pistil where pollen grains land during pollination.", "order": 4},
        {"zoneId": "zone_style", "prompt": "Click the slender tube connecting the stigma to the ovary.", "order": 5},
        {"zoneId": "zone_ovary", "prompt": "Click the enlarged base structure that contains the ovules and develops into a fruit after fertilization.", "order": 6},
    ]
    # Filter prompts to only include zones that were actually detected
    detected_zone_ids = {z["id"] for z in zones}
    prompts = [p for p in prompts if p["zoneId"] in detected_zone_ids]

    blueprint = {
        "templateType": "INTERACTIVE_DIAGRAM",
        "title": "Parts of a Flower",
        "narrativeIntro": "Flowers are the reproductive organs of flowering plants. Each part plays a specific role in pollination and seed formation. Read each description and click the correct structure on the diagram.",
        "diagram": {
            "assetPrompt": "Flower anatomy cross-section diagram",
            "assetUrl": diagram_url,
            "zones": blueprint_zones,
        },
        "labels": labels,
        "tasks": [{"id": "task_identify", "type": "click_identify", "questionText": "Identify each flower part from its functional description.", "requiredToProceed": True}],
        "interactionMode": "click_to_identify",
        "mechanics": [{
            "type": "click_to_identify",
            "scoring": {"strategy": "per_zone", "points_per_correct": 15, "max_score": 90, "partial_credit": False},
            "feedback": {
                "on_correct": "That's right! You found the correct structure.",
                "on_incorrect": "Not quite. Re-read the description and think about the function.",
                "on_completion": "Excellent! You've identified all the parts of a flower!",
            },
        }],
        "identificationPrompts": prompts,
        "clickToIdentifyConfig": {
            "promptStyle": "functional",
            "selectionMode": "sequential",
            "highlightStyle": "subtle",
            "magnificationEnabled": True,
            "magnificationFactor": 2.5,
            "exploreModeEnabled": True,
            "exploreTimeLimitSeconds": 30,
            "showZoneCount": True,
            "instructions": "Read the description, then click the matching structure on the diagram.",
        },
        "scoringStrategy": {"type": "per_zone", "base_points_per_zone": 15, "max_score": 90},
        "feedbackMessages": {
            "perfect": "Perfect score! You're a botanical expert!",
            "good": "Good work! Review the parts you missed.",
            "retry": "Try again — pay attention to the function described in each prompt.",
        },
        "animationCues": {"correctPlacement": "glow", "incorrectPlacement": "shake", "allLabeled": "confetti"},
    }

    return insert_demo_game("Parts of a Flower", "Identify the parts of a flower from functional descriptions", blueprint)


# ─── Game 3: sequencing — Blood Flow Through the Heart ────────────

async def create_sequencing_game(svc) -> str:
    game_id = "demo_sequencing"
    logger.info("Creating sequencing demo: Blood Flow Through the Heart")

    steps = [
        {"name": "Deoxygenated blood enters right atrium", "description": "Blood returning from the body enters through the superior and inferior vena cava."},
        {"name": "Blood passes through tricuspid valve", "description": "The tricuspid valve opens to allow blood from the right atrium into the right ventricle."},
        {"name": "Right ventricle pumps to lungs", "description": "The right ventricle contracts, pushing blood through the pulmonary valve into the pulmonary artery."},
        {"name": "Gas exchange in lung capillaries", "description": "In the alveoli, carbon dioxide is released and oxygen is absorbed into the blood."},
        {"name": "Oxygenated blood returns to left atrium", "description": "Oxygen-rich blood travels back to the heart through the pulmonary veins."},
        {"name": "Left ventricle pumps to body", "description": "The left ventricle contracts powerfully, sending blood through the aortic valve into the aorta and out to the body."},
    ]

    # Generate style-consistent step illustrations
    step_images = await svc.generate_item_illustrations(
        game_id=game_id,
        items=steps,
        style="simple medical illustration showing the described process",
        category="cardiovascular system",
        aspect_ratio="4:3",
    )

    # Build sequence items
    seq_items = []
    for i, step in enumerate(steps):
        img_url = step_images.get(step["name"])
        seq_items.append({
            "id": f"step_{i}",
            "text": step["name"],
            "description": step["description"],
            "image": img_url,
            "order_index": i,
        })

    blueprint = {
        "templateType": "INTERACTIVE_DIAGRAM",
        "title": "Blood Flow Through the Heart",
        "narrativeIntro": "Blood follows a precise path through the heart in a continuous cycle. Each step must happen in the correct order for oxygen to be delivered throughout the body.",
        "diagram": {
            "assetPrompt": "Blood flow through heart diagram",
            "zones": [],
        },
        "labels": [],
        "tasks": [{"id": "task_seq", "type": "label_diagram", "questionText": "Arrange the steps of blood circulation in the correct order.", "requiredToProceed": True}],
        "interactionMode": "sequencing",
        "mechanics": [{
            "type": "sequencing",
            "scoring": {"strategy": "per_zone", "points_per_correct": 10, "max_score": 60, "partial_credit": True},
            "feedback": {
                "on_correct": "That step is in the right position!",
                "on_incorrect": "That's not quite right. Think about where blood goes next.",
                "on_completion": "You've correctly traced the path of blood through the heart!",
            },
        }],
        "sequenceConfig": {
            "sequenceType": "cyclic",
            "items": seq_items,
            "correctOrder": [f"step_{i}" for i in range(len(steps))],
            "allowPartialCredit": True,
            "instructionText": "Drag the cards to arrange the steps of blood flow in the correct order, starting from when deoxygenated blood enters the heart.",
            "layout_mode": "horizontal_timeline",
            "interaction_pattern": "drag_reorder",
            "card_type": "image_with_caption",
            "connector_style": "arrow",
            "show_position_numbers": True,
        },
        "scoringStrategy": {"type": "per_zone", "base_points_per_zone": 10, "max_score": 60, "partial_credit": True},
        "feedbackMessages": {
            "perfect": "Perfect! You understand the cardiac cycle completely!",
            "good": "Good effort! Review the steps that were out of order.",
            "retry": "Try again. Remember: body → right side → lungs → left side → body.",
        },
        "animationCues": {"correctPlacement": "pulse", "incorrectPlacement": "shake", "allLabeled": "confetti"},
    }

    return insert_demo_game("Blood Flow Through the Heart", "Arrange the steps of blood circulation in order", blueprint)


# ─── Game 4: sorting_categories — Cell Organelles ─────────────────

async def create_sorting_game(svc) -> str:
    game_id = "demo_sorting"
    logger.info("Creating sorting demo: Plant vs Animal Cell Organelles")

    items_data = [
        {"name": "Cell Wall", "description": "Rigid outer layer made of cellulose", "category": "plant_only", "difficulty": "easy"},
        {"name": "Chloroplast", "description": "Converts light energy into glucose via photosynthesis", "category": "plant_only", "difficulty": "easy"},
        {"name": "Central Vacuole", "description": "Large fluid-filled sac for storage and maintaining turgor pressure", "category": "plant_only", "difficulty": "medium"},
        {"name": "Centrioles", "description": "Cylindrical structures involved in cell division", "category": "animal_only", "difficulty": "medium"},
        {"name": "Lysosomes", "description": "Membrane-bound organelles containing digestive enzymes", "category": "animal_only", "difficulty": "medium"},
        {"name": "Flagella", "description": "Whip-like appendages used for locomotion", "category": "animal_only", "difficulty": "hard"},
        {"name": "Nucleus", "description": "Contains genetic material (DNA) and controls cell activities", "category": "both", "difficulty": "easy"},
        {"name": "Mitochondria", "description": "Powerhouse of the cell — produces ATP through cellular respiration", "category": "both", "difficulty": "easy"},
        {"name": "Endoplasmic Reticulum", "description": "Network of membranes involved in protein and lipid synthesis", "category": "both", "difficulty": "hard"},
    ]

    # Generate item images via search → Gemini regeneration
    item_images = await svc.generate_items_from_references(
        game_id=game_id,
        items=[{"name": d["name"], "description": d["description"]} for d in items_data],
        search_template="{name} cell organelle microscope illustration educational",
        regen_template="A clean scientific illustration of {name} ({description}). White background, centered, detailed, textbook quality, no text labels.",
        category="cell biology",
        transparent=True,
    )

    # Build sorting items
    sorting_items = []
    for i, item in enumerate(items_data):
        sorting_items.append({
            "id": f"item_{i}",
            "text": item["name"],
            "correctCategoryId": item["category"],
            "description": item["description"],
            "image": item_images.get(item["name"]),
            "difficulty": item["difficulty"],
        })

    categories = [
        {"id": "plant_only", "label": "Plant Cell Only", "color": "#22c55e", "description": "Organelles found exclusively in plant cells"},
        {"id": "animal_only", "label": "Animal Cell Only", "color": "#ef4444", "description": "Organelles found exclusively in animal cells"},
        {"id": "both", "label": "Both Cells", "color": "#6366f1", "description": "Organelles found in both plant and animal cells"},
    ]

    blueprint = {
        "templateType": "INTERACTIVE_DIAGRAM",
        "title": "Plant vs Animal Cell Organelles",
        "narrativeIntro": "Plant and animal cells share many organelles but each has unique structures adapted to their functions. Sort each organelle into the correct category based on whether it's found in plant cells only, animal cells only, or both.",
        "diagram": {
            "assetPrompt": "Cell organelles sorting game",
            "zones": [],
        },
        "labels": [],
        "tasks": [{"id": "task_sort", "type": "label_diagram", "questionText": "Sort each organelle into the correct category.", "requiredToProceed": True}],
        "interactionMode": "sorting_categories",
        "mechanics": [{
            "type": "sorting_categories",
            "scoring": {"strategy": "per_zone", "points_per_correct": 10, "max_score": 90, "partial_credit": False},
            "feedback": {
                "on_correct": "Correct! That organelle is in the right category.",
                "on_incorrect": "Not quite. Think about whether this organelle is unique to one cell type.",
                "on_completion": "Great job sorting all the organelles!",
            },
        }],
        "sortingConfig": {
            "items": sorting_items,
            "categories": categories,
            "allowPartialCredit": False,
            "showCategoryHints": True,
            "instructions": "Drag each organelle card into the correct category bucket. Think about the unique features of plant and animal cells.",
            "sort_mode": "bucket",
            "item_card_type": "image_with_caption",
            "container_style": "bucket",
            "submit_mode": "batch_submit",
        },
        "scoringStrategy": {"type": "per_zone", "base_points_per_zone": 10, "max_score": 90},
        "feedbackMessages": {
            "perfect": "Perfect! You know your cell biology!",
            "good": "Good effort! Review which organelles are shared vs unique.",
            "retry": "Remember: cell wall & chloroplasts are plant-exclusive, while centrioles & lysosomes are animal-exclusive.",
        },
        "animationCues": {"correctPlacement": "pulse", "incorrectPlacement": "shake", "allLabeled": "confetti"},
    }

    return insert_demo_game("Plant vs Animal Cell Organelles", "Sort organelles into plant only, animal only, or both", blueprint)


# ─── Game 5: memory_match — Human Body Systems ───────────────────

async def create_memory_match_game(svc) -> str:
    game_id = "demo_memory_match"
    logger.info("Creating memory_match demo: Human Body Systems")

    pairs_data = [
        {"name": "Heart", "function": "Pumps blood throughout the body", "explanation": "The heart is a four-chambered muscular organ that contracts ~100,000 times daily to circulate blood carrying oxygen and nutrients."},
        {"name": "Lungs", "function": "Exchange of oxygen and carbon dioxide", "explanation": "The lungs contain ~300 million alveoli providing a surface area the size of a tennis court for gas exchange."},
        {"name": "Brain", "function": "Controls body functions and processes information", "explanation": "The brain contains ~86 billion neurons and uses about 20% of the body's total energy despite being only 2% of body weight."},
        {"name": "Stomach", "function": "Breaks down food with acids and enzymes", "explanation": "The stomach produces hydrochloric acid (pH 1.5-3.5) and pepsin to begin protein digestion. Its mucus lining protects it from self-digestion."},
        {"name": "Kidneys", "function": "Filters blood and produces urine", "explanation": "Each kidney contains about 1 million nephrons that filter approximately 180 liters of blood per day, producing 1-2 liters of urine."},
        {"name": "Liver", "function": "Detoxifies blood and produces bile", "explanation": "The liver performs over 500 functions including detoxification, protein synthesis, bile production, and glycogen storage."},
    ]

    # Generate organ images via search → Gemini regeneration
    pair_images = await svc.generate_items_from_references(
        game_id=game_id,
        items=[{"name": p["name"], "description": p["function"]} for p in pairs_data],
        search_template="{name} organ anatomy educational illustration",
        regen_template="A clear educational illustration of the human {name}. Centered, colorful, white background, anatomical detail, no text labels, suitable for a game card.",
        category="human anatomy",
        subdir="pairs",
        transparent=True,
    )

    # Build memory match pairs
    mm_pairs = []
    for i, pair in enumerate(pairs_data):
        img_url = pair_images.get(pair["name"])
        mm_pairs.append({
            "id": f"pair_{i}",
            "front": img_url or pair["name"],
            "back": pair["function"],
            "frontType": "image" if img_url else "text",
            "backType": "text",
            "explanation": pair["explanation"],
            "category": "organs",
        })

    blueprint = {
        "templateType": "INTERACTIVE_DIAGRAM",
        "title": "Human Body Systems",
        "narrativeIntro": "The human body is an incredible machine with organs that each perform critical functions. Match each organ image to its function by connecting them.",
        "diagram": {
            "assetPrompt": "Human body systems memory game",
            "zones": [],
        },
        "labels": [],
        "tasks": [{"id": "task_match", "type": "label_diagram", "questionText": "Match each organ to its function.", "requiredToProceed": True}],
        "interactionMode": "memory_match",
        "mechanics": [{
            "type": "memory_match",
            "scoring": {"strategy": "per_zone", "points_per_correct": 20, "max_score": 120, "partial_credit": False},
            "feedback": {
                "on_correct": "Match found! Great job!",
                "on_incorrect": "Not a match. Remember what you've seen!",
                "on_completion": "Excellent! You matched all the organs to their functions!",
            },
        }],
        "memoryMatchConfig": {
            "pairs": mm_pairs,
            "showAttemptsCounter": True,
            "instructions": "Match each organ image to its function by connecting them. Click an organ on the left, then click its function on the right.",
            "game_variant": "column_match",
            "match_type": "image_to_label",
            "show_explanation_on_match": True,
        },
        "scoringStrategy": {"type": "per_zone", "base_points_per_zone": 20, "max_score": 120},
        "feedbackMessages": {
            "perfect": "Amazing memory! You matched everything perfectly!",
            "good": "Well done! You know your organ systems.",
            "retry": "Try again — focus on remembering card positions.",
        },
        "animationCues": {"correctPlacement": "glow", "incorrectPlacement": "fade", "allLabeled": "confetti"},
    }

    return insert_demo_game("Human Body Systems", "Match organs to their functions", blueprint)


# ─── Game 6: trace_path — Digestive System Journey ────────────────

async def create_trace_path_game(svc) -> str:
    game_id = "demo_trace_path"
    logger.info("Creating trace_path demo: The Digestive System Journey")

    waypoint_labels = ["Mouth", "Esophagus", "Stomach", "Small Intestine", "Large Intestine", "Rectum"]

    result = await svc.generate_diagram(
        game_id=game_id,
        subject="human digestive system",
        structures=waypoint_labels,
        style="clean educational illustration showing full digestive tract, colorful, anatomically accurate",
    )
    zones = result["zones"]
    diagram_url = result["diagram_url"]

    # Build zones for blueprint
    blueprint_zones = []
    for z in zones:
        zone_data = {
            "id": z["id"],
            "label": z["label"],
            "x": z["x"],
            "y": z["y"],
            "radius": z["radius"],
            "shape": z.get("shape", "circle"),
            "description": z.get("description", ""),
            "zone_type": "area",
        }
        if "points" in z:
            zone_data["points"] = z["points"]
        if "center" in z:
            zone_data["center"] = z["center"]
        blueprint_zones.append(zone_data)

    labels = [{"id": f"label_{z['id']}", "text": z["label"], "correctZoneId": z["id"]} for z in zones]

    # Build path waypoints in correct order
    waypoint_order = {name: i for i, name in enumerate(waypoint_labels)}
    ordered_zones = sorted(zones, key=lambda z: waypoint_order.get(z["label"], 99))

    path_waypoints = []
    for i, z in enumerate(ordered_zones):
        wp_type = "standard"
        if z["label"] == "Stomach":
            wp_type = "gate"
        elif i == len(ordered_zones) - 1:
            wp_type = "terminus"

        path_waypoints.append({
            "zoneId": z["id"],
            "order": i,
            "type": wp_type,
        })

    blueprint = {
        "templateType": "INTERACTIVE_DIAGRAM",
        "title": "The Digestive System Journey",
        "narrativeIntro": "Follow the path of food as it travels through the digestive system. From the moment you take a bite, food undergoes mechanical and chemical breakdown as it passes through each organ. Trace the correct path from mouth to rectum.",
        "diagram": {
            "assetPrompt": "Human digestive system diagram",
            "assetUrl": diagram_url,
            "zones": blueprint_zones,
        },
        "labels": labels,
        "tasks": [{"id": "task_trace", "type": "trace_path", "questionText": "Trace the path food takes through the digestive system.", "requiredToProceed": True}],
        "interactionMode": "trace_path",
        "mechanics": [{
            "type": "trace_path",
            "scoring": {"strategy": "per_zone", "points_per_correct": 15, "max_score": 90, "partial_credit": True},
            "feedback": {
                "on_correct": "Correct! Food passes through this organ next.",
                "on_incorrect": "Not quite. Think about the order food travels through the digestive tract.",
                "on_completion": "You've successfully traced the entire digestive journey!",
            },
        }],
        "paths": [{
            "id": "digestive_path",
            "waypoints": path_waypoints,
            "description": "The path food takes through the digestive system",
            "requiresOrder": True,
        }],
        "tracePathConfig": {
            "pathType": "linear",
            "drawingMode": "click_waypoints",
            "particleTheme": "droplets",
            "particleSpeed": "medium",
            "colorTransitionEnabled": False,
            "showDirectionArrows": False,
            "showWaypointLabels": True,
            "showFullFlowOnComplete": True,
            "submitMode": "batch",
            "instructions": "Click each organ that food passes through, in the correct order. Submit when ready.",
        },
        "scoringStrategy": {"type": "per_zone", "base_points_per_zone": 15, "max_score": 90, "partial_credit": True},
        "feedbackMessages": {
            "perfect": "Perfect! You traced the entire digestive pathway correctly!",
            "good": "Good effort! Review the order of organs in the digestive tract.",
            "retry": "Remember: mouth → esophagus → stomach → small intestine → large intestine → rectum.",
        },
        "animationCues": {"correctPlacement": "path_draw", "incorrectPlacement": "shake", "allLabeled": "confetti"},
    }

    return insert_demo_game("The Digestive System Journey", "Trace the path food takes through the digestive system", blueprint)


# ─── Game 7: description_matching — The Skeletal System ──────────

async def create_description_matching_game(svc) -> str:
    game_id = "demo_description"
    logger.info("Creating description_matching demo: The Skeletal System")

    bone_structures = ["Skull", "Ribcage", "Spine", "Pelvis", "Femur", "Humerus", "Scapula", "Patella"]

    result = await svc.generate_diagram(
        game_id=game_id,
        subject="human skeletal system front view",
        structures=bone_structures,
        style="clean educational anatomical illustration, full human skeleton front view, labeled, white background",
    )
    zones = result["zones"]
    diagram_url = result["diagram_url"]

    # Functional descriptions — don't give away answers
    bone_descriptions = {
        "Skull": "This bony structure protects the brain and forms the shape of the face.",
        "Ribcage": "This cage-like structure of 12 pairs of curved bones protects the heart and lungs.",
        "Spine": "This flexible column of 33 vertebrae supports the body and protects the spinal cord.",
        "Pelvis": "This basin-shaped structure supports upper body weight and connects the spine to the lower limbs.",
        "Femur": "The longest and strongest bone in the body, extending from hip to knee.",
        "Humerus": "The long bone of the upper arm, connecting shoulder to elbow.",
        "Scapula": "This flat, triangular bone on the back connects the humerus to the clavicle.",
        "Patella": "This small, thick, triangular bone sits in front of the knee joint.",
    }

    # Build zones for blueprint
    blueprint_zones = []
    for z in zones:
        zone_data = {
            "id": z["id"],
            "label": z["label"],
            "x": z["x"],
            "y": z["y"],
            "radius": z["radius"],
            "shape": z.get("shape", "circle"),
            "description": bone_descriptions.get(z["label"], ""),
            "zone_type": "area",
        }
        if "points" in z:
            zone_data["points"] = z["points"]
        if "center" in z:
            zone_data["center"] = z["center"]
        blueprint_zones.append(zone_data)

    # Labels (needed for scoring)
    labels = [{"id": f"label_{z['id']}", "text": z["label"], "correctZoneId": z["id"]} for z in zones]

    # Build descriptions dict keyed by actual returned zone IDs
    desc_config = {}
    for z in zones:
        desc = bone_descriptions.get(z["label"])
        if desc:
            desc_config[z["id"]] = desc

    blueprint = {
        "templateType": "INTERACTIVE_DIAGRAM",
        "title": "The Skeletal System",
        "narrativeIntro": "The human skeleton provides structure, protects vital organs, and enables movement. Read each description and click the matching bone on the diagram.",
        "diagram": {
            "assetPrompt": "Human skeletal system front view",
            "assetUrl": diagram_url,
            "zones": blueprint_zones,
        },
        "labels": labels,
        "tasks": [{"id": "task_desc", "type": "label_diagram", "questionText": "Match bone descriptions to structures on the skeleton.", "requiredToProceed": True}],
        "interactionMode": "description_matching",
        "mechanics": [{
            "type": "description_matching",
            "scoring": {"strategy": "per_zone", "points_per_correct": 10, "max_score": len(desc_config) * 10, "partial_credit": False},
            "feedback": {
                "on_correct": "Correct! You identified the right bone.",
                "on_incorrect": "Not quite — re-read the description and think about the bone's location and function.",
                "on_completion": "Excellent! You matched all bones to their descriptions!",
            },
        }],
        "descriptionMatchingConfig": {
            "descriptions": desc_config,
            "mode": "click_zone",
            "description_panel_position": "left",
        },
        "scoringStrategy": {"type": "per_zone", "base_points_per_zone": 10, "max_score": len(desc_config) * 10},
        "feedbackMessages": {
            "perfect": "Outstanding! You're a skeletal anatomy expert!",
            "good": "Good work! Review the bones you missed.",
            "retry": "Try again — focus on each bone's unique function and location.",
        },
        "animationCues": {"correctPlacement": "glow", "incorrectPlacement": "shake", "allLabeled": "confetti"},
    }

    return insert_demo_game("The Skeletal System", "Match bone descriptions to structures on the skeleton", blueprint)


# ─── Game 8: branching_scenario — Emergency Room Triage ──────────

async def create_branching_game(svc) -> str:
    """Create a branching scenario game — purely text-based, no images needed."""
    game_id = "demo_branching"
    logger.info("Creating branching_scenario demo: Emergency Room Triage")

    nodes = [
        # Decision node 1: Initial assessment
        {
            "id": "node_arrival",
            "question": "A 58-year-old male arrives at the ER clutching his chest. He is sweating profusely and reports severe pain radiating to his left arm. He appears pale and anxious.",
            "description": "The patient's vitals show elevated heart rate (110 bpm) and blood pressure (160/95 mmHg). He has no known allergies.",
            "options": [
                {
                    "id": "opt_vitals_ecg",
                    "text": "Perform 12-lead ECG and check troponin levels immediately",
                    "nextNodeId": "node_vitals",
                    "isCorrect": True,
                    "quality": "optimal",
                    "consequence": "Good call — an ECG will quickly reveal cardiac ischemia patterns, and troponin levels confirm myocardial damage.",
                    "points": 20,
                },
                {
                    "id": "opt_intake",
                    "text": "Complete standard intake paperwork and medical history first",
                    "nextNodeId": "end_delay",
                    "isCorrect": False,
                    "quality": "harmful",
                    "consequence": "With classic signs of acute MI, delaying diagnostic tests for paperwork wastes critical time. Every minute counts for cardiac muscle survival.",
                    "points": 0,
                },
                {
                    "id": "opt_pain_meds",
                    "text": "Administer morphine for pain and monitor for 30 minutes",
                    "nextNodeId": "node_medicate",
                    "isCorrect": False,
                    "quality": "suboptimal",
                    "consequence": "Pain management matters, but treating symptoms without diagnosing the cause first could mask a worsening condition.",
                    "points": 5,
                },
            ],
        },
        # Decision node 2: ECG results
        {
            "id": "node_vitals",
            "question": "The ECG shows significant ST-segment elevation in leads II, III, and aVF. Troponin I is markedly elevated at 2.4 ng/mL (normal < 0.04). This indicates an acute inferior STEMI.",
            "description": "The clock is ticking — guideline-recommended door-to-balloon time is under 90 minutes.",
            "options": [
                {
                    "id": "opt_cath_lab",
                    "text": "Activate the cardiac catheterization lab and administer aspirin + heparin",
                    "nextNodeId": "node_cath",
                    "isCorrect": True,
                    "quality": "optimal",
                    "consequence": "Excellent — immediate cath lab activation with dual antiplatelet therapy is the gold-standard treatment for STEMI.",
                    "points": 25,
                },
                {
                    "id": "opt_xray",
                    "text": "Order a chest X-ray to rule out other causes before proceeding",
                    "nextNodeId": "node_xray",
                    "isCorrect": False,
                    "quality": "suboptimal",
                    "consequence": "While chest X-rays can be useful, the ECG and troponin already confirm STEMI. Additional imaging delays definitive treatment.",
                    "points": 5,
                },
                {
                    "id": "opt_discharge_early",
                    "text": "Start oral medication and schedule outpatient follow-up",
                    "nextNodeId": "end_discharge",
                    "isCorrect": False,
                    "quality": "harmful",
                    "consequence": "Discharging a patient with an active STEMI is extremely dangerous. This patient needs immediate intervention, not outpatient care.",
                    "points": 0,
                },
            ],
        },
        # Decision node 3: Cath lab
        {
            "id": "node_cath",
            "question": "The catheterization reveals a 95% blockage of the right coronary artery. The interventional cardiologist is ready to proceed.",
            "description": "The patient is stable on the cath lab table with continuous monitoring.",
            "options": [
                {
                    "id": "opt_angioplasty",
                    "text": "Proceed with percutaneous coronary intervention (PCI) and stent placement",
                    "nextNodeId": "end_success",
                    "isCorrect": True,
                    "quality": "optimal",
                    "consequence": "PCI with stent placement restores blood flow immediately. The patient's ECG normalizes and symptoms resolve.",
                    "points": 25,
                },
                {
                    "id": "opt_schedule_surgery",
                    "text": "Schedule coronary artery bypass surgery for later this week",
                    "nextNodeId": "end_delay_surgery",
                    "isCorrect": False,
                    "quality": "suboptimal",
                    "consequence": "CABG is sometimes necessary, but delaying treatment when PCI is immediately available risks further myocardial damage.",
                    "points": 5,
                },
            ],
        },
        # Decision node 4: Pain-first detour
        {
            "id": "node_medicate",
            "question": "After 20 minutes, the patient's pain briefly decreased but is now returning with greater intensity. His blood pressure has dropped to 90/60 mmHg and he appears more distressed.",
            "description": "The nurse reports the patient is becoming diaphoretic again and his oxygen saturation is falling.",
            "options": [
                {
                    "id": "opt_now_ecg",
                    "text": "Order an immediate ECG and troponin panel",
                    "nextNodeId": "node_vitals",
                    "isCorrect": True,
                    "quality": "acceptable",
                    "consequence": "Better late than never — the ECG will reveal the cardiac damage that has been progressing during the delay. Critical time has been lost.",
                    "points": 10,
                },
                {
                    "id": "opt_more_meds",
                    "text": "Increase the pain medication dosage",
                    "nextNodeId": "end_overdose",
                    "isCorrect": False,
                    "quality": "harmful",
                    "consequence": "Increasing opioid dosage without a diagnosis further depresses respiration and masks deterioration. The underlying MI continues unchecked.",
                    "points": 0,
                },
            ],
        },
        # Decision node 5: X-ray detour
        {
            "id": "node_xray",
            "question": "The chest X-ray returns normal — no pneumothorax, no aortic dissection. However, 25 minutes have now passed since the confirmed STEMI diagnosis.",
            "description": "The patient is becoming increasingly anxious and reports worsening chest pressure.",
            "options": [
                {
                    "id": "opt_now_cath",
                    "text": "Activate the cath lab immediately and begin antiplatelet therapy",
                    "nextNodeId": "node_cath",
                    "isCorrect": True,
                    "quality": "acceptable",
                    "consequence": "The cath lab is activated, but the delay has narrowed the treatment window. Time lost means more heart muscle at risk.",
                    "points": 10,
                },
                {
                    "id": "opt_discharge_xray",
                    "text": "Since the X-ray is normal, reassure and discharge with medication",
                    "nextNodeId": "end_discharge",
                    "isCorrect": False,
                    "quality": "harmful",
                    "consequence": "A normal chest X-ray does not rule out MI. The ECG and troponin already confirmed STEMI — discharge would be catastrophic.",
                    "points": 0,
                },
            ],
        },
        # End nodes
        {
            "id": "end_success",
            "question": "The PCI was successful. Blood flow is restored, the patient's symptoms resolve, and he is moved to the cardiac care unit for monitoring. Expected full recovery.",
            "isEndNode": True,
            "node_type": "ending",
            "ending_type": "good",
            "endMessage": "Outstanding clinical decision-making! You identified the STEMI quickly, activated appropriate protocols, and ensured timely intervention.",
            "options": [],
        },
        {
            "id": "end_delay",
            "question": "While completing intake forms, the patient's condition deteriorated rapidly. He went into cardiac arrest before diagnostic tests could be ordered. Resuscitation efforts were unsuccessful.",
            "isEndNode": True,
            "node_type": "ending",
            "ending_type": "bad",
            "endMessage": "Administrative tasks should never delay critical diagnostic workup when a patient presents with acute chest pain and classic MI symptoms.",
            "options": [],
        },
        {
            "id": "end_discharge",
            "question": "The patient was discharged but collapsed in the parking lot from a massive myocardial infarction. Emergency services were called, but significant heart damage had already occurred.",
            "isEndNode": True,
            "node_type": "ending",
            "ending_type": "bad",
            "endMessage": "Never discharge a patient with confirmed ST-elevation. ECG and troponin findings always take precedence over other test results.",
            "options": [],
        },
        {
            "id": "end_overdose",
            "question": "The increased opioid dosage caused respiratory depression. By the time the team recognized the underlying MI and the respiratory compromise, the patient required emergency intubation and suffered significant myocardial necrosis.",
            "isEndNode": True,
            "node_type": "ending",
            "ending_type": "bad",
            "endMessage": "Treating symptoms without a diagnosis can make things worse. Always identify the underlying cause before escalating symptomatic treatment.",
            "options": [],
        },
        {
            "id": "end_delay_surgery",
            "question": "While waiting for scheduled surgery, the patient experienced a second cardiac event in the hospital. Emergency PCI was performed, but the cumulative damage resulted in reduced cardiac function.",
            "isEndNode": True,
            "node_type": "ending",
            "ending_type": "bad",
            "endMessage": "When PCI is available and the lesion is amenable, immediate intervention is preferred over scheduling bypass surgery later.",
            "options": [],
        },
    ]

    # Calculate max score for the optimal path: 20 + 25 + 25 = 70
    decision_nodes = [n for n in nodes if not n.get("isEndNode")]
    max_score = sum(
        max((opt.get("points", 0) for opt in n["options"]), default=0)
        for n in decision_nodes
    )

    blueprint = {
        "templateType": "INTERACTIVE_DIAGRAM",
        "title": "Emergency Room Triage",
        "narrativeIntro": "You are the attending physician in a busy emergency room. A patient has just arrived with alarming symptoms. Your clinical decisions will determine the outcome. Choose wisely — every minute counts.",
        "diagram": {
            "assetPrompt": "Emergency room triage scenario",
            "zones": [],
        },
        "labels": [],
        "tasks": [{"id": "task_branch", "type": "label_diagram", "questionText": "Navigate the clinical scenario by making the best treatment decisions.", "requiredToProceed": True}],
        "interactionMode": "branching_scenario",
        "mechanics": [{
            "type": "branching_scenario",
            "scoring": {"strategy": "per_zone", "points_per_correct": 20, "max_score": max_score, "partial_credit": True},
            "feedback": {
                "on_correct": "Good clinical judgment!",
                "on_incorrect": "That decision may not be optimal. Consider the urgency of the situation.",
                "on_completion": "Scenario complete. Review the path you took and the outcomes of your decisions.",
            },
        }],
        "branchingConfig": {
            "nodes": nodes,
            "startNodeId": "node_arrival",
            "showPathTaken": True,
            "allowBacktrack": True,
            "showConsequences": True,
            "multipleValidEndings": False,
            "instructions": "Read each clinical scenario carefully and choose the best course of action. Your goal is to achieve the best patient outcome.",
        },
        "scoringStrategy": {"type": "per_zone", "base_points_per_zone": 20, "max_score": max_score},
        "feedbackMessages": {
            "perfect": "Perfect triage! You made every correct decision under pressure.",
            "good": "Good effort! Review the consequences of each decision to improve.",
            "retry": "Try again. Focus on the urgency of symptoms and standard cardiac protocols.",
        },
        "animationCues": {"correctPlacement": "pulse", "incorrectPlacement": "shake", "allLabeled": "confetti"},
    }

    return insert_demo_game("Emergency Room Triage", "Navigate clinical decisions for a patient with acute chest pain", blueprint)


# ─── Game 9: compare_contrast — Plant Cell vs Animal Cell ─────────

async def create_compare_contrast_game(svc) -> str:
    game_id = "demo_compare"
    logger.info("Creating compare_contrast demo: Plant Cell vs Animal Cell")

    # Generate two diagrams
    plant_structures = ["Cell Wall", "Chloroplast", "Central Vacuole", "Nucleus", "Mitochondria", "Endoplasmic Reticulum"]
    animal_structures = ["Centrioles", "Lysosomes", "Nucleus", "Mitochondria", "Endoplasmic Reticulum", "Golgi Apparatus"]

    plant_result, animal_result = await asyncio.gather(
        svc.generate_diagram(
            game_id=f"{game_id}/plant",
            subject="plant cell cross-section",
            structures=plant_structures,
            style="clean educational cross-section, colorful, labeled organelles, white background",
        ),
        svc.generate_diagram(
            game_id=f"{game_id}/animal",
            subject="animal cell cross-section",
            structures=animal_structures,
            style="clean educational cross-section, colorful, labeled organelles, white background",
        ),
    )

    plant_zones = plant_result["zones"]
    animal_zones = animal_result["zones"]
    plant_url = plant_result["diagram_url"]
    animal_url = animal_result["diagram_url"]

    # Convert circle zones (x, y, radius) to rect zones (x, y, width, height)
    # and prefix IDs to avoid collisions
    def convert_zones(zones, prefix):
        converted = []
        for z in zones:
            r = z.get("radius", 5)
            converted.append({
                "id": f"{prefix}_{z['id']}",
                "label": z["label"],
                "x": max(0, z["x"] - r),
                "y": max(0, z["y"] - r),
                "width": min(r * 2, 100),
                "height": min(r * 2, 100),
            })
        return converted

    plant_compare_zones = convert_zones(plant_zones, "plant")
    animal_compare_zones = convert_zones(animal_zones, "animal")

    # Build expected categories based on which structures were actually detected
    plant_labels = {z["label"] for z in plant_zones}
    animal_labels = {z["label"] for z in animal_zones}
    shared_labels = plant_labels & animal_labels

    # Structures unique to plant cells
    plant_unique = {"Cell Wall", "Chloroplast", "Central Vacuole"}
    # Structures unique to animal cells
    animal_unique = {"Centrioles", "Lysosomes", "Golgi Apparatus"}

    expected_categories = {}
    for z in plant_compare_zones:
        label = z["label"]
        if label in plant_unique:
            expected_categories[z["id"]] = "unique_a"
        elif label in shared_labels:
            expected_categories[z["id"]] = "similar"
        else:
            expected_categories[z["id"]] = "unique_a"

    for z in animal_compare_zones:
        label = z["label"]
        if label in animal_unique:
            expected_categories[z["id"]] = "unique_b"
        elif label in shared_labels:
            expected_categories[z["id"]] = "similar"
        else:
            expected_categories[z["id"]] = "unique_b"

    blueprint = {
        "templateType": "INTERACTIVE_DIAGRAM",
        "title": "Plant Cell vs Animal Cell",
        "narrativeIntro": "Plant and animal cells share a common ancestor but have evolved distinct features. Examine both cell diagrams and categorize each structure as unique to one cell type or shared between both.",
        "diagram": {
            "assetPrompt": "Plant cell vs animal cell comparison",
            "zones": [],
        },
        "labels": [],
        "tasks": [{"id": "task_compare", "type": "label_diagram", "questionText": "Categorize each organelle as unique to plant cells, unique to animal cells, or found in both.", "requiredToProceed": True}],
        "interactionMode": "compare_contrast",
        "mechanics": [{
            "type": "compare_contrast",
            "scoring": {"strategy": "per_zone", "points_per_correct": 10, "max_score": len(expected_categories) * 10, "partial_credit": False},
            "feedback": {
                "on_correct": "Correct! You categorized that organelle correctly.",
                "on_incorrect": "Not quite — think about whether this organelle is found in one or both cell types.",
                "on_completion": "Great job! You've identified the similarities and differences between plant and animal cells.",
            },
        }],
        "compareConfig": {
            "diagramA": {
                "id": "plant_cell",
                "name": "Plant Cell",
                "imageUrl": plant_url,
                "zones": plant_compare_zones,
            },
            "diagramB": {
                "id": "animal_cell",
                "name": "Animal Cell",
                "imageUrl": animal_url,
                "zones": animal_compare_zones,
            },
            "expectedCategories": expected_categories,
            "highlightMatching": True,
            "instructions": "Examine both cells and categorize each structure. Click a structure, then choose whether it's 'Unique to Plant Cell', 'Unique to Animal Cell', or 'Similar in Both'.",
            "comparison_mode": "side_by_side",
            "zoom_enabled": True,
        },
        "scoringStrategy": {"type": "per_zone", "base_points_per_zone": 10, "max_score": len(expected_categories) * 10},
        "feedbackMessages": {
            "perfect": "Perfect! You understand the differences between plant and animal cells!",
            "good": "Good effort! Review which organelles are shared vs unique.",
            "retry": "Remember: cell wall & chloroplasts are plant-exclusive, while centrioles & lysosomes are animal-exclusive.",
        },
        "animationCues": {"correctPlacement": "pulse", "incorrectPlacement": "shake", "allLabeled": "confetti"},
    }

    return insert_demo_game("Plant Cell vs Animal Cell", "Compare organelles between plant and animal cells", blueprint)


# ─── Main ─────────────────────────────────────────────────────────

MECHANIC_MAP = {
    "drag_drop": create_drag_drop_game,
    "click_to_identify": create_click_to_identify_game,
    "sequencing": create_sequencing_game,
    "sorting_categories": create_sorting_game,
    "memory_match": create_memory_match_game,
    "trace_path": create_trace_path_game,
    "description_matching": create_description_matching_game,
    "branching_scenario": create_branching_game,
    "compare_contrast": create_compare_contrast_game,
}


async def main():
    parser = argparse.ArgumentParser(description="Create demo games with AI-generated assets")
    parser.add_argument("--mechanic", "-m", choices=list(MECHANIC_MAP.keys()) + ["all"], default="all")
    parser.add_argument("--skip-assets", action="store_true", help="Skip asset generation (use existing)")
    args = parser.parse_args()

    # Clean up old demo records only when recreating all
    if args.mechanic == "all":
        cleanup_old_demo_games()

    from app.services.asset_gen.core import AssetGenService
    svc = AssetGenService()

    game_urls = {}

    if args.mechanic == "all":
        for name, creator in MECHANIC_MAP.items():
            try:
                pid = await creator(svc)
                game_urls[name] = f"http://localhost:3000/game/{pid}"
            except Exception as e:
                logger.error(f"Failed to create {name}: {e}")
                import traceback; traceback.print_exc()
    else:
        creator = MECHANIC_MAP[args.mechanic]
        pid = await creator(svc)
        game_urls[args.mechanic] = f"http://localhost:3000/game/{pid}"

    print("\n" + "=" * 60)
    print("  Demo Games Created")
    print("=" * 60)
    for mechanic, url in game_urls.items():
        print(f"  {mechanic:25s} → {url}")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
