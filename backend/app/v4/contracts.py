"""V4 Pipeline Contracts — mechanic classification, model routing, trigger mapping.

Imports from the existing mechanic_contracts registry (16KB, already exists)
and adds V4-specific classifications and mappings.
"""

from typing import Any

from app.config.mechanic_contracts import (
    MECHANIC_CONTRACTS,
    MechanicContract,
    get_contract,
    get_contract_safe,
    normalize_mechanic_type,
)

# ── Mechanic Sets ────────────────────────────────────────────────

SUPPORTED_MECHANICS: set[str] = {
    "drag_drop",
    "click_to_identify",
    "trace_path",
    "sequencing",
    "sorting_categories",
    "memory_match",
    "branching_scenario",
    "description_matching",
}

CONTENT_ONLY_MECHANICS: set[str] = {
    "sequencing",
    "sorting_categories",
    "memory_match",
    "branching_scenario",
}

ZONE_BASED_MECHANICS: set[str] = {
    "drag_drop",
    "click_to_identify",
    "trace_path",
    "description_matching",
}


# ── Model Routing ────────────────────────────────────────────────
# From audit 38: Pro for complex reasoning, Flash for simpler mechanics

MODEL_ROUTING: dict[str, str] = {
    "branching_scenario": "pro",
    "sorting_categories": "pro",
    "sequencing": "pro",
    "trace_path": "pro",
    "drag_drop": "flash",
    "click_to_identify": "flash",
    "memory_match": "flash",
    "description_matching": "flash",
}


# ── Trigger Map ──────────────────────────────────────────────────
# Maps (trigger_hint, mechanic_type) -> frontend trigger string.
# From audit 39 Finding 13. Wildcard "*" matches any mechanic type.

TRIGGER_MAP: dict[tuple[str, str], str] = {
    ("completion", "drag_drop"): "all_zones_labeled",
    ("completion", "trace_path"): "path_complete",
    ("completion", "click_to_identify"): "identification_complete",
    ("completion", "sequencing"): "sequence_complete",
    ("completion", "sorting_categories"): "sorting_complete",
    ("completion", "memory_match"): "memory_complete",
    ("completion", "branching_scenario"): "branching_complete",
    ("completion", "description_matching"): "description_complete",
    ("score_threshold", "*"): "percentage_complete",
    ("time_elapsed", "*"): "time_elapsed",
    ("user_choice", "*"): "user_choice",
}


def resolve_trigger(trigger_hint: str, mechanic_type: str) -> str:
    """Resolve a generic trigger hint to a frontend-specific trigger string.

    Tries exact match first, then wildcard "*" match.
    Falls back to the trigger_hint itself if no mapping found.
    """
    key = (trigger_hint, mechanic_type)
    if key in TRIGGER_MAP:
        return TRIGGER_MAP[key]
    wildcard_key = (trigger_hint, "*")
    if wildcard_key in TRIGGER_MAP:
        return TRIGGER_MAP[wildcard_key]
    return trigger_hint


def build_capability_spec() -> dict[str, Any]:
    """Generate capability specification from contracts for prompt injection.

    This is dynamically built from the contract registry so it stays in sync
    with the source of truth (audit 39 Finding 26 — no hardcoded capability specs).
    """
    spec: dict[str, Any] = {
        "supported_mechanics": sorted(SUPPORTED_MECHANICS),
        "zone_based_mechanics": sorted(ZONE_BASED_MECHANICS),
        "content_only_mechanics": sorted(CONTENT_ONLY_MECHANICS),
        "mechanics": {},
    }

    for mtype in SUPPORTED_MECHANICS:
        contract = get_contract(mtype)
        spec["mechanics"][mtype] = {
            "display_name": contract.display_name,
            "needs_diagram": contract.needs_diagram,
            "needs_zones": contract.needs_zones,
            "entity_type": contract.entity_type,
            "frontend_config_key": contract.frontend_config_key,
            "dk_fields": list(contract.dk_fields),
            "designer_guidance": contract.game_designer.guidance_note,
        }

    return spec
