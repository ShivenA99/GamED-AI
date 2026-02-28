"""
CLIP Zone Labeling Service.

Uses CLIP to match detected zones to canonical labels from domain knowledge.
This provides semantic matching between image regions and expected labels,
without requiring a VLM to describe each zone.

The approach:
1. Crop each detected zone from the image
2. Use CLIP to compute similarity between the crop and each canonical label
3. Assign the most similar label to each zone
4. Handle conflicts using confidence scores and spatial reasoning
"""

import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger("gamed_ai.services.clip_labeling")


class CLIPZoneLabeler:
    """
    Label detected zones using CLIP similarity matching.

    Given a list of zones (with bounding boxes) and a list of canonical labels,
    this service matches each zone to the most similar label using CLIP.
    """

    def __init__(self, model_name: str = "openai/clip-vit-base-patch32"):
        """
        Initialize the CLIP zone labeler.

        Args:
            model_name: HuggingFace model name for CLIP
        """
        self.model_name = os.getenv("CLIP_MODEL", model_name)
        self._model = None
        self._processor = None
        self._device = None
        logger.info(f"CLIPZoneLabeler initialized with model: {self.model_name}")

    def _ensure_loaded(self):
        """Lazy load the CLIP model."""
        if self._model is not None:
            return

        try:
            import torch
            from transformers import CLIPProcessor, CLIPModel

            logger.info(f"Loading CLIP model: {self.model_name}")

            self._model = CLIPModel.from_pretrained(self.model_name)
            self._processor = CLIPProcessor.from_pretrained(self.model_name)

            # Use MPS on Mac, CUDA if available, otherwise CPU
            if torch.backends.mps.is_available():
                self._device = "mps"
            elif torch.cuda.is_available():
                self._device = "cuda"
            else:
                self._device = "cpu"

            self._model = self._model.to(self._device)
            logger.info(f"CLIP model loaded on device: {self._device}")

        except ImportError as e:
            logger.error(f"Failed to import transformers/torch: {e}")
            raise ImportError(
                "CLIP requires transformers and torch. Install with: "
                "pip install transformers torch"
            )

    async def is_available(self) -> bool:
        """Check if CLIP is available."""
        try:
            import transformers  # noqa: F401
            import torch  # noqa: F401
            return True
        except ImportError:
            return False

    def label_zone(
        self,
        zone_crop,
        canonical_labels: List[str],
        context_prefix: str = "anatomical diagram showing"
    ) -> Dict[str, Any]:
        """
        Match a zone crop to the best canonical label using CLIP.

        Args:
            zone_crop: PIL Image of the cropped zone
            canonical_labels: List of possible labels to match
            context_prefix: Prefix to add to labels for better matching

        Returns:
            Dict with:
                - label: Best matching label
                - confidence: Confidence score (0-1)
                - all_scores: Dict of all label scores
        """
        import torch

        self._ensure_loaded()

        # Enhance labels with context for better matching
        enhanced_labels = [f"{context_prefix} {label}" for label in canonical_labels]

        # Prepare inputs
        inputs = self._processor(
            text=enhanced_labels,
            images=zone_crop,
            return_tensors="pt",
            padding=True
        )

        # Move to device
        inputs = {k: v.to(self._device) for k, v in inputs.items()}

        # Get similarities
        with torch.no_grad():
            outputs = self._model(**inputs)
            logits = outputs.logits_per_image
            probs = logits.softmax(dim=1)[0].cpu().numpy()

        # Find best match
        best_idx = int(np.argmax(probs))

        # Create scores dict with original labels (not enhanced)
        all_scores = {label: float(probs[i]) for i, label in enumerate(canonical_labels)}

        return {
            "label": canonical_labels[best_idx],
            "confidence": float(probs[best_idx]),
            "all_scores": all_scores
        }

    def label_all_zones(
        self,
        image,
        zones: List[Dict[str, Any]],
        canonical_labels: List[str],
        context_prefix: str = "anatomical diagram showing",
        min_confidence: float = 0.1
    ) -> List[Dict[str, Any]]:
        """
        Label all zones using CLIP, ensuring unique label assignment.

        Uses a greedy assignment strategy:
        1. For each zone, compute similarity to all labels
        2. Assign highest-confidence matches first
        3. Remove assigned labels from consideration

        Args:
            image: PIL Image
            zones: List of zones with bbox
            canonical_labels: List of labels to match
            context_prefix: Context prefix for labels
            min_confidence: Minimum confidence to assign a label

        Returns:
            Zones with added 'label' and 'label_confidence' fields
        """
        from PIL import Image

        self._ensure_loaded()

        if not zones:
            return []

        if not canonical_labels:
            logger.warning("No canonical labels provided - zones will be unlabeled")
            return zones

        logger.info(f"Labeling {len(zones)} zones with {len(canonical_labels)} canonical labels")

        # Compute all scores
        zone_scores = []
        for i, zone in enumerate(zones):
            bbox = zone["bbox"]

            # Crop zone from image
            crop = image.crop((
                bbox["x"],
                bbox["y"],
                bbox["x"] + bbox["width"],
                bbox["y"] + bbox["height"]
            ))

            # Skip very small crops
            if crop.width < 10 or crop.height < 10:
                zone_scores.append({"zone_idx": i, "scores": {}})
                continue

            # Get scores for this zone
            result = self.label_zone(crop, canonical_labels, context_prefix)
            zone_scores.append({
                "zone_idx": i,
                "scores": result["all_scores"]
            })

        # Greedy assignment: assign highest confidence matches first
        labeled_zones = [zone.copy() for zone in zones]
        assigned_labels = set()

        # Create list of (zone_idx, label, score) tuples
        all_assignments = []
        for zs in zone_scores:
            for label, score in zs["scores"].items():
                all_assignments.append((zs["zone_idx"], label, score))

        # Sort by score descending
        all_assignments.sort(key=lambda x: x[2], reverse=True)

        # Assign greedily
        assigned_zones = set()
        for zone_idx, label, score in all_assignments:
            if zone_idx in assigned_zones:
                continue
            if label in assigned_labels:
                continue
            if score < min_confidence:
                continue

            labeled_zones[zone_idx]["label"] = label
            labeled_zones[zone_idx]["label_confidence"] = score
            assigned_labels.add(label)
            assigned_zones.add(zone_idx)

        # Handle unassigned zones
        for i, zone in enumerate(labeled_zones):
            if "label" not in zone:
                zone["label"] = "unknown"
                zone["label_confidence"] = 0.0

        # Log results
        assigned_count = sum(1 for z in labeled_zones if z["label"] != "unknown")
        logger.info(f"Assigned labels to {assigned_count}/{len(zones)} zones")

        return labeled_zones

    def label_zones_with_fallback(
        self,
        image,
        zones: List[Dict[str, Any]],
        canonical_labels: List[str],
        context_prefix: str = "anatomical diagram showing"
    ) -> Tuple[List[Dict[str, Any]], List[str]]:
        """
        Label zones with fallback for unmatched labels.

        If some canonical labels aren't matched to any zone, they are
        returned as 'missing' so the caller can handle them.

        Args:
            image: PIL Image
            zones: List of zones
            canonical_labels: Expected labels
            context_prefix: Context for labels

        Returns:
            Tuple of (labeled_zones, missing_labels)
        """
        labeled_zones = self.label_all_zones(
            image, zones, canonical_labels, context_prefix
        )

        # Find missing labels
        assigned = {z["label"] for z in labeled_zones if z["label"] != "unknown"}
        missing = [l for l in canonical_labels if l not in assigned]

        if missing:
            logger.warning(f"Missing labels not matched to zones: {missing}")

        return labeled_zones, missing

    def get_label_embeddings(
        self,
        labels: List[str],
        context_prefix: str = "anatomical diagram showing"
    ) -> np.ndarray:
        """
        Compute CLIP embeddings for a list of labels.

        Useful for caching embeddings when labeling multiple images
        with the same set of labels.

        Args:
            labels: List of label strings
            context_prefix: Context prefix

        Returns:
            Numpy array of shape (num_labels, embedding_dim)
        """
        import torch

        self._ensure_loaded()

        enhanced = [f"{context_prefix} {label}" for label in labels]

        inputs = self._processor(
            text=enhanced,
            return_tensors="pt",
            padding=True
        )

        inputs = {k: v.to(self._device) for k, v in inputs.items()}

        with torch.no_grad():
            text_features = self._model.get_text_features(**inputs)
            text_features = text_features / text_features.norm(dim=-1, keepdim=True)

        return text_features.cpu().numpy()

    def get_image_embedding(self, image) -> np.ndarray:
        """
        Compute CLIP embedding for an image.

        Args:
            image: PIL Image

        Returns:
            Numpy array of shape (embedding_dim,)
        """
        import torch

        self._ensure_loaded()

        inputs = self._processor(images=image, return_tensors="pt")
        inputs = {k: v.to(self._device) for k, v in inputs.items()}

        with torch.no_grad():
            image_features = self._model.get_image_features(**inputs)
            image_features = image_features / image_features.norm(dim=-1, keepdim=True)

        return image_features.cpu().numpy()[0]


# Singleton instance
_clip_labeler: Optional[CLIPZoneLabeler] = None


def get_clip_labeler() -> CLIPZoneLabeler:
    """Get or create the CLIP labeler singleton."""
    global _clip_labeler
    if _clip_labeler is None:
        _clip_labeler = CLIPZoneLabeler()
    return _clip_labeler
