"""Algorithm domain knowledge schema — output of algo_dk_retriever."""

from typing import Optional
from pydantic import BaseModel, Field


class CommonBug(BaseModel):
    bug_type: str
    description: str
    buggy_line: str = ""
    correct_line: str = ""


class ExampleInput(BaseModel):
    input: str
    expected: str
    trace: str = ""


class DifficultyVariants(BaseModel):
    beginner: str = ""
    intermediate: str = ""
    advanced: str = ""


class AlgorithmDomainKnowledge(BaseModel):
    """Domain knowledge about an algorithm, gathered via web search + LLM."""

    algorithm_name: str
    algorithm_category: str = ""
    pseudocode: str = ""
    language_implementations: dict[str, str] = Field(default_factory=dict)
    time_complexity: dict[str, str] = Field(
        default_factory=dict,
        description="e.g. {'best': 'O(1)', 'average': 'O(log n)', 'worst': 'O(log n)'}",
    )
    space_complexity: dict[str, str] = Field(default_factory=dict)
    common_bugs: list[CommonBug] = Field(default_factory=list)
    common_misconceptions: list[str] = Field(default_factory=list)
    data_structures_used: list[str] = Field(default_factory=list)
    key_operations: list[str] = Field(default_factory=list)
    example_inputs: list[ExampleInput] = Field(default_factory=list)
    related_algorithms: list[str] = Field(default_factory=list)
    visualization_keywords: list[str] = Field(default_factory=list)
    difficulty_variants: Optional[DifficultyVariants] = None
