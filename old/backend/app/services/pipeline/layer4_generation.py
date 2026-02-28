"""Layer 4: Multi-Modal Content Generation"""
from typing import Dict, Any, Optional
from pathlib import Path
from app.services.llm_service import LLMService
from app.services.pipeline.validators import StoryValidator, HTMLValidator, ValidationResult
from app.services.template_registry import get_registry
from app.utils.logger import setup_logger
import json

logger = setup_logger("layer4_generation")

class StoryGenerator:
    """Generate story data from question and strategy"""
    
    def __init__(self):
        self.llm_service = LLMService()
        self.validator = StoryValidator()
    
    def generate(
        self,
        question_data: Dict[str, Any],
        prompt_template: str,
        strategy: Dict[str, Any] = None,
        template_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate complete story data"""
        
        # Load base story prompt
        base_prompt_path = Path(__file__).parent.parent.parent.parent / "prompts" / "story_base.md"
        try:
            with open(base_prompt_path, 'r', encoding='utf-8') as f:
                base_prompt = f.read()
        except Exception as e:
            logger.warning(f"Failed to load story_base.md, using provided template: {e}")
            base_prompt = prompt_template
        
        # Load template-specific supplement if template_type is provided
        system_prompt = base_prompt
        actual_template = template_type  # Track the actual template being used
        if template_type:
            # Check if this is an algorithmic/coding question - use ALGORITHM_VISUALIZATION for any coding/algorithm question
            question_type = question_data.get('question_type', '')
            subject = question_data.get('subject', '')
            key_concepts = question_data.get('key_concepts', [])
            question_text = question_data.get('text', '').lower()
            
            # Check if this is an algorithmic/coding question (regardless of initial template routing)
            # If template is STATE_TRACER_CODE or PARAMETER_PLAYGROUND, route to ALGORITHM_VISUALIZATION
            is_algorithmic = (
                template_type in ["PARAMETER_PLAYGROUND", "STATE_TRACER_CODE"] or
                question_type == "coding" or 
                "algorithm" in str(key_concepts).lower() or
                "coding" in subject.lower() or
                any(concept in ["binary search", "sorting", "graph", "cycle", "two pointer", "sliding window", "dynamic programming", "floyd", "tortoise", "hare", "duplicate", "array", "linked list"] 
                    for concept in str(key_concepts).lower() + question_text)
            )
            
            # Use ALGORITHM_VISUALIZATION for algorithmic questions, otherwise use template_type
            template_name = "ALGORITHM_VISUALIZATION" if is_algorithmic else template_type
            actual_template = template_name  # Update to show actual template being used
            
            template_supplement_path = Path(__file__).parent.parent.parent.parent / "prompts" / "story_templates" / f"{template_name}.txt"
            try:
                with open(template_supplement_path, 'r', encoding='utf-8') as f:
                    template_supplement = f.read()
                    system_prompt = base_prompt + "\n\n" + template_supplement
                    logger.info(f"Generating story data (template: {template_name})")
                    if is_algorithmic:
                        logger.info(f"Using ALGORITHM_VISUALIZATION template for algorithmic question (routed from {template_type})")
            except Exception as e:
                # Fallback to original template_type if ALGORITHM_VISUALIZATION doesn't exist
                if is_algorithmic:
                    template_supplement_path = Path(__file__).parent.parent.parent.parent / "prompts" / "story_templates" / f"{template_type}.txt"
                    try:
                        with open(template_supplement_path, 'r', encoding='utf-8') as f:
                            template_supplement = f.read()
                            system_prompt = base_prompt + "\n\n" + template_supplement
                            logger.info(f"Loaded fallback template supplement for {template_type}")
                    except Exception as e2:
                        logger.warning(f"Failed to load template supplement for {template_type}: {e2}")
                else:
                    logger.warning(f"Failed to load template supplement for {template_type}: {e}")
                # Use base prompt only
        
        user_prompt = f"""Generate a story-based visualization for the following question:

Question: {question_data.get('text', '')}
Options: {question_data.get('options', [])}
Type: {question_data.get('question_type', 'reasoning')}
Subject: {question_data.get('subject', 'General')}
Difficulty: {question_data.get('difficulty', 'intermediate')}
Key Concepts: {question_data.get('key_concepts', [])}
Intent: {question_data.get('intent', '')}

Game Format: {strategy.get('game_format', 'quiz') if strategy else 'quiz'}
Storyline: {json.dumps(strategy.get('storyline', {}), indent=2) if strategy else 'None'}
TemplateType: {template_type if template_type else 'Not specified'}

Follow the schema and requirements in the system prompt. Respond with ONLY valid JSON matching the output schema."""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        try:
            # Try OpenAI first, fallback to Anthropic
            try:
                logger.info("Attempting story generation with OpenAI...")
                response = self.llm_service.call_llm(messages, use_anthropic=False)
            except Exception as e:
                logger.warning(f"OpenAI failed, trying Anthropic: {e}")
                response = self.llm_service.call_llm(messages, use_anthropic=True)
            
            # Extract JSON
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                response = response.split("```")[1].split("```")[0].strip()
            
            story_data = json.loads(response)
            
            # Log the raw story data for debugging (first 500 chars)
            logger.debug(f"Raw story data received: {json.dumps(story_data, indent=2)[:500]}...")
            
            # Normalize question_flow field names for consistency
            # The prompt schema uses "intuitive_question", but we normalize to "question_text" for consistency
            if "question_flow" in story_data and isinstance(story_data["question_flow"], list):
                for q in story_data["question_flow"]:
                    if isinstance(q, dict):
                        # Normalize field names - use question_text as standard
                        # Priority: intuitive_question (from schema) > question_text > text > question > content
                        if "intuitive_question" in q and "question_text" not in q:
                            q["question_text"] = q.pop("intuitive_question")
                        elif "text" in q and "question_text" not in q:
                            q["question_text"] = q.pop("text")
                        elif "question" in q and "question_text" not in q:
                            q["question_text"] = q.pop("question")
                        elif "content" in q and "question_text" not in q:
                            q["question_text"] = q.pop("content")
            
            # Validate story data
            validation_result = self.validator.validate(story_data)
            
            if not validation_result.is_valid:
                logger.error(f"Story validation failed: {validation_result.errors}")
                raise ValueError(f"Story validation failed: {', '.join(validation_result.errors)}")
            
            if validation_result.warnings:
                logger.warning(f"Story validation warnings: {validation_result.warnings}")
            
            logger.info(f"Story generated successfully - Title: {story_data.get('story_title', 'Untitled')}")
            
            # Log story generation event (if we have question_id context, it would be passed)
            # For now, log with template type
            logger.info(
                f"event=story_generated template_type={template_type or 'unknown'} "
                f"success=True token_count=unknown"
            )
            
            return {
                "success": True,
                "data": story_data,
                "validation": validation_result.to_dict()
            }
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse story JSON: {e}")
            raise ValueError(f"Failed to parse story JSON: {e}")
        except Exception as e:
            logger.error(f"Story generation failed: {e}", exc_info=True)
            raise

class HTMLGenerator:
    """Generate HTML visualization from story data"""
    
    def __init__(self):
        self.llm_service = LLMService()
        self.validator = HTMLValidator()
    
    def generate(self, story_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate HTML visualization"""
        logger.info("Generating HTML visualization")
        
        prompt = f"""Generate a complete, interactive HTML page for the following story-based visualization.

Story Data:
{json.dumps(story_data, indent=2)}

Requirements:
1. Questions must be prominently displayed at the top
2. Answer submission is required before showing results
3. Visual feedback on answers (green for correct, red for incorrect)
4. Interactive animations and visual elements
5. Responsive design
6. Include all CSS and JavaScript inline

Generate ONLY the HTML code, no markdown, no explanations."""
        
        messages = [
            {"role": "system", "content": "You are an expert web developer. Generate complete, functional HTML pages with inline CSS and JavaScript."},
            {"role": "user", "content": prompt}
        ]
        
        try:
            # Try OpenAI first, fallback to Anthropic
            try:
                logger.info("Attempting HTML generation with OpenAI...")
                response = self.llm_service.call_llm(messages, use_anthropic=False)
            except Exception as e:
                logger.warning(f"OpenAI failed, trying Anthropic: {e}")
                response = self.llm_service.call_llm(messages, use_anthropic=True)
            
            # Extract HTML
            if "```html" in response:
                response = response.split("```html")[1].split("```")[0].strip()
            elif "```" in response:
                response = response.split("```")[1].split("```")[0].strip()
            
            # Validate HTML
            validation_result = self.validator.validate({"html": response})
            
            if not validation_result.is_valid:
                logger.error(f"HTML validation failed: {validation_result.errors}")
                raise ValueError(f"HTML validation failed: {', '.join(validation_result.errors)}")
            
            if validation_result.warnings:
                logger.warning(f"HTML validation warnings: {validation_result.warnings}")
            
            logger.info(f"HTML generated successfully - Length: {len(response)} chars")
            
            return {
                "success": True,
                "data": {"html": response},
                "validation": validation_result.to_dict()
            }
        except Exception as e:
            logger.error(f"HTML generation failed: {e}", exc_info=True)
            raise

class ImageGenerator:
    """Generate images for visualizations using DALL-E"""
    
    def __init__(self):
        self.llm_service = LLMService()
        self.openai_client = None
        if self.llm_service.openai_client:
            self.openai_client = self.llm_service.openai_client
    
    def generate(self, description: str, size: str = "1024x1024") -> Dict[str, Any]:
        """Generate image from description using DALL-E"""
        if not self.openai_client:
            logger.warning("OpenAI client not available for image generation")
            return {
                "success": False,
                "message": "OpenAI client not configured"
            }
        
        try:
            logger.info(f"Generating image: {description[:100]}...")
            
            # Enhanced prompt for educational content
            enhanced_prompt = f"Educational illustration, clear and colorful, suitable for learning: {description}"
            
            response = self.openai_client.images.generate(
                model="dall-e-3",
                prompt=enhanced_prompt,
                size=size,
                quality="standard",
                n=1,
            )
            
            image_url = response.data[0].url
            logger.info(f"Image generated successfully: {image_url[:100]}...")
            
            return {
                "success": True,
                "url": image_url,
                "description": description
            }
            
        except Exception as e:
            logger.error(f"Failed to generate image: {e}")
            return {
                "success": False,
                "message": f"Image generation failed: {str(e)}"
            }

class AnimationGenerator:
    """Generate animations using DALL-E frame sequences"""
    
    def __init__(self):
        self.llm_service = LLMService()
        self.openai_client = None
        if self.llm_service.openai_client:
            self.openai_client = self.llm_service.openai_client
    
    def generate(self, animation_spec: Dict[str, Any]) -> Dict[str, Any]:
        """Generate animation from specification using multiple DALL-E frames"""
        if not self.openai_client:
            logger.warning("OpenAI client not available for animation generation")
            return {
                "success": False,
                "message": "OpenAI client not configured"
            }
        
        try:
            prompt = animation_spec.get("prompt", "")
            frames = animation_spec.get("frames", 5)
            
            logger.info(f"Generating animation: {prompt[:100]}... ({frames} frames)")
            
            # Generate multiple frames
            frame_urls = []
            for i in range(frames):
                frame_prompt = f"{prompt}, frame {i+1} of {frames}, showing progression step by step"
                
                try:
                    response = self.openai_client.images.generate(
                        model="dall-e-3",
                        prompt=f"Educational illustration, clear and colorful: {frame_prompt}",
                        size="1024x1024",
                        quality="standard",
                        n=1,
                    )
                    frame_urls.append(response.data[0].url)
                    logger.info(f"Generated frame {i+1}/{frames}")
                except Exception as e:
                    logger.warning(f"Failed to generate frame {i+1}: {e}")
            
            if frame_urls:
                # Return first frame URL as the animation representation
                # In production, combine frames into GIF using PIL/Pillow
                logger.info(f"Generated {len(frame_urls)} animation frames")
                return {
                    "success": True,
                    "url": frame_urls[0],  # First frame as placeholder
                    "frames": frame_urls,
                    "frame_count": len(frame_urls)
                }
            else:
                return {
                    "success": False,
                    "message": "Failed to generate any animation frames"
                }
                
        except Exception as e:
            logger.error(f"Failed to generate animation: {e}")
            return {
                "success": False,
                "message": f"Animation generation failed: {str(e)}"
            }

class BlueprintGenerator:
    """Generate game blueprint JSON from story data and template"""
    
    def __init__(self):
        self.llm_service = LLMService()
        self.template_registry = get_registry()
        self._load_base_prompt()
    
    def _load_base_prompt(self):
        """Load base blueprint prompt"""
        prompt_path = Path(__file__).parent.parent.parent.parent / "prompts" / "blueprint_base.md"
        try:
            with open(prompt_path, 'r', encoding='utf-8') as f:
                self.base_prompt = f.read()
        except Exception as e:
            logger.error(f"Failed to load blueprint_base.md: {e}")
            self.base_prompt = """You are a Game Blueprint Generator. Generate JSON blueprints matching TypeScript interfaces."""
    
    def _load_ts_interface(self, template_type: str, story_data: Dict[str, Any] = None) -> str:
        """Load TypeScript interface for template"""
        # For coding/algorithm questions, use ALGORITHM_VISUALIZATION regardless of initial template routing
        # If template is STATE_TRACER_CODE or PARAMETER_PLAYGROUND, route to ALGORITHM_VISUALIZATION
        if template_type in ["PARAMETER_PLAYGROUND", "STATE_TRACER_CODE"]:
            interface_path = Path(__file__).parent.parent.parent.parent / "prompts" / "blueprint_templates" / "ALGORITHM_VISUALIZATION.ts.txt"
            try:
                with open(interface_path, 'r', encoding='utf-8') as f:
                    logger.info(f"Loaded ALGORITHM_VISUALIZATION blueprint interface (routed from {template_type})")
                    return f.read()
            except Exception as e:
                logger.warning(f"Failed to load ALGORITHM_VISUALIZATION interface, falling back to {template_type}: {e}")
        
        # Also check story_data for algorithmic indicators
        if story_data:
            key_concepts = story_data.get('key_concepts', [])
            learning_alignment = story_data.get('learning_alignment', '')
            story_title = story_data.get('story_title', '').lower()
            
            # Check if this is an algorithmic/coding question
            is_algorithmic = (
                "algorithm" in str(key_concepts).lower() or
                "coding" in str(learning_alignment).lower() or
                any(concept in ["binary search", "sorting", "graph", "cycle", "two pointer", "sliding window", "dynamic programming", "floyd", "tortoise", "hare", "duplicate", "array", "linked list"] 
                    for concept in str(key_concepts).lower() + str(learning_alignment).lower() + story_title)
            )
            
            if is_algorithmic:
                interface_path = Path(__file__).parent.parent.parent.parent / "prompts" / "blueprint_templates" / "ALGORITHM_VISUALIZATION.ts.txt"
                try:
                    with open(interface_path, 'r', encoding='utf-8') as f:
                        logger.info(f"Loaded ALGORITHM_VISUALIZATION blueprint interface (detected algorithmic question)")
                        return f.read()
                except Exception as e:
                    logger.warning(f"Failed to load ALGORITHM_VISUALIZATION interface, falling back to {template_type}: {e}")
        
        # Default: use template_type
        interface_path = Path(__file__).parent.parent.parent.parent / "prompts" / "blueprint_templates" / f"{template_type}.ts.txt"
        try:
            with open(interface_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            logger.error(f"Failed to load TS interface for {template_type}: {e}")
            return f"// TypeScript interface for {template_type}"
    
    def generate(
        self,
        story_data: Dict[str, Any],
        template_type: str,
        question_text: str = None
    ) -> Dict[str, Any]:
        """Generate blueprint JSON from story data"""
        
        # Check if this should use ALGORITHM_VISUALIZATION
        actual_template = template_type
        # If template is STATE_TRACER_CODE or PARAMETER_PLAYGROUND, route to ALGORITHM_VISUALIZATION
        if template_type in ["PARAMETER_PLAYGROUND", "STATE_TRACER_CODE"]:
            actual_template = "ALGORITHM_VISUALIZATION"
            logger.info(f"Generating blueprint for template: {actual_template} (routed from {template_type})")
        elif story_data:
            key_concepts = story_data.get('key_concepts', [])
            learning_alignment = story_data.get('learning_alignment', '')
            story_title = story_data.get('story_title', '').lower()
            
            # Check if this is an algorithmic/coding question
            is_algorithmic = (
                "algorithm" in str(key_concepts).lower() or
                "coding" in str(learning_alignment).lower() or
                any(concept in ["binary search", "sorting", "graph", "cycle", "two pointer", "sliding window", "dynamic programming", "floyd", "tortoise", "hare", "duplicate", "array", "linked list"] 
                    for concept in str(key_concepts).lower() + str(learning_alignment).lower() + story_title)
            )
            
            if is_algorithmic:
                actual_template = "ALGORITHM_VISUALIZATION"
                logger.info(f"Generating blueprint for template: {actual_template} (detected algorithmic question)")
            else:
                logger.info(f"Generating blueprint for template: {template_type}")
        else:
            logger.info(f"Generating blueprint for template: {template_type}")
        
        # Get template metadata - use PARAMETER_PLAYGROUND if routing to ALGORITHM_VISUALIZATION
        metadata_template = "PARAMETER_PLAYGROUND" if actual_template == "ALGORITHM_VISUALIZATION" else template_type
        template_metadata = self.template_registry.get_template(metadata_template)
        if not template_metadata:
            raise ValueError(f"Template {metadata_template} not found in registry")
        
        # Load TypeScript interface (pass story_data to detect algorithmic questions)
        ts_interface = self._load_ts_interface(template_type, story_data)
        
        # Build system prompt
        system_prompt = self.base_prompt + "\n\n" + ts_interface
        
        # Build user prompt with original question for algorithm correctness
        question_context = ""
        if question_text:
            question_context = f"\n\nORIGINAL QUESTION (for algorithm correctness):\n{question_text}\n\nIMPORTANT: If the question requires O(log n) runtime or mentions binary search, the code MUST implement binary search, NOT linear search."
        
        user_prompt = f"""TemplateType: {template_type}

Template Metadata:
{json.dumps(template_metadata, indent=2)}

TypeScript interface for this template:

{ts_interface}

Story Data:
{json.dumps(story_data, indent=2)}
{question_context}

Generate a blueprint object that conforms EXACTLY to the TypeScript interface.
Do not include any fields that are not defined in the interface.
Do not wrap the response in any additional text."""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        try:
            # Try OpenAI first, fallback to Anthropic
            try:
                logger.info("Attempting blueprint generation with OpenAI...")
                response = self.llm_service.call_llm(messages, use_anthropic=False)
            except Exception as e:
                logger.warning(f"OpenAI failed, trying Anthropic: {e}")
                response = self.llm_service.call_llm(messages, use_anthropic=True)
            
            # Extract JSON
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                response = response.split("```")[1].split("```")[0].strip()
            
            blueprint = json.loads(response)
            
            # Ensure templateType matches
            # If we routed to ALGORITHM_VISUALIZATION, use PARAMETER_PLAYGROUND as templateType
            # (as specified in the ALGORITHM_VISUALIZATION interface)
            if actual_template == "ALGORITHM_VISUALIZATION":
                blueprint["templateType"] = "PARAMETER_PLAYGROUND"
                validation_template = "PARAMETER_PLAYGROUND"
            else:
                blueprint["templateType"] = template_type
                validation_template = template_type
            
            # Post-process: Ensure tasks have correctAnswer from story_data
            if "tasks" in blueprint and isinstance(blueprint["tasks"], list) and story_data:
                question_flow = story_data.get("question_flow", [])
                for i, task in enumerate(blueprint["tasks"]):
                    if isinstance(task, dict):
                        # If correctAnswer is missing, try to get it from question_flow
                        if "correctAnswer" not in task or task.get("correctAnswer") is None:
                            if i < len(question_flow):
                                q = question_flow[i]
                                answer_struct = q.get("answer_structure", {})
                                correct_answer = answer_struct.get("correct_answer")
                                if correct_answer is not None:
                                    task["correctAnswer"] = correct_answer
                                    logger.info(f"Added missing correctAnswer '{correct_answer}' to task {task.get('id', i)}")
                        
                        # Ensure options are in correct format if they exist
                        if "options" in task and isinstance(task["options"], list):
                            # Convert string options to {value, label} format if needed
                            formatted_options = []
                            for opt in task["options"]:
                                if isinstance(opt, str):
                                    formatted_options.append({"value": opt, "label": opt})
                                elif isinstance(opt, dict) and "value" in opt:
                                    formatted_options.append(opt)
                                else:
                                    formatted_options.append({"value": str(opt), "label": str(opt)})
                            task["options"] = formatted_options
            
            # Validate blueprint against the correct template type
            is_valid, errors = self.template_registry.validate_blueprint(blueprint, validation_template)
            if not is_valid:
                logger.error(f"Blueprint validation failed: {errors}")
                raise ValueError(f"Blueprint validation failed: {', '.join(errors)}")
            
            logger.info(f"Blueprint generated successfully for {validation_template} (routed from {template_type})")
            
            return {
                "success": True,
                "data": blueprint,
                "valid": True,
                "error_fields": []
            }
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse blueprint JSON: {e}")
            raise ValueError(f"Failed to parse blueprint JSON: {e}")
        except Exception as e:
            logger.error(f"Blueprint generation failed: {e}", exc_info=True)
            raise

class AssetRequest:
    """Represents an asset generation request"""
    def __init__(self, type: str, purpose: str, prompt: str):
        self.type = type  # "image", "gif", "audio", etc.
        self.purpose = purpose  # "diagram", "background", etc.
        self.prompt = prompt

class AssetPlanner:
    """Plans which assets need to be generated from blueprint"""
    
    def plan_assets(self, blueprint: Dict[str, Any]) -> list[AssetRequest]:
        """Extract asset requests from blueprint"""
        requests = []
        if not blueprint:
            logger.warning("Blueprint is None or empty, cannot plan assets")
            return requests
            
        template_type = blueprint.get("templateType")
        if not template_type:
            logger.warning("Blueprint missing templateType, cannot plan assets")
            return requests
        
        if template_type == "LABEL_DIAGRAM":
            diagram = blueprint.get("diagram", {})
            if diagram.get("assetPrompt"):
                requests.append(AssetRequest(
                    type="image",
                    purpose="diagram",
                    prompt=diagram["assetPrompt"]
                ))
        
        elif template_type == "IMAGE_HOTSPOT_QA":
            image = blueprint.get("image", {})
            if image.get("assetPrompt"):
                requests.append(AssetRequest(
                    type="image",
                    purpose="image",
                    prompt=image["assetPrompt"]
                ))
        
        elif template_type == "PARAMETER_PLAYGROUND":
            viz = blueprint.get("visualization", {})
            if viz.get("assetPrompt"):
                requests.append(AssetRequest(
                    type="image",
                    purpose="visualization",
                    prompt=viz["assetPrompt"]
                ))
        
        elif template_type == "SPOT_THE_MISTAKE":
            content = blueprint.get("content", {})
            if content.get("assetPrompt"):
                requests.append(AssetRequest(
                    type="image",
                    purpose="content",
                    prompt=content["assetPrompt"]
                ))
        
        elif template_type == "MICRO_SCENARIO_BRANCHING":
            scenarios = blueprint.get("scenarios", [])
            for i, scenario in enumerate(scenarios):
                if scenario.get("assetPrompt"):
                    requests.append(AssetRequest(
                        type="image",
                        purpose=f"scenario_{i}",
                        prompt=scenario["assetPrompt"]
                    ))
        
        elif template_type == "BEFORE_AFTER_TRANSFORMER":
            before = blueprint.get("beforeState", {})
            after = blueprint.get("afterState", {})
            if before.get("assetPrompt"):
                requests.append(AssetRequest(
                    type="image",
                    purpose="before",
                    prompt=before["assetPrompt"]
                ))
            if after.get("assetPrompt"):
                requests.append(AssetRequest(
                    type="image",
                    purpose="after",
                    prompt=after["assetPrompt"]
                ))
        
        logger.info(f"Planned {len(requests)} asset requests for {template_type}")
        return requests

class AssetGenerator:
    """Generates assets (images, animations, etc.) from prompts using DALL-E and other services"""
    
    def __init__(self):
        self.llm_service = LLMService()
        self.openai_client = None
        if self.llm_service.openai_client:
            self.openai_client = self.llm_service.openai_client
    
    def _generate_image_dalle(self, prompt: str, size: str = "1024x1024") -> Optional[str]:
        """Generate image using DALL-E API"""
        if not self.openai_client:
            logger.warning("OpenAI client not available, cannot generate images with DALL-E")
            return None
        
        try:
            logger.info(f"Calling DALL-E API - Prompt: {prompt[:100]}... Size: {size}")
            
            # Enhanced prompt for educational content
            enhanced_prompt = f"Educational illustration, clear and colorful, suitable for learning: {prompt}"
            
            response = self.openai_client.images.generate(
                model="dall-e-3",
                prompt=enhanced_prompt,
                size=size,
                quality="standard",
                n=1,
            )
            
            image_url = response.data[0].url
            logger.info(
                f"DALL-E image generated successfully - URL: {image_url[:100]}... "
                f"Model: dall-e-3, Size: {size}"
            )
            return image_url
            
        except Exception as e:
            logger.error(
                f"DALL-E image generation failed - Error: {str(e)}, "
                f"Prompt: {prompt[:100]}..."
            )
            return None
    
    def _generate_animation(self, prompt: str, frames: int = 5) -> Optional[str]:
        """Generate animation (GIF) from prompt using multiple DALL-E images"""
        if not self.openai_client:
            logger.warning("OpenAI client not available, cannot generate animations")
            return None
        
        try:
            logger.info(f"Generating animation: {prompt[:100]}...")
            
            # Generate multiple frames for animation
            frame_urls = []
            for i in range(frames):
                frame_prompt = f"{prompt}, frame {i+1} of {frames}, showing progression"
                frame_url = self._generate_image_dalle(frame_prompt, size="1024x1024")
                if frame_url:
                    frame_urls.append(frame_url)
            
            if len(frame_urls) > 1:
                # For now, return the first frame URL
                # In production, you would combine these into a GIF using PIL or similar
                logger.info(f"Generated {len(frame_urls)} animation frames")
                return frame_urls[0]  # Return first frame as placeholder
            elif frame_urls:
                return frame_urls[0]
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to generate animation: {e}")
            return None
    
    def generate_assets(self, requests: list[AssetRequest]) -> Dict[str, str]:
        """Generate assets and return URL map"""
        urls = {}
        total_requests = len(requests)
        dalle_success = 0
        dalle_failed = 0
        placeholder_used = 0
        
        logger.info(f"Starting asset generation for {total_requests} asset(s)")
        
        for req in requests:
            if req.type == "image":
                logger.info(f"Generating image asset: {req.purpose} - Prompt: {req.prompt[:100]}...")
                
                # Try DALL-E generation
                image_url = self._generate_image_dalle(req.prompt)
                
                if image_url:
                    urls[req.purpose] = image_url
                    dalle_success += 1
                    logger.info(
                        f"Successfully generated DALL-E image for {req.purpose} - "
                        f"URL: {image_url[:100]}..."
                    )
                else:
                    # Fallback to placeholder if DALL-E fails
                    dalle_failed += 1
                    placeholder_used += 1
                    placeholder_url = f"https://placeholder.com/800x600?text={req.purpose.replace('_', '+')}"
                    urls[req.purpose] = placeholder_url
                    logger.warning(
                        f"DALL-E generation failed for {req.purpose}, using placeholder. "
                        f"Prompt was: {req.prompt[:100]}"
                    )
            
            elif req.type == "animation":
                logger.info(f"Generating animation: {req.purpose} - Prompt: {req.prompt[:100]}...")
                
                # Generate animation
                animation_url = self._generate_animation(req.prompt)
                
                if animation_url:
                    urls[req.purpose] = animation_url
                    dalle_success += 1
                    logger.info(
                        f"Successfully generated animation for {req.purpose} - "
                        f"URL: {animation_url[:100]}..."
                    )
                else:
                    # Fallback to placeholder
                    dalle_failed += 1
                    placeholder_used += 1
                    placeholder_url = f"https://placeholder.com/800x600?text={req.purpose.replace('_', '+')}"
                    urls[req.purpose] = placeholder_url
                    logger.warning(
                        f"Animation generation failed for {req.purpose}, using placeholder. "
                        f"Prompt was: {req.prompt[:100]}"
                    )
        
        # Log summary
        logger.info(
            f"Asset generation complete - Total: {total_requests}, "
            f"DALL-E Success: {dalle_success}, DALL-E Failed: {dalle_failed}, "
            f"Placeholders Used: {placeholder_used}"
        )
        
        return urls
    
    def inject_asset_urls(self, blueprint: Dict[str, Any], asset_urls: Dict[str, str]) -> Dict[str, Any]:
        """Inject asset URLs into blueprint"""
        if not blueprint:
            logger.warning("Blueprint is None, cannot inject asset URLs")
            return {}
            
        template_type = blueprint.get("templateType")
        if not template_type:
            logger.warning("Blueprint missing templateType, cannot inject asset URLs")
            return blueprint
        
        if template_type == "LABEL_DIAGRAM":
            if "diagram" in blueprint and "diagram" in asset_urls:
                blueprint["diagram"]["assetUrl"] = asset_urls["diagram"]
        
        elif template_type == "IMAGE_HOTSPOT_QA":
            if "image" in blueprint and "image" in asset_urls:
                blueprint["image"]["assetUrl"] = asset_urls["image"]
        
        elif template_type == "PARAMETER_PLAYGROUND":
            if "visualization" in blueprint and "visualization" in asset_urls:
                blueprint["visualization"]["assetUrl"] = asset_urls["visualization"]
        
        elif template_type == "SPOT_THE_MISTAKE":
            if "content" in blueprint and "content" in asset_urls:
                blueprint["content"]["assetUrl"] = asset_urls["content"]
        
        elif template_type == "MICRO_SCENARIO_BRANCHING":
            scenarios = blueprint.get("scenarios", [])
            for i, scenario in enumerate(scenarios):
                key = f"scenario_{i}"
                if key in asset_urls:
                    scenario["imageUrl"] = asset_urls[key]
        
        elif template_type == "BEFORE_AFTER_TRANSFORMER":
            if "beforeState" in blueprint and "before" in asset_urls:
                blueprint["beforeState"]["assetUrl"] = asset_urls["before"]
            if "afterState" in blueprint and "after" in asset_urls:
                blueprint["afterState"]["assetUrl"] = asset_urls["after"]
        
        return blueprint

class GenerationOrchestrator:
    """Orchestrate content generation"""
    
    def __init__(self):
        self.story_generator = StoryGenerator()
        self.html_generator = HTMLGenerator()
        self.blueprint_generator = BlueprintGenerator()
        self.asset_planner = AssetPlanner()
        self.asset_generator = AssetGenerator()
        self.image_generator = ImageGenerator()
        self.animation_generator = AnimationGenerator()
    
    def generate_content(
        self,
        question_data: Dict[str, Any],
        strategy: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate all content for visualization"""
        logger.info("Starting content generation")
        
        try:
            # Step 1: Generate story
            prompt_template = strategy.get("prompt_template", "")
            story_result = self.story_generator.generate(
                question_data,
                prompt_template,
                strategy
            )
            story_data = story_result["data"]
            
            # Step 2: Generate HTML
            html_result = self.html_generator.generate(story_data)
            html_content = html_result["data"]["html"]
            
            logger.info("Content generation complete")
            
            return {
                "success": True,
                "story": story_data,
                "html": html_content,
                "story_validation": story_result.get("validation"),
                "html_validation": html_result.get("validation")
            }
        except Exception as e:
            logger.error(f"Content generation failed: {e}", exc_info=True)
            raise

