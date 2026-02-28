// Game Blueprint TypeScript Types
// These types match the backend TypeScript interfaces used in blueprint generation

export type TemplateType =
  | "LABEL_DIAGRAM"
  | "IMAGE_HOTSPOT_QA"
  | "SEQUENCE_BUILDER"
  | "TIMELINE_ORDER"
  | "BUCKET_SORT"
  | "MATCH_PAIRS"
  | "MATRIX_MATCH"
  | "PARAMETER_PLAYGROUND"
  | "GRAPH_SKETCHER"
  | "VECTOR_SANDBOX"
  | "STATE_TRACER_CODE"
  | "SPOT_THE_MISTAKE"
  | "CONCEPT_MAP_BUILDER"
  | "MICRO_SCENARIO_BRANCHING"
  | "DESIGN_CONSTRAINT_BUILDER"
  | "PROBABILITY_LAB"
  | "BEFORE_AFTER_TRANSFORMER"
  | "GEOMETRY_BUILDER";

// Base task interface
export interface Task {
  id: string;
  type: string;
  questionText: string;
  requiredToProceed: boolean;
}

// LABEL_DIAGRAM
export interface LabelDiagramBlueprint {
  templateType: "LABEL_DIAGRAM";
  title: string;
  narrativeIntro: string;
  diagram: {
    assetPrompt: string;
    assetUrl?: string;
    zones: Array<{
      id: string;
      label: string;
      x: number;
      y: number;
      radius: number;
    }>;
  };
  labels: Array<{
    id: string;
    text: string;
    isCorrect: boolean;
  }>;
  tasks: Array<{
    id: string;
    type: "label_diagram" | "free_response";
    questionText: string;
    requiredToProceed: boolean;
    rubric?: {
      mustMention?: string[];
      commonMisconceptions?: string[];
    };
  }>;
  animationCues: {
    correctPlacement: string;
    incorrectPlacement: string;
    onSubmitCorrect?: string;
    onSubmitIncorrect?: string;
  };
}

// IMAGE_HOTSPOT_QA
export interface ImageHotspotQABlueprint {
  templateType: "IMAGE_HOTSPOT_QA";
  title: string;
  narrativeIntro: string;
  image: {
    assetPrompt: string;
    assetUrl?: string;
  };
  hotspots: Array<{
    id: string;
    x: number;
    y: number;
    radius: number;
    label: string;
  }>;
  tasks: Array<{
    id: string;
    hotspotId: string;
    questionText: string;
    type: "multiple_choice" | "free_response";
    options?: string[];
    correctAnswer: string;
    feedback: {
      correct: string;
      incorrect: string;
    };
    requiredToProceed: boolean;
  }>;
  animationCues: {
    hotspotClick: string;
    modalOpen: string;
    correctAnswer: string;
    incorrectAnswer: string;
  };
}

// SEQUENCE_BUILDER
export interface SequenceBuilderBlueprint {
  templateType: "SEQUENCE_BUILDER";
  title: string;
  narrativeIntro: string;
  steps: Array<{
    id: string;
    text: string;
    orderIndex: number;
    description?: string;
  }>;
  distractors?: Array<{
    id: string;
    text: string;
    description?: string;
  }>;
  tasks: Array<{
    id: string;
    type: "sequence_order";
    questionText: string;
    requiredToProceed: boolean;
  }>;
  animationCues: {
    stepDrag: string;
    correctPlacement: string;
    incorrectPlacement: string;
    sequenceComplete?: string;
  };
}

// TIMELINE_ORDER
export interface TimelineOrderBlueprint {
  templateType: "TIMELINE_ORDER";
  title: string;
  narrativeIntro: string;
  events: Array<{
    id: string;
    text: string;
    timestamp: number;
    description?: string;
  }>;
  timeline: {
    startTime: number;
    endTime: number;
    unit?: string;
  };
  tasks: Array<Task & { type: "timeline_order" }>;
  animationCues: {
    eventPlacement: string;
    correctOrder: string;
    incorrectOrder: string;
    timelineProgress?: string;
  };
}

