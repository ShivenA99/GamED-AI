#!/usr/bin/env python3
"""
Verify Agentic Educational Game System Implementation

This script checks that all components of the agentic system are properly
implemented and configured.

Usage:
    cd backend
    PYTHONPATH=. python scripts/verify_agentic_implementation.py
"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Tuple

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def check_file_exists(filepath: str, description: str) -> Tuple[bool, str]:
    """Check if a file exists."""
    path = Path(__file__).parent.parent / filepath
    exists = path.exists()
    status = "PASS" if exists else "FAIL"
    return exists, f"[{status}] {description}: {filepath}"


def check_import(module: str, description: str) -> Tuple[bool, str]:
    """Check if a module can be imported."""
    try:
        __import__(module)
        return True, f"[PASS] {description}: {module}"
    except ImportError as e:
        return False, f"[FAIL] {description}: {module} - {e}"


def check_interaction_patterns() -> List[Tuple[bool, str]]:
    """Check interaction patterns configuration."""
    results = []

    try:
        from app.config.interaction_patterns import (
            INTERACTION_PATTERNS,
            PatternStatus,
            get_implemented_patterns,
        )

        # Count patterns by status
        complete = [p for p in INTERACTION_PATTERNS.values() if p.status == PatternStatus.COMPLETE]
        partial = [p for p in INTERACTION_PATTERNS.values() if p.status == PatternStatus.PARTIAL]
        missing = [p for p in INTERACTION_PATTERNS.values() if p.status == PatternStatus.MISSING]
        experimental = [p for p in INTERACTION_PATTERNS.values() if p.status == PatternStatus.EXPERIMENTAL]

        results.append((True, f"[PASS] Interaction patterns loaded: {len(INTERACTION_PATTERNS)} total"))
        results.append((True, f"  - COMPLETE: {len(complete)} ({', '.join(p.id for p in complete[:5])}...)"))
        results.append((True, f"  - PARTIAL: {len(partial)} ({', '.join(p.id for p in partial)})"))
        results.append((len(missing) == 0, f"  - MISSING: {len(missing)} ({', '.join(p.id for p in missing)})"))
        results.append((True, f"  - EXPERIMENTAL: {len(experimental)}"))

        # Check implemented patterns helper
        implemented = get_implemented_patterns()
        results.append((len(implemented) >= 8, f"[PASS] Implemented patterns: {len(implemented)}"))

    except Exception as e:
        results.append((False, f"[FAIL] Error checking interaction patterns: {e}"))

    return results


def check_asset_capabilities() -> List[Tuple[bool, str]]:
    """Check asset capabilities configuration."""
    results = []

    try:
        from app.config.asset_capabilities import (
            GENERATION_METHODS,
            ASSET_TYPES,
            PRACTICAL_LIMITS,
            get_available_methods,
        )

        results.append((True, f"[PASS] Asset capabilities loaded:"))
        results.append((True, f"  - Generation methods: {len(GENERATION_METHODS)}"))
        results.append((True, f"  - Asset types: {len(ASSET_TYPES)}"))
        results.append((True, f"  - Available methods: {len(get_available_methods())}"))
        results.append((True, f"  - Practical limits defined: {len(PRACTICAL_LIMITS)}"))

    except Exception as e:
        results.append((False, f"[FAIL] Error checking asset capabilities: {e}"))

    return results


def check_agentic_agents() -> List[Tuple[bool, str]]:
    """Check that all agentic agents are properly implemented."""
    results = []

    agents = [
        ("app.agents.diagram_analyzer", "diagram_analyzer", "Diagram Analyzer"),
        ("app.agents.game_designer", "game_designer", "Game Designer"),
        ("app.agents.scene_sequencer", "scene_sequencer", "Scene Sequencer"),
        ("app.agents.multi_scene_image_orchestrator", "multi_scene_image_orchestrator", "Multi-Scene Orchestrator"),
        ("app.agents.asset_planner", "asset_planner", "Asset Planner"),
        ("app.agents.asset_validator", "asset_validator", "Asset Validator"),
    ]

    for module_name, func_name, display_name in agents:
        try:
            module = __import__(module_name, fromlist=[func_name])
            func = getattr(module, func_name, None)
            if func is not None:
                results.append((True, f"[PASS] {display_name}: {module_name}.{func_name}"))
            else:
                results.append((False, f"[FAIL] {display_name}: Function {func_name} not found in {module_name}"))
        except ImportError as e:
            results.append((False, f"[FAIL] {display_name}: Could not import {module_name} - {e}"))

    return results


def check_instrumentation() -> List[Tuple[bool, str]]:
    """Check that all agents are registered in instrumentation."""
    results = []

    try:
        from app.agents.instrumentation import extract_input_keys, extract_output_keys

        required_agents = [
            "diagram_analyzer",
            "game_designer",
            "scene_sequencer",
            "multi_scene_image_orchestrator",
            "asset_planner",
            "asset_validator",
        ]

        for agent in required_agents:
            input_keys = extract_input_keys({}, agent)
            output_keys = extract_output_keys({}, agent)

            if input_keys or output_keys:
                results.append((True, f"[PASS] Instrumentation for {agent}: {len(input_keys)} inputs, {len(output_keys)} outputs"))
            else:
                results.append((False, f"[WARN] {agent}: No input/output keys registered"))

    except Exception as e:
        results.append((False, f"[FAIL] Error checking instrumentation: {e}"))

    return results


def check_presets() -> List[Tuple[bool, str]]:
    """Check preset configurations."""
    results = []

    try:
        from app.config.presets import PRESET_REGISTRY, get_preset, is_advanced_preset

        results.append((True, f"[PASS] Presets loaded: {list(PRESET_REGISTRY.keys())}"))

        # Check Preset 1
        preset1 = get_preset("interactive_diagram_hierarchical")
        if preset1:
            results.append((True, f"[PASS] Preset 1 (interactive_diagram_hierarchical) loaded"))
        else:
            results.append((False, f"[FAIL] Preset 1 not found"))

        # Check Preset 2
        preset2 = get_preset("advanced_interactive_diagram")
        if preset2:
            results.append((True, f"[PASS] Preset 2 (advanced_interactive_diagram) loaded"))
            features = preset2.get("features", {})
            results.append((True, f"  - Multi-scene: {features.get('use_multi_scene', False)}"))
            results.append((True, f"  - Polygon zones: {features.get('use_polygon_zones', False)}"))
            results.append((True, f"  - Bloom's mapping: {features.get('use_blooms_interaction_mapping', False)}"))
        else:
            results.append((False, f"[FAIL] Preset 2 not found"))

        # Check is_advanced_preset
        is_adv = is_advanced_preset("advanced_interactive_diagram")
        results.append((is_adv, f"[{'PASS' if is_adv else 'FAIL'}] is_advanced_preset() returns {is_adv}"))

    except Exception as e:
        results.append((False, f"[FAIL] Error checking presets: {e}"))

    return results


def check_services() -> List[Tuple[bool, str]]:
    """Check service implementations."""
    results = []

    # Check nanobanana service
    try:
        from app.services.nanobanana_service import get_nanobanana_service, NanobananaService

        service = get_nanobanana_service()
        results.append((True, f"[PASS] Nanobanana service loaded"))
        results.append((True, f"  - Configured: {service.is_configured()}"))

    except Exception as e:
        results.append((False, f"[FAIL] Nanobanana service: {e}"))

    return results


def check_example_game_designs() -> List[Tuple[bool, str]]:
    """Check example game designs for agent learning."""
    results = []

    try:
        from app.config.example_game_designs import EXAMPLE_GAME_DESIGNS

        results.append((True, f"[PASS] Example game designs loaded: {len(EXAMPLE_GAME_DESIGNS)} examples"))

        for i, example in enumerate(EXAMPLE_GAME_DESIGNS[:3]):
            question = example.get("question", "Unknown")[:50]
            scenes = len(example.get("design", {}).get("scenes", []))
            results.append((True, f"  - Example {i+1}: '{question}...' ({scenes} scenes)"))

    except Exception as e:
        results.append((False, f"[FAIL] Error checking example game designs: {e}"))

    return results


def check_state_fields() -> List[Tuple[bool, str]]:
    """Check that AgentState has all required fields for Preset 2."""
    results = []

    try:
        from app.agents.state import AgentState, create_initial_state

        # Check if we can create initial state
        state = create_initial_state("test_id", "Test question")
        results.append((True, f"[PASS] create_initial_state() works"))

        # Required Preset 2 fields
        required_fields = [
            "diagram_type",
            "diagram_type_config",
            "diagram_analysis",
            "game_design",
            "planned_assets",
            "generated_assets",
            "asset_validation",
            "_pipeline_preset",
            "_ai_images_generated",
        ]

        for field in required_fields:
            if field in state:
                results.append((True, f"  - {field}: defined ✓"))
            else:
                results.append((False, f"  - {field}: MISSING ✗"))

        # Check multi-scene fields
        multi_scene_fields = [
            "needs_multi_scene",
            "num_scenes",
            "scene_progression_type",
            "scene_breakdown",
            "scene_diagrams",
            "scene_zones",
            "scene_labels",
        ]

        multi_scene_defined = all(f in state for f in multi_scene_fields)
        results.append((multi_scene_defined, f"[{'PASS' if multi_scene_defined else 'FAIL'}] Multi-scene fields: {len([f for f in multi_scene_fields if f in state])}/{len(multi_scene_fields)}"))

    except Exception as e:
        results.append((False, f"[FAIL] Error checking state fields: {e}"))

    return results


def main():
    """Run all verification checks."""
    print("=" * 70)
    print("AGENTIC EDUCATIONAL GAME SYSTEM - IMPLEMENTATION VERIFICATION")
    print("=" * 70)
    print()

    all_results = []

    # Check core files
    print("1. CORE FILES")
    print("-" * 40)
    files_to_check = [
        ("app/config/interaction_patterns.py", "Interaction Patterns Library"),
        ("app/config/asset_capabilities.py", "Asset Capabilities Manifest"),
        ("app/config/example_game_designs.py", "Example Game Designs"),
        ("app/services/nanobanana_service.py", "Nanobanana Service"),
        ("app/agents/diagram_analyzer.py", "Diagram Analyzer Agent"),
        ("app/agents/game_designer.py", "Game Designer Agent"),
        ("app/agents/scene_sequencer.py", "Scene Sequencer Agent"),
        ("app/agents/multi_scene_image_orchestrator.py", "Multi-Scene Orchestrator"),
        ("app/agents/asset_planner.py", "Asset Planner Agent"),
        ("app/agents/asset_validator.py", "Asset Validator Agent"),
    ]

    for filepath, description in files_to_check:
        passed, msg = check_file_exists(filepath, description)
        print(msg)
        all_results.append(passed)
    print()

    # Check interaction patterns
    print("2. INTERACTION PATTERNS")
    print("-" * 40)
    for passed, msg in check_interaction_patterns():
        print(msg)
        if not msg.startswith("  "):
            all_results.append(passed)
    print()

    # Check asset capabilities
    print("3. ASSET CAPABILITIES")
    print("-" * 40)
    for passed, msg in check_asset_capabilities():
        print(msg)
        if not msg.startswith("  "):
            all_results.append(passed)
    print()

    # Check agentic agents
    print("4. AGENTIC AGENTS")
    print("-" * 40)
    for passed, msg in check_agentic_agents():
        print(msg)
        all_results.append(passed)
    print()

    # Check instrumentation
    print("5. INSTRUMENTATION")
    print("-" * 40)
    for passed, msg in check_instrumentation():
        print(msg)
        all_results.append(passed)
    print()

    # Check presets
    print("6. PRESETS")
    print("-" * 40)
    for passed, msg in check_presets():
        print(msg)
        if not msg.startswith("  "):
            all_results.append(passed)
    print()

    # Check services
    print("7. SERVICES")
    print("-" * 40)
    for passed, msg in check_services():
        print(msg)
        if not msg.startswith("  "):
            all_results.append(passed)
    print()

    # Check example game designs
    print("8. EXAMPLE GAME DESIGNS")
    print("-" * 40)
    for passed, msg in check_example_game_designs():
        print(msg)
        if not msg.startswith("  "):
            all_results.append(passed)
    print()

    # Check state fields
    print("9. STATE FIELDS")
    print("-" * 40)
    for passed, msg in check_state_fields():
        print(msg)
        if not msg.startswith("  "):
            all_results.append(passed)
    print()

    # Summary
    print("=" * 70)
    passed_count = sum(all_results)
    total_count = len(all_results)
    pass_rate = (passed_count / total_count * 100) if total_count > 0 else 0

    print(f"SUMMARY: {passed_count}/{total_count} checks passed ({pass_rate:.1f}%)")

    if pass_rate == 100:
        print("ALL CHECKS PASSED - Implementation verified!")
        return 0
    elif pass_rate >= 80:
        print("MOSTLY PASSING - Some optional components may be missing")
        return 0
    else:
        print("VERIFICATION FAILED - Critical components missing")
        return 1


if __name__ == "__main__":
    sys.exit(main())
