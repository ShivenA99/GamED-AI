"""Algorithm Domain Knowledge Retriever — gathers algorithm-specific knowledge.

Uses web search to find pseudocode, implementations, common bugs,
complexity analysis, and visualization keywords for the target algorithm.
"""

import json
import time
from datetime import datetime
from typing import Any, Optional

from app.services.llm_service import get_llm_service
from app.services.web_search import get_serper_client, WebSearchError
from app.utils.logging_config import get_logger

logger = get_logger("gamed_ai.v4_algorithm.agents.dk_retriever")

DK_FIELD_CHAR_LIMIT = 4000

# Common algorithm names for extraction
KNOWN_ALGORITHMS = [
    "binary search", "linear search", "interpolation search", "exponential search",
    "bubble sort", "merge sort", "quick sort", "insertion sort", "selection sort",
    "heap sort", "radix sort", "counting sort", "bucket sort", "tim sort",
    "bfs", "breadth first search", "dfs", "depth first search",
    "dijkstra", "bellman ford", "floyd warshall", "kruskal", "prim",
    "a*", "a star",
    "knapsack", "0/1 knapsack", "fractional knapsack",
    "fibonacci", "factorial", "tower of hanoi", "n queens", "n-queens",
    "topological sort", "strongly connected components", "tarjan",
    "binary tree traversal", "bst operations", "avl tree", "red black tree",
    "hash table", "hash map", "linked list operations",
    "stack operations", "queue operations", "priority queue",
    "longest common subsequence", "longest increasing subsequence",
    "edit distance", "matrix chain multiplication", "coin change",
    "activity selection", "huffman coding", "job scheduling",
    "traveling salesman", "graph coloring", "sudoku solver",
    "kadane", "two pointer", "sliding window",
]


def _extract_algorithm_name(question_text: str) -> str:
    """Extract algorithm name from question text."""
    lower = question_text.lower()
    for algo in KNOWN_ALGORITHMS:
        if algo in lower:
            return algo.title()
    return question_text.split("?")[0].strip()[:60]


def _build_search_queries(algorithm_name: str) -> list[str]:
    """Build multiple search queries for comprehensive algorithm knowledge."""
    name = algorithm_name.lower()
    return [
        f"{name} algorithm pseudocode implementation python",
        f"{name} algorithm common bugs mistakes errors",
        f"{name} time space complexity analysis big O",
        f"{name} algorithm visualization educational step by step",
    ]


