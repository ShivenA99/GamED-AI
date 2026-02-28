import { create } from 'zustand';
import { Label, PlacedLabel, LabelDiagramBlueprint, DistractorLabel } from '../types';

interface LabelDiagramState {
  // Labels that haven't been placed yet
  availableLabels: (Label | DistractorLabel)[];
  // Labels that have been placed on zones
  placedLabels: PlacedLabel[];
  // Current score
  score: number;
  // Total possible score
  maxScore: number;
  // Whether the game is complete
  isComplete: boolean;
  // Hint visibility state
  showHints: boolean;
  // Currently dragged label
  draggingLabelId: string | null;
  // Feedback for incorrect placement
  incorrectFeedback: { labelId: string; message: string } | null;
  // Blueprint reference
  blueprint: LabelDiagramBlueprint | null;

  // Actions
  initializeGame: (blueprint: LabelDiagramBlueprint) => void;
  placeLabel: (labelId: string, zoneId: string) => boolean;
  removeLabel: (labelId: string) => void;
  setDraggingLabel: (labelId: string | null) => void;
  toggleHints: () => void;
  resetGame: () => void;
  clearIncorrectFeedback: () => void;
}

export const useLabelDiagramState = create<LabelDiagramState>((set, get) => ({
  availableLabels: [],
  placedLabels: [],
  score: 0,
  maxScore: 0,
  isComplete: false,
  showHints: false,
  draggingLabelId: null,
  incorrectFeedback: null,
  blueprint: null,

  initializeGame: (blueprint: LabelDiagramBlueprint) => {
    // Combine regular labels with distractor labels and shuffle
    const allLabels: (Label | DistractorLabel)[] = [
      ...blueprint.labels,
      ...(blueprint.distractorLabels || []),
    ];

    // Shuffle the labels
    const shuffled = [...allLabels].sort(() => Math.random() - 0.5);

    set({
      availableLabels: shuffled,
      placedLabels: [],
      score: 0,
      maxScore: blueprint.labels.length * 10,
      isComplete: false,
      showHints: false,
      draggingLabelId: null,
      incorrectFeedback: null,
      blueprint,
    });
  },

  placeLabel: (labelId: string, zoneId: string) => {
    const state = get();
    const { blueprint, availableLabels, placedLabels } = state;

    if (!blueprint) return false;

    // Find the label being placed
    const label = availableLabels.find((l) => l.id === labelId);
    if (!label) return false;

    // Check if this is a distractor label (no correctZoneId)
    const isDistractor = !('correctZoneId' in label);

    // Check if placement is correct
    let isCorrect = false;
    if (!isDistractor && 'correctZoneId' in label) {
      isCorrect = label.correctZoneId === zoneId;
    }

    if (isCorrect) {
      // Correct placement
      const newPlacedLabels = [...placedLabels, { labelId, zoneId, isCorrect: true }];
      const newAvailableLabels = availableLabels.filter((l) => l.id !== labelId);
      const newScore = state.score + 10;

      // Check if game is complete (all correct labels placed)
      const correctLabelsCount = blueprint.labels.length;
      const placedCorrectCount = newPlacedLabels.filter((p) => p.isCorrect).length;
      const isComplete = placedCorrectCount >= correctLabelsCount;

      set({
        availableLabels: newAvailableLabels,
        placedLabels: newPlacedLabels,
        score: newScore,
        isComplete,
        draggingLabelId: null,
        incorrectFeedback: null,
      });

      return true;
    } else {
      // Incorrect placement - show feedback but don't place
      const zone = blueprint.diagram.zones.find((z) => z.id === zoneId);
      let message = blueprint.animationCues?.incorrectPlacement || 'Try again!';

      if (isDistractor && 'explanation' in label) {
        message = label.explanation;
      }

      set({
        draggingLabelId: null,
        incorrectFeedback: {
          labelId,
          message,
        },
      });

      return false;
    }
  },

  removeLabel: (labelId: string) => {
    const state = get();
    const { blueprint, placedLabels, availableLabels } = state;

    if (!blueprint) return;

    const placed = placedLabels.find((p) => p.labelId === labelId);
    if (!placed) return;

    // Find the original label
    const originalLabel = blueprint.labels.find((l) => l.id === labelId);
    if (!originalLabel) return;

    set({
      placedLabels: placedLabels.filter((p) => p.labelId !== labelId),
      availableLabels: [...availableLabels, originalLabel],
      score: state.score - 10,
      isComplete: false,
    });
  },

  setDraggingLabel: (labelId: string | null) => {
    set({ draggingLabelId: labelId, incorrectFeedback: null });
  },

  toggleHints: () => {
    set((state) => ({ showHints: !state.showHints }));
  },

  resetGame: () => {
    const { blueprint } = get();
    if (blueprint) {
      get().initializeGame(blueprint);
    }
  },

  clearIncorrectFeedback: () => {
    set({ incorrectFeedback: null });
  },
}));
