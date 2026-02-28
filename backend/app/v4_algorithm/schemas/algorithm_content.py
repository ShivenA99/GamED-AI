"""Content schemas for all 5 algorithm game types.

Each schema matches the corresponding frontend TypeScript interface in types.ts.
Field names use camelCase to match frontend expectations.
"""

from typing import Annotated, Optional, Literal, Union
from pydantic import BaseModel, Field, field_validator


def _pad_hints_to_3(v):
    """Pad hints list to exactly 3 strings. LLMs often return 0-2 hints."""
    if not isinstance(v, list):
        v = []
    while len(v) < 3:
        v.append("")
    return v[:3]


# ── Shared ────────────────────────────────────────────────────────


class LearnScaffolding(BaseModel):
    """Scaffolding config for learn mode."""
    pre_filled_steps: int = 0
    auto_play_count: int = 0
    explanation_timing: str = "immediate"  # immediate, after_attempt, after_hint
    extra: dict = Field(default_factory=dict)


class TestConfig(BaseModel):
    """Config for test mode."""
    hint_penalties: list[float] = Field(default=[0.1, 0.2, 0.3])
    time_limit_seconds: Optional[int] = None
    strict_scoring: bool = False
    extra: dict = Field(default_factory=dict)


class LearnModeConfig(BaseModel):
    """Learn mode configuration for the blueprint."""
    auto_reveal_hint_tier_1_after_ms: Optional[int] = 10000
    hint_penalties: list[float] = Field(default=[0, 0, 0])
    partial_credit_multiplier: float = 0.5
    show_correct_answer_on_wrong: bool = True
    show_misconceptions_preemptively: bool = True
    scaffolding: dict = Field(default_factory=dict)


class TestModeConfig(BaseModel):
    """Test mode configuration for the blueprint."""
    auto_reveal_hint_tier_1_after_ms: Optional[int] = None
    hint_penalties: list[float] = Field(default=[0.1, 0.2, 0.3])
    partial_credit_multiplier: float = 0.0
    show_correct_answer_on_wrong: bool = False
    show_misconceptions_preemptively: bool = False
    time_limit_seconds: Optional[int] = None


# ── StateTracer ───────────────────────────────────────────────────


class ArrayHighlight(BaseModel):
    index: int
    color: str = "active"


class ArrayDataStructure(BaseModel):
    type: Literal["array"] = "array"
    elements: list[Union[int, float, str]]
    highlights: list[ArrayHighlight] = Field(default_factory=list)
    sortedIndices: list[int] = Field(default_factory=list)


class GraphNode(BaseModel):
    id: str
    label: str
    x: float = 0
    y: float = 0
    state: str = "unvisited"


class GraphEdge(BaseModel):
    source: str = Field(alias="from", serialization_alias="from")
    to: str
    weight: Optional[float] = None
    state: str = "default"
    directed: bool = False

    model_config = {"populate_by_name": True}


class GraphDataStructure(BaseModel):
    type: Literal["graph"] = "graph"
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    auxiliary: Optional[dict] = None


class TreeNode(BaseModel):
    id: str
    value: Union[int, float, str]
    left: Optional[str] = None
    right: Optional[str] = None
    state: str = "default"


class TreeDataStructure(BaseModel):
    type: Literal["tree"] = "tree"
    nodes: list[TreeNode]
    root: str
    highlightPath: list[str] = Field(default_factory=list)


class DPCell(BaseModel):
    value: Optional[Union[int, float, str]] = None
    state: str = "empty"


class DPTableDataStructure(BaseModel):
    type: Literal["dp_table"] = "dp_table"
    cells: list[list[DPCell]]
    rowLabels: list[str] = Field(default_factory=list)
    colLabels: list[str] = Field(default_factory=list)
    activeCell: Optional[list[int]] = None
    dependencies: list[dict] = Field(default_factory=list)


class StackItem(BaseModel):
    id: str
    value: str
    state: str = "default"


class StackDataStructure(BaseModel):
    type: Literal["stack"] = "stack"
    items: list[StackItem]
    capacity: Optional[int] = None


