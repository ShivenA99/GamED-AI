import type { InteractiveDiagramBlueprint } from '../types';

export const memoryMatchDemo: InteractiveDiagramBlueprint = {
  templateType: 'INTERACTIVE_DIAGRAM',
  title: 'Match Organs to Their Functions',
  narrativeIntro: 'The human body has many organs, each with a specific function. Flip cards to find matching pairs — match each organ image to its primary function.',
  diagram: {
    assetPrompt: 'Educational illustration of the human body showing major organs, clean medical diagram style',
    zones: [],
  },
  labels: [],
  tasks: [
    { id: 't-1', type: 'label_diagram', questionText: 'Match each organ to its primary function', requiredToProceed: true },
  ],
  animationCues: {
    correctPlacement: 'glow',
    incorrectPlacement: 'fade',
    allLabeled: 'confetti',
  },
  mechanics: [
    { type: 'memory_match', scoring: { strategy: 'per_zone', points_per_correct: 15, max_score: 90 }, feedback: { on_correct: 'Match found!', on_incorrect: 'Not a match — try to remember where each card is.', on_completion: 'All pairs matched! You know your organs well.' } },
  ],
  interactionMode: 'memory_match',
  memoryMatchConfig: {
    pairs: [
      { id: 'pair-heart', front: 'Heart', back: 'Pumps blood throughout the body via rhythmic contractions', frontType: 'image' as const, backType: 'text' as const, explanation: 'The heart is a muscular pump that circulates blood carrying oxygen and nutrients to all tissues.', category: 'circulatory' },
      { id: 'pair-lungs', front: 'Lungs', back: 'Exchange oxygen and carbon dioxide with the atmosphere', frontType: 'image' as const, backType: 'text' as const, explanation: 'The lungs contain tiny air sacs (alveoli) where gas exchange occurs between air and blood.', category: 'respiratory' },
      { id: 'pair-brain', front: 'Brain', back: 'Processes information and controls body functions', frontType: 'image' as const, backType: 'text' as const, explanation: 'The brain is the control center of the nervous system, handling thought, memory, emotion, and motor control.', category: 'nervous' },
      { id: 'pair-liver', front: 'Liver', back: 'Detoxifies blood and produces bile for digestion', frontType: 'image' as const, backType: 'text' as const, explanation: 'The liver filters blood, metabolizes drugs, produces bile, and stores glycogen for energy.', category: 'digestive' },
      { id: 'pair-kidney', front: 'Kidneys', back: 'Filter blood to remove waste and regulate fluid balance', frontType: 'image' as const, backType: 'text' as const, explanation: 'The kidneys filter about 200 liters of blood daily, producing urine to remove waste products.', category: 'excretory' },
      { id: 'pair-stomach', front: 'Stomach', back: 'Breaks down food using acid and enzymes', frontType: 'image' as const, backType: 'text' as const, explanation: 'The stomach uses hydrochloric acid and pepsin to chemically digest food into chyme.', category: 'digestive' },
    ],
    gridSize: [4, 3],
    flipDurationMs: 400,
    showAttemptsCounter: true,
    instructions: 'Flip two cards at a time to find matching organ-function pairs. Try to remember card positions to minimize attempts!',
    game_variant: 'classic',
    match_type: 'image_to_label',
    card_back_style: 'gradient',
    matched_card_behavior: 'checkmark',
    show_explanation_on_match: true,
  },
  feedbackMessages: {
    perfect: 'Incredible memory! You matched all organs with minimal attempts!',
    good: 'Great job matching organs to their functions!',
    retry: 'Try to remember card positions — fewer flips means a higher score.',
  },
};
