import json
import hashlib
from typing import Any, Dict, List
from pathlib import Path
from datetime import datetime

from models import (
    PNGAssetConfig,
    SVGAssetConfig,
    SpriteAssetConfig,
    JobMetadata,
)
from prompts import build_png_prompt, build_svg_prompt, build_sprite_prompt
from pipeline.state import PipelineState


def load_input_node(state: dict) -> dict:
    """Load and parse the input JSON, detect asset type."""
    try:
        data = state["input_json"]
        asset_type = data.get("job", {}).get("assetType")
        
        if asset_type == "png":
            config = PNGAssetConfig(**data)
        elif asset_type == "svg":
            config = SVGAssetConfig(**data)
        elif asset_type == "sprite":
            config = SpriteAssetConfig(**data)
        else:
            raise ValueError(f"Unknown asset type: {asset_type}")
        
        state["config"] = config
        state["asset_type"] = asset_type
        state["status"] = "input_loaded"
    except Exception as e:
        state["errors"] = state.get("errors", []) + [f"load_input failed: {str(e)}"]
        state["status"] = "failed"
    
    return state


def plan_job_node(state: dict) -> dict:
    """Plan the job based on asset type."""
    try:
        config = state["config"]
        asset_type = state["asset_type"]
        
        plan = {
            "asset_type": asset_type,
            "expected_outputs": [],
            "validation_rules": [],
        }
        
        if asset_type == "png":
            plan["expected_outputs"] = ["asset.png", "metadata.json", "manifest.json"]
            plan["validation_rules"] = ["dimensions", "transparency", "file_size"]
        elif asset_type == "svg":
            plan["expected_outputs"] = ["asset_raster.png", "asset.svg", "metadata.json", "manifest.json"]
            plan["validation_rules"] = ["svg_valid", "no_raster_embeds", "path_count"]
        elif asset_type == "sprite":
            plan["expected_outputs"] = ["sprite_sheet.png", "frames/", "metadata.json", "manifest.json"]
            plan["validation_rules"] = ["frame_consistency", "sheet_dimensions", "transparency"]
        
        state["job_plan"] = plan
        state["status"] = "job_planned"
    except Exception as e:
        state["errors"] = state.get("errors", []) + [f"plan_job failed: {str(e)}"]
        state["status"] = "failed"
    
    return state


def build_prompt_node(state: dict) -> dict:
    """Build the compiled prompt and audit."""
    try:
        config = state["config"]
        asset_type = state["asset_type"]
        
        if asset_type == "png":
            prompt = build_png_prompt(config.promptSpec)
        elif asset_type == "svg":
            prompt = build_svg_prompt(config.promptSpec)
        elif asset_type == "sprite":
            # For sprites, we'll build prompts per frame later
            prompt = build_sprite_prompt(config.promptSpec, 0, config.assetSpec.sprite.frameCount, config.assetSpec)
        
        # Create audit
        audit = {
            "input_hash": hashlib.sha256(json.dumps(state["input_json"], sort_keys=True).encode()).hexdigest(),
            "prompt_hash": hashlib.sha256(prompt.encode()).hexdigest(),
            "compiled_at": datetime.now().isoformat(),
        }
        
        state["compiled_prompt"] = prompt
        state["prompt_audit"] = audit
        state["status"] = "prompt_built"
    except Exception as e:
        state["errors"] = state.get("errors", []) + [f"build_prompt failed: {str(e)}"]
        state["status"] = "failed"
    
    return state


def generate_images_node(state: dict) -> dict:
    """Generate images using the appropriate API."""
    try:
        config = state["config"]
        asset_type = state["asset_type"]
        
        # Mock generation for now - in real implementation, call Google Imagen API
        generated = []
        for i in range(config.imagenConfig.numberOfImages):
            generated.append({
                "id": f"gen_{i}",
                "url": f"mock_url_{i}",
                "metadata": {"seed": config.imagenConfig.seed or 12345 + i}
            })
        
        state["generated_images"] = generated
        state["generation_metadata"] = {
            "model": config.model.name,
            "count": len(generated),
            "generated_at": datetime.now().isoformat(),
        }
        state["status"] = "images_generated"
    except Exception as e:
        state["errors"] = state.get("errors", []) + [f"generate_images failed: {str(e)}"]
        state["status"] = "failed"
    
    return state


def validate_outputs_node(state: dict) -> dict:
    """Validate the generated outputs."""
    try:
        config = state["config"]
        asset_type = state["asset_type"]
        
        # Mock validation - in real implementation, check files
        validation_results = []
        for img in state["generated_images"]:
            validation_results.append({
                "image_id": img["id"],
                "is_valid": True,  # Mock as valid
                "checks": ["dimensions", "transparency", "file_size"]
            })
        
        state["validation_results"] = validation_results
        state["is_valid"] = all(r["is_valid"] for r in validation_results)
        state["status"] = "outputs_validated"
    except Exception as e:
        state["errors"] = state.get("errors", []) + [f"validate_outputs failed: {str(e)}"]
        state["status"] = "failed"
    
    return state


def retry_or_finalize_node(state: dict) -> dict:
    """Decide whether to retry or finalize."""
    try:
        if state.get("is_valid", False):
            state["status"] = "ready_to_finalize"
        else:
            attempt_count = state.get("attempt_count", 0) + 1
            state["attempt_count"] = attempt_count
            max_attempts = state["config"].retrySpec.maxAttempts
            if attempt_count < max_attempts:
                # Add repair directives
                state["repair_directives"] = state.get("repair_directives", []) + ["Fix: improve quality and meet validation requirements"]
                state["status"] = "retry_needed"
            else:
                state["status"] = "max_retries_exceeded"
    except Exception as e:
        state["errors"] = state.get("errors", []) + [f"retry_or_finalize failed: {str(e)}"]
        state["status"] = "failed"
    
    return state


def postprocess_and_save_node(state: dict) -> dict:
    """Postprocess and save final assets."""
    try:
        config = state["config"]
        asset_type = state["asset_type"]
        
        # Mock saving - create output paths
        base_dir = Path(config.outputSpec.baseDir) / config.job.projectId / config.job.topicId / asset_type / config.job.assetId / f"v{config.job.version}"
        base_dir.mkdir(parents=True, exist_ok=True)
        
        output_paths = []
        if asset_type == "png":
            output_paths.append(str(base_dir / "asset.png"))
        elif asset_type == "svg":
            output_paths.extend([
                str(base_dir / "asset_raster.png"),
                str(base_dir / "asset.svg")
            ])
        elif asset_type == "sprite":
            output_paths.extend([
                str(base_dir / "sprite_sheet.png"),
                str(base_dir / "frames")
            ])
        
        # Mock metadata and manifest
        metadata_path = str(base_dir / "metadata.json")
        manifest_path = str(base_dir / "manifest.json")
        
        state["output_paths"] = output_paths
        state["metadata_path"] = metadata_path
        state["manifest_path"] = manifest_path
        state["status"] = "completed"
    except Exception as e:
        state["errors"] = state.get("errors", []) + [f"postprocess_and_save failed: {str(e)}"]
        state["status"] = "failed"
    
    return state


def checkpoint_node(state: dict) -> dict:
    """Save checkpoint."""
    try:
        # Mock checkpoint - in real implementation, save to SQLite/JSON
        state["checkpoint_id_value"] = f"checkpoint_{datetime.now().timestamp()}"
        # Here we would persist the state
    except Exception as e:
        state["errors"] = state.get("errors", []) + [f"checkpoint failed: {str(e)}"]
    
    return state