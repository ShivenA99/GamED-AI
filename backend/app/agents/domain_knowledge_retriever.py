"""
Domain Knowledge Retriever Agent

Uses web search to gather domain knowledge (key terms, concepts, labels)
and normalizes them into a structured list.
Includes query intent detection for multi-mechanic support (sequence/flow data retrieval).
"""

import json
import logging
import re
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.agents.state import AgentState
from app.agents.instrumentation import InstrumentedAgentContext
from app.agents.schemas.domain_knowledge import get_domain_knowledge_schema
from app.services.llm_service import get_llm_service
from app.services.web_search import get_serper_client, WebSearchError
from app.utils.logging_config import get_logger

logger = get_logger("gamed_ai.agents.domain_knowledge_retriever")


# =============================================================================
# QUERY INTENT DETECTION (Phase 0: Multi-Mechanic Support)
# =============================================================================

def _detect_query_intent(question: str) -> Dict[str, Any]:
    """
    Detect what type of knowledge the query requires.

    Analyzes the question to determine if it needs:
    - Labels (always for label-diagram)
    - Sequence/flow data (for "show order", "trace path", etc.)
    - Comparison data (for "compare X and Y")

    Args:
        question: The user's question text

    Returns:
        Dict with content characteristics:
        - needs_labels: bool
        - needs_sequence: bool
        - needs_comparison: bool
        - sequence_type: str | None ("linear", "cyclic", "branching")
    """
    question_lower = question.lower()

    intents = {
        "needs_labels": True,  # Most game types need domain terms/labels
        "needs_sequence": False,
        "needs_comparison": False,
        "sequence_type": None,
    }

    # Sequence/flow indicators
    sequence_keywords = [
        "flow", "order", "sequence", "steps", "process", "cycle",
        "path", "trace", "stages", "phases", "progression",
        "through", "from.*to", "route", "journey", "pathway"
    ]

    # Check for sequence indicators using regex for compound patterns
    for keyword in sequence_keywords:
        if re.search(keyword, question_lower):
            intents["needs_sequence"] = True
            break

    # Determine sequence type if sequence is needed
    if intents["needs_sequence"]:
        if any(kw in question_lower for kw in ["cycle", "circular", "loop", "repeat"]):
            intents["sequence_type"] = "cyclic"
        elif any(kw in question_lower for kw in ["branch", "either", "or", "diverge", "split"]):
            intents["sequence_type"] = "branching"
        else:
            intents["sequence_type"] = "linear"

    # Comparison indicators
    comparison_keywords = ["compare", "contrast", "difference", "similar", "versus", "vs"]
    if any(kw in question_lower for kw in comparison_keywords):
        intents["needs_comparison"] = True

    logger.debug(
        "Detected query intent",
        question=question[:50],
        needs_sequence=intents["needs_sequence"],
        sequence_type=intents["sequence_type"],
        needs_comparison=intents["needs_comparison"]
    )

    return intents


async def _search_for_sequence(
    question: str,
    seq_type: str,
    labels: List[str],
    ctx: Optional[InstrumentedAgentContext] = None
) -> Optional[Dict[str, Any]]:
    """
    Search for sequence/ordering data from authoritative sources.

    Args:
        question: The user's question
        seq_type: Type of sequence ("linear", "cyclic", "branching")
        labels: List of canonical labels already retrieved
        ctx: Instrumentation context for metrics

    Returns:
        SequenceFlowData dict or None if not found
    """
    # Build sequence-specific search query
    search_query = f"{question} correct order steps sequence"

    try:
        client = get_serper_client()
        search_start = time.time()
        results = await client.search(search_query)
        search_latency_ms = int((time.time() - search_start) * 1000)

        if ctx:
            ctx.set_tool_metrics([{
                "name": "serper_sequence_search",
                "arguments": {"query": search_query},
                "result": {"results_count": len(results)},
                "status": "success",
                "latency_ms": search_latency_ms,
                "api_calls": 1,
                "estimated_cost_usd": 0.01,
            }])

        if not results:
            return None

        # Extract snippets for LLM processing
        snippets = []
        for result in results[:5]:  # Limit to top 5 results
            link = result.get("link") or result.get("url") or ""
            snippet = result.get("snippet") or ""
            if snippet:
                snippets.append({"url": link, "snippet": snippet})

        if not snippets:
            return None

        # Use LLM to extract sequence order from snippets
        llm = get_llm_service()

        extraction_prompt = f"""Extract the correct sequence/order from the search results.

Question: {question}
Known labels: {json.dumps(labels)}
Sequence type: {seq_type}

Search snippets:
{json.dumps(snippets, indent=2)}

Return a JSON object with:
{{
    "flow_type": "{seq_type}",
    "sequence_items": [
        {{"id": "step_1", "text": "<item text>", "order_index": 0, "description": "<optional description>"}},
        {{"id": "step_2", "text": "<item text>", "order_index": 1, "description": "<optional description>"}},
        ...
    ],
    "flow_description": "<brief description of the flow/process>",
    "source_url": "<URL of best source>"
}}

Rules:
- Use the known labels where they match sequence items
- Create IDs like "step_1", "step_2", etc.
- order_index should be 0-indexed
- For cyclic sequences, the last item connects back to the first
- Include description for each step if available from sources
"""

        sequence_data = await llm.generate_json_for_agent(
            agent_name="domain_knowledge_retriever",
            prompt=extraction_prompt,
            schema_hint="SequenceFlowData with sequence_items"
        )

        # Extract LLM metrics
        if isinstance(sequence_data, dict):
            sequence_data.pop("_llm_metrics", None)

        if sequence_data and sequence_data.get("sequence_items"):
            logger.info(
                "Extracted sequence data",
                flow_type=sequence_data.get("flow_type"),
                item_count=len(sequence_data.get("sequence_items", []))
            )
            return sequence_data

        return None

    except WebSearchError as e:
        logger.warning(f"Sequence search failed: {e}")
        return None
    except Exception as e:
        logger.error(f"Error extracting sequence data: {e}")
        return None


