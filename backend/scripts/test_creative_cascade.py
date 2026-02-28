"""End-to-end integration test for the V4 3-stage creative cascade.

Tests the FULL flow without LLM calls:
  Stage 1: GameConcept creation (WHAT/WHY)
  Stage 2: SceneCreativeDesign per scene (HOW)
  Stage 3: GraphBuilder → GamePlan (deterministic graph)
  Stage 4: Content prompt generation — verify context flows through
  Stage 5: Content schema parsing — verify Pydantic models accept LLM-shaped output
  Stage 6: Blueprint assembly — verify all fields reach final blueprint

Uses a multi-scene heart anatomy game with ALL 8 supported mechanics.
"""

import json
import sys
import traceback

# === Stage 1: GameConcept ===

def test_stage_1():
    """Create a realistic GameConcept for a heart anatomy lesson."""
    from app.v4.schemas.game_concept import GameConcept, SceneConcept, MechanicChoice

    concept = GameConcept(
        title="Journey Through the Heart",
        subject="Biology",
        difficulty="intermediate",
        estimated_duration_minutes=15,
        narrative_theme="medical_exploration",
        narrative_intro="Join Dr. Heart on an adventure through the cardiovascular system!",
        completion_message="You've mastered the heart anatomy!",
        all_zone_labels=[
            "Left Atrium", "Right Atrium", "Left Ventricle", "Right Ventricle",
            "Aorta", "Pulmonary Artery", "Pulmonary Vein", "Vena Cava",
            "Mitral Valve", "Tricuspid Valve",
        ],
        distractor_labels=["Spleen", "Kidney", "Liver"],
        label_hierarchy={"Left Atrium": ["Mitral Valve"], "Right Atrium": ["Tricuspid Valve"]},
        scenes=[
            SceneConcept(
                title="Heart Chambers",
                learning_goal="Identify the four chambers and their roles",
                narrative_intro="The heart has four chambers that work together.",
                zone_labels=["Left Atrium", "Right Atrium", "Left Ventricle", "Right Ventricle"],
                needs_diagram=True,
                image_description="Labeled diagram of the human heart",
                mechanics=[
                    MechanicChoice(
                        mechanic_type="drag_drop",
                        learning_purpose="Identify the four chambers",
                        zone_labels_used=["Left Atrium", "Right Atrium", "Left Ventricle", "Right Ventricle"],
                        expected_item_count=4,
                        points_per_item=10,
                    ),
                    MechanicChoice(
                        mechanic_type="click_to_identify",
                        learning_purpose="Test recall of chamber functions",
                        zone_labels_used=["Left Atrium", "Right Atrium", "Left Ventricle", "Right Ventricle"],
                        expected_item_count=4,
                        points_per_item=15,
                    ),
                    MechanicChoice(
                        mechanic_type="description_matching",
                        learning_purpose="Match descriptions to chambers",
                        zone_labels_used=["Left Atrium", "Right Atrium", "Left Ventricle", "Right Ventricle"],
                        expected_item_count=4,
                        points_per_item=10,
                    ),
                ],
            ),
            SceneConcept(
                title="Blood Flow Pathway",
                learning_goal="Understand the path of blood through the heart",
                narrative_intro="Follow the blood as it flows through the heart.",
                zone_labels=["Vena Cava", "Right Atrium", "Right Ventricle", "Pulmonary Artery",
                             "Pulmonary Vein", "Left Atrium", "Left Ventricle", "Aorta"],
                needs_diagram=True,
                image_description="Diagram showing blood flow through the heart",
                mechanics=[
                    MechanicChoice(
                        mechanic_type="trace_path",
                        learning_purpose="Trace blood flow through the heart",
                        zone_labels_used=["Vena Cava", "Right Atrium", "Right Ventricle", "Pulmonary Artery",
                                          "Pulmonary Vein", "Left Atrium", "Left Ventricle", "Aorta"],
                        expected_item_count=8,
                        points_per_item=5,
                        advance_trigger="completion",
                    ),
                    MechanicChoice(
                        mechanic_type="sequencing",
                        learning_purpose="Order the steps of blood circulation",
                        zone_labels_used=[],  # Content-only
                        expected_item_count=6,
                        points_per_item=10,
                        advance_trigger="completion",
                    ),
                ],
            ),
            SceneConcept(
                title="Heart Conditions",
                learning_goal="Understand common heart conditions and their treatments",
                narrative_intro="What happens when the heart doesn't work properly?",
                zone_labels=[],
                needs_diagram=False,
                image_description="",
                mechanics=[
                    MechanicChoice(
                        mechanic_type="sorting_categories",
                        learning_purpose="Categorize symptoms by condition",
                        zone_labels_used=[],
                        expected_item_count=8,
                        points_per_item=10,
                    ),
                    MechanicChoice(
                        mechanic_type="memory_match",
                        learning_purpose="Match conditions with treatments",
                        zone_labels_used=[],
                        expected_item_count=5,
                        points_per_item=10,
                    ),
                    MechanicChoice(
                        mechanic_type="branching_scenario",
                        learning_purpose="Diagnose a patient with heart symptoms",
                        zone_labels_used=[],
                        expected_item_count=4,
                        points_per_item=20,
                        advance_trigger="completion",
                    ),
                ],
            ),
        ],
    )

    # Validate
    assert len(concept.scenes) == 3, f"Expected 3 scenes, got {len(concept.scenes)}"
    total_mechanics = sum(len(s.mechanics) for s in concept.scenes)
    assert total_mechanics == 8, f"Expected 8 mechanics, got {total_mechanics}"
    assert len(concept.all_zone_labels) == 10

    mechanic_types = set()
    for scene in concept.scenes:
        for m in scene.mechanics:
            mechanic_types.add(m.mechanic_type)

    expected_types = {
        "drag_drop", "click_to_identify", "description_matching",
        "trace_path", "sequencing", "sorting_categories",
        "memory_match", "branching_scenario",
    }
    assert mechanic_types == expected_types, f"Missing mechanics: {expected_types - mechanic_types}"

    print(f"  ✓ GameConcept: {concept.title}")
    print(f"    {len(concept.scenes)} scenes, {total_mechanics} mechanics, {len(concept.all_zone_labels)} labels")
    return concept


