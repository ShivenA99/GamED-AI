import type { InteractiveDiagramBlueprint } from '../types';

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export const descriptionMatchingDemo = {
  "templateType": "INTERACTIVE_DIAGRAM",
  "title": "Flower Power: Anatomy & Function",
  "subject": "Biology",
  "difficulty": "beginner",
  "narrativeIntro": "Embark on a botanical journey to uncover the secrets of flower anatomy and their vital roles in plant reproduction. First, identify the key structures, then delve into their specific functions.",
  "narrativeTheme": "Botanical Exploration",
  "completionMessage": "Congratulations, botanist! You've mastered the intricate world of flower parts and their essential functions in plant reproduction.",
  "estimatedDurationMinutes": 8,
  "diagram": {
    "assetPrompt": "Labeled diagram of a flower",
    "zones": [
      {
        "id": "zone_petal",
        "label": "petal",
        "points": [
          [
            77.9,
            50.8
          ],
          [
            76.3,
            46.4
          ],
          [
            73.4,
            43.4
          ],
          [
            71.7,
            39.1
          ],
          [
            70.3,
            38.1
          ],
          [
            67.5,
            40.4
          ],
          [
            59.1,
            50.3
          ],
          [
            54.3,
            55.1
          ],
          [
            54.0,
            56.8
          ],
          [
            60.4,
            56.0
          ],
          [
            71.7,
            56.0
          ],
          [
            75.8,
            54.1
          ]
        ],
        "x": 67.7,
        "y": 48.9,
        "radius": 15.8,
        "shape": "polygon",
        "center": {
          "x": 67.7,
          "y": 48.9
        },
        "description": "These often brightly colored or scented structures primarily attract pollinators, like insects or birds, to facilitate pollen transfer for reproduction."
      },
      {
        "id": "zone_sepal",
        "label": "sepal",
        "points": [
          [
            70.7,
            58.4
          ],
          [
            68.8,
            57.8
          ],
          [
            63.9,
            57.2
          ],
          [
            63.3,
            56.8
          ],
          [
            63.3,
            56.4
          ],
          [
            61.1,
            56.8
          ],
          [
            57.8,
            56.6
          ],
          [
            53.5,
            58.7
          ],
          [
            52.8,
            59.5
          ],
          [
            52.4,
            61.2
          ],
          [
            53.3,
            61.5
          ],
          [
            54.2,
            61.0
          ],
          [
            56.7,
            64.8
          ],
          [
            58.0,
            65.7
          ],
          [
            59.4,
            65.9
          ],
          [
            60.8,
            64.7
          ],
          [
            65.5,
            63.1
          ],
          [
            67.0,
            61.3
          ],
          [
            68.9,
            60.2
          ]
        ],
        "x": 60.6,
        "y": 60.4,
        "radius": 10.3,
        "shape": "polygon",
        "center": {
          "x": 60.6,
          "y": 60.4
        },
        "description": "Typically green and leaf-like, these structures enclose and protect the developing flower bud before it opens, safeguarding the inner floral parts."
      },
      {
        "id": "zone_anther",
        "label": "anther",
        "points": [
          [
            54.5,
            36.8
          ],
          [
            56.5,
            36.8
          ],
          [
            56.5,
            41.2
          ],
          [
            54.5,
            41.2
          ]
        ],
        "x": 55.5,
        "y": 39.0,
        "width": 2.1,
        "height": 4.4,
        "shape": "rect",
        "description": "This part of the stamen is responsible for producing and containing the pollen grains, which are essential for plant fertilization."
      },
      {
        "id": "zone_stigma",
        "label": "stigma",
        "points": [
          [
            48.8,
            33.9
          ],
          [
            50.7,
            33.9
          ],
          [
            50.7,
            39.1
          ],
          [
            48.8,
            39.1
          ]
        ],
        "x": 49.7,
        "y": 36.5,
        "width": 1.9,
        "height": 5.3,
        "shape": "rect",
        "description": "The receptive, often sticky, tip of the pistil designed to capture and hold pollen grains during the process of pollination."
      },
      {
        "id": "zone_style",
        "label": "style",
        "points": [
          [
            48.3,
            39.1
          ],
          [
            51.2,
            39.1
          ],
          [
            51.2,
            50.5
          ],
          [
            48.3,
            50.5
          ]
        ],
        "x": 49.8,
        "y": 44.8,
        "width": 2.9,
        "height": 11.4,
        "shape": "rect",
        "description": "A stalk-like structure connecting the stigma to the ovary, providing a pathway for pollen tubes to grow and reach the ovules for fertilization."
      },
      {
        "id": "zone_ovary",
        "label": "ovary",
        "points": [
          [
            49.4,
            50.0
          ],
          [
            48.4,
            50.8
          ],
          [
            47.3,
            52.7
          ],
          [
            46.7,
            54.9
          ],
          [
            46.6,
            58.7
          ],
          [
            46.0,
            59.4
          ],
          [
            45.6,
            62.3
          ],
          [
            47.6,
            69.9
          ],
          [
            49.2,
            73.0
          ],
          [
            50.2,
            73.3
          ],
          [
            51.4,
            71.3
          ],
          [
            52.5,
            68.2
          ],
          [
            53.5,
            62.8
          ],
          [
            53.4,
            61.7
          ],
          [
            52.4,
            60.6
          ],
          [
            52.9,
            57.3
          ],
          [
            52.2,
            52.8
          ],
          [
            51.5,
            51.3
          ],
          [
            50.8,
            51.4
          ]
        ],
        "x": 49.9,
        "y": 60.1,
        "radius": 13.2,
        "shape": "polygon",
        "center": {
          "x": 49.9,
          "y": 60.1
        },
        "description": "Located at the base of the pistil, this structure contains the ovules and develops into the fruit after successful fertilization."
      }
    ],
    "imageUrl": "/api/assets/demo/390db3d9-d8be-430b-b340-54623661295b/diagram_scene_1.png",
    "assetUrl": "/api/assets/demo/390db3d9-d8be-430b-b340-54623661295b/diagram_scene_1.png"
  },
  "labels": [
    {
      "id": "label_s1_0",
      "text": "petal",
      "correctZoneId": "zone_petal"
    },
    {
      "id": "label_s1_1",
      "text": "sepal",
      "correctZoneId": "zone_sepal"
    },
    {
      "id": "label_s1_2",
      "text": "anther",
      "correctZoneId": "zone_anther"
    },
    {
      "id": "label_s1_3",
      "text": "stigma",
      "correctZoneId": "zone_stigma"
    },
    {
      "id": "label_s1_4",
      "text": "style",
      "correctZoneId": "zone_style"
    },
    {
      "id": "label_s1_5",
      "text": "ovary",
      "correctZoneId": "zone_ovary"
    }
  ],
  "distractorLabels": [],
  "mechanics": [
    {
      "type": "drag_drop",
      "config": {
        "instruction_text": "Welcome, botanist! Drag and drop the labels to correctly identify the major parts of this flower. Pay close attention to their positions!"
      },
      "scoring": {
        "strategy": "per_correct",
        "points_per_correct": 10,
        "max_score": 60,
        "partial_credit": true
      },
      "feedback": {
        "on_correct": "Excellent! That's the correct placement for this flower part.",
        "on_incorrect": "Not quite. Take another look at the flower part's structure and its typical location, then try again.",
        "on_completion": "Fantastic! You've successfully identified and placed all the major flower parts.",
        "misconceptions": [
          {
            "trigger_label": "sepal_petal_confusion",
            "message": "Remember, while sepals are often green and protective, in some flowers (like lilies), they can be colorful and petal-like, collectively called tepals. Petals are primarily for attracting pollinators."
          },
          {
            "trigger_label": "anther_stigma_confusion",
            "message": "Careful! The anther is the male part that produces pollen, while the stigma is the receptive female part that receives pollen."
          }
        ]
      }
    },
    {
      "type": "description_matching",
      "config": {
        "instruction_text": "Excellent work identifying the flower's parts! Now, match each labeled part to its specific function in plant reproduction. Think about what each structure *does*."
      },
      "scoring": {
        "strategy": "per_correct",
        "points_per_correct": 15,
        "max_score": 90,
        "partial_credit": true
      },
      "feedback": {
        "on_correct": "That's a perfect match! You've correctly identified its function in plant reproduction.",
        "on_incorrect": "This description doesn't quite fit. Re-evaluate the specific function of this part and its role in the reproductive process.",
        "on_completion": "Outstanding! You've accurately described the specific functions of each flower part.",
        "misconceptions": [
          {
            "trigger_label": "ovary_fruit_confusion",
            "message": "Important distinction: The ovary *contains* the ovules and *develops* into the fruit *after* fertilization, protecting the developing seeds."
          }
        ]
      }
    }
  ],
  "modeTransitions": [
    {
      "from": "drag_drop",
      "to": "description_matching",
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
    "max_score": 150
  },
  "totalMaxScore": 150,
  "generation_complete": true,
  "dragDropConfig": {
    "leader_line_style": "elbow",
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
    "feedback_timing": "immediate",
    "pin_marker_shape": "circle"
  },
  "descriptionMatchingConfig": {
    "descriptions": {
      "zone_petal": "These often brightly colored or scented structures primarily attract pollinators, like insects or birds, to facilitate pollen transfer for reproduction.",
      "zone_sepal": "Typically green and leaf-like, these structures enclose and protect the developing flower bud before it opens, safeguarding the inner floral parts.",
      "zone_anther": "This part of the stamen is responsible for producing and containing the pollen grains, which are essential for plant fertilization.",
      "zone_stigma": "The receptive, often sticky, tip of the pistil designed to capture and hold pollen grains during the process of pollination.",
      "zone_style": "A stalk-like structure connecting the stigma to the ovary, providing a pathway for pollen tubes to grow and reach the ovules for fertilization.",
      "zone_ovary": "Located at the base of the pistil, this structure contains the ovules and develops into the fruit after successful fertilization."
    },
    "mode": "click_zone",
    "show_connecting_lines": true,
    "defer_evaluation": false,
    "description_panel_position": "right"
  },
  "tasks": []
} as any as InteractiveDiagramBlueprint;