async def algo_dk_retriever(state: dict) -> dict:
    """Retrieve algorithm domain knowledge via web search + LLM extraction.

    Reads: question_text
    Writes: domain_knowledge
    """
    question_text = state.get("question_text", "")
    logger.info(f"DK retriever: {question_text[:100]}")

    if not question_text:
        return {
            "domain_knowledge": {"algorithm_name": "", "error": "missing question text"},
            "phase_errors": [{"phase": "algo_dk_retrieval", "error": "missing question text"}],
        }

    algorithm_name = _extract_algorithm_name(question_text)
    logger.info(f"Extracted algorithm: '{algorithm_name}'")

    # Search for algorithm knowledge
    queries = _build_search_queries(algorithm_name)
    all_snippets: list[dict] = []

    try:
        client = get_serper_client()
        for query in queries[:3]:  # Limit to 3 searches
            t0 = time.time()
            results = await client.search(query)
            ms = int((time.time() - t0) * 1000)
            logger.info(f"Search '{query[:50]}...' → {len(results)} results in {ms}ms")

            for r in results[:5]:
                snippet = r.get("snippet") or ""
                if snippet:
                    all_snippets.append({
                        "url": r.get("link") or r.get("url") or "",
                        "title": r.get("title") or "",
                        "snippet": snippet,
                        "query": query,
                    })

    except WebSearchError as e:
        logger.warning(f"Search failed: {e}")
        # Continue with LLM-only extraction

    # LLM extraction
    llm = get_llm_service()

    snippets_text = ""
    if all_snippets:
        snippets_text = f"""
## Web Search Results ({len(all_snippets)} snippets):
{json.dumps(all_snippets[:15], indent=2)}
"""

    extraction_prompt = f"""You are an algorithm education expert. Extract comprehensive domain knowledge
about the algorithm from the question and search results.

## Question: {question_text}
## Algorithm: {algorithm_name}
{snippets_text}
Return a JSON object with these fields:
{{
    "algorithm_name": "{algorithm_name}",
    "algorithm_category": "<sorting|searching|graph|dynamic_programming|string|tree|greedy|backtracking|divide_and_conquer|linked_list|stack_queue|hashing|math>",
    "pseudocode": "<clean pseudocode of the algorithm, 10-30 lines>",
    "language_implementations": {{
        "python": "<complete Python implementation, 10-40 lines>",
        "javascript": "<complete JavaScript implementation, 10-40 lines>"
    }},
    "time_complexity": {{
        "best": "<e.g. O(1)>",
        "average": "<e.g. O(n log n)>",
        "worst": "<e.g. O(n^2)>"
    }},
    "space_complexity": {{
        "iterative": "<e.g. O(1)>",
        "recursive": "<e.g. O(n)>"
    }},
    "common_bugs": [
        {{
            "bug_type": "<off_by_one|wrong_operator|wrong_variable|missing_base_case|wrong_initialization|wrong_return|infinite_loop|boundary_error|logic_error>",
            "description": "<what the bug is>",
            "buggy_line": "<the incorrect code line>",
            "correct_line": "<the correct code line>"
        }}
    ],
    "common_misconceptions": ["<misconception 1>", "<misconception 2>"],
    "data_structures_used": ["<array|graph|tree|dp_table|stack|linked_list|heap|hash_map|queue>"],
    "key_operations": ["<compare|swap|divide|merge|search|insert|delete|traverse>"],
    "example_inputs": [
        {{
            "input": "<example input>",
            "expected": "<expected output>",
            "trace": "<brief execution trace>"
        }}
    ],
    "related_algorithms": ["<related algo 1>", "<related algo 2>"],
    "visualization_keywords": ["<keyword for image search>"],
    "difficulty_variants": {{
        "beginner": "<simple problem variant>",
        "intermediate": "<medium variant>",
        "advanced": "<hard variant>"
    }}
}}

Rules:
- Provide REAL, CORRECT algorithm implementations (not pseudocode placeholders)
- Include at least 3 common bugs with actual buggy vs correct code lines
- Include at least 2 example inputs with execution traces
- All complexity notations must be standard Big-O
- data_structures_used should reflect what the algorithm actually uses
"""

    t_main = time.time()
    try:
        knowledge = await llm.generate_json_for_agent(
            agent_name="v4a_dk_retriever",
            prompt=extraction_prompt,
            schema_hint="AlgorithmDomainKnowledge with implementations and bugs",
        )
        main_ms = int((time.time() - t_main) * 1000)

        if isinstance(knowledge, dict):
            knowledge.pop("_llm_metrics", None)
        else:
            knowledge = {}

    except Exception as e:
        logger.error(f"LLM extraction failed: {e}")
        main_ms = int((time.time() - t_main) * 1000)
        knowledge = {}

    # Ensure required fields
    knowledge.setdefault("algorithm_name", algorithm_name)
    knowledge.setdefault("algorithm_category", "")
    knowledge.setdefault("pseudocode", "")
    knowledge.setdefault("language_implementations", {})
    knowledge.setdefault("time_complexity", {})
    knowledge.setdefault("space_complexity", {})
    knowledge.setdefault("common_bugs", [])
    knowledge.setdefault("common_misconceptions", [])
    knowledge.setdefault("data_structures_used", [])
    knowledge.setdefault("key_operations", [])
    knowledge.setdefault("example_inputs", [])
    knowledge.setdefault("related_algorithms", [])
    knowledge.setdefault("visualization_keywords", [])
    knowledge.setdefault("difficulty_variants", None)
    knowledge["retrieved_at"] = datetime.utcnow().isoformat()

    # Truncate
    for key, val in knowledge.items():
        if isinstance(val, str) and len(val) > DK_FIELD_CHAR_LIMIT:
            knowledge[key] = val[:DK_FIELD_CHAR_LIMIT]

    logger.info(
        f"DK retriever done: category='{knowledge.get('algorithm_category')}', "
        f"bugs={len(knowledge.get('common_bugs', []))}, "
        f"implementations={len(knowledge.get('language_implementations', {}))}, "
        f"extraction_ms={main_ms}"
    )

    return {"domain_knowledge": knowledge}