# === Stage 2: SceneCreativeDesign ===

def test_stage_2(concept):
    """Create SceneCreativeDesigns as the scene designer LLM would."""
    from app.v4.schemas.creative_design import (
        SceneCreativeDesign, MechanicCreativeDesign, ImageSpec,
    )

    designs = {}

    # Scene 1: Heart Chambers
    designs["scene_1"] = SceneCreativeDesign(
        scene_id="scene_1",
        title="Heart Chambers",
        visual_concept="Detailed anatomical cross-section of the human heart",
        color_palette_direction="warm reds and blues for arterial/venous",
        spatial_layout="centered diagram with labels around",
        atmosphere="clinical yet engaging",
        image_spec=ImageSpec(
            description="Anatomical cross-section of the human heart showing all four chambers",
            must_include_structures=["Left Atrium", "Right Atrium", "Left Ventricle", "Right Ventricle"],
            style="clean_educational",
            annotation_preference="clean_unlabeled",
            color_direction="arterial red, venous blue",
        ),
        mechanic_designs=[
            MechanicCreativeDesign(
                mechanic_type="drag_drop",
                visual_style="anatomical labels",
                card_type="text_badge",
                layout_mode="radial",
                connector_style="arrow",
                color_direction="chamber colors",
                instruction_text="Drag each label to the correct chamber of the heart",
                instruction_tone="educational",
                narrative_hook="Can you identify all four chambers?",
                hint_strategy="progressive",
                feedback_style="encouraging",
                difficulty_curve="gradual",
                generation_goal="Generate labels matching the four chambers with plausible distractors",
                key_concepts=["atrium", "ventricle", "left/right orientation"],
                pedagogical_focus="spatial awareness of heart anatomy",
            ),
            MechanicCreativeDesign(
                mechanic_type="click_to_identify",
                visual_style="clean highlight",
                instruction_text="Click on the chamber described in each prompt",
                generation_goal="Create identification prompts describing chamber functions",
                key_concepts=["receiving blood", "pumping blood", "oxygenated vs deoxygenated"],
                prompt_style="functional",
                hint_strategy="progressive",
                feedback_style="explanatory",
                difficulty_curve="gradual",
            ),
            MechanicCreativeDesign(
                mechanic_type="description_matching",
                visual_style="side panel descriptions",
                instruction_text="Match each description to the correct chamber",
                generation_goal="Create functional descriptions for each chamber",
                key_concepts=["function", "blood type", "wall thickness"],
                description_source="functional_role",
                hint_strategy="none",
                feedback_style="detailed",
                difficulty_curve="flat",
            ),
        ],
        scene_narrative="Let's start by identifying the four chambers of the heart.",
        transition_narrative="Now that you know the chambers, let's see how blood flows through them.",
    )

    # Scene 2: Blood Flow Pathway
    designs["scene_2"] = SceneCreativeDesign(
        scene_id="scene_2",
        title="Blood Flow Pathway",
        visual_concept="Heart diagram with animated blood flow arrows",
        color_palette_direction="red for oxygenated, blue for deoxygenated",
        image_spec=ImageSpec(
            description="Heart diagram showing blood flow direction with arrows",
            must_include_structures=["Vena Cava", "Right Atrium", "Right Ventricle", "Pulmonary Artery",
                                      "Pulmonary Vein", "Left Atrium", "Left Ventricle", "Aorta"],
            style="clean_educational",
        ),
        mechanic_designs=[
            MechanicCreativeDesign(
                mechanic_type="trace_path",
                visual_style="flowing animation",
                instruction_text="Trace the path of blood from the vena cava through the heart to the aorta",
                generation_goal="Create waypoint path following blood circulation",
                key_concepts=["pulmonary circuit", "systemic circuit", "oxygenation"],
                path_process="blood circulation through heart chambers",
                connector_style="flowing",
                hint_strategy="waypoint_highlight",
                feedback_style="encouraging",
                difficulty_curve="gradual",
            ),
            MechanicCreativeDesign(
                mechanic_type="sequencing",
                visual_style="step cards",
                card_type="illustrated",
                layout_mode="vertical_list",
                connector_style="arrow",
                instruction_text="Arrange the steps of blood circulation in the correct order",
                generation_goal="Create sequence steps for blood flow through the heart",
                key_concepts=["deoxygenated blood", "oxygenated blood", "chambers", "vessels"],
                sequence_topic="blood circulation pathway through the heart",
                hint_strategy="progressive",
                feedback_style="encouraging",
                difficulty_curve="gradual",
            ),
        ],
        scene_narrative="Blood follows a specific path through the heart.",
    )

    # Scene 3: Heart Conditions (content-only, no diagram)
    designs["scene_3"] = SceneCreativeDesign(
        scene_id="scene_3",
        title="Heart Conditions",
        visual_concept="Clinical information cards",
        mechanic_designs=[
            MechanicCreativeDesign(
                mechanic_type="sorting_categories",
                visual_style="condition cards",
                card_type="text_with_icon",
                layout_mode="bucket",
                instruction_text="Sort the symptoms into the correct heart condition category",
                generation_goal="Create symptom categories for common heart conditions",
                key_concepts=["arrhythmia", "heart failure", "coronary artery disease"],
                category_names=["Arrhythmia", "Heart Failure", "Coronary Artery Disease"],
                hint_strategy="category_hint",
                feedback_style="clinical",
                difficulty_curve="steep",
            ),
            MechanicCreativeDesign(
                mechanic_type="memory_match",
                visual_style="flashcard style",
                instruction_text="Match each heart condition with its primary treatment",
                generation_goal="Create condition-treatment pairs",
                key_concepts=["medication", "surgery", "lifestyle changes"],
                match_type="condition_to_treatment",
                hint_strategy="none",
                feedback_style="explanatory",
                difficulty_curve="flat",
            ),
            MechanicCreativeDesign(
                mechanic_type="branching_scenario",
                visual_style="clinical case study",
                instruction_text="A patient arrives with chest pain. Diagnose and treat.",
                generation_goal="Create a medical decision tree for heart diagnosis",
                key_concepts=["symptoms", "diagnosis", "treatment options"],
                narrative_premise="A 55-year-old patient arrives at the ER with chest pain and shortness of breath",
                hint_strategy="none",
                feedback_style="clinical",
                difficulty_curve="steep",
            ),
        ],
        scene_narrative="Now let's apply your knowledge to real-world heart conditions.",
    )

    # Validate all designs
    for sid, design in designs.items():
        scene_concept = concept.scenes[int(sid.split("_")[1]) - 1]
        assert len(design.mechanic_designs) == len(scene_concept.mechanics), \
            f"{sid}: design has {len(design.mechanic_designs)} mechanics, concept has {len(scene_concept.mechanics)}"
        for i, md in enumerate(design.mechanic_designs):
            assert md.mechanic_type == scene_concept.mechanics[i].mechanic_type, \
                f"{sid} mechanic {i}: design type {md.mechanic_type} != concept type {scene_concept.mechanics[i].mechanic_type}"

    print(f"  ✓ SceneCreativeDesigns: {len(designs)} scenes")
    for sid, d in designs.items():
        print(f"    {sid}: {d.title} — {len(d.mechanic_designs)} mechanic designs")
        for md in d.mechanic_designs:
            hints = []
            if md.sequence_topic: hints.append(f"sequence_topic={md.sequence_topic[:30]}")
            if md.category_names: hints.append(f"categories={md.category_names}")
            if md.narrative_premise: hints.append(f"premise={md.narrative_premise[:30]}")
            if md.path_process: hints.append(f"path={md.path_process[:30]}")
            if md.match_type: hints.append(f"match={md.match_type}")
            if md.prompt_style: hints.append(f"prompt={md.prompt_style}")
            if md.description_source: hints.append(f"desc_src={md.description_source}")
            hint_str = f" ({', '.join(hints)})" if hints else ""
            print(f"      {md.mechanic_type}: {md.generation_goal[:50]}...{hint_str}")

    return designs