// BUCKET_SORT
export interface BucketSortBlueprint {
  templateType: "BUCKET_SORT";
  title: string;
  narrativeIntro: string;
  buckets: Array<{
    id: string;
    label: string;
    description?: string;
  }>;
  items: Array<{
    id: string;
    text: string;
    correctBucketId: string;
    description?: string;
  }>;
  tasks: Array<Task & { type: "bucket_sort" }>;
  animationCues: {
    itemDrag: string;
    correctDrop: string;
    incorrectDrop: string;
    bucketFull?: string;
  };
}

// MATCH_PAIRS
export interface MatchPairsBlueprint {
  templateType: "MATCH_PAIRS";
  title: string;
  narrativeIntro: string;
  pairs: Array<{
    id: string;
    leftItem: {
      id: string;
      text: string;
      imageUrl?: string;
    };
    rightItem: {
      id: string;
      text: string;
      imageUrl?: string;
    };
  }>;
  tasks: Array<Task & { type: "match_pairs" }>;
  animationCues: {
    cardFlip: string;
    cardMatch: string;
    cardMismatch: string;
    allMatched?: string;
  };
}

// MATRIX_MATCH
export interface MatrixMatchBlueprint {
  templateType: "MATRIX_MATCH";
  title: string;
  narrativeIntro: string;
  rows: Array<{
    id: string;
    label: string;
  }>;
  columns: Array<{
    id: string;
    label: string;
  }>;
  matches: Array<{
    rowId: string;
    columnId: string;
    isCorrect: boolean;
  }>;
  tasks: Array<Task & { type: "matrix_match" }>;
  animationCues: {
    cellSelect: string;
    matchFound: string;
    mismatch: string;
    matrixComplete?: string;
  };
}

// PARAMETER_PLAYGROUND
export interface ParameterPlaygroundBlueprint {
  templateType: "PARAMETER_PLAYGROUND";
  title: string;
  narrativeIntro: string;
  parameters: Array<{
    id: string;
    label: string;
    type: "slider" | "input" | "dropdown";
    min?: number;
    max?: number;
    defaultValue: number | string;
    unit?: string;
  }>;
  visualization: {
    type: "chart" | "graph" | "diagram" | "simulation";
    assetPrompt?: string;
    assetUrl?: string;
    // Enhanced visualization config
    algorithmType?: "binary_search" | "binary_search_rotated" | "sorting" | "graph" | "custom";
    array?: number[];
    target?: number;
    steps?: Array<{
      stepNumber: number;
      left?: number;
      right?: number;
      mid?: number;
      comparison?: string;
      decision?: string;
      explanation?: string;
      variables?: Record<string, any>;
      highlightIndices?: number[];
      sortedRanges?: Array<{ start: number; end: number }>;
    }>;
    code?: string;
  };
  tasks: Array<{
    id: string;
    type: "parameter_adjustment" | "prediction";
    questionText: string;
    targetValues?: Record<string, number | string>;
    requiredToProceed: boolean;
  }>;
  animationCues: {
    parameterChange: string;
    visualizationUpdate: string;
    targetReached?: string;
  };
}

// GRAPH_SKETCHER
export interface GraphSketcherBlueprint {
  templateType: "GRAPH_SKETCHER";
  title: string;
  narrativeIntro: string;
  graph: {
    nodes: Array<{
      id: string;
      label: string;
      x?: number;
      y?: number;
      required?: boolean;
    }>;
    edges: Array<{
      id: string;
      fromNodeId: string;
      toNodeId: string;
      required?: boolean;
      label?: string;
    }>;
  };
  tasks: Array<{
    id: string;
    type: "graph_construction" | "graph_analysis";
    questionText: string;
    requiredToProceed: boolean;
  }>;
  animationCues: {
    nodeCreate: string;
    edgeCreate: string;
    graphValid: string;
    graphInvalid?: string;
  };
}

// VECTOR_SANDBOX
export interface VectorSandboxBlueprint {
  templateType: "VECTOR_SANDBOX";
  title: string;
  narrativeIntro: string;
  vectors: Array<{
    id: string;
    label: string;
    initialX: number;
    initialY: number;
    magnitude: number;
    angle: number;
    color?: string;
  }>;
  operations: Array<{
    id: string;
    type: "add" | "subtract" | "scale" | "dot_product" | "cross_product";
    label: string;
  }>;
  tasks: Array<{
    id: string;
    type: "vector_operation" | "vector_analysis";
    questionText: string;
    targetResult?: {
      magnitude?: number;
      angle?: number;
      components?: { x: number; y: number };
    };
    requiredToProceed: boolean;
  }>;
  animationCues: {
    vectorMove: string;
    operationApply: string;
    resultDisplay: string;
  };
}

