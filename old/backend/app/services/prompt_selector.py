import os
from pathlib import Path
from app.utils.logger import setup_logger

# Set up logging
logger = setup_logger("prompt_selector")

class PromptSelector:
    def __init__(self):
        self.prompts_dir = Path(__file__).parent.parent.parent / "prompts"
        self.default_prompt = None
        logger.info(f"Initializing PromptSelector - Prompts directory: {self.prompts_dir}")
        self._load_default_prompt()

    def _load_default_prompt(self):
        """Load the default coding question prompt"""
        # Try to load story_base.md first
        prompt_file = self.prompts_dir / "story_base.md"
        if prompt_file.exists():
            logger.info(f"Loading prompt template from: {prompt_file}")
            with open(prompt_file, 'r', encoding='utf-8') as f:
                self.default_prompt = f.read()
            logger.info(f"Prompt template loaded - Length: {len(self.default_prompt)} chars")
        else:
            logger.warning(f"Prompt file not found: {prompt_file}, using fallback prompt")
            # Fallback prompt
            self.default_prompt = """You are a Visual Story Architect for Learning.
Transform problems into question-driven, interactive visual experiences.
Generate a story-based visualization with:
- A story that grounds the logic in a relatable world
- Visual metaphors mapping data to objects/colors
- Multiple intuitive questions that must be answered
- Question-driven interaction flow
- Visual feedback on answers

Respond with JSON matching the schema provided in the examples."""

    def select_prompt(self, question_type: str, subject: str) -> str:
        """Select appropriate prompt template based on question type and subject"""
        logger.info(f"Selecting prompt - Type: {question_type}, Subject: {subject}")
        
        # For now, we use the default prompt for all questions
        # In the future, we can have different prompts for different types
        
        # Map question types to potential specialized prompts
        prompt_map = {
            "coding": self.default_prompt,
            "math": self.default_prompt,
            "science": self.default_prompt,
            "reasoning": self.default_prompt,
            "application": self.default_prompt,
        }
        
        selected = prompt_map.get(question_type, self.default_prompt)
        logger.debug(f"Prompt selected - Length: {len(selected)} chars")
        return selected