# === Stage 3: Graph Builder ===

def test_stage_3(concept, designs):
    """Run the deterministic graph builder."""
    from app.v4.graph_builder import build_game_graph

    plan = build_game_graph(concept, designs)

    # Validate structure
    assert len(plan.scenes) == 3
    assert plan.total_max_score > 0

    for si, scene in enumerate(plan.scenes):
        assert scene.scene_id == f"scene_{si+1}"
        assert scene.scene_number == si + 1
        assert len(scene.mechanics) > 0

        # Verify creative_design propagated
        assert scene.creative_design is not None, f"{scene.scene_id}: no creative_design"
        assert scene.creative_design.scene_id == scene.scene_id

        for mi, mech in enumerate(scene.mechanics):
            # Verify IDs are formulaic
            expected_id = f"s{si+1}_m{mi}"
            assert mech.mechanic_id == expected_id, \
                f"Expected {expected_id}, got {mech.mechanic_id}"

            # Verify creative_design propagated to mechanic
            assert mech.creative_design is not None, \
                f"{mech.mechanic_id}: no creative_design"
            assert mech.creative_design.mechanic_type == mech.mechanic_type, \
                f"{mech.mechanic_id}: creative_design type mismatch"

            # Verify scores computed
            assert mech.max_score == mech.expected_item_count * mech.points_per_item, \
                f"{mech.mechanic_id}: score mismatch"

            # Verify mechanic-specific hints survived
            cd = mech.creative_design
            if mech.mechanic_type == "sequencing":
                assert cd.sequence_topic is not None, f"{mech.mechanic_id}: missing sequence_topic"
            elif mech.mechanic_type == "branching_scenario":
                assert cd.narrative_premise is not None, f"{mech.mechanic_id}: missing narrative_premise"
            elif mech.mechanic_type == "sorting_categories":
                assert cd.category_names is not None, f"{mech.mechanic_id}: missing category_names"
            elif mech.mechanic_type == "trace_path":
                assert cd.path_process is not None, f"{mech.mechanic_id}: missing path_process"
            elif mech.mechanic_type == "memory_match":
                assert cd.match_type is not None, f"{mech.mechanic_id}: missing match_type"
            elif mech.mechanic_type == "click_to_identify":
                assert cd.prompt_style is not None, f"{mech.mechanic_id}: missing prompt_style"
            elif mech.mechanic_type == "description_matching":
                assert cd.description_source is not None, f"{mech.mechanic_id}: missing description_source"

        # Verify connections
        if len(scene.mechanics) > 1:
            assert len(scene.mechanic_connections) == len(scene.mechanics) - 1, \
                f"{scene.scene_id}: expected {len(scene.mechanics) - 1} connections, got {len(scene.mechanic_connections)}"
            for conn in scene.mechanic_connections:
                # Trigger should be resolved (not raw "completion")
                from app.v4.contracts import TRIGGER_MAP
                assert conn.trigger != "", f"Empty trigger for {conn.from_mechanic_id} → {conn.to_mechanic_id}"

        # Verify terminal flag
        assert scene.mechanics[-1].is_terminal, \
            f"{scene.scene_id}: last mechanic should be terminal"

    print(f"  ✓ GamePlan: {plan.title}")
    print(f"    total_max_score={plan.total_max_score}")
    for scene in plan.scenes:
        print(f"    {scene.scene_id}: {scene.title} — {len(scene.mechanics)} mechanics, max_score={scene.scene_max_score}")
        for mech in scene.mechanics:
            print(f"      {mech.mechanic_id}: {mech.mechanic_type} (score={mech.max_score}, terminal={mech.is_terminal})")
        for conn in scene.mechanic_connections:
            print(f"      {conn.from_mechanic_id} → {conn.to_mechanic_id} [trigger={conn.trigger}]")

    return plan