def _build_search_query(
    question_text: str,
    pedagogical_context: Optional[Dict[str, Any]] = None
) -> str:
    """
    Build a search query customized based on pedagogical context.

    Args:
        question_text: The raw question text
        pedagogical_context: Context from input_enhancer containing:
            - blooms_level: remember, understand, apply, analyze, evaluate, create
            - difficulty: easy, medium, hard
            - subject: the subject domain (e.g., "biology", "anatomy")

    Returns:
        A search query tailored to the pedagogical needs
    """
    cleaned = question_text.strip().rstrip(".")

    if not pedagogical_context:
        return f"{cleaned} key concepts and components"

    blooms_level = (pedagogical_context.get("blooms_level") or "").lower()
    difficulty = (pedagogical_context.get("difficulty") or "").lower()
    subject = (pedagogical_context.get("subject") or "").lower()

    # Customize search suffix based on Bloom's taxonomy level
    if blooms_level in ("remember", "knowledge"):
        # Basic identification - key terms
        query_suffix = "key parts and components"
    elif blooms_level in ("understand", "comprehension"):
        # Understanding function - parts and their functions
        query_suffix = "components and their functions"
    elif blooms_level in ("apply", "application"):
        # Applying knowledge - how parts work together
        query_suffix = "structure and function relationships"
    elif blooms_level in ("analyze", "analysis"):
        # Analyzing relationships - hierarchy and connections
        query_suffix = "components relationships hierarchy structure"
    elif blooms_level in ("evaluate", "synthesis", "create"):
        # Higher-order thinking - comprehensive view
        query_suffix = "detailed structure components relationships"
    else:
        # Default
        query_suffix = "key concepts and components"

    # Add subject-specific terminology for better results
    subject_terms = {
        "biology": "biological anatomy",
        "anatomy": "anatomical structures",
        "botany": "plant anatomy botanical",
        "zoology": "animal anatomy zoological",
        "chemistry": "chemical structure molecular",
        "physics": "physical components diagram",
        "geography": "geographical features map",
        "earth science": "geological features layers",
    }

    domain_term = ""
    for key, term in subject_terms.items():
        if key in subject:
            domain_term = term
            break

    # Adjust depth based on difficulty
    if difficulty == "hard":
        query_suffix += " detailed comprehensive"
    elif difficulty == "easy":
        query_suffix += " basic main"

    # Build final query
    query_parts = [cleaned, query_suffix]
    if domain_term:
        query_parts.append(domain_term)

    return " ".join(query_parts)


