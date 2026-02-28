"""
Blueprint Validator Agent

Validates generated blueprints for schema correctness, semantic validity,
and pedagogical alignment. Extracted from graph.py for modularity.
"""

from typing import Optional
from datetime import datetime
import logging

from app.agents.state import AgentState
from app.agents.instrumentation import instrumented_agent, InstrumentedAgentContext

logger = logging.getLogger("gamed_ai.agents.blueprint_validator")


@instrumented_agent("blueprint_validator")
async def blueprint_validator_agent(state: AgentState, ctx: Optional[InstrumentedAgentContext] = None) -> dict:
    """
    Validate generated blueprint.

    Performs:
    1. Schema validation (required fields)
    2. Semantic validation (valid references)
    3. Pedagogical validation (alignment check)
    """
    from app.agents.blueprint_generator import validate_blueprint

    logger.info("BlueprintValidator: Validating blueprint")

    blueprint = state.get("blueprint", {})
    template_type = blueprint.get("templateType", state.get("template_selection", {}).get("template_type", ""))

    # Run validation
    validation_result = await validate_blueprint(
        blueprint,
        template_type,
        context={
            "question_text": state.get("question_text", ""),
            "pedagogical_context": state.get("pedagogical_context", {}),
            "domain_knowledge": state.get("domain_knowledge", {}),
            "diagram_zones": state.get("diagram_zones"),
            "diagram_image": state.get("diagram_image"),
        },
    )

    errors = validation_result.get("errors", [])
    warnings = validation_result.get("warnings", [])
    is_valid = validation_result.get("valid", False)

    # Track retries
    retry_counts = state.get("retry_counts", {})
    if not is_valid:
        retry_counts["blueprint_generator"] = retry_counts.get("blueprint_generator", 0) + 1

    result_state = {
        "validation_results": {
            **state.get("validation_results", {}),
            "blueprint": {
                "is_valid": is_valid,
                "errors": errors,
                "warnings": warnings,
                "suggestions": [],
                "validated_at": datetime.utcnow().isoformat()
            }
        },
        "retry_counts": retry_counts,
        "current_validation_errors": errors,
        "current_agent": "check_template_status",
        "last_updated_at": datetime.utcnow().isoformat()
    }

    # Phase 6: Set generation_complete when blueprint is valid
    # This signals pipeline completion, allowing us to skip diagram_spec/svg agents
    if is_valid:
        result_state["generation_complete"] = True
        logger.info("BlueprintValidator: Blueprint valid - setting generation_complete=True")

    # Set validation results for instrumentation
    if ctx:
        ctx.set_validation_results(
            passed=is_valid,
            errors=errors if not is_valid else None
        )
        ctx.complete(result_state)

    return result_state
