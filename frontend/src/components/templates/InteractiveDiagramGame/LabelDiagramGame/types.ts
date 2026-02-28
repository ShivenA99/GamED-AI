export interface Zone {
  id: string;
  label: string;
  x: number;  // 0-100 percentage
  y: number;  // 0-100 percentage
  radius: number;
  description?: string;
}

export interface Label {
  id: string;
  text: string;
  correctZoneId: string;
}

export interface DistractorLabel {
  id: string;
  text: string;
  explanation: string;
}

export interface Task {
  id: string;
  type: 'label_diagram' | 'identify_function' | 'trace_path';
  questionText: string;
  requiredToProceed: boolean;
}

export interface Hint {
  zoneId: string;
  hintText: string;
}

export interface AnimationCues {
  labelDrag?: string;
  correctPlacement: string;
  incorrectPlacement: string;
  allLabeled?: string;
}

export interface FeedbackMessages {
  perfect: string;
  good: string;
  retry: string;
}

export interface LabelDiagramBlueprint {
  templateType: 'LABEL_DIAGRAM';
  title: string;
  narrativeIntro: string;
  diagram: {
    assetPrompt: string;
    assetUrl?: string;
    width?: number;
    height?: number;
    zones: Zone[];
  };
  labels: Label[];
  distractorLabels?: DistractorLabel[];
  tasks: Task[];
  animationCues: AnimationCues;
  hints?: Hint[];
  feedbackMessages?: FeedbackMessages;
}

export interface PlacedLabel {
  labelId: string;
  zoneId: string;
  isCorrect: boolean;
}

export interface GameState {
  // Labels that haven't been placed yet
  availableLabels: Label[];
  // Labels that have been placed on zones
  placedLabels: PlacedLabel[];
  // Current score
  score: number;
  // Whether the game is complete
  isComplete: boolean;
  // Hint visibility state
  showHints: boolean;
  // Currently dragged label
  draggingLabelId: string | null;
}