# === Stage 4: Content prompt generation ===

def test_stage_4(plan):
    """Verify content prompts contain all creative design context."""
    from app.v4.prompts.content_generator import build_content_prompt
    from app.v4.agents.content_generator import build_scene_context

    plan_dict = plan.model_dump()

    for scene in plan_dict.get("scenes", []):
        scene_context = build_scene_context(scene, {
            "canonical_labels": plan_dict.get("all_zone_labels", []),
            "label_descriptions": {
                "Left Atrium": "Upper left chamber receiving oxygenated blood from lungs",
                "Right Atrium": "Upper right chamber receiving deoxygenated blood from body",
            },
        })

        for mech in scene.get("mechanics", []):
            prompt = build_content_prompt(
                mechanic_type=mech["mechanic_type"],
                creative_design=mech["creative_design"],
                scene_context=scene_context,
                dk=None,
                mechanic_plan=mech,
            )

            # Verify creative design fields in prompt
            cd = mech["creative_design"]
            assert cd["visual_style"] in prompt, \
                f"{mech['mechanic_id']}: visual_style not in prompt"
            assert cd["generation_goal"] in prompt, \
                f"{mech['mechanic_id']}: generation_goal not in prompt"

            # Verify mechanic-specific hints in prompt
            mtype = mech["mechanic_type"]
            if mtype == "sequencing":
                assert cd["sequence_topic"] in prompt, \
                    f"{mech['mechanic_id']}: sequence_topic not in prompt"
            elif mtype == "branching_scenario":
                assert cd["narrative_premise"] in prompt, \
                    f"{mech['mechanic_id']}: narrative_premise not in prompt"
            elif mtype == "sorting_categories":
                for cat in (cd.get("category_names") or []):
                    assert cat in prompt, \
                        f"{mech['mechanic_id']}: category '{cat}' not in prompt"
            elif mtype == "trace_path":
                assert cd["path_process"] in prompt, \
                    f"{mech['mechanic_id']}: path_process not in prompt"
            elif mtype == "memory_match":
                assert cd["match_type"] in prompt, \
                    f"{mech['mechanic_id']}: match_type not in prompt"
            elif mtype == "click_to_identify":
                assert cd["prompt_style"] in prompt, \
                    f"{mech['mechanic_id']}: prompt_style not in prompt"

            # Verify zone labels in prompt for zone-based mechanics
            if mtype in {"drag_drop", "click_to_identify", "trace_path", "description_matching"}:
                for label in mech.get("zone_labels_used", [])[:3]:
                    assert label in prompt, \
                        f"{mech['mechanic_id']}: zone label '{label}' not in prompt"

    print(f"  ✓ Content prompts: all creative design context verified in prompts")


# === Stage 5: Content schema parsing ===

