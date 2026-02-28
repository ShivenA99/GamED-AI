"""
Diagram Image Generator Agent

Generates clean educational diagrams using Gemini Imagen from retrieved
reference images and contextual information.

This agent is part of the hierarchical label diagram preset pipeline:
- Receives a reference image from diagram_image_retriever
- Uses scene structure, domain knowledge, and pedagogical context
- Generates a clean diagram WITHOUT text labels (labels added by frontend)
- Outputs generated_diagram_path and diagram_metadata

Key Features:
- Gemini-only image generation (Nano Banana / Imagen 3)
- Reference image validation (prevents CDN error pages being saved)
- Graceful fallback to prompt-only generation if reference fails

Inputs:
    - diagram_image: Retrieved reference image from web
    - scene_structure: From scene_stage1 (visual theme, layout)
    - domain_knowledge: Canonical labels, hierarchical_relationships
    - pedagogical_context: Subject, difficulty, Bloom's level

Outputs:
    - generated_diagram_path: Path to generated clean image
    - diagram_metadata: Dimensions, style info, generation details
"""

import asyncio
import hashlib
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from app.agents.state import AgentState
from app.agents.instrumentation import InstrumentedAgentContext
from app.utils.logging_config import get_logger

logger = get_logger("gamed_ai.agents.diagram_image_generator")

# Output directory for generated diagrams
OUTPUT_DIR = Path("pipeline_outputs/generated_diagrams")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


async def download_and_validate_image(image_url: str, output_path: str) -> bool:
    """
    Download a reference image from URL and validate it's actually an image.

    This function validates the downloaded content is a real image before saving,
    preventing issues with CDN error pages (e.g., Facebook's lookaside URLs that
    require auth cookies and return HTML instead of images).

    Args:
        image_url: URL to download from
        output_path: Local path to save validated image

    Returns:
        True if download and validation successful, False otherwise
    """
    try:
        import aiohttp
        from PIL import Image
        from io import BytesIO

        async with aiohttp.ClientSession() as session:
            # Set headers to mimic browser request
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
            }
            async with session.get(image_url, timeout=30, headers=headers) as response:
                if response.status != 200:
                    logger.warning(f"Failed to download image: HTTP {response.status} from {image_url[:80]}")
                    return False

                content = await response.read()

                # Check content type header
                content_type = response.headers.get("Content-Type", "")
                if "text/html" in content_type or "application/json" in content_type:
                    logger.warning(f"Downloaded content is {content_type}, not an image: {image_url[:80]}")
                    return False

                # Validate it's a real image using PIL
                try:
                    img = Image.open(BytesIO(content))
                    img.verify()  # Verify it's a valid image format

                    # Re-open after verify (verify closes the file)
                    img = Image.open(BytesIO(content))
                    width, height = img.size

                    # Sanity check dimensions
                    if width < 50 or height < 50:
                        logger.warning(f"Image too small ({width}x{height}), likely not a diagram")
                        return False

                    logger.info(f"Validated image: {width}x{height}, format={img.format}")

                except Exception as e:
                    logger.warning(f"Downloaded content is not a valid image: {e}")
                    return False

                # Save validated image
                with open(output_path, "wb") as f:
                    f.write(content)

                logger.info(f"Downloaded and validated reference image to {output_path}")
                return True

    except Exception as e:
        logger.error(f"Failed to download reference image: {e}")
        return False


async def download_reference_image(image_url: str, output_path: str) -> Optional[str]:
    """Legacy wrapper for backward compatibility."""
    success = await download_and_validate_image(image_url, output_path)
    return output_path if success else None


