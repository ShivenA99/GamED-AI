"""Layer 2.5: Template Router - Selects appropriate game template"""
from typing import Dict, Any
from pathlib import Path
from app.services.llm_service import LLMService
from app.utils.logger import setup_logger
import json

logger = setup_logger("layer2_template_router")

class TemplateRouter:
    """Routes questions to appropriate game templates"""
    
    def __init__(self):
        self.llm_service = LLMService()
        self._load_system_prompt()
    
    def _load_system_prompt(self) -> str:
        """Load template router system prompt"""
        prompt_path = Path(__file__).parent.parent.parent.parent / "prompts" / "template_router_system.txt"
        try:
            with open(prompt_path, 'r', encoding='utf-8') as f:
                self.system_prompt = f.read()
        except Exception as e:
            logger.error(f"Failed to load template router prompt: {e}")
            # Fallback prompt
            self.system_prompt = """You are a template router for an educational game engine.
Select one template from: LABEL_DIAGRAM, IMAGE_HOTSPOT_QA, SEQUENCE_BUILDER, TIMELINE_ORDER, BUCKET_SORT, MATCH_PAIRS, MATRIX_MATCH, PARAMETER_PLAYGROUND, GRAPH_SKETCHER, VECTOR_SANDBOX, STATE_TRACER_CODE, SPOT_THE_MISTAKE, CONCEPT_MAP_BUILDER, MICRO_SCENARIO_BRANCHING, DESIGN_CONSTRAINT_BUILDER, PROBABILITY_LAB, BEFORE_AFTER_TRANSFORMER, GEOMETRY_BUILDER.
Respond with JSON: {"templateType": "...", "confidence": 0.0-1.0, "rationale": "..."}"""
    
    def route_template(
        self,
        question_text: str,
        analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Route question to appropriate template"""
        logger.info("Routing question to template")
        
        question_type = analysis.get("question_type", "reasoning")
        subject = analysis.get("subject", "General")
        difficulty = analysis.get("difficulty", "intermediate")
        key_concepts = analysis.get("key_concepts", [])
        intent = analysis.get("intent", "")
        
        user_prompt = f"""Question: {question_text}

Analysis:
- question_type: {question_type}
- subject: {subject}
- difficulty: {difficulty}
- key_concepts: {key_concepts}
- intent: {intent}

Choose the best templateType."""
        
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        try:
            # Try OpenAI first, fallback to Anthropic
            try:
                logger.info("Attempting template routing with OpenAI...")
                response = self.llm_service.call_llm(messages, use_anthropic=False)
            except Exception as e:
                logger.warning(f"OpenAI failed, trying Anthropic: {e}")
                response = self.llm_service.call_llm(messages, use_anthropic=True)
            
            # Extract JSON
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                response = response.split("```")[1].split("```")[0].strip()
            
            result = json.loads(response)
            
            # Validate template type
            valid_templates = [
                "LABEL_DIAGRAM", "IMAGE_HOTSPOT_QA", "SEQUENCE_BUILDER", "TIMELINE_ORDER",
                "BUCKET_SORT", "MATCH_PAIRS", "MATRIX_MATCH", "PARAMETER_PLAYGROUND",
                "GRAPH_SKETCHER", "VECTOR_SANDBOX", "STATE_TRACER_CODE", "SPOT_THE_MISTAKE",
                "CONCEPT_MAP_BUILDER", "MICRO_SCENARIO_BRANCHING", "DESIGN_CONSTRAINT_BUILDER",
                "PROBABILITY_LAB", "BEFORE_AFTER_TRANSFORMER", "GEOMETRY_BUILDER"
            ]
            
            template_type = result.get("templateType", "")
            if template_type not in valid_templates:
                logger.warning(f"Invalid template type {template_type}, defaulting to SEQUENCE_BUILDER")
                template_type = "SEQUENCE_BUILDER"
                result["templateType"] = template_type
                result["confidence"] = 0.5
                result["rationale"] = "Default fallback template"
            
            logger.info(f"Template routed to: {template_type} (confidence: {result.get('confidence', 0)})")
            
            return {
                "success": True,
                "data": result
            }
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse template router response: {e}")
            # Default fallback
            return {
                "success": True,
                "data": {
                    "templateType": "SEQUENCE_BUILDER",
                    "confidence": 0.5,
                    "rationale": "Fallback due to parsing error"
                }
            }
        except Exception as e:
            logger.error(f"Template routing failed: {e}", exc_info=True)
            # Default fallback
            return {
                "success": True,
                "data": {
                    "templateType": "SEQUENCE_BUILDER",
                    "confidence": 0.5,
                    "rationale": f"Fallback due to error: {str(e)}"
                }
            }

