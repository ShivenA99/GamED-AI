"""
State Validation for Retry Functionality

Validates that reconstructed state has all required keys before starting retry execution.
"""

from typing import Dict, List, Optional, Any, Tuple
from pydantic import BaseModel, Field, validator
import logging

logger = logging.getLogger("gamed_ai.schemas.state_validation")


class RetryStateValidation(BaseModel):
    """
    Pydantic model for validating retry state.
    
    Validates that all required fields are present before starting retry execution.
    """
    # Core required fields (always required)
    question_id: str = Field(..., description="Question ID - always required")
    question_text: str = Field(..., description="Question text - always required")
    
    # Optional fields (may be None)
    question_options: Optional[List[str]] = None
    pedagogical_context: Optional[Dict[str, Any]] = None
    template_selection: Optional[Dict[str, Any]] = None
    domain_knowledge: Optional[Dict[str, Any]] = None
    game_plan: Optional[Dict[str, Any]] = None
    scene_data: Optional[Dict[str, Any]] = None
    diagram_image: Optional[Dict[str, Any]] = None
    diagram_segments: Optional[Dict[str, Any]] = None
    diagram_zones: Optional[List[Dict[str, Any]]] = None
    diagram_labels: Optional[List[Dict[str, Any]]] = None
    cleaned_image_path: Optional[str] = None
    sam3_prompts: Optional[Dict[str, str]] = None
    blueprint: Optional[Dict[str, Any]] = None
    diagram_spec: Optional[Dict[str, Any]] = None
    
    class Config:
        extra = "allow"  # Allow additional fields from AgentState


# Stage-specific required keys map
# Based on extract_input_keys() from instrumentation.py
STAGE_REQUIRED_KEYS: Dict[str, List[str]] = {
    # Core pipeline stages
    "input_enhancer": ["question_text"],  # question_options is optional
    "domain_knowledge_retriever": ["question_text"],
    "router": ["question_text"],  # pedagogical_context may be None initially
    "game_planner": ["question_text", "template_selection"],
    "scene_generator": ["question_text", "game_plan", "template_selection"],
    
    # Diagram pipeline stages
    "diagram_image_retriever": ["question_text", "template_selection"],
    "image_label_remover": ["diagram_image"],
    "sam3_prompt_generator": ["template_selection", "cleaned_image_path", "diagram_image"],
    "diagram_image_segmenter": ["diagram_image", "sam3_prompts", "cleaned_image_path"],
    "diagram_zone_labeler": ["template_selection", "diagram_segments", "cleaned_image_path"],
    
    # Blueprint generator - critical stage
    "blueprint_generator": [
        "question_text",
        "template_selection",
        "game_plan",
        "scene_data"
    ],
    
    # Other generation stages
    "diagram_spec_generator": ["blueprint", "template_selection"],
    "diagram_svg_generator": ["diagram_spec", "diagram_image"],
    "code_generator": ["blueprint", "template_selection"],
    "asset_generator": ["blueprint"],
    
    # Validation stages
    "blueprint_validator": ["blueprint", "template_selection"],
    "diagram_spec_validator": ["diagram_spec"],
    "code_verifier": ["generated_code", "blueprint"],
    
    # Human review
    "human_review": [],  # No specific requirements
}


def validate_retry_state(
    state: Dict[str, Any],
    from_stage: str
) -> Tuple[bool, Optional[str]]:
    """
    Validate that reconstructed state has all required keys for retry.
    
    Args:
        state: Reconstructed state dictionary
        from_stage: Stage name to retry from
        
    Returns:
        Tuple of (is_valid, error_message)
        - is_valid: True if state is valid, False otherwise
        - error_message: Human-readable error message if invalid, None if valid
    """
    logger.info(f"Validating retry state for stage '{from_stage}'")
    
    # Always validate core required fields
    if not state.get("question_id"):
        logger.error(f"State validation failed: missing question_id for stage '{from_stage}'")
        return False, "Missing required field: question_id"
    
    if not state.get("question_text"):
        logger.error(f"State validation failed: missing question_text for stage '{from_stage}'")
        return False, "Missing required field: question_text"
    
    # Validate stage-specific requirements
    required_keys = STAGE_REQUIRED_KEYS.get(from_stage, [])
    missing_keys = []
    
    for key in required_keys:
        if key not in state or state[key] is None:
            missing_keys.append(key)
    
    if missing_keys:
        error_msg = (
            f"Missing required state keys for stage '{from_stage}': {', '.join(missing_keys)}. "
            f"State reconstruction may be incomplete. Please check that all previous stages completed successfully."
        )
        logger.error(f"State validation failed for stage '{from_stage}': {error_msg}")
        return False, error_msg
    
    # Try to validate with Pydantic model (for type checking)
    try:
        RetryStateValidation(**state)
        logger.debug(f"Pydantic validation passed for stage '{from_stage}'")
    except Exception as e:
        # Log warning but don't fail - Pydantic validation is strict
        logger.warning(f"Pydantic validation warning for retry state (stage '{from_stage}'): {e}")
        # Still return True if required keys are present
    
    logger.info(f"State validation passed for stage '{from_stage}'")
    return True, None
