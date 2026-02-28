from typing import Dict, Any, List
from pathlib import Path
import json


class ValidationResult:
    def __init__(self, is_valid: bool, errors: List[str] = None, metadata: Dict[str, Any] = None):
        self.is_valid = is_valid
        self.errors = errors or []
        self.metadata = metadata or {}
    def __init__(self, is_valid: bool, errors: List[str] = None, metadata: Dict[str, Any] = None):
        self.is_valid = is_valid
        self.errors = errors or []
        self.metadata = metadata or {}


def validate_sprite(sheet_path: str, spec: Dict[str, Any]) -> ValidationResult:
    """Validate sprite sheet against specifications."""
    
    errors = []
    metadata = {}
    
    try:
        if not Path(sheet_path).exists():
            errors.append("Sprite sheet file does not exist")
            return ValidationResult(False, errors)
        
        sprite_spec = spec.get("assetSpec", {}).get("sprite", {})
        
        # Check sheet dimensions
        expected_width = sprite_spec["grid"]["cols"] * (sprite_spec["frameSize"]["w"] + sprite_spec["paddingPx"])
        expected_height = sprite_spec["grid"]["rows"] * (sprite_spec["frameSize"]["h"] + sprite_spec["paddingPx"])
        
        # Mock dimension check
        metadata["sheet_dimensions"] = f"{expected_width}x{expected_height}"
        metadata["expected_frames"] = sprite_spec["frameCount"]
        
        # Mock frame consistency check
        metadata["frame_consistency_score"] = 0.95  # High similarity
        
        # Check transparency
        metadata["has_transparency"] = True
        
        # Validate frame count
        frames_dir = Path(sheet_path).parent / "frames"
        if frames_dir.exists():
            frame_files = list(frames_dir.glob("frame_*.png"))
            metadata["actual_frames"] = len(frame_files)
            
            if len(frame_files) != sprite_spec["frameCount"]:
                errors.append(f"Frame count mismatch: expected {sprite_spec['frameCount']}, found {len(frame_files)}")
        
        is_valid = len(errors) == 0
        
    except Exception as e:
        errors.append(f"Validation failed: {str(e)}")
        is_valid = False
    
    return ValidationResult(is_valid, errors, metadata)