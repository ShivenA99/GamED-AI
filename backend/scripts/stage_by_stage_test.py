#!/usr/bin/env python3
"""
Stage-by-Stage Pipeline Test Runner

A comprehensive test runner that:
1. Covers ALL 20+ pipeline stages
2. Saves each stage's output to a timestamped directory
3. Allows pausing between stages for manual inspection
4. Supports resuming from saved state
5. Records timing, errors, and metrics for each stage

Usage:
    # Interactive mode (default)
    PYTHONPATH=. python scripts/stage_by_stage_test.py "Label the parts of a flower"

    # Auto mode (non-interactive)
    PYTHONPATH=. python scripts/stage_by_stage_test.py --auto "Label the parts of a cell"

    # Resume from previous run
    PYTHONPATH=. python scripts/stage_by_stage_test.py --resume pipeline_outputs/test_runs/latest/ --from 10

    # Single stage mode
    PYTHONPATH=. python scripts/stage_by_stage_test.py --stage blueprint_generator --state path/to/state.json
"""

import argparse
import asyncio
import json
import logging
import os
import re
import shutil
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple
from dataclasses import dataclass, field, asdict

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("stage_by_stage_test")

# Suppress verbose logs from other modules
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("openai").setLevel(logging.WARNING)
logging.getLogger("anthropic").setLevel(logging.WARNING)

# ============================================================================
# AGENT IMPORTS
# ============================================================================

# Phase 1: Input Processing
from app.agents.input_enhancer import input_enhancer_agent
from app.agents.domain_knowledge_retriever import domain_knowledge_retriever_agent
from app.agents.router import router_agent

# Phase 2: Planning
from app.agents.game_planner import game_planner_agent
from app.agents.scene_stage1_structure import scene_stage1_structure
from app.agents.scene_stage2_assets import scene_stage2_assets
from app.agents.scene_stage3_interactions import scene_stage3_interactions

# Phase 3: Image Pipeline
from app.agents.diagram_image_retriever import diagram_image_retriever_agent
from app.agents.image_label_classifier import image_label_classifier
from app.agents.qwen_annotation_detector import qwen_annotation_detector
from app.agents.direct_structure_locator import direct_structure_locator
from app.agents.image_label_remover import image_label_remover_agent
from app.agents.qwen_sam_zone_detector import qwen_sam_zone_detector

# Phase 4: Blueprint & Assets
from app.agents.blueprint_generator import blueprint_generator_agent, validate_blueprint
from app.agents.asset_planner import asset_planner
from app.agents.asset_generator_orchestrator import asset_generator_orchestrator

# Phase 5: Diagram Generation
from app.agents.diagram_spec_generator import diagram_spec_generator_agent
from app.agents.diagram_svg_generator import diagram_svg_generator_agent

# Validators
from app.agents.playability_validator import playability_validator


# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class StageOutput:
    """Output from a single stage."""
    stage_name: str
    stage_order: int
    started_at: str
    completed_at: str
    duration_ms: int
    status: str  # 'success', 'error', 'skipped'
    input_keys: List[str]
    output_keys: List[str]
    output: Dict[str, Any]
    metrics: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


@dataclass
class RunManifest:
    """Manifest for a test run."""
    run_id: str
    question_text: str
    started_at: str
    completed_at: Optional[str] = None
    total_duration_ms: int = 0
    stages_completed: int = 0
    stages_failed: int = 0
    stages_skipped: int = 0
    image_classification: Optional[str] = None
    route_taken: List[str] = field(default_factory=list)
    total_tokens: int = 0
    stage_timings: Dict[str, int] = field(default_factory=dict)


# ============================================================================
# STAGE DEFINITIONS
# ============================================================================

