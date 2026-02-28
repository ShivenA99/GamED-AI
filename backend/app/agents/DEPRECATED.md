# Deprecated & Experimental Agents

This document tracks agents that are not part of the production pipeline.

---

## Deprecated Agents

These agents have been superseded by newer implementations.

### `qwen_label_remover.py`
- **Status**: DEPRECATED
- **Superseded by**: `image_label_remover.py` + `qwen_annotation_detector.py`
- **Reason**: The original approach combined detection and inpainting in one agent. The new architecture separates concerns:
  - `qwen_annotation_detector.py` handles detection of text labels and leader lines
  - `image_label_remover.py` handles the inpainting/removal
- **Keep for**: Reference implementation showing VLM-based detection + LaMa inpainting

### `qwen_zone_detector.py`
- **Status**: DEPRECATED
- **Superseded by**: `qwen_sam_zone_detector.py`
- **Reason**: The new `qwen_sam_zone_detector.py` combines:
  - SAM3 segmentation for precise zone boundaries
  - Qwen VL for label assignment based on leader line endpoints
- **Keep for**: Reference for per-label VLM detection approach

---

## Experimental Agents

These agents implement alternative approaches not used in production.

### `smart_zone_detector.py`
- **Status**: EXPERIMENTAL
- **Alternative to**: `qwen_sam_zone_detector.py`
- **Approach**: Uses SAM3 + CLIP for zone detection and labeling
- **Why not in production**: CLIP semantic matching is less accurate than Qwen VL for educational diagrams
- **Keep for**: Experimentation with CLIP-based approaches

### `smart_inpainter.py`
- **Status**: EXPERIMENTAL
- **Alternative to**: `image_label_remover.py`
- **Approach**: Multi-method inpainting with LaMa/SD/OpenCV fallback
- **Why not in production**: Designed to work with `combined_label_detector.py` which is also experimental
- **Keep for**: Testing advanced inpainting methods (Stable Diffusion)

### `combined_label_detector.py`
- **Status**: EXPERIMENTAL
- **Alternative to**: `qwen_annotation_detector.py`
- **Approach**: EasyOCR + Hough Transform + optional CLIP filtering
- **Why not in production**: VLM-based detection (Qwen) provides better accuracy for varied diagram styles
- **Keep for**: Testing non-VLM detection approaches

---

## Production Pipeline Agents (Current)

For reference, the current production pipeline uses these agents for labeled diagram processing:

1. **Classification**: `image_label_classifier.py` - Determines if diagram is labeled or unlabeled
2. **For Labeled Diagrams**:
   - `qwen_annotation_detector.py` - Detects text labels and leader lines
   - `image_label_remover.py` - Removes detected annotations via inpainting
   - `qwen_sam_zone_detector.py` - Creates zones from leader line endpoints using SAM3
3. **For Unlabeled Diagrams**:
   - `direct_structure_locator.py` - Fast path using Qwen VL to directly locate structures

---

## Migration Guide

If you're maintaining code that imports deprecated agents:

```python
# OLD (deprecated)
from app.agents.qwen_label_remover import qwen_label_remover

# NEW (production)
from app.agents.qwen_annotation_detector import qwen_annotation_detector
from app.agents.image_label_remover import image_label_remover
```

```python
# OLD (deprecated)
from app.agents.qwen_zone_detector import qwen_zone_detector

# NEW (production)
from app.agents.qwen_sam_zone_detector import qwen_sam_zone_detector
```

---

*Last updated: January 2026*
