"""
Research Tools for GamED.AI v2

Tools for researching domain knowledge, retrieving images, and analyzing questions.
These tools support the research phase of game generation.
"""

import os
import json
from typing import Dict, Any, List, Optional
import httpx

from app.utils.logging_config import get_logger
from app.tools.registry import register_tool, get_tool_registry

logger = get_logger("gamed_ai.tools.research")


# ============================================================================
# Tool Implementations
# ============================================================================

async def get_domain_knowledge_impl(
    question: str,
    subject: Optional[str] = None,
    num_results: int = 5
) -> Dict[str, Any]:
    """
    Search for domain knowledge related to a question using Serper API.

    Args:
        question: The educational question to research
        subject: Optional subject hint (e.g., "biology", "chemistry")
        num_results: Number of search results to retrieve

    Returns:
        Dict with canonical_labels, definitions, related_terms
    """
    serper_api_key = os.getenv("SERPER_API_KEY")

    if not serper_api_key:
        logger.warning("SERPER_API_KEY not set, returning empty domain knowledge")
        return {
            "canonical_labels": [],
            "definitions": {},
            "related_terms": [],
            "sources": [],
            "error": "SERPER_API_KEY not configured"
        }

    # Build search query
    search_query = question
    if subject:
        search_query = f"{subject} {question}"

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                "https://google.serper.dev/search",
                headers={"X-API-KEY": serper_api_key},
                json={
                    "q": search_query,
                    "num": num_results
                }
            )
            response.raise_for_status()
            data = response.json()

        # Extract relevant information
        organic_results = data.get("organic", [])

        # Parse results to extract domain terms
        canonical_labels = []
        definitions = {}
        sources = []

        for result in organic_results[:num_results]:
            snippet = result.get("snippet", "")
            title = result.get("title", "")
            link = result.get("link", "")

            sources.append({
                "title": title,
                "snippet": snippet,
                "url": link
            })

            # Simple extraction of potential labels from title and snippet
            # In production, this would use NLP or LLM for better extraction
            text = f"{title} {snippet}".lower()

            # Look for common anatomical/scientific terms
            for term in _extract_domain_terms(text, subject):
                if term not in canonical_labels:
                    canonical_labels.append(term)
                    definitions[term] = snippet[:200]

        return {
            "canonical_labels": canonical_labels[:10],  # Limit to 10
            "definitions": definitions,
            "related_terms": canonical_labels[10:20] if len(canonical_labels) > 10 else [],
            "sources": sources,
            "search_query": search_query
        }

    except Exception as e:
        logger.error(f"Domain knowledge search failed: {e}")
        return {
            "canonical_labels": [],
            "definitions": {},
            "related_terms": [],
            "sources": [],
            "error": str(e)
        }


def _extract_domain_terms(text: str, subject: Optional[str]) -> List[str]:
    """Extract potential domain terms from text based on subject."""
    # Common patterns for different subjects
    # This is a simplified implementation
    terms = []

    # Biology/anatomy terms
    bio_patterns = [
        "heart", "lung", "liver", "kidney", "brain", "stomach",
        "cell", "nucleus", "membrane", "mitochondria",
        "artery", "vein", "capillary", "aorta",
        "muscle", "bone", "tissue", "organ"
    ]

    # Chemistry terms
    chem_patterns = [
        "atom", "molecule", "element", "compound",
        "electron", "proton", "neutron", "ion",
        "bond", "reaction", "catalyst", "solution"
    ]

    # Physics terms
    physics_patterns = [
        "force", "energy", "mass", "velocity",
        "acceleration", "momentum", "gravity",
        "wave", "frequency", "amplitude"
    ]

    patterns = bio_patterns + chem_patterns + physics_patterns

    for pattern in patterns:
        if pattern in text:
            terms.append(pattern.title())

    return terms


async def retrieve_diagram_image_impl(
    query: str,
    num_results: int = 5,
    image_type: str = "educational"
) -> Dict[str, Any]:
    """
    Search for diagram images using Serper Image Search.

    Args:
        query: Search query for diagram images
        num_results: Number of image results to retrieve
        image_type: Type of image (educational, labeled, diagram)

    Returns:
        Dict with images list containing url, title, source
    """
    serper_api_key = os.getenv("SERPER_API_KEY")

    if not serper_api_key:
        logger.warning("SERPER_API_KEY not set, cannot retrieve images")
        return {
            "images": [],
            "error": "SERPER_API_KEY not configured"
        }

    # Enhance query for educational diagrams
    enhanced_query = f"{query} {image_type} diagram labeled"

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                "https://google.serper.dev/images",
                headers={"X-API-KEY": serper_api_key},
                json={
                    "q": enhanced_query,
                    "num": num_results
                }
            )
            response.raise_for_status()
            data = response.json()

        images = []
        for img in data.get("images", [])[:num_results]:
            images.append({
                "url": img.get("imageUrl", ""),
                "title": img.get("title", ""),
                "source": img.get("link", ""),
                "width": img.get("imageWidth", 0),
                "height": img.get("imageHeight", 0)
            })

        return {
            "images": images,
            "search_query": enhanced_query,
            "total_found": len(images)
        }

    except Exception as e:
        logger.error(f"Image search failed: {e}")
        return {
            "images": [],
            "error": str(e)
        }