def test_stage_5():
    """Verify Pydantic content models accept realistic LLM-shaped output."""
    from app.v4.schemas.mechanic_content import get_content_model

    # Simulate LLM output for each mechanic type
    test_outputs = {
        "drag_drop": {
            "labels": ["Left Atrium", "Right Atrium", "Left Ventricle", "Right Ventricle"],
            "distractor_labels": ["Spleen", "Kidney"],
            "interaction_mode": "drag_drop",
            "feedback_timing": "immediate",
            "label_style": "text_badge",
            "leader_line_style": "curved",
            "leader_line_color": "#333",
            "leader_line_animate": True,
            "pin_marker_shape": "circle",
            "label_anchor_side": "auto",
            "tray_position": "bottom",
            "tray_layout": "horizontal",
            "placement_animation": "spring",
            "incorrect_animation": "shake",
            "zone_idle_animation": "pulse",
            "zone_hover_effect": "highlight",
            "max_attempts": None,
            "shuffle_labels": True,
        },
        "click_to_identify": {
            "prompts": [
                {"text": "Click on the chamber that receives oxygenated blood from the lungs",
                 "target_label": "Left Atrium", "explanation": "The left atrium receives blood from pulmonary veins", "order": 0},
                {"text": "Click on the chamber that pumps blood to the body",
                 "target_label": "Left Ventricle", "explanation": "The left ventricle is the strongest chamber", "order": 1},
            ],
            "prompt_style": "functional",
            "selection_mode": "sequential",
            "highlight_style": "outlined",
            "magnification_enabled": False,
            "magnification_factor": 1.5,
            "explore_mode_enabled": False,
            "show_zone_count": True,
        },
        "trace_path": {
            "paths": [
                {
                    "label": "Blood Circulation",
                    "description": "Trace the flow of blood through the heart",
                    "color": "#E74C3C",
                    "requiresOrder": True,
                    "waypoints": [
                        {"label": "Vena Cava", "order": 0},
                        {"label": "Right Atrium", "order": 1},
                        {"label": "Right Ventricle", "order": 2},
                        {"label": "Pulmonary Artery", "order": 3},
                    ],
                }
            ],
            "path_type": "linear",
            "drawing_mode": "click_waypoints",
            "particleTheme": "dots",
            "particleSpeed": "medium",
            "color_transition_enabled": False,
            "show_direction_arrows": True,
            "show_waypoint_labels": True,
            "show_full_flow_on_complete": True,
            "submit_mode": "immediate",
        },
        "sequencing": {
            "items": [
                {"id": "s1", "content": "Blood enters via vena cava", "explanation": "First step"},
                {"id": "s2", "content": "Blood fills right atrium", "explanation": "Second step"},
                {"id": "s3", "content": "Blood moves to right ventricle", "explanation": "Third step"},
                {"id": "s4", "content": "Blood pumped to lungs via pulmonary artery", "explanation": "Fourth step"},
                {"id": "s5", "content": "Oxygenated blood returns via pulmonary vein", "explanation": "Fifth step"},
                {"id": "s6", "content": "Blood pumped to body via aorta", "explanation": "Sixth step"},
            ],
            "correct_order": ["s1", "s2", "s3", "s4", "s5", "s6"],
            "sequence_type": "ordered",
            "layout_mode": "vertical_list",
            "interaction_pattern": "drag_reorder",
            "card_type": "illustrated",
            "connector_style": "arrow",
            "show_position_numbers": False,
            "allow_partial_credit": True,
        },
        "sorting_categories": {
            "categories": [
                {"id": "cat1", "label": "Arrhythmia", "color": "#4A90D9", "description": "Irregular heartbeat"},
                {"id": "cat2", "label": "Heart Failure", "color": "#E74C3C", "description": "Heart can't pump enough"},
                {"id": "cat3", "label": "Coronary Artery Disease", "color": "#F5A623", "description": "Blocked arteries"},
            ],
            "items": [
                {"id": "i1", "content": "Rapid heartbeat", "correctCategoryId": "cat1", "explanation": "Tachycardia"},
                {"id": "i2", "content": "Chest pain during exertion", "correctCategoryId": "cat3", "explanation": "Angina"},
                {"id": "i3", "content": "Swollen ankles", "correctCategoryId": "cat2", "explanation": "Fluid retention"},
                {"id": "i4", "content": "Palpitations", "correctCategoryId": "cat1", "explanation": "Irregular rhythm"},
                {"id": "i5", "content": "Shortness of breath", "correctCategoryId": "cat2", "explanation": "Poor pumping"},
                {"id": "i6", "content": "Fatigue during activity", "correctCategoryId": "cat3", "explanation": "Poor blood flow"},
                {"id": "i7", "content": "Dizziness", "correctCategoryId": "cat1", "explanation": "Low blood flow from rhythm issue"},
                {"id": "i8", "content": "Crushing chest pressure", "correctCategoryId": "cat3", "explanation": "Heart attack sign"},
            ],
            "sort_mode": "bucket",
            "item_card_type": "text_with_icon",
            "container_style": "bucket",
            "submit_mode": "immediate_feedback",
            "allow_multi_category": False,
            "show_category_hints": False,
            "allow_partial_credit": True,
        },
        "memory_match": {
            "pairs": [
                {"id": "p1", "front": "Arrhythmia", "back": "Beta Blockers",
                 "frontType": "text", "backType": "text", "explanation": "Controls heart rhythm", "category": ""},
                {"id": "p2", "front": "Heart Failure", "back": "ACE Inhibitors",
                 "frontType": "text", "backType": "text", "explanation": "Reduces strain on heart", "category": ""},
                {"id": "p3", "front": "Coronary Artery Disease", "back": "Stent Placement",
                 "frontType": "text", "backType": "text", "explanation": "Opens blocked arteries", "category": ""},
                {"id": "p4", "front": "Hypertension", "back": "Diuretics",
                 "frontType": "text", "backType": "text", "explanation": "Reduces blood volume", "category": ""},
                {"id": "p5", "front": "Valve Disease", "back": "Valve Replacement",
                 "frontType": "text", "backType": "text", "explanation": "Repairs damaged valves", "category": ""},
            ],
            "game_variant": "classic",
            "gridSize": [2, 5],
            "match_type": "condition_to_treatment",
            "card_back_style": "question_mark",
            "matched_card_behavior": "fade",
            "show_explanation_on_match": True,
            "flip_duration_ms": 400,
            "show_attempts_counter": True,
        },
        "branching_scenario": {
            "nodes": [
                {
                    "id": "n1", "question": "A 55-year-old patient presents with chest pain. What's your first step?",
                    "description": "", "node_type": "decision",
                    "options": [
                        {"id": "o1", "text": "Take ECG", "nextNodeId": "n2", "isCorrect": True,
                         "consequence": "Good - ECG is standard first step", "points": 20},
                        {"id": "o2", "text": "Prescribe pain medication", "nextNodeId": "n3", "isCorrect": False,
                         "consequence": "Risky - need to diagnose first", "points": 0},
                    ],
                    "isEndNode": False,
                },
                {
                    "id": "n2", "question": "ECG shows ST elevation. What do you suspect?",
                    "description": "", "node_type": "decision",
                    "options": [
                        {"id": "o3", "text": "Myocardial infarction", "nextNodeId": "n4", "isCorrect": True,
                         "consequence": "Correct - STEMI identified", "points": 20},
                        {"id": "o4", "text": "Anxiety", "nextNodeId": "n5", "isCorrect": False,
                         "consequence": "Missing critical signs", "points": 0},
                    ],
                    "isEndNode": False,
                },
                {
                    "id": "n3", "question": "Patient's condition worsens",
                    "isEndNode": True, "endMessage": "The patient needed immediate ECG. Masking pain was dangerous.",
                    "ending_type": "suboptimal", "options": [], "narrative_text": "",
                },
                {
                    "id": "n4", "question": "You've correctly identified a STEMI!",
                    "isEndNode": True, "endMessage": "Excellent! Quick ECG and correct diagnosis saved the patient.",
                    "ending_type": "optimal", "options": [], "narrative_text": "",
                },
                {
                    "id": "n5", "question": "The ST elevation was missed.",
                    "isEndNode": True, "endMessage": "ST elevation on ECG is a critical sign of heart attack.",
                    "ending_type": "suboptimal", "options": [], "narrative_text": "",
                },
            ],
            "startNodeId": "n1",
            "narrative_structure": "branching",
            "show_path_taken": True,
            "allow_backtrack": False,
            "show_consequences": True,
            "multiple_valid_endings": False,
        },
        "description_matching": {
            "descriptions": {
                "Left Atrium": "Upper left chamber that receives oxygenated blood from the pulmonary veins",
                "Right Atrium": "Upper right chamber that receives deoxygenated blood from the vena cava",
                "Left Ventricle": "Lower left chamber with the thickest walls, pumps blood to the body via the aorta",
                "Right Ventricle": "Lower right chamber that pumps deoxygenated blood to the lungs via the pulmonary artery",
            },
            "mode": "click_zone",
            "distractor_descriptions": ["A small organ that filters blood and removes old red blood cells"],
            "show_connecting_lines": True,
            "defer_evaluation": False,
            "description_panel_position": "right",
        },
    }

    errors = []
    for mtype, output in test_outputs.items():
        try:
            model = get_content_model(mtype)
            parsed = model(**output)
            content_dict = parsed.model_dump()

            # Verify key content fields survived
            if mtype == "drag_drop":
                assert len(content_dict["labels"]) == 4
                assert content_dict["leader_line_style"] == "curved"
                assert content_dict["tray_position"] == "bottom"
            elif mtype == "sequencing":
                assert len(content_dict["items"]) == 6
                assert content_dict["card_type"] == "illustrated"
                assert content_dict["connector_style"] == "arrow"
            elif mtype == "sorting_categories":
                assert len(content_dict["categories"]) == 3
                assert len(content_dict["items"]) == 8
                assert content_dict["sort_mode"] == "bucket"
            elif mtype == "memory_match":
                assert len(content_dict["pairs"]) == 5
                assert content_dict["match_type"] == "condition_to_treatment"
                assert content_dict["gridSize"] == [2, 5]
            elif mtype == "branching_scenario":
                assert len(content_dict["nodes"]) == 5
                assert content_dict["startNodeId"] == "n1"
                assert content_dict["show_consequences"] is True
            elif mtype == "click_to_identify":
                assert len(content_dict["prompts"]) == 2
                assert content_dict["prompt_style"] == "functional"
            elif mtype == "trace_path":
                assert len(content_dict["paths"]) == 1
                assert content_dict["particleSpeed"] == "medium"
            elif mtype == "description_matching":
                assert len(content_dict["descriptions"]) == 4
                assert content_dict["description_panel_position"] == "right"

        except Exception as e:
            errors.append(f"{mtype}: {e}")

    if errors:
        for e in errors:
            print(f"  ✗ {e}")
        raise AssertionError(f"{len(errors)} content model(s) failed")

    print(f"  ✓ Content schemas: all 8 mechanic models parsed successfully")
    return test_outputs