class QueueItem(BaseModel):
    id: str
    value: Union[int, float, str]
    state: str = "default"


class QueueDataStructure(BaseModel):
    type: Literal["queue"] = "queue"
    items: list[QueueItem] = Field(default_factory=list)
    frontIndex: int = 0
    backIndex: int = 0
    capacity: Optional[int] = None
    highlights: list[int] = Field(default_factory=list)
    variant: str = "fifo"  # fifo | lifo | deque | priority


class LLNode(BaseModel):
    id: str
    value: Union[int, str]
    next: Optional[str] = None
    state: str = "default"


class LLPointer(BaseModel):
    name: str
    target: Optional[str] = None
    color: str = "#3b82f6"


class LinkedListDataStructure(BaseModel):
    type: Literal["linked_list"] = "linked_list"
    nodes: list[LLNode]
    head: Optional[str] = None
    pointers: list[LLPointer] = Field(default_factory=list)


# New data structure types

class HeapDataStructure(BaseModel):
    type: Literal["heap"] = "heap"
    elements: list[Union[int, float]]
    heapType: str = "min"  # min | max
    highlights: list[int] = Field(default_factory=list)


class HashMapDataStructure(BaseModel):
    type: Literal["hash_map"] = "hash_map"
    buckets: list[list[dict]] = Field(default_factory=list)
    capacity: int = 16
    highlights: list[int] = Field(default_factory=list)


class CustomObjectDataStructure(BaseModel):
    type: Literal["custom"] = "custom"
    fields: dict = Field(default_factory=dict)
    highlights: list[str] = Field(default_factory=list)
    label: str = ""


# Prediction types

class ArrangementPrediction(BaseModel):
    type: Literal["arrangement"] = "arrangement"
    prompt: str
    elements: list[Union[int, float, str]]
    correctArrangement: list[Union[int, float, str]]


class ValuePrediction(BaseModel):
    type: Literal["value"] = "value"
    prompt: str
    correctValue: str
    acceptableValues: list[str] = Field(default_factory=list)
    placeholder: str = ""


class MultipleChoicePrediction(BaseModel):
    type: Literal["multiple_choice"] = "multiple_choice"
    prompt: str
    options: list[dict]  # [{id, label}]
    correctId: str


class MultiSelectPrediction(BaseModel):
    type: Literal["multi_select"] = "multi_select"
    prompt: str
    options: list[dict]  # [{id, label}]
    correctIds: list[str]


class CodeCompletionPrediction(BaseModel):
    type: Literal["code_completion"] = "code_completion"
    prompt: str
    codeTemplate: str
    correctCode: str
    acceptableVariants: list[str] = Field(default_factory=list)


class TrueFalsePrediction(BaseModel):
    type: Literal["true_false"] = "true_false"
    prompt: str
    correctAnswer: bool
    explanation: str = ""


class ExecutionStep(BaseModel):
    stepNumber: int
    codeLine: int
    description: str
    variables: dict = Field(default_factory=dict)
    changedVariables: list[str] = Field(default_factory=list)
    dataStructure: Annotated[
        Union[
            ArrayDataStructure, GraphDataStructure, TreeDataStructure,
            DPTableDataStructure, StackDataStructure, QueueDataStructure,
            LinkedListDataStructure, HeapDataStructure, HashMapDataStructure,
            CustomObjectDataStructure,
        ],
        Field(discriminator='type'),
    ]
    prediction: Optional[Annotated[
        Union[
            ArrangementPrediction, ValuePrediction, MultipleChoicePrediction,
            MultiSelectPrediction, CodeCompletionPrediction, TrueFalsePrediction,
        ],
        Field(discriminator='type'),
    ]] = None
    explanation: str = ""
    hints: list[str] = Field(default_factory=list, min_length=0, max_length=3)

    @field_validator('hints', mode='before')
    @classmethod
    def pad_hints(cls, v):
        return _pad_hints_to_3(v)