# Define all stages in order with their agent functions
# Format: (stage_name, agent_function, description, required_input_keys, output_keys)
STAGE_DEFINITIONS = [
    # Phase 1: Input Processing
    ("input_enhancer", input_enhancer_agent, "Extract pedagogical context",
     ["question_text"], ["pedagogical_context"]),
    ("domain_knowledge_retriever", domain_knowledge_retriever_agent, "Search for canonical labels",
     ["question_text", "pedagogical_context"], ["domain_knowledge"]),
    ("router", router_agent, "Select game template",
     ["question_text", "pedagogical_context"], ["template_selection"]),

    # Phase 2: Planning
    ("game_planner", game_planner_agent, "Plan game mechanics",
     ["question_text", "template_selection", "pedagogical_context"], ["game_plan"]),
    ("scene_stage1_structure", scene_stage1_structure, "Define scene structure and regions",
     ["question_text", "game_plan", "template_selection"], ["scene_structure"]),
    ("scene_stage2_assets", scene_stage2_assets, "Populate regions with assets",
     ["question_text", "game_plan", "scene_structure"], ["scene_assets"]),
    ("scene_stage3_interactions", scene_stage3_interactions, "Define behaviors and interactions",
     ["game_plan", "scene_structure", "scene_assets"], ["scene_interactions", "scene_data"]),

    # Phase 3: Image Pipeline (INTERACTIVE_DIAGRAM only)
    ("diagram_image_retriever", diagram_image_retriever_agent, "Find diagram image from web",
     ["question_text", "template_selection"], ["diagram_image"]),
    ("image_label_classifier", image_label_classifier, "Classify diagram as labeled/unlabeled",
     ["diagram_image"], ["image_classification"]),
    # Conditional: labeled path
    ("qwen_annotation_detector", qwen_annotation_detector, "[LABELED] Detect text labels and leader lines",
     ["diagram_image", "image_classification"], ["annotation_elements", "text_labels_found"]),
    ("image_label_remover", image_label_remover_agent, "[LABELED] Inpaint to remove annotations",
     ["diagram_image", "annotation_elements"], ["cleaned_image_path", "removed_labels"]),
    ("qwen_sam_zone_detector", qwen_sam_zone_detector, "[LABELED] Create zones from endpoints using SAM3",
     ["cleaned_image_path", "annotation_elements", "domain_knowledge"], ["diagram_zones", "diagram_labels"]),
    # Conditional: unlabeled path
    ("direct_structure_locator", direct_structure_locator, "[UNLABELED] Locate structures directly",
     ["diagram_image", "domain_knowledge"], ["diagram_zones", "diagram_labels"]),

    # Phase 4: Blueprint & Assets
    ("blueprint_generator", blueprint_generator_agent, "Generate game blueprint JSON",
     ["template_selection", "game_plan", "scene_data", "domain_knowledge", "diagram_zones"], ["blueprint"]),
    ("blueprint_validator", None, "Validate blueprint structure and content",
     ["blueprint", "template_selection"], ["validation_results"]),
    ("asset_planner", asset_planner, "Plan required media assets",
     ["blueprint", "scene_data"], ["planned_assets"]),
    ("asset_generator_orchestrator", asset_generator_orchestrator, "Generate/retrieve game assets",
     ["planned_assets"], ["generated_assets"]),

    # Phase 5: Diagram Generation
    ("diagram_spec_generator", diagram_spec_generator_agent, "Generate SVG diagram specifications",
     ["blueprint"], ["diagram_spec"]),
    ("diagram_spec_validator", None, "Validate diagram specs",
     ["diagram_spec"], ["validation_results"]),
    ("diagram_svg_generator", diagram_svg_generator_agent, "Render final SVG",
     ["blueprint", "diagram_spec"], ["diagram_svg", "generation_complete"]),

    # Playability check
    ("playability_validator", playability_validator, "Validate game is completable",
     ["blueprint"], ["playability_valid", "playability_score", "playability_issues"]),
]

# Create lookup maps
STAGE_BY_NAME = {s[0]: s for s in STAGE_DEFINITIONS}
STAGE_ORDER = {s[0]: i + 1 for i, s in enumerate(STAGE_DEFINITIONS)}


# ============================================================================
# STAGE RUNNER
# ============================================================================