# === Stage 6: Blueprint assembly ===

def test_stage_6(plan, content_outputs):
    """Verify blueprint assembler produces complete output with all config fields."""
    from app.v4.helpers.blueprint_assembler import assemble_blueprint

    plan_dict = plan.model_dump()

    # Build mechanic_contents list (simulating what content_merge would produce)
    mechanic_contents = []
    mechanic_type_order = {
        "scene_1": ["drag_drop", "click_to_identify", "description_matching"],
        "scene_2": ["trace_path", "sequencing"],
        "scene_3": ["sorting_categories", "memory_match", "branching_scenario"],
    }

    for scene in plan_dict.get("scenes", []):
        sid = scene["scene_id"]
        for mech in scene.get("mechanics", []):
            mid = mech["mechanic_id"]
            mtype = mech["mechanic_type"]
            content = content_outputs.get(mtype, {})
            mechanic_contents.append({
                "mechanic_id": mid,
                "scene_id": sid,
                "mechanic_type": mtype,
                "status": "success",
                "content": content,
            })

    # Build interaction_results (simulating what interaction_merge would produce)
    interaction_results = []
    for scene in plan_dict.get("scenes", []):
        sid = scene["scene_id"]
        scoring = {}
        feedback = {}
        for mech in scene.get("mechanics", []):
            mid = mech["mechanic_id"]
            scoring[mid] = {
                "strategy": "per_correct",
                "points_per_correct": mech.get("points_per_item", 10),
                "max_score": mech.get("max_score", 0),
                "partial_credit": True,
            }
            feedback[mid] = {
                "on_correct": "Well done!",
                "on_incorrect": "Not quite, try again.",
                "on_completion": "Section complete!",
                "misconceptions": [],
            }
        interaction_results.append({
            "scene_id": sid,
            "mechanic_scoring": scoring,
            "mechanic_feedback": feedback,
        })

    # Build asset_results (simulating what asset_merge would produce)
    asset_results = [
        {
            "scene_id": "scene_1",
            "status": "success",
            "diagram_url": "https://example.com/heart_chambers.png",
            "zones": [
                {"id": "z1_la", "label": "Left Atrium", "points": [[100, 100], [200, 100], [200, 200], [100, 200]]},
                {"id": "z1_ra", "label": "Right Atrium", "points": [[300, 100], [400, 100], [400, 200], [300, 200]]},
                {"id": "z1_lv", "label": "Left Ventricle", "points": [[100, 250], [200, 250], [200, 350], [100, 350]]},
                {"id": "z1_rv", "label": "Right Ventricle", "points": [[300, 250], [400, 250], [400, 350], [300, 350]]},
            ],
            "match_quality": 1.0,
        },
        {
            "scene_id": "scene_2",
            "status": "success",
            "diagram_url": "https://example.com/blood_flow.png",
            "zones": [
                {"id": "z2_vc", "label": "Vena Cava", "points": [[50, 100], [100, 100], [100, 150], [50, 150]]},
                {"id": "z2_ra", "label": "Right Atrium", "points": [[150, 100], [200, 100], [200, 150], [150, 150]]},
                {"id": "z2_rv", "label": "Right Ventricle", "points": [[250, 200], [300, 200], [300, 250], [250, 250]]},
                {"id": "z2_pa", "label": "Pulmonary Artery", "points": [[350, 100], [400, 100], [400, 150], [350, 150]]},
                {"id": "z2_pv", "label": "Pulmonary Vein", "points": [[350, 250], [400, 250], [400, 300], [350, 300]]},
                {"id": "z2_la", "label": "Left Atrium", "points": [[250, 300], [300, 300], [300, 350], [250, 350]]},
                {"id": "z2_lv", "label": "Left Ventricle", "points": [[150, 300], [200, 300], [200, 350], [150, 350]]},
                {"id": "z2_ao", "label": "Aorta", "points": [[50, 300], [100, 300], [100, 350], [50, 350]]},
            ],
            "match_quality": 1.0,
        },
        # Scene 3 has no diagram (content-only)
    ]

    # Assemble!
    blueprint = assemble_blueprint(plan_dict, mechanic_contents, interaction_results, asset_results)

    # === Validate blueprint structure ===
    errors = []

    # Root structure
    assert blueprint["templateType"] == "INTERACTIVE_DIAGRAM"
    assert blueprint["title"] == "Journey Through the Heart"
    assert blueprint["generation_complete"] is True
    assert blueprint["totalMaxScore"] == plan.total_max_score

    # First scene diagram (promoted to root)
    diag = blueprint["diagram"]
    assert diag["assetUrl"] == "https://example.com/heart_chambers.png"
    assert len(diag["zones"]) == 4

    # Labels (from first scene)
    assert len(blueprint["labels"]) == 4

    # Mechanics array should have ALL 8 mechanics
    assert len(blueprint["mechanics"]) == 8, f"Expected 8 mechanics, got {len(blueprint['mechanics'])}"

    # Mode transitions should connect sequential mechanics within each scene
    assert len(blueprint["modeTransitions"]) >= 2  # At least some transitions

    # === Verify per-mechanic config keys ===
    configs_present = set()
    for key in ["dragDropConfig", "clickToIdentifyConfig", "tracePathConfig",
                "sequenceConfig", "sortingConfig", "memoryMatchConfig",
                "branchingConfig", "descriptionMatchingConfig"]:
        if key in blueprint:
            configs_present.add(key)

    # First scene configs promoted to root
    assert "dragDropConfig" in blueprint, "Missing dragDropConfig at root"

    # Verify dragDropConfig has visual config fields (not data fields!)
    dd_config = blueprint["dragDropConfig"]
    assert "leader_line_style" in dd_config, "dragDropConfig missing leader_line_style"
    assert "tray_position" in dd_config, "dragDropConfig missing tray_position"
    assert "labels" not in dd_config, "dragDropConfig should NOT have 'labels' (data leakage!)"
    assert "distractor_labels" not in dd_config, "dragDropConfig should NOT have 'distractor_labels' (data leakage!)"

    # Verify identificationPrompts at ROOT (not inside config)
    assert "identificationPrompts" in blueprint, "Missing identificationPrompts at root"
    prompts = blueprint["identificationPrompts"]
    assert len(prompts) == 2
    assert all("targetZoneId" in p for p in prompts), "identificationPrompts missing targetZoneId"
    assert all("targetLabelId" in p for p in prompts), "identificationPrompts missing targetLabelId"

    # Multi-scene
    assert blueprint.get("is_multi_scene") is True, "Should be multi-scene"
    gs = blueprint.get("game_sequence", {})
    assert len(gs.get("scenes", [])) == 3

    # Verify scene 2 has paths at game_sequence level
    scene2_gs = gs["scenes"][1]
    assert "paths" in scene2_gs, "Scene 2 should have paths"
    paths = scene2_gs["paths"]
    assert len(paths) == 1
    assert len(paths[0]["waypoints"]) == 4
    # Waypoints should have zoneId resolved
    for wp in paths[0]["waypoints"]:
        assert "zoneId" in wp, f"Waypoint missing zoneId: {wp}"

    # Verify scene 2 has sequenceConfig
    assert "sequenceConfig" in scene2_gs, "Scene 2 should have sequenceConfig"
    seq_config = scene2_gs["sequenceConfig"]
    assert len(seq_config["items"]) == 6
    assert seq_config["card_type"] == "illustrated"

    # Verify scene 3 configs
    scene3_gs = gs["scenes"][2]
    assert "sortingConfig" in scene3_gs, "Scene 3 should have sortingConfig"
    assert "memoryMatchConfig" in scene3_gs, "Scene 3 should have memoryMatchConfig"
    assert "branchingConfig" in scene3_gs, "Scene 3 should have branchingConfig"

    # Verify sorting config has visual fields
    sort_config = scene3_gs["sortingConfig"]
    assert sort_config["sort_mode"] == "bucket"
    assert len(sort_config["categories"]) == 3
    assert len(sort_config["items"]) == 8

    # Verify memory match config
    mm_config = scene3_gs["memoryMatchConfig"]
    assert mm_config["match_type"] == "condition_to_treatment"
    assert len(mm_config["pairs"]) == 5
    assert mm_config["gridSize"] == [2, 5]

    # Verify branching config
    br_config = scene3_gs["branchingConfig"]
    assert len(br_config["nodes"]) == 5
    assert br_config["startNodeId"] == "n1"
    assert br_config["show_consequences"] is True

    # Verify scene 3 has no diagram (content-only)
    scene3_diag = scene3_gs.get("diagram", {})
    assert scene3_diag.get("assetUrl") is None, "Scene 3 should have no diagram"

    # Verify scoring in mechanics array
    for mech in blueprint["mechanics"]:
        assert "scoring" in mech, f"Mechanic missing scoring: {mech['type']}"
        assert "feedback" in mech, f"Mechanic missing feedback: {mech['type']}"
        assert mech["scoring"]["max_score"] > 0, f"Mechanic has zero max_score: {mech['type']}"

    # Verify narrative
    assert len(blueprint["narrativeIntro"]) > 0, "Missing narrative intro"

    print(f"  ✓ Blueprint assembly: all 8 mechanics assembled correctly")
    print(f"    Template: {blueprint['templateType']}")
    print(f"    Score: {blueprint['totalMaxScore']}")
    print(f"    Scenes: {len(gs.get('scenes', []))}")
    print(f"    Mechanics: {len(blueprint['mechanics'])}")
    print(f"    Transitions: {len(blueprint['modeTransitions'])}")
    print(f"    Config keys present: {configs_present}")
    print(f"    identificationPrompts: {len(blueprint.get('identificationPrompts', []))} prompts")

    return blueprint