// STATE_TRACER_CODE
export interface StateTracerCodeBlueprint {
  templateType: "STATE_TRACER_CODE";
  title: string;
  narrativeIntro: string;
  code: string;
  initialInput?: any;
  steps: Array<{
    index: number;
    description: string;
    expectedVariables: Record<string, any>;
    expectedDataStructures?: Array<{
      name: string;
      summary: string;
    }>;
  }>;
  tasks: Array<{
    id: string;
    type: "variable_value" | "step_analysis" | "execution_flow";
    questionText: string;
    stepIndex?: number;
    variableName?: string;
    correctAnswer: string;
    requiredToProceed: boolean;
  }>;
  animationCues: {
    lineHighlight: string;
    variableUpdate: string;
    stepComplete: string;
    executionComplete?: string;
  };
}

// SPOT_THE_MISTAKE
export interface SpotTheMistakeBlueprint {
  templateType: "SPOT_THE_MISTAKE";
  title: string;
  narrativeIntro: string;
  content: {
    type: "code" | "text" | "diagram";
    text?: string;
    code?: string;
    assetPrompt?: string;
    assetUrl?: string;
  };
  mistakes: Array<{
    id: string;
    lineNumber?: number;
    startChar?: number;
    endChar?: number;
    regionId?: string;
    description: string;
    correction: string;
  }>;
  tasks: Array<Task & { type: "mistake_identification" }>;
  animationCues: {
    mistakeHighlight: string;
    mistakeFound: string;
    allMistakesFound?: string;
  };
}

// CONCEPT_MAP_BUILDER
export interface ConceptMapBuilderBlueprint {
  templateType: "CONCEPT_MAP_BUILDER";
  title: string;
  narrativeIntro: string;
  concepts: Array<{
    id: string;
    label: string;
    description?: string;
    required?: boolean;
    initialX?: number;
    initialY?: number;
  }>;
  connections: Array<{
    id: string;
    fromConceptId: string;
    toConceptId: string;
    label?: string;
    required?: boolean;
  }>;
  tasks: Array<{
    id: string;
    type: "concept_map_construction" | "relationship_analysis";
    questionText: string;
    requiredToProceed: boolean;
  }>;
  animationCues: {
    conceptPlace: string;
    connectionDraw: string;
    mapValid: string;
    mapInvalid?: string;
  };
}

// MICRO_SCENARIO_BRANCHING
export interface MicroScenarioBranchingBlueprint {
  templateType: "MICRO_SCENARIO_BRANCHING";
  title: string;
  narrativeIntro: string;
  scenarios: Array<{
    id: string;
    text: string;
    imageUrl?: string;
    assetPrompt?: string;
  }>;
  branches: Array<{
    id: string;
    fromScenarioId: string;
    toScenarioId: string;
    choiceText: string;
    isCorrect?: boolean;
    consequence?: string;
  }>;
  tasks: Array<{
    id: string;
    type: "decision_making" | "path_analysis";
    questionText: string;
    targetPath?: string[];
    requiredToProceed: boolean;
  }>;
  animationCues: {
    scenarioTransition: string;
    choiceSelect: string;
    pathComplete: string;
    optimalPath?: string;
  };
}

// DESIGN_CONSTRAINT_BUILDER
export interface DesignConstraintBuilderBlueprint {
  templateType: "DESIGN_CONSTRAINT_BUILDER";
  title: string;
  narrativeIntro: string;
  constraints: Array<{
    id: string;
    text: string;
    type: "required" | "optional" | "forbidden";
    description?: string;
  }>;
  designSpace: {
    elements: Array<{
      id: string;
      label: string;
      type: string;
      properties?: Record<string, any>;
    }>;
    canvas: {
      width: number;
      height: number;
    };
  };
  tasks: Array<{
    id: string;
    type: "design_construction" | "constraint_satisfaction";
    questionText: string;
    requiredToProceed: boolean;
  }>;
  animationCues: {
    elementPlace: string;
    constraintCheck: string;
    constraintViolated: string;
    constraintSatisfied: string;
    designComplete?: string;
  };
}

