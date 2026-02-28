"""Local file storage for generated assets."""

import hashlib
import json
import os
import shutil
from pathlib import Path
from datetime import datetime, timezone


ASSETS_ROOT = Path(__file__).parent.parent.parent.parent / "assets" / "demo"


class AssetStorage:
    """Manages local storage of generated game assets.

    Directory layout:
        assets/demo/{game_id}/
            manifest.json          # Lists all assets with metadata
            diagram.png            # Main diagram (if applicable)
            zones.json             # Detected zones
            items/                 # Per-item images
                item_001.png
                item_002.png
            icons/                 # SVG icons
                icon_heart.svg
            patterns/              # SVG patterns
                card_back.svg
            crops/                 # Zoom crops
                zone_001.png
    """

    def __init__(self, root: Path | None = None):
        self.root = root or ASSETS_ROOT
        self.root.mkdir(parents=True, exist_ok=True)

    def game_dir(self, game_id: str) -> Path:
        d = self.root / game_id
        d.mkdir(parents=True, exist_ok=True)
        return d

    def save_image(self, game_id: str, filename: str, data: bytes, subdir: str = "") -> str:
        """Save image bytes to disk. Returns the URL path for frontend."""
        gdir = self.game_dir(game_id)
        if subdir:
            target = gdir / subdir
            target.mkdir(parents=True, exist_ok=True)
        else:
            target = gdir
        filepath = target / filename
        filepath.write_bytes(data)
        # URL: /api/assets/demo/{game_id}/[subdir/]filename
        rel = filepath.relative_to(self.root)  # relative to assets/demo/
        return f"/api/assets/demo/{rel}"

    def save_svg(self, game_id: str, filename: str, svg_code: str, subdir: str = "icons") -> str:
        """Save SVG code to disk. Returns the URL path."""
        gdir = self.game_dir(game_id)
        target = gdir / subdir
        target.mkdir(parents=True, exist_ok=True)
        filepath = target / filename
        filepath.write_text(svg_code, encoding="utf-8")
        rel = filepath.relative_to(self.root)
        return f"/api/assets/demo/{rel}"

    def save_json(self, game_id: str, filename: str, data: dict) -> Path:
        """Save JSON data to disk. Returns file path."""
        gdir = self.game_dir(game_id)
        filepath = gdir / filename
        filepath.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return filepath

    def save_manifest(self, game_id: str, manifest: dict) -> Path:
        """Save asset manifest."""
        manifest["generated_at"] = datetime.now(timezone.utc).isoformat()
        return self.save_json(game_id, "manifest.json", manifest)

    def get_asset_path(self, game_id: str, filename: str, subdir: str = "") -> Path:
        """Get the filesystem path for an asset."""
        gdir = self.game_dir(game_id)
        if subdir:
            return gdir / subdir / filename
        return gdir / filename

    def asset_exists(self, game_id: str, filename: str, subdir: str = "") -> bool:
        return self.get_asset_path(game_id, filename, subdir).exists()

    @staticmethod
    def compute_hash(data: bytes) -> str:
        return hashlib.sha256(data).hexdigest()[:16]