# === Stage 7: Validator ===

def test_stage_7(plan):
    """Run the game plan validator."""
    from app.v4.validators.game_plan_validator import validate_game_plan

    result = validate_game_plan(plan)

    if not result.passed:
        error_issues = [i for i in result.issues if i.severity == "error"]
        if error_issues:
            print(f"  ✗ Validation FAILED with {len(error_issues)} errors:")
            for issue in error_issues:
                print(f"    ERROR: {issue.message}")
            raise AssertionError(f"Game plan validation failed: {len(error_issues)} errors")

    warnings = [i for i in result.issues if i.severity == "warning"]
    print(f"  ✓ Game plan validation: PASSED (score={result.score}, warnings={len(warnings)})")
    for w in warnings:
        print(f"    WARN: {w.message}")

    # Verify scores were computed
    assert plan.total_max_score > 0, "total_max_score not computed"
    for scene in plan.scenes:
        assert scene.scene_max_score > 0, f"{scene.scene_id}: scene_max_score not computed"
        for mech in scene.mechanics:
            assert mech.max_score > 0, f"{mech.mechanic_id}: max_score not computed"

    print(f"    total_max_score={plan.total_max_score}")


# === Main ===

def main():
    print("\n" + "=" * 70)
    print("V4 Creative Cascade — End-to-End Integration Test")
    print("=" * 70)

    try:
        print("\n── Stage 1: GameConcept (WHAT/WHY) ──")
        concept = test_stage_1()

        print("\n── Stage 2: SceneCreativeDesign (HOW) ──")
        designs = test_stage_2(concept)

        print("\n── Stage 3: GraphBuilder → GamePlan ──")
        plan = test_stage_3(concept, designs)

        print("\n── Stage 7: Game Plan Validation ──")
        test_stage_7(plan)

        print("\n── Stage 4: Content Prompt Generation ──")
        test_stage_4(plan)

        print("\n── Stage 5: Content Schema Parsing ──")
        content_outputs = test_stage_5()

        print("\n── Stage 6: Blueprint Assembly ──")
        blueprint = test_stage_6(plan, content_outputs)

        print("\n" + "=" * 70)
        print("ALL STAGES PASSED — Creative cascade flows end-to-end")
        print(f"  8 mechanics × 3 scenes × 6 stages = complete coverage")
        print("=" * 70)

    except Exception as e:
        print(f"\n{'='*70}")
        print(f"FAILED: {e}")
        traceback.print_exc()
        print(f"{'='*70}")
        sys.exit(1)


if __name__ == "__main__":
    main()
