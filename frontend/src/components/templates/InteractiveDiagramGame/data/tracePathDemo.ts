import type { InteractiveDiagramBlueprint } from '../types';

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export const tracePathDemo = {
  "templateType": "INTERACTIVE_DIAGRAM",
  "title": "Digestive Journey: Food's Path",
  "subject": "Biology",
  "difficulty": "beginner",
  "narrativeIntro": "Welcome, aspiring biologist! Today, we'll embark on an incredible journey through the human body. Your mission: to map the path of food as it travels through the digestive system, from the moment it enters the mouth until it reaches the large intestine.",
  "narrativeTheme": "Inner Exploration",
  "completionMessage": "Excellent work! You've successfully navigated the intricate pathways of the digestive system, demonstrating a clear understanding of how food travels through our bodies.",
  "estimatedDurationMinutes": 7,
  "diagram": {
    "assetPrompt": "Diagram of the human digestive system",
    "zones": [
      {
        "id": "zone_mouth",
        "label": "Mouth",
        "points": [
          [
            39.6,
            19.6
          ],
          [
            46.1,
            19.6
          ],
          [
            46.1,
            24.8
          ],
          [
            39.6,
            24.8
          ]
        ],
        "x": 42.9,
        "y": 22.2,
        "width": 6.5,
        "height": 5.1,
        "shape": "rect"
      },
      {
        "id": "zone_esophagus",
        "label": "Esophagus",
        "points": [
          [
            71.5,
            24.0
          ],
          [
            73.5,
            24.0
          ],
          [
            73.5,
            39.2
          ],
          [
            71.5,
            39.2
          ]
        ],
        "x": 72.5,
        "y": 31.6,
        "width": 2.1,
        "height": 15.3,
        "shape": "rect"
      },
      {
        "id": "zone_stomach",
        "label": "Stomach",
        "points": [
          [
            69.3,
            47.2
          ],
          [
            75.9,
            47.2
          ],
          [
            75.9,
            53.2
          ],
          [
            69.3,
            53.2
          ]
        ],
        "x": 72.6,
        "y": 50.2,
        "width": 6.6,
        "height": 5.9,
        "shape": "rect"
      },
      {
        "id": "zone_small_intestine",
        "label": "Small Intestine",
        "x": 86.3,
        "y": 71.5,
        "radius": 3,
        "shape": "circle",
        "center": {
          "x": 86.25999999999999,
          "y": 71.45
        }
      },
      {
        "id": "zone_large_intestine",
        "label": "Large Intestine",
        "points": [
          [
            82.2,
            52.7
          ],
          [
            80.6,
            52.4
          ],
          [
            75.2,
            57.1
          ],
          [
            71.2,
            57.2
          ],
          [
            66.8,
            55.0
          ],
          [
            67.0,
            63.1
          ],
          [
            68.9,
            72.0
          ],
          [
            68.0,
            75.8
          ],
          [
            66.0,
            76.4
          ],
          [
            66.9,
            80.7
          ],
          [
            64.7,
            80.6
          ],
          [
            65.1,
            81.6
          ],
          [
            66.9,
            81.9
          ],
          [
            65.6,
            82.4
          ],
          [
            67.0,
            84.8
          ],
          [
            68.8,
            85.3
          ],
          [
            70.3,
            83.9
          ],
          [
            72.0,
            90.5
          ],
          [
            73.1,
            90.2
          ],
          [
            74.1,
            84.3
          ],
          [
            76.4,
            85.5
          ],
          [
            78.4,
            84.1
          ],
          [
            80.6,
            79.5
          ],
          [
            81.8,
            80.0
          ],
          [
            84.1,
            74.0
          ],
          [
            84.3,
            69.9
          ],
          [
            82.6,
            64.6
          ],
          [
            83.1,
            54.5
          ]
        ],
        "x": 73.3,
        "y": 74.3,
        "radius": 23.4,
        "shape": "polygon",
        "center": {
          "x": 73.3,
          "y": 74.3
        }
      }
    ],
    "imageUrl": "/api/assets/demo/f4e798a7-bc7d-4611-b77e-62c9bd4bb392/diagram_scene_1.png",
    "assetUrl": "/api/assets/demo/f4e798a7-bc7d-4611-b77e-62c9bd4bb392/diagram_scene_1.png"
  },
  "labels": [
    {
      "id": "label_s1_0",
      "text": "Mouth",
      "correctZoneId": "zone_mouth"
    },
    {
      "id": "label_s1_1",
      "text": "Esophagus",
      "correctZoneId": "zone_esophagus"
    },
    {
      "id": "label_s1_2",
      "text": "Stomach",
      "correctZoneId": "zone_stomach"
    },
    {
      "id": "label_s1_3",
      "text": "Small Intestine",
      "correctZoneId": "zone_small_intestine"
    },
    {
      "id": "label_s1_4",
      "text": "Large Intestine",
      "correctZoneId": "zone_large_intestine"
    }
  ],
  "distractorLabels": [],
  "mechanics": [
    {
      "type": "drag_drop",
      "config": {
        "instruction_text": "First, let's identify the key organs that form the continuous tube through which food passes. Drag and drop the labels to their correct locations on the diagram."
      },
      "scoring": {
        "strategy": "per_correct",
        "points_per_correct": 10,
        "max_score": 50,
        "partial_credit": true
      },
      "feedback": {
        "on_correct": "Excellent! That's the correct location for this organ.",
        "on_incorrect": "Not quite. Remember, food travels through these organs in a specific sequence. Try placing this label in a different area.",
        "on_completion": "Fantastic! You've successfully identified all the major organs of the alimentary canal!",
        "misconceptions": [
          {
            "trigger_label": "incorrect_placement_accessory_organ_area",
            "message": "While organs like the liver, pancreas, and gallbladder produce substances vital for digestion (e.g., bile, enzymes), food does not physically enter them; it remains within the alimentary canal."
          },
          {
            "trigger_label": "swapped_small_large_intestine_placement",
            "message": "It's a common misconception! The small intestine is actually significantly longer (about 6 meters) than the large intestine (about 1.5 meters), but it is narrower in diameter."
          },
          {
            "trigger_label": "incorrect_placement_stomach_large_intestine_absorption",
            "message": "Remember, the majority of chemical digestion and nutrient absorption takes place in the small intestine. The stomach primarily churns food, and the large intestine mainly absorbs water."
          }
        ]
      }
    },
    {
      "type": "trace_path",
      "config": {
        "instruction_text": "Excellent! Now that you've identified the major organs of the alimentary canal, trace the sequential path that food takes as it travels through these structures, starting from the Mouth."
      },
      "scoring": {
        "strategy": "per_correct",
        "points_per_correct": 15,
        "max_score": 75,
        "partial_credit": true
      },
      "feedback": {
        "on_correct": "That's the correct next step in the digestive path!",
        "on_incorrect": "Not quite. Think about the sequential flow of food. Which organ comes next after this one?",
        "on_completion": "Outstanding! You've successfully traced the entire path of food through the alimentary canal!",
        "misconceptions": [
          {
            "trigger_label": "traced_through_accessory_organ",
            "message": "While organs like the liver, pancreas, and gallbladder produce substances vital for digestion (e.g., bile, enzymes), food does not physically enter them; it remains within the alimentary canal."
          },
          {
            "trigger_label": "skipped_small_intestine_or_reversed_order",
            "message": "It's a common misconception! The small intestine is actually significantly longer (about 6 meters) than the large intestine (about 1.5 meters), but it is narrower in diameter."
          },
          {
            "trigger_label": "path_skips_small_intestine_for_absorption",
            "message": "Remember, the majority of chemical digestion and nutrient absorption takes place in the small intestine. The stomach primarily churns food, and the large intestine mainly absorbs water."
          }
        ]
      }
    }
  ],
  "modeTransitions": [
    {
      "from": "drag_drop",
      "to": "trace_path",
      "trigger": "all_zones_labeled",
      "animation": "fade"
    }
  ],
  "interactionMode": "drag_drop",
  "animationCues": {
    "correctPlacement": "pulse-green",
    "incorrectPlacement": "shake-red"
  },
  "scoringStrategy": {
    "type": "per_zone",
    "base_points_per_zone": 10,
    "max_score": 125
  },
  "totalMaxScore": 125,
  "generation_complete": true,
  "dragDropConfig": {
    "tray_position": "bottom",
    "placement_animation": "spring",
    "show_distractors": false,
    "zone_idle_animation": "pulse",
    "interaction_mode": "drag_drop",
    "zone_hover_effect": "highlight",
    "leader_line_color": "",
    "max_attempts": 3,
    "label_anchor_side": "auto",
    "label_style": "text",
    "incorrect_animation": "shake",
    "shuffle_labels": true,
    "tray_layout": "horizontal",
    "leader_line_animate": true,
    "feedback_timing": "deferred",
    "pin_marker_shape": "circle"
  },
  "tracePathConfig": {
    "particleSpeed": "medium",
    "particleTheme": "dots"
  },
  "paths": [
    {
      "id": "path_s1_0",
      "label": "Path of Digestion",
      "description": "Trace the path of food as it travels through the alimentary canal, starting from the Mouth.",
      "color": "#1ABC9C",
      "requiresOrder": true,
      "waypoints": [
        {
          "id": "wp_s1_0_0",
          "label": "Mouth",
          "zoneId": "zone_mouth",
          "order": 0
        },
        {
          "id": "wp_s1_0_1",
          "label": "Esophagus",
          "zoneId": "zone_esophagus",
          "order": 1
        },
        {
          "id": "wp_s1_0_2",
          "label": "Stomach",
          "zoneId": "zone_stomach",
          "order": 2
        },
        {
          "id": "wp_s1_0_3",
          "label": "Small Intestine",
          "zoneId": "zone_small_intestine",
          "order": 3
        },
        {
          "id": "wp_s1_0_4",
          "label": "Large Intestine",
          "zoneId": "zone_large_intestine",
          "order": 4
        }
      ]
    }
  ],
  "tasks": []
} as any as InteractiveDiagramBlueprint;