def _extract_snippets(results: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    snippets = []
    for result in results:
        link = result.get("link") or result.get("url") or ""
        snippet = result.get("snippet") or ""
        title = result.get("title") or ""
        if link or snippet or title:
            snippets.append({"url": link, "title": title, "snippet": snippet})
    return snippets


async def _generate_label_descriptions(
    canonical_labels: List[str],
    question_text: str,
    llm: Any,
    ctx: Optional[InstrumentedAgentContext] = None,
) -> Optional[Dict[str, str]]:
    """
    Generate functional descriptions for each canonical label using LLM.

    These descriptions are used by downstream mechanics like description_matching
    and click_to_identify, which need textual descriptions of each labeled structure.

    Returns:
        Dict mapping label text -> functional description, or None on failure.
    """
    if not canonical_labels:
        return None

    labels_str = ", ".join(canonical_labels[:25])
    prompt = f"""For each of the following labels from the question "{question_text}", provide a concise functional description (1-2 sentences) suitable for an educational matching game.

Labels: {labels_str}

Return a JSON object mapping each label to its description:
{{
    "Label Name": "Brief functional description of what this structure does or is.",
    ...
}}

Rules:
- Descriptions should be educationally accurate and age-appropriate
- Focus on FUNCTION or ROLE, not just definition
- Keep each description under 40 words
- Use active voice where possible
"""

    try:
        result = await llm.generate_json_for_agent(
            agent_name="domain_knowledge_retriever",
            prompt=prompt,
            schema_hint="Dict mapping label text to description string",
        )
        if isinstance(result, dict):
            result.pop("_llm_metrics", None)
            # Filter to only keep entries that match our labels
            descriptions = {}
            for label in canonical_labels:
                for key, val in result.items():
                    if key.lower() == label.lower() and isinstance(val, str):
                        descriptions[label] = val
                        break
            if descriptions:
                logger.info(
                    "Generated label descriptions",
                    description_count=len(descriptions),
                )
                return descriptions
        return None
    except Exception as e:
        logger.warning(f"Label description generation failed: {e}")
        return None


async def _generate_comparison_data(
    canonical_labels: List[str],
    question_text: str,
    llm: Any,
    ctx: Optional[InstrumentedAgentContext] = None,
) -> Optional[Dict[str, Any]]:
    """
    Generate comparison data when the question involves comparing/contrasting.

    Returns:
        Dict with categories, similarities, differences, or None on failure.
    """
    if not canonical_labels:
        return None

    labels_str = ", ".join(canonical_labels[:25])
    prompt = f"""The question "{question_text}" involves comparison. Given these labels: {labels_str}

Generate comparison data as JSON:
{{
    "comparison_type": "structural" | "functional" | "categorical",
    "groups": [
        {{
            "group_name": "Group A name",
            "members": ["label1", "label2"],
            "distinguishing_features": ["feature1", "feature2"]
        }},
        {{
            "group_name": "Group B name",
            "members": ["label3", "label4"],
            "distinguishing_features": ["feature3", "feature4"]
        }}
    ],
    "similarities": ["shared trait 1", "shared trait 2"],
    "differences": ["key difference 1", "key difference 2"],
    "sorting_categories": [
        {{"id": "cat_a", "name": "Category A", "description": "What belongs here"}},
        {{"id": "cat_b", "name": "Category B", "description": "What belongs here"}}
    ]
}}

Rules:
- Use the provided labels wherever possible
- Make groups educationally meaningful
- sorting_categories can be used by the sorting_categories mechanic
"""

    try:
        result = await llm.generate_json_for_agent(
            agent_name="domain_knowledge_retriever",
            prompt=prompt,
            schema_hint="Comparison data with groups, similarities, differences",
        )
        if isinstance(result, dict):
            result.pop("_llm_metrics", None)
            if result.get("groups") or result.get("similarities"):
                logger.info(
                    "Generated comparison data",
                    group_count=len(result.get("groups", [])),
                )
                return result
        return None
    except Exception as e:
        logger.warning(f"Comparison data generation failed: {e}")
        return None


async def domain_knowledge_retriever_agent(state: AgentState, ctx: Optional[InstrumentedAgentContext] = None) -> dict:
    question_id = state.get("question_id", "unknown")
    question_text = state.get("question_text", "")
    pedagogical_context = state.get("pedagogical_context", {}) or {}

    logger.info("Starting domain knowledge retrieval",
                question_id=question_id,
                agent_name="domain_knowledge_retriever",
                blooms_level=pedagogical_context.get("blooms_level"),
                subject=pedagogical_context.get("subject"))

    if not question_text:
        logger.error("Missing question text for domain knowledge retrieval")
        return {
            **state,
            "current_agent": "domain_knowledge_retriever",
            "current_validation_errors": ["Domain knowledge retrieval: missing question text"],
        }

    # Phase 0: Detect query intent to determine what knowledge is needed
    content_characteristics = _detect_query_intent(question_text)
    logger.info(
        "Query intent detected",
        needs_sequence=content_characteristics.get("needs_sequence"),
        sequence_type=content_characteristics.get("sequence_type"),
        needs_comparison=content_characteristics.get("needs_comparison")
    )

    query = _build_search_query(question_text, pedagogical_context)
    logger.info("Built search query", query=query)

    try:
        logger.info("Searching via Serper API", query=query)
        client = get_serper_client()
        search_start = time.time()
        results = await client.search(query)
        search_latency_ms = int((time.time() - search_start) * 1000)
        logger.info(f"Serper search completed", result_count=len(results))

        # Track Serper API cost
        if ctx:
            ctx.set_tool_metrics([{
                "name": "serper_web_search",
                "arguments": {"query": query},
                "result": {"results_count": len(results)},
                "status": "success",
                "latency_ms": search_latency_ms,
                "api_calls": 1,
                "estimated_cost_usd": 0.01,  # Serper pricing ~$0.01 per search
            }])
    except WebSearchError as e:
        logger.error("Serper search failed", 
                    exc_info=True,
                    error_type=type(e).__name__,
                    query=query)
        return {
            **state,
            "current_agent": "domain_knowledge_retriever",
            "current_validation_errors": [f"Domain knowledge retrieval failed: {e}"],
        }

    snippets = _extract_snippets(results)
    logger.info("Extracted snippets", snippets_count=len(snippets))
    
    if not snippets:
        logger.warning("No snippets extracted from search results")
        return {
            **state,
            "current_agent": "domain_knowledge_retriever",
            "current_validation_errors": ["Domain knowledge retrieval: no search results"],
        }

    llm = get_llm_service()

    # Build pedagogical context section for the prompt
    pedagogy_section = ""
    if pedagogical_context:
        blooms = pedagogical_context.get("blooms_level", "remember")
        difficulty = pedagogical_context.get("difficulty", "medium")
        subject = pedagogical_context.get("subject", "")

        pedagogy_section = f"""
## PEDAGOGICAL CONTEXT (use this to guide label selection and ordering):
- Bloom's Level: {blooms}
- Difficulty: {difficulty}
- Subject Domain: {subject}

Guidance based on Bloom's level:
- "remember": Focus on basic part identification; fewer labels (4-8), clear names
- "understand": Include functional descriptions; show how parts relate
- "apply": Include working relationships; show cause-effect connections
- "analyze": Deep hierarchies; parent-child relationships; detailed sub-parts (10-15 labels)
- "evaluate/create": Comprehensive labeling; all sub-structures; 15+ labels

Guidance based on difficulty:
- "easy": Main visible parts only; no sub-components
- "medium": Main parts + major sub-components
- "hard": Comprehensive including subtle structures
"""

    prompt = f"""You are an educational domain knowledge extractor.

Question: {question_text}
Search query: {query}
Search snippets (JSON):
{json.dumps(snippets, indent=2)}
{pedagogy_section}
Return structured JSON with the following fields:

## REQUIRED FIELDS:
1. query: original query used
2. canonical_labels: exhaustive list of correct labels for the diagram
3. acceptable_variants: map of canonical label to acceptable variants
4. hierarchical_relationships: list of parent-child relationships where one part contains others
   Format: {{"parent": "stamen", "children": ["anther", "filament"], "relationship_type": "contains"}}

   IMPORTANT - Relationship Types:
   - "composed_of" or "subdivided_into": Use for LAYERED structures where children are STRATA/LAYERS within the parent (e.g., heart wall layers, skin layers). Children may overlap spatially.
   - "contains" or "has_part": Use for DISCRETE parts where children are separate structures within parent bounds (e.g., flower contains petals, stamens). Children should NOT overlap.

5. sources: list of sources with url/title/snippet used to derive labels

## NEW FIELDS - Query Intent Analysis:
6. query_intent: Analysis of what the user wants to learn
   {{
     "learning_focus": "identify_parts" | "understand_structure" | "trace_process" | "compare_components"
       - "identify_parts": Basic part identification (e.g., "Label the parts of...")
       - "understand_structure": How parts relate (e.g., "Show how... connects to...")
       - "trace_process": Follow a flow/path (e.g., "Trace the path of blood...")
       - "compare_components": Similarities/differences (e.g., "Compare plant and animal cells")

     "depth_preference": "overview" | "detailed" | "comprehensive"
       - "overview": Main parts only (4-6 labels)
       - "detailed": Main parts + immediate sub-parts (7-12 labels)
       - "comprehensive": All levels including fine details (13+ labels)

     "suggested_progression": Array of labels in optimal learning order
       - Start with general/outer structures
       - Progress to specific/inner structures
       - Group related parts together
   }}

7. suggested_reveal_order: List of labels in optimal pedagogical sequence
   - Order labels by: hierarchy level (parents first), visual prominence, then complexity
   - Example for flower: ["Petals", "Sepals", "Stamen", "Pistil", "Anther", "Filament", "Stigma", "Style", "Ovary"]

8. scene_hints: (Optional) Suggestions for multi-scene games when content is complex
   Only include if:
   - Hierarchy depth > 2
   - Label count > 12
   - Content naturally divides into multiple views

   Format: [{{"focus": "which labels to include", "reason": "why separate scene needed", "suggested_scope": "optional view description"}}]

## Rules:
- canonical_labels must be academic and correct for the question
- Prefer commonly accepted textbook terms; avoid vague labels
- For anatomical/structural diagrams, identify which parts contain or are composed of sub-parts
- hierarchical_relationships should only include relationships where:
  a) The parent is a major structural component
  b) The children are distinct sub-parts that are physically part of the parent
  c) Users would benefit from learning the parent before its sub-components
- Be precise about relationship_type: use "composed_of" only for true layer structures
- suggested_reveal_order should enable progressive disclosure of complexity
"""

    knowledge = await llm.generate_json_for_agent(
        agent_name="domain_knowledge_retriever",
        prompt=prompt,
        schema_hint="DomainKnowledge JSON with canonical_labels and sources",
        json_schema=get_domain_knowledge_schema(),
    )

    # Extract LLM metrics for instrumentation
    if isinstance(knowledge, dict):
        llm_metrics = knowledge.pop("_llm_metrics", None)
        if ctx and llm_metrics:
            ctx.set_llm_metrics(
                model=llm_metrics.get("model"),
                prompt_tokens=llm_metrics.get("prompt_tokens"),
                completion_tokens=llm_metrics.get("completion_tokens"),
                latency_ms=llm_metrics.get("latency_ms"),
            )

    # Guard against None or invalid result
    if knowledge is None or not isinstance(knowledge, dict):
        logger.error("Invalid knowledge result from LLM", knowledge_type=type(knowledge).__name__)
        knowledge = {"canonical_labels": [], "acceptable_variants": {}, "sources": [], "query": query}

    canonical_labels = knowledge.get("canonical_labels", []) or []
    label_count = len(canonical_labels)
    logger.info("Domain knowledge extracted",
               canonical_labels_count=label_count,
               labels=canonical_labels[:10] if isinstance(canonical_labels, list) else [])

    validation_errors: List[str] = []
    if label_count < 4:
        logger.warning("Too few labels extracted", label_count=label_count)
        validation_errors.append(
            f"Domain knowledge retrieval yielded too few labels ({label_count})"
        )

    # Phase 2.2: Generate label descriptions for downstream mechanics
    label_descriptions = await _generate_label_descriptions(
        canonical_labels=canonical_labels,
        question_text=question_text,
        llm=llm,
        ctx=ctx,
    )

    # Phase 2.2: Generate comparison data if query needs it
    comparison_data = None
    if content_characteristics.get("needs_comparison"):
        comparison_data = await _generate_comparison_data(
            canonical_labels=canonical_labels,
            question_text=question_text,
            llm=llm,
            ctx=ctx,
        )

    # Phase 0: Retrieve sequence data if query needs it
    sequence_flow_data = None
    if content_characteristics.get("needs_sequence"):
        logger.info(
            "Searching for sequence data",
            sequence_type=content_characteristics.get("sequence_type")
        )
        sequence_flow_data = await _search_for_sequence(
            question=question_text,
            seq_type=content_characteristics.get("sequence_type", "linear"),
            labels=canonical_labels,
            ctx=ctx
        )
        if sequence_flow_data:
            logger.info(
                "Sequence data retrieved",
                flow_type=sequence_flow_data.get("flow_type"),
                item_count=len(sequence_flow_data.get("sequence_items", []))
            )
        else:
            logger.warning("No sequence data found, will rely on game_planner to infer order")

    return {
        **state,
        "domain_knowledge": {
            **knowledge,
            "retrieved_at": datetime.utcnow().isoformat(),
            # Phase 0: Include sequence and content characteristics
            "sequence_flow_data": sequence_flow_data,
            "content_characteristics": content_characteristics,
            # Phase 2.2: Label descriptions and comparison data for downstream mechanics
            "label_descriptions": label_descriptions,
            "comparison_data": comparison_data,
        },
        # F1 fix: Promote canonical_labels to top-level state so V3 agents
        # (via v3_context.py) can read them without digging into domain_knowledge.
        "canonical_labels": canonical_labels,
        "current_agent": "domain_knowledge_retriever",
        "current_validation_errors": validation_errors,
        "last_updated_at": datetime.utcnow().isoformat(),
    }
