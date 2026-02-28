import type { InteractiveDiagramBlueprint } from '../types';

export const sortingDemo: InteractiveDiagramBlueprint = {
  templateType: 'INTERACTIVE_DIAGRAM',
  title: 'Plant Cell vs Animal Cell Features',
  narrativeIntro: 'Plant cells and animal cells share many organelles, but each has unique features. Sort the following structures into the correct category based on whether they are found in plant cells only, animal cells only, or both.',
  diagram: {
    assetPrompt: 'Side-by-side comparison of plant cell and animal cell, educational illustration showing key differences',
    zones: [],
  },
  labels: [],
  tasks: [
    { id: 't-1', type: 'label_diagram', questionText: 'Sort each feature into Plant Cell Only, Animal Cell Only, or Both', requiredToProceed: true },
  ],
  animationCues: {
    correctPlacement: 'pulse',
    incorrectPlacement: 'shake',
    allLabeled: 'confetti',
  },
  mechanics: [
    { type: 'sorting_categories', scoring: { strategy: 'per_zone', points_per_correct: 10, max_score: 90 }, feedback: { on_correct: 'Correct category!', on_incorrect: 'Think about whether this structure is found in plant cells, animal cells, or both.', on_completion: 'You sorted all features correctly!' } },
  ],
  interactionMode: 'sorting_categories',
  sortingConfig: {
    items: [
      { id: 'item-cw', content: 'Cell Wall', correctCategoryId: 'cat-plant', description: 'Rigid outer layer made of cellulose that provides structural support', image: '/api/assets/demo/demo_sorting/items/cell_wall.png', difficulty: 'easy' },
      { id: 'item-chloro', content: 'Chloroplasts', correctCategoryId: 'cat-plant', description: 'Organelles that convert sunlight into glucose via photosynthesis', image: '/api/assets/demo/demo_sorting/items/chloroplast.png', difficulty: 'easy' },
      { id: 'item-lv', content: 'Large Central Vacuole', correctCategoryId: 'cat-plant', description: 'A large fluid-filled sac that maintains turgor pressure', image: '/api/assets/demo/demo_sorting/items/central_vacuole.png', difficulty: 'medium' },
      { id: 'item-centro', content: 'Centrioles', correctCategoryId: 'cat-animal', description: 'Cylindrical structures involved in organizing spindle fibers during cell division', image: '/api/assets/demo/demo_sorting/items/centrioles.png', difficulty: 'medium' },
      { id: 'item-lyso', content: 'Lysosomes', correctCategoryId: 'cat-animal', description: 'Vesicles containing digestive enzymes for breaking down waste materials', image: '/api/assets/demo/demo_sorting/items/lysosomes.png', difficulty: 'medium' },
      { id: 'item-flagella', content: 'Flagella', correctCategoryId: 'cat-animal', description: 'Whip-like appendages used for cellular locomotion', image: '/api/assets/demo/demo_sorting/items/flagella.png', difficulty: 'hard' },
      { id: 'item-nucleus', content: 'Nucleus', correctCategoryId: 'cat-both', description: 'Contains DNA and controls cell activities; present in both cell types', image: '/api/assets/demo/demo_sorting/items/nucleus.png', difficulty: 'easy' },
      { id: 'item-mito', content: 'Mitochondria', correctCategoryId: 'cat-both', description: 'Produces ATP through cellular respiration; found in both cell types', image: '/api/assets/demo/demo_sorting/items/mitochondria.png', difficulty: 'easy' },
      { id: 'item-er', content: 'Endoplasmic Reticulum', correctCategoryId: 'cat-both', description: 'Network of membranes for protein and lipid synthesis', image: '/api/assets/demo/demo_sorting/items/endoplasmic_reticulum.png', difficulty: 'medium' },
    ],
    categories: [
      { id: 'cat-plant', label: 'Plant Cell Only', description: 'Features found exclusively in plant cells', color: '#22c55e' },
      { id: 'cat-animal', label: 'Animal Cell Only', description: 'Features found exclusively in animal cells', color: '#3b82f6' },
      { id: 'cat-both', label: 'Both', description: 'Features found in both plant and animal cells', color: '#a855f7' },
    ],
    allowPartialCredit: true,
    showCategoryHints: true,
    instructions: 'Drag each cell feature into the correct category bucket. Some features are shared by both cell types!',
    sort_mode: 'bucket',
    item_card_type: 'text_with_icon',
    container_style: 'labeled_bin',
    submit_mode: 'batch_submit',
  },
  feedbackMessages: {
    perfect: 'Perfect sorting! You know your cell biology!',
    good: 'Good job! Remember that many organelles like mitochondria and ER are shared.',
    retry: 'Think about what makes plant cells unique — cell wall, chloroplasts, and large vacuole.',
  },
};