def build_generation_prompt(
    subject: str,
    canonical_labels: List[str],
    visual_theme: str = "clean educational",
    style_directive: str = "diagram",
    hierarchical_relationships: Optional[Dict] = None,
) -> str:
    """
    Build a prompt for diagram generation.

    Args:
        subject: Subject matter (e.g., "flower anatomy", "cell structure")
        canonical_labels: List of parts to include
        visual_theme: Visual style theme
        style_directive: Type of diagram (realistic, illustrated, schematic)
        hierarchical_relationships: Optional hierarchical groupings

    Returns:
        Generation prompt string
    """
    # Build parts list
    parts_list = ", ".join(canonical_labels) if canonical_labels else "main components"

    # Build hierarchy context if available
    hierarchy_context = ""
    if hierarchical_relationships:
        # Handle both list and dict formats for hierarchical_relationships
        groups = []
        if isinstance(hierarchical_relationships, dict):
            groups = hierarchical_relationships.get("groups", [])
        elif isinstance(hierarchical_relationships, list):
            # If it's already a list, use it directly as groups
            groups = hierarchical_relationships

        if groups:
            hierarchy_items = []
            for group in groups:
                if isinstance(group, dict):
                    group_name = group.get("name", "Group")
                    members = group.get("members", [])
                    if members:
                        hierarchy_items.append(f"- {group_name}: {', '.join(members)}")
                elif isinstance(group, str):
                    # If group is just a string, add it directly
                    hierarchy_items.append(f"- {group}")
            if hierarchy_items:
                hierarchy_context = f"\n\nThe diagram should clearly show these structural groupings:\n" + "\n".join(hierarchy_items)

    # Build the generation prompt - emphasize academic accuracy
    prompt = f"""Create a SCIENTIFICALLY ACCURATE, professional educational diagram of {subject}.

CRITICAL ACADEMIC ACCURACY REQUIREMENTS:
- Must be anatomically/biologically/scientifically CORRECT and accurate to real-world references
- Follow established scientific illustration conventions for this subject
- Proportions, positions, and relationships between parts must be medically/scientifically accurate
- Use colors and textures that reflect real biological/physical structures
- Suitable for use in academic textbooks, medical education, or scientific publications

STYLE REQUIREMENTS:
- {visual_theme} illustration style
- Clean white or light neutral background
- High contrast colors for each distinct part
- Clear visual separation between different structures
- No text, labels, arrows, or annotations (labels will be added separately)
- Professional scientific illustration quality matching educational textbooks

CONTENT REQUIREMENTS:
- Show a clear, well-composed, ANATOMICALLY ACCURATE view of the {subject}
- Include all these parts clearly visible and distinct: {parts_list}
- Each part should be easily identifiable by its shape, color, and position
- Maintain correct spatial relationships and proportions as found in real specimens
- Parts should be visually distinct from each other{hierarchy_context}

OUTPUT SPECIFICATIONS:
- Single, centered composition
- All parts fully visible (no cropping)
- Consistent lighting and shading
- Educational diagram suitable for academic learning and assessment

CRITICAL: The diagram must be COMPLETELY CLEAN with NO TEXT of any kind:
- DO NOT include any text labels, numbers, or letters
- DO NOT include any arrows pointing to parts
- DO NOT include any leader lines or annotation lines
- DO NOT include any captions or titles
- The image should be a pure anatomical/scientific illustration only
- Text labels will be added programmatically by the application later

Generate a scientifically accurate, clean {style_directive} of {subject} showing all the main components in their correct anatomical positions. The output must contain ZERO text or annotations and must be academically accurate."""

    return prompt


async def generate_with_gemini(
    prompt: str,
    reference_image_path: Optional[str] = None,
    dimensions: Optional[Dict[str, int]] = None,
) -> Dict[str, Any]:
    """
    Generate image using Gemini Imagen.

    Args:
        prompt: Generation prompt
        reference_image_path: Optional path to reference image
        dimensions: Optional width/height

    Returns:
        Dict with success, image_path, and metadata
    """
    try:
        from google import genai
        from google.genai import types
        from PIL import Image
        import io

        api_key = os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            return {
                "success": False,
                "error": "GOOGLE_API_KEY not set",
                "generator": "gemini-imagen",
            }

        client = genai.Client(api_key=api_key)

        logger.info("Generating diagram with Gemini Imagen")
        start_time = time.time()

        # Build content with optional reference image
        contents = [prompt]
        if reference_image_path and os.path.exists(reference_image_path):
            try:
                ref_image = Image.open(reference_image_path)
                # Verify the image is valid
                ref_image.verify()
                # Re-open after verify (verify closes the file)
                ref_image = Image.open(reference_image_path)
                contents = [prompt, ref_image]
                logger.info(f"Using reference image: {reference_image_path} ({ref_image.size})")
            except Exception as e:
                logger.warning(f"Could not open reference image, generating without reference: {e}")
                # Continue with prompt only - don't fail the whole generation

        # Use configurable model for image generation
        # Options: gemini-2.5-flash-image (Nano Banana stable), gemini-3-pro-image-preview (Nano Banana Pro)
        # Note: gemini-2.0-flash-exp is deprecated, use gemini-2.5-flash-image instead
        model = os.getenv("GEMINI_IMAGE_MODEL", "gemini-2.5-flash-image")
        logger.info(f"Using Gemini model: {model}")

        response = client.models.generate_content(
            model=model,
            contents=contents,
            config=types.GenerateContentConfig(
                response_modalities=["image", "text"],
            )
        )

        duration_ms = int((time.time() - start_time) * 1000)

        # Extract generated image
        generated_image = None
        response_text = ""

        for part in response.parts:
            if hasattr(part, 'inline_data') and part.inline_data is not None:
                image_data = part.inline_data.data
                generated_image = Image.open(io.BytesIO(image_data))
            elif hasattr(part, 'text') and part.text:
                response_text += part.text

        if generated_image:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = str(OUTPUT_DIR / f"gemini_diagram_{timestamp}.png")
            generated_image.save(output_path)
            logger.info(f"Saved generated diagram to {output_path}")

            return {
                "success": True,
                "generated_path": output_path,
                "generator": model,
                "response_text": response_text,
                "duration_ms": duration_ms,
            }
        else:
            return {
                "success": False,
                "error": "No image in response",
                "response_text": response_text,
                "generator": model,
            }

    except Exception as e:
        logger.error(f"Gemini generation failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "generator": "gemini",
        }


