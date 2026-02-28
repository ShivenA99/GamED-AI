"""Layer 3: Gamification Strategy Engine"""
from typing import Dict, Any
from app.services.llm_service import LLMService
from app.services.prompt_selector import PromptSelector
from app.utils.logger import setup_logger
import json

logger = setup_logger("layer3_strategy")

class GameFormatSelector:
    """Select optimal game format for question"""
    
    def __init__(self):
        self.llm_service = LLMService()
    
    def select_format(
        self,
        question_type: str,
        subject: str,
        difficulty: str,
        key_concepts: list = None
    ) -> Dict[str, Any]:
        """Select optimal game format"""
        logger.info(f"Selecting game format for {question_type} question")
        
        prompt = f"""Based on the question characteristics, select the optimal game format.
        Available formats: drag_drop, matching, timeline, simulation, puzzle, quiz, interactive_diagram
        
        Question Type: {question_type}
        Subject: {subject}
        Difficulty: {difficulty}
        Key Concepts: {', '.join(key_concepts) if key_concepts else 'None'}
        
        Respond with ONLY a JSON object: {{"game_format": "format_here", "rationale": "why this format"}}"""
        
        messages = [
            {"role": "system", "content": "You are a gamification expert. Always respond with valid JSON only."},
            {"role": "user", "content": prompt}
        ]
        
        try:
            response = self.llm_service.call_llm(messages, use_anthropic=False)
            
            # Parse JSON response
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                response = response.split("```")[1].split("```")[0].strip()
            
            result = json.loads(response)
            logger.info(f"Game format selected: {result.get('game_format')}")
            return result
        except Exception as e:
            logger.error(f"Game format selection failed: {e}", exc_info=True)
            # Default fallback
            return {"game_format": "quiz", "rationale": "Default format"}

class StorylineGenerator:
    """Generate narrative context and storyline"""
    
    def __init__(self):
        self.llm_service = LLMService()
    
    def generate_storyline(
        self,
        question_text: str,
        question_type: str,
        subject: str,
        game_format: str
    ) -> Dict[str, Any]:
        """Generate engaging storyline"""
        logger.info("Generating storyline")
        
        prompt = f"""Create an engaging, educational storyline that makes this question come alive.
        
        Question: {question_text}
        Question Type: {question_type}
        Subject: {subject}
        Game Format: {game_format}
        
        Respond with ONLY a JSON object: {{
            "story_title": "title",
            "story_context": "engaging narrative",
            "characters": ["character1", "character2"],
            "setting": "where the story takes place"
        }}"""
        
        messages = [
            {"role": "system", "content": "You are a creative educational storyteller. Always respond with valid JSON only."},
            {"role": "user", "content": prompt}
        ]
        
        try:
            response = self.llm_service.call_llm(messages, use_anthropic=False)
            
            # Parse JSON response
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                response = response.split("```")[1].split("```")[0].strip()
            
            result = json.loads(response)
            logger.info(f"Storyline generated: {result.get('story_title')}")
            return result
        except Exception as e:
            logger.error(f"Storyline generation failed: {e}", exc_info=True)
            raise

class InteractionDesigner:
    """Define UI interactions and user experience"""
    
    def __init__(self):
        self.llm_service = LLMService()
    
    def design_interactions(
        self,
        game_format: str,
        question_type: str,
        difficulty: str
    ) -> Dict[str, Any]:
        """Design interaction patterns"""
        logger.info("Designing interaction patterns")
        
        prompt = f"""Design the interaction patterns for this game.
        
        Game Format: {game_format}
        Question Type: {question_type}
        Difficulty: {difficulty}
        
        Respond with ONLY a JSON object: {{
            "interaction_type": "click|drag|swipe|type",
            "feedback_style": "immediate|delayed|progressive",
            "hints_enabled": true/false,
            "animation_style": "smooth|bouncy|minimal"
        }}"""
        
        messages = [
            {"role": "system", "content": "You are a UX designer. Always respond with valid JSON only."},
            {"role": "user", "content": prompt}
        ]
        
        try:
            response = self.llm_service.call_llm(messages, use_anthropic=False)
            
            # Parse JSON response
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                response = response.split("```")[1].split("```")[0].strip()
            
            result = json.loads(response)
            logger.info(f"Interaction design complete: {result.get('interaction_type')}")
            return result
        except Exception as e:
            logger.error(f"Interaction design failed: {e}", exc_info=True)
            # Default fallback
            return {
                "interaction_type": "click",
                "feedback_style": "immediate",
                "hints_enabled": True,
                "animation_style": "smooth"
            }

