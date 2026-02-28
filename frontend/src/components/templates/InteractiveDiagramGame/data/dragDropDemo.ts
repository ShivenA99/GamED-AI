import type { InteractiveDiagramBlueprint } from '../types';

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export const dragDropDemo = {
  "templateType": "INTERACTIVE_DIAGRAM",
  "title": "Heart Anatomy Explorer",
  "subject": "Biology",
  "difficulty": "beginner",
  "narrativeIntro": "Welcome, future cardiologists! Your mission is to accurately label the intricate parts of the human heart, a vital organ that powers our entire circulatory system.",
  "narrativeTheme": "Medical Discovery",
  "completionMessage": "Excellent work! You've successfully mapped the human heart, demonstrating a strong understanding of its fundamental anatomy.",
  "estimatedDurationMinutes": 7,
  "diagram": {
    "assetPrompt": "Detailed anatomical diagram of the human heart",
    "zones": [
      {
        "id": "zone_right_atrium",
        "label": "Right Atrium",
        "points": [
          [
            32.3,
            35.1
          ],
          [
            27.2,
            36.0
          ],
          [
            24.2,
            39.4
          ],
          [
            24.9,
            47.2
          ],
          [
            23.0,
            56.3
          ],
          [
            24.0,
            64.7
          ],
          [
            27.2,
            70.8
          ],
          [
            30.4,
            74.0
          ],
          [
            31.3,
            72.0
          ],
          [
            34.3,
            69.5
          ],
          [
            37.8,
            69.0
          ],
          [
            39.4,
            69.7
          ],
          [
            37.8,
            67.0
          ],
          [
            37.8,
            64.2
          ],
          [
            38.9,
            61.7
          ],
          [
            41.0,
            60.1
          ],
          [
            41.2,
            48.7
          ],
          [
            37.1,
            43.3
          ],
          [
            34.6,
            36.4
          ]
        ],
        "x": 32.9,
        "y": 57.1,
        "radius": 22.0,
        "shape": "polygon",
        "center": {
          "x": 32.9,
          "y": 57.1
        }
      },
      {
        "id": "zone_left_atrium",
        "label": "Left Atrium",
        "points": [
          [
            52.5,
            38.7
          ],
          [
            51.4,
            43.1
          ],
          [
            51.4,
            44.6
          ],
          [
            57.4,
            50.8
          ],
          [
            58.8,
            50.1
          ],
          [
            60.8,
            50.1
          ],
          [
            64.1,
            51.0
          ],
          [
            64.3,
            50.6
          ],
          [
            64.7,
            50.8
          ],
          [
            64.7,
            50.1
          ],
          [
            65.7,
            50.6
          ],
          [
            68.7,
            47.8
          ],
          [
            71.0,
            47.2
          ],
          [
            70.3,
            44.6
          ],
          [
            68.2,
            41.0
          ],
          [
            65.9,
            38.3
          ],
          [
            62.9,
            36.4
          ],
          [
            61.5,
            36.0
          ],
          [
            56.7,
            36.2
          ],
          [
            53.5,
            37.4
          ]
        ],
        "x": 61.7,
        "y": 44.8,
        "radius": 11.0,
        "shape": "polygon",
        "center": {
          "x": 61.7,
          "y": 44.8
        }
      },
      {
        "id": "zone_right_ventricle",
        "label": "Right Ventricle",
        "points": [
          [
            31.3,
            72.7
          ],
          [
            31.3,
            74.7
          ],
          [
            34.1,
            77.4
          ],
          [
            45.4,
            82.7
          ],
          [
            59.7,
            86.1
          ],
          [
            65.7,
            86.3
          ],
          [
            67.1,
            85.6
          ],
          [
            66.1,
            82.9
          ],
          [
            58.3,
            73.3
          ],
          [
            54.8,
            64.5
          ],
          [
            52.1,
            61.3
          ],
          [
            49.8,
            63.1
          ],
          [
            46.8,
            63.8
          ],
          [
            40.8,
            61.0
          ],
          [
            40.8,
            63.1
          ],
          [
            38.7,
            67.0
          ],
          [
            40.6,
            69.5
          ],
          [
            35.7,
            69.5
          ]
        ],
        "x": 47.7,
        "y": 72.5,
        "radius": 23.4,
        "shape": "polygon",
        "center": {
          "x": 47.7,
          "y": 72.5
        }
      },
      {
        "id": "zone_left_ventricle",
        "label": "Left Ventricle",
        "points": [
          [
            60.1,
            52.6
          ],
          [
            61.3,
            55.1
          ],
          [
            59.4,
            57.6
          ],
          [
            59.7,
            59.0
          ],
          [
            56.9,
            61.5
          ],
          [
            54.8,
            62.0
          ],
          [
            56.0,
            64.2
          ],
          [
            60.4,
            67.0
          ],
          [
            61.8,
            70.6
          ],
          [
            60.8,
            70.4
          ],
          [
            61.5,
            72.2
          ],
          [
            64.5,
            73.3
          ],
          [
            62.7,
            74.0
          ],
          [
            62.9,
            75.2
          ],
          [
            64.3,
            75.6
          ],
          [
            63.4,
            77.2
          ],
          [
            62.9,
            76.5
          ],
          [
            64.1,
            77.4
          ],
          [
            64.3,
            78.8
          ],
          [
            63.4,
            78.8
          ],
          [
            64.3,
            80.0
          ],
          [
            66.6,
            80.2
          ],
          [
            68.2,
            78.6
          ],
          [
            68.7,
            80.6
          ],
          [
            69.8,
            81.3
          ],
          [
            69.1,
            82.7
          ],
          [
            70.3,
            83.4
          ],
          [
            73.5,
            82.9
          ],
          [
            75.6,
            79.7
          ],
          [
            76.3,
            72.4
          ],
          [
            75.1,
            67.2
          ],
          [
            71.2,
            58.5
          ],
          [
            70.5,
            50.8
          ],
          [
            68.9,
            50.8
          ],
          [
            67.7,
            52.2
          ],
          [
            66.6,
            56.9
          ],
          [
            63.1,
            53.5
          ]
        ],
        "x": 65.2,
        "y": 69.5,
        "radius": 19.4,
        "shape": "polygon",
        "center": {
          "x": 65.2,
          "y": 69.5
        }
      },
      {
        "id": "zone_tricuspid_valve",
        "label": "Tricuspid Valve",
        "x": 78.5,
        "y": 67.1,
        "shape": "circle",
        "radius": 3
      },
      {
        "id": "zone_pulmonary_valve",
        "label": "Pulmonary Valve",
        "points": [
          [
            45.4,
            50.8
          ],
          [
            43.3,
            52.4
          ],
          [
            41.9,
            55.1
          ],
          [
            41.2,
            58.5
          ],
          [
            41.5,
            60.4
          ],
          [
            42.4,
            61.7
          ],
          [
            44.2,
            62.6
          ],
          [
            46.3,
            63.1
          ],
          [
            48.8,
            62.9
          ],
          [
            50.5,
            62.2
          ],
          [
            51.4,
            61.0
          ],
          [
            51.4,
            58.5
          ],
          [
            50.9,
            56.3
          ],
          [
            50.0,
            53.5
          ],
          [
            48.6,
            51.7
          ],
          [
            47.0,
            50.8
          ]
        ],
        "x": 46.5,
        "y": 57.6,
        "radius": 6.9,
        "shape": "polygon",
        "center": {
          "x": 46.5,
          "y": 57.6
        }
      },
      {
        "id": "zone_mitral_valve",
        "label": "Mitral Valve",
        "points": [
          [
            56.5,
            47.4
          ],
          [
            71.5,
            47.4
          ],
          [
            71.5,
            56.6
          ],
          [
            56.5,
            56.6
          ]
        ],
        "x": 64.0,
        "y": 52.0,
        "width": 15.1,
        "height": 9.2,
        "shape": "rect"
      },
      {
        "id": "zone_aortic_valve",
        "label": "Aortic Valve",
        "points": [
          [
            51.8,
            51.0
          ],
          [
            50.9,
            52.2
          ],
          [
            50.9,
            54.4
          ],
          [
            51.2,
            54.7
          ],
          [
            51.2,
            56.0
          ],
          [
            51.6,
            58.1
          ],
          [
            53.9,
            60.6
          ],
          [
            55.1,
            61.5
          ],
          [
            56.0,
            61.7
          ],
          [
            56.9,
            61.3
          ],
          [
            57.6,
            60.6
          ],
          [
            57.8,
            59.9
          ],
          [
            58.3,
            59.7
          ],
          [
            58.3,
            59.0
          ],
          [
            57.8,
            58.5
          ],
          [
            57.8,
            58.1
          ],
          [
            58.1,
            57.9
          ],
          [
            58.3,
            58.1
          ],
          [
            59.7,
            57.2
          ],
          [
            60.8,
            55.4
          ],
          [
            60.8,
            54.2
          ],
          [
            60.1,
            53.3
          ],
          [
            58.5,
            52.6
          ],
          [
            57.1,
            51.3
          ],
          [
            54.8,
            50.6
          ],
          [
            53.5,
            50.6
          ]
        ],
        "x": 56.1,
        "y": 56.5,
        "radius": 7.0,
        "shape": "polygon",
        "center": {
          "x": 56.1,
          "y": 56.5
        }
      },
      {
        "id": "zone_aorta",
        "label": "Aorta",
        "points": [
          [
            59.7,
            5.7
          ],
          [
            57.6,
            5.9
          ],
          [
            53.0,
            13.4
          ],
          [
            53.7,
            5.2
          ],
          [
            51.4,
            4.1
          ],
          [
            48.4,
            4.6
          ],
          [
            47.0,
            14.4
          ],
          [
            44.9,
            13.2
          ],
          [
            41.2,
            6.2
          ],
          [
            38.7,
            6.6
          ],
          [
            36.9,
            8.7
          ],
          [
            39.9,
            15.9
          ],
          [
            35.3,
            26.2
          ],
          [
            35.0,
            36.0
          ],
          [
            36.4,
            41.0
          ],
          [
            41.5,
            48.3
          ],
          [
            44.0,
            30.1
          ],
          [
            45.9,
            25.5
          ],
          [
            49.5,
            23.0
          ],
          [
            55.8,
            23.7
          ],
          [
            62.2,
            22.1
          ],
          [
            59.0,
            14.6
          ],
          [
            62.4,
            8.2
          ]
        ],
        "x": 47.8,
        "y": 17.5,
        "radius": 31.4,
        "shape": "polygon",
        "center": {
          "x": 47.8,
          "y": 17.5
        }
      },
      {
        "id": "zone_pulmonary_artery",
        "label": "Pulmonary Artery",
        "points": [
          [
            15.2,
            23.9
          ],
          [
            14.5,
            25.5
          ],
          [
            14.5,
            27.8
          ],
          [
            15.7,
            29.4
          ],
          [
            16.6,
            29.8
          ],
          [
            19.4,
            30.1
          ],
          [
            19.6,
            30.3
          ],
          [
            24.0,
            30.5
          ],
          [
            24.0,
            24.8
          ],
          [
            23.7,
            24.1
          ],
          [
            23.3,
            23.9
          ],
          [
            22.1,
            23.9
          ],
          [
            21.9,
            23.7
          ],
          [
            17.7,
            23.5
          ],
          [
            17.5,
            23.2
          ],
          [
            16.1,
            23.2
          ]
        ],
        "x": 19.1,
        "y": 26.1,
        "radius": 6.6,
        "shape": "polygon",
        "center": {
          "x": 19.1,
          "y": 26.1
        }
      },
      {
        "id": "zone_pulmonary_veins",
        "label": "Pulmonary Veins",
        "points": [
          [
            83.9,
            40.5
          ],
          [
            82.9,
            39.6
          ],
          [
            82.3,
            39.4
          ],
          [
            80.6,
            39.4
          ],
          [
            80.4,
            39.6
          ],
          [
            79.5,
            39.4
          ],
          [
            79.3,
            39.6
          ],
          [
            71.7,
            40.1
          ],
          [
            71.0,
            40.3
          ],
          [
            70.7,
            40.8
          ],
          [
            74.0,
            47.2
          ],
          [
            74.9,
            47.8
          ],
          [
            78.8,
            47.2
          ],
          [
            82.5,
            47.2
          ],
          [
            83.4,
            46.7
          ],
          [
            84.1,
            45.8
          ],
          [
            84.6,
            44.0
          ],
          [
            84.6,
            42.6
          ]
        ],
        "x": 79.4,
        "y": 42.6,
        "radius": 8.9,
        "shape": "polygon",
        "center": {
          "x": 79.4,
          "y": 42.6
        }
      },
      {
        "id": "zone_superior_vena_cava",
        "label": "Superior Vena Cava",
        "points": [
          [
            26.3,
            8.7
          ],
          [
            24.0,
            9.8
          ],
          [
            23.3,
            10.9
          ],
          [
            24.4,
            30.5
          ],
          [
            24.2,
            39.6
          ],
          [
            25.6,
            42.1
          ],
          [
            29.5,
            43.1
          ],
          [
            32.9,
            41.7
          ],
          [
            35.0,
            39.0
          ],
          [
            34.3,
            36.2
          ],
          [
            32.9,
            11.2
          ],
          [
            30.9,
            9.1
          ]
        ],
        "x": 28.6,
        "y": 26.8,
        "radius": 18.2,
        "shape": "polygon",
        "center": {
          "x": 28.6,
          "y": 26.8
        }
      },
      {
        "id": "zone_inferior_vena_cava",
        "label": "Inferior Vena Cava",
        "points": [
          [
            24.0,
            74.3
          ],
          [
            23.5,
            77.0
          ],
          [
            22.8,
            90.4
          ],
          [
            23.5,
            91.8
          ],
          [
            25.3,
            93.4
          ],
          [
            26.7,
            93.8
          ],
          [
            30.0,
            93.6
          ],
          [
            32.9,
            91.1
          ],
          [
            33.6,
            82.2
          ],
          [
            29.3,
            79.3
          ]
        ],
        "x": 27.2,
        "y": 86.7,
        "radius": 12.8,
        "shape": "polygon",
        "center": {
          "x": 27.2,
          "y": 86.7
        }
      }
    ],
    "imageUrl": "https://www.ptdirect.com/images/personal-training-chambers-of-the-heart",
    "assetUrl": "/api/assets/demo/demo_drag_drop_v2/diagram.png"
  },
  "labels": [
    {
      "id": "label_s1_0",
      "text": "Right Atrium",
      "correctZoneId": "zone_right_atrium"
    },
    {
      "id": "label_s1_1",
      "text": "Left Atrium",
      "correctZoneId": "zone_left_atrium"
    },
    {
      "id": "label_s1_2",
      "text": "Right Ventricle",
      "correctZoneId": "zone_right_ventricle"
    },
    {
      "id": "label_s1_3",
      "text": "Left Ventricle",
      "correctZoneId": "zone_left_ventricle"
    },
    {
      "id": "label_s1_4",
      "text": "Tricuspid Valve",
      "correctZoneId": "zone_tricuspid_valve"
    },
    {
      "id": "label_s1_5",
      "text": "Pulmonary Valve",
      "correctZoneId": "zone_pulmonary_valve"
    },
    {
      "id": "label_s1_6",
      "text": "Mitral Valve",
      "correctZoneId": "zone_mitral_valve"
    },
    {
      "id": "label_s1_7",
      "text": "Aortic Valve",
      "correctZoneId": "zone_aortic_valve"
    },
    {
      "id": "label_s1_8",
      "text": "Aorta",
      "correctZoneId": "zone_aorta"
    },
    {
      "id": "label_s1_9",
      "text": "Pulmonary Artery",
      "correctZoneId": "zone_pulmonary_artery"
    },
    {
      "id": "label_s1_10",
      "text": "Pulmonary Veins",
      "correctZoneId": "zone_pulmonary_veins"
    },
    {
      "id": "label_s1_11",
      "text": "Superior Vena Cava",
      "correctZoneId": "zone_superior_vena_cava"
    },
    {
      "id": "label_s1_12",
      "text": "Inferior Vena Cava",
      "correctZoneId": "zone_inferior_vena_cava"
    }
  ],
  "distractorLabels": [],
  "mechanics": [
    {
      "type": "drag_drop",
      "config": {
        "instruction_text": "Welcome, aspiring medical professional! Your first task is to master the anatomy of the human heart. Drag each anatomical label from the list and drop it onto its corresponding structure on the detailed heart diagram. Ensure precise placement for accurate identification."
      },
      "scoring": {
        "strategy": "per_correct",
        "points_per_correct": 10,
        "max_score": 130,
        "partial_credit": true
      },
      "feedback": {
        "on_correct": "Excellent! You've correctly identified that part of the heart.",
        "on_incorrect": "Not quite the right spot for that label. Take another look at its position relative to other structures.",
        "on_completion": "Fantastic work! You've successfully labeled all the key structures of the human heart. You're ready to explore how it functions!",
        "misconceptions": [
          {
            "trigger_label": "misplaced_heart_location",
            "message": "Remember, the heart is centrally located in the chest, behind the sternum, with its apex (bottom tip) tilted slightly to the left."
          },
          {
            "trigger_label": "artery_vein_confusion",
            "message": "It's a common misconception! Arteries carry blood away from the heart, and veins carry blood towards the heart. The pulmonary artery carries deoxygenated blood, and the pulmonary veins carry oxygenated blood."
          },
          {
            "trigger_label": "single_pump_misconception",
            "message": "The human heart is actually a four-chambered organ that functions as two separate, coordinated pumps (pulmonary and systemic circuits) working in parallel."
          }
        ]
      }
    }
  ],
  "modeTransitions": [],
  "interactionMode": "drag_drop",
  "animationCues": {
    "correctPlacement": "pulse-green",
    "incorrectPlacement": "shake-red"
  },
  "scoringStrategy": {
    "type": "per_zone",
    "base_points_per_zone": 10,
    "max_score": 130
  },
  "totalMaxScore": 130,
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
    "feedback_timing": "deferred",
    "pin_marker_shape": "circle"
  },
  "tasks": []
} as any as InteractiveDiagramBlueprint;
