import hashlib
import json
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime


class ArtifactStore:
    """Handle storage of generated assets and metadata."""
    
    def __init__(self, base_dir: str):
        self.base_dir = Path(base_dir)
    
    def get_output_dir(self, config: Any) -> Path:
        """Get the output directory for an asset."""
        return (
            self.base_dir /
            config.job.projectId /
            config.job.topicId /
            config.job.assetType /
            config.job.assetId /
            f"v{config.job.version}"
        )
    
    def save_asset(self, content: bytes, filename: str, config: Any) -> str:
        """Save an asset file and return its path."""
        output_dir = self.get_output_dir(config)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = output_dir / filename
        with open(file_path, 'wb') as f:
            f.write(content)
        
        return str(file_path)
    
    def save_metadata(self, metadata: Dict[str, Any], config: Any) -> str:
        """Save metadata JSON."""
        output_dir = self.get_output_dir(config)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        metadata_path = output_dir / "metadata.json"
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2, default=str)
        
        return str(metadata_path)
    
    def save_manifest(self, manifest: Dict[str, Any], config: Any) -> str:
        """Save manifest JSON."""
        output_dir = self.get_output_dir(config)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        manifest_path = output_dir / "manifest.json"
        with open(manifest_path, 'w') as f:
            json.dump(manifest, f, indent=2, default=str)
        
        return str(manifest_path)
    
    def compute_hashes(self, content: bytes) -> Dict[str, str]:
        """Compute content hashes."""
        return {
            "sha256": hashlib.sha256(content).hexdigest(),
            "md5": hashlib.md5(content).hexdigest(),
        }
    
    def create_manifest(
        self,
        config: Any,
        output_paths: List[str],
        input_hash: str,
        prompt_hash: str
    ) -> Dict[str, Any]:
        """Create a manifest for the asset."""
        return {
            "jobId": config.job.jobId,
            "assetId": config.job.assetId,
            "assetType": config.job.assetType,
            "version": config.job.version,
            "createdAt": datetime.now().isoformat(),
            "inputHash": input_hash,
            "promptHash": prompt_hash,
            "model": config.model.name,
            "outputs": output_paths,
            "thumbnails": [],  # Would be populated if thumbnails are generated
        }