class DifficultyAdapter:
    """Adjust challenge level based on performance"""
    
    def __init__(self):
        self.llm_service = LLMService()
    
    def adapt_difficulty(
        self,
        current_difficulty: str,
        performance_data: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Adapt difficulty based on performance"""
        logger.info(f"Adapting difficulty from {current_difficulty}")
        
        # If no performance data, return current difficulty
        if not performance_data:
            return {"difficulty": current_difficulty, "adjusted": False}
        
        prompt = f"""Based on performance data, suggest difficulty adjustment.
        
        Current Difficulty: {current_difficulty}
        Performance: {json.dumps(performance_data)}
        
        Respond with ONLY a JSON object: {{
            "difficulty": "beginner|intermediate|advanced",
            "adjusted": true/false,
            "reason": "why adjusted"
        }}"""
        
        messages = [
            {"role": "system", "content": "You are an adaptive learning expert. Always respond with valid JSON only."},
            {"role": "user", "content": prompt}
        ]
        
        try:
            response = self.llm_service.call_llm(messages, use_anthropic=False)
            
            # Parse JSON response
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                response = response.split("```")[1].split("```")[0].strip()
            
            result = json.loads(response)
            logger.info(f"Difficulty adapted: {result.get('difficulty')}")
            return result
        except Exception as e:
            logger.error(f"Difficulty adaptation failed: {e}", exc_info=True)
            return {"difficulty": current_difficulty, "adjusted": False}

class StrategyOrchestrator:
    """Orchestrate gamification strategy"""
    
    def __init__(self):
        self.format_selector = GameFormatSelector()
        self.storyline_generator = StorylineGenerator()
        self.interaction_designer = InteractionDesigner()
        self.difficulty_adapter = DifficultyAdapter()
        self.prompt_selector = PromptSelector()
    
    def create_strategy(
        self,
        question_text: str,
        analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create complete gamification strategy"""
        logger.info("Creating gamification strategy")
        
        try:
            question_type = analysis.get("question_type", "reasoning")
            subject = analysis.get("subject", "General")
            difficulty = analysis.get("difficulty", "intermediate")
            key_concepts = analysis.get("key_concepts", [])
            
            # Step 1: Select game format
            format_result = self.format_selector.select_format(
                question_type, subject, difficulty, key_concepts
            )
            game_format = format_result.get("game_format", "quiz")
            
            # Step 2: Generate storyline
            storyline_result = self.storyline_generator.generate_storyline(
                question_text, question_type, subject, game_format
            )
            
            # Step 3: Design interactions
            interaction_result = self.interaction_designer.design_interactions(
                game_format, question_type, difficulty
            )
            
            # Step 4: Get prompt template
            prompt_template = self.prompt_selector.select_prompt(question_type, subject)
            
            strategy = {
                "game_format": game_format,
                "format_rationale": format_result.get("rationale"),
                "storyline": storyline_result,
                "interactions": interaction_result,
                "prompt_template": prompt_template,
                "difficulty": difficulty
            }
            
            logger.info(f"Strategy created - Format: {game_format}")
            return {
                "success": True,
                "data": strategy
            }
        except Exception as e:
            logger.error(f"Strategy creation failed: {e}", exc_info=True)
            raise


