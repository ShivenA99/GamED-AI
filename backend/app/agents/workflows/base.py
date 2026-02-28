"""Base workflow utilities for asset generation workflows."""
import logging
from typing import Dict, List, Any, Optional, Callable, Awaitable
from dataclasses import dataclass
from enum import Enum
from datetime import datetime

logger = logging.getLogger("gamed_ai.workflows.base")

class WorkflowStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"

@dataclass
class WorkflowResult:
    success: bool
    workflow_name: str
    asset_id: str
    scene_number: int
    output_type: str
    data: Dict[str, Any]
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "workflow_name": self.workflow_name,
            "asset_id": self.asset_id,
            "scene_number": self.scene_number,
            "output_type": self.output_type,
            "data": self.data,
            "error": self.error,
            "metadata": self.metadata,
            "started_at": self.started_at,
            "completed_at": self.completed_at
        }

@dataclass
class WorkflowContext:
    asset_spec: Dict[str, Any]
    domain_knowledge: Dict[str, Any]
    dependencies: Dict[str, 'WorkflowResult']
    scene_number: int
    instrumentation_ctx: Optional[Any] = None
    state: Optional[Dict[str, Any]] = None

    def get_dependency(self, output_type: str) -> Optional['WorkflowResult']:
        for dep in self.dependencies.values():
            if dep.output_type == output_type:
                return dep
        return None

    def get_spec_value(self, key: str, default: Any = None) -> Any:
        return self.asset_spec.get("spec", {}).get(key, default)

WorkflowFunction = Callable[[WorkflowContext], Awaitable[WorkflowResult]]

class WorkflowRegistry:
    _workflows: Dict[str, WorkflowFunction] = {}
    _metadata: Dict[str, Dict[str, Any]] = {}

    @classmethod
    def register(cls, name: str, description: str = "", output_type: str = ""):
        def decorator(fn: WorkflowFunction) -> WorkflowFunction:
            cls._workflows[name] = fn
            cls._metadata[name] = {
                "name": name,
                "description": description or fn.__doc__ or "",
                "output_type": output_type,
                "function": fn.__name__
            }
            logger.info(f"Registered workflow: {name}")
            return fn
        return decorator

    @classmethod
    def get(cls, name: str) -> Optional[WorkflowFunction]:
        return cls._workflows.get(name)

    @classmethod
    def list_workflows(cls) -> List[str]:
        return list(cls._workflows.keys())

    @classmethod
    def get_metadata(cls, name: str) -> Optional[Dict[str, Any]]:
        return cls._metadata.get(name)

async def run_workflow_step(step_name: str, step_fn: Callable, context: WorkflowContext, **kwargs) -> Dict[str, Any]:
    step_logger = logging.getLogger(f"gamed_ai.workflows.step.{step_name}")
    started_at = datetime.utcnow().isoformat()
    step_logger.info(f"Starting workflow step: {step_name}")
    try:
        result = await step_fn(context=context, **kwargs)
        step_logger.info(f"Completed workflow step: {step_name}")
        return {"success": True, "step_name": step_name, "started_at": started_at, "completed_at": datetime.utcnow().isoformat(), "result": result}
    except Exception as e:
        step_logger.error(f"Failed workflow step {step_name}: {e}")
        return {"success": False, "step_name": step_name, "started_at": started_at, "completed_at": datetime.utcnow().isoformat(), "error": str(e)}

def merge_workflow_results(base_result: WorkflowResult, additional_data: Dict[str, Any]) -> WorkflowResult:
    merged_data = {**base_result.data, **additional_data}
    return WorkflowResult(
        success=base_result.success, workflow_name=base_result.workflow_name, asset_id=base_result.asset_id,
        scene_number=base_result.scene_number, output_type=base_result.output_type, data=merged_data,
        error=base_result.error, metadata=base_result.metadata, started_at=base_result.started_at, completed_at=base_result.completed_at
    )

def create_failed_result(workflow_name: str, asset_id: str, scene_number: int, output_type: str, error: str) -> WorkflowResult:
    return WorkflowResult(
        success=False, workflow_name=workflow_name, asset_id=asset_id, scene_number=scene_number,
        output_type=output_type, data={}, error=error,
        started_at=datetime.utcnow().isoformat(), completed_at=datetime.utcnow().isoformat()
    )
