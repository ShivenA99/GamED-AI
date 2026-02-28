# Multi-Asset Image Generation Pipeline

A production-ready image asset generation pipeline for interactive games, built with LangGraph and Google Gemini Imagen.

## Features

- **Three Asset Types**: PNG (raster), SVG (vector icons), Sprite (animation frames)
- **Robust Validation**: Pydantic schemas with asset-type-specific validation
- **Retry Logic**: Automatic repair loops with feedback for failed generations
- **Checkpointing**: Resume interrupted jobs safely
- **LangGraph Orchestration**: Structured pipeline with proper state management
- **Production Ready**: Comprehensive logging, metadata, and manifest generation

## Installation

```bash
pip install -e .
```

Set your Google API key:
```bash
export GOOGLE_API_KEY=your_api_key_here
```

## Quick Start

Run with example configurations:

```bash
# PNG asset generation
python -m asset_pipeline.cli.main --input tests/fixtures/png_example.json

# SVG icon generation
python -m asset_pipeline.cli.main --input tests/fixtures/svg_example.json

# Sprite sheet generation
python -m asset_pipeline.cli.main --input tests/fixtures/sprite_example.json
```

## Architecture

The pipeline uses LangGraph with the following nodes:

1. **load_input** → Parse and validate JSON input
2. **plan_job** → Plan based on asset type
3. **build_prompt** → Compile optimized prompts
4. **generate_images** → Call Google Imagen API
5. **validate_outputs** → Asset-type-specific validation
6. **retry_or_finalize** → Handle failures with repair loops
7. **postprocess_and_save** → Save assets with metadata
8. **checkpoint** → Persist state for resume

## Asset Types

### PNG Assets
- Production raster assets with gradients and shading
- Optimized for inventory/UI elements
- 3:4 aspect ratio, studio lighting

### SVG Assets
- Flat vector icons for UI
- No gradients, minimal colors (2-4)
- 1:1 square aspect ratio
- Post-processed with potrace/SVGO

### Sprite Assets
- Animation frames packed into sprite sheets
- Consistent character design across frames
- Frame-by-frame generation with consistency rules

## Configuration

Each asset type has its own Pydantic schema with optimized settings:

- **Model Selection**: Imagen 4.0 primary, with Gemini fallback
- **Safety Settings**: Configurable harm category blocking
- **Validation Rules**: Dimensions, file size, transparency, sharpness
- **Retry Logic**: Bounded attempts with backoff and repair directives
- **Output**: Structured directory layout with metadata and manifests

## Output Structure

```
assets/
├── {projectId}/
│   └── {topicId}/
│       └── {assetType}/
│           └── {assetId}/
│               └── v{version}/
│                   ├── asset.png          # PNG
│                   ├── asset_raster.png   # SVG raster
│                   ├── asset.svg          # SVG vector
│                   ├── sprite_sheet.png   # Sprite sheet
│                   ├── frames/            # Individual frames
│                   ├── metadata.json      # Provenance data
│                   ├── manifest.json      # Output index
│                   └── thumbnails/        # Auto-generated thumbs
```

## Development

Run tests:
```bash
pytest
```

Install development dependencies:
```bash
pip install -e ".[dev]"
```

## License

MIT License