class StageRunner:
    """Runs pipeline stages one by one with output saving."""

    def __init__(
        self,
        output_dir: Path,
        interactive: bool = True,
        question_text: str = ""
    ):
        self.output_dir = output_dir
        self.interactive = interactive
        self.question_text = question_text
        self.state: Dict[str, Any] = {}
        self.manifest = RunManifest(
            run_id=output_dir.name,
            question_text=question_text,
            started_at=datetime.now(timezone.utc).isoformat()
        )
        self.stage_outputs: Dict[str, StageOutput] = {}

        # Ensure output directory exists
        output_dir.mkdir(parents=True, exist_ok=True)

    def initialize_state(self, question: str, question_id: str = "test_run") -> None:
        """Initialize the pipeline state with a question."""
        self.question_text = question
        self.manifest.question_text = question
        self.state = {
            "question_id": question_id,
            "question_text": question,
            "question_options": [],
            "auto_retry": True,
        }

    def load_state_from_dir(self, dir_path: Path, from_stage: int) -> None:
        """Load state from a previous run to resume."""
        # Try to load full_state.json first
        full_state_path = dir_path / "full_state.json"
        if full_state_path.exists():
            with open(full_state_path) as f:
                self.state = json.load(f)
            logger.info(f"Loaded full state from {full_state_path}")
            return

        # Otherwise, reconstruct from individual stage outputs
        for stage_num in range(1, from_stage):
            stage_files = list(dir_path.glob(f"{stage_num:02d}_*.json"))
            if stage_files:
                with open(stage_files[0]) as f:
                    stage_data = json.load(f)
                    if "output" in stage_data:
                        self.state.update(stage_data["output"])

        logger.info(f"Reconstructed state from {from_stage - 1} stage files")

    def should_skip_stage(self, stage_name: str) -> Tuple[bool, str]:
        """Determine if a stage should be skipped based on current state."""
        template_type = self.state.get("template_selection", {}).get("template_type", "")
        classification = self.state.get("image_classification", {}).get("classification", "")

        # Image pipeline stages only for INTERACTIVE_DIAGRAM
        image_pipeline_stages = [
            "diagram_image_retriever", "image_label_classifier",
            "qwen_annotation_detector", "image_label_remover",
            "qwen_sam_zone_detector", "direct_structure_locator"
        ]
        if stage_name in image_pipeline_stages and template_type != "INTERACTIVE_DIAGRAM":
            return True, f"Only runs for INTERACTIVE_DIAGRAM (current: {template_type})"

        # Labeled path stages
        labeled_stages = ["qwen_annotation_detector", "image_label_remover", "qwen_sam_zone_detector"]
        if stage_name in labeled_stages and classification == "unlabeled":
            return True, "Skipped (unlabeled diagram path)"

        # Unlabeled path stage
        if stage_name == "direct_structure_locator" and classification != "unlabeled":
            return True, "Skipped (labeled diagram path)"

        # Asset stages - skip if no planned assets
        if stage_name == "asset_generator_orchestrator":
            planned = self.state.get("planned_assets", [])
            if not planned:
                return True, "No assets to generate"

        return False, ""

    async def run_stage(
        self,
        stage_num: int,
        stage_name: str,
        agent_fn: Optional[Callable],
        description: str
    ) -> StageOutput:
        """Run a single stage and return the output."""
        started_at = datetime.now(timezone.utc).isoformat()
        start_time = time.time()

        # Check if should skip
        should_skip, skip_reason = self.should_skip_stage(stage_name)
        if should_skip:
            return StageOutput(
                stage_name=stage_name,
                stage_order=stage_num,
                started_at=started_at,
                completed_at=datetime.now(timezone.utc).isoformat(),
                duration_ms=0,
                status="skipped",
                input_keys=[],
                output_keys=[],
                output={},
                warnings=[skip_reason]
            )

        # Get stage definition
        stage_def = STAGE_BY_NAME.get(stage_name)
        if not stage_def:
            raise ValueError(f"Unknown stage: {stage_name}")

        _, _, _, input_keys, output_keys = stage_def

        # Handle special validator stages that don't have agent functions
        if agent_fn is None:
            if stage_name == "blueprint_validator":
                result = await self._run_blueprint_validator()
            elif stage_name == "diagram_spec_validator":
                result = await self._run_diagram_spec_validator()
            else:
                raise ValueError(f"No agent function for stage: {stage_name}")
        else:
            # Run the actual agent
            try:
                result = await agent_fn(self.state)
            except Exception as e:
                logger.error(f"Stage {stage_name} failed: {e}")
                traceback.print_exc()
                return StageOutput(
                    stage_name=stage_name,
                    stage_order=stage_num,
                    started_at=started_at,
                    completed_at=datetime.now(timezone.utc).isoformat(),
                    duration_ms=int((time.time() - start_time) * 1000),
                    status="error",
                    input_keys=input_keys,
                    output_keys=[],
                    output={},
                    errors=[str(e), traceback.format_exc()]
                )

        # Update state with result
        if result:
            self.state.update(result)

        duration_ms = int((time.time() - start_time) * 1000)

        # Extract actual output keys (only the ones we care about)
        actual_output = {}
        for key in output_keys:
            if key in self.state:
                actual_output[key] = self.state[key]

        return StageOutput(
            stage_name=stage_name,
            stage_order=stage_num,
            started_at=started_at,
            completed_at=datetime.now(timezone.utc).isoformat(),
            duration_ms=duration_ms,
            status="success",
            input_keys=input_keys,
            output_keys=list(actual_output.keys()),
            output=actual_output
        )

    async def _run_blueprint_validator(self) -> Dict[str, Any]:
        """Run blueprint validation."""
        blueprint = self.state.get("blueprint", {})
        template_type = blueprint.get("templateType",
            self.state.get("template_selection", {}).get("template_type", ""))

        validation_result = await validate_blueprint(
            blueprint,
            template_type,
            context={
                "question_text": self.state.get("question_text", ""),
                "pedagogical_context": self.state.get("pedagogical_context", {}),
                "domain_knowledge": self.state.get("domain_knowledge", {}),
                "diagram_zones": self.state.get("diagram_zones"),
                "diagram_image": self.state.get("diagram_image"),
            }
        )

        return {
            "validation_results": {
                "blueprint": {
                    "is_valid": validation_result.get("valid", False),
                    "errors": validation_result.get("errors", []),
                    "warnings": validation_result.get("warnings", [])
                }
            }
        }

    async def _run_diagram_spec_validator(self) -> Dict[str, Any]:
        """Run diagram spec validation."""
        from app.agents.schemas.interactive_diagram import DiagramSvgSpec

        spec = self.state.get("diagram_spec", {})
        errors = []
        is_valid = True

        try:
            DiagramSvgSpec.model_validate(spec)
        except Exception as e:
            is_valid = False
            errors.append(str(e))

        return {
            "validation_results": {
                "diagram_spec": {
                    "is_valid": is_valid,
                    "errors": errors,
                    "warnings": []
                }
            }
        }

    def save_stage_output(self, stage_num: int, stage_output: StageOutput) -> Path:
        """Save stage output to JSON file."""
        filename = f"{stage_num:02d}_{stage_output.stage_name}.json"
        filepath = self.output_dir / filename

        with open(filepath, 'w') as f:
            json.dump(asdict(stage_output), f, indent=2, default=str)

        return filepath

    def save_image_artifact(self, stage_num: int, name: str, source_path: str) -> Optional[Path]:
        """Save image artifacts (diagrams, masks, etc.)."""
        if not source_path or not Path(source_path).exists():
            return None

        ext = Path(source_path).suffix
        dest_filename = f"{stage_num:02d}_{name}{ext}"
        dest_path = self.output_dir / dest_filename

        shutil.copy2(source_path, dest_path)
        return dest_path

    def save_manifest(self) -> Path:
        """Save the run manifest."""
        manifest_path = self.output_dir / "manifest.json"
        with open(manifest_path, 'w') as f:
            json.dump(asdict(self.manifest), f, indent=2)
        return manifest_path

    def save_full_state(self) -> Path:
        """Save the complete final state."""
        state_path = self.output_dir / "full_state.json"
        with open(state_path, 'w') as f:
            json.dump(self.state, f, indent=2, default=str)
        return state_path

    def print_stage_summary(self, stage_output: StageOutput) -> None:
        """Print a summary of the stage output."""
        status_marker = {
            "success": "[OK]",
            "error": "[FAIL]",
            "skipped": "[SKIP]"
        }

        print(f"\n{'='*60}")
        print(f"  {status_marker.get(stage_output.status, '?')} Stage {stage_output.stage_order}: {stage_output.stage_name}")
        print(f"{'='*60}")
        print(f"  Status: {stage_output.status.upper()}")
        print(f"  Duration: {stage_output.duration_ms}ms")

        if stage_output.errors:
            print(f"  [!] Errors:")
            for err in stage_output.errors[:3]:
                print(f"     - {err[:100]}...")

        if stage_output.warnings:
            print(f"  [!] Warnings:")
            for warn in stage_output.warnings[:3]:
                print(f"     - {warn}")

        if stage_output.output:
            print(f"  Output keys: {list(stage_output.output.keys())}")
            # Print key values summary
            for key, value in stage_output.output.items():
                if isinstance(value, dict):
                    print(f"     - {key}: {{...}} ({len(value)} keys)")
                elif isinstance(value, list):
                    print(f"     - {key}: [...] ({len(value)} items)")
                elif isinstance(value, str) and len(value) > 50:
                    print(f"     - {key}: \"{value[:50]}...\"")
                else:
                    print(f"     - {key}: {value}")

    def prompt_user(self, stage_num: int, stage_name: str, description: str) -> str:
        """Interactive prompt for user action."""
        print(f"\n>> Next: Stage {stage_num} - {stage_name}")
        print(f"   {description}")
        print()
        print("  [Enter] Continue | [s] Skip | [r] Retry last | [i] Inspect | [q] Quit")

        try:
            choice = input(">>> ").strip().lower()
        except EOFError:
            choice = 'q'

        return choice

    def inspect_output(self, stage_name: str) -> None:
        """Allow user to inspect a stage's output."""
        if stage_name in self.stage_outputs:
            output = self.stage_outputs[stage_name]
            print(json.dumps(asdict(output), indent=2, default=str))
        else:
            # Look for the file
            files = list(self.output_dir.glob(f"*_{stage_name}.json"))
            if files:
                with open(files[0]) as f:
                    print(f.read())
            else:
                print(f"No output found for stage: {stage_name}")


