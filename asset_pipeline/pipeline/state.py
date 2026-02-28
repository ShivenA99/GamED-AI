from typing import Any, Dict, List, Optional, TypedDict


class PipelineState(TypedDict, total=False):
    # Input
    input_json: Dict[str, Any]
    asset_type: str
    
    # Parsed config
    config: Optional[Any]  # Union of PNGAssetConfig, etc.
    
    # Job planning
    job_plan: Optional[Dict[str, Any]]
    
    # Prompt building
    compiled_prompt: Optional[str]
    prompt_audit: Optional[Dict[str, Any]]
    
    # Generation
    generated_images: List[Dict[str, Any]]
    generation_metadata: Optional[Dict[str, Any]]
    
    # Validation
    validation_results: List[Dict[str, Any]]
    is_valid: bool
    
    # Retry
    attempt_count: int
    repair_directives: List[str]
    
    # Finalization
    output_paths: List[str]
    metadata_path: Optional[str]
    manifest_path: Optional[str]
    
    # Checkpoint
    checkpoint_id_value: Optional[str]
    
    # Error handling
    errors: List[str]
    status: str