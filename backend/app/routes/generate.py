"""Game Generation API Routes"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query, Request
from fastapi.responses import Response
from sqlalchemy.orm import Session
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator
from typing import Literal
import logging
import uuid
import httpx
import urllib.parse
import ipaddress
import socket

from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.db.database import get_db
from app.db.models import Question, Process
from app.agents import state as agent_state
from app.agents.graph import get_compiled_graph
from app.agents.instrumentation import create_pipeline_run

logger = logging.getLogger("gamed_ai.routes.generate")

# Rate limiter configuration
limiter = Limiter(key_func=get_remote_address)
router = APIRouter()


# =============================================================================
# SECURITY UTILITIES
# =============================================================================

# Private IP ranges to block for SSRF prevention
PRIVATE_IP_RANGES = [
    ipaddress.ip_network('10.0.0.0/8'),
    ipaddress.ip_network('172.16.0.0/12'),
    ipaddress.ip_network('192.168.0.0/16'),
    ipaddress.ip_network('127.0.0.0/8'),
    ipaddress.ip_network('169.254.0.0/16'),
    ipaddress.ip_network('::1/128'),
    ipaddress.ip_network('fc00::/7'),
    ipaddress.ip_network('fe80::/10'),
]


def is_safe_url(url: str) -> bool:
    """
    Validate URL to prevent SSRF attacks.

    Blocks:
    - Non-HTTP(S) URLs
    - Private/internal IP addresses
    - Localhost and loopback addresses
    """
    if not url or not url.startswith(("http://", "https://")):
        return False

    try:
        parsed = urllib.parse.urlparse(url)
        if not parsed.hostname:
            return False

        # Resolve hostname to IP
        ip_str = socket.gethostbyname(parsed.hostname)
        ip_obj = ipaddress.ip_address(ip_str)

        # Check against private ranges
        for network in PRIVATE_IP_RANGES:
            if ip_obj in network:
                logger.warning(f"SSRF prevention: blocked private IP {ip_str} in URL {url[:100]}")
                return False

        return True
    except (socket.gaierror, socket.herror) as e:
        logger.warning(f"DNS resolution failed for URL {url[:100]}: {e}")
        return False
    except ValueError as e:
        logger.warning(f"Invalid IP address in URL {url[:100]}: {e}")
        return False
    except Exception as e:
        logger.warning(f"URL validation failed for {url[:100]}: {e}")
        return False


def sanitize_error_for_client(error: Exception, context: str = "") -> tuple[str, str]:
    """
    Sanitize error messages for client response.

    Returns:
        Tuple of (user_friendly_message, internal_reference_id)

    The full traceback is logged server-side but NOT returned to clients.
    """
    ref_id = str(uuid.uuid4())[:8]

    # Log full error details server-side
    logger.error(
        f"[{ref_id}] Error in {context}: {type(error).__name__}: {error}",
        exc_info=True
    )

    # Return sanitized message to client
    return f"An error occurred. Reference ID: {ref_id}", ref_id


# Valid topology and preset types
VALID_TOPOLOGIES = Literal["T0", "T1", "T2", "T4", "T5", "T7", "HAD"]
VALID_PRESETS = Literal["groq_free", "cost_optimized", "balanced", "quality_optimized", "openai_only", "anthropic_only", "gemini_only", "local_only"]


class GenerationConfig(BaseModel):
    """Configuration for pipeline run with strict validation"""
    provider: Literal["openai", "anthropic", "google", "gemini", "local", "groq"] = "google"
    topology: VALID_TOPOLOGIES = "T1"
    agent_config_preset: Optional[VALID_PRESETS] = None
    pipeline_preset: Optional[str] = None


class GenerateRequest(BaseModel):
    """Request model for game generation with validation"""
    question_text: str = Field(
        ...,
        min_length=10,
        max_length=2000,
        description="The question text (10-2000 characters)"
    )
    question_options: Optional[List[str]] = Field(
        default=None,
        max_length=10,
        description="Optional answer choices (max 10)"
    )
    config: Optional[GenerationConfig] = None
    # Convenience: accept pipeline_preset at top level
    pipeline_preset: Optional[str] = None

    @field_validator('question_text')
    @classmethod
    def validate_question_text(cls, v: str) -> str:
        """Ensure question is not just whitespace"""
        stripped = v.strip()
        if not stripped:
            raise ValueError('Question cannot be empty or whitespace only')
        return stripped

    @field_validator('question_options')
    @classmethod
    def validate_options(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        """Validate answer options if provided"""
        if v is None:
            return v
        # Filter out empty options
        filtered = [opt.strip() for opt in v if opt and opt.strip()]
        if len(filtered) > 10:
            raise ValueError('Maximum 10 answer options allowed')
        return filtered if filtered else None


# =============================================================================
# RESPONSE MODELS
# =============================================================================

from datetime import datetime as dt


class GenerateStartResponse(BaseModel):
    """Response model for starting generation"""
    process_id: str
    run_id: str
    question_id: str
    status: str
    message: str


class ProcessSummary(BaseModel):
    """Summary of a generation process"""
    id: str
    question_id: str
    question_text: str
    template_type: Optional[str] = None
    thumbnail_url: Optional[str] = None
    status: str
    current_agent: Optional[str] = None
    progress_percent: Optional[float] = None
    error_message: Optional[str] = None
    created_at: Optional[str] = None
    completed_at: Optional[str] = None


class ProcessListResponse(BaseModel):
    """Response model for listing processes"""
    processes: List[ProcessSummary]
    total: int


class GenerationStatusResponse(BaseModel):
    """Response model for generation status"""
    process_id: str
    status: str
    current_agent: Optional[str] = None
    progress_percent: Optional[float] = None
    error_message: Optional[str] = None
    created_at: Optional[str] = None
    completed_at: Optional[str] = None


class BlueprintResponse(BaseModel):
    """Response model for generated blueprint"""
    process_id: str
    template_type: str
    blueprint: dict
    story_data: Optional[dict] = None
    pedagogical_context: Optional[dict] = None
    game_plan: Optional[dict] = None
    created_at: Optional[str] = None


def _build_agent_outputs(state: dict) -> dict:
    agent_outputs: dict = {}
    agent_history = {
        entry.get("agent_name"): entry
        for entry in state.get("agent_history", [])
        if isinstance(entry, dict) and entry.get("agent_name")
    }

    def record(agent_name: str, output: Optional[dict]):
        if output is None:
            return
        payload = {"output": output}
        history = agent_history.get(agent_name)
        if history:
            payload["metadata"] = history
        agent_outputs[agent_name] = payload

    record("input_enhancer", state.get("pedagogical_context"))
    record("domain_knowledge_retriever", state.get("domain_knowledge"))
    record("diagram_image_retriever", state.get("diagram_image"))
    record("diagram_image_segmenter", state.get("diagram_segments"))
    record("diagram_zone_labeler", {
        "diagram_zones": state.get("diagram_zones"),
        "diagram_labels": state.get("diagram_labels"),
    } if state.get("diagram_zones") or state.get("diagram_labels") else None)

    routing_payload = {}
    if state.get("template_selection") is not None:
        routing_payload["template_selection"] = state.get("template_selection")
    if state.get("routing_confidence") is not None:
        routing_payload["routing_confidence"] = state.get("routing_confidence")
    if state.get("routing_requires_human_review") is not None:
        routing_payload["routing_requires_human_review"] = state.get("routing_requires_human_review")
    if routing_payload:
        record("router", routing_payload)

    record("game_planner", state.get("game_plan"))
    record("scene_generator", state.get("scene_data"))
    record("story_generator", state.get("story_data"))
    record("blueprint_generator", state.get("blueprint"))
    record("diagram_spec_generator", state.get("diagram_spec"))
    record("diagram_svg_generator", state.get("diagram_svg"))
    record("asset_generator", state.get("asset_urls"))

    validation_results = state.get("validation_results", {})
    if isinstance(validation_results, dict):
        record("blueprint_validator", validation_results.get("blueprint"))
        record("diagram_spec_validator", validation_results.get("diagram_spec"))
        record("code_verifier", validation_results.get("code"))

    if state.get("pending_human_review") is not None:
        record("human_review", state.get("pending_human_review"))

    # V3 pipeline outputs
    record("game_designer_v3", state.get("game_design_v3"))
    record("scene_architect_v3", state.get("scene_specs_v3"))
    record("interaction_designer_v3", state.get("interaction_specs_v3"))
    record("asset_generator_v3", state.get("generated_assets_v3"))

    # V4 pipeline outputs
    record("v4_input_analyzer", state.get("pedagogical_context"))
    record("v4_dk_retriever", state.get("domain_knowledge"))
    record("v4_game_designer", state.get("game_plan"))
    record("v4_game_plan_validator", state.get("design_validation"))
    record("v4_content_builder", {
        "mechanic_contents": state.get("mechanic_contents"),
        "interaction_results": state.get("interaction_results"),
    } if state.get("mechanic_contents") else None)
    record("v4_asset_worker", state.get("generated_assets"))
    record("v4_assembler", state.get("blueprint"))

    # V4 Algorithm pipeline outputs
    record("v4a_dk_retriever", state.get("domain_knowledge"))
    record("v4a_game_concept_designer", state.get("game_concept"))
    record("v4a_concept_validator", state.get("concept_validation"))
    record("v4a_graph_builder", state.get("game_plan"))
    record("v4a_plan_validator", state.get("plan_validation"))
    record("v4a_scene_content_gen", state.get("scene_contents"))
    record("v4a_asset_worker", state.get("scene_assets"))
    record("v4a_blueprint_assembler", state.get("blueprint"))

    return agent_outputs


@router.get("/processes", response_model=ProcessListResponse)
async def list_processes(
    limit: int = 20,
    offset: int = 0,
    db: Session = Depends(get_db)
) -> ProcessListResponse:
    """List all generation processes with their questions"""
    from app.db.models import Visualization

    processes = db.query(Process).order_by(Process.created_at.desc()).offset(offset).limit(limit).all()

    result = []
    for p in processes:
        # Get question text
        question = p.question
        question_text = question.text if question else "Untitled question"

        # Get template type and thumbnail from visualization if available
        template_type = None
        thumbnail_url = None
        mechanic_type = None
        title = None
        visualization = db.query(Visualization).filter(Visualization.process_id == p.id).first()
        if visualization:
            template_type = visualization.template_type
            # Extract thumbnail URL and mechanic from blueprint
            blueprint = visualization.blueprint
            if blueprint and isinstance(blueprint, dict):
                title = blueprint.get("title")
                # Try multiple paths for diagram URL
                diagram = blueprint.get("diagram", {})
                if diagram and isinstance(diagram, dict):
                    thumbnail_url = diagram.get("assetUrl")
                # Also check scenes for multi-scene games
                if not thumbnail_url:
                    scenes = blueprint.get("scenes", [])
                    if scenes and isinstance(scenes, list) and len(scenes) > 0:
                        scene_diagram = scenes[0].get("diagram", {})
                        if scene_diagram:
                            thumbnail_url = scene_diagram.get("assetUrl")
                # Extract mechanic type from mechanics array or interactionMode
                mechanics = blueprint.get("mechanics", [])
                if mechanics and isinstance(mechanics, list) and len(mechanics) > 0:
                    mechanic_type = mechanics[0].get("type")
                if not mechanic_type:
                    mechanic_type = blueprint.get("interactionMode")

        result.append({
            "id": p.id,
            "question_id": p.question_id,
            "question_text": question_text[:200] + "..." if len(question_text) > 200 else question_text,
            "template_type": template_type,
            "thumbnail_url": thumbnail_url,
            "mechanic_type": mechanic_type,
            "title": title,
            "status": p.status,
            "current_agent": p.current_agent,
            "progress_percent": p.progress_percent,
            "error_message": p.error_message,
            "created_at": p.created_at.isoformat() if p.created_at else None,
            "completed_at": p.completed_at.isoformat() if p.completed_at else None
        })

    return {
        "processes": result,
        "total": db.query(Process).count()
    }


@router.delete("/processes/{process_id}")
async def delete_process(
    process_id: str,
    db: Session = Depends(get_db)
):
    """Delete a game process and all related records"""
    from app.db.models import (
        Visualization, AgentExecution, HumanReview,
        PipelineRun, StageExecution, ExecutionLog,
        LearningSession, AttemptRecord
    )

    process = db.query(Process).filter(Process.id == process_id).first()
    if not process:
        raise HTTPException(status_code=404, detail="Process not found")

    # Delete in dependency order (children first)
    # 1. Pipeline run children: StageExecution → ExecutionLog
    run_ids = [r.id for r in db.query(PipelineRun.id).filter(PipelineRun.process_id == process_id).all()]
    if run_ids:
        db.query(ExecutionLog).filter(ExecutionLog.run_id.in_(run_ids)).delete(synchronize_session=False)
        db.query(StageExecution).filter(StageExecution.run_id.in_(run_ids)).delete(synchronize_session=False)
        db.query(PipelineRun).filter(PipelineRun.process_id == process_id).delete(synchronize_session=False)

    # 2. Learning sessions and attempts
    viz = db.query(Visualization).filter(Visualization.process_id == process_id).first()
    if viz:
        session_ids = [s.id for s in db.query(LearningSession.id).filter(LearningSession.visualization_id == viz.id).all()]
        if session_ids:
            db.query(AttemptRecord).filter(AttemptRecord.session_id.in_(session_ids)).delete(synchronize_session=False)
            db.query(LearningSession).filter(LearningSession.visualization_id == viz.id).delete(synchronize_session=False)
        db.delete(viz)

    # 3. Agent executions, human reviews
    db.query(AgentExecution).filter(AgentExecution.process_id == process_id).delete(synchronize_session=False)
    db.query(HumanReview).filter(HumanReview.process_id == process_id).delete(synchronize_session=False)

    # 4. Process itself
    db.delete(process)
    db.commit()

    logger.info(f"Deleted process {process_id} and all related records")
    return {"status": "deleted", "process_id": process_id}


@router.post("/generate", response_model=GenerateStartResponse)
@limiter.limit("10/minute")
async def start_generation(
    request: Request,
    body: GenerateRequest,
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db)
) -> GenerateStartResponse:
    """
    Start game generation for a question.

    This endpoint:
    1. Creates a Question record
    2. Creates a Process record
    3. Starts the LangGraph pipeline in background
    4. Returns process_id for status tracking
    """
    # Create question
    question = Question(
        id=str(uuid.uuid4()),
        text=body.question_text,
        options=body.question_options
    )
    db.add(question)
    db.commit()
    db.refresh(question)

    # Create process
    process = Process(
        id=str(uuid.uuid4()),
        question_id=question.id,
        status="pending",
        thread_id=str(uuid.uuid4())  # LangGraph thread ID
    )
    db.add(process)
    db.commit()
    db.refresh(process)

    logger.info(f"Created process {process.id} for question {question.id}")

    # Use config or defaults
    if body.config is None:
        config = GenerationConfig()
    else:
        config = body.config

    topology = config.topology
    provider = config.provider
    # Accept pipeline_preset from top-level or nested config
    pipeline_preset = body.pipeline_preset or config.pipeline_preset or "interactive_diagram_hierarchical"

    # Map provider to agent config preset
    provider_to_preset = {
        "openai": "openai_only",
        "anthropic": "anthropic_only",
        "google": "gemini_only",
        "gemini": "gemini_only",
        "local": "local_only",
        "groq": "groq_free"
    }

    agent_preset = config.agent_config_preset or provider_to_preset.get(provider, "balanced")

    logger.info(f"Using pipeline_preset={pipeline_preset}, agent_preset={agent_preset}, topology={topology}")
    
    # Create initial state for state reconstruction on retry
    initial_state = agent_state.create_initial_state(
        question_id=question.id,
        question_text=body.question_text,
        question_options=body.question_options
    )
    
    run_id = create_pipeline_run(
        process_id=process.id,
        topology=topology,
        config_snapshot={
            "question_id": question.id,
            "question_text": body.question_text[:200],
            "topology": topology,
            "provider": provider,
            "agent_config_preset": agent_preset,
            "pipeline_preset": pipeline_preset,
            "thread_id": process.thread_id,
            "initial_state": initial_state
        },
        db=db
    )
    
    logger.info(f"Created pipeline run {run_id} for process {process.id}")

    # Start generation in background (run_id is already created)
    if background_tasks:
        background_tasks.add_task(
            run_generation_pipeline,
            process.id,
            question.id,
            body.question_text,
            body.question_options,
            process.thread_id,
            run_id,  # Pass the run_id so it doesn't create a duplicate
            topology=topology,  # Pass topology
            agent_preset=agent_preset,  # Pass agent model preset
            pipeline_preset=pipeline_preset  # Pass pipeline preset
        )

    return {
        "process_id": process.id,
        "run_id": run_id,  # Return run_id immediately
        "question_id": question.id,
        "status": "started",
        "message": "Game generation started"
    }


@router.get("/generate/{process_id}/status", response_model=GenerationStatusResponse)
async def get_generation_status(
    process_id: str,
    db: Session = Depends(get_db)
) -> GenerationStatusResponse:
    """Get the status of a game generation process"""
    process = db.query(Process).filter(Process.id == process_id).first()
    if not process:
        raise HTTPException(status_code=404, detail="Process not found")

    return {
        "process_id": process.id,
        "status": process.status,
        "current_agent": process.current_agent,
        "progress_percent": process.progress_percent,
        "error_message": process.error_message,
        "created_at": process.created_at.isoformat() if process.created_at else None,
        "completed_at": process.completed_at.isoformat() if process.completed_at else None
    }


@router.get("/proxy/image")
@limiter.limit("60/minute")
async def proxy_image(
    request: Request,
    url: str = Query(..., description="Image URL to proxy")
):
    """Proxy image requests to avoid CORS issues with SSRF protection"""
    try:
        decoded_url = urllib.parse.unquote(url)

        # SSRF Prevention: Validate URL before making request
        if not is_safe_url(decoded_url):
            raise HTTPException(
                status_code=400,
                detail="Invalid or blocked URL. Only public HTTP(S) URLs are allowed."
            )

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(decoded_url)
            response.raise_for_status()

            # Determine content type
            content_type = response.headers.get("content-type", "image/png")

            return Response(
                content=response.content,
                media_type=content_type,
                headers={
                    "Cache-Control": "public, max-age=3600",
                    "Access-Control-Allow-Origin": "*",
                }
            )
    except HTTPException:
        raise  # Re-raise HTTP exceptions as-is
    except httpx.HTTPError as e:
        user_msg, _ = sanitize_error_for_client(e, "proxy_image")
        raise HTTPException(status_code=502, detail=user_msg)
    except Exception as e:
        user_msg, _ = sanitize_error_for_client(e, "proxy_image")
        raise HTTPException(status_code=500, detail=user_msg)


@router.get("/assets/v3/{run_id}/{filename}")
async def serve_v3_asset(run_id: str, filename: str):
    """Serve V3 pipeline-generated images (diagrams, cleaned versions)."""
    from pathlib import Path
    from fastapi.responses import FileResponse
    import re

    # Sanitize filename — only allow safe characters
    if not re.match(r'^[a-zA-Z0-9_\-\.]+\.(png|jpg|jpeg|svg|gif|webp)$', filename):
        raise HTTPException(status_code=400, detail="Invalid filename")

    base_path = Path(__file__).parent.parent.parent
    asset_path = base_path / "pipeline_outputs" / "v3_assets" / run_id / filename

    if not asset_path.exists():
        # Try subdirectories (scenes may be stored in scene_1/, scene_2/, etc.)
        v3_dir = base_path / "pipeline_outputs" / "v3_assets" / run_id
        if v3_dir.exists():
            for sub in v3_dir.rglob(filename):
                asset_path = sub
                break

    if not asset_path.exists():
        raise HTTPException(status_code=404, detail=f"V3 asset not found: {filename}")

    suffix_to_type = {
        ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
        ".svg": "image/svg+xml", ".gif": "image/gif", ".webp": "image/webp",
    }
    content_type = suffix_to_type.get(asset_path.suffix.lower(), "image/png")

    return FileResponse(
        asset_path,
        media_type=content_type,
        headers={
            "Cache-Control": "public, max-age=3600",
            "Access-Control-Allow-Origin": "*",
        }
    )


@router.get("/assets/generated-diagrams/{filename}")
async def serve_generated_diagram(filename: str):
    """Serve images from pipeline_outputs/generated_diagrams/."""
    from pathlib import Path
    from fastapi.responses import FileResponse
    import re

    if not re.match(r'^[a-zA-Z0-9_\-\.]+\.(png|jpg|jpeg|svg|gif|webp)$', filename):
        raise HTTPException(status_code=400, detail="Invalid filename")

    base_path = Path(__file__).parent.parent.parent
    asset_path = base_path / "pipeline_outputs" / "generated_diagrams" / filename

    if not asset_path.exists():
        raise HTTPException(status_code=404, detail=f"Generated diagram not found: {filename}")

    suffix_to_type = {
        ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
        ".svg": "image/svg+xml", ".gif": "image/gif", ".webp": "image/webp",
    }
    content_type = suffix_to_type.get(asset_path.suffix.lower(), "image/png")

    return FileResponse(
        asset_path,
        media_type=content_type,
        headers={
            "Cache-Control": "public, max-age=3600",
            "Access-Control-Allow-Origin": "*",
        }
    )


@router.get("/assets/{question_id}/cleaned/diagram_cleaned.png")
async def serve_cleaned_image(question_id: str):
    """Serve cleaned diagram images (with text removed)"""
    from pathlib import Path
    from fastapi.responses import FileResponse
    
    # Construct path to cleaned image
    base_path = Path(__file__).parent.parent.parent
    cleaned_image_path = base_path / "pipeline_outputs" / "assets" / question_id / "cleaned" / "diagram_cleaned.png"
    
    if not cleaned_image_path.exists():
        # Try alternative path
        cleaned_image_path = base_path / "pipeline_outputs" / "assets" / question_id / "cleaned_image.png"
    
    if not cleaned_image_path.exists():
        # Try to find by searching for any cleaned image in assets
        assets_dir = base_path / "pipeline_outputs" / "assets"
        if assets_dir.exists():
            # Search for cleaned images
            for asset_dir in assets_dir.iterdir():
                if asset_dir.is_dir():
                    cleaned_file = asset_dir / "cleaned" / "diagram_cleaned.png"
                    if cleaned_file.exists():
                        cleaned_image_path = cleaned_file
                        logger.info(f"Found cleaned image at alternative path: {cleaned_image_path}")
                        break
    
    if not cleaned_image_path.exists():
        raise HTTPException(
            status_code=404, 
            detail=f"Cleaned image not found for question {question_id}. Searched: {base_path / 'pipeline_outputs' / 'assets' / question_id}"
        )
    
    return FileResponse(
        cleaned_image_path,
        media_type="image/png",
        headers={
            "Cache-Control": "public, max-age=3600",
            "Access-Control-Allow-Origin": "*",
        }
    )


@router.get("/assets/{question_id}/generated/diagram.png")
async def serve_generated_diagram(question_id: str, db: Session = Depends(get_db)):
    """Serve AI-generated diagram images (from Gemini Imagen)"""
    from pathlib import Path
    from fastapi.responses import FileResponse
    from app.db.models import PipelineRun, StageExecution

    base_path = Path(__file__).parent.parent.parent

    # First, check for local file directly in assets directory
    local_asset_path = base_path / "pipeline_outputs" / "assets" / question_id / "generated" / "diagram.png"
    if local_asset_path.exists():
        logger.info(f"Serving generated diagram from local assets: {local_asset_path}")
        return FileResponse(
            local_asset_path,
            media_type="image/png",
            headers={
                "Cache-Control": "public, max-age=3600",
                "Access-Control-Allow-Origin": "*",
            }
        )

    # Try to find the generated diagram from the pipeline stage output
    try:
        # Find the process for this question
        process = db.query(Process).filter(Process.question_id == question_id).first()
        if process:
            # Get the most recent successful run
            run = db.query(PipelineRun).filter(
                PipelineRun.process_id == process.id,
                PipelineRun.status == "success"
            ).order_by(PipelineRun.started_at.desc()).first()

            if run:
                # Find diagram from stage outputs — check both standalone and workflow modes
                for stage_name in ["diagram_image_generator", "asset_generator_orchestrator"]:
                    stage = db.query(StageExecution).filter(
                        StageExecution.run_id == run.id,
                        StageExecution.stage_name == stage_name,
                        StageExecution.status == "success"
                    ).first()

                    if stage and stage.output_snapshot:
                        generated_path = stage.output_snapshot.get("generated_diagram_path")
                        if generated_path:
                            full_path = base_path / generated_path
                            if full_path.exists():
                                logger.info(f"Serving generated diagram from {stage_name}: {full_path}")
                                return FileResponse(
                                    full_path,
                                    media_type="image/png",
                                    headers={
                                        "Cache-Control": "public, max-age=3600",
                                        "Access-Control-Allow-Origin": "*",
                                    }
                                )
    except Exception as e:
        logger.warning(f"Error finding generated diagram from pipeline state: {e}")

    # Don't use fallback that returns random wrong images
    # Instead, return 404 so the frontend can show a placeholder
    raise HTTPException(
        status_code=404,
        detail=f"Generated diagram not found for question {question_id}"
    )


@router.get("/assets/workflow/{filename}")
async def serve_workflow_image(filename: str):
    """Serve workflow-generated images (diagrams saved by labeling_diagram_workflow)."""
    from pathlib import Path
    from fastapi.responses import FileResponse
    import re

    # Sanitize filename — only allow safe characters
    if not re.match(r'^[a-zA-Z0-9_\-]+\.(png|jpg|jpeg|svg|gif|webp)$', filename):
        raise HTTPException(status_code=400, detail="Invalid filename")

    base_path = Path(__file__).parent.parent.parent
    image_path = base_path / "pipeline_outputs" / "workflow_images" / filename

    if not image_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Workflow image not found: {filename}"
        )

    # Determine content type
    suffix_to_type = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".svg": "image/svg+xml",
        ".gif": "image/gif",
        ".webp": "image/webp",
    }
    content_type = suffix_to_type.get(image_path.suffix.lower(), "image/png")

    return FileResponse(
        image_path,
        media_type=content_type,
        headers={
            "Cache-Control": "public, max-age=3600",
            "Access-Control-Allow-Origin": "*",
        }
    )


@router.get("/assets/demo/{game_id}/{rest_path:path}")
async def serve_demo_asset(game_id: str, rest_path: str):
    """Serve demo game assets from backend/assets/demo/{game_id}/."""
    from pathlib import Path
    from fastapi.responses import FileResponse
    import re

    # Sanitize path components
    if ".." in rest_path or ".." in game_id:
        raise HTTPException(status_code=400, detail="Invalid path")

    base_path = Path(__file__).parent.parent.parent
    asset_path = base_path / "assets" / "demo" / game_id / rest_path

    if not asset_path.exists() or not asset_path.is_file():
        raise HTTPException(status_code=404, detail=f"Asset not found: {game_id}/{rest_path}")

    suffix_to_type = {
        ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
        ".svg": "image/svg+xml", ".gif": "image/gif", ".webp": "image/webp",
        ".json": "application/json",
    }
    content_type = suffix_to_type.get(asset_path.suffix.lower(), "application/octet-stream")

    return FileResponse(
        asset_path,
        media_type=content_type,
        headers={"Cache-Control": "public, max-age=3600", "Access-Control-Allow-Origin": "*"},
    )


@router.get("/generate/{process_id}/blueprint", response_model=BlueprintResponse)
async def get_generated_blueprint(
    process_id: str,
    db: Session = Depends(get_db)
) -> BlueprintResponse:
    """Get the generated blueprint for a completed process"""
    from app.db.models import Visualization
    from fastapi.responses import JSONResponse

    process = db.query(Process).filter(Process.id == process_id).first()
    if not process:
        raise HTTPException(status_code=404, detail="Process not found")

    if process.status != "completed":
        raise HTTPException(status_code=400, detail=f"Process not completed (status: {process.status})")

    visualization = db.query(Visualization).filter(Visualization.process_id == process_id).first()
    if not visualization:
        raise HTTPException(status_code=404, detail="No visualization found for this process")

    blueprint = visualization.blueprint
    question_id = process.question_id
    
    # Handle image URLs - ALWAYS prefer cleaned image if it exists
    if isinstance(blueprint, dict) and blueprint.get("diagram"):
        diagram = blueprint["diagram"]
        
        # First priority: Check if cleaned image exists and use it
        if question_id:
            from pathlib import Path
            base_path = Path(__file__).parent.parent.parent
            cleaned_image_path = base_path / "pipeline_outputs" / "assets" / question_id / "cleaned" / "diagram_cleaned.png"
            if cleaned_image_path.exists():
                diagram["assetUrl"] = f"/api/assets/{question_id}/cleaned/diagram_cleaned.png"
                logger.info(f"✅ Using cleaned image (text removed) for blueprint: {diagram['assetUrl']}")
            else:
                # Fallback: Use original image directly
                # External URLs work fine in <img> tags (no CORS issues for images)
                asset_url = diagram.get("assetUrl")
                if asset_url and asset_url.startswith("http"):
                    logger.info(f"Using external image directly: {asset_url[:80]}")
                elif asset_url and asset_url.startswith("/api/assets/"):
                    # Already a local asset URL - keep as-is
                    pass

    # Handle multi-scene image URLs: each scene in game_sequence may have its own diagram
    if isinstance(blueprint, dict) and blueprint.get("is_multi_scene") and blueprint.get("game_sequence"):
        game_seq = blueprint["game_sequence"]
        for scene in game_seq.get("scenes", []):
            scene_diagram = scene.get("diagram", {})
            if isinstance(scene_diagram, dict):
                for key in ("assetUrl", "cleanedUrl", "originalUrl"):
                    asset_url = scene_diagram.get(key, "")
                    if not asset_url:
                        continue
                    # V3 local paths → serve via V3 asset route
                    if "pipeline_outputs/v3_assets" in asset_url or (asset_url.startswith("/") and "v3_assets" in asset_url):
                        from pathlib import Path as _Path
                        filename = _Path(asset_url).name
                        # Extract run_id from path: pipeline_outputs/v3_assets/{run_id}/...
                        parts = asset_url.replace("\\", "/").split("/")
                        v3_idx = next((i for i, p in enumerate(parts) if p == "v3_assets"), -1)
                        run_id_part = parts[v3_idx + 1] if v3_idx >= 0 and v3_idx + 1 < len(parts) else process_id
                        scene_diagram[key] = f"/api/assets/v3/{run_id_part}/{filename}"
                    elif "pipeline_outputs/generated_diagrams" in asset_url or "generated_diagrams/" in asset_url:
                        from pathlib import Path as _Path
                        filename = _Path(asset_url).name
                        scene_diagram[key] = f"/api/assets/generated-diagrams/{filename}"
                    elif asset_url.startswith("http") and "/api/assets/" not in asset_url:
                        pass  # External URLs work fine in <img> tags

    return {
        "process_id": process_id,
        "template_type": visualization.template_type,
        "blueprint": blueprint,
        "story_data": visualization.story_data,
        "pedagogical_context": visualization.pedagogical_context,
        "game_plan": visualization.game_plan,
        "created_at": visualization.created_at.isoformat() if visualization.created_at else None
    }


@router.post("/generate/{process_id}/resume")
async def resume_generation(
    process_id: str,
    human_feedback: Optional[str] = None,
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db)
):
    """
    Resume a paused generation process (after human review).
    """
    process = db.query(Process).filter(Process.id == process_id).first()
    if not process:
        raise HTTPException(status_code=404, detail="Process not found")

    if process.status != "human_review":
        raise HTTPException(
            status_code=400,
            detail=f"Cannot resume process in status: {process.status}"
        )

    # Update process status
    process.status = "processing"
    db.commit()

    # Resume in background
    if background_tasks:
        background_tasks.add_task(
            resume_generation_pipeline,
            process.id,
            process.thread_id,
            human_feedback
        )

    return {
        "process_id": process.id,
        "status": "resuming",
        "message": "Generation resumed"
    }


async def run_generation_pipeline(
    process_id: str,
    question_id: str,
    question_text: str,
    question_options: Optional[list],
    thread_id: str,
    run_id: Optional[str] = None,
    topology: str = "T1",  # Add parameter
    agent_preset: str = "balanced",  # Add parameter for agent models
    pipeline_preset: str = "default"  # Add parameter for pipeline routing
):
    """Run the LangGraph generation pipeline"""
    from app.db.database import SessionLocal
    from app.db.models import Visualization
    from datetime import datetime
    from app.routes.pipeline import save_pipeline_run
    from app.agents.instrumentation import (
        create_pipeline_run,
        update_pipeline_run_status,
        add_execution_log
    )
    # create_initial_state is imported at module level (line 13)
    import os

    db = SessionLocal()
    start_time = datetime.utcnow()
    final_state = None
    error_message = None
    success = False
    # run_id is passed as parameter, don't overwrite it

    # Temporarily set environment variables for this run
    original_agent_preset = os.environ.get("AGENT_CONFIG_PRESET")
    original_pipeline_preset = os.environ.get("PIPELINE_PRESET")
    os.environ["AGENT_CONFIG_PRESET"] = agent_preset
    os.environ["PIPELINE_PRESET"] = pipeline_preset

    logger.info(f"Starting pipeline with PIPELINE_PRESET={pipeline_preset}, AGENT_CONFIG_PRESET={agent_preset}")
    
    try:
        # Update process status
        process = db.query(Process).filter(Process.id == process_id).first()
        process.status = "processing"
        db.commit()

        # Create pipeline run if not already created (for backward compatibility)
        if not run_id:
            topology = os.getenv("TOPOLOGY", "T1")
            
            # Create initial state for state reconstruction on retry
            initial_state = agent_state.create_initial_state(
                question_id=question_id,
                question_text=question_text,
                question_options=question_options
            )
            
            run_id = create_pipeline_run(
                process_id=process_id,
                topology=topology,
                config_snapshot={
                    "question_id": question_id,
                    "question_text": question_text[:200],
                    "topology": topology,
                    "thread_id": thread_id,
                    "initial_state": initial_state  # Store full initial state for retry reconstruction
                },
                db=db
            )
        else:
            # Update run status to running if it was pre-created
            from app.db.models import PipelineRun
            run = db.query(PipelineRun).filter(PipelineRun.id == run_id).first()
            if run:
                run.status = "running"
                if not run.started_at:
                    run.started_at = datetime.utcnow()
                db.commit()

        # Create initial state with run_id for instrumentation
        initial_state = agent_state.create_initial_state(
            question_id=question_id,
            question_text=question_text,
            question_options=question_options
        )
        initial_state["_run_id"] = run_id

        # Get compiled graph with specified topology and preset
        # Architecture presets and game-type presets that need the full graph
        # must be passed as preset to get create_game_generation_graph() wiring
        # (which includes game_designer → design_interpreter → workflow routing)
        presets_needing_full_graph = (
            "preset_1",                     # V1 — Baseline
            "preset_1_agentic_sequential",  # V1.1 — Agentic Sequential
            "preset_1_react",               # V2 — ReAct
            "had",                          # V2.5 — Hierarchical Agentic DAG
            "interactive_diagram_hierarchical",   # V1 variant — Hierarchical
            "advanced_interactive_diagram",       # V1 variant — Advanced
            "v3",                           # V3 — 5-Phase ReAct (current)
            "v4",                           # V4 — Streamlined 5-phase pipeline
            "v4_algorithm",                 # V4 Algorithm — Algorithm games pipeline
        )
        if pipeline_preset in presets_needing_full_graph:
            graph = get_compiled_graph(topology=topology, preset=pipeline_preset)
        else:
            graph = get_compiled_graph(topology=topology)

        # Run the graph with astream_events to capture checkpoints
        # This enables true resume from specific stages during retry
        config = {
            "configurable": {"thread_id": thread_id},
            "recursion_limit": 80,  # Pipeline has 25+ nodes; default 25 is too low
        }

        from app.agents.instrumentation import save_stage_checkpoint
        
        final_state = None
        last_checkpoint_id = None
        
        # Use astream_events to capture checkpoints after each node
        # This enables true resume from specific stages during retry
        logger.info(f"Starting pipeline execution with checkpointing for run {run_id}")
        
        try:
            async for event in graph.astream_events(initial_state, config, version="v2"):
                event_type = event.get("event")
                node_name = event.get("name", "")
                
                # Capture checkpoint_id when a node completes
                if event_type == "on_chain_end" and node_name:
                    # Skip internal nodes
                    if node_name in ["__start__", "__end__", "check_template_status"]:
                        continue
                    
                    # Get checkpoint_id from event metadata
                    # Checkpoint is created after node execution
                    checkpoint_id = event.get("data", {}).get("checkpoint_id")
                    if checkpoint_id:
                        last_checkpoint_id = checkpoint_id
                        # Save checkpoint_id to StageExecution
                        try:
                            save_stage_checkpoint(
                                run_id=run_id,
                                stage_name=node_name,
                                checkpoint_id=checkpoint_id,
                                db=db
                            )
                            logger.debug(f"Captured checkpoint {checkpoint_id} for stage '{node_name}'")
                        except Exception as save_error:
                            logger.warning(
                                f"Failed to save checkpoint for stage '{node_name}': {save_error}. "
                                f"Continuing execution."
                            )
                
                # Capture state updates as we go
                # Final state will be the last state update
                elif event_type == "on_chain_stream" and node_name:
                    # State updates come through on_chain_stream events
                    state_update = event.get("data", {}).get("chunk")
                    if state_update and isinstance(state_update, dict):
                        # Merge state updates to build final state
                        if final_state is None:
                            final_state = state_update.copy()
                        else:
                            final_state.update(state_update)
            
            # If we didn't get final state from stream, get it from the last checkpoint
            # or use ainvoke as fallback
            if final_state is None:
                logger.warning("astream_events did not provide final state, fetching from graph")
                # Try to get final state by invoking with the last checkpoint
                if last_checkpoint_id:
                    try:
                        config_with_checkpoint = {
                            "configurable": {
                                "thread_id": thread_id,
                                "checkpoint_id": last_checkpoint_id
                            }
                        }
                        # Get state from checkpoint
                        from langgraph.checkpoint.base import Checkpoint
                        checkpointer = graph.checkpointer
                        checkpoint = await checkpointer.aget(config_with_checkpoint)
                        if checkpoint:
                            final_state = checkpoint.get("channel_values", {})
                    except Exception as checkpoint_error:
                        logger.warning(f"Failed to get state from checkpoint: {checkpoint_error}")
                
                # If still no final state, fail rather than re-running the entire pipeline
                if final_state is None:
                    raise RuntimeError(
                        "Pipeline completed but no final state was captured from "
                        "astream_events or checkpoints. This may indicate a graph "
                        "configuration issue."
                    )
                
        except Exception as stream_error:
            logger.error(
                f"Error during astream_events execution: {stream_error}.",
                exc_info=True
            )
            # Do NOT re-run via ainvoke — that would duplicate the entire pipeline.
            # Instead, propagate the error so the process is marked as failed.
            raise

        # Update process with result
        is_complete = final_state.get("generation_complete", False)
        success = bool(is_complete)
        process.status = "completed" if is_complete else "error"
        process.current_agent = final_state.get("current_agent")
        process.error_message = final_state.get("error_message")
        process.progress_percent = 100 if is_complete else process.progress_percent
        process.completed_at = datetime.utcnow() if is_complete else None
        db.commit()
        
        # Update pipeline run status
        if run_id:
            update_pipeline_run_status(
                run_id=run_id,
                status="success" if success else "failed",
                error_message=final_state.get("error_message"),
                final_state_summary={
                    "template_type": final_state.get("template_selection", {}).get("template_type") if isinstance(final_state.get("template_selection"), dict) else None,
                    "generation_complete": is_complete,
                    "blueprint_title": final_state.get("blueprint", {}).get("title") if isinstance(final_state.get("blueprint"), dict) else None
                },
                db=db
            )

        # Save the visualization/blueprint if generation completed
        if is_complete and final_state.get("blueprint"):
            blueprint = final_state["blueprint"]
            template_type = blueprint.get("templateType", "UNKNOWN")

            visualization = Visualization(
                id=str(uuid.uuid4()),
                process_id=process_id,
                template_type=template_type,
                blueprint=blueprint,
                asset_urls=final_state.get("asset_urls"),
                pedagogical_context=final_state.get("pedagogical_context"),
                game_plan=final_state.get("game_plan"),
                story_data=final_state.get("story_data")
            )
            db.add(visualization)
            db.commit()
            logger.info(f"Saved visualization for process {process_id} (template: {template_type})")

        logger.info(f"Process {process_id} completed with status: {process.status}")

    except Exception as e:
        # Sanitize error for client exposure while logging full details
        user_msg, ref_id = sanitize_error_for_client(e, f"pipeline {process_id}")
        error_message = user_msg

        process = db.query(Process).filter(Process.id == process_id).first()
        if process:
            process.status = "error"
            # Store sanitized message with reference ID, not full traceback
            process.error_message = user_msg
            db.commit()

        # Update pipeline run status - store reference ID, not full traceback
        if run_id:
            update_pipeline_run_status(
                run_id=run_id,
                status="failed",
                error_message=user_msg,
                error_traceback=f"See server logs for reference ID: {ref_id}",
                db=db
            )
    finally:
        try:
            end_time = datetime.utcnow()
            duration_ms = int((end_time - start_time).total_seconds() * 1000)
            pipeline_state = final_state or {
                "question_id": question_id,
                "question_text": question_text,
                "question_options": question_options,
                "error_message": error_message,
                "generation_complete": success,
                "agent_history": [],
                "validation_results": {},
                "current_validation_errors": [],
            }
            agent_outputs = _build_agent_outputs(pipeline_state)
            save_pipeline_run(
                run_id=process_id,
                question_id=question_id,
                question_text=question_text,
                topology=pipeline_preset or topology or "T1",
                agent_outputs=agent_outputs,
                final_state=pipeline_state,
                success=success,
                duration_ms=duration_ms,
                error_message=error_message,
            )
            logger.info(f"Saved pipeline run {process_id} to pipeline_outputs")

            # Update pipeline run with final state summary
            if run_id and success:
                update_pipeline_run_status(
                    run_id=run_id,
                    status="success",
                    final_state_summary={
                        "template_type": pipeline_state.get("template_selection", {}).get("template_type"),
                        "blueprint_title": pipeline_state.get("blueprint", {}).get("title") if pipeline_state.get("blueprint") else None,
                        "generation_complete": pipeline_state.get("generation_complete"),
                        "duration_ms": duration_ms
                    },
                    db=db
                )
        except Exception as save_error:
            logger.error(
                f"Failed to save pipeline run {process_id}: {save_error}",
                exc_info=True
            )
        db.close()

        # Restore original presets
        if original_agent_preset:
            os.environ["AGENT_CONFIG_PRESET"] = original_agent_preset
        elif "AGENT_CONFIG_PRESET" in os.environ:
            del os.environ["AGENT_CONFIG_PRESET"]

        if original_pipeline_preset:
            os.environ["PIPELINE_PRESET"] = original_pipeline_preset
        elif "PIPELINE_PRESET" in os.environ:
            del os.environ["PIPELINE_PRESET"]


async def resume_generation_pipeline(
    process_id: str,
    thread_id: str,
    human_feedback: Optional[str]
):
    """Resume a paused LangGraph pipeline"""
    from app.db.database import SessionLocal

    db = SessionLocal()
    try:
        graph = get_compiled_graph()
        config = {
            "configurable": {"thread_id": thread_id},
            "recursion_limit": 80,
        }

        # Get current state and update with human feedback
        # Then continue execution
        # NOTE: Full LangGraph resumption requires:
        # 1. Checkpointing with SqliteSaver/PostgresSaver
        # 2. State reconstruction from checkpoint_id
        # 3. Proper interrupt/resume flow with human_feedback handling
        # See: https://langchain-ai.github.io/langgraph/how-tos/persistence/

        logger.info(f"Resumed process {process_id}")

    except Exception as e:
        logger.error(f"Resume pipeline failed: {e}", exc_info=True)
        process = db.query(Process).filter(Process.id == process_id).first()
        if process:
            process.status = "error"
            process.error_message = str(e)
            db.commit()
    finally:
        db.close()
