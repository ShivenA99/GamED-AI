"""Pipeline Orchestrator - Executes pipeline steps with validation and tracking"""
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from datetime import datetime
from app.db.models import Process, PipelineStep
from app.repositories.process_repository import ProcessRepository
from app.repositories.pipeline_step_repository import PipelineStepRepository
from app.repositories.question_repository import QuestionRepository
from app.repositories.story_repository import StoryRepository
from app.repositories.visualization_repository import VisualizationRepository
from app.repositories.game_blueprint_repository import GameBlueprintRepository
from app.services.pipeline.layer1_input import DocumentParserService, QuestionExtractorService
from app.services.pipeline.layer2_classification import ClassificationOrchestrator
from app.services.pipeline.layer2_template_router import TemplateRouter
from app.services.pipeline.layer3_strategy import StrategyOrchestrator
from app.services.pipeline.layer4_generation import GenerationOrchestrator
from app.services.pipeline.validators import get_validator
from app.services.pipeline.retry_handler import RetryHandler
from app.services.cache_service import CacheService
from app.utils.logger import setup_logger

logger = setup_logger("orchestrator")

class PipelineOrchestrator:
    """Orchestrates the complete pipeline execution"""
    
    # Define pipeline steps
    PIPELINE_STEPS = [
        {"name": "document_parsing", "number": 1, "layer": 1},
        {"name": "question_extraction", "number": 2, "layer": 1},
        {"name": "question_analysis", "number": 3, "layer": 2},
        {"name": "template_routing", "number": 4, "layer": 2},
        {"name": "strategy_creation", "number": 5, "layer": 3},
        {"name": "story_generation", "number": 6, "layer": 4},
        {"name": "blueprint_generation", "number": 7, "layer": 4},
        {"name": "asset_planning", "number": 8, "layer": 4},
        {"name": "asset_generation", "number": 9, "layer": 4},
    ]
    
    def __init__(self, db: Session):
        self.db = db
        self.retry_handler = RetryHandler(max_retries=3, initial_delay=1.0)
        
        # Initialize services
        self.document_parser = DocumentParserService()
        self.question_extractor = QuestionExtractorService()
        self.classifier = ClassificationOrchestrator()
        self.template_router = TemplateRouter()
        self.strategy_orchestrator = StrategyOrchestrator()
        self.generation_orchestrator = GenerationOrchestrator()
        self.cache_service = CacheService()
    
    def execute_pipeline(
        self,
        process_id: str,
        question_id: str,
        file_content: bytes = None,
        filename: str = None
    ) -> Dict[str, Any]:
        """Execute complete pipeline for a question"""
        logger.info(f"Starting pipeline execution - Process: {process_id}, Question: {question_id}")
        
        try:
            # Update process status
            ProcessRepository.update_status(
                self.db, process_id, "processing", progress=0, current_step="Initializing"
            )
            
            # Get question
            question = QuestionRepository.get_by_id(self.db, question_id)
            if not question:
                raise ValueError(f"Question {question_id} not found")
            
            # Track pipeline state
            pipeline_state = {
                "question_id": question_id,
                "question_text": question.text,
                "question_options": question.options,
                "file_content": file_content,
                "filename": filename,
                "parsed_data": None,
                "extracted_question": None,
                "analysis": None,
                "template_type": None,
                "strategy": None,
                "story": None,
                "blueprint": None,
                "assets": None
            }
            
            # Execute each step
            last_completed_step = PipelineStepRepository.get_last_completed_step(self.db, process_id)
            start_from_step = (last_completed_step.step_number + 1) if last_completed_step else 1
            
            for step_def in self.PIPELINE_STEPS:
                if step_def["number"] < start_from_step:
                    logger.info(f"Skipping step {step_def['number']} - already completed")
                    continue
                
                step_result = self._execute_step(
                    process_id,
                    step_def,
                    pipeline_state
                )
                
                if not step_result["success"]:
                    logger.error(f"Step {step_def['number']} failed: {step_result.get('error')}")
                    ProcessRepository.update_status(
                        self.db,
                        process_id,
                        "error",
                        current_step=step_def["name"],
                        error_message=step_result.get("error")
                    )
                    return step_result
                
                # Update pipeline state with step output
                pipeline_state.update(step_result.get("state_updates", {}))
                
                # Update progress at END of step (after it completes)
                # This ensures progress reflects completed steps
                progress = int((step_def["number"] / len(self.PIPELINE_STEPS)) * 100)
                ProcessRepository.update_status(
                    self.db,
                    process_id,
                    "processing",
                    progress=progress,
                    current_step=step_def["name"]
                )
                logger.debug(f"Updated progress to {progress}% after step {step_def['number']} completed")
            
            # Store final results
            visualization_id = self._store_results(process_id, question_id, pipeline_state)
            
            # Mark process as completed
            ProcessRepository.update_status(
                self.db,
                process_id,
                "completed",
                progress=100,
                current_step="Complete"
            )
            
            logger.info(f"Pipeline completed successfully - Process: {process_id}, Visualization: {visualization_id}")
            
            return {
                "success": True,
                "process_id": process_id,
                "visualization_id": visualization_id
            }
            
        except Exception as e:
            logger.error(f"Pipeline execution failed: {e}", exc_info=True)
            # Rollback any pending transaction before updating status
            try:
                self.db.rollback()
            except Exception:
                pass  # Ignore rollback errors if already rolled back
            
            try:
                ProcessRepository.update_status(
                    self.db,
                    process_id,
                    "error",
                    error_message=str(e)
                )
            except Exception as update_error:
                logger.error(f"Failed to update process status after error: {update_error}")
                # Rollback again if status update fails
                try:
                    self.db.rollback()
                except Exception:
                    pass
            raise
    
    def _execute_step(
        self,
        process_id: str,
        step_def: Dict[str, Any],
        pipeline_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a single pipeline step"""
        step_name = step_def["name"]
        step_number = step_def["number"]
        
        logger.info(f"Executing step {step_number}: {step_name}")
        
        # Update progress at START of step (before it completes)
        # Calculate progress based on step number: (step_number - 1) / total_steps * 100
        # This shows progress while the step is processing
        total_steps = len(self.PIPELINE_STEPS)
        progress_at_start = int(((step_number - 1) / total_steps) * 100)
        ProcessRepository.update_status(
            self.db,
            process_id,
            "processing",
            progress=progress_at_start,
            current_step=step_name
        )
        logger.debug(f"Updated progress to {progress_at_start}% at start of step {step_number}")
        
        # Create step record
        try:
            step = PipelineStepRepository.create(
                self.db,
                process_id,
                step_name,
                step_number,
                input_data=self._sanitize_for_storage(pipeline_state)
            )
        except Exception as create_error:
            # If step creation fails (e.g., JSON serialization), rollback and re-raise
            logger.error(f"Failed to create step record for {step_name}: {create_error}")
            self.db.rollback()
            raise
        
        try:
            # Update step status to processing
            PipelineStepRepository.update_status(
                self.db, step.id, "processing"
            )
            
            # Execute step based on name
            step_result = None
            state_updates = {}
            
            if step_name == "document_parsing":
                if pipeline_state.get("file_content") and pipeline_state.get("filename"):
                    result = self.document_parser.parse_document(
                        pipeline_state["file_content"],
                        pipeline_state["filename"]
                    )
                    pipeline_state["parsed_data"] = result["data"]
                    step_result = result
                else:
                    # Skip if no file content (question already in DB)
                    PipelineStepRepository.update_status(
                        self.db, step.id, "skipped",
                        output_data={"message": "File content not provided, using existing question"}
                    )
                    return {"success": True, "state_updates": {}}
            
            elif step_name == "question_extraction":
                if pipeline_state.get("parsed_data"):
                    text = pipeline_state["parsed_data"].get("full_text") or pipeline_state["parsed_data"].get("text")
                    result = self.question_extractor.extract_question(
                        text,
                        pipeline_state.get("filename")
                    )
                    pipeline_state["extracted_question"] = result["data"]
                    step_result = result
                else:
                    # Use existing question from DB
                    extracted = {
                        "text": pipeline_state["question_text"],
                        "options": pipeline_state["question_options"],
                        "file_type": "existing"
                    }
                    pipeline_state["extracted_question"] = extracted
                    step_result = {"success": True, "data": extracted}
            
            elif step_name == "question_analysis":
                question_text = pipeline_state.get("extracted_question", {}).get("text") or pipeline_state["question_text"]
                question_options = pipeline_state.get("extracted_question", {}).get("options") or pipeline_state["question_options"]
                result = self.classifier.analyze_question(question_text, question_options)
                analysis_data = result["data"]
                pipeline_state["analysis"] = analysis_data
                
                # Store analysis in database
                from app.db.models import QuestionAnalysis
                question_id = pipeline_state["question_id"]
                existing_analysis = self.db.query(QuestionAnalysis).filter(
                    QuestionAnalysis.question_id == question_id
                ).first()
                
                if existing_analysis:
                    # Update existing
                    existing_analysis.question_type = analysis_data["question_type"]
                    existing_analysis.subject = analysis_data["subject"]
                    existing_analysis.difficulty = analysis_data["difficulty"]
                    existing_analysis.key_concepts = analysis_data.get("key_concepts", [])
                    existing_analysis.intent = analysis_data.get("intent", "")
                else:
                    # Create new
                    analysis = QuestionAnalysis(
                        question_id=question_id,
                        question_type=analysis_data["question_type"],
                        subject=analysis_data["subject"],
                        difficulty=analysis_data["difficulty"],
                        key_concepts=analysis_data.get("key_concepts", []),
                        intent=analysis_data.get("intent", "")
                    )
                    self.db.add(analysis)
                
                self.db.commit()
                step_result = result
            
            elif step_name == "template_routing":
                result = self.template_router.route_template(
                    pipeline_state["question_text"],
                    pipeline_state["analysis"]
                )
                routing_data = result["data"]
                template_type = routing_data.get("templateType")
                confidence = routing_data.get("confidence", 0)
                rationale = routing_data.get("rationale", "")
                pipeline_state["template_type"] = template_type
                
                # Log template routing event
                question_id = pipeline_state.get("question_id", "unknown")
                logger.info(
                    f"event=template_routed question_id={question_id} template_type={template_type} "
                    f"confidence={confidence} rationale={rationale[:100]}"
                )
                
                step_result = result
            
            elif step_name == "strategy_creation":
                question_data = {
                    "text": pipeline_state["question_text"],
                    "options": pipeline_state["question_options"],
                    **pipeline_state["analysis"]
                }
                result = self.strategy_orchestrator.create_strategy(
                    pipeline_state["question_text"],
                    pipeline_state["analysis"]
                )
                pipeline_state["strategy"] = result["data"]
                step_result = result
            
            elif step_name == "story_generation":
                question_text = pipeline_state["question_text"]
                question_options = pipeline_state["question_options"]
                
                # Check cache first
                cached_story = self.cache_service.get_story(question_text, question_options)
                if cached_story:
                    logger.info(f"Using cached story for question: {question_text[:50]}...")
                    pipeline_state["story"] = cached_story
                    step_result = {
                        "success": True,
                        "data": cached_story,
                        "cached": True,
                        "state_updates": {"story": cached_story}
                    }
                else:
                    # Generate new story
                    question_data = {
                        "text": question_text,
                        "options": question_options,
                        **pipeline_state["analysis"]
                    }
                    result = self.generation_orchestrator.story_generator.generate(
                        question_data,
                        pipeline_state["strategy"]["prompt_template"],
                        pipeline_state["strategy"],
                        pipeline_state.get("template_type")
                    )
                    pipeline_state["story"] = result["data"]
                    
                    # Save to cache
                    self.cache_service.save_story(question_text, question_options, result["data"])
                    
                    step_result = {
                        **result,
                        "cached": False
                    }
            
            elif step_name == "blueprint_generation":
                question_text = pipeline_state["question_text"]
                question_options = pipeline_state["question_options"]
                template_type = pipeline_state["template_type"]
                
                # Check cache first
                cached_blueprint_data = self.cache_service.get_blueprint(question_text, question_options)
                if cached_blueprint_data:
                    logger.info(f"Using cached blueprint for question: {question_text[:50]}...")
                    blueprint_data = cached_blueprint_data.get("blueprint", cached_blueprint_data)
                    # Use cached template_type if available, otherwise use current
                    if "template_type" in cached_blueprint_data:
                        template_type = cached_blueprint_data["template_type"]
                    pipeline_state["blueprint"] = blueprint_data
                    is_valid = True  # Cached blueprints are assumed valid
                    step_result = {
                        "success": True,
                        "data": blueprint_data,
                        "valid": True,
                        "cached": True,
                        "state_updates": {"blueprint": blueprint_data}
                    }
                else:
                    # Generate new blueprint
                    result = self.generation_orchestrator.blueprint_generator.generate(
                        pipeline_state["story"],
                        template_type,
                        question_text
                    )
                    blueprint_data = result["data"]
                    is_valid = result.get("valid", True)
                    error_fields = result.get("error_fields", [])
                    pipeline_state["blueprint"] = blueprint_data
                    
                    # Save to cache
                    self.cache_service.save_blueprint(question_text, question_options, blueprint_data, template_type)
                    
                    step_result = {
                        **result,
                        "cached": False
                    }
                
                # Log blueprint generation event
                question_id = pipeline_state.get("question_id", "unknown")
                is_cached = step_result.get("cached", False)
                logger.info(
                    f"event=blueprint_generated question_id={question_id} template_type={template_type} "
                    f"valid={is_valid} cached={is_cached}"
                )
            
            elif step_name == "asset_planning":
                asset_requests = self.generation_orchestrator.asset_planner.plan_assets(
                    pipeline_state["blueprint"]
                )
                asset_request_count = len(asset_requests)
                pipeline_state["asset_requests"] = asset_requests
                
                # Log asset planning event with details
                question_id = pipeline_state.get("question_id", "unknown")
                template_type = pipeline_state.get("template_type", "unknown")
                
                # Log each asset request
                asset_details = []
                for req in asset_requests:
                    asset_details.append({
                        "type": req.type,
                        "purpose": req.purpose,
                        "prompt_preview": req.prompt[:100] if req.prompt else ""
                    })
                    logger.info(
                        f"event=asset_planned question_id={question_id} template_type={template_type} "
                        f"asset_type={req.type} purpose={req.purpose} prompt={req.prompt[:100]}"
                    )
                
                logger.info(
                    f"event=assets_planned question_id={question_id} template_type={template_type} "
                    f"asset_request_count={asset_request_count}"
                )
                
                step_result = {
                    "success": True,
                    "data": {
                        "asset_request_count": asset_request_count,
                        "asset_requests": asset_details
                    }
                }
            
            elif step_name == "asset_generation":
                asset_requests = pipeline_state.get("asset_requests", [])
                question_id = pipeline_state.get("question_id", "unknown")
                template_type = pipeline_state.get("template_type", "unknown")
                
                # Log start of asset generation
                logger.info(
                    f"event=asset_generation_started question_id={question_id} template_type={template_type} "
                    f"total_assets={len(asset_requests)}"
                )
                
                asset_urls = self.generation_orchestrator.asset_generator.generate_assets(
                    asset_requests
                )
                
                # Inject asset URLs into blueprint
                pipeline_state["blueprint"] = self.generation_orchestrator.asset_generator.inject_asset_urls(
                    pipeline_state["blueprint"],
                    asset_urls
                )
                pipeline_state["assets"] = asset_urls
                
                # Log detailed asset generation events
                generated_count = 0
                failed_count = 0
                asset_results = []
                
                for req in asset_requests:
                    purpose = req.purpose
                    url = asset_urls.get(purpose)
                    
                    if url:
                        generated_count += 1
                        is_dalle = "dalle" in url.lower() or "openai" in url.lower() or url.startswith("https://oaidalle")
                        asset_type = "dalle" if is_dalle else "placeholder"
                        
                        asset_results.append({
                            "purpose": purpose,
                            "type": req.type,
                            "status": "success",
                            "url": url,
                            "generation_method": asset_type
                        })
                        
                        logger.info(
                            f"event=asset_generated question_id={question_id} template_type={template_type} "
                            f"asset_type={req.type} purpose={purpose} generation_method={asset_type} "
                            f"url={url[:100]}"
                        )
                    else:
                        failed_count += 1
                        asset_results.append({
                            "purpose": purpose,
                            "type": req.type,
                            "status": "failed",
                            "error": "No URL generated"
                        })
                        
                        logger.warning(
                            f"event=asset_generation_failed question_id={question_id} template_type={template_type} "
                            f"asset_type={req.type} purpose={purpose}"
                        )
                
                # Log summary
                logger.info(
                    f"event=asset_generation_complete question_id={question_id} template_type={template_type} "
                    f"total={len(asset_requests)} generated={generated_count} failed={failed_count}"
                )
                
                step_result = {
                    "success": True,
                    "data": {
                        "asset_urls": asset_urls,
                        "generated_count": generated_count,
                        "failed_count": failed_count,
                        "asset_results": asset_results
                    }
                }
            
            # Validate step output
            validator = get_validator(step_name)
            if validator and step_result:
                validation_result = validator.validate(step_result.get("data", {}))
                if not validation_result.is_valid:
                    raise ValueError(f"Step validation failed: {', '.join(validation_result.errors)}")
            
            # Update step as completed
            # Include cache information in output_data
            output_data = self._sanitize_for_storage(step_result.get("data", {}))
            if step_result.get("cached"):
                output_data["_cached"] = True
            
            PipelineStepRepository.update_status(
                self.db,
                step.id,
                "completed",
                output_data=output_data,
                validation_result=step_result.get("validation") if step_result else None
            )
            
            logger.info(f"Step {step_number} completed successfully: {step_name}")
            
            return {
                "success": True,
                "state_updates": state_updates
            }
            
        except Exception as e:
            logger.error(f"Step {step_number} failed: {e}", exc_info=True)
            
            # Update step as error
            PipelineStepRepository.update_status(
                self.db,
                step.id,
                "error",
                error_message=str(e)
            )
            
            return {
                "success": False,
                "error": str(e)
            }
    
    def _store_results(
        self,
        process_id: str,
        question_id: str,
        pipeline_state: Dict[str, Any]
    ) -> str:
        """Store final results in database"""
        logger.info("Storing pipeline results")
        
        # Store story if generated
        story_data = pipeline_state.get("story")
        if story_data:
            StoryRepository.create(self.db, question_id, story_data)
        
        # Store blueprint if generated
        blueprint_data = pipeline_state.get("blueprint")
        assets_data = pipeline_state.get("assets", {})
        blueprint_id = None
        
        if blueprint_data:
            template_type = pipeline_state.get("template_type", "SEQUENCE_BUILDER")
            blueprint = GameBlueprintRepository.create(
                self.db,
                question_id,
                template_type,
                blueprint_data,
                assets_data
            )
            blueprint_id = blueprint.id
            
            # Log blueprint saved event
            logger.info(
                f"event=blueprint_saved blueprint_id={blueprint_id} question_id={question_id} "
                f"template_type={template_type}"
            )
        
        # Store visualization (backward compatibility - may have HTML or blueprint)
        html_content = pipeline_state.get("html", "")
        visualization = VisualizationRepository.create(
            self.db,
            process_id,
            question_id,
            html_content,
            story_data or {}
        )
        
        # Link blueprint to visualization if available
        if blueprint_id:
            visualization.blueprint_id = blueprint_id
            self.db.commit()
        
        return visualization.id
    
    def _sanitize_for_storage(self, data: Any) -> Any:
        """Sanitize data for database storage (remove large binary data, etc.)"""
        # Handle AssetRequest objects (convert to dict for JSON serialization)
        if hasattr(data, 'type') and hasattr(data, 'purpose') and hasattr(data, 'prompt'):
            # This is an AssetRequest object - convert to dict
            return {
                "type": getattr(data, 'type', None),
                "purpose": getattr(data, 'purpose', None),
                "prompt": getattr(data, 'prompt', None)
            }
        if isinstance(data, dict):
            sanitized = {}
            for key, value in data.items():
                if key in ["file_content"]:
                    # Don't store binary data
                    sanitized[key] = f"<binary data: {len(value) if value else 0} bytes>"
                elif isinstance(value, (dict, list)):
                    sanitized[key] = self._sanitize_for_storage(value)
                else:
                    sanitized[key] = self._sanitize_for_storage(value)  # Recursively sanitize
            return sanitized
        elif isinstance(data, list):
            return [self._sanitize_for_storage(item) for item in data]
        else:
            return data
    
    def retry_step(self, step_id: str) -> Dict[str, Any]:
        """Retry a failed step"""
        logger.info(f"Retrying step: {step_id}")
        
        step = PipelineStepRepository.get_by_id(self.db, step_id)
        if not step:
            raise ValueError(f"Step {step_id} not found")
        
        if step.status != "error":
            raise ValueError(f"Step {step_id} is not in error state")
        
        # Increment retry count
        PipelineStepRepository.increment_retry(self.db, step_id)
        
        # Get process and question
        process = ProcessRepository.get_by_id(self.db, step.process_id)
        question = QuestionRepository.get_by_id(self.db, process.question_id)
        
        # Rebuild pipeline state from completed steps
        pipeline_state = {
            "question_id": question.id,
            "question_text": question.text,
            "question_options": question.options,
        }
        
        # Get all completed steps to rebuild state
        completed_steps = [
            s for s in PipelineStepRepository.get_by_process_id(self.db, step.process_id)
            if s.status == "completed" and s.step_number < step.step_number
        ]
        
        # Rebuild state from completed steps
        for completed_step in completed_steps:
            if completed_step.output_data:
                pipeline_state.update(completed_step.output_data)
        
        # Find step definition
        step_def = next(
            (s for s in self.PIPELINE_STEPS if s["name"] == step.step_name),
            None
        )
        
        if not step_def:
            raise ValueError(f"Unknown step: {step.step_name}")
        
        # Execute step
        result = self._execute_step(process.id, step_def, pipeline_state)
        
        return result