async def analyze_question_impl(
    question: str
) -> Dict[str, Any]:
    """
    Analyze a question to extract pedagogical context.

    Args:
        question: The educational question to analyze

    Returns:
        Dict with blooms_level, subject, key_concepts, question_type
    """
    from app.services.llm_service import get_llm_service

    llm = get_llm_service()

    analysis_prompt = f"""Analyze this educational question and extract:
1. Bloom's Taxonomy level (remember, understand, apply, analyze, evaluate, create)
2. Subject area (biology, chemistry, physics, mathematics, etc.)
3. Key concepts to be learned
4. Question type (identification, comparison, explanation, problem-solving)

Question: {question}

Respond in JSON format:
{{
    "blooms_level": "...",
    "subject": "...",
    "key_concepts": ["concept1", "concept2"],
    "question_type": "...",
    "difficulty": "easy|medium|hard"
}}"""

    try:
        result = await llm.generate_json(
            prompt=analysis_prompt,
            system_prompt="You are an educational assessment expert. Analyze questions accurately."
        )

        return {
            "blooms_level": result.get("blooms_level", "understand"),
            "subject": result.get("subject", "general"),
            "key_concepts": result.get("key_concepts", []),
            "question_type": result.get("question_type", "identification"),
            "difficulty": result.get("difficulty", "medium")
        }

    except Exception as e:
        logger.error(f"Question analysis failed: {e}")
        return {
            "blooms_level": "understand",
            "subject": "general",
            "key_concepts": [],
            "question_type": "identification",
            "difficulty": "medium",
            "error": str(e)
        }


async def select_template_impl(
    question: str,
    blooms_level: str = "understand",
    subject: str = "general",
    question_type: str = "identification"
) -> Dict[str, Any]:
    """
    Select the best game template for a question.

    NOTE: This tool is now a NO-OP that always returns INTERACTIVE_DIAGRAM.
    The template is hardcoded in the pipeline for the Label Diagram game.
    This tool is kept for backwards compatibility with existing agent prompts.

    Args:
        question: The educational question
        blooms_level: Bloom's taxonomy level (ignored)
        subject: Subject area (ignored)
        question_type: Type of question (ignored)

    Returns:
        Dict with template_name, confidence, reasoning
    """
    # HARDCODED: Always return INTERACTIVE_DIAGRAM for the Label Diagram pipeline
    # This reduces cognitive load on agents - no need to select template
    logger.info("select_template called - returning hardcoded INTERACTIVE_DIAGRAM (template is fixed)")

    return {
        "template_name": "INTERACTIVE_DIAGRAM",
        "confidence": 1.0,
        "scores": {
            "INTERACTIVE_DIAGRAM": 10,
            "SEQUENCE_BUILDER": 0,
            "MATCHING_PAIRS": 0,
            "QUIZ": 0
        },
        "reasoning": "Template is hardcoded to INTERACTIVE_DIAGRAM for the Label Diagram pipeline. "
                    f"Question: '{question[:50]}...' will use Label Diagram game template."
    }


# ============================================================================
# Tool Registration
# ============================================================================

def register_research_tools() -> None:
    """Register all research tools in the registry."""

    # get_domain_knowledge
    register_tool(
        name="get_domain_knowledge",
        description="Search for domain knowledge and canonical labels related to an educational question. Returns authoritative terminology, definitions, and related concepts.",
        parameters={
            "type": "object",
            "properties": {
                "question": {
                    "type": "string",
                    "description": "The educational question to research"
                },
                "subject": {
                    "type": "string",
                    "description": "Optional subject hint (e.g., 'biology', 'chemistry')"
                },
                "num_results": {
                    "type": "integer",
                    "description": "Number of search results to retrieve (default 5)",
                    "default": 5
                }
            },
            "required": ["question"]
        },
        function=get_domain_knowledge_impl
    )

    # retrieve_diagram_image
    register_tool(
        name="retrieve_diagram_image",
        description="Search for educational diagram images using web image search. Returns candidate images with URLs and metadata.",
        parameters={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query for diagram images"
                },
                "num_results": {
                    "type": "integer",
                    "description": "Number of images to retrieve (default 5)",
                    "default": 5
                },
                "image_type": {
                    "type": "string",
                    "description": "Type of image (educational, labeled, diagram)",
                    "default": "educational"
                }
            },
            "required": ["query"]
        },
        function=retrieve_diagram_image_impl
    )

    # analyze_question
    register_tool(
        name="analyze_question",
        description="Analyze an educational question to extract pedagogical context including Bloom's level, subject, and key concepts.",
        parameters={
            "type": "object",
            "properties": {
                "question": {
                    "type": "string",
                    "description": "The educational question to analyze"
                }
            },
            "required": ["question"]
        },
        function=analyze_question_impl
    )

    # select_template
    register_tool(
        name="select_template",
        description="Select the best game template for an educational question based on its pedagogical characteristics.",
        parameters={
            "type": "object",
            "properties": {
                "question": {
                    "type": "string",
                    "description": "The educational question"
                },
                "blooms_level": {
                    "type": "string",
                    "description": "Bloom's taxonomy level"
                },
                "subject": {
                    "type": "string",
                    "description": "Subject area"
                },
                "question_type": {
                    "type": "string",
                    "description": "Type of question"
                }
            },
            "required": ["question", "blooms_level", "subject", "question_type"]
        },
        function=select_template_impl
    )

    logger.info("Research tools registered")
