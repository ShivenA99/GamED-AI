#!/usr/bin/env python3
"""CLI entry point for the asset pipeline."""

import argparse
import json
import sys
from pathlib import Path

from pipeline.graph import asset_pipeline_graph
from pipeline.state import PipelineState


def main():
    parser = argparse.ArgumentParser(description="Multi-Asset Image Generation Pipeline")
    parser.add_argument(
        "--input",
        required=True,
        help="Path to JSON input file"
    )
    parser.add_argument(
        "--output-dir",
        default="./assets",
        help="Base output directory"
    )
    
    args = parser.parse_args()
    
    # Load input JSON
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: Input file {input_path} does not exist")
        sys.exit(1)
    
    with open(input_path) as f:
        input_data = json.load(f)
    
    # Create initial state
    initial_state = {
        "input_json": input_data,
        "asset_type": input_data.get("job", {}).get("assetType", "unknown"),
        "status": "initialized"
    }
    
    # Run the pipeline
    try:
        final_state = asset_pipeline_graph.invoke(
            initial_state,
            config={"recursion_limit": 10}
        )
        
        if final_state["status"] == "completed":
            print("Pipeline completed successfully!")
            print(f"Outputs saved to: {final_state.get('output_paths', [])}")
            if final_state.get("metadata_path"):
                print(f"Metadata: {final_state['metadata_path']}")
            if final_state.get("manifest_path"):
                print(f"Manifest: {final_state['manifest_path']}")
        else:
            print(f"Pipeline failed with status: {final_state['status']}")
            if final_state.get("errors"):
                print("Errors:")
                for error in final_state["errors"]:
                    print(f"  - {error}")
            sys.exit(1)
            
    except Exception as e:
        print(f"Pipeline execution failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()