from validators import validate_png, validate_svg, validate_sprite


def test_png_validator():
    """Test PNG validation."""
    # Mock image path
    image_path = "/tmp/mock.png"
    
    # Mock spec
    spec = {
        "validationSpec": {
            "transparencyRequired": True,
            "maxFileSizeKB": 800
        }
    }
    
    result = validate_png(image_path, spec)
    # Since file doesn't exist, should fail
    assert not result.is_valid
    assert "does not exist" in result.errors[0]
    print("PNG validator test passed")


def test_svg_validator():
    """Test SVG validation."""
    # Mock SVG path
    svg_path = "/tmp/mock.svg"
    
    spec = {
        "assetSpec": {
            "svg": {
                "disallowRasterEmbeds": True,
                "maxPaths": 2000
            }
        },
        "validationSpec": {
            "maxFileSizeKB": 200
        }
    }
    
    result = validate_svg(svg_path, spec)
    assert not result.is_valid
    assert "does not exist" in result.errors[0]
    print("SVG validator test passed")


def test_sprite_validator():
    """Test sprite validation."""
    sheet_path = "/tmp/mock_sheet.png"
    
    spec = {
        "assetSpec": {
            "sprite": {
                "frameCount": 8,
                "frameSize": {"w": 256, "h": 256},
                "grid": {"cols": 4, "rows": 2},
                "paddingPx": 4
            }
        }
    }
    
    result = validate_sprite(sheet_path, spec)
    assert not result.is_valid
    assert "does not exist" in result.errors[0]
    print("Sprite validator test passed")


if __name__ == "__main__":
    test_png_validator()
    test_svg_validator()
    test_sprite_validator()
    print("All validator tests passed!")