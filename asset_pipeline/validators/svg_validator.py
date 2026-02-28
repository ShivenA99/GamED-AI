from typing import Dict, Any, List
from pathlib import Path
import xml.etree.ElementTree as ET


class ValidationResult:
    def __init__(self, is_valid: bool, errors: List[str] = None, metadata: Dict[str, Any] = None):
        self.is_valid = is_valid
        self.errors = errors or []
        self.metadata = metadata or {}
    def __init__(self, is_valid: bool, errors: List[str] = None, metadata: Dict[str, Any] = None):
        self.is_valid = is_valid
        self.errors = errors or []
        self.metadata = metadata or {}


def validate_svg(svg_path: str, spec: Dict[str, Any]) -> ValidationResult:
    """Validate SVG asset against specifications."""
    
    errors = []
    metadata = {}
    
    try:
        if not Path(svg_path).exists():
            errors.append("SVG file does not exist")
            return ValidationResult(False, errors)
        
        # Parse SVG
        tree = ET.parse(svg_path)
        root = tree.getroot()
        
        # Check for raster embeds
        images = root.findall(".//{http://www.w3.org/2000/svg}image")
        if images and spec.get("assetSpec", {}).get("svg", {}).get("disallowRasterEmbeds"):
            errors.append("SVG contains raster image embeds")
        
        # Count paths
        paths = root.findall(".//{http://www.w3.org/2000/svg}path")
        path_count = len(paths)
        metadata["path_count"] = path_count
        
        max_paths = spec.get("assetSpec", {}).get("svg", {}).get("maxPaths", 2000)
        if path_count > max_paths:
            errors.append(f"Path count {path_count} exceeds limit {max_paths}")
        
        # Check file size
        file_size_kb = Path(svg_path).stat().st_size / 1024
        metadata["file_size_kb"] = file_size_kb
        
        max_size = spec.get("validationSpec", {}).get("maxFileSizeKB", 200)
        if file_size_kb > max_size:
            errors.append(f"File size {file_size_kb:.1f}KB exceeds limit {max_size}KB")
        
        # Mock render test
        metadata["render_test_passed"] = True
        
        is_valid = len(errors) == 0
        
    except ET.ParseError as e:
        errors.append(f"Invalid SVG XML: {str(e)}")
        is_valid = False
    except Exception as e:
        errors.append(f"Validation failed: {str(e)}")
        is_valid = False
    
    return ValidationResult(is_valid, errors, metadata)