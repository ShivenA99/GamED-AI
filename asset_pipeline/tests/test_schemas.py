import json
from pathlib import Path

from models import PNGAssetConfig, SVGAssetConfig, SpriteAssetConfig


def test_png_schema_validation():
    """Test PNG asset config validation."""
    fixture_path = Path(__file__).parent / "fixtures" / "png_example.json"
    
    with open(fixture_path) as f:
        data = json.load(f)
    
    config = PNGAssetConfig(**data)
    assert config.job.assetType == "png"
    assert config.imagenConfig.aspectRatio == "3:4"
    print("PNG schema test passed")


def test_svg_schema_validation():
    """Test SVG asset config validation."""
    fixture_path = Path(__file__).parent / "fixtures" / "svg_example.json"
    
    with open(fixture_path) as f:
        data = json.load(f)
    
    config = SVGAssetConfig(**data)
    assert config.job.assetType == "svg"
    assert config.imagenConfig.aspectRatio == "1:1"
    print("SVG schema test passed")


def test_sprite_schema_validation():
    """Test sprite asset config validation."""
    fixture_path = Path(__file__).parent / "fixtures" / "sprite_example.json"
    
    with open(fixture_path) as f:
        data = json.load(f)
    
    config = SpriteAssetConfig(**data)
    assert config.job.assetType == "sprite"
    assert config.assetSpec.sprite.frameCount == 8
    print("Sprite schema test passed")


if __name__ == "__main__":
    test_png_schema_validation()
    test_svg_schema_validation()
    test_sprite_schema_validation()
    print("All schema tests passed!")