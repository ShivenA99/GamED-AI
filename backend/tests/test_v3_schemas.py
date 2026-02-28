"""
Tests for v3 pipeline schemas: AssetGraph, AssetSpec, GameDesignV3.

Uses the heart anatomy game as the canonical test fixture:
- 1 scene with 3 mechanics (drag_drop → trace_path → click_to_identify)
- 8 zone labels, 2 distractors, hierarchy groups
- Media assets: background, flow arrows overlay
- Sounds: correct, incorrect, completion
"""

import json
import pytest

from app.agents.schemas.asset_graph import (
    AssetGraph,
    AssetGameLogic,
    AssetNode,
    AnimationNode,
    BaseNode,
    Edge,
    GameNode,
    ImageNode,
    LabelNode,
    MechanicNode,
    NodeType,
    PathNode,
    RelationType,
    SceneNode,
    SoundNode,
    ThemeNode,
    TransitionNode,
    ZoneNode,
)
from app.agents.schemas.asset_spec import (
    AssetManifest,
    AssetSpec,
    AssetType,
    ContentSpec,
    DimensionSpec,
    PositionSpec,
    StyleSpec,
    WorkerType,
    ASSET_TYPE_TO_WORKER,
    estimate_manifest_cost,
)
from app.agents.schemas.game_design_v3 import (
    AnimationDesign,
    ClickDesign,
    DifficultySpec,
    DistractorLabel,
    GameDesignV3,
    HierarchyGroup,
    HierarchySpec,
    LabelDesign,
    MechanicAnimations,
    MechanicDesign,
    MechanicFeedback,
    MechanicScoring,
    MechanicTransitionSpec,
    MediaAssetDesign,
    MisconceptionFeedback,
    PathDesign,
    SceneDesign,
    SceneTransitionSpec,
    SceneVisualSpec,
    SoundDesign,
    ThemeSpec,
    ZoneSpec,
    validate_game_design,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def make_heart_game_design() -> GameDesignV3:
    """Canonical test fixture: heart anatomy game with 3 mechanics in 1 scene."""
    return GameDesignV3(
        title="Heart Anatomy Explorer",
        narrative_intro="Explore the human heart from chambers to blood flow.",
        pedagogical_reasoning="Progressive: naming (recall) → flow (understanding) → classification (application).",
        learning_objectives=[
            "Identify the 4 chambers and major vessels of the heart",
            "Trace the path of blood through the heart",
            "Classify regions as oxygenated or deoxygenated",
        ],
        estimated_duration_minutes=8,
        theme=ThemeSpec(
            visual_tone="clinical_educational",
            color_palette={
                "primary": "#3b82f6",
                "success": "#22c55e",
                "error": "#ef4444",
            },
            background_description="Subtle blue gradient with floating molecule patterns",
        ),
        labels=LabelDesign(
            zone_labels=[
                "Left Atrium", "Right Atrium", "Left Ventricle", "Right Ventricle",
                "Aorta", "Pulmonary Artery", "Superior Vena Cava", "Inferior Vena Cava",
            ],
            group_only_labels=["Heart"],
            distractor_labels=[
                DistractorLabel(text="Carotid Artery", explanation="Part of neck vasculature, not the heart"),
                DistractorLabel(text="Femoral Vein", explanation="Located in the leg, not the heart"),
            ],
            hierarchy=HierarchySpec(
                enabled=True,
                strategy="Progressive reveal from chambers to vessels",
                groups=[
                    HierarchyGroup(parent="Heart", children=["Left Atrium", "Right Atrium", "Left Ventricle", "Right Ventricle"]),
                ],
            ),
        ),
        scenes=[
            SceneDesign(
                scene_number=1,
                title="The Human Heart",
                learning_goal="Master heart anatomy from naming to function",
                visual=SceneVisualSpec(
                    description="Cross-sectional anatomical diagram of the human heart",
                    required_elements=["4 chambers", "valves", "major blood vessels"],
                    style="clean educational, no pre-printed labels",
                    image_source="search_then_generate",
                ),
                zone_labels=[
                    "Left Atrium", "Right Atrium", "Left Ventricle", "Right Ventricle",
                    "Aorta", "Pulmonary Artery", "Superior Vena Cava", "Inferior Vena Cava",
                ],
                zone_specs=[
                    ZoneSpec(label="Left Atrium", zone_type="area", difficulty=2),
                    ZoneSpec(label="Right Ventricle", zone_type="area", difficulty=2,
                             hint_progression=["It's on the right side of the diagram", "Lower chamber"]),
                ],
                mechanics=[
                    MechanicDesign(
                        type="drag_drop",
                        description="Drag labels onto heart chambers and vessels",
                        zone_labels_used=["Left Atrium", "Right Atrium", "Left Ventricle", "Right Ventricle",
                                          "Aorta", "Pulmonary Artery", "Superior Vena Cava", "Inferior Vena Cava"],
                        scoring=MechanicScoring(points_per_correct=10, partial_credit=True),
                        feedback=MechanicFeedback(
                            on_correct="Label snaps with green glow",
                            on_incorrect="Label shakes and returns",
                            misconception_feedback=[
                                MisconceptionFeedback(
                                    trigger="Right Ventricle on left side",
                                    message="The heart's right side appears on YOUR left because you're looking at it from the front.",
                                ),
                            ],
                        ),
                        animations=MechanicAnimations(
                            on_correct=AnimationDesign(type="glow", color="#22c55e", duration_ms=400),
                            on_incorrect=AnimationDesign(type="shake", duration_ms=300),
                        ),
                    ),
                    MechanicDesign(
                        type="trace_path",
                        description="Trace blood flow through the heart",
                        zone_labels_used=["Superior Vena Cava", "Right Atrium", "Right Ventricle",
                                          "Pulmonary Artery", "Left Atrium", "Left Ventricle", "Aorta"],
                        path_config=PathDesign(
                            waypoints=["Superior Vena Cava", "Right Atrium", "Right Ventricle",
                                       "Pulmonary Artery", "Left Atrium", "Left Ventricle", "Aorta"],
                            path_type="linear",
                            visual_style="blue_to_red_gradient",
                        ),
                        scoring=MechanicScoring(points_per_correct=10),
                        feedback=MechanicFeedback(
                            on_correct="Flow arrow extends. Whoosh sound.",
                            on_incorrect="Flash red. Blood must pass through lungs.",
                        ),
                    ),
                    MechanicDesign(
                        type="click_to_identify",
                        description="Click each region to classify oxygenation",
                        zone_labels_used=["Right Atrium", "Right Ventricle", "Pulmonary Artery",
                                          "Left Atrium", "Left Ventricle", "Aorta",
                                          "Superior Vena Cava", "Inferior Vena Cava"],
                        click_config=ClickDesign(
                            click_options=["Oxygenated (Red)", "Deoxygenated (Blue)"],
                            correct_assignments={
                                "Right Atrium": "Deoxygenated (Blue)",
                                "Right Ventricle": "Deoxygenated (Blue)",
                                "Pulmonary Artery": "Deoxygenated (Blue)",
                                "Left Atrium": "Oxygenated (Red)",
                                "Left Ventricle": "Oxygenated (Red)",
                                "Aorta": "Oxygenated (Red)",
                                "Superior Vena Cava": "Deoxygenated (Blue)",
                                "Inferior Vena Cava": "Deoxygenated (Blue)",
                            },
                        ),
                        scoring=MechanicScoring(points_per_correct=10),
                        feedback=MechanicFeedback(on_correct="Zone fills with correct color."),
                    ),
                ],
                mechanic_transitions=[
                    MechanicTransitionSpec(
                        from_mechanic="drag_drop",
                        to_mechanic="trace_path",
                        trigger="score_threshold",
                        threshold=0.7,
                        animation="fade",
                        message="Great! Now trace the blood flow.",
                    ),
                    MechanicTransitionSpec(
                        from_mechanic="trace_path",
                        to_mechanic="click_to_identify",
                        trigger="all_complete",
                        animation="fade",
                    ),
                ],
                media_assets=[
                    MediaAssetDesign(
                        id="bg_molecules",
                        description="Floating molecule patterns",
                        asset_type="css_animation",
                        placement="background",
                        layer=-1,
                        trigger="always",
                    ),
                    MediaAssetDesign(
                        id="flow_arrows",
                        description="Animated blood flow arrows along vessels",
                        asset_type="gif",
                        placement="overlay",
                        layer=2,
                        trigger="on_mechanic_start",
                        trigger_config={"mechanic_type": "trace_path"},
                        generation_prompt="Animated red and blue blood flow arrows on a heart diagram",
                    ),
                ],
                sounds=[
                    SoundDesign(event="correct", description="Bright chime, 200ms"),
                    SoundDesign(event="incorrect", description="Soft buzz, 150ms"),
                    SoundDesign(event="completion", description="Triumphant fanfare, 1500ms"),
                ],
                max_score=230,
            ),
        ],
        difficulty=DifficultySpec(
            approach="Progressive: naming (recall) → flow (understanding) → classification (application)",
            initial_level="medium",
            hint_enabled=True,
        ),
        total_max_score=230,
        star_thresholds=[0.6, 0.8, 1.0],
    )


def make_heart_asset_graph() -> AssetGraph:
    """Build an AssetGraph from the heart game design."""
    graph = AssetGraph()

    # Game node
    game = GameNode(id="game_1", title="Heart Anatomy Explorer", total_max_score=230)
    graph.add_node(game)

    # Theme
    theme = ThemeNode(id="theme_1", visual_tone="clinical_educational")
    graph.add_node(theme)
    graph.add_edge_simple("game_1", "theme_1", RelationType.STYLED_BY)

    # Scene
    scene = SceneNode(id="scene_1", scene_number=1, title="The Human Heart", max_score=230)
    graph.add_node(scene)
    graph.add_edge_simple("game_1", "scene_1", RelationType.CONTAINS)

    # Primary image
    img = ImageNode(
        id="img_heart",
        description="Cross-sectional anatomical diagram of the human heart",
        required_elements=["4 chambers", "valves", "major blood vessels"],
        image_source="search_then_generate",
    )
    graph.add_node(img)
    graph.add_edge_simple("scene_1", "img_heart", RelationType.HAS_IMAGE)

    # Zones
    zone_labels = ["Left Atrium", "Right Atrium", "Left Ventricle", "Right Ventricle",
                    "Aorta", "Pulmonary Artery", "Superior Vena Cava", "Inferior Vena Cava"]
    for i, label in enumerate(zone_labels):
        zone = ZoneNode(id=f"zone_{i}", label=label, zone_type="area", hierarchy_level=1)
        graph.add_node(zone)
        graph.add_edge_simple(f"zone_{i}", "img_heart", RelationType.POSITIONED_ON)

    # Labels (correct + distractors)
    for i, label in enumerate(zone_labels):
        lbl = LabelNode(id=f"label_{i}", text=label, correct_zone_id=f"zone_{i}")
        graph.add_node(lbl)
        graph.add_edge_simple(f"label_{i}", f"zone_{i}", RelationType.TARGETS)

    dist1 = LabelNode(id="label_dist_1", text="Carotid Artery", is_distractor=True,
                       distractor_explanation="Part of neck vasculature")
    dist2 = LabelNode(id="label_dist_2", text="Femoral Vein", is_distractor=True,
                       distractor_explanation="Located in the leg")
    graph.add_node(dist1)
    graph.add_node(dist2)

    # Mechanics
    mech_dd = MechanicNode(id="mech_drag_drop", mechanic_type="drag_drop",
                           description="Drag labels onto heart")
    mech_tp = MechanicNode(id="mech_trace_path", mechanic_type="trace_path",
                           description="Trace blood flow")
    mech_ci = MechanicNode(id="mech_click_identify", mechanic_type="click_to_identify",
                           description="Classify oxygenation")
    graph.add_node(mech_dd)
    graph.add_node(mech_tp)
    graph.add_node(mech_ci)
    graph.add_edge_simple("scene_1", "mech_drag_drop", RelationType.CONTAINS)
    graph.add_edge_simple("scene_1", "mech_trace_path", RelationType.CONTAINS)
    graph.add_edge_simple("scene_1", "mech_click_identify", RelationType.CONTAINS)

    # Mechanic → zones
    for i in range(8):
        graph.add_edge_simple("mech_drag_drop", f"zone_{i}", RelationType.OPERATES_ON)

    # Path for trace_path
    path = PathNode(
        id="path_blood_flow",
        description="Blood flow through the heart",
        path_type="linear",
        waypoint_zone_ids=["zone_6", "zone_1", "zone_3", "zone_5", "zone_0", "zone_2", "zone_4"],
    )
    graph.add_node(path)
    graph.add_edge_simple("mech_trace_path", "path_blood_flow", RelationType.FOLLOWS_PATH)

    # Scene-level assets (independent of zones)
    bg_asset = AssetNode(
        id="asset_bg_molecules",
        asset_type="css_animation",
        description="Floating molecule patterns",
        placement="background",
        layer=-1,
        game_logic=AssetGameLogic(trigger="always"),
    )
    graph.add_node(bg_asset)
    graph.add_edge_simple("scene_1", "asset_bg_molecules", RelationType.HAS_BACKGROUND)

    flow_asset = AssetNode(
        id="asset_flow_arrows",
        asset_type="gif",
        description="Animated blood flow arrows",
        placement="overlay",
        layer=2,
        game_logic=AssetGameLogic(
            trigger="on_mechanic_start",
            trigger_config={"mechanic_type": "trace_path"},
            states={
                "hidden": {"opacity": 0},
                "visible": {"opacity": 1},
            },
            initial_state="hidden",
            state_transitions=[
                {"from": "hidden", "to": "visible", "when": "on_mechanic_start"},
            ],
        ),
    )
    graph.add_node(flow_asset)
    graph.add_edge_simple("scene_1", "asset_flow_arrows", RelationType.CONTAINS)

    # Animations
    anim_correct = AnimationNode(id="anim_correct", animation_type="glow",
                                  trigger="on_correct", color="#22c55e", duration_ms=400)
    anim_incorrect = AnimationNode(id="anim_incorrect", animation_type="shake",
                                    trigger="on_incorrect", duration_ms=300)
    anim_complete = AnimationNode(id="anim_complete", animation_type="confetti",
                                   trigger="on_complete", duration_ms=2500)
    graph.add_node(anim_correct)
    graph.add_node(anim_incorrect)
    graph.add_node(anim_complete)
    graph.add_edge_simple("mech_drag_drop", "anim_correct", RelationType.TRIGGERS)
    graph.add_edge_simple("mech_drag_drop", "anim_incorrect", RelationType.TRIGGERS)
    graph.add_edge_simple("scene_1", "anim_complete", RelationType.TRIGGERS)

    # Sounds
    snd_correct = SoundNode(id="snd_correct", sound_event="correct", description="Bright chime")
    snd_incorrect = SoundNode(id="snd_incorrect", sound_event="incorrect", description="Soft buzz")
    snd_complete = SoundNode(id="snd_complete", sound_event="completion", description="Fanfare")
    graph.add_node(snd_correct)
    graph.add_node(snd_incorrect)
    graph.add_node(snd_complete)

    # Transitions
    trans_1 = TransitionNode(id="trans_dd_tp", from_id="mech_drag_drop", to_id="mech_trace_path",
                              trigger="score_threshold", threshold=0.7, animation="fade",
                              message="Great! Now trace the blood flow.")
    trans_2 = TransitionNode(id="trans_tp_ci", from_id="mech_trace_path", to_id="mech_click_identify",
                              trigger="all_complete", animation="fade")
    graph.add_node(trans_1)
    graph.add_node(trans_2)
    graph.add_edge_simple("mech_drag_drop", "trans_dd_tp", RelationType.TRANSITIONS_TO)
    graph.add_edge_simple("mech_trace_path", "trans_tp_ci", RelationType.TRANSITIONS_TO)

    # Generation dependencies
    graph.add_edge_simple("img_heart", "asset_flow_arrows", RelationType.DEPENDS_ON)
    for i in range(8):
        graph.add_edge_simple("img_heart", f"zone_{i}", RelationType.DEPENDS_ON)

    return graph


# ---------------------------------------------------------------------------
# Tests: GameDesignV3
# ---------------------------------------------------------------------------

class TestGameDesignV3:
    def test_create_heart_design(self):
        design = make_heart_game_design()
        assert design.title == "Heart Anatomy Explorer"
        assert len(design.scenes) == 1
        assert len(design.scenes[0].mechanics) == 3
        assert design.total_max_score == 230

    def test_labels_global(self):
        design = make_heart_game_design()
        assert len(design.labels.zone_labels) == 8
        assert len(design.labels.distractor_labels) == 2
        assert design.labels.hierarchy.enabled is True
        assert len(design.labels.hierarchy.groups) == 1

    def test_mechanics_in_scene(self):
        design = make_heart_game_design()
        scene = design.scenes[0]
        types = [m.type for m in scene.mechanics]
        assert types == ["drag_drop", "trace_path", "click_to_identify"]

    def test_trace_path_has_config(self):
        design = make_heart_game_design()
        trace = design.scenes[0].mechanics[1]
        assert trace.path_config is not None
        assert len(trace.path_config.waypoints) == 7
        assert trace.path_config.path_type == "linear"

    def test_click_identify_has_config(self):
        design = make_heart_game_design()
        click = design.scenes[0].mechanics[2]
        assert click.click_config is not None
        assert len(click.click_config.click_options) == 2
        assert len(click.click_config.correct_assignments) == 8

    def test_mechanic_transitions(self):
        design = make_heart_game_design()
        scene = design.scenes[0]
        assert len(scene.mechanic_transitions) == 2
        assert scene.mechanic_transitions[0].from_mechanic == "drag_drop"
        assert scene.mechanic_transitions[0].to_mechanic == "trace_path"

    def test_media_assets_scene_level(self):
        design = make_heart_game_design()
        scene = design.scenes[0]
        assert len(scene.media_assets) == 2
        bg = scene.media_assets[0]
        assert bg.placement == "background"
        assert bg.trigger == "always"
        overlay = scene.media_assets[1]
        assert overlay.trigger == "on_mechanic_start"

    def test_sounds(self):
        design = make_heart_game_design()
        scene = design.scenes[0]
        assert len(scene.sounds) == 3
        events = [s.event for s in scene.sounds]
        assert "correct" in events
        assert "completion" in events

    def test_validate_valid_design(self):
        design = make_heart_game_design()
        issues = validate_game_design(design)
        assert issues == [], f"Unexpected issues: {issues}"

    def test_validate_missing_label(self):
        design = make_heart_game_design()
        design.scenes[0].zone_labels.append("Nonexistent Organ")
        issues = validate_game_design(design)
        assert any("not in global labels" in i for i in issues)

    def test_validate_missing_mechanic(self):
        design = make_heart_game_design()
        design.scenes[0].mechanics = []
        issues = validate_game_design(design)
        assert any("at least one mechanic" in i for i in issues)

    def test_validate_bad_mechanic_type(self):
        design = make_heart_game_design()
        design.scenes[0].mechanics[0].type = "rocket_launch"
        issues = validate_game_design(design)
        assert any("unknown mechanic type" in i for i in issues)

    def test_serialization_roundtrip(self):
        design = make_heart_game_design()
        data = design.model_dump()
        restored = GameDesignV3(**data)
        assert restored.title == design.title
        assert len(restored.scenes) == len(design.scenes)
        assert len(restored.scenes[0].mechanics) == len(design.scenes[0].mechanics)

    def test_json_roundtrip(self):
        design = make_heart_game_design()
        json_str = design.model_dump_json()
        data = json.loads(json_str)
        restored = GameDesignV3(**data)
        assert restored.title == design.title


# ---------------------------------------------------------------------------
# Tests: AssetGraph
# ---------------------------------------------------------------------------

class TestAssetGraph:
    def test_create_heart_graph(self):
        graph = make_heart_asset_graph()
        assert graph.node_count > 0
        assert graph.edge_count > 0

    def test_scene_nodes(self):
        graph = make_heart_asset_graph()
        scenes = graph.get_scene_nodes()
        assert len(scenes) == 1
        assert scenes[0].title == "The Human Heart"

    def test_mechanics_for_scene(self):
        graph = make_heart_asset_graph()
        mechs = graph.get_mechanics_for_scene("scene_1")
        assert len(mechs) == 3
        types = {m.mechanic_type for m in mechs}
        assert types == {"drag_drop", "trace_path", "click_to_identify"}

    def test_image_for_scene(self):
        graph = make_heart_asset_graph()
        img = graph.get_image_for_scene("scene_1")
        assert img is not None
        assert img.id == "img_heart"

    def test_zones_for_image(self):
        graph = make_heart_asset_graph()
        zones = graph.get_zones_for_image("img_heart")
        assert len(zones) == 8

    def test_labels_for_zone(self):
        graph = make_heart_asset_graph()
        labels = graph.get_labels_for_zone("zone_0")
        assert len(labels) == 1
        assert labels[0].text == "Left Atrium"

    def test_scene_level_assets(self):
        graph = make_heart_asset_graph()
        assets = graph.get_assets_for_scene("scene_1")
        assert len(assets) == 2
        asset_ids = {a.id for a in assets}
        assert "asset_bg_molecules" in asset_ids
        assert "asset_flow_arrows" in asset_ids

    def test_asset_game_logic(self):
        graph = make_heart_asset_graph()
        flow = graph.get_node("asset_flow_arrows")
        assert flow is not None
        assert flow.game_logic is not None
        assert flow.game_logic.trigger == "on_mechanic_start"
        assert flow.game_logic.initial_state == "hidden"
        assert len(flow.game_logic.states) == 2
        assert len(flow.game_logic.state_transitions) == 1

    def test_paths_for_scene(self):
        graph = make_heart_asset_graph()
        paths = graph.get_paths_for_scene("scene_1")
        assert len(paths) == 1
        assert paths[0].path_type == "linear"
        assert len(paths[0].waypoint_zone_ids) == 7

    def test_transitions(self):
        graph = make_heart_asset_graph()
        transitions = graph.get_transitions_from("mech_drag_drop")
        assert len(transitions) == 1
        assert transitions[0].trigger == "score_threshold"

    def test_topological_sort(self):
        graph = make_heart_asset_graph()
        order = graph.get_generation_order()
        # img_heart should come before zones and flow_arrows
        img_idx = order.index("img_heart")
        for i in range(8):
            zone_idx = order.index(f"zone_{i}")
            assert img_idx < zone_idx, f"img_heart should come before zone_{i}"
        flow_idx = order.index("asset_flow_arrows")
        assert img_idx < flow_idx, "img_heart should come before flow_arrows"

    def test_validate_graph(self):
        graph = make_heart_asset_graph()
        issues = graph.validate_graph()
        assert issues == [], f"Unexpected issues: {issues}"

    def test_serialization_roundtrip(self):
        graph = make_heart_asset_graph()
        data = graph.serialize()
        restored = AssetGraph.deserialize(data)
        assert restored.node_count == graph.node_count
        assert restored.edge_count == graph.edge_count
        # Check a specific node survived
        scene = restored.get_node("scene_1")
        assert scene is not None
        assert scene.title == "The Human Heart"

    def test_json_roundtrip(self):
        graph = make_heart_asset_graph()
        data = graph.serialize()
        json_str = json.dumps(data)
        restored_data = json.loads(json_str)
        restored = AssetGraph.deserialize(restored_data)
        assert restored.node_count == graph.node_count

    def test_scene_subgraph(self):
        graph = make_heart_asset_graph()
        sub = graph.get_scene_subgraph("scene_1")
        # Should contain scene, image, zones, labels, mechanics, assets, animations, sounds, paths, transitions, theme
        assert sub.has_node("scene_1")
        assert sub.has_node("img_heart")
        assert sub.has_node("zone_0")
        assert sub.has_node("label_0")
        assert sub.has_node("mech_drag_drop")
        assert sub.has_node("asset_bg_molecules")
        assert sub.has_node("asset_flow_arrows")
        assert sub.has_node("anim_correct")
        assert sub.has_node("path_blood_flow")
        assert sub.has_node("trans_dd_tp")
        assert sub.has_node("theme_1")
        # Should NOT contain the game node (it's the parent)
        # Subgraph is scene-scoped
        assert sub.edge_count > 0

    def test_scene_subgraph_performance(self):
        """Subgraph should be smaller than full graph."""
        graph = make_heart_asset_graph()
        sub = graph.get_scene_subgraph("scene_1")
        # Scene subgraph shouldn't include distractor labels not connected to scene zones
        # (distractors are added at game level, not connected to zones)
        assert sub.node_count <= graph.node_count

    def test_cycle_detection(self):
        graph = AssetGraph()
        a = BaseNode(id="a", node_type=NodeType.ASSET)
        b = BaseNode(id="b", node_type=NodeType.ASSET)
        c = BaseNode(id="c", node_type=NodeType.ASSET)
        graph.add_node(a)
        graph.add_node(b)
        graph.add_node(c)
        graph.add_edge_simple("a", "b", RelationType.DEPENDS_ON)
        graph.add_edge_simple("b", "c", RelationType.DEPENDS_ON)
        graph.add_edge_simple("c", "a", RelationType.DEPENDS_ON)  # cycle!
        with pytest.raises(ValueError, match="Cycle detected"):
            graph.topological_sort()


# ---------------------------------------------------------------------------
# Tests: AssetSpec
# ---------------------------------------------------------------------------

class TestAssetSpec:
    def test_create_diagram_spec(self):
        spec = AssetSpec(
            asset_id="heart_diagram",
            asset_type=AssetType.DIAGRAM,
            graph_node_id="img_heart",
            dimensions=DimensionSpec(width=800, height=600, aspect_ratio="4:3"),
            style=StyleSpec(
                visual_tone="clinical_educational",
                style_prompt_suffix="clean educational, no text labels",
                negative_prompt="blurry, text, watermark",
            ),
            content=ContentSpec(
                description="Cross-sectional heart diagram",
                required_elements=["4 chambers", "valves", "vessels"],
            ),
            worker=WorkerType.IMAGE_SEARCH,
            fallback_worker=WorkerType.IMAGEN,
            priority=100,
            scene_number=1,
        )
        assert spec.asset_type == AssetType.DIAGRAM
        assert spec.worker == WorkerType.IMAGE_SEARCH
        assert spec.dimensions.width == 800

    def test_create_zone_detection_spec(self):
        spec = AssetSpec(
            asset_id="zones_scene_1",
            asset_type=AssetType.ZONE_OVERLAY,
            graph_node_id="zone_0",
            content=ContentSpec(
                zone_labels=["Left Atrium", "Right Atrium"],
                zone_hints={"Left Atrium": "Upper left chamber"},
            ),
            worker=WorkerType.ZONE_DETECTOR,
            depends_on=["heart_diagram"],
            scene_number=1,
        )
        assert spec.worker == WorkerType.ZONE_DETECTOR
        assert len(spec.depends_on) == 1

    def test_create_sound_spec(self):
        spec = AssetSpec(
            asset_id="snd_correct",
            asset_type=AssetType.SOUND_EFFECT,
            graph_node_id="snd_correct",
            content=ContentSpec(
                sound_event="correct",
                sound_description="Bright chime, 200ms, satisfying",
            ),
            worker=WorkerType.AUDIO_GEN,
        )
        assert spec.worker == WorkerType.AUDIO_GEN

    def test_asset_manifest(self):
        manifest = AssetManifest(game_id="heart_game")
        manifest.add_spec(AssetSpec(
            asset_id="diagram", asset_type=AssetType.DIAGRAM,
            graph_node_id="img", worker=WorkerType.IMAGE_SEARCH,
        ))
        manifest.add_spec(AssetSpec(
            asset_id="zones", asset_type=AssetType.ZONE_OVERLAY,
            graph_node_id="z", worker=WorkerType.ZONE_DETECTOR,
            depends_on=["diagram"],
        ))
        manifest.add_spec(AssetSpec(
            asset_id="bg_anim", asset_type=AssetType.CSS_ANIMATION,
            graph_node_id="bg", worker=WorkerType.CSS_ANIMATION,
        ))
        assert len(manifest.specs) == 3
        assert len(manifest.get_specs_by_type(AssetType.DIAGRAM)) == 1
        assert len(manifest.get_pending_specs()) == 3

        manifest.mark_completed("diagram", "/path/to/diagram.png", "/api/assets/diagram.png")
        assert manifest.get_spec("diagram").status == "completed"
        assert len(manifest.get_pending_specs()) == 2
        assert len(manifest.get_completed_specs()) == 1

    def test_cost_estimation(self):
        manifest = AssetManifest(game_id="test")
        manifest.add_spec(AssetSpec(
            asset_id="a", asset_type=AssetType.DIAGRAM,
            graph_node_id="x", worker=WorkerType.IMAGEN,
        ))
        manifest.add_spec(AssetSpec(
            asset_id="b", asset_type=AssetType.SOUND_EFFECT,
            graph_node_id="y", worker=WorkerType.AUDIO_GEN,
        ))
        manifest.add_spec(AssetSpec(
            asset_id="c", asset_type=AssetType.CSS_ANIMATION,
            graph_node_id="z", worker=WorkerType.CSS_ANIMATION,
        ))
        cost = estimate_manifest_cost(manifest)
        assert cost == pytest.approx(0.03)  # 0.02 + 0.01 + 0.0

    def test_default_worker_routing(self):
        assert ASSET_TYPE_TO_WORKER[AssetType.DIAGRAM] == WorkerType.IMAGE_SEARCH
        assert ASSET_TYPE_TO_WORKER[AssetType.ZONE_OVERLAY] == WorkerType.ZONE_DETECTOR
        assert ASSET_TYPE_TO_WORKER[AssetType.CSS_ANIMATION] == WorkerType.CSS_ANIMATION
        assert ASSET_TYPE_TO_WORKER[AssetType.SOUND_EFFECT] == WorkerType.AUDIO_GEN
