"""V4 Algorithm Pipeline State — TypedDict with Annotated reducers.

Architecture:
  Phase 0: START ──┬── input_analyzer ──┬── algo_phase0_merge
                   └── algo_dk_retriever ┘
  Phase 1: algo_game_concept_designer → algo_concept_validator ──[retry]──
  Phase 2: algo_graph_builder → algo_plan_validator ──[retry]──
  Phase 3: ──[scene_content_dispatch]── algo_scene_content_gen(s) → algo_content_merge
  Phase 4: ──[scene_asset_dispatch]── algo_asset_worker(s) → algo_asset_merge
  Phase 5: algo_blueprint_assembler → END
"""

from typing import TypedDict, Optional, Annotated, Any
import operator


class V4AlgorithmState(TypedDict, total=False):
    # ── Input (immutable after init) ──────────────────────────────
    question_text: str
    question_id: str
    _run_id: str
    _pipeline_preset: str

    # ── Phase 0: Context Gathering ────────────────────────────────
    pedagogical_context: Optional[dict[str, Any]]
    content_structure: Optional[dict[str, Any]]
    domain_knowledge: Optional[dict[str, Any]]  # AlgorithmDomainKnowledge

    # ── Phase 1: Game Concept Design ─────────────────────────────
    game_concept: Optional[dict[str, Any]]  # AlgorithmGameConcept
    concept_validation: Optional[dict[str, Any]]
    concept_retry_count: int

    # ── Phase 2: Game Plan (deterministic) ────────────────────────
    game_plan: Optional[dict[str, Any]]  # AlgorithmGamePlan
    plan_validation: Optional[dict[str, Any]]
    plan_retry_count: int

    # ── Phase 3: Scene Content Generation (parallel Send) ─────────
    scene_contents_raw: Annotated[list[dict[str, Any]], operator.add]
    scene_contents: Optional[dict[str, Any]]  # {scene_id: content_dict}
    content_validation: Optional[dict[str, Any]]
    content_retry_count: int
    failed_content_ids: Annotated[list[str], operator.add]

    # ── Phase 4: Scene Asset Generation (parallel Send) ──────────
    scene_assets_raw: Annotated[list[dict[str, Any]], operator.add]
    scene_assets: Optional[dict[str, Any]]  # {scene_id: {image_url, ...}}
    failed_asset_ids: Annotated[list[str], operator.add]
    asset_retry_count: int

    # ── Phase 5: Blueprint Assembly ───────────────────────────────
    blueprint: Optional[dict[str, Any]]
    assembly_warnings: Optional[list[str]]

    # ── Metadata ──────────────────────────────────────────────────
    generation_complete: bool
    error_message: Optional[str]
    phase_errors: Annotated[list[dict[str, Any]], operator.add]
    is_degraded: bool
    _stage_order: int
    started_at: str
    last_updated_at: str