async def diagram_image_generator(
    state: AgentState,
    ctx: Optional[InstrumentedAgentContext] = None
) -> dict:
    """
    Generate a clean educational diagram from retrieved reference + context.

    This agent is used in the hierarchical label diagram preset pipeline.
    It generates a clean diagram image using Gemini Imagen.

    Inputs from state:
        - diagram_image: Retrieved reference image info (from diagram_image_retriever)
        - scene_structure: Visual theme and layout (from scene_stage1)
        - domain_knowledge: Canonical labels, hierarchical relationships
        - pedagogical_context: Subject, difficulty, Bloom's level

    Outputs to state:
        - generated_diagram_path: Path to the generated clean image
        - diagram_metadata: Generation details and metadata
    """
    question_id = state.get("question_id", "unknown")
    template_type = state.get("template_selection", {}).get("template_type", "")

    logger.info(f"Starting diagram image generation for {question_id}")

    # Check if this is a INTERACTIVE_DIAGRAM template
    if template_type != "INTERACTIVE_DIAGRAM":
        logger.warning(f"diagram_image_generator called for non-INTERACTIVE_DIAGRAM template: {template_type}")
        return {
            "current_agent": "diagram_image_generator",
            "last_updated_at": datetime.utcnow().isoformat(),
        }

    # Get inputs from state
    diagram_image = state.get("diagram_image", {})
    scene_structure = state.get("scene_structure", {})
    domain_knowledge = state.get("domain_knowledge", {}) or {}
    pedagogical_context = state.get("pedagogical_context", {}) or {}

    # Extract relevant information
    reference_url = diagram_image.get("image_url") or diagram_image.get("url")
    reference_description = diagram_image.get("title") or diagram_image.get("description", "")

    canonical_labels = list(domain_knowledge.get("canonical_labels", []) or [])
    hierarchical_relationships = domain_knowledge.get("hierarchical_relationships")

    subject = pedagogical_context.get("subject", "")
    question_text = state.get("question_text", "")

    # Get scene_data for backward compatibility (legacy pipeline)
    scene_data = state.get("scene_data") or {}

    # Determine visual theme from scene structure (with fallback to scene_data for backward compatibility)
    # scene_structure comes from scene_stage1_structure (hierarchical pipeline)
    # scene_data comes from legacy scene_generator
    visual_theme = None
    if scene_structure.get("visual_theme"):
        visual_theme = scene_structure["visual_theme"]
    elif isinstance(scene_structure.get("theme"), dict) and scene_structure["theme"].get("style"):
        visual_theme = scene_structure["theme"]["style"]
    elif scene_data.get("visual_theme"):
        visual_theme = scene_data["visual_theme"]
    else:
        visual_theme = "clean educational"

    # Handle case where visual_theme is a dict (e.g., {"name": "...", "description": "..."})
    if isinstance(visual_theme, dict):
        visual_theme = visual_theme.get("name", "clean educational")

    # Determine subject from question if not available
    if not subject:
        subject = question_text.replace("Label the parts of ", "").replace("Label ", "").strip()
        if subject.startswith("a "):
            subject = subject[2:]
        if subject.startswith("an "):
            subject = subject[3:]
        if subject.endswith("?"):
            subject = subject[:-1]

    logger.info(f"Generating diagram for subject: {subject}")
    logger.info(f"Canonical labels: {canonical_labels}")
    logger.info(f"Visual theme: {visual_theme}")

    # Build generation prompt
    prompt = build_generation_prompt(
        subject=subject,
        canonical_labels=canonical_labels,
        visual_theme=visual_theme,
        style_directive="scientific illustration",
        hierarchical_relationships=hierarchical_relationships,
    )

    # Always use Gemini Imagen (Gemini-only mode)
    logger.info("Using Gemini Imagen for diagram generation")

    result: Dict[str, Any] = {}

    # Download and validate reference image if available
    # Try primary URL first, then backup images if download fails
    ref_path = None
    backup_images = diagram_image.get("backup_images", [])
    urls_to_try = []

    if reference_url:
        urls_to_try.append(("primary", reference_url))

    # Add backup URLs
    for i, backup in enumerate(backup_images):
        backup_url = backup.get("image_url")
        if backup_url:
            urls_to_try.append((f"backup_{i+1}", backup_url))

    # Try each URL until one succeeds
    for url_type, url in urls_to_try:
        ref_path = str(OUTPUT_DIR / f"reference_{question_id}_{url_type}.png")
        logger.info(f"Trying {url_type} reference image: {url[:80]}")
        download_success = await download_and_validate_image(url, ref_path)

        if download_success:
            logger.info(f"Successfully downloaded {url_type} reference image")
            break
        else:
            logger.warning(f"{url_type} reference image download failed, trying next...")
            ref_path = None

    if not ref_path:
        logger.warning("All reference image downloads failed, generating without reference")

    # Generate with Gemini (with or without reference)
    result = await generate_with_gemini(
        prompt=prompt,
        reference_image_path=ref_path,
    )

    # Handle result
    if result.get("success"):
        generated_path = result.get("generated_path")

        # Track LLM metrics if ctx is available
        if ctx:
            ctx.set_llm_metrics(
                model=result.get("generator", "unknown"),
                latency_ms=result.get("duration_ms", 0),
            )

        logger.info(f"Diagram generation successful: {generated_path}")

        # Copy to expected assets location for consistent serving
        # This ensures /api/assets/{question_id}/generated/diagram.png works correctly
        import shutil
        assets_dir = Path("pipeline_outputs/assets") / question_id / "generated"
        assets_dir.mkdir(parents=True, exist_ok=True)
        assets_path = assets_dir / "diagram.png"
        try:
            shutil.copy(generated_path, assets_path)
            logger.info(f"Copied generated diagram to assets: {assets_path}")
        except Exception as e:
            logger.warning(f"Failed to copy to assets directory: {e}")

        return {
            "generated_diagram_path": generated_path,
            "diagram_metadata": {
                "generator": result.get("generator"),
                "size": result.get("size", "1024x1024"),
                "duration_ms": result.get("duration_ms"),
                "revised_prompt": result.get("revised_prompt"),
                "subject": subject,
                "canonical_labels": canonical_labels,
                "generated_at": datetime.utcnow().isoformat(),
            },
            # Also update diagram_image to point to generated image for downstream agents
            "diagram_image": {
                **diagram_image,
                "generated_path": generated_path,
                "is_generated": True,
                "original_url": reference_url,
            },
            # Use generated image path for zone detection
            "cleaned_image_path": generated_path,
            "current_agent": "diagram_image_generator",
            "last_updated_at": datetime.utcnow().isoformat(),
        }
    else:
        error_msg = result.get("error", "Unknown generation error")
        logger.error(f"Diagram generation failed: {error_msg}")

        # Track fallback if using ctx
        if ctx:
            ctx.set_fallback_used(f"Generation failed: {error_msg}")

        return {
            "current_agent": "diagram_image_generator",
            "current_validation_errors": [f"Diagram generation failed: {error_msg}"],
            "last_updated_at": datetime.utcnow().isoformat(),
            "_used_fallback": True,
            "_fallback_reason": f"Image generation failed: {error_msg}",
        }
