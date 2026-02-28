from models.svg_schema import SVGPromptSpec


def build_svg_prompt(spec: SVGPromptSpec) -> str:
    parts = [
        spec.subject,
        spec.context,
        spec.style,
        ", ".join(spec.qualityModifiers),
        spec.photography.lighting,
        spec.aspectRatioHint
    ]
    return ". ".join(filter(None, parts))