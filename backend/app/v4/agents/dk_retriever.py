"""Domain Knowledge Retriever Agent (V4).

Gathers domain knowledge via web search and LLM extraction.
~60% reused from V3 domain_knowledge_retriever.py.

State writes: domain_knowledge
Model: gemini-2.5-flash (via agent config)
"""

import json
import re
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.services.llm_service import get_llm_service
from app.services.web_search import get_serper_client, WebSearchError
from app.utils.logging_config import get_logger

logger = get_logger("gamed_ai.v4.dk_retriever")

# Hard char limit per DK field (V3 pattern)
DK_FIELD_CHAR_LIMIT = 4000


def _detect_query_intent(question: str) -> Dict[str, Any]:
    """Detect what type of knowledge the query requires.

    Returns dict with: needs_labels, needs_sequence, needs_comparison, sequence_type.
    """
    question_lower = question.lower()

    intents: Dict[str, Any] = {
        "needs_labels": True,
        "needs_sequence": False,
        "needs_comparison": False,
        "sequence_type": None,
    }

    sequence_keywords = [
        "flow", "order", "sequence", "steps", "process", "cycle",
        "path", "trace", "stages", "phases", "progression",
        "through", "from.*to", "route", "journey", "pathway",
    ]
    for keyword in sequence_keywords:
        if re.search(keyword, question_lower):
            intents["needs_sequence"] = True
            break

    if intents["needs_sequence"]:
        if any(kw in question_lower for kw in ("cycle", "circular", "loop", "repeat")):
            intents["sequence_type"] = "cyclic"
        elif any(kw in question_lower for kw in ("branch", "either", "or", "diverge")):
            intents["sequence_type"] = "branching"
        else:
            intents["sequence_type"] = "linear"

    comparison_keywords = ["compare", "contrast", "difference", "similar", "versus", "vs"]
    if any(kw in question_lower for kw in comparison_keywords):
        intents["needs_comparison"] = True

    return intents


def _build_search_query(
    question_text: str,
    pedagogical_context: Optional[Dict[str, Any]] = None,
) -> str:
    """Build search query customized by pedagogical context."""
    cleaned = question_text.strip().rstrip(".")

    if not pedagogical_context:
        return f"{cleaned} key concepts and components"

    blooms = (pedagogical_context.get("blooms_level") or "").lower()
    difficulty = (pedagogical_context.get("difficulty") or "").lower()
    subject = (pedagogical_context.get("subject") or "").lower()

    suffix_map = {
        "remember": "key parts and components",
        "understand": "components and their functions",
        "apply": "structure and function relationships",
        "analyze": "components relationships hierarchy structure",
    }
    query_suffix = suffix_map.get(blooms, "key concepts and components")

    subject_terms = {
        "biology": "biological anatomy",
        "chemistry": "chemical structure molecular",
        "physics": "physical components diagram",
        "geography": "geographical features map",
    }
    domain_term = ""
    for key, term in subject_terms.items():
        if key in subject:
            domain_term = term
            break

    if difficulty == "hard":
        query_suffix += " detailed comprehensive"
    elif difficulty == "easy":
        query_suffix += " basic main"

    parts = [cleaned, query_suffix]
    if domain_term:
        parts.append(domain_term)
    return " ".join(parts)


async def _search_for_sequence(
    question: str,
    seq_type: str,
    labels: List[str],
) -> Optional[Dict[str, Any]]:
    """Search for sequence/ordering data from authoritative sources."""
    search_query = f"{question} correct order steps sequence"

    try:
        client = get_serper_client()
        results = await client.search(search_query)

        if not results:
            return None

        snippets = []
        for r in results[:5]:
            snippet = r.get("snippet") or ""
            if snippet:
                snippets.append({
                    "url": r.get("link") or r.get("url") or "",
                    "snippet": snippet,
                })

        if not snippets:
            return None

        llm = get_llm_service()
        extraction_prompt = f"""Extract the correct sequence/order from search results.

Question: {question}
Known labels: {json.dumps(labels)}
Sequence type: {seq_type}

Search snippets:
{json.dumps(snippets, indent=2)}

Return JSON:
{{
    "flow_type": "{seq_type}",
    "sequence_items": [
        {{"id": "step_1", "text": "<item>", "order_index": 0, "description": "<desc>"}}
    ],
    "flow_description": "<brief>",
    "source_url": "<best source URL>"
}}
"""
        data = await llm.generate_json_for_agent(
            agent_name="dk_retriever",
            prompt=extraction_prompt,
            schema_hint="SequenceFlowData with sequence_items",
        )
        if isinstance(data, dict):
            data.pop("_llm_metrics", None)  # Metrics tracked by instrumentation wrapper

        if data and data.get("sequence_items"):
            logger.info(f"Extracted sequence: {data.get('flow_type')}, "
                        f"{len(data.get('sequence_items', []))} items")
            return data
        return None

    except (WebSearchError, Exception) as e:
        logger.warning(f"Sequence search failed: {e}")
        return None


