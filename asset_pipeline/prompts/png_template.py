from models.png_schema import PNGPromptSpec


def build_png_prompt(spec: PNGPromptSpec) -> str:
    parts = [
        spec.subject,
        spec.context,
        spec.style,
        ", ".join(spec.qualityModifiers),
        f"{spec.photography.cameraProximity}, {spec.photography.cameraPosition}",
        spec.photography.lighting,
        spec.photography.cameraSettings,
        spec.aspectRatioHint
    ]
    return ". ".join(filter(None, parts))