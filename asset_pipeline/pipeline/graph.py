from langgraph.graph import StateGraph
from pipeline.state import PipelineState
from pipeline.nodes import (
    load_input_node,
    plan_job_node,
    build_prompt_node,
    generate_images_node,
    validate_outputs_node,
    retry_or_finalize_node,
    postprocess_and_save_node,
    checkpoint_node,
)


def create_asset_pipeline_graph():
    """Create the LangGraph for asset generation pipeline."""
    
    # Create the graph
    workflow = StateGraph(PipelineState)
    
    # Add nodes
    workflow.add_node("load_input", load_input_node)
    workflow.add_node("plan_job", plan_job_node)
    workflow.add_node("build_prompt", build_prompt_node)
    workflow.add_node("generate_images", generate_images_node)
    workflow.add_node("validate_outputs", validate_outputs_node)
    workflow.add_node("postprocess_and_save", postprocess_and_save_node)
    workflow.add_node("checkpoint", checkpoint_node)
    
    # Define edges
    workflow.add_edge("load_input", "plan_job")
    workflow.add_edge("plan_job", "build_prompt")
    workflow.add_edge("build_prompt", "generate_images")
    workflow.add_edge("generate_images", "validate_outputs")
    workflow.add_edge("validate_outputs", "postprocess_and_save")
    workflow.add_edge("postprocess_and_save", "checkpoint")
    
    # Set entry point
    workflow.set_entry_point("load_input")
    
    # Set entry point
    workflow.set_entry_point("load_input")
    
    # Compile the graph
    return workflow.compile()


# Create the graph instance
asset_pipeline_graph = create_asset_pipeline_graph()