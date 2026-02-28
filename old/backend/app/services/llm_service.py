import os
import json
from typing import Dict, Any, Optional
from openai import OpenAI
from anthropic import Anthropic
from dotenv import load_dotenv
from app.utils.logger import setup_logger
from app.services.pipeline.retry_handler import RetryHandler, retry_on_failure

# Load environment variables
load_dotenv()

# Set up logging
logger = setup_logger("llm_service")

# Initialize retry handler for LLM calls
llm_retry_handler = RetryHandler(max_retries=3, initial_delay=1.0, max_delay=30.0)

class LLMService:
    def __init__(self):
        self.openai_client = None
        self.anthropic_client = None
        self._initialized = False
        self._initialize()
    
    def _initialize(self):
        """Lazy initialization of LLM clients"""
        if self._initialized:
            return
        
        # Try to initialize OpenAI
        openai_key = os.getenv("OPENAI_API_KEY")
        if openai_key:
            try:
                self.openai_client = OpenAI(api_key=openai_key)
                logger.info("OpenAI client initialized successfully")
            except Exception as e:
                logger.warning(f"Failed to initialize OpenAI client: {e}")
        else:
            logger.info("OPENAI_API_KEY not found in environment variables")
        
        # Try to initialize Anthropic
        anthropic_key = os.getenv("ANTHROPIC_API_KEY")
        if anthropic_key:
            try:
                self.anthropic_client = Anthropic(api_key=anthropic_key)
                logger.info("Anthropic client initialized successfully")
            except Exception as e:
                logger.warning(f"Failed to initialize Anthropic client: {e}")
        else:
            logger.info("ANTHROPIC_API_KEY not found in environment variables")
        
        # Log configuration status
        if not self.openai_client and not self.anthropic_client:
            logger.warning(
                "No LLM API keys configured. Please create a .env file in the backend directory "
                "with either OPENAI_API_KEY or ANTHROPIC_API_KEY. "
                "See SETUP.md for instructions."
            )
        
        self._initialized = True
        
        # Don't raise error here - check when actually using the service

    def _call_openai(self, messages: list, model: str = "gpt-4", temperature: float = 0.7) -> str:
        """Call OpenAI API with retry logic"""
        if not self.openai_client:
            raise ValueError("OpenAI client not initialized")
        
        logger.info(f"Calling OpenAI API - Model: {model}, Temperature: {temperature}")
        logger.debug(f"OpenAI Request - Messages count: {len(messages)}")
        logger.debug(f"OpenAI Request - System message: {messages[0].get('content', '')[:200] if messages else 'None'}...")
        
        def _make_call():
            response = self.openai_client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature
            )
            return response
        
        # Use retry handler
        try:
            response = llm_retry_handler.execute_sync(_make_call)
            
            content = response.choices[0].message.content
            logger.info(f"OpenAI API call successful - Response length: {len(content)} chars")
            logger.debug(f"OpenAI Response preview: {content[:500]}...")
            logger.debug(f"OpenAI Usage - Tokens: {response.usage.total_tokens if hasattr(response, 'usage') else 'N/A'}")
            
            return content
        except Exception as e:
            logger.error(f"OpenAI API call failed after retries: {str(e)}", exc_info=True)
            raise

    def _call_anthropic(self, messages: list, model: str = "claude-3-opus-20240229", temperature: float = 0.7) -> str:
        """Call Anthropic API with retry logic"""
        if not self.anthropic_client:
            raise ValueError("Anthropic client not initialized")
        
        # Convert messages format for Anthropic
        system_message = None
        conversation = []
        
        for msg in messages:
            if msg["role"] == "system":
                system_message = msg["content"]
            else:
                conversation.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })
        
        logger.info(f"Calling Anthropic API - Model: {model}, Temperature: {temperature}")
        logger.debug(f"Anthropic Request - System message length: {len(system_message) if system_message else 0}")
        logger.debug(f"Anthropic Request - Conversation messages: {len(conversation)}")
        logger.debug(f"Anthropic Request - System preview: {system_message[:200] if system_message else 'None'}...")
        
        def _make_call():
            response = self.anthropic_client.messages.create(
                model=model,
                max_tokens=4096,
                system=system_message if system_message else "",
                messages=conversation,
                temperature=temperature
            )
            return response
        
        # Use retry handler
        try:
            response = llm_retry_handler.execute_sync(_make_call)
            
            content = response.content[0].text
            logger.info(f"Anthropic API call successful - Response length: {len(content)} chars")
            logger.debug(f"Anthropic Response preview: {content[:500]}...")
            logger.debug(f"Anthropic Usage - Input tokens: {response.usage.input_tokens if hasattr(response, 'usage') else 'N/A'}, Output tokens: {response.usage.output_tokens if hasattr(response, 'usage') else 'N/A'}")
            
            return content
        except Exception as e:
            logger.error(f"Anthropic API call failed after retries: {str(e)}", exc_info=True)
            raise

    def call_llm(self, messages: list, model: Optional[str] = None, use_anthropic: bool = False) -> str:
        """Call LLM (OpenAI primary, Anthropic fallback)"""
        # Ensure initialized
        if not self._initialized:
            self._initialize()
        
        # Check if at least one client is available
        if not self.openai_client and not self.anthropic_client:
            raise ValueError("At least one LLM API key must be configured (OPENAI_API_KEY or ANTHROPIC_API_KEY). Please create a .env file in the backend directory with your API key.")
        
        # OpenAI is primary, Anthropic is fallback
        if use_anthropic and self.anthropic_client:
            return self._call_anthropic(messages, model or "claude-3-opus-20240229")
        elif self.openai_client:
            return self._call_openai(messages, model or "gpt-4")
        elif self.anthropic_client:
            return self._call_anthropic(messages, model or "claude-3-opus-20240229")
        else:
            raise ValueError("No LLM client available")

    def analyze_question(self, question_text: str, options: list = None) -> Dict[str, Any]:
        """Analyze question to determine type, subject, difficulty, etc."""
        logger.info(f"Analyzing question - Length: {len(question_text)} chars, Options: {len(options) if options else 0}")
        logger.debug(f"Question text: {question_text[:200]}...")
        
        prompt = f"""Analyze the following question and provide a JSON response with:
- question_type: one of ["coding", "math", "science", "reasoning", "application"]
- subject: specific subject area (e.g., "Biology", "Algebra", "Python Programming")
- difficulty: one of ["beginner", "intermediate", "advanced"]
- key_concepts: list of key concepts tested
- intent: what reasoning or intuition this problem tests

Question: {question_text}
Options: {options if options else "None"}

Respond with ONLY valid JSON, no additional text."""

        messages = [
            {"role": "system", "content": "You are an expert educational content analyzer. Always respond with valid JSON only."},
            {"role": "user", "content": prompt}
        ]

        # Try OpenAI first, fallback to Anthropic
        try:
            logger.info("Attempting question analysis with OpenAI...")
            response = self.call_llm(messages, use_anthropic=False)
        except Exception as e:
            logger.warning(f"OpenAI API call failed: {e}. Falling back to Anthropic...")
            if not self.anthropic_client:
                error_msg = (
                    f"OpenAI API call failed: {e}\n\n"
                    "To fix this issue:\n"
                    "1. Create a .env file in the backend directory\n"
                    "2. Add either:\n"
                    "   OPENAI_API_KEY=your_valid_openai_key\n"
                    "   OR\n"
                    "   ANTHROPIC_API_KEY=your_valid_anthropic_key\n"
                    "3. Restart the backend server\n\n"
                    "Get your API keys from:\n"
                    "- OpenAI: https://platform.openai.com/account/api-keys\n"
                    "- Anthropic: https://console.anthropic.com/settings/keys"
                )
                raise ValueError(error_msg)
            logger.info("Using Anthropic as fallback for question analysis")
            response = self.call_llm(messages, use_anthropic=True)
        
        # Try to extract JSON from response
        try:
            logger.debug(f"Raw LLM response length: {len(response)} chars")
            # Remove markdown code blocks if present
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0].strip()
                logger.debug("Removed ```json code block markers")
            elif "```" in response:
                response = response.split("```")[1].split("```")[0].strip()
                logger.debug("Removed ``` code block markers")
            
            analysis = json.loads(response)
            logger.info(f"Question analysis successful - Type: {analysis.get('question_type')}, Subject: {analysis.get('subject')}, Difficulty: {analysis.get('difficulty')}")
            logger.debug(f"Full analysis result: {json.dumps(analysis, indent=2)}")
            return analysis
        except json.JSONDecodeError as e:
            # Fallback if JSON parsing fails
            logger.warning(f"Failed to parse JSON from LLM response: {e}")
            logger.debug(f"Failed response content: {response[:500]}...")
            logger.warning("Using fallback analysis data")
            return {
                "question_type": "reasoning",
                "subject": "General",
                "difficulty": "intermediate",
                "key_concepts": [],
                "intent": "General problem solving"
            }

    def generate_story(self, question_data: Dict[str, Any], prompt_template: str) -> Dict[str, Any]:
        """Generate story from question using the prompt template"""
        logger.info("Starting story generation")
        logger.debug(f"Question data: {json.dumps(question_data, indent=2)}")
        logger.debug(f"Prompt template length: {len(prompt_template)} chars")
        
        system_prompt = prompt_template
        
        user_prompt = f"""Generate a story-based visualization for the following question:

Question: {question_data.get('text', '')}
Options: {question_data.get('options', [])}
Type: {question_data.get('question_type', 'reasoning')}
Subject: {question_data.get('subject', 'General')}
Difficulty: {question_data.get('difficulty', 'intermediate')}
Key Concepts: {question_data.get('key_concepts', [])}
Intent: {question_data.get('intent', '')}

Follow the schema and requirements in the system prompt. Respond with ONLY valid JSON matching the output schema."""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        # Try OpenAI first, fallback to Anthropic
        try:
            logger.info("Attempting story generation with OpenAI...")
            response = self.call_llm(messages, use_anthropic=False)
        except Exception as e:
            logger.warning(f"OpenAI API call failed: {e}. Falling back to Anthropic...")
            if not self.anthropic_client:
                error_msg = (
                    f"OpenAI API call failed: {e}\n\n"
                    "To fix this issue:\n"
                    "1. Create a .env file in the backend directory\n"
                    "2. Add either:\n"
                    "   OPENAI_API_KEY=your_valid_openai_key\n"
                    "   OR\n"
                    "   ANTHROPIC_API_KEY=your_valid_anthropic_key\n"
                    "3. Restart the backend server\n\n"
                    "Get your API keys from:\n"
                    "- OpenAI: https://platform.openai.com/account/api-keys\n"
                    "- Anthropic: https://console.anthropic.com/settings/keys"
                )
                raise ValueError(error_msg)
            logger.info("Using Anthropic as fallback for story generation")
            response = self.call_llm(messages, use_anthropic=True)
        
        # Extract JSON
        try:
            logger.debug(f"Raw story response length: {len(response)} chars")
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0].strip()
                logger.debug("Removed ```json code block markers")
            elif "```" in response:
                response = response.split("```")[1].split("```")[0].strip()
                logger.debug("Removed ``` code block markers")
            
            story_data = json.loads(response)
            logger.info(f"Story generation successful - Title: {story_data.get('story_title', 'Untitled')}")
            logger.debug(f"Story data keys: {list(story_data.keys())}")
            logger.debug(f"Question flow count: {len(story_data.get('question_flow', []))}")
            return story_data
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse story JSON: {e}")
            logger.debug(f"Failed response content: {response[:1000]}...")
            raise ValueError(f"Failed to parse story JSON from LLM response: {e}")

    def generate_html(self, story_data: Dict[str, Any]) -> str:
        """Generate HTML visualization from story data"""
        logger.info("Starting HTML generation")
        logger.debug(f"Story data keys: {list(story_data.keys())}")
        logger.debug(f"Story title: {story_data.get('story_title', 'Untitled')}")
        
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

        # Try OpenAI first, fallback to Anthropic
        try:
            logger.info("Attempting HTML generation with OpenAI...")
            response = self.call_llm(messages, use_anthropic=False)
        except Exception as e:
            logger.warning(f"OpenAI API call failed: {e}. Falling back to Anthropic...")
            if not self.anthropic_client:
                error_msg = (
                    f"OpenAI API call failed: {e}\n\n"
                    "To fix this issue:\n"
                    "1. Create a .env file in the backend directory\n"
                    "2. Add either:\n"
                    "   OPENAI_API_KEY=your_valid_openai_key\n"
                    "   OR\n"
                    "   ANTHROPIC_API_KEY=your_valid_anthropic_key\n"
                    "3. Restart the backend server\n\n"
                    "Get your API keys from:\n"
                    "- OpenAI: https://platform.openai.com/account/api-keys\n"
                    "- Anthropic: https://console.anthropic.com/settings/keys"
                )
                raise ValueError(error_msg)
            logger.info("Using Anthropic as fallback for HTML generation")
            response = self.call_llm(messages, use_anthropic=True)
        
        # Extract HTML
        logger.debug(f"Raw HTML response length: {len(response)} chars")
        if "```html" in response:
            response = response.split("```html")[1].split("```")[0].strip()
            logger.debug("Removed ```html code block markers")
        elif "```" in response:
            response = response.split("```")[1].split("```")[0].strip()
            logger.debug("Removed ``` code block markers")
        
        logger.info(f"HTML generation successful - Final length: {len(response)} chars")
        logger.debug(f"HTML preview (first 500 chars): {response[:500]}...")
        return response