async def _generate_label_descriptions(
    canonical_labels: List[str],
    question_text: str,
    llm: Any,
) -> tuple[Optional[Dict[str, str]], Dict[str, Any]]:
    """Generate functional descriptions for each canonical label.

    Returns (descriptions_or_None, llm_metrics_dict).
    """
    if not canonical_labels:
        return None, {}

    labels_str = ", ".join(canonical_labels[:25])
    # Build a JSON template with the exact label keys to guide the LLM
    label_template = ", ".join(f'"{label}": "..."' for label in canonical_labels[:25])
    prompt = f"""For each label listed below, provide a concise functional description (1-2 sentences).

Labels: {labels_str}

Context question: "{question_text}"

Return a JSON object with EXACTLY these keys (copy them verbatim):
{{
    {label_template}
}}

Rules:
- Use the EXACT label text as the JSON key — do NOT rename, pluralize, or reformat
- Focus on FUNCTION or ROLE, not just definition
- Keep under 40 words per description
- Every label must have a description string value
"""

    try:
        result = await llm.generate_json_for_agent(
            agent_name="dk_retriever",
            prompt=prompt,
            schema_hint="Dict mapping label text to description string",
        )
        metrics: Dict[str, Any] = {}
        if isinstance(result, dict):
            metrics = result.pop("_llm_metrics", {})
            descriptions = {}

            # Build normalized lookup: stripped-lowercase key → (original_key, value)
            result_norm: Dict[str, tuple[str, Any]] = {}
            for key, val in result.items():
                norm_key = key.strip().lower()
                if isinstance(val, str):
                    result_norm[norm_key] = (key, val)

            for label in canonical_labels:
                norm_label = label.strip().lower()
                # Exact match (case-insensitive, whitespace-stripped)
                if norm_label in result_norm:
                    _, val = result_norm[norm_label]
                    descriptions[label] = val[:DK_FIELD_CHAR_LIMIT]
                    continue
                # Substring match: LLM may return "The Nucleus" for "Nucleus"
                for norm_key, (_, val) in result_norm.items():
                    if norm_label in norm_key or norm_key in norm_label:
                        descriptions[label] = val[:DK_FIELD_CHAR_LIMIT]
                        break

            if descriptions:
                logger.info(
                    f"Label descriptions: matched {len(descriptions)}/{len(canonical_labels)}"
                )
            else:
                logger.warning(
                    f"Label descriptions: 0 matches. LLM returned keys: "
                    f"{list(result.keys())[:10]}, expected: {canonical_labels[:10]}"
                )
            return (descriptions if descriptions else None), metrics
        return None, metrics
    except Exception as e:
        logger.warning(f"Label description generation failed: {e}")
        return None, {}


async def _generate_comparison_data(
    canonical_labels: List[str],
    question_text: str,
    llm: Any,
) -> tuple[Optional[Dict[str, Any]], Dict[str, Any]]:
    """Generate comparison data for compare/contrast questions.

    Returns (comparison_data_or_None, llm_metrics_dict).
    """
    if not canonical_labels:
        return None, {}

    labels_str = ", ".join(canonical_labels[:25])
    prompt = f"""The question "{question_text}" involves comparison. Labels: {labels_str}

Generate comparison data as JSON:
{{
    "comparison_type": "structural" | "functional" | "categorical",
    "groups": [
        {{"group_name": "Group A", "members": ["label1"], "distinguishing_features": ["feature1"]}}
    ],
    "similarities": ["shared trait 1"],
    "differences": ["key difference 1"],
    "sorting_categories": [
        {{"id": "cat_a", "name": "Category A", "description": "What belongs here"}}
    ]
}}
"""

    try:
        result = await llm.generate_json_for_agent(
            agent_name="dk_retriever",
            prompt=prompt,
            schema_hint="Comparison data with groups, similarities, differences",
        )
        metrics: Dict[str, Any] = {}
        if isinstance(result, dict):
            metrics = result.pop("_llm_metrics", {})
            if result.get("groups") or result.get("similarities"):
                return result, metrics
        return None, metrics
    except Exception as e:
        logger.warning(f"Comparison data generation failed: {e}")
        return None, {}