# ============================================================================
# MAIN RUNNER
# ============================================================================

async def run_pipeline(
    question: str,
    output_dir: Path,
    interactive: bool = True,
    start_from: int = 1,
    resume_dir: Optional[Path] = None,
    single_stage: Optional[str] = None,
    state_file: Optional[Path] = None
) -> RunManifest:
    """Run the full pipeline or a subset of stages."""

    # Create runner
    runner = StageRunner(output_dir, interactive, question)

    # Initialize or load state
    if resume_dir:
        runner.load_state_from_dir(resume_dir, start_from)
    elif state_file:
        with open(state_file) as f:
            runner.state = json.load(f)
    else:
        runner.initialize_state(question)

    # Determine which stages to run
    if single_stage:
        stages_to_run = [(STAGE_ORDER[single_stage], *STAGE_BY_NAME[single_stage][:3])]
    else:
        stages_to_run = [
            (i + 1, s[0], s[1], s[2])
            for i, s in enumerate(STAGE_DEFINITIONS)
            if i + 1 >= start_from
        ]

    print("\n" + "="*60)
    print("  STAGE-BY-STAGE PIPELINE TEST RUNNER")
    print("="*60)
    print(f"\nQuestion: {question}")
    print(f"Output directory: {output_dir}")
    print(f"Stages to run: {len(stages_to_run)}")
    if interactive:
        print("\nRunning in INTERACTIVE mode. Press Enter to continue between stages.")
    else:
        print("\nRunning in AUTO mode.")

    current_stage = start_from - 1
    stages_completed = 0
    stages_failed = 0
    stages_skipped = 0

    for stage_num, stage_name, agent_fn, description in stages_to_run:
        current_stage = stage_num

        # Interactive prompt
        if interactive and stage_num > start_from:
            choice = runner.prompt_user(stage_num, stage_name, description)

            if choice == 'q':
                print("\n-- Exiting...")
                break
            elif choice == 's':
                print(f"   Skipping stage {stage_num}...")
                stages_skipped += 1
                continue
            elif choice == 'r' and stage_num > 1:
                # Re-run previous stage
                prev_stage = stages_to_run[stage_num - 2]
                print(f"   Retrying stage {prev_stage[0]}...")
                stage_output = await runner.run_stage(prev_stage[0], prev_stage[1], prev_stage[2], prev_stage[3])
                runner.print_stage_summary(stage_output)
                runner.save_stage_output(prev_stage[0], stage_output)
                continue
            elif choice == 'i':
                # Inspect previous stage output
                if stage_num > 1:
                    prev_name = stages_to_run[stage_num - 2][1]
                    runner.inspect_output(prev_name)
                continue

        # Run the stage
        print(f"\n>> Running stage {stage_num}: {stage_name}...")

        try:
            stage_output = await runner.run_stage(stage_num, stage_name, agent_fn, description)
            runner.stage_outputs[stage_name] = stage_output

            # Print summary
            runner.print_stage_summary(stage_output)

            # Save output
            runner.save_stage_output(stage_num, stage_output)

            # Save image artifacts if applicable
            if stage_name == "diagram_image_retriever" and stage_output.status == "success":
                diagram = runner.state.get("diagram_image", {})
                if diagram.get("local_path"):
                    saved = runner.save_image_artifact(stage_num, "diagram_image", diagram["local_path"])
                    if saved:
                        print(f"   [IMG] Saved diagram image: {saved.name}")

            if stage_name == "qwen_annotation_detector":
                mask_path = runner.state.get("detection_mask_path")
                if mask_path:
                    saved = runner.save_image_artifact(stage_num, "annotation_mask", mask_path)
                    if saved:
                        print(f"   [IMG] Saved annotation mask: {saved.name}")

            if stage_name == "image_label_remover":
                cleaned_path = runner.state.get("cleaned_image_path")
                if cleaned_path:
                    saved = runner.save_image_artifact(stage_num, "cleaned_image", cleaned_path)
                    if saved:
                        print(f"   [IMG] Saved cleaned image: {saved.name}")

            if stage_name == "qwen_sam_zone_detector":
                zones_viz_path = runner.state.get("zones_visualization_path")
                if zones_viz_path:
                    saved = runner.save_image_artifact(stage_num, "zones_visualization", zones_viz_path)
                    if saved:
                        print(f"   [IMG] Saved zones visualization: {saved.name}")

            if stage_name == "diagram_svg_generator":
                svg_content = runner.state.get("diagram_svg")
                if svg_content:
                    svg_path = runner.output_dir / f"{stage_num:02d}_final_diagram.svg"
                    with open(svg_path, 'w') as f:
                        f.write(svg_content)
                    print(f"   [IMG] Saved final SVG: {svg_path.name}")

            # Update manifest
            if stage_output.status == "success":
                stages_completed += 1
                runner.manifest.stage_timings[stage_name] = stage_output.duration_ms
            elif stage_output.status == "error":
                stages_failed += 1
            else:
                stages_skipped += 1

            # Track image classification
            if stage_name == "image_label_classifier":
                runner.manifest.image_classification = runner.state.get(
                    "image_classification", {}
                ).get("classification")
                runner.manifest.route_taken.append(
                    f"{runner.manifest.image_classification}_path"
                )

        except Exception as e:
            logger.error(f"Error in stage {stage_num} ({stage_name}): {e}")
            traceback.print_exc()
            stages_failed += 1

            if interactive:
                retry = input("\nRetry this stage? (y/n): ").strip().lower()
                if retry == 'y':
                    continue

    # Finalize manifest
    runner.manifest.completed_at = datetime.now(timezone.utc).isoformat()
    runner.manifest.stages_completed = stages_completed
    runner.manifest.stages_failed = stages_failed
    runner.manifest.stages_skipped = stages_skipped
    runner.manifest.total_duration_ms = sum(runner.manifest.stage_timings.values())

    # Save final outputs
    runner.save_manifest()
    runner.save_full_state()

    # Print summary
    print("\n" + "="*60)
    print("  PIPELINE RUN COMPLETE")
    print("="*60)
    print(f"\n  Stages completed: {stages_completed}")
    print(f"  Stages failed: {stages_failed}")
    print(f"  Stages skipped: {stages_skipped}")
    print(f"  Total duration: {runner.manifest.total_duration_ms}ms")
    print(f"\n  Outputs saved to: {runner.output_dir}")
    print(f"  - manifest.json: Run summary")
    print(f"  - full_state.json: Complete final state")
    print(f"  - XX_<stage>.json: Individual stage outputs")

    return runner.manifest


