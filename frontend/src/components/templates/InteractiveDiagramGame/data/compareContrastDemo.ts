import type { InteractiveDiagramBlueprint } from '../types';

export const compareContrastDemo: InteractiveDiagramBlueprint = {
  templateType: 'INTERACTIVE_DIAGRAM',
  title: 'Compare Plant and Animal Cells',
  narrativeIntro: 'Plant and animal cells are both eukaryotic, but they have key structural differences. Examine both diagrams and categorize each feature as similar, different, or unique to one cell type.',
  diagram: {
    assetPrompt: 'Side-by-side educational diagrams of a plant cell and an animal cell with labeled structures, clean illustration',
    zones: [],
  },
  labels: [],
  tasks: [
    { id: 't-1', type: 'label_diagram', questionText: 'Compare the structures of plant and animal cells', requiredToProceed: true },
  ],
  animationCues: {
    correctPlacement: 'glow',
    incorrectPlacement: 'shake',
    allLabeled: 'confetti',
  },
  mechanics: [
    { type: 'compare_contrast', scoring: { strategy: 'per_zone', points_per_correct: 10, max_score: 100 }, feedback: { on_correct: 'Correct categorization!', on_incorrect: 'Think about whether this feature is shared or unique.', on_completion: 'Great job comparing cell types!' } },
  ],
  interactionMode: 'compare_contrast',
  compareConfig: {
    diagramA: {
      id: 'plant-cell',
      name: 'Plant Cell',
      imageUrl: '/api/assets/demo/demo_compare/plant/diagram.png',
      zones: [
        { id: 'pz-cw', label: 'Cell Wall', x: 10, y: 50, width: 15, height: 15 },
        { id: 'pz-chloro', label: 'Chloroplast', x: 30, y: 30, width: 12, height: 12 },
        { id: 'pz-vacuole', label: 'Central Vacuole', x: 50, y: 50, width: 20, height: 20 },
        { id: 'pz-nucleus', label: 'Nucleus', x: 60, y: 25, width: 15, height: 15 },
        { id: 'pz-mito', label: 'Mitochondria', x: 75, y: 60, width: 10, height: 10 },
        { id: 'pz-er', label: 'ER', x: 40, y: 70, width: 12, height: 10 },
        { id: 'pz-plasto', label: 'Plastids', x: 25, y: 65, width: 10, height: 10 },
      ],
    },
    diagramB: {
      id: 'animal-cell',
      name: 'Animal Cell',
      imageUrl: '/api/assets/demo/demo_compare/animal/diagram.png',
      zones: [
        { id: 'az-membrane', label: 'Cell Membrane', x: 10, y: 50, width: 15, height: 15 },
        { id: 'az-centro', label: 'Centrioles', x: 30, y: 30, width: 10, height: 10 },
        { id: 'az-lyso', label: 'Lysosomes', x: 50, y: 55, width: 10, height: 10 },
        { id: 'az-nucleus', label: 'Nucleus', x: 60, y: 25, width: 15, height: 15 },
        { id: 'az-mito', label: 'Mitochondria', x: 75, y: 60, width: 10, height: 10 },
        { id: 'az-er', label: 'ER', x: 40, y: 70, width: 12, height: 10 },
        { id: 'az-golgi', label: 'Golgi', x: 25, y: 65, width: 10, height: 10 },
      ],
    },
    expectedCategories: {
      'Cell Wall': 'unique_a',
      'Chloroplast': 'unique_a',
      'Central Vacuole': 'unique_a',
      'Plastids': 'unique_a',
      'Centrioles': 'unique_b',
      'Lysosomes': 'unique_b',
      'Nucleus': 'similar',
      'Mitochondria': 'similar',
      'ER': 'similar',
      'Cell Membrane': 'similar',
      'Golgi': 'similar',
    },
    highlightMatching: true,
    instructions: 'Examine both cell diagrams. For each highlighted structure, categorize it as: Similar (found in both), Unique to Plant Cell, or Unique to Animal Cell.',
    comparison_mode: 'side_by_side',
    category_labels: {
      similar: 'Found in Both',
      unique_a: 'Plant Cell Only',
      unique_b: 'Animal Cell Only',
    },
    category_colors: {
      similar: '#a855f7',
      unique_a: '#22c55e',
      unique_b: '#3b82f6',
    },
    exploration_enabled: true,
    zoom_enabled: true,
  },
  feedbackMessages: {
    perfect: 'Perfect comparison! You understand the key differences between cell types.',
    good: 'Good work! Remember that many organelles are shared.',
    retry: 'Focus on which structures are exclusive to plant cells (cell wall, chloroplasts, large vacuole).',
  },
};
