#!/usr/bin/env python3
"""
Demo script for testing the GamED.AI v2 pipeline

Run with: python scripts/demo_pipeline.py

Requires:
- OPENAI_API_KEY or ANTHROPIC_API_KEY in .env file
"""

import asyncio
import json
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.agents import (
    create_initial_state,
    run_game_generation,
    TopologyType,
    create_topology,
    list_all_topologies
)


# Sample test questions
TEST_QUESTIONS = [
    {
        "id": "algo_binary_search",
        "text": "Explain how binary search works on a sorted array. Demonstrate the algorithm finding the number 7 in the array [1, 3, 5, 7, 9, 11, 13].",
        "options": None
    },
    {
        "id": "bio_cell_parts",
        "text": "Identify and label the main parts of an animal cell including the nucleus, mitochondria, cell membrane, and cytoplasm.",
        "options": None
    },
    {
        "id": "history_revolution",
        "text": "Arrange the following events of the American Revolution in chronological order:",
        "options": [
            "Boston Tea Party",
            "Declaration of Independence",
            "Battle of Yorktown",
            "First Continental Congress"
        ]
    },
    {
        "id": "chem_elements",
        "text": "Categorize the following elements into metals, non-metals, and metalloids:",
        "options": ["Iron", "Carbon", "Silicon", "Gold", "Oxygen", "Arsenic"]
    }
]


async def demo_single_question(question: dict):
    """Run the pipeline on a single question"""
    print(f"\n{'='*60}")
    print(f"Question: {question['text'][:80]}...")
    print(f"{'='*60}")

    try:
        result = await run_game_generation(
            question_id=question["id"],
            question_text=question["text"],
            question_options=question.get("options")
        )

        print("\n--- Results ---")
        print(f"Success: {result.get('generation_complete', False)}")

        if result.get("pedagogical_context"):
            ctx = result["pedagogical_context"]
            print(f"Bloom's Level: {ctx.get('blooms_level')}")
            print(f"Subject: {ctx.get('subject')}")
            print(f"Difficulty: {ctx.get('difficulty')}")

        if result.get("template_selection"):
            sel = result["template_selection"]
            print(f"Template: {sel.get('template_type')}")
            print(f"Confidence: {sel.get('confidence', 0):.2f}")

        if result.get("blueprint"):
            bp = result["blueprint"]
            print(f"Blueprint Title: {bp.get('title')}")
            print(f"Tasks: {len(bp.get('tasks', []))}")

        if result.get("error_message"):
            print(f"Error: {result['error_message']}")

        return result

    except Exception as e:
        print(f"Error: {e}")
        return None


async def demo_topology_comparison():
    """Compare different topologies on the same question"""
    print("\n" + "="*60)
    print("TOPOLOGY COMPARISON")
    print("="*60)

    # List available topologies
    print("\nAvailable Topologies:")
    for t in list_all_topologies():
        print(f"  - {t['name']}: {t['description']}")

    question = TEST_QUESTIONS[0]  # Use binary search question

    topologies_to_test = [
        TopologyType.T0_SEQUENTIAL,
        TopologyType.T1_SEQUENTIAL_VALIDATED,
    ]

    for topo_type in topologies_to_test:
        print(f"\n--- Testing {topo_type.value} ---")

        try:
            graph = create_topology(topo_type)
            compiled = graph.compile()

            initial_state = create_initial_state(
                question_id=question["id"],
                question_text=question["text"],
                question_options=question.get("options")
            )

            result = await compiled.ainvoke(initial_state)

            print(f"  Complete: {result.get('generation_complete', False)}")
            print(f"  Template: {result.get('template_selection', {}).get('template_type', 'N/A')}")

            if result.get("validation_results"):
                for key, val in result["validation_results"].items():
                    if isinstance(val, dict) and "is_valid" in val:
                        print(f"  {key} valid: {val['is_valid']}")

        except Exception as e:
            print(f"  Error: {e}")


async def main():
    """Main demo entry point"""
    print("="*60)
    print("GamED.AI v2 Pipeline Demo")
    print("="*60)

    # Check for API keys
    import os
    from dotenv import load_dotenv
    load_dotenv()

    openai_key = os.getenv("OPENAI_API_KEY")
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    groq_key = os.getenv("GROQ_API_KEY")

    if not openai_key and not anthropic_key and not groq_key:
        print("\nWARNING: No API keys found!")
        print("Set GROQ_API_KEY (free!), OPENAI_API_KEY, or ANTHROPIC_API_KEY in .env file")
        print("Running with fallback/mock responses...\n")
    else:
        print(f"\nAPI Keys configured:")
        if groq_key:
            print(f"  - GROQ_API_KEY: ***{groq_key[-4:]}")
        if openai_key:
            print(f"  - OPENAI_API_KEY: ***{openai_key[-4:]}")
        if anthropic_key:
            print(f"  - ANTHROPIC_API_KEY: ***{anthropic_key[-4:]}")

    # Run demo on all questions
    print("\n--- All Questions Demo ---")
    for q in TEST_QUESTIONS:
        await demo_single_question(q)

    # Topology comparison (lightweight)
    # await demo_topology_comparison()

    print("\n" + "="*60)
    print("Demo Complete!")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())