class ScoringConfig(BaseModel):
    basePoints: int = 100
    streakThresholds: list[dict] = Field(
        default_factory=lambda: [
            {"min": 0, "multiplier": 1},
            {"min": 3, "multiplier": 1.5},
            {"min": 5, "multiplier": 2},
            {"min": 8, "multiplier": 3},
        ]
    )
    hintPenalties: list[float] = Field(default=[0.1, 0.2, 0.3])
    perfectRunBonus: float = 0.2


class StateTracerSceneContent(BaseModel):
    """Content for a StateTracer scene."""
    algorithmName: str
    algorithmDescription: str = ""
    narrativeIntro: str = ""
    code: str
    language: str = "python"
    steps: list[ExecutionStep]
    scoringConfig: Optional[ScoringConfig] = None
    learn_scaffolding: Optional[LearnScaffolding] = None
    test_config: Optional[TestConfig] = None


# ── BugHunter ─────────────────────────────────────────────────────


class FixOption(BaseModel):
    id: str
    codeText: str
    isCorrect: bool
    feedback: str = ""


class BugDefinition(BaseModel):
    bugId: str
    bugLines: list[int] = Field(default_factory=list)
    buggyLinesText: list[str] = Field(default_factory=list)
    correctLinesText: list[str] = Field(default_factory=list)
    bugType: str  # off_by_one, wrong_operator, etc.
    difficulty: int = Field(default=1, ge=1, le=3)
    explanation: str = ""
    bugTypeExplanation: str = ""
    fixOptions: list[FixOption] = Field(default_factory=list)
    hints: list[str] = Field(default_factory=list, min_length=0, max_length=3)

    @field_validator('hints', mode='before')
    @classmethod
    def pad_hints(cls, v):
        return _pad_hints_to_3(v)


class BugHunterTestCase(BaseModel):
    id: str
    inputDescription: str
    expectedOutput: str
    buggyOutput: str = ""
    exposedBugs: list[str] = Field(default_factory=list)


class RedHerring(BaseModel):
    lineNumber: int
    feedback: str = ""


class BugHunterRound(BaseModel):
    roundId: str
    title: str = ""
    buggyCode: str
    correctCode: str
    bugs: list[BugDefinition]
    testCases: list[BugHunterTestCase] = Field(default_factory=list)
    redHerrings: list[RedHerring] = Field(default_factory=list)


class BugHunterConfig(BaseModel):
    revealSequentially: bool = True
    showTestOutput: bool = True
    showRunButton: bool = True
    fixMode: Literal["multiple_choice", "free_text"] = "multiple_choice"
    maxWrongLineClicks: int = 3
    roundMode: bool = True


class BugHunterSceneContent(BaseModel):
    """Content for a BugHunter scene."""
    algorithmName: str
    algorithmDescription: str = ""
    narrativeIntro: str = ""
    language: str = "python"
    rounds: list[BugHunterRound]
    config: BugHunterConfig = Field(default_factory=BugHunterConfig)
    learn_scaffolding: Optional[LearnScaffolding] = None
    test_config: Optional[TestConfig] = None


# ── AlgorithmBuilder ──────────────────────────────────────────────


class ParsonsBlock(BaseModel):
    id: str
    code: str
    indent_level: int = Field(default=0, ge=0, le=7)
    is_distractor: bool = False
    distractor_explanation: str = ""
    group_id: str = ""  # interchangeable blocks share group_id


class AlgorithmBuilderTestCase(BaseModel):
    id: str
    inputDescription: str
    expectedOutput: str
    explanation: str = ""


class AlgorithmBuilderConfig(BaseModel):
    indentation_matters: bool = True
    max_attempts: Optional[int] = None  # null = unlimited
    show_line_numbers: bool = True
    allow_indent_adjustment: bool = True
    indent_px_per_level: int = 24
    max_indent_level: int = 7


