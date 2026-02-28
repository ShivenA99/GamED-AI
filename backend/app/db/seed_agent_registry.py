"""
Seed the AgentRegistry with initial agent metadata.

Run this once after creating the database to populate agent metadata
for the dashboard UI.
"""

from app.db.database import SessionLocal
from app.db.models import AgentRegistry


# Agent metadata definitions
AGENT_METADATA = [
    {
        "id": "input_enhancer",
        "display_name": "Input Enhancer",
        "description": "Analyzes and enhances the input question with pedagogical context (Bloom's taxonomy, subject, difficulty)",
        "category": "input",
        "typical_inputs": ["question_text", "question_options"],
        "typical_outputs": ["pedagogical_context"],
        "icon": "sparkles",
        "color": "#8B5CF6"  # Purple
    },
    {
        "id": "domain_knowledge_retriever",
        "display_name": "Domain Knowledge",
        "description": "Retrieves canonical labels and domain knowledge via web search for accurate game content",
        "category": "input",
        "typical_inputs": ["question_text", "pedagogical_context"],
        "typical_outputs": ["domain_knowledge"],
        "icon": "search",
        "color": "#3B82F6"  # Blue
    },
    {
        "id": "router",
        "display_name": "Template Router",
        "description": "Selects the best game template based on question type and learning objectives",
        "category": "routing",
        "typical_inputs": ["question_text", "pedagogical_context", "domain_knowledge"],
        "typical_outputs": ["template_selection", "routing_confidence"],
        "icon": "git-branch",
        "color": "#10B981"  # Green
    },
    {
        "id": "game_planner",
        "display_name": "Game Planner",
        "description": "Creates the game plan with mechanics, difficulty progression, and learning objectives",
        "category": "generation",
        "typical_inputs": ["template_selection", "pedagogical_context", "domain_knowledge"],
        "typical_outputs": ["game_plan"],
        "icon": "clipboard-list",
        "color": "#F59E0B"  # Amber
    },
    {
        "id": "scene_generator",
        "display_name": "Scene Generator",
        "description": "Generates visual scene data including theme, layout, and asset requirements",
        "category": "generation",
        "typical_inputs": ["game_plan", "template_selection"],
        "typical_outputs": ["scene_data"],
        "icon": "image",
        "color": "#EC4899"  # Pink
    },
    {
        "id": "diagram_image_retriever",
        "display_name": "Diagram Retriever",
        "description": "Searches and retrieves diagram images for INTERACTIVE_DIAGRAM template",
        "category": "image",
        "typical_inputs": ["domain_knowledge", "game_plan"],
        "typical_outputs": ["diagram_image"],
        "icon": "photo",
        "color": "#06B6D4"  # Cyan
    },
    {
        "id": "image_label_remover",
        "display_name": "Label Remover",
        "description": "Removes existing labels from diagram images using inpainting",
        "category": "image",
        "typical_inputs": ["diagram_image"],
        "typical_outputs": ["diagram_image"],  # Updated with cleaned image
        "icon": "eraser",
        "color": "#6366F1"  # Indigo
    },
    {
        "id": "sam3_prompt_generator",
        "display_name": "SAM3 Prompt Gen",
        "description": "Generates point prompts for SAM3 segmentation model",
        "category": "image",
        "typical_inputs": ["diagram_image", "game_plan"],
        "typical_outputs": ["sam3_prompts"],
        "icon": "crosshair",
        "color": "#84CC16"  # Lime
    },
    {
        "id": "diagram_image_segmenter",
        "display_name": "Image Segmenter",
        "description": "Segments diagram into interactive zones using SAM2/SAM",
        "category": "image",
        "typical_inputs": ["diagram_image", "sam3_prompts"],
        "typical_outputs": ["diagram_segments", "diagram_zones"],
        "icon": "scissors",
        "color": "#EF4444"  # Red
    },
    {
        "id": "diagram_zone_labeler",
        "display_name": "Zone Labeler",
        "description": "Labels segmented zones using VLM (vision-language model)",
        "category": "image",
        "typical_inputs": ["diagram_zones", "domain_knowledge"],
        "typical_outputs": ["diagram_labels"],
        "icon": "tag",
        "color": "#F97316"  # Orange
    },
    {
        "id": "blueprint_generator",
        "display_name": "Blueprint Generator",
        "description": "Generates the complete game blueprint with all game data",
        "category": "generation",
        "typical_inputs": ["game_plan", "scene_data", "diagram_labels", "domain_knowledge"],
        "typical_outputs": ["blueprint"],
        "icon": "document-text",
        "color": "#8B5CF6"  # Purple
    },
    {
        "id": "blueprint_validator",
        "display_name": "Blueprint Validator",
        "description": "Validates generated blueprint for schema, semantics, and pedagogy",
        "category": "validation",
        "typical_inputs": ["blueprint"],
        "typical_outputs": ["validation_results"],
        "icon": "check-circle",
        "color": "#10B981"  # Green
    },
    {
        "id": "diagram_spec_generator",
        "display_name": "Diagram Spec Gen",
        "description": "Generates SVG specification for diagram visualization",
        "category": "generation",
        "typical_inputs": ["blueprint", "diagram_zones"],
        "typical_outputs": ["diagram_spec"],
        "icon": "code",
        "color": "#3B82F6"  # Blue
    },
    {
        "id": "diagram_spec_validator",
        "display_name": "Diagram Spec Validator",
        "description": "Validates diagram SVG specification",
        "category": "validation",
        "typical_inputs": ["diagram_spec"],
        "typical_outputs": ["validation_results"],
        "icon": "check-badge",
        "color": "#10B981"  # Green
    },
    {
        "id": "diagram_svg_generator",
        "display_name": "SVG Generator",
        "description": "Generates final SVG markup from diagram specification",
        "category": "generation",
        "typical_inputs": ["diagram_spec"],
        "typical_outputs": ["diagram_svg"],
        "icon": "cube",
        "color": "#EC4899"  # Pink
    },
    {
        "id": "code_generator",
        "display_name": "Code Generator",
        "description": "Generates React component code for stub templates",
        "category": "generation",
        "typical_inputs": ["blueprint", "scene_data"],
        "typical_outputs": ["generated_code"],
        "icon": "code-bracket",
        "color": "#F59E0B"  # Amber
    },
    {
        "id": "code_verifier",
        "display_name": "Code Verifier",
        "description": "Verifies generated code in Docker sandbox",
        "category": "validation",
        "typical_inputs": ["generated_code", "blueprint"],
        "typical_outputs": ["validation_results"],
        "icon": "shield-check",
        "color": "#10B981"  # Green
    },
    {
        "id": "asset_generator",
        "display_name": "Asset Generator",
        "description": "Generates or retrieves image assets for the game",
        "category": "output",
        "typical_inputs": ["blueprint", "diagram_svg"],
        "typical_outputs": ["asset_urls", "generation_complete"],
        "icon": "photograph",
        "color": "#6366F1"  # Indigo
    },
    {
        "id": "human_review",
        "display_name": "Human Review",
        "description": "Pauses for human review and approval",
        "category": "review",
        "typical_inputs": ["template_selection", "blueprint", "current_validation_errors"],
        "typical_outputs": ["pending_human_review"],
        "icon": "user-circle",
        "color": "#F43F5E"  # Rose
    }
]


def seed_agent_registry():
    """Seed the agent registry with initial metadata."""
    db = SessionLocal()
    try:
        for agent_data in AGENT_METADATA:
            # Check if agent already exists
            existing = db.query(AgentRegistry).filter_by(id=agent_data["id"]).first()
            if existing:
                # Update existing record
                for key, value in agent_data.items():
                    setattr(existing, key, value)
            else:
                # Create new record
                agent = AgentRegistry(**agent_data)
                db.add(agent)

        db.commit()
        print(f"Seeded {len(AGENT_METADATA)} agents to registry")
    except Exception as e:
        db.rollback()
        print(f"Error seeding agent registry: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    from app.db.database import init_db
    init_db()
    seed_agent_registry()
