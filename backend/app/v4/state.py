"""V4 Pipeline State — 3-stage creative cascade state fields.

Uses Annotated reducers for Send API accumulation fields (parallel workers).
Sequential fields don't need reducers since merge nodes handle deduplication.

Architecture:
  Phase 0: Understanding (parallel) → pedagogical_context, domain_knowledge
  Phase 1a: Game Concept → game_concept
  Phase 1b: Scene Design (parallel Send) → scene_creative_designs
  Graph Builder: game_plan
  Phase 2a: Content Generation (parallel Send) → mechanic_contents
  Phase 2b: Interaction Design (parallel Send) → interaction_results
  Phase 3a: Asset Needs → Asset Art Direction → art_directed_manifests
  Phase 3b: Asset Chains (parallel Send) → scene_assets
  Phase 4: Blueprint Assembly → blueprint
"""

from typing import TypedDict, Optional, Annotated, Any
import operator


class V4MainState(TypedDict, total=False):
    # ── Input (immutable after init) ──────────────────────────────
    question_text: str
    question_id: str
    question_options: Optional[list[str]]
    _run_id: str
    _pipeline_preset: str

    # ── Phase 0: Context Gathering ────────────────────────────────
    pedagogical_context: Optional[dict[str, Any]]
    content_structure: Optional[dict[str, Any]]
    domain_knowledge: Optional[dict[str, Any]]

    # ── Phase 1a: Game Concept ────────────────────────────────────
    game_concept: Optional[dict[str, Any]]
    concept_validation: Optional[dict[str, Any]]
    concept_retry_count: int

    # ── Phase 1b: Scene Design (parallel Send) ────────────────────
    # Parallel scene designers write to reducer; merge node deduplicates
    scene_creative_designs_raw: Annotated[list[dict[str, Any]], operator.add]
    scene_creative_designs: Optional[dict[str, Any]]  # {scene_id: SceneCreativeDesign}
    scene_design_validation: Optional[dict[str, Any]]  # {scene_id: ValidationResult}
    scene_design_retry_counts: Optional[dict[str, int]]  # {scene_id: count}
    failed_scene_design_ids: Annotated[list[str], operator.add]

    # ── Graph Builder (deterministic) ─────────────────────────────
    game_plan: Optional[dict[str, Any]]
    design_validation: Optional[dict[str, Any]]
    design_retry_count: int
    design_validation_override: bool

    # ── Phase 2a: Content Generation (parallel Send) ──────────────
    mechanic_contents_raw: Annotated[list[dict[str, Any]], operator.add]
    mechanic_contents: Optional[list[dict[str, Any]]]
    content_validation: Optional[dict[str, Any]]  # {mechanic_id: ValidationResult}
    content_retry_counts: Optional[dict[str, int]]
    failed_content_ids: Annotated[list[str], operator.add]

    # ── Phase 2b: Interaction Design (parallel Send) ──────────────
    interaction_results_raw: Annotated[list[dict[str, Any]], operator.add]
    interaction_results: Optional[list[dict[str, Any]]]
    interaction_validation: Optional[dict[str, Any]]
    interaction_retry_counts: Optional[dict[str, int]]
    failed_interaction_ids: Annotated[list[str], operator.add]
    content_retry_count: int

    # ── Phase 3a: Asset Needs + Art Direction ─────────────────────
    asset_needs: Optional[dict[str, Any]]  # {scene_id: AssetNeeds}
    art_directed_manifests_raw: Annotated[list[dict[str, Any]], operator.add]
    art_directed_manifests: Optional[dict[str, Any]]  # {scene_id: ArtDirectedManifest}
    art_direction_validation: Optional[dict[str, Any]]
    art_direction_retry_counts: Optional[dict[str, int]]
    failed_art_direction_ids: Annotated[list[str], operator.add]

    # ── Phase 3b: Asset Chains (parallel Send) ────────────────────
    generated_assets_raw: Annotated[list[dict[str, Any]], operator.add]
    generated_assets: Optional[list[dict[str, Any]]]
    scene_assets: Optional[dict[str, Any]]  # {scene_id: SceneAssets}
    failed_asset_scene_ids: Annotated[list[str], operator.add]
    asset_retry_count: int

    # ── Phase 4: Assembly ─────────────────────────────────────────
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
