from typing import Dict, Any
from pathlib import Path
import subprocess
import json


class Vectorizer:
    """Convert raster images to SVG vectors."""
    
    def __init__(self):
        pass
    
    def vectorize_image(
        self,
        input_path: str,
        output_path: str,
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Vectorize a raster image to SVG."""
        
        tool = config.get("vectorizeTool", "potrace")
        
        if tool == "potrace":
            # Use potrace for vectorization
            svg_path = Path(output_path)
            bmp_path = svg_path.with_suffix('.bmp')
            
            # Convert to BMP first if needed
            # Mock: assume input is already suitable
            
            # Run potrace
            cmd = [
                "potrace",
                "-s",  # SVG output
                "-o", str(svg_path),
                input_path
            ]
            
            try:
                subprocess.run(cmd, check=True)
                
                # Optimize with SVGO if configured
                if config.get("optimize", {}).get("tool") == "svgo":
                    svgo_cmd = ["svgo", str(svg_path)]
                    subprocess.run(svgo_cmd, check=True)
                
                return {
                    "svg_path": str(svg_path),
                    "tool_used": "potrace",
                    "optimized": config.get("optimize", {}).get("tool") == "svgo"
                }
            except subprocess.CalledProcessError as e:
                raise RuntimeError(f"Vectorization failed: {e}")
        
        else:
            raise ValueError(f"Unsupported vectorization tool: {tool}")