class AlgorithmBuilderSceneContent(BaseModel):
    """Content for an AlgorithmBuilder scene."""
    algorithmName: str
    algorithmDescription: str = ""
    problemDescription: str = ""
    language: str = "python"
    correct_order: list[ParsonsBlock]
    distractors: list[ParsonsBlock] = Field(default_factory=list)
    config: AlgorithmBuilderConfig = Field(default_factory=AlgorithmBuilderConfig)
    hints: list[str] = Field(default_factory=list, min_length=0, max_length=3)
    test_cases: list[AlgorithmBuilderTestCase] = Field(default_factory=list)
    learn_scaffolding: Optional[LearnScaffolding] = None
    test_config: Optional[TestConfig] = None

    @field_validator('hints', mode='before')
    @classmethod
    def pad_hints(cls, v):
        return _pad_hints_to_3(v)


# ── ComplexityAnalyzer ────────────────────────────────────────────


class CodeSection(BaseModel):
    sectionId: str
    label: str
    startLine: int
    endLine: int
    complexity: str
    isBottleneck: bool = False


class ComplexityChallenge(BaseModel):
    challengeId: str
    type: Literal["identify_from_code", "infer_from_growth", "find_bottleneck"]
    title: str
    description: str = ""
    code: str = ""
    language: str = "python"
    growthData: Optional[dict] = None  # {inputSizes: [], operationCounts: []}
    codeSections: list[CodeSection] = Field(default_factory=list)
    correctComplexity: str
    options: list[str]
    explanation: str = ""
    points: int = 100
    hints: list[str] = Field(default_factory=list, min_length=0, max_length=3)
    complexityDimension: Literal["time", "space", "both"] = "time"
    caseVariant: Literal["worst", "best", "average", "amortized"] = "worst"

    @field_validator('hints', mode='before')
    @classmethod
    def pad_hints(cls, v):
        return _pad_hints_to_3(v)


class ComplexityAnalyzerSceneContent(BaseModel):
    """Content for a ComplexityAnalyzer scene."""
    algorithmName: str
    algorithmDescription: str = ""
    challenges: list[ComplexityChallenge]
    complexity_dimension: Literal["time", "space", "both"] = "time"
    case_variants: Literal["worst_only", "best_worst", "all_cases"] = "worst_only"
    learn_scaffolding: Optional[LearnScaffolding] = None
    test_config: Optional[TestConfig] = None


# ── ConstraintPuzzle ──────────────────────────────────────────────


class SelectableItem(BaseModel):
    id: str
    name: str
    properties: dict = Field(default_factory=dict)
    icon: str = ""


class BoardConfig(BaseModel):
    """Generic board config. The boardType discriminator determines shape."""
    boardType: Literal["item_selection", "grid_placement", "multiset_building", "graph_interaction", "value_assignment", "sequence_building"]
    # Type-specific fields stored in extra
    extra: dict = Field(default_factory=dict)
    items: list[SelectableItem] = Field(default_factory=list)
    gridSize: Optional[int] = None
    capacity: Optional[float] = None
    denominations: list[float] = Field(default_factory=list)
    targetAmount: Optional[float] = None


class Constraint(BaseModel):
    type: str  # capacity, no_conflict, sum_property, all_different, min_count, max_count, dependency, no_overlap, custom, logical, precedence
    params: dict = Field(default_factory=dict)
    description: str = ""


class PuzzleScoringConfig(BaseModel):
    method: str = "optimality_ratio"  # optimality_ratio, binary, constraint_count, custom
    maxPoints: int = 400
    params: dict = Field(default_factory=dict)


class ConstraintPuzzleSceneContent(BaseModel):
    """Content for a ConstraintPuzzle scene."""
    title: str = ""
    narrative: str = ""
    rules: list[str] = Field(default_factory=list)
    objective: str = ""
    boardConfig: BoardConfig
    constraints: list[Constraint] = Field(default_factory=list)
    scoringConfig: PuzzleScoringConfig = Field(default_factory=PuzzleScoringConfig)
    optimalValue: float = 0
    optimalSolutionDescription: str = ""
    algorithmName: str = ""
    algorithmExplanation: str = ""
    hints: list[str] = Field(default_factory=list, min_length=0, max_length=3)
    learn_scaffolding: Optional[LearnScaffolding] = None
    test_config: Optional[TestConfig] = None

    @field_validator('hints', mode='before')
    @classmethod
    def pad_hints(cls, v):
        return _pad_hints_to_3(v)
