"""Validation schemas — used by all validators (game_plan, content, blueprint)."""

from typing import Literal, Optional
from pydantic import BaseModel, Field


class ValidationIssue(BaseModel):
    """A single validation finding."""
    severity: Literal["error", "warning", "info"]
    message: str
    field_path: Optional[str] = None
    mechanic_id: Optional[str] = None


class ValidationResult(BaseModel):
    """Result of any validation step."""
    passed: bool
    score: float = Field(ge=0.0, le=1.0, default=1.0)
    issues: list[ValidationIssue] = Field(default_factory=list)
    retry_allowed: bool = True

    @property
    def errors(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.severity == "error"]

    @property
    def warnings(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.severity == "warning"]

    @property
    def has_errors(self) -> bool:
        return any(i.severity == "error" for i in self.issues)
