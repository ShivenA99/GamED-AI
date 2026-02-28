from models.sprite_schema import SpritePromptSpec, SpriteAssetSpec


def build_sprite_prompt(spec: SpritePromptSpec, frame_n: int, total_frames: int, sprite_spec: SpriteAssetSpec) -> str:
    frame_desc = sprite_spec.sprite.framePrompts[frame_n] if frame_n < len(sprite_spec.sprite.framePrompts) else f"Frame {frame_n+1}"
    
    parts = [
        spec.subject,
        f"Frame {frame_n+1} of {total_frames}: {frame_desc}",
        spec.context,
        spec.style,
        ", ".join(spec.qualityModifiers),
        ", ".join(sprite_spec.sprite.consistencyRules),
        spec.aspectRatioHint
    ]
    return ". ".join(filter(None, parts))