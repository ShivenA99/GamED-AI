import type { InteractiveDiagramBlueprint } from '../types';

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export const clickToIdentifyDemo = {
  "templateType": "INTERACTIVE_DIAGRAM",
  "title": "Animal Cell Explorer: Function First",
  "subject": "Biology",
  "difficulty": "intermediate",
  "narrativeIntro": "Welcome, intrepid biologist! Your mission is to navigate the intricate world of an animal cell. We'll start by identifying its key structures and then delve into the vital functions each organelle performs to keep the cell alive and thriving. Prepare your microscope and let's begin our journey into the microscopic marvel!",
  "narrativeTheme": "Cellular Exploration",
  "completionMessage": "Congratulations, Cell Explorer! You've successfully identified and understood the crucial functions of all major animal cell organelles. Your expertise is vital for understanding life at its most fundamental level!",
  "estimatedDurationMinutes": 12,
  "diagram": {
    "assetPrompt": "Detailed diagram of an animal cell showing organelles",
    "zones": [
      {
        "id": "zone_cell_membrane",
        "label": "Cell Membrane",
        "points": [
          [
            49.2,
            10.8
          ],
          [
            38.7,
            13.9
          ],
          [
            28.2,
            24.7
          ],
          [
            22.6,
            39.0
          ],
          [
            21.6,
            52.5
          ],
          [
            24.7,
            67.7
          ],
          [
            30.7,
            78.2
          ],
          [
            40.3,
            86.2
          ],
          [
            51.4,
            88.4
          ],
          [
            62.7,
            84.5
          ],
          [
            71.0,
            75.9
          ],
          [
            76.7,
            63.2
          ],
          [
            78.4,
            47.2
          ],
          [
            75.9,
            33.8
          ],
          [
            69.5,
            21.5
          ],
          [
            59.5,
            13.0
          ]
        ],
        "x": 50.1,
        "y": 50.0,
        "radius": 39.2,
        "shape": "polygon",
        "center": {
          "x": 50.1,
          "y": 50.0
        },
        "description": "Regulates the passage of substances into and out of the cell, maintaining cell integrity and mediating cell-cell communication."
      },
      {
        "id": "zone_cytoplasm",
        "label": "Cytoplasm",
        "points": [
          [
            45.7,
            11.2
          ],
          [
            34.6,
            17.0
          ],
          [
            26.7,
            27.5
          ],
          [
            22.0,
            42.7
          ],
          [
            22.0,
            56.8
          ],
          [
            26.3,
            71.2
          ],
          [
            33.5,
            81.4
          ],
          [
            42.8,
            87.3
          ],
          [
            54.3,
            88.0
          ],
          [
            64.8,
            82.9
          ],
          [
            72.7,
            73.0
          ],
          [
            77.4,
            59.7
          ],
          [
            78.2,
            45.5
          ],
          [
            74.6,
            30.3
          ],
          [
            67.1,
            18.8
          ],
          [
            57.8,
            12.3
          ]
        ],
        "x": 50.0,
        "y": 50.4,
        "radius": 39.4,
        "shape": "polygon",
        "center": {
          "x": 50.0,
          "y": 50.4
        },
        "description": "The jelly-like substance filling the cell, providing a medium for organelles and facilitating many metabolic reactions.",
        "parentZoneId": "zone_cell_membrane"
      },
      {
        "id": "zone_nucleus",
        "label": "Nucleus",
        "points": [
          [
            48.6,
            37.2
          ],
          [
            45.3,
            39.5
          ],
          [
            43.2,
            42.8
          ],
          [
            42.3,
            47.1
          ],
          [
            42.7,
            52.3
          ],
          [
            45.6,
            57.4
          ],
          [
            49.3,
            59.1
          ],
          [
            52.3,
            59.0
          ],
          [
            55.7,
            56.8
          ],
          [
            57.8,
            53.4
          ],
          [
            58.6,
            49.5
          ],
          [
            58.4,
            44.3
          ],
          [
            54.0,
            38.0
          ],
          [
            51.5,
            36.9
          ]
        ],
        "x": 50.4,
        "y": 48.1,
        "radius": 11.3,
        "shape": "polygon",
        "center": {
          "x": 50.4,
          "y": 48.1
        },
        "description": "Houses the cell's genetic material (DNA) and controls cell growth, metabolism, and reproduction by regulating gene expression.",
        "parentZoneId": "zone_cytoplasm"
      },
      {
        "id": "zone_mitochondrion",
        "label": "Mitochondrion",
        "points": [
          [
            44.3,
            80.9
          ],
          [
            44.6,
            82.1
          ],
          [
            45.8,
            83.4
          ],
          [
            47.4,
            84.5
          ],
          [
            49.4,
            85.2
          ],
          [
            51.9,
            85.3
          ],
          [
            53.6,
            85.0
          ],
          [
            54.9,
            84.1
          ],
          [
            55.5,
            83.1
          ],
          [
            55.3,
            81.5
          ],
          [
            54.6,
            80.7
          ],
          [
            53.3,
            80.0
          ],
          [
            50.4,
            80.0
          ],
          [
            47.0,
            79.1
          ],
          [
            45.9,
            79.1
          ],
          [
            44.9,
            79.5
          ]
        ],
        "x": 49.9,
        "y": 82.1,
        "radius": 5.7,
        "shape": "polygon",
        "center": {
          "x": 49.9,
          "y": 82.1
        },
        "description": "Generates most of the cell's supply of adenosine triphosphate (ATP), the primary energy currency of the cell.",
        "parentZoneId": "zone_cytoplasm"
      },
      {
        "id": "zone_golgi_apparatus",
        "label": "Golgi Apparatus",
        "points": [
          [
            39.3,
            59.3
          ],
          [
            38.8,
            62.6
          ],
          [
            38.9,
            63.7
          ],
          [
            38.5,
            64.8
          ],
          [
            39.7,
            66.3
          ],
          [
            42.8,
            68.2
          ],
          [
            45.6,
            68.9
          ],
          [
            48.4,
            68.5
          ],
          [
            49.7,
            67.5
          ],
          [
            50.3,
            61.3
          ],
          [
            48.9,
            59.5
          ],
          [
            45.6,
            57.9
          ],
          [
            44.3,
            58.0
          ],
          [
            43.8,
            58.4
          ],
          [
            40.7,
            58.3
          ]
        ],
        "x": 43.7,
        "y": 62.9,
        "radius": 7.6,
        "shape": "polygon",
        "center": {
          "x": 43.7,
          "y": 62.9
        },
        "description": "Modifies, sorts, and packages proteins and lipids for secretion or delivery to other organelles.",
        "parentZoneId": "zone_cytoplasm"
      },
      {
        "id": "zone_endoplasmic_reticulum",
        "label": "Endoplasmic Reticulum",
        "points": [
          [
            58.4,
            48.0
          ],
          [
            66.8,
            48.0
          ],
          [
            66.8,
            71.0
          ],
          [
            58.4,
            71.0
          ]
        ],
        "x": 62.6,
        "y": 59.5,
        "width": 8.4,
        "height": 23.1,
        "shape": "rect",
        "description": "A network of membranes involved in protein and lipid synthesis, detoxification, and calcium storage.",
        "parentZoneId": "zone_cytoplasm"
      },
      {
        "id": "zone_lysosome",
        "label": "Lysosome",
        "points": [
          [
            75.0,
            48.1
          ],
          [
            77.5,
            48.1
          ],
          [
            77.5,
            51.1
          ],
          [
            75.0,
            51.1
          ]
        ],
        "x": 76.3,
        "y": 49.6,
        "width": 2.5,
        "height": 3.0,
        "shape": "rect",
        "description": "Contains digestive enzymes to break down waste materials, cellular debris, and foreign invaders.",
        "parentZoneId": "zone_cytoplasm"
      },
      {
        "id": "zone_peroxisome",
        "label": "Peroxisome",
        "points": [
          [
            46.8,
            34.0
          ],
          [
            48.8,
            34.0
          ],
          [
            48.8,
            36.0
          ],
          [
            46.8,
            36.0
          ]
        ],
        "x": 47.8,
        "y": 35.0,
        "width": 1.9,
        "height": 1.9,
        "shape": "rect",
        "description": "Involved in metabolic processes, including fatty acid breakdown and detoxification of harmful substances, producing hydrogen peroxide.",
        "parentZoneId": "zone_cytoplasm"
      },
      {
        "id": "zone_centrosome",
        "label": "Centrosome",
        "points": [
          [
            36.4,
            32.3
          ],
          [
            34.4,
            38.1
          ],
          [
            33.6,
            41.2
          ],
          [
            34.7,
            42.2
          ],
          [
            35.9,
            42.5
          ],
          [
            36.1,
            41.1
          ],
          [
            36.7,
            40.4
          ],
          [
            36.8,
            40.7
          ],
          [
            36.4,
            42.8
          ],
          [
            37.4,
            44.0
          ],
          [
            38.3,
            44.1
          ],
          [
            38.8,
            43.5
          ],
          [
            40.3,
            38.5
          ],
          [
            41.2,
            36.6
          ],
          [
            41.3,
            35.3
          ],
          [
            40.5,
            34.4
          ],
          [
            39.4,
            34.1
          ],
          [
            38.5,
            35.4
          ],
          [
            38.1,
            34.8
          ],
          [
            38.5,
            33.8
          ],
          [
            37.6,
            32.8
          ]
        ],
        "x": 37.7,
        "y": 38.5,
        "radius": 6.3,
        "shape": "polygon",
        "center": {
          "x": 37.7,
          "y": 38.5
        },
        "description": "The main microtubule-organizing center in animal cells, crucial for cell division and cytoskeleton organization.",
        "parentZoneId": "zone_cytoplasm"
      },
      {
        "id": "zone_centriole",
        "label": "Centriole",
        "points": [
          [
            36.5,
            34.0
          ],
          [
            41.7,
            34.0
          ],
          [
            41.7,
            44.0
          ],
          [
            36.5,
            44.0
          ]
        ],
        "x": 39.1,
        "y": 39.0,
        "width": 5.2,
        "height": 10.0,
        "shape": "rect",
        "description": "A cylindrical organelle within the centrosome, involved in the formation of spindle fibers during cell division.",
        "parentZoneId": "zone_centrosome"
      },
      {
        "id": "zone_vacuole",
        "label": "Vacuole",
        "points": [
          [
            34.2,
            77.0
          ],
          [
            35.8,
            77.0
          ],
          [
            35.8,
            78.6
          ],
          [
            34.2,
            78.6
          ]
        ],
        "x": 35.0,
        "y": 77.8,
        "width": 1.5,
        "height": 1.7,
        "shape": "rect",
        "description": "Primarily involved in storage of water, nutrients, and waste products; typically small and temporary in animal cells.",
        "parentZoneId": "zone_cytoplasm"
      }
    ],
    "imageUrl": "/api/assets/demo/ab5c9d19-c947-483f-a40a-d5f1c71e7a65/diagram_scene_1.png",
    "assetUrl": "/api/assets/demo/ab5c9d19-c947-483f-a40a-d5f1c71e7a65/diagram_scene_1.png"
  },
  "labels": [
    {
      "id": "label_s1_0",
      "text": "Cell Membrane",
      "correctZoneId": "zone_cell_membrane"
    },
    {
      "id": "label_s1_1",
      "text": "Cytoplasm",
      "correctZoneId": "zone_cytoplasm"
    },
    {
      "id": "label_s1_2",
      "text": "Nucleus",
      "correctZoneId": "zone_nucleus"
    },
    {
      "id": "label_s1_3",
      "text": "Mitochondrion",
      "correctZoneId": "zone_mitochondrion"
    },
    {
      "id": "label_s1_4",
      "text": "Golgi Apparatus",
      "correctZoneId": "zone_golgi_apparatus"
    },
    {
      "id": "label_s1_5",
      "text": "Endoplasmic Reticulum",
      "correctZoneId": "zone_endoplasmic_reticulum"
    },
    {
      "id": "label_s1_6",
      "text": "Lysosome",
      "correctZoneId": "zone_lysosome"
    },
    {
      "id": "label_s1_7",
      "text": "Peroxisome",
      "correctZoneId": "zone_peroxisome"
    },
    {
      "id": "label_s1_8",
      "text": "Centrosome",
      "correctZoneId": "zone_centrosome"
    },
    {
      "id": "label_s1_9",
      "text": "Centriole",
      "correctZoneId": "zone_centriole"
    },
    {
      "id": "label_s1_10",
      "text": "Vacuole",
      "correctZoneId": "zone_vacuole"
    }
  ],
  "distractorLabels": [],
  "mechanics": [
    {
      "type": "drag_drop",
      "config": {
        "instruction_text": "Our first view of the animal cell reveals many vital structures. Drag and drop the correct label onto each highlighted organelle to identify it."
      },
      "scoring": {
        "strategy": "per_correct",
        "points_per_correct": 10,
        "max_score": 110,
        "partial_credit": true
      },
      "feedback": {
        "on_correct": "Excellent! You've correctly identified the {label_name}.",
        "on_incorrect": "Not quite. The {label_name} belongs to a different part of the cell. Take another look at its structure and location.",
        "on_completion": "Fantastic work! You've successfully identified all the major components of the animal cell. Now let's explore their functions!",
        "misconceptions": [
          {
            "trigger_label": "wrong_zone_Lysosome_placed_Peroxisome",
            "message": "It's easy to confuse these! Remember, lysosomes are for waste breakdown and recycling, while peroxisomes are specialized in detoxifying harmful substances and breaking down fatty acids."
          },
          {
            "trigger_label": "wrong_zone_Peroxisome_placed_Lysosome",
            "message": "It's easy to confuse these! Remember, lysosomes are for waste breakdown and recycling, while peroxisomes are specialized in detoxifying harmful substances and breaking down fatty acids."
          },
          {
            "trigger_label": "wrong_zone_Endoplasmic Reticulum_placed_Golgi Apparatus",
            "message": "While both are involved in protein processing, the Endoplasmic Reticulum is where proteins and lipids are synthesized, and the Golgi Apparatus modifies, sorts, and packages them for delivery."
          },
          {
            "trigger_label": "wrong_zone_Golgi Apparatus_placed_Endoplasmic Reticulum",
            "message": "While both are involved in protein processing, the Endoplasmic Reticulum is where proteins and lipids are synthesized, and the Golgi Apparatus modifies, sorts, and packages them for delivery."
          }
        ]
      }
    },
    {
      "type": "description_matching",
      "config": {
        "instruction_text": "Now that you've successfully identified the major organelles, match each one to its primary function to deepen your understanding of their roles within the cell."
      },
      "scoring": {
        "strategy": "per_correct",
        "points_per_correct": 15,
        "max_score": 165,
        "partial_credit": true
      },
      "feedback": {
        "on_correct": "Spot on! That description perfectly matches the function of the {organelle_name}.",
        "on_incorrect": "Not quite. Re-evaluate the description and the organelle's primary role. Each organelle has a unique and vital function.",
        "on_completion": "Outstanding! You've accurately matched all the organelles with their descriptions, demonstrating a strong understanding of their roles. Remember, these organelles work together in a highly coordinated manner, forming complex pathways and systems to maintain cellular life and carry out specific tasks!",
        "misconceptions": [
          {
            "trigger_label": "mismatch_Lysosome_Peroxisome",
            "message": "Careful with these two! Lysosomes are the cell's recycling centers, breaking down waste and cellular debris. Peroxisomes, on the other hand, are crucial for detoxification and breaking down fatty acids."
          },
          {
            "trigger_label": "mismatch_Peroxisome_Lysosome",
            "message": "Careful with these two! Lysosomes are the cell's recycling centers, breaking down waste and cellular debris. Peroxisomes, on the other hand, are crucial for detoxification and breaking down fatty acids."
          },
          {
            "trigger_label": "mismatch_Endoplasmic Reticulum_Golgi Apparatus",
            "message": "While both are part of the endomembrane system, the Endoplasmic Reticulum is primarily involved in synthesis and transport, whereas the Golgi Apparatus is the cell's 'post office' for modifying, sorting, and packaging."
          },
          {
            "trigger_label": "mismatch_Golgi Apparatus_Endoplasmic Reticulum",
            "message": "While both are part of the endomembrane system, the Endoplasmic Reticulum is primarily involved in synthesis and transport, whereas the Golgi Apparatus is the cell's 'post office' for modifying, sorting, and packaging."
          }
        ]
      }
    },
    {
      "type": "drag_drop",
      "config": {
        "instruction_text": "Drag and drop the labels to correctly identify the main components of the animal cell nucleus."
      },
      "scoring": {
        "strategy": "per_correct",
        "points_per_correct": 10,
        "max_score": 30,
        "partial_credit": true
      },
      "feedback": {
        "on_correct": "Excellent! You've correctly identified that part of the nucleus.",
        "on_incorrect": "Not quite right. Take another look at the structure and its name. Remember what each part does.",
        "on_completion": "Fantastic! You've successfully labeled all the key parts of the nucleus!",
        "misconceptions": [
          {
            "trigger_label": "incorrect_placement_Nucleus",
            "message": "Remember, the Nucleus is the entire central organelle housing the genetic material and controlling cell activities, not just a specific part within it."
          },
          {
            "trigger_label": "incorrect_placement_Nuclear Envelope",
            "message": "The Nuclear Envelope is the protective double membrane surrounding the nucleus, regulating what enters and exits."
          },
          {
            "trigger_label": "incorrect_placement_Nucleolus",
            "message": "The Nucleolus is a dense structure inside the nucleus, crucial for ribosomal RNA synthesis and ribosome assembly."
          },
          {
            "trigger_label": "distractor_placed_in_nucleus_zone",
            "message": "Careful! The Mitochondrion and Cytoplasm are distinct from the nucleus. Focus on the structures *within* or *directly surrounding* the nucleus."
          }
        ]
      }
    },
    {
      "type": "description_matching",
      "config": {
        "instruction_text": "Now that you've labeled the parts of the nucleus, match each structure to its primary function by clicking the description and then the corresponding part on the diagram."
      },
      "scoring": {
        "strategy": "per_correct",
        "points_per_correct": 15,
        "max_score": 45,
        "partial_credit": true
      },
      "feedback": {
        "on_correct": "Spot on! That description perfectly matches its function.",
        "on_incorrect": "Close, but not quite. Re-evaluate the specific role of each part. What does this structure *do*?",
        "on_completion": "Outstanding! You've accurately described the functions of all the nucleus's components!",
        "misconceptions": [
          {
            "trigger_label": "confusing_nucleus_parts_functions",
            "message": "Each part of the nucleus, like the Nuclear Envelope and Nucleolus, has distinct structural features and highly specific functions crucial for cellular processes. Don't confuse their roles!"
          }
        ]
      }
    },
    {
      "type": "drag_drop",
      "config": {
        "instruction_text": "Identify the key structures of the endoplasmic reticulum network by dragging the correct labels to their corresponding zones on the diagram."
      },
      "scoring": {
        "strategy": "per_correct",
        "points_per_correct": 10,
        "max_score": 30,
        "partial_credit": true
      },
      "feedback": {
        "on_correct": "Excellent! That's the correct location for this component.",
        "on_incorrect": "Not quite. Consider the specific features or functions of this organelle to find its correct place.",
        "on_completion": "Fantastic! You've correctly identified and placed all the key components of the Endoplasmic Reticulum network.",
        "misconceptions": [
          {
            "trigger_label": "RER_SER_placement_confusion",
            "message": "It looks like you might be mixing up the Rough and Smooth ER. Remember, the 'rough' part comes from ribosomes, which are involved in protein synthesis, while the 'smooth' part handles lipids and detoxification."
          },
          {
            "trigger_label": "Ribosome_misplacement",
            "message": "Ribosomes are the protein factories of the cell, found both free in the cytoplasm and attached to the Rough ER. Where would they best fit in this diagram?"
          }
        ]
      }
    },
    {
      "type": "description_matching",
      "config": {
        "instruction_text": "Now that you've identified the structures, match each one to its primary function within the cell by dragging the description to the correct labeled zone."
      },
      "scoring": {
        "strategy": "per_correct",
        "points_per_correct": 15,
        "max_score": 45,
        "partial_credit": true
      },
      "feedback": {
        "on_correct": "That's a perfect match! You've correctly identified the function.",
        "on_incorrect": "Not quite. Re-evaluate the specific functions. Which organelle is responsible for this particular task?",
        "on_completion": "Outstanding! You've accurately described the functions of each part of the ER network and ribosomes.",
        "misconceptions": [
          {
            "trigger_label": "RER_SER_function_confusion",
            "message": "You're close, but let's clarify the roles of the Rough and Smooth ER. The Rough ER is the protein factory, while the Smooth ER is crucial for lipid synthesis and detoxification."
          },
          {
            "trigger_label": "Ribosome_function_confusion",
            "message": "Don't forget the primary role of ribosomes! They are the fundamental sites for protein synthesis, translating genetic instructions into proteins."
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
    },
    {
      "from": "drag_drop",
      "to": "description_matching",
      "trigger": "all_zones_labeled",
      "animation": "fade"
    },
    {
      "from": "drag_drop",
      "to": "click_zone",
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
    "max_score": 425
  },
  "totalMaxScore": 425,
  "generation_complete": true,
  "dragDropConfig": {
    "leader_line_style": "none",
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
      "zone_cell_membrane": "Regulates the passage of substances into and out of the cell, maintaining cell integrity and mediating cell-cell communication.",
      "zone_cytoplasm": "The jelly-like substance filling the cell, providing a medium for organelles and facilitating many metabolic reactions.",
      "zone_nucleus": "Houses the cell's genetic material (DNA) and controls cell growth, metabolism, and reproduction by regulating gene expression.",
      "zone_mitochondrion": "Generates most of the cell's supply of adenosine triphosphate (ATP), the primary energy currency of the cell.",
      "zone_golgi_apparatus": "Modifies, sorts, and packages proteins and lipids for secretion or delivery to other organelles.",
      "zone_endoplasmic_reticulum": "A network of membranes involved in protein and lipid synthesis, detoxification, and calcium storage.",
      "zone_lysosome": "Contains digestive enzymes to break down waste materials, cellular debris, and foreign invaders.",
      "zone_peroxisome": "Involved in metabolic processes, including fatty acid breakdown and detoxification of harmful substances, producing hydrogen peroxide.",
      "zone_centrosome": "The main microtubule-organizing center in animal cells, crucial for cell division and cytoskeleton organization.",
      "zone_centriole": "A cylindrical organelle within the centrosome, involved in the formation of spindle fibers during cell division.",
      "zone_vacuole": "Primarily involved in storage of water, nutrients, and waste products; typically small and temporary in animal cells."
    },
    "mode": "click_zone",
    "show_connecting_lines": true,
    "defer_evaluation": false,
    "description_panel_position": "right"
  },
  "is_multi_scene": true,
  "game_sequence": {
    "sequence_id": "11071ad9-abdc-4e9c-a51a-a7fc1e04133f",
    "sequence_title": "Animal Cell Explorer: Function First",
    "sequence_description": "",
    "scenes": [
      {
        "scene_id": "scene_1",
        "scene_number": 1,
        "title": "The Cell's Core Components",
        "narrative_intro": "Our first view of the animal cell reveals many vital structures. First, label them to orient yourself, then match each part to its primary role.",
        "learning_goal": "Identify and describe the functions of major animal cell organelles in an overview.",
        "diagram": {
          "assetPrompt": "A detailed, high-resolution scientific illustration of a typical animal cell. All major organelles are clearly depicted with distinct shapes, textures, and relative sizes, making them easily identifiable as separate zones. The cell membrane forms a clear boundary. The cytoplasm is visible as the internal environment. The nucleus is prominent, and other organelles like mitochondria, Golgi apparatus, endoplasmic reticulum (both rough and smooth implied but labeled as general ER), lysosomes, peroxisomes, centrosome, centrioles, and a small animal vacuole are all distinctly rendered and spatially separated for unambiguous zone identification.",
          "zones": [
            {
              "id": "zone_cell_membrane",
              "label": "Cell Membrane",
              "points": [
                [
                  49.2,
                  10.8
                ],
                [
                  38.7,
                  13.9
                ],
                [
                  28.2,
                  24.7
                ],
                [
                  22.6,
                  39.0
                ],
                [
                  21.6,
                  52.5
                ],
                [
                  24.7,
                  67.7
                ],
                [
                  30.7,
                  78.2
                ],
                [
                  40.3,
                  86.2
                ],
                [
                  51.4,
                  88.4
                ],
                [
                  62.7,
                  84.5
                ],
                [
                  71.0,
                  75.9
                ],
                [
                  76.7,
                  63.2
                ],
                [
                  78.4,
                  47.2
                ],
                [
                  75.9,
                  33.8
                ],
                [
                  69.5,
                  21.5
                ],
                [
                  59.5,
                  13.0
                ]
              ],
              "x": 50.1,
              "y": 50.0,
              "radius": 39.2,
              "shape": "polygon",
              "center": {
                "x": 50.1,
                "y": 50.0
              },
              "description": "Regulates the passage of substances into and out of the cell, maintaining cell integrity and mediating cell-cell communication.",
              "hierarchyLevel": 1,
              "childZoneIds": [
                "zone_cytoplasm"
              ]
            },
            {
              "id": "zone_cytoplasm",
              "label": "Cytoplasm",
              "points": [
                [
                  45.7,
                  11.2
                ],
                [
                  34.6,
                  17.0
                ],
                [
                  26.7,
                  27.5
                ],
                [
                  22.0,
                  42.7
                ],
                [
                  22.0,
                  56.8
                ],
                [
                  26.3,
                  71.2
                ],
                [
                  33.5,
                  81.4
                ],
                [
                  42.8,
                  87.3
                ],
                [
                  54.3,
                  88.0
                ],
                [
                  64.8,
                  82.9
                ],
                [
                  72.7,
                  73.0
                ],
                [
                  77.4,
                  59.7
                ],
                [
                  78.2,
                  45.5
                ],
                [
                  74.6,
                  30.3
                ],
                [
                  67.1,
                  18.8
                ],
                [
                  57.8,
                  12.3
                ]
              ],
              "x": 50.0,
              "y": 50.4,
              "radius": 39.4,
              "shape": "polygon",
              "center": {
                "x": 50.0,
                "y": 50.4
              },
              "description": "The jelly-like substance filling the cell, providing a medium for organelles and facilitating many metabolic reactions.",
              "hierarchyLevel": 2,
              "parentZoneId": "zone_cell_membrane",
              "childZoneIds": [
                "zone_nucleus",
                "zone_mitochondrion",
                "zone_endoplasmic_reticulum",
                "zone_golgi_apparatus",
                "zone_lysosome",
                "zone_peroxisome",
                "zone_centrosome",
                "zone_vacuole"
              ]
            },
            {
              "id": "zone_nucleus",
              "label": "Nucleus",
              "points": [
                [
                  48.6,
                  37.2
                ],
                [
                  45.3,
                  39.5
                ],
                [
                  43.2,
                  42.8
                ],
                [
                  42.3,
                  47.1
                ],
                [
                  42.7,
                  52.3
                ],
                [
                  45.6,
                  57.4
                ],
                [
                  49.3,
                  59.1
                ],
                [
                  52.3,
                  59.0
                ],
                [
                  55.7,
                  56.8
                ],
                [
                  57.8,
                  53.4
                ],
                [
                  58.6,
                  49.5
                ],
                [
                  58.4,
                  44.3
                ],
                [
                  54.0,
                  38.0
                ],
                [
                  51.5,
                  36.9
                ]
              ],
              "x": 50.4,
              "y": 48.1,
              "radius": 11.3,
              "shape": "polygon",
              "center": {
                "x": 50.4,
                "y": 48.1
              },
              "description": "Houses the cell's genetic material (DNA) and controls cell growth, metabolism, and reproduction by regulating gene expression.",
              "hierarchyLevel": 3,
              "parentZoneId": "zone_cytoplasm"
            },
            {
              "id": "zone_mitochondrion",
              "label": "Mitochondrion",
              "points": [
                [
                  44.3,
                  80.9
                ],
                [
                  44.6,
                  82.1
                ],
                [
                  45.8,
                  83.4
                ],
                [
                  47.4,
                  84.5
                ],
                [
                  49.4,
                  85.2
                ],
                [
                  51.9,
                  85.3
                ],
                [
                  53.6,
                  85.0
                ],
                [
                  54.9,
                  84.1
                ],
                [
                  55.5,
                  83.1
                ],
                [
                  55.3,
                  81.5
                ],
                [
                  54.6,
                  80.7
                ],
                [
                  53.3,
                  80.0
                ],
                [
                  50.4,
                  80.0
                ],
                [
                  47.0,
                  79.1
                ],
                [
                  45.9,
                  79.1
                ],
                [
                  44.9,
                  79.5
                ]
              ],
              "x": 49.9,
              "y": 82.1,
              "radius": 5.7,
              "shape": "polygon",
              "center": {
                "x": 49.9,
                "y": 82.1
              },
              "description": "Generates most of the cell's supply of adenosine triphosphate (ATP), the primary energy currency of the cell.",
              "hierarchyLevel": 3,
              "parentZoneId": "zone_cytoplasm"
            },
            {
              "id": "zone_golgi_apparatus",
              "label": "Golgi Apparatus",
              "points": [
                [
                  39.3,
                  59.3
                ],
                [
                  38.8,
                  62.6
                ],
                [
                  38.9,
                  63.7
                ],
                [
                  38.5,
                  64.8
                ],
                [
                  39.7,
                  66.3
                ],
                [
                  42.8,
                  68.2
                ],
                [
                  45.6,
                  68.9
                ],
                [
                  48.4,
                  68.5
                ],
                [
                  49.7,
                  67.5
                ],
                [
                  50.3,
                  61.3
                ],
                [
                  48.9,
                  59.5
                ],
                [
                  45.6,
                  57.9
                ],
                [
                  44.3,
                  58.0
                ],
                [
                  43.8,
                  58.4
                ],
                [
                  40.7,
                  58.3
                ]
              ],
              "x": 43.7,
              "y": 62.9,
              "radius": 7.6,
              "shape": "polygon",
              "center": {
                "x": 43.7,
                "y": 62.9
              },
              "description": "Modifies, sorts, and packages proteins and lipids for secretion or delivery to other organelles.",
              "hierarchyLevel": 3,
              "parentZoneId": "zone_cytoplasm"
            },
            {
              "id": "zone_endoplasmic_reticulum",
              "label": "Endoplasmic Reticulum",
              "points": [
                [
                  58.4,
                  48.0
                ],
                [
                  66.8,
                  48.0
                ],
                [
                  66.8,
                  71.0
                ],
                [
                  58.4,
                  71.0
                ]
              ],
              "x": 62.6,
              "y": 59.5,
              "width": 8.4,
              "height": 23.1,
              "shape": "rect",
              "description": "A network of membranes involved in protein and lipid synthesis, detoxification, and calcium storage.",
              "hierarchyLevel": 3,
              "parentZoneId": "zone_cytoplasm"
            },
            {
              "id": "zone_lysosome",
              "label": "Lysosome",
              "points": [
                [
                  75.0,
                  48.1
                ],
                [
                  77.5,
                  48.1
                ],
                [
                  77.5,
                  51.1
                ],
                [
                  75.0,
                  51.1
                ]
              ],
              "x": 76.3,
              "y": 49.6,
              "width": 2.5,
              "height": 3.0,
              "shape": "rect",
              "description": "Contains digestive enzymes to break down waste materials, cellular debris, and foreign invaders.",
              "hierarchyLevel": 3,
              "parentZoneId": "zone_cytoplasm"
            },
            {
              "id": "zone_peroxisome",
              "label": "Peroxisome",
              "points": [
                [
                  46.8,
                  34.0
                ],
                [
                  48.8,
                  34.0
                ],
                [
                  48.8,
                  36.0
                ],
                [
                  46.8,
                  36.0
                ]
              ],
              "x": 47.8,
              "y": 35.0,
              "width": 1.9,
              "height": 1.9,
              "shape": "rect",
              "description": "Involved in metabolic processes, including fatty acid breakdown and detoxification of harmful substances, producing hydrogen peroxide.",
              "hierarchyLevel": 3,
              "parentZoneId": "zone_cytoplasm"
            },
            {
              "id": "zone_centrosome",
              "label": "Centrosome",
              "points": [
                [
                  36.4,
                  32.3
                ],
                [
                  34.4,
                  38.1
                ],
                [
                  33.6,
                  41.2
                ],
                [
                  34.7,
                  42.2
                ],
                [
                  35.9,
                  42.5
                ],
                [
                  36.1,
                  41.1
                ],
                [
                  36.7,
                  40.4
                ],
                [
                  36.8,
                  40.7
                ],
                [
                  36.4,
                  42.8
                ],
                [
                  37.4,
                  44.0
                ],
                [
                  38.3,
                  44.1
                ],
                [
                  38.8,
                  43.5
                ],
                [
                  40.3,
                  38.5
                ],
                [
                  41.2,
                  36.6
                ],
                [
                  41.3,
                  35.3
                ],
                [
                  40.5,
                  34.4
                ],
                [
                  39.4,
                  34.1
                ],
                [
                  38.5,
                  35.4
                ],
                [
                  38.1,
                  34.8
                ],
                [
                  38.5,
                  33.8
                ],
                [
                  37.6,
                  32.8
                ]
              ],
              "x": 37.7,
              "y": 38.5,
              "radius": 6.3,
              "shape": "polygon",
              "center": {
                "x": 37.7,
                "y": 38.5
              },
              "description": "The main microtubule-organizing center in animal cells, crucial for cell division and cytoskeleton organization.",
              "hierarchyLevel": 3,
              "parentZoneId": "zone_cytoplasm",
              "childZoneIds": [
                "zone_centriole"
              ]
            },
            {
              "id": "zone_centriole",
              "label": "Centriole",
              "points": [
                [
                  36.5,
                  34.0
                ],
                [
                  41.7,
                  34.0
                ],
                [
                  41.7,
                  44.0
                ],
                [
                  36.5,
                  44.0
                ]
              ],
              "x": 39.1,
              "y": 39.0,
              "width": 5.2,
              "height": 10.0,
              "shape": "rect",
              "description": "A cylindrical organelle within the centrosome, involved in the formation of spindle fibers during cell division.",
              "hierarchyLevel": 4,
              "parentZoneId": "zone_centrosome"
            },
            {
              "id": "zone_vacuole",
              "label": "Vacuole",
              "points": [
                [
                  34.2,
                  77.0
                ],
                [
                  35.8,
                  77.0
                ],
                [
                  35.8,
                  78.6
                ],
                [
                  34.2,
                  78.6
                ]
              ],
              "x": 35.0,
              "y": 77.8,
              "width": 1.5,
              "height": 1.7,
              "shape": "rect",
              "description": "Primarily involved in storage of water, nutrients, and waste products; typically small and temporary in animal cells.",
              "hierarchyLevel": 3,
              "parentZoneId": "zone_cytoplasm"
            }
          ],
          "imageUrl": "/api/assets/demo/ab5c9d19-c947-483f-a40a-d5f1c71e7a65/diagram_scene_1.png",
          "assetUrl": "/api/assets/demo/ab5c9d19-c947-483f-a40a-d5f1c71e7a65/diagram_scene_1.png"
        },
        "zones": [
          {
            "id": "zone_cell_membrane",
            "label": "Cell Membrane",
            "points": [
              [
                49.2,
                10.8
              ],
              [
                38.7,
                13.9
              ],
              [
                28.2,
                24.7
              ],
              [
                22.6,
                39.0
              ],
              [
                21.6,
                52.5
              ],
              [
                24.7,
                67.7
              ],
              [
                30.7,
                78.2
              ],
              [
                40.3,
                86.2
              ],
              [
                51.4,
                88.4
              ],
              [
                62.7,
                84.5
              ],
              [
                71.0,
                75.9
              ],
              [
                76.7,
                63.2
              ],
              [
                78.4,
                47.2
              ],
              [
                75.9,
                33.8
              ],
              [
                69.5,
                21.5
              ],
              [
                59.5,
                13.0
              ]
            ],
            "x": 50.1,
            "y": 50.0,
            "radius": 39.2,
            "shape": "polygon",
            "center": {
              "x": 50.1,
              "y": 50.0
            },
            "description": "Regulates the passage of substances into and out of the cell, maintaining cell integrity and mediating cell-cell communication.",
            "hierarchyLevel": 1,
            "childZoneIds": [
              "zone_cytoplasm"
            ]
          },
          {
            "id": "zone_cytoplasm",
            "label": "Cytoplasm",
            "points": [
              [
                45.7,
                11.2
              ],
              [
                34.6,
                17.0
              ],
              [
                26.7,
                27.5
              ],
              [
                22.0,
                42.7
              ],
              [
                22.0,
                56.8
              ],
              [
                26.3,
                71.2
              ],
              [
                33.5,
                81.4
              ],
              [
                42.8,
                87.3
              ],
              [
                54.3,
                88.0
              ],
              [
                64.8,
                82.9
              ],
              [
                72.7,
                73.0
              ],
              [
                77.4,
                59.7
              ],
              [
                78.2,
                45.5
              ],
              [
                74.6,
                30.3
              ],
              [
                67.1,
                18.8
              ],
              [
                57.8,
                12.3
              ]
            ],
            "x": 50.0,
            "y": 50.4,
            "radius": 39.4,
            "shape": "polygon",
            "center": {
              "x": 50.0,
              "y": 50.4
            },
            "description": "The jelly-like substance filling the cell, providing a medium for organelles and facilitating many metabolic reactions.",
            "hierarchyLevel": 2,
            "parentZoneId": "zone_cell_membrane",
            "childZoneIds": [
              "zone_nucleus",
              "zone_mitochondrion",
              "zone_endoplasmic_reticulum",
              "zone_golgi_apparatus",
              "zone_lysosome",
              "zone_peroxisome",
              "zone_centrosome",
              "zone_vacuole"
            ]
          },
          {
            "id": "zone_nucleus",
            "label": "Nucleus",
            "points": [
              [
                48.6,
                37.2
              ],
              [
                45.3,
                39.5
              ],
              [
                43.2,
                42.8
              ],
              [
                42.3,
                47.1
              ],
              [
                42.7,
                52.3
              ],
              [
                45.6,
                57.4
              ],
              [
                49.3,
                59.1
              ],
              [
                52.3,
                59.0
              ],
              [
                55.7,
                56.8
              ],
              [
                57.8,
                53.4
              ],
              [
                58.6,
                49.5
              ],
              [
                58.4,
                44.3
              ],
              [
                54.0,
                38.0
              ],
              [
                51.5,
                36.9
              ]
            ],
            "x": 50.4,
            "y": 48.1,
            "radius": 11.3,
            "shape": "polygon",
            "center": {
              "x": 50.4,
              "y": 48.1
            },
            "description": "Houses the cell's genetic material (DNA) and controls cell growth, metabolism, and reproduction by regulating gene expression.",
            "hierarchyLevel": 3,
            "parentZoneId": "zone_cytoplasm"
          },
          {
            "id": "zone_mitochondrion",
            "label": "Mitochondrion",
            "points": [
              [
                44.3,
                80.9
              ],
              [
                44.6,
                82.1
              ],
              [
                45.8,
                83.4
              ],
              [
                47.4,
                84.5
              ],
              [
                49.4,
                85.2
              ],
              [
                51.9,
                85.3
              ],
              [
                53.6,
                85.0
              ],
              [
                54.9,
                84.1
              ],
              [
                55.5,
                83.1
              ],
              [
                55.3,
                81.5
              ],
              [
                54.6,
                80.7
              ],
              [
                53.3,
                80.0
              ],
              [
                50.4,
                80.0
              ],
              [
                47.0,
                79.1
              ],
              [
                45.9,
                79.1
              ],
              [
                44.9,
                79.5
              ]
            ],
            "x": 49.9,
            "y": 82.1,
            "radius": 5.7,
            "shape": "polygon",
            "center": {
              "x": 49.9,
              "y": 82.1
            },
            "description": "Generates most of the cell's supply of adenosine triphosphate (ATP), the primary energy currency of the cell.",
            "hierarchyLevel": 3,
            "parentZoneId": "zone_cytoplasm"
          },
          {
            "id": "zone_golgi_apparatus",
            "label": "Golgi Apparatus",
            "points": [
              [
                39.3,
                59.3
              ],
              [
                38.8,
                62.6
              ],
              [
                38.9,
                63.7
              ],
              [
                38.5,
                64.8
              ],
              [
                39.7,
                66.3
              ],
              [
                42.8,
                68.2
              ],
              [
                45.6,
                68.9
              ],
              [
                48.4,
                68.5
              ],
              [
                49.7,
                67.5
              ],
              [
                50.3,
                61.3
              ],
              [
                48.9,
                59.5
              ],
              [
                45.6,
                57.9
              ],
              [
                44.3,
                58.0
              ],
              [
                43.8,
                58.4
              ],
              [
                40.7,
                58.3
              ]
            ],
            "x": 43.7,
            "y": 62.9,
            "radius": 7.6,
            "shape": "polygon",
            "center": {
              "x": 43.7,
              "y": 62.9
            },
            "description": "Modifies, sorts, and packages proteins and lipids for secretion or delivery to other organelles.",
            "hierarchyLevel": 3,
            "parentZoneId": "zone_cytoplasm"
          },
          {
            "id": "zone_endoplasmic_reticulum",
            "label": "Endoplasmic Reticulum",
            "points": [
              [
                58.4,
                48.0
              ],
              [
                66.8,
                48.0
              ],
              [
                66.8,
                71.0
              ],
              [
                58.4,
                71.0
              ]
            ],
            "x": 62.6,
            "y": 59.5,
            "width": 8.4,
            "height": 23.1,
            "shape": "rect",
            "description": "A network of membranes involved in protein and lipid synthesis, detoxification, and calcium storage.",
            "hierarchyLevel": 3,
            "parentZoneId": "zone_cytoplasm"
          },
          {
            "id": "zone_lysosome",
            "label": "Lysosome",
            "points": [
              [
                75.0,
                48.1
              ],
              [
                77.5,
                48.1
              ],
              [
                77.5,
                51.1
              ],
              [
                75.0,
                51.1
              ]
            ],
            "x": 76.3,
            "y": 49.6,
            "width": 2.5,
            "height": 3.0,
            "shape": "rect",
            "description": "Contains digestive enzymes to break down waste materials, cellular debris, and foreign invaders.",
            "hierarchyLevel": 3,
            "parentZoneId": "zone_cytoplasm"
          },
          {
            "id": "zone_peroxisome",
            "label": "Peroxisome",
            "points": [
              [
                46.8,
                34.0
              ],
              [
                48.8,
                34.0
              ],
              [
                48.8,
                36.0
              ],
              [
                46.8,
                36.0
              ]
            ],
            "x": 47.8,
            "y": 35.0,
            "width": 1.9,
            "height": 1.9,
            "shape": "rect",
            "description": "Involved in metabolic processes, including fatty acid breakdown and detoxification of harmful substances, producing hydrogen peroxide.",
            "hierarchyLevel": 3,
            "parentZoneId": "zone_cytoplasm"
          },
          {
            "id": "zone_centrosome",
            "label": "Centrosome",
            "points": [
              [
                36.4,
                32.3
              ],
              [
                34.4,
                38.1
              ],
              [
                33.6,
                41.2
              ],
              [
                34.7,
                42.2
              ],
              [
                35.9,
                42.5
              ],
              [
                36.1,
                41.1
              ],
              [
                36.7,
                40.4
              ],
              [
                36.8,
                40.7
              ],
              [
                36.4,
                42.8
              ],
              [
                37.4,
                44.0
              ],
              [
                38.3,
                44.1
              ],
              [
                38.8,
                43.5
              ],
              [
                40.3,
                38.5
              ],
              [
                41.2,
                36.6
              ],
              [
                41.3,
                35.3
              ],
              [
                40.5,
                34.4
              ],
              [
                39.4,
                34.1
              ],
              [
                38.5,
                35.4
              ],
              [
                38.1,
                34.8
              ],
              [
                38.5,
                33.8
              ],
              [
                37.6,
                32.8
              ]
            ],
            "x": 37.7,
            "y": 38.5,
            "radius": 6.3,
            "shape": "polygon",
            "center": {
              "x": 37.7,
              "y": 38.5
            },
            "description": "The main microtubule-organizing center in animal cells, crucial for cell division and cytoskeleton organization.",
            "hierarchyLevel": 3,
            "parentZoneId": "zone_cytoplasm",
            "childZoneIds": [
              "zone_centriole"
            ]
          },
          {
            "id": "zone_centriole",
            "label": "Centriole",
            "points": [
              [
                36.5,
                34.0
              ],
              [
                41.7,
                34.0
              ],
              [
                41.7,
                44.0
              ],
              [
                36.5,
                44.0
              ]
            ],
            "x": 39.1,
            "y": 39.0,
            "width": 5.2,
            "height": 10.0,
            "shape": "rect",
            "description": "A cylindrical organelle within the centrosome, involved in the formation of spindle fibers during cell division.",
            "hierarchyLevel": 4,
            "parentZoneId": "zone_centrosome"
          },
          {
            "id": "zone_vacuole",
            "label": "Vacuole",
            "points": [
              [
                34.2,
                77.0
              ],
              [
                35.8,
                77.0
              ],
              [
                35.8,
                78.6
              ],
              [
                34.2,
                78.6
              ]
            ],
            "x": 35.0,
            "y": 77.8,
            "width": 1.5,
            "height": 1.7,
            "shape": "rect",
            "description": "Primarily involved in storage of water, nutrients, and waste products; typically small and temporary in animal cells.",
            "hierarchyLevel": 3,
            "parentZoneId": "zone_cytoplasm"
          }
        ],
        "labels": [
          {
            "id": "label_s1_0",
            "text": "Cell Membrane",
            "correctZoneId": "zone_cell_membrane"
          },
          {
            "id": "label_s1_1",
            "text": "Cytoplasm",
            "correctZoneId": "zone_cytoplasm"
          },
          {
            "id": "label_s1_2",
            "text": "Nucleus",
            "correctZoneId": "zone_nucleus"
          },
          {
            "id": "label_s1_3",
            "text": "Mitochondrion",
            "correctZoneId": "zone_mitochondrion"
          },
          {
            "id": "label_s1_4",
            "text": "Golgi Apparatus",
            "correctZoneId": "zone_golgi_apparatus"
          },
          {
            "id": "label_s1_5",
            "text": "Endoplasmic Reticulum",
            "correctZoneId": "zone_endoplasmic_reticulum"
          },
          {
            "id": "label_s1_6",
            "text": "Lysosome",
            "correctZoneId": "zone_lysosome"
          },
          {
            "id": "label_s1_7",
            "text": "Peroxisome",
            "correctZoneId": "zone_peroxisome"
          },
          {
            "id": "label_s1_8",
            "text": "Centrosome",
            "correctZoneId": "zone_centrosome"
          },
          {
            "id": "label_s1_9",
            "text": "Centriole",
            "correctZoneId": "zone_centriole"
          },
          {
            "id": "label_s1_10",
            "text": "Vacuole",
            "correctZoneId": "zone_vacuole"
          }
        ],
        "distractorLabels": [
          {
            "id": "distractor_s1_0",
            "text": "Cell Wall",
            "explanation": "This is not part of the diagram.",
            "isDistractor": true
          },
          {
            "id": "distractor_s1_1",
            "text": "Chloroplast",
            "explanation": "This is not part of the diagram.",
            "isDistractor": true
          },
          {
            "id": "distractor_s1_2",
            "text": "Large Central Vacuole",
            "explanation": "This is not part of the diagram.",
            "isDistractor": true
          }
        ],
        "max_score": 275,
        "mechanics": [
          {
            "type": "drag_drop",
            "config": {
              "instruction_text": "Our first view of the animal cell reveals many vital structures. Drag and drop the correct label onto each highlighted organelle to identify it."
            },
            "scoring": {
              "strategy": "per_correct",
              "points_per_correct": 10,
              "max_score": 110,
              "partial_credit": true
            },
            "feedback": {
              "on_correct": "Excellent! You've correctly identified the {label_name}.",
              "on_incorrect": "Not quite. The {label_name} belongs to a different part of the cell. Take another look at its structure and location.",
              "on_completion": "Fantastic work! You've successfully identified all the major components of the animal cell. Now let's explore their functions!",
              "misconceptions": [
                {
                  "trigger_label": "wrong_zone_Lysosome_placed_Peroxisome",
                  "message": "It's easy to confuse these! Remember, lysosomes are for waste breakdown and recycling, while peroxisomes are specialized in detoxifying harmful substances and breaking down fatty acids.",
                  "severity": "medium"
                },
                {
                  "trigger_label": "wrong_zone_Peroxisome_placed_Lysosome",
                  "message": "It's easy to confuse these! Remember, lysosomes are for waste breakdown and recycling, while peroxisomes are specialized in detoxifying harmful substances and breaking down fatty acids.",
                  "severity": "medium"
                },
                {
                  "trigger_label": "wrong_zone_Endoplasmic Reticulum_placed_Golgi Apparatus",
                  "message": "While both are involved in protein processing, the Endoplasmic Reticulum is where proteins and lipids are synthesized, and the Golgi Apparatus modifies, sorts, and packages them for delivery.",
                  "severity": "medium"
                },
                {
                  "trigger_label": "wrong_zone_Golgi Apparatus_placed_Endoplasmic Reticulum",
                  "message": "While both are involved in protein processing, the Endoplasmic Reticulum is where proteins and lipids are synthesized, and the Golgi Apparatus modifies, sorts, and packages them for delivery.",
                  "severity": "medium"
                }
              ]
            }
          },
          {
            "type": "description_matching",
            "config": {
              "instruction_text": "Now that you've successfully identified the major organelles, match each one to its primary function to deepen your understanding of their roles within the cell."
            },
            "scoring": {
              "strategy": "per_correct",
              "points_per_correct": 15,
              "max_score": 165,
              "partial_credit": true
            },
            "feedback": {
              "on_correct": "Spot on! That description perfectly matches the function of the {organelle_name}.",
              "on_incorrect": "Not quite. Re-evaluate the description and the organelle's primary role. Each organelle has a unique and vital function.",
              "on_completion": "Outstanding! You've accurately matched all the organelles with their descriptions, demonstrating a strong understanding of their roles. Remember, these organelles work together in a highly coordinated manner, forming complex pathways and systems to maintain cellular life and carry out specific tasks!",
              "misconceptions": [
                {
                  "trigger_label": "mismatch_Lysosome_Peroxisome",
                  "message": "Careful with these two! Lysosomes are the cell's recycling centers, breaking down waste and cellular debris. Peroxisomes, on the other hand, are crucial for detoxification and breaking down fatty acids.",
                  "severity": "medium"
                },
                {
                  "trigger_label": "mismatch_Peroxisome_Lysosome",
                  "message": "Careful with these two! Lysosomes are the cell's recycling centers, breaking down waste and cellular debris. Peroxisomes, on the other hand, are crucial for detoxification and breaking down fatty acids.",
                  "severity": "medium"
                },
                {
                  "trigger_label": "mismatch_Endoplasmic Reticulum_Golgi Apparatus",
                  "message": "While both are part of the endomembrane system, the Endoplasmic Reticulum is primarily involved in synthesis and transport, whereas the Golgi Apparatus is the cell's 'post office' for modifying, sorting, and packaging.",
                  "severity": "medium"
                },
                {
                  "trigger_label": "mismatch_Golgi Apparatus_Endoplasmic Reticulum",
                  "message": "While both are part of the endomembrane system, the Endoplasmic Reticulum is primarily involved in synthesis and transport, whereas the Golgi Apparatus is the cell's 'post office' for modifying, sorting, and packaging.",
                  "severity": "medium"
                }
              ]
            }
          }
        ],
        "mode_transitions": [
          {
            "from": "drag_drop",
            "to": "description_matching",
            "trigger": "all_zones_labeled",
            "animation": "fade"
          }
        ],
        "tasks": [],
        "interaction_mode": "drag_drop",
        "dragDropConfig": {
          "leader_line_style": "none",
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
            "zone_cell_membrane": "Regulates the passage of substances into and out of the cell, maintaining cell integrity and mediating cell-cell communication.",
            "zone_cytoplasm": "The jelly-like substance filling the cell, providing a medium for organelles and facilitating many metabolic reactions.",
            "zone_nucleus": "Houses the cell's genetic material (DNA) and controls cell growth, metabolism, and reproduction by regulating gene expression.",
            "zone_mitochondrion": "Generates most of the cell's supply of adenosine triphosphate (ATP), the primary energy currency of the cell.",
            "zone_golgi_apparatus": "Modifies, sorts, and packages proteins and lipids for secretion or delivery to other organelles.",
            "zone_endoplasmic_reticulum": "A network of membranes involved in protein and lipid synthesis, detoxification, and calcium storage.",
            "zone_lysosome": "Contains digestive enzymes to break down waste materials, cellular debris, and foreign invaders.",
            "zone_peroxisome": "Involved in metabolic processes, including fatty acid breakdown and detoxification of harmful substances, producing hydrogen peroxide.",
            "zone_centrosome": "The main microtubule-organizing center in animal cells, crucial for cell division and cytoskeleton organization.",
            "zone_centriole": "A cylindrical organelle within the centrosome, involved in the formation of spindle fibers during cell division.",
            "zone_vacuole": "Primarily involved in storage of water, nutrients, and waste products; typically small and temporary in animal cells."
          },
          "mode": "click_zone",
          "distractor_descriptions": [
            "Site of photosynthesis, converting light energy into chemical energy.",
            "Provides rigid structural support and protection to the cell, found outside the cell membrane.",
            "Responsible for the synthesis of all proteins in the cell."
          ],
          "show_connecting_lines": true,
          "defer_evaluation": false,
          "description_panel_position": "right"
        }
      },
      {
        "scene_id": "scene_2",
        "scene_number": 2,
        "title": "Unveiling the Nucleus",
        "narrative_intro": "Let's zoom in on the cell's control center: the Nucleus. It's more complex than it appears! Label its distinct parts and then match them to their critical functions.",
        "learning_goal": "Identify and describe the functions of the nucleus and its internal structures.",
        "diagram": {
          "assetPrompt": "A highly magnified, detailed scientific diagram of an animal cell nucleus. Clearly show the double-membraned nuclear envelope with visible nuclear pores, and a distinct, darker nucleolus within the nucleus. The surrounding cytoplasm should be subtly indicated but not detailed, emphasizing the nucleus itself. The diagram should be clean and ready for interactive labeling.",
          "zones": [
            {
              "id": "zone_nucleus",
              "label": "Nucleus",
              "points": [
                [
                  51.5,
                  38.8
                ],
                [
                  48.3,
                  40.3
                ],
                [
                  46.3,
                  42.8
                ],
                [
                  44.6,
                  47.7
                ],
                [
                  44.5,
                  52.9
                ],
                [
                  45.7,
                  57.8
                ],
                [
                  48.3,
                  57.7
                ],
                [
                  47.9,
                  59.1
                ],
                [
                  48.7,
                  60.0
                ],
                [
                  52.8,
                  61.1
                ],
                [
                  55.8,
                  59.7
                ],
                [
                  58.3,
                  56.7
                ],
                [
                  54.0,
                  54.1
                ],
                [
                  53.6,
                  53.2
                ],
                [
                  54.3,
                  52.9
                ],
                [
                  58.9,
                  55.4
                ],
                [
                  59.9,
                  53.3
                ],
                [
                  60.1,
                  49.8
                ],
                [
                  59.4,
                  48.4
                ],
                [
                  59.7,
                  46.9
                ],
                [
                  59.2,
                  44.9
                ],
                [
                  57.1,
                  41.2
                ],
                [
                  54.8,
                  39.3
                ]
              ],
              "x": 53.2,
              "y": 51.0,
              "radius": 12.3,
              "shape": "polygon",
              "center": {
                "x": 53.2,
                "y": 51.0
              },
              "description": "Houses the cell's genetic material and controls cell activities."
            },
            {
              "id": "zone_nuclear_envelope",
              "label": "Nuclear Envelope",
              "points": [
                [
                  53.3,
                  38.8
                ],
                [
                  50.5,
                  39.0
                ],
                [
                  47.5,
                  41.1
                ],
                [
                  45.7,
                  43.9
                ],
                [
                  44.6,
                  47.6
                ],
                [
                  44.5,
                  52.7
                ],
                [
                  45.6,
                  57.8
                ],
                [
                  48.3,
                  57.7
                ],
                [
                  48.2,
                  59.6
                ],
                [
                  51.5,
                  61.6
                ],
                [
                  55.7,
                  60.0
                ],
                [
                  58.5,
                  56.8
                ],
                [
                  54.0,
                  54.1
                ],
                [
                  53.8,
                  52.9
                ],
                [
                  58.3,
                  55.4
                ],
                [
                  60.2,
                  53.8
                ],
                [
                  60.1,
                  49.7
                ],
                [
                  58.5,
                  43.3
                ],
                [
                  56.1,
                  40.1
                ]
              ],
              "x": 52.4,
              "y": 50.8,
              "radius": 12.0,
              "shape": "polygon",
              "center": {
                "x": 52.4,
                "y": 50.8
              },
              "description": "A double membrane that separates the nucleus from the cytoplasm and regulates molecular traffic."
            },
            {
              "id": "zone_nucleolus",
              "label": "Nucleolus",
              "points": [
                [
                  49.0,
                  47.2
                ],
                [
                  55.5,
                  47.2
                ],
                [
                  55.5,
                  55.3
                ],
                [
                  49.0,
                  55.3
                ]
              ],
              "x": 52.2,
              "y": 51.3,
              "width": 6.5,
              "height": 8.1,
              "shape": "rect",
              "description": "Site of ribosomal RNA synthesis and ribosome assembly."
            }
          ],
          "imageUrl": "https://sciencenotes.org/wp-content/uploads/2023/05/Labeled-Animal-Cell-Diagram.png",
          "assetUrl": "https://sciencenotes.org/wp-content/uploads/2023/05/Labeled-Animal-Cell-Diagram.png"
        },
        "zones": [
          {
            "id": "zone_nucleus",
            "label": "Nucleus",
            "points": [
              [
                51.5,
                38.8
              ],
              [
                48.3,
                40.3
              ],
              [
                46.3,
                42.8
              ],
              [
                44.6,
                47.7
              ],
              [
                44.5,
                52.9
              ],
              [
                45.7,
                57.8
              ],
              [
                48.3,
                57.7
              ],
              [
                47.9,
                59.1
              ],
              [
                48.7,
                60.0
              ],
              [
                52.8,
                61.1
              ],
              [
                55.8,
                59.7
              ],
              [
                58.3,
                56.7
              ],
              [
                54.0,
                54.1
              ],
              [
                53.6,
                53.2
              ],
              [
                54.3,
                52.9
              ],
              [
                58.9,
                55.4
              ],
              [
                59.9,
                53.3
              ],
              [
                60.1,
                49.8
              ],
              [
                59.4,
                48.4
              ],
              [
                59.7,
                46.9
              ],
              [
                59.2,
                44.9
              ],
              [
                57.1,
                41.2
              ],
              [
                54.8,
                39.3
              ]
            ],
            "x": 53.2,
            "y": 51.0,
            "radius": 12.3,
            "shape": "polygon",
            "center": {
              "x": 53.2,
              "y": 51.0
            },
            "description": "Houses the cell's genetic material and controls cell activities."
          },
          {
            "id": "zone_nuclear_envelope",
            "label": "Nuclear Envelope",
            "points": [
              [
                53.3,
                38.8
              ],
              [
                50.5,
                39.0
              ],
              [
                47.5,
                41.1
              ],
              [
                45.7,
                43.9
              ],
              [
                44.6,
                47.6
              ],
              [
                44.5,
                52.7
              ],
              [
                45.6,
                57.8
              ],
              [
                48.3,
                57.7
              ],
              [
                48.2,
                59.6
              ],
              [
                51.5,
                61.6
              ],
              [
                55.7,
                60.0
              ],
              [
                58.5,
                56.8
              ],
              [
                54.0,
                54.1
              ],
              [
                53.8,
                52.9
              ],
              [
                58.3,
                55.4
              ],
              [
                60.2,
                53.8
              ],
              [
                60.1,
                49.7
              ],
              [
                58.5,
                43.3
              ],
              [
                56.1,
                40.1
              ]
            ],
            "x": 52.4,
            "y": 50.8,
            "radius": 12.0,
            "shape": "polygon",
            "center": {
              "x": 52.4,
              "y": 50.8
            },
            "description": "A double membrane that separates the nucleus from the cytoplasm and regulates molecular traffic."
          },
          {
            "id": "zone_nucleolus",
            "label": "Nucleolus",
            "points": [
              [
                49.0,
                47.2
              ],
              [
                55.5,
                47.2
              ],
              [
                55.5,
                55.3
              ],
              [
                49.0,
                55.3
              ]
            ],
            "x": 52.2,
            "y": 51.3,
            "width": 6.5,
            "height": 8.1,
            "shape": "rect",
            "description": "Site of ribosomal RNA synthesis and ribosome assembly."
          }
        ],
        "labels": [
          {
            "id": "label_s2_0",
            "text": "Nucleus",
            "correctZoneId": "zone_nucleus"
          },
          {
            "id": "label_s2_1",
            "text": "Nuclear Envelope",
            "correctZoneId": "zone_nuclear_envelope"
          },
          {
            "id": "label_s2_2",
            "text": "Nucleolus",
            "correctZoneId": "zone_nucleolus"
          }
        ],
        "distractorLabels": [
          {
            "id": "distractor_s2_0",
            "text": "Cell Wall",
            "explanation": "This is not part of the diagram.",
            "isDistractor": true
          },
          {
            "id": "distractor_s2_1",
            "text": "Chloroplast",
            "explanation": "This is not part of the diagram.",
            "isDistractor": true
          },
          {
            "id": "distractor_s2_2",
            "text": "Large Central Vacuole",
            "explanation": "This is not part of the diagram.",
            "isDistractor": true
          }
        ],
        "max_score": 75,
        "mechanics": [
          {
            "type": "drag_drop",
            "config": {
              "instruction_text": "Drag and drop the labels to correctly identify the main components of the animal cell nucleus."
            },
            "scoring": {
              "strategy": "per_correct",
              "points_per_correct": 10,
              "max_score": 30,
              "partial_credit": true
            },
            "feedback": {
              "on_correct": "Excellent! You've correctly identified that part of the nucleus.",
              "on_incorrect": "Not quite right. Take another look at the structure and its name. Remember what each part does.",
              "on_completion": "Fantastic! You've successfully labeled all the key parts of the nucleus!",
              "misconceptions": [
                {
                  "trigger_label": "incorrect_placement_Nucleus",
                  "message": "Remember, the Nucleus is the entire central organelle housing the genetic material and controlling cell activities, not just a specific part within it.",
                  "severity": "medium"
                },
                {
                  "trigger_label": "incorrect_placement_Nuclear Envelope",
                  "message": "The Nuclear Envelope is the protective double membrane surrounding the nucleus, regulating what enters and exits.",
                  "severity": "medium"
                },
                {
                  "trigger_label": "incorrect_placement_Nucleolus",
                  "message": "The Nucleolus is a dense structure inside the nucleus, crucial for ribosomal RNA synthesis and ribosome assembly.",
                  "severity": "medium"
                },
                {
                  "trigger_label": "distractor_placed_in_nucleus_zone",
                  "message": "Careful! The Mitochondrion and Cytoplasm are distinct from the nucleus. Focus on the structures *within* or *directly surrounding* the nucleus.",
                  "severity": "low"
                }
              ]
            }
          },
          {
            "type": "description_matching",
            "config": {
              "instruction_text": "Now that you've labeled the parts of the nucleus, match each structure to its primary function by clicking the description and then the corresponding part on the diagram."
            },
            "scoring": {
              "strategy": "per_correct",
              "points_per_correct": 15,
              "max_score": 45,
              "partial_credit": true
            },
            "feedback": {
              "on_correct": "Spot on! That description perfectly matches its function.",
              "on_incorrect": "Close, but not quite. Re-evaluate the specific role of each part. What does this structure *do*?",
              "on_completion": "Outstanding! You've accurately described the functions of all the nucleus's components!",
              "misconceptions": [
                {
                  "trigger_label": "confusing_nucleus_parts_functions",
                  "message": "Each part of the nucleus, like the Nuclear Envelope and Nucleolus, has distinct structural features and highly specific functions crucial for cellular processes. Don't confuse their roles!",
                  "severity": "medium"
                }
              ]
            }
          }
        ],
        "mode_transitions": [
          {
            "from": "drag_drop",
            "to": "description_matching",
            "trigger": "all_zones_labeled",
            "animation": "fade"
          }
        ],
        "tasks": [],
        "interaction_mode": "drag_drop",
        "dragDropConfig": {
          "leader_line_style": "none",
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
            "zone_nucleus": "Houses the cell's genetic material and controls cell activities.",
            "zone_nuclear_envelope": "A double membrane that separates the nucleus from the cytoplasm and regulates molecular traffic.",
            "zone_nucleolus": "Site of ribosomal RNA synthesis and ribosome assembly."
          },
          "mode": "click_zone",
          "distractor_descriptions": [],
          "show_connecting_lines": true,
          "defer_evaluation": false,
          "description_panel_position": "right"
        }
      },
      {
        "scene_id": "scene_3",
        "scene_number": 3,
        "title": "The Endoplasmic Reticulum Network",
        "narrative_intro": "Now, let's explore the extensive Endoplasmic Reticulum network. It comes in two forms, each with unique roles, and works closely with ribosomes. Identify these structures and their specific functions.",
        "learning_goal": "Differentiate and describe the functions of the Rough ER, Smooth ER, and Ribosomes.",
        "diagram": {
          "assetPrompt": "A highly magnified, detailed scientific diagram of the endoplasmic reticulum network within a eukaryotic cell. Clearly depicts the interconnected network of membranes, distinguishing between the Rough Endoplasmic Reticulum (RER) with numerous small dots representing ribosomes on its surface, and the Smooth Endoplasmic Reticulum (SER), which lacks ribosomes and appears tubular. The ribosomes on the RER should be clearly visible and distinct.",
          "zones": [
            {
              "id": "zone_rough_endoplasmic_reticulum",
              "label": "Rough Endoplasmic Reticulum",
              "points": [
                [
                  28.1,
                  48.3
                ],
                [
                  21.9,
                  52.5
                ],
                [
                  12.8,
                  61.3
                ],
                [
                  4.6,
                  72.6
                ],
                [
                  4.7,
                  73.7
                ],
                [
                  6.1,
                  73.6
                ],
                [
                  12.1,
                  65.3
                ],
                [
                  13.3,
                  66.1
                ],
                [
                  9.1,
                  72.0
                ],
                [
                  9.1,
                  73.7
                ],
                [
                  6.5,
                  76.0
                ],
                [
                  7.9,
                  76.9
                ],
                [
                  10.8,
                  74.4
                ],
                [
                  11.4,
                  77.3
                ],
                [
                  9.0,
                  82.1
                ],
                [
                  10.1,
                  82.1
                ],
                [
                  11.6,
                  79.1
                ],
                [
                  14.0,
                  78.4
                ],
                [
                  12.5,
                  84.7
                ],
                [
                  18.8,
                  78.6
                ],
                [
                  21.1,
                  79.6
                ],
                [
                  21.8,
                  78.8
                ],
                [
                  21.1,
                  76.6
                ],
                [
                  24.7,
                  74.7
                ],
                [
                  24.8,
                  71.8
                ],
                [
                  28.7,
                  68.9
                ],
                [
                  28.1,
                  67.5
                ],
                [
                  29.2,
                  65.3
                ],
                [
                  28.2,
                  59.8
                ],
                [
                  29.6,
                  53.2
                ]
              ],
              "x": 16.4,
              "y": 71.5,
              "radius": 26.0,
              "shape": "polygon",
              "center": {
                "x": 16.4,
                "y": 71.5
              },
              "description": "Synthesizes and modifies proteins destined for secretion or membranes."
            },
            {
              "id": "zone_smooth_endoplasmic_reticulum",
              "label": "Smooth Endoplasmic Reticulum",
              "points": [
                [
                  43.2,
                  22.9
                ],
                [
                  39.1,
                  28.8
                ],
                [
                  33.8,
                  31.5
                ],
                [
                  35.0,
                  39.0
                ],
                [
                  27.7,
                  46.3
                ],
                [
                  29.8,
                  53.1
                ],
                [
                  28.0,
                  58.7
                ],
                [
                  29.2,
                  66.1
                ],
                [
                  28.2,
                  67.5
                ],
                [
                  29.6,
                  73.4
                ],
                [
                  34.9,
                  77.1
                ],
                [
                  35.8,
                  81.0
                ],
                [
                  39.9,
                  79.6
                ],
                [
                  43.5,
                  74.9
                ],
                [
                  48.1,
                  77.5
                ],
                [
                  54.6,
                  76.2
                ],
                [
                  54.6,
                  73.5
                ],
                [
                  56.5,
                  73.4
                ],
                [
                  57.1,
                  71.1
                ],
                [
                  55.4,
                  69.2
                ],
                [
                  57.3,
                  60.8
                ],
                [
                  54.9,
                  57.9
                ],
                [
                  54.1,
                  52.9
                ],
                [
                  55.7,
                  45.6
                ],
                [
                  50.9,
                  39.7
                ],
                [
                  45.5,
                  39.7
                ],
                [
                  46.7,
                  35.9
                ],
                [
                  44.8,
                  34.6
                ],
                [
                  48.7,
                  33.2
                ],
                [
                  49.6,
                  31.0
                ],
                [
                  49.0,
                  29.1
                ],
                [
                  46.1,
                  28.4
                ],
                [
                  46.1,
                  25.9
                ],
                [
                  41.5,
                  26.3
                ]
              ],
              "x": 44.0,
              "y": 52.4,
              "radius": 29.8,
              "shape": "polygon",
              "center": {
                "x": 44.0,
                "y": 52.4
              },
              "description": "Involved in lipid synthesis, detoxification, and calcium storage."
            },
            {
              "id": "zone_ribosome",
              "label": "Ribosome",
              "points": [
                [
                  99.9,
                  29.5
                ],
                [
                  75.1,
                  19.4
                ],
                [
                  43.2,
                  21.8
                ],
                [
                  45.4,
                  27.9
                ],
                [
                  40.8,
                  26.5
                ],
                [
                  39.1,
                  34.7
                ],
                [
                  36.4,
                  32.4
                ],
                [
                  39.8,
                  28.8
                ],
                [
                  34.2,
                  31.1
                ],
                [
                  35.5,
                  38.9
                ],
                [
                  28.1,
                  48.4
                ],
                [
                  20.1,
                  48.4
                ],
                [
                  23.3,
                  51.9
                ],
                [
                  13.7,
                  59.5
                ],
                [
                  7.4,
                  56.8
                ],
                [
                  13.3,
                  63.3
                ],
                [
                  4.6,
                  73.1
                ],
                [
                  11.2,
                  68.2
                ],
                [
                  7.1,
                  75.8
                ],
                [
                  10.9,
                  74.4
                ],
                [
                  9.4,
                  82.1
                ],
                [
                  14.2,
                  78.4
                ],
                [
                  12.7,
                  84.5
                ],
                [
                  29.0,
                  68.6
                ],
                [
                  36.2,
                  80.8
                ],
                [
                  42.1,
                  74.4
                ],
                [
                  47.7,
                  76.6
                ],
                [
                  37.4,
                  73.6
                ],
                [
                  37.2,
                  69.3
                ],
                [
                  50.6,
                  71.9
                ],
                [
                  48.1,
                  66.4
                ],
                [
                  55.6,
                  63.7
                ],
                [
                  56.4,
                  67.9
                ],
                [
                  52.5,
                  66.4
                ],
                [
                  57.8,
                  74.4
                ],
                [
                  49.5,
                  76.9
                ],
                [
                  80.0,
                  79.4
                ],
                [
                  82.2,
                  70.4
                ],
                [
                  86.7,
                  69.2
                ],
                [
                  84.5,
                  63.0
                ],
                [
                  89.4,
                  62.3
                ],
                [
                  85.1,
                  52.5
                ],
                [
                  92.7,
                  46.6
                ],
                [
                  86.9,
                  42.8
                ],
                [
                  92.5,
                  43.9
                ],
                [
                  89.0,
                  37.6
                ]
              ],
              "x": 46.4,
              "y": 57.7,
              "radius": 60.5,
              "shape": "polygon",
              "center": {
                "x": 46.4,
                "y": 57.7
              },
              "description": "Primary site of protein synthesis (translation)."
            }
          ],
          "imageUrl": "/api/assets/demo/ab5c9d19-c947-483f-a40a-d5f1c71e7a65/diagram_scene_3.png",
          "assetUrl": "/api/assets/demo/ab5c9d19-c947-483f-a40a-d5f1c71e7a65/diagram_scene_3.png"
        },
        "zones": [
          {
            "id": "zone_rough_endoplasmic_reticulum",
            "label": "Rough Endoplasmic Reticulum",
            "points": [
              [
                28.1,
                48.3
              ],
              [
                21.9,
                52.5
              ],
              [
                12.8,
                61.3
              ],
              [
                4.6,
                72.6
              ],
              [
                4.7,
                73.7
              ],
              [
                6.1,
                73.6
              ],
              [
                12.1,
                65.3
              ],
              [
                13.3,
                66.1
              ],
              [
                9.1,
                72.0
              ],
              [
                9.1,
                73.7
              ],
              [
                6.5,
                76.0
              ],
              [
                7.9,
                76.9
              ],
              [
                10.8,
                74.4
              ],
              [
                11.4,
                77.3
              ],
              [
                9.0,
                82.1
              ],
              [
                10.1,
                82.1
              ],
              [
                11.6,
                79.1
              ],
              [
                14.0,
                78.4
              ],
              [
                12.5,
                84.7
              ],
              [
                18.8,
                78.6
              ],
              [
                21.1,
                79.6
              ],
              [
                21.8,
                78.8
              ],
              [
                21.1,
                76.6
              ],
              [
                24.7,
                74.7
              ],
              [
                24.8,
                71.8
              ],
              [
                28.7,
                68.9
              ],
              [
                28.1,
                67.5
              ],
              [
                29.2,
                65.3
              ],
              [
                28.2,
                59.8
              ],
              [
                29.6,
                53.2
              ]
            ],
            "x": 16.4,
            "y": 71.5,
            "radius": 26.0,
            "shape": "polygon",
            "center": {
              "x": 16.4,
              "y": 71.5
            },
            "description": "Synthesizes and modifies proteins destined for secretion or membranes."
          },
          {
            "id": "zone_smooth_endoplasmic_reticulum",
            "label": "Smooth Endoplasmic Reticulum",
            "points": [
              [
                43.2,
                22.9
              ],
              [
                39.1,
                28.8
              ],
              [
                33.8,
                31.5
              ],
              [
                35.0,
                39.0
              ],
              [
                27.7,
                46.3
              ],
              [
                29.8,
                53.1
              ],
              [
                28.0,
                58.7
              ],
              [
                29.2,
                66.1
              ],
              [
                28.2,
                67.5
              ],
              [
                29.6,
                73.4
              ],
              [
                34.9,
                77.1
              ],
              [
                35.8,
                81.0
              ],
              [
                39.9,
                79.6
              ],
              [
                43.5,
                74.9
              ],
              [
                48.1,
                77.5
              ],
              [
                54.6,
                76.2
              ],
              [
                54.6,
                73.5
              ],
              [
                56.5,
                73.4
              ],
              [
                57.1,
                71.1
              ],
              [
                55.4,
                69.2
              ],
              [
                57.3,
                60.8
              ],
              [
                54.9,
                57.9
              ],
              [
                54.1,
                52.9
              ],
              [
                55.7,
                45.6
              ],
              [
                50.9,
                39.7
              ],
              [
                45.5,
                39.7
              ],
              [
                46.7,
                35.9
              ],
              [
                44.8,
                34.6
              ],
              [
                48.7,
                33.2
              ],
              [
                49.6,
                31.0
              ],
              [
                49.0,
                29.1
              ],
              [
                46.1,
                28.4
              ],
              [
                46.1,
                25.9
              ],
              [
                41.5,
                26.3
              ]
            ],
            "x": 44.0,
            "y": 52.4,
            "radius": 29.8,
            "shape": "polygon",
            "center": {
              "x": 44.0,
              "y": 52.4
            },
            "description": "Involved in lipid synthesis, detoxification, and calcium storage."
          },
          {
            "id": "zone_ribosome",
            "label": "Ribosome",
            "points": [
              [
                99.9,
                29.5
              ],
              [
                75.1,
                19.4
              ],
              [
                43.2,
                21.8
              ],
              [
                45.4,
                27.9
              ],
              [
                40.8,
                26.5
              ],
              [
                39.1,
                34.7
              ],
              [
                36.4,
                32.4
              ],
              [
                39.8,
                28.8
              ],
              [
                34.2,
                31.1
              ],
              [
                35.5,
                38.9
              ],
              [
                28.1,
                48.4
              ],
              [
                20.1,
                48.4
              ],
              [
                23.3,
                51.9
              ],
              [
                13.7,
                59.5
              ],
              [
                7.4,
                56.8
              ],
              [
                13.3,
                63.3
              ],
              [
                4.6,
                73.1
              ],
              [
                11.2,
                68.2
              ],
              [
                7.1,
                75.8
              ],
              [
                10.9,
                74.4
              ],
              [
                9.4,
                82.1
              ],
              [
                14.2,
                78.4
              ],
              [
                12.7,
                84.5
              ],
              [
                29.0,
                68.6
              ],
              [
                36.2,
                80.8
              ],
              [
                42.1,
                74.4
              ],
              [
                47.7,
                76.6
              ],
              [
                37.4,
                73.6
              ],
              [
                37.2,
                69.3
              ],
              [
                50.6,
                71.9
              ],
              [
                48.1,
                66.4
              ],
              [
                55.6,
                63.7
              ],
              [
                56.4,
                67.9
              ],
              [
                52.5,
                66.4
              ],
              [
                57.8,
                74.4
              ],
              [
                49.5,
                76.9
              ],
              [
                80.0,
                79.4
              ],
              [
                82.2,
                70.4
              ],
              [
                86.7,
                69.2
              ],
              [
                84.5,
                63.0
              ],
              [
                89.4,
                62.3
              ],
              [
                85.1,
                52.5
              ],
              [
                92.7,
                46.6
              ],
              [
                86.9,
                42.8
              ],
              [
                92.5,
                43.9
              ],
              [
                89.0,
                37.6
              ]
            ],
            "x": 46.4,
            "y": 57.7,
            "radius": 60.5,
            "shape": "polygon",
            "center": {
              "x": 46.4,
              "y": 57.7
            },
            "description": "Primary site of protein synthesis (translation)."
          }
        ],
        "labels": [
          {
            "id": "label_s3_0",
            "text": "Rough Endoplasmic Reticulum",
            "correctZoneId": "zone_rough_endoplasmic_reticulum"
          },
          {
            "id": "label_s3_1",
            "text": "Smooth Endoplasmic Reticulum",
            "correctZoneId": "zone_smooth_endoplasmic_reticulum"
          },
          {
            "id": "label_s3_2",
            "text": "Ribosome",
            "correctZoneId": "zone_ribosome"
          }
        ],
        "distractorLabels": [
          {
            "id": "distractor_s3_0",
            "text": "Cell Wall",
            "explanation": "This is not part of the diagram.",
            "isDistractor": true
          },
          {
            "id": "distractor_s3_1",
            "text": "Chloroplast",
            "explanation": "This is not part of the diagram.",
            "isDistractor": true
          },
          {
            "id": "distractor_s3_2",
            "text": "Large Central Vacuole",
            "explanation": "This is not part of the diagram.",
            "isDistractor": true
          }
        ],
        "max_score": 75,
        "mechanics": [
          {
            "type": "drag_drop",
            "config": {
              "instruction_text": "Identify the key structures of the endoplasmic reticulum network by dragging the correct labels to their corresponding zones on the diagram."
            },
            "scoring": {
              "strategy": "per_correct",
              "points_per_correct": 10,
              "max_score": 30,
              "partial_credit": true
            },
            "feedback": {
              "on_correct": "Excellent! That's the correct location for this component.",
              "on_incorrect": "Not quite. Consider the specific features or functions of this organelle to find its correct place.",
              "on_completion": "Fantastic! You've correctly identified and placed all the key components of the Endoplasmic Reticulum network.",
              "misconceptions": [
                {
                  "trigger_label": "RER_SER_placement_confusion",
                  "message": "It looks like you might be mixing up the Rough and Smooth ER. Remember, the 'rough' part comes from ribosomes, which are involved in protein synthesis, while the 'smooth' part handles lipids and detoxification.",
                  "severity": "high"
                },
                {
                  "trigger_label": "Ribosome_misplacement",
                  "message": "Ribosomes are the protein factories of the cell, found both free in the cytoplasm and attached to the Rough ER. Where would they best fit in this diagram?",
                  "severity": "medium"
                }
              ]
            }
          },
          {
            "type": "description_matching",
            "config": {
              "instruction_text": "Now that you've identified the structures, match each one to its primary function within the cell by dragging the description to the correct labeled zone."
            },
            "scoring": {
              "strategy": "per_correct",
              "points_per_correct": 15,
              "max_score": 45,
              "partial_credit": true
            },
            "feedback": {
              "on_correct": "That's a perfect match! You've correctly identified the function.",
              "on_incorrect": "Not quite. Re-evaluate the specific functions. Which organelle is responsible for this particular task?",
              "on_completion": "Outstanding! You've accurately described the functions of each part of the ER network and ribosomes.",
              "misconceptions": [
                {
                  "trigger_label": "RER_SER_function_confusion",
                  "message": "You're close, but let's clarify the roles of the Rough and Smooth ER. The Rough ER is the protein factory, while the Smooth ER is crucial for lipid synthesis and detoxification.",
                  "severity": "high"
                },
                {
                  "trigger_label": "Ribosome_function_confusion",
                  "message": "Don't forget the primary role of ribosomes! They are the fundamental sites for protein synthesis, translating genetic instructions into proteins.",
                  "severity": "medium"
                }
              ]
            }
          }
        ],
        "mode_transitions": [
          {
            "from": "drag_drop",
            "to": "click_zone",
            "trigger": "all_zones_labeled",
            "animation": "fade"
          }
        ],
        "tasks": [],
        "interaction_mode": "drag_drop",
        "dragDropConfig": {
          "leader_line_style": "none",
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
            "zone_rough_endoplasmic_reticulum": "Synthesizes and modifies proteins destined for secretion or membranes.",
            "zone_smooth_endoplasmic_reticulum": "Involved in lipid synthesis, detoxification, and calcium storage.",
            "zone_ribosome": "Primary site of protein synthesis (translation)."
          },
          "mode": "click_zone",
          "distractor_descriptions": [],
          "show_connecting_lines": true,
          "defer_evaluation": false,
          "description_panel_position": "right"
        }
      }
    ],
    "total_scenes": 3,
    "total_max_score": 425,
    "estimated_duration_minutes": 12,
    "difficulty_level": "intermediate",
    "progression_type": "linear"
  },
  "zoneGroups": [
    {
      "id": "group_zone_cell_membrane",
      "parentZoneId": "zone_cell_membrane",
      "childZoneIds": [
        "zone_cytoplasm"
      ],
      "revealTrigger": "complete_parent",
      "label": "Cell Membrane"
    },
    {
      "id": "group_zone_cytoplasm",
      "parentZoneId": "zone_cytoplasm",
      "childZoneIds": [
        "zone_nucleus",
        "zone_mitochondrion",
        "zone_endoplasmic_reticulum",
        "zone_golgi_apparatus",
        "zone_lysosome",
        "zone_peroxisome",
        "zone_centrosome",
        "zone_vacuole"
      ],
      "revealTrigger": "complete_parent",
      "label": "Cytoplasm"
    },
    {
      "id": "group_zone_centrosome",
      "parentZoneId": "zone_centrosome",
      "childZoneIds": [
        "zone_centriole"
      ],
      "revealTrigger": "complete_parent",
      "label": "Centrosome"
    }
  ],
  "temporalConstraints": [
    {
      "constraint_type": "after",
      "zone_a": "zone_cytoplasm",
      "zone_b": "zone_cell_membrane",
      "description": "Zone zone_cytoplasm visible after zone_cell_membrane is labeled"
    },
    {
      "constraint_type": "after",
      "zone_a": "zone_nucleus",
      "zone_b": "zone_cytoplasm",
      "description": "Zone zone_nucleus visible after zone_cytoplasm is labeled"
    },
    {
      "constraint_type": "after",
      "zone_a": "zone_mitochondrion",
      "zone_b": "zone_cytoplasm",
      "description": "Zone zone_mitochondrion visible after zone_cytoplasm is labeled"
    },
    {
      "constraint_type": "after",
      "zone_a": "zone_endoplasmic_reticulum",
      "zone_b": "zone_cytoplasm",
      "description": "Zone zone_endoplasmic_reticulum visible after zone_cytoplasm is labeled"
    },
    {
      "constraint_type": "after",
      "zone_a": "zone_golgi_apparatus",
      "zone_b": "zone_cytoplasm",
      "description": "Zone zone_golgi_apparatus visible after zone_cytoplasm is labeled"
    },
    {
      "constraint_type": "after",
      "zone_a": "zone_lysosome",
      "zone_b": "zone_cytoplasm",
      "description": "Zone zone_lysosome visible after zone_cytoplasm is labeled"
    },
    {
      "constraint_type": "after",
      "zone_a": "zone_peroxisome",
      "zone_b": "zone_cytoplasm",
      "description": "Zone zone_peroxisome visible after zone_cytoplasm is labeled"
    },
    {
      "constraint_type": "after",
      "zone_a": "zone_centrosome",
      "zone_b": "zone_cytoplasm",
      "description": "Zone zone_centrosome visible after zone_cytoplasm is labeled"
    },
    {
      "constraint_type": "after",
      "zone_a": "zone_vacuole",
      "zone_b": "zone_cytoplasm",
      "description": "Zone zone_vacuole visible after zone_cytoplasm is labeled"
    },
    {
      "constraint_type": "after",
      "zone_a": "zone_centriole",
      "zone_b": "zone_centrosome",
      "description": "Zone zone_centriole visible after zone_centrosome is labeled"
    }
  ],
  "revealOrder": [
    "zone_cell_membrane",
    "zone_cytoplasm",
    "zone_nucleus",
    "zone_mitochondrion",
    "zone_endoplasmic_reticulum",
    "zone_golgi_apparatus",
    "zone_lysosome",
    "zone_peroxisome",
    "zone_centrosome",
    "zone_centriole",
    "zone_vacuole"
  ],
  "tasks": []
} as any as InteractiveDiagramBlueprint;
