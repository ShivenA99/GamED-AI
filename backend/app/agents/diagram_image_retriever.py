"""
Diagram Image Retriever Agent
"""

import logging
import time
from datetime import datetime
from typing import Optional

from app.agents.state import AgentState
from app.agents.instrumentation import InstrumentedAgentContext
from app.services.image_retrieval import (
    build_image_query,
    build_image_queries,
    search_diagram_images,
    search_diagram_images_multi,
    select_best_image,
    select_best_image_scored,
    select_top_images_scored,
)
from app.utils.logging_config import get_logger

logger = get_logger("gamed_ai.agents.diagram_image_retriever")


async def diagram_image_retriever_agent(state: AgentState, ctx: Optional[InstrumentedAgentContext] = None) -> dict:
    import os
    question_id = state.get("question_id", "unknown")
    template_type = state.get("template_selection", {}).get("template_type", "")
    
    logger.info("Starting diagram image retrieval", 
                question_id=question_id, 
                template_type=template_type,
                agent_name="diagram_image_retriever")
    
    if os.getenv("USE_IMAGE_DIAGRAMS", "true").lower() != "true":
        logger.info("Skipping image retrieval: USE_IMAGE_DIAGRAMS not enabled")
        return {**state, "current_agent": "diagram_image_retriever"}
    
    if template_type != "INTERACTIVE_DIAGRAM":
        logger.info(f"Skipping image retrieval: template_type={template_type} (not INTERACTIVE_DIAGRAM)")
        return {**state, "current_agent": "diagram_image_retriever"}

    # Reset retry state when starting a new image search attempt
    retry_attempts = state.get("image_search_attempts", 0)
    if retry_attempts > 0:
        logger.info(f"Retry attempt {retry_attempts + 1}, searching for new image", 
                   attempt=retry_attempts + 1)

    question_text = state.get("question_text", "")
    domain_knowledge = state.get("domain_knowledge", {}) or {}
    canonical_labels = list(domain_knowledge.get("canonical_labels", []) or [])

    # Use multi-query strategy to prefer unlabeled diagrams
    use_multi_query = os.getenv("USE_MULTI_QUERY_SEARCH", "true").lower() == "true"

    if use_multi_query:
        queries = build_image_queries(question_text, canonical_labels)
        logger.info("Using multi-query strategy (preferring unlabeled diagrams)",
                    query_count=len(queries),
                    canonical_labels_count=len(canonical_labels),
                    queries=queries[:3])
    else:
        query = build_image_query(question_text, canonical_labels)
        queries = [query]
        logger.info("Using single query strategy",
                    query=query,
                    canonical_labels_count=len(canonical_labels))

    try:
        search_start = time.time()
        if use_multi_query:
            logger.info("Searching for diagram images via multi-query strategy")
            results = await search_diagram_images_multi(queries, max_results=5)
            num_api_calls = len(queries)  # Each query is a separate API call
        else:
            logger.info("Searching for diagram images via single query")
            results = await search_diagram_images(queries[0], max_results=5)
            num_api_calls = 1
        search_latency_ms = int((time.time() - search_start) * 1000)

        logger.info(f"Found {len(results)} image results", result_count=len(results))

        # Track Serper Image Search API cost
        if ctx:
            ctx.set_tool_metrics([{
                "name": "serper_image_search",
                "arguments": {"queries": queries, "max_results": 5},
                "result": {"results_count": len(results), "multi_query": use_multi_query},
                "status": "success",
                "latency_ms": search_latency_ms,
                "api_calls": num_api_calls,
                "estimated_cost_usd": num_api_calls * 0.01,  # Serper pricing ~$0.01 per search
            }])

        # Get top scored images (primary + backups for fallback if download fails)
        top_images = select_top_images_scored(results, prefer_unlabeled=False, top_n=5)
        if not top_images:
            logger.error("No usable diagram image found in results", result_count=len(results))
            return {
                **state,
                "current_agent": "diagram_image_retriever",
                "current_validation_errors": ["No usable diagram image found"],
            }

        image = top_images[0]  # Best image
        backup_images = top_images[1:] if len(top_images) > 1 else []  # Fallback images

        logger.info("Selected best image",
                   image_url=image.get("image_url", "N/A")[:80],
                   source_url=image.get("source_url", "N/A")[:80],
                   license=image.get("license", "unknown"),
                   backup_count=len(backup_images))

        # Reset retry flag and clear old cleaned image when starting new attempt
        update = {
            **state,
            "diagram_image": {
                **image,
                "backup_images": backup_images,  # Include backups for fallback
                "queries": queries if use_multi_query else [queries[0]],
                "query": queries[0] if queries else "",  # Primary query for backward compat
                "retrieved_at": datetime.utcnow().isoformat(),
                "multi_query_used": use_multi_query,
            },
            "retry_image_search": False,  # Reset retry flag for new attempt
            "current_agent": "diagram_image_retriever",
            "last_updated_at": datetime.utcnow().isoformat(),
        }
        
        # Clear old cleaned image and segments when retrying (new image will be processed)
        if retry_attempts > 0:
            logger.info("Clearing old image data for retry", attempt=retry_attempts + 1)
            update["cleaned_image_path"] = None
            update["removed_labels"] = None
            update["diagram_segments"] = None
            update["diagram_zones"] = None
            update["diagram_labels"] = None
        
        logger.info("Image retrieval completed successfully", 
                   image_url=image.get("image_url", "N/A")[:80])
        return update
    except Exception as e:
        logger.error("Diagram image retrieval failed", 
                    exc_info=True,
                    error_type=type(e).__name__,
                    error_message=str(e))
        return {
            **state,
            "current_agent": "diagram_image_retriever",
            "current_validation_errors": [f"Diagram image retrieval failed: {e}"],
        }