def create_output_dir(question: str) -> Path:
    """Create a timestamped output directory for a test run."""
    base_dir = Path(__file__).parent.parent / "pipeline_outputs" / "test_runs"
    base_dir.mkdir(parents=True, exist_ok=True)

    # Create slug from question
    slug = re.sub(r'[^a-z0-9]+', '_', question.lower())[:30].strip('_')
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    dir_name = f"{timestamp}_{slug}"
    output_dir = base_dir / dir_name
    output_dir.mkdir(parents=True, exist_ok=True)

    # Update 'latest' symlink
    latest_link = base_dir / "latest"
    if latest_link.is_symlink():
        latest_link.unlink()
    latest_link.symlink_to(output_dir.name)

    return output_dir


def main():
    parser = argparse.ArgumentParser(
        description="Stage-by-stage pipeline test runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive mode (default)
  PYTHONPATH=. python scripts/stage_by_stage_test.py "Label the parts of a flower"

  # Auto mode (non-interactive)
  PYTHONPATH=. python scripts/stage_by_stage_test.py --auto "Label the parts of a cell"

  # Resume from previous run
  PYTHONPATH=. python scripts/stage_by_stage_test.py --resume pipeline_outputs/test_runs/latest/ --from 10

  # Single stage mode
  PYTHONPATH=. python scripts/stage_by_stage_test.py --stage blueprint_generator --state path/to/state.json
        """
    )

    parser.add_argument("question", nargs="?", default="Label the parts of a flower",
                       help="The question/prompt to process")
    parser.add_argument("--auto", action="store_true",
                       help="Run in auto mode (no pauses)")
    parser.add_argument("--resume", type=Path,
                       help="Resume from a previous run directory")
    parser.add_argument("--from", dest="from_stage", type=int, default=1,
                       help="Start from this stage number")
    parser.add_argument("--stage", type=str,
                       help="Run only this single stage")
    parser.add_argument("--state", type=Path,
                       help="Load initial state from this JSON file")
    parser.add_argument("--output", type=Path,
                       help="Output directory (default: auto-generated)")
    parser.add_argument("--list-stages", action="store_true",
                       help="List all available stages and exit")

    args = parser.parse_args()

    # List stages mode
    if args.list_stages:
        print("\nAvailable Pipeline Stages:")
        print("="*60)
        for i, (name, _, desc, inputs, outputs) in enumerate(STAGE_DEFINITIONS, 1):
            print(f"  {i:2d}. {name}")
            print(f"      {desc}")
            print(f"      Inputs: {', '.join(inputs)}")
            print(f"      Outputs: {', '.join(outputs)}")
            print()
        return

    # Validate single stage
    if args.stage and args.stage not in STAGE_BY_NAME:
        print(f"Error: Unknown stage '{args.stage}'")
        print("Use --list-stages to see available stages")
        sys.exit(1)

    # Create output directory
    if args.output:
        output_dir = args.output
        output_dir.mkdir(parents=True, exist_ok=True)
    else:
        output_dir = create_output_dir(args.question)

    # Run pipeline
    asyncio.run(run_pipeline(
        question=args.question,
        output_dir=output_dir,
        interactive=not args.auto,
        start_from=args.from_stage,
        resume_dir=args.resume,
        single_stage=args.stage,
        state_file=args.state
    ))


if __name__ == "__main__":
    main()
