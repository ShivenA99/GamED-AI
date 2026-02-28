from generators.sprite_packer import SpritePacker


def test_sprite_packer():
    """Test sprite packing functionality."""
    packer = SpritePacker()
    
    frame_paths = [f"/tmp/frame_{i}.png" for i in range(8)]
    output_path = "/tmp/sprite_sheet.png"
    
    sprite_spec = {
        "frameSize": {"w": 256, "h": 256},
        "grid": {"cols": 4, "rows": 2},
        "paddingPx": 4,
        "packOrder": "row_major",
        "fps": 12,
        "frameCount": 8
    }
    
    result = packer.pack_frames(frame_paths, output_path, sprite_spec)
    
    assert "sheet_path" in result
    assert "metadata_path" in result
    assert "metadata" in result
    assert result["metadata"]["frameCount"] == 8
    print("Sprite packer test passed")


if __name__ == "__main__":
    test_sprite_packer()
    print("All packer tests passed!")