// PROBABILITY_LAB
export interface ProbabilityLabBlueprint {
  templateType: "PROBABILITY_LAB";
  title: string;
  narrativeIntro: string;
  experiments: Array<{
    id: string;
    name: string;
    description: string;
    type: "coin_flip" | "dice_roll" | "card_draw" | "custom";
    parameters?: Record<string, any>;
  }>;
  parameters: Array<{
    id: string;
    label: string;
    type: "slider" | "input" | "dropdown";
    min?: number;
    max?: number;
    defaultValue: number | string;
  }>;
  tasks: Array<{
    id: string;
    type: "probability_prediction" | "experiment_analysis";
    questionText: string;
    targetProbability?: number;
    requiredToProceed: boolean;
  }>;
  animationCues: {
    experimentRun: string;
    resultUpdate: string;
    probabilityDisplay: string;
    targetReached?: string;
  };
}

// BEFORE_AFTER_TRANSFORMER
export interface BeforeAfterTransformerBlueprint {
  templateType: "BEFORE_AFTER_TRANSFORMER";
  title: string;
  narrativeIntro: string;
  beforeState: {
    description: string;
    assetPrompt?: string;
    assetUrl?: string;
    data?: any;
  };
  afterState: {
    description: string;
    assetPrompt?: string;
    assetUrl?: string;
    data?: any;
  };
  transformations: Array<{
    id: string;
    description: string;
    order: number;
    effect?: string;
  }>;
  tasks: Array<{
    id: string;
    type: "transformation_sequence" | "transformation_analysis";
    questionText: string;
    requiredToProceed: boolean;
  }>;
  animationCues: {
    transformationApply: string;
    stateTransition: string;
    sequenceCorrect: string;
    sequenceIncorrect?: string;
  };
}

// GEOMETRY_BUILDER
export interface GeometryBuilderBlueprint {
  templateType: "GEOMETRY_BUILDER";
  title: string;
  narrativeIntro: string;
  shapes: Array<{
    id: string;
    type: "point" | "line" | "circle" | "polygon" | "angle";
    required?: boolean;
    properties?: Record<string, any>;
  }>;
  tools: Array<{
    id: string;
    label: string;
    type: "ruler" | "compass" | "protractor" | "freehand";
  }>;
  tasks: Array<{
    id: string;
    type: "shape_construction" | "property_analysis";
    questionText: string;
    targetShape?: {
      type: string;
      properties: Record<string, any>;
    };
    requiredToProceed: boolean;
  }>;
  animationCues: {
    toolUse: string;
    shapeCreate: string;
    constructionValid: string;
    constructionInvalid?: string;
  };
}

// Union type for all blueprints
export type GameBlueprint =
  | LabelDiagramBlueprint
  | ImageHotspotQABlueprint
  | SequenceBuilderBlueprint
  | TimelineOrderBlueprint
  | BucketSortBlueprint
  | MatchPairsBlueprint
  | MatrixMatchBlueprint
  | ParameterPlaygroundBlueprint
  | GraphSketcherBlueprint
  | VectorSandboxBlueprint
  | StateTracerCodeBlueprint
  | SpotTheMistakeBlueprint
  | ConceptMapBuilderBlueprint
  | MicroScenarioBranchingBlueprint
  | DesignConstraintBuilderBlueprint
  | ProbabilityLabBlueprint
  | BeforeAfterTransformerBlueprint
  | GeometryBuilderBlueprint;

// Type guards
export function isLabelDiagramBlueprint(blueprint: GameBlueprint): blueprint is LabelDiagramBlueprint {
  return blueprint.templateType === "LABEL_DIAGRAM";
}

export function isImageHotspotQABlueprint(blueprint: GameBlueprint): blueprint is ImageHotspotQABlueprint {
  return blueprint.templateType === "IMAGE_HOTSPOT_QA";
}

export function isSequenceBuilderBlueprint(blueprint: GameBlueprint): blueprint is SequenceBuilderBlueprint {
  return blueprint.templateType === "SEQUENCE_BUILDER";
}

// Add more type guards as needed...