def _truncate_dk_fields(dk: Dict[str, Any]) -> Dict[str, Any]:
    """Truncate DK fields to hard char limit."""
    for key, val in dk.items():
        if isinstance(val, str) and len(val) > DK_FIELD_CHAR_LIMIT:
            dk[key] = val[:DK_FIELD_CHAR_LIMIT]
        elif isinstance(val, list):
            val_str = json.dumps(val)
            if len(val_str) > DK_FIELD_CHAR_LIMIT:
                # Truncate list by removing items from the end
                while len(json.dumps(val)) > DK_FIELD_CHAR_LIMIT and len(val) > 1:
                    val.pop()
                dk[key] = val
    return dk


async def dk_retriever(state: dict) -> dict:
    """Retrieve domain knowledge for the question.

    Args:
        state: V4MainState dict with question_text.

    Returns:
        Dict with domain_knowledge to merge into state.
    """
    question_text = state.get("question_text", "")
    pedagogical_context = state.get("pedagogical_context") or {}

    logger.info(f"Starting DK retrieval for: {question_text[:80]}...")

    if not question_text:
        logger.error("Missing question text")
        return {
            "domain_knowledge": {"canonical_labels": [], "error": "missing question text"},
            "phase_errors": [{"phase": "dk_retrieval", "error": "missing question text"}],
        }

    # Detect query intent
    content_characteristics = _detect_query_intent(question_text)
    logger.info(f"Intent: sequence={content_characteristics['needs_sequence']}, "
                f"comparison={content_characteristics['needs_comparison']}")

    # Build and execute search
    query = _build_search_query(question_text, pedagogical_context)
    logger.info(f"Search query: {query}")

    try:
        client = get_serper_client()
        search_start = time.time()
        results = await client.search(query)
        search_ms = int((time.time() - search_start) * 1000)
        logger.info(f"Search returned {len(results)} results in {search_ms}ms")
    except WebSearchError as e:
        logger.error(f"Search failed: {e}")
        return {
            "domain_knowledge": {"canonical_labels": [], "error": str(e)},
            "phase_errors": [{"phase": "dk_retrieval", "error": f"search failed: {e}"}],
        }

    # Extract snippets
    snippets = []
    for r in results:
        snippet = r.get("snippet") or ""
        if snippet:
            snippets.append({
                "url": r.get("link") or r.get("url") or "",
                "title": r.get("title") or "",
                "snippet": snippet,
            })

    if not snippets:
        logger.warning("No snippets found")
        return {
            "domain_knowledge": {"canonical_labels": [], "error": "no search results"},
            "phase_errors": [{"phase": "dk_retrieval", "error": "no search snippets"}],
        }

    # Main LLM extraction
    llm = get_llm_service()
    sub_stages: list[dict[str, Any]] = []

    pedagogy_section = ""
    if pedagogical_context:
        pedagogy_section = f"""
## Pedagogical Context:
- Bloom's Level: {pedagogical_context.get('blooms_level', 'remember')}
- Difficulty: {pedagogical_context.get('difficulty', 'medium')}
- Subject: {pedagogical_context.get('subject', '')}
"""

    prompt = f"""You are an educational domain knowledge extractor.

Question: {question_text}
Search query: {query}
Search snippets:
{json.dumps(snippets, indent=2)}
{pedagogy_section}
Return structured JSON with:
1. canonical_labels: exhaustive list of correct labels
2. acceptable_variants: map of canonical label to variants
3. hierarchical_relationships: spatial CONTAINMENT hierarchy — which structures physically
   contain other structures in the diagram. Use ONLY labels from canonical_labels as keys
   (not the whole organism/object). Format: {{"container_label": ["contained_label", ...]}}
   Example for a cell: {{"Cell Wall": ["Cell Membrane"], "Cell Membrane": ["Cytoplasm"],
   "Cytoplasm": ["Nucleus", "Vacuole", "Chloroplast", "Mitochondrion"],
   "Nucleus": ["Nucleolus", "Nuclear Envelope"]}}
   Only include relationships where one structure visually contains another in the diagram.
4. sources: list of sources used
5. query_intent: {{learning_focus, depth_preference, suggested_progression}}
6. suggested_reveal_order: labels in optimal pedagogical sequence (outermost structures first)
7. scene_hints: (optional) multi-scene suggestions if content is complex
"""

    t_main = time.time()
    knowledge = await llm.generate_json_for_agent(
        agent_name="dk_retriever",
        prompt=prompt,
        schema_hint="DomainKnowledge JSON with canonical_labels and sources",
    )
    main_ms = int((time.time() - t_main) * 1000)

    # Extract LLM metrics (includes prompt/response previews)
    main_llm_metrics = knowledge.pop("_llm_metrics", {}) if isinstance(knowledge, dict) else {}

    if not isinstance(knowledge, dict):
        knowledge = {"canonical_labels": [], "acceptable_variants": {}, "sources": []}

    raw_labels = knowledge.get("canonical_labels", []) or []
    # Normalize: LLM sometimes returns dicts like {"label": "X"} instead of strings
    canonical_labels: list[str] = []
    for item in raw_labels:
        if isinstance(item, str):
            canonical_labels.append(item)
        elif isinstance(item, dict):
            # Try common key names the LLM might use
            val = item.get("label") or item.get("name") or item.get("text") or ""
            if val:
                canonical_labels.append(str(val))
        else:
            canonical_labels.append(str(item))
    knowledge["canonical_labels"] = canonical_labels
    logger.info(f"Extracted {len(canonical_labels)} canonical labels: {canonical_labels[:10]}")

    sub_stages.append({
        "id": "dk_main_extraction",
        "name": "Main DK extraction",
        "type": "llm_extraction",
        "status": "success" if canonical_labels else "degraded",
        "duration_ms": main_ms,
        "model": main_llm_metrics.get("model", "dk_retriever"),
        "prompt_preview": main_llm_metrics.get("prompt_preview"),
        "response_preview": main_llm_metrics.get("response_preview"),
        "output_summary": {
            "label_count": len(canonical_labels),
            "canonical_labels": canonical_labels[:20],
            "acceptable_variants": knowledge.get("acceptable_variants", {}),
            "sources": knowledge.get("sources", []),
        },
    })

    # Generate label descriptions
    t_labels = time.time()
    label_descriptions, labels_metrics = await _generate_label_descriptions(
        canonical_labels, question_text, llm,
    )
    labels_ms = int((time.time() - t_labels) * 1000)
    sub_stages.append({
        "id": "dk_label_descriptions",
        "name": "Label descriptions",
        "type": "llm_extraction",
        "status": "success" if label_descriptions else "skipped",
        "duration_ms": labels_ms,
        "model": labels_metrics.get("model", "dk_retriever"),
        "prompt_preview": labels_metrics.get("prompt_preview"),
        "response_preview": labels_metrics.get("response_preview"),
        "output_summary": {
            "description_count": len(label_descriptions) if label_descriptions else 0,
            "descriptions": label_descriptions or {},
        },
    })

    # Generate comparison data if needed
    comparison_data = None
    if content_characteristics.get("needs_comparison"):
        t_comp = time.time()
        comparison_data, comp_metrics = await _generate_comparison_data(
            canonical_labels, question_text, llm,
        )
        comp_ms = int((time.time() - t_comp) * 1000)
        sub_stages.append({
            "id": "dk_comparison_data",
            "name": "Comparison data",
            "type": "llm_extraction",
            "status": "success" if comparison_data else "failed",
            "duration_ms": comp_ms,
            "model": comp_metrics.get("model", "dk_retriever"),
            "prompt_preview": comp_metrics.get("prompt_preview"),
            "response_preview": comp_metrics.get("response_preview"),
            "output_summary": comparison_data if comparison_data else {},
        })

    # Generate sequence data if needed
    sequence_flow_data = None
    if content_characteristics.get("needs_sequence"):
        t_seq = time.time()
        sequence_flow_data = await _search_for_sequence(
            question_text,
            content_characteristics.get("sequence_type", "linear"),
            canonical_labels,
        )
        seq_ms = int((time.time() - t_seq) * 1000)
        sub_stages.append({
            "id": "dk_sequence_flow",
            "name": "Sequence flow",
            "type": "search_extraction",
            "status": "success" if sequence_flow_data else "failed",
            "duration_ms": seq_ms,
            "model": "dk_retriever",
            "output_summary": sequence_flow_data if sequence_flow_data else {},
        })

    # Build final DK dict
    domain_knowledge = {
        **knowledge,
        "retrieved_at": datetime.utcnow().isoformat(),
        "sequence_flow_data": sequence_flow_data,
        "content_characteristics": content_characteristics,
        "label_descriptions": label_descriptions,
        "comparison_data": comparison_data,
    }

    # Truncate fields
    domain_knowledge = _truncate_dk_fields(domain_knowledge)

    result: dict[str, Any] = {
        "domain_knowledge": domain_knowledge,
        "_sub_stages": sub_stages,
    }

    # Warn if too few labels (only fatal for drag_drop; degraded for others)
    if len(canonical_labels) < 2:
        logger.warning(f"Very few labels: {len(canonical_labels)}")
        result["phase_errors"] = [
            {"phase": "dk_retrieval", "error": f"only {len(canonical_labels)} labels found"}
        ]

    return result
