import type { InteractiveDiagramBlueprint } from '../types';

export const sequencingDemo: InteractiveDiagramBlueprint = {
  templateType: 'INTERACTIVE_DIAGRAM',
  title: 'Blood Flow Through the Heart',
  narrativeIntro: 'Blood follows a specific route through the heart and lungs in a continuous cycle. Arrange the steps of blood flow in the correct order from when deoxygenated blood enters the heart to when oxygenated blood is pumped to the body.',
  diagram: {
    assetPrompt: 'Educational diagram showing the steps of blood flow through the heart and lungs, cardiac cycle sequence',
    zones: [],
  },
  labels: [],
  tasks: [
    { id: 't-1', type: 'label_diagram', questionText: 'Arrange the steps of blood flow in the correct order', requiredToProceed: true },
  ],
  animationCues: {
    correctPlacement: 'pulse',
    incorrectPlacement: 'shake',
    allLabeled: 'confetti',
  },
  mechanics: [
    { type: 'sequencing', scoring: { strategy: 'per_zone', points_per_correct: 15, max_score: 90 }, feedback: { on_correct: 'Correct order!', on_incorrect: 'That\'s not quite right. Think about where blood goes after each step.', on_completion: 'You ordered all steps of blood flow correctly!' } },
  ],
  interactionMode: 'sequencing',
  sequenceConfig: {
    sequenceType: 'cyclic',
    items: [
      { id: 'seq-1', content: 'Deoxygenated blood enters the right atrium', description: 'Blood returning from the body enters the heart through the superior and inferior vena cava into the right atrium.', image: '/api/assets/demo/demo_sequencing/items/item_000_deoxygenated_blood_enters_right_atrium.png', icon: '🔵', order_index: 0 },
      { id: 'seq-2', content: 'Blood passes through the tricuspid valve', description: 'The right atrium contracts, pushing blood through the tricuspid valve into the right ventricle.', image: '/api/assets/demo/demo_sequencing/items/item_001_blood_passes_through_tricuspid_valve.png', icon: '🔷', order_index: 1 },
      { id: 'seq-3', content: 'Right ventricle pumps blood to the lungs', description: 'The right ventricle contracts, sending deoxygenated blood through the pulmonary valve into the pulmonary arteries toward the lungs.', image: '/api/assets/demo/demo_sequencing/items/item_002_right_ventricle_pumps_to_lungs.png', icon: '💨', order_index: 2 },
      { id: 'seq-4', content: 'Gas exchange occurs in lung capillaries', description: 'In the lungs, carbon dioxide is released and oxygen is absorbed into the blood through tiny capillaries surrounding the alveoli.', image: '/api/assets/demo/demo_sequencing/items/item_003_gas_exchange_in_lung_capillaries.png', icon: '🫁', order_index: 3 },
      { id: 'seq-5', content: 'Oxygenated blood returns to the left atrium', description: 'Freshly oxygenated blood travels through the pulmonary veins back to the left atrium of the heart.', image: '/api/assets/demo/demo_sequencing/items/item_004_oxygenated_blood_returns_to_left_atrium.png', icon: '🔴', order_index: 4 },
      { id: 'seq-6', content: 'Left ventricle pumps blood to the body', description: 'Blood passes through the mitral valve into the left ventricle, which contracts powerfully to pump oxygenated blood through the aorta to the entire body.', image: '/api/assets/demo/demo_sequencing/items/item_005_left_ventricle_pumps_to_body.png', icon: '❤️', order_index: 5 },
    ],
    correctOrder: ['seq-1', 'seq-2', 'seq-3', 'seq-4', 'seq-5', 'seq-6'],
    allowPartialCredit: true,
    instructionText: 'Drag the steps into the correct order to show how blood flows through the heart and lungs.',
    layout_mode: 'horizontal_timeline',
    interaction_pattern: 'drag_reorder',
    card_type: 'text_with_icon',
    connector_style: 'arrow',
    show_position_numbers: true,
  },
  feedbackMessages: {
    perfect: 'Excellent! You ordered all steps of cardiac blood flow correctly!',
    good: 'Almost there! Remember that blood goes to the lungs before returning to the left side.',
    retry: 'Think about the path: right side → lungs → left side → body. Deoxygenated blood always enters the right atrium first.',
  },
};
