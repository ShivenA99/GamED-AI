"""
LLM Service for GamED.AI v2

Provides async LLM integration for agents with:
- OpenAI, Anthropic, and Google Gemini support
- Tool calling (function calling) for agentic workflows
- ReAct reasoning loops (Reason→Act→Observe)
- Retry logic with exponential backoff
- Token tracking
- Structured output parsing
- Per-agent model configuration (plug-and-play)

Usage:
    # Basic usage
    llm = get_llm_service()
    response = await llm.generate("What is 2+2?")

    # Agent-specific usage (uses config from agent_models.py)
    response = await llm.generate_for_agent(
        agent_name="blueprint_generator",
        prompt="Generate a SEQUENCE_BUILDER blueprint..."
    )

    # Tool calling (single shot)
    tools = [Tool(name="search", description="...", parameters={...}, function=search_fn)]
    result = await llm.generate_with_tools(
        prompt="Find information about...",
        tools=tools,
        mode="single"
    )

    # ReAct loop
    result = await llm.generate_with_tools(
        prompt="Research and plan...",
        tools=tools,
        mode="react",
        max_iterations=10
    )
"""

import os
import json
import asyncio
import time
import copy
from typing import Dict, Any, Optional, List, Union, Callable, Awaitable, TYPE_CHECKING
import httpx
from dataclasses import dataclass, field
from enum import Enum
from openai import AsyncOpenAI
from anthropic import AsyncAnthropic
from dotenv import load_dotenv

# Use override=True to ensure .env values take precedence over any inherited env vars
load_dotenv(override=True)

from app.utils.logging_config import get_logger

logger = get_logger("gamed_ai.services.llm_service")

# Lazy import to avoid circular dependency
if TYPE_CHECKING:
    from app.config.agent_models import AgentModelConfig
    from app.config.models import ModelConfig, ModelProvider


@dataclass
class LLMResponse:
    """Structured LLM response with metadata"""
    content: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    latency_ms: int = 0
    # Raw Gemini Content object for thought signature preservation (Gemini 3+)
    # This should be passed back in multi-turn conversations to maintain reasoning context
    _raw_gemini_content: Any = None


@dataclass
class RetryConfig:
    """Configuration for retry behavior"""
    max_retries: int = 3
    initial_delay: float = 1.0
    max_delay: float = 30.0
    exponential_base: float = 2.0


# ============================================================================
# Tool Calling Types
# ============================================================================

class ToolCallStatus(Enum):
    """Status of a tool call"""
    SUCCESS = "success"
    ERROR = "error"
    TIMEOUT = "timeout"


@dataclass
class Tool:
    """
    Definition of a tool that can be called by the LLM.

    Attributes:
        name: Unique identifier for the tool
        description: Human-readable description of what the tool does
        parameters: JSON Schema describing the tool's parameters
        function: Async callable that executes the tool
    """
    name: str
    description: str
    parameters: Dict[str, Any]  # JSON Schema
    function: Callable[..., Awaitable[Any]]

    def to_openai_format(self) -> Dict[str, Any]:
        """Convert to OpenAI function calling format"""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters
            }
        }

    def to_anthropic_format(self) -> Dict[str, Any]:
        """Convert to Anthropic tool format"""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.parameters
        }

    def to_gemini_format(self) -> Dict[str, Any]:
        """Convert to Google Gemini function declaration format"""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters
        }


@dataclass
class ToolCall:
    """
    Represents a tool call requested by the LLM.

    Attributes:
        id: Unique identifier for this tool call
        name: Name of the tool to call
        arguments: Arguments to pass to the tool
    """
    id: str
    name: str
    arguments: Dict[str, Any]


@dataclass
class ToolResult:
    """
    Result from executing a tool.

    Attributes:
        tool_call_id: ID of the tool call this result is for
        name: Name of the tool that was called
        result: The result returned by the tool
        status: Success/error/timeout status
        error: Error message if status is ERROR
        latency_ms: Time taken to execute the tool
    """
    tool_call_id: str
    name: str
    result: Any
    status: ToolCallStatus = ToolCallStatus.SUCCESS
    error: Optional[str] = None
    latency_ms: int = 0


@dataclass
class ReActStep:
    """
    Single step in a ReAct reasoning loop.

    Attributes:
        thought: The LLM's reasoning about what to do
        action: The tool call (if any) decided upon
        observation: Result from executing the tool
        iteration: Which iteration this step belongs to
    """
    thought: str
    action: Optional[ToolCall] = None
    observation: Optional[str] = None
    iteration: int = 0


@dataclass
class ToolCallingResponse:
    """
    Complete response from a tool-calling interaction.

    Attributes:
        content: Final text response from the LLM
        model: Model used for generation
        tool_calls: List of tool calls made
        tool_results: Results from tool executions
        react_trace: Full ReAct trace if mode="react"
        iterations: Number of ReAct iterations
        total_input_tokens: Total input tokens across all LLM calls
        total_output_tokens: Total output tokens across all LLM calls
        total_latency_ms: Total time for the entire interaction
        stop_reason: Why the interaction stopped (completed, max_iterations, error)
    """
    content: str
    model: str
    tool_calls: List[ToolCall] = field(default_factory=list)
    tool_results: List[ToolResult] = field(default_factory=list)
    react_trace: List[ReActStep] = field(default_factory=list)
    iterations: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_latency_ms: int = 0
    stop_reason: str = "completed"


# ============================================================================
# Streaming Callback Types
# ============================================================================

@dataclass
class StreamingChunk:
    """
    A chunk of streaming output from an LLM.

    Attributes:
        content: The text content of this chunk
        is_final: Whether this is the final chunk
        accumulated_content: All content received so far
    """
    content: str
    is_final: bool = False
    accumulated_content: str = ""


@dataclass
class LiveStepEvent:
    """
    A live step event emitted during ReAct loop execution.

    Attributes:
        type: One of 'thought', 'action', 'observation', 'decision'
        content: The content of this step
        tool: Tool name if this is an action step
        timestamp: ISO timestamp when this step occurred
        iteration: Which ReAct iteration this belongs to
    """
    type: str  # 'thought' | 'action' | 'observation' | 'decision'
    content: str
    tool: Optional[str] = None
    timestamp: Optional[str] = None
    iteration: int = 0


# Type aliases for callbacks
# StreamCallback receives streaming text chunks in real-time
StreamCallback = Callable[[StreamingChunk], Awaitable[None]]

# StepCallback receives ReAct step events in real-time
StepCallback = Callable[[LiveStepEvent], Awaitable[None]]


class LLMService:
    """
    Async LLM service supporting OpenAI, Anthropic, Google Gemini, Groq, and Ollama.

    Usage:
        service = LLMService()
        response = await service.generate("What is 2+2?")
        parsed = await service.generate_json(prompt, schema_hint="Return JSON with 'answer' key")
    """

    # Default models
    DEFAULT_OPENAI_MODEL = "gpt-4-turbo-preview"
    DEFAULT_ANTHROPIC_MODEL = "claude-3-5-sonnet-20241022"
    DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"
    DEFAULT_GROQ_MODEL = "llama-3.3-70b-versatile"
    DEFAULT_OLLAMA_MODEL = "llama3.2:latest"
    DEFAULT_SGLANG_URL = "http://localhost:30000"

    # Groq API base URL (OpenAI-compatible)
    GROQ_BASE_URL = "https://api.groq.com/openai/v1"

    # Ollama API base URL (OpenAI-compatible)
    OLLAMA_BASE_URL = "http://localhost:11434/v1"

    def __init__(
        self,
        openai_api_key: Optional[str] = None,
        anthropic_api_key: Optional[str] = None,
        google_api_key: Optional[str] = None,
        groq_api_key: Optional[str] = None,
        ollama_base_url: Optional[str] = None,
        retry_config: Optional[RetryConfig] = None,
        prefer_anthropic: bool = False,
        prefer_gemini: bool = False,
        prefer_groq: bool = False,
        prefer_ollama: bool = False
    ):
        self.retry_config = retry_config or RetryConfig()
        self.prefer_anthropic = prefer_anthropic
        self.prefer_gemini = prefer_gemini
        self.prefer_groq = prefer_groq
        self.prefer_ollama = prefer_ollama

        # Initialize clients
        self.openai_client: Optional[AsyncOpenAI] = None
        self.anthropic_client: Optional[AsyncAnthropic] = None
        self.gemini_client: Optional[Any] = None  # Google genai client
        self.groq_client: Optional[AsyncOpenAI] = None
        self.ollama_client: Optional[AsyncOpenAI] = None

        # Try Ollama (LOCAL! - check first if preferred)
        ollama_url = ollama_base_url or os.getenv("OLLAMA_BASE_URL", self.OLLAMA_BASE_URL)
        use_ollama_env = os.getenv("USE_OLLAMA", "").lower() == "true"
        if self.prefer_ollama or use_ollama_env:
            try:
                # Ensure base_url ends with /v1 for OpenAI-compatible endpoint
                if not ollama_url.endswith("/v1"):
                    if ollama_url.endswith("/"):
                        ollama_url = ollama_url.rstrip("/") + "/v1"
                    else:
                        ollama_url = ollama_url + "/v1"

                self.ollama_client = AsyncOpenAI(
                    api_key="ollama",  # Not used, but required by OpenAI client
                    base_url=ollama_url
                )
                logger.info(f"Ollama client initialized (LOCAL at {ollama_url})")
            except Exception as e:
                logger.warning(f"Failed to initialize Ollama: {e}")

        # Try Google Gemini
        google_key = google_api_key or os.getenv("GOOGLE_API_KEY")
        if google_key:
            try:
                from google import genai
                self.gemini_client = genai.Client(api_key=google_key)
                logger.info("Google Gemini client initialized")
            except ImportError:
                logger.warning("google-genai package not installed. Run: pip install google-genai")
            except Exception as e:
                logger.warning(f"Failed to initialize Gemini: {e}")

        # Try Groq (FREE! - check first)
        groq_key = groq_api_key or os.getenv("GROQ_API_KEY")
        if groq_key:
            try:
                self.groq_client = AsyncOpenAI(
                    api_key=groq_key,
                    base_url=self.GROQ_BASE_URL
                )
                logger.info("Groq client initialized (FREE tier!)")
            except Exception as e:
                logger.warning(f"Failed to initialize Groq: {e}")

        # Try OpenAI
        openai_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        if openai_key:
            try:
                self.openai_client = AsyncOpenAI(api_key=openai_key)
                logger.info("OpenAI client initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize OpenAI: {e}")

        # Try Anthropic
        anthropic_key = anthropic_api_key or os.getenv("ANTHROPIC_API_KEY")
        if anthropic_key:
            try:
                self.anthropic_client = AsyncAnthropic(api_key=anthropic_key)
                logger.info("Anthropic client initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize Anthropic: {e}")

        if not self.openai_client and not self.anthropic_client and not self.gemini_client and not self.groq_client and not self.ollama_client:
            logger.warning(
                "No LLM clients configured. Set USE_OLLAMA=true (local), GOOGLE_API_KEY, GROQ_API_KEY (free!), OPENAI_API_KEY, or ANTHROPIC_API_KEY."
            )

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        use_anthropic: Optional[bool] = None,
        use_gemini: Optional[bool] = None,
        use_groq: Optional[bool] = None,
        use_ollama: Optional[bool] = None
    ) -> LLMResponse:
        """
        Generate text from an LLM.

        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            model: Model override
            temperature: Sampling temperature
            max_tokens: Maximum output tokens
            use_anthropic: Force Anthropic (None = use preference)
            use_groq: Force Groq (None = use preference)

        Returns:
            LLMResponse with content and metadata
        """
        import time
        start_time = time.time()

        # Determine which client to use
        from app.config.models import MODEL_REGISTRY, ModelProvider
        
        # If model is specified and in registry, use its provider
        if model and model in MODEL_REGISTRY:
            config = MODEL_REGISTRY[model]
            if config.provider == ModelProvider.GOOGLE and self.gemini_client:
                response = await self._call_gemini(
                    prompt, system_prompt, config.model_id, temperature, max_tokens
                )
            elif config.provider == ModelProvider.GROQ and self.groq_client:
                response = await self._call_groq(
                    prompt, system_prompt, model, temperature, max_tokens
                )
            elif config.provider == ModelProvider.LOCAL and self.ollama_client:
                response = await self._call_ollama(
                    prompt, system_prompt, model, temperature, max_tokens
                )
            elif config.provider == ModelProvider.ANTHROPIC and self.anthropic_client:
                response = await self._call_anthropic(
                    prompt, system_prompt, model, temperature, max_tokens
                )
            elif config.provider == ModelProvider.OPENAI and self.openai_client:
                response = await self._call_openai(
                    prompt, system_prompt, model, temperature, max_tokens
                )
            else:
                # Fallback to flag-based logic
                use_anthropic = use_anthropic if use_anthropic is not None else self.prefer_anthropic
                use_gemini = use_gemini if use_gemini is not None else self.prefer_gemini
                use_groq = use_groq if use_groq is not None else self.prefer_groq
                use_ollama = use_ollama if use_ollama is not None else self.prefer_ollama

                # NOTE: Removed USE_OLLAMA env override here - it was causing Gemini models to route to Ollama
                # Provider should be determined by model configuration, not global env flag

                if use_ollama and self.ollama_client:
                    response = await self._call_ollama(
                        prompt, system_prompt, model, temperature, max_tokens
                    )
                elif use_gemini and self.gemini_client:
                    response = await self._call_gemini(
                        prompt, system_prompt, model, temperature, max_tokens
                    )
                elif use_groq and self.groq_client:
                    response = await self._call_groq(
                        prompt, system_prompt, model, temperature, max_tokens
                    )
                elif use_anthropic and self.anthropic_client:
                    response = await self._call_anthropic(
                        prompt, system_prompt, model, temperature, max_tokens
                    )
                elif self.openai_client:
                    response = await self._call_openai(
                        prompt, system_prompt, model, temperature, max_tokens
                    )
                elif self.gemini_client:
                    # Fallback to Gemini if available
                    response = await self._call_gemini(
                        prompt, system_prompt, model, temperature, max_tokens
                    )
                elif self.ollama_client:
                    # Fallback to Ollama if available (LOCAL! - prioritize when USE_OLLAMA=true)
                    response = await self._call_ollama(
                        prompt, system_prompt, model, temperature, max_tokens
                    )
                elif self.groq_client:
                    # Fallback to Groq if available (FREE!)
                    response = await self._call_groq(
                        prompt, system_prompt, model, temperature, max_tokens
                    )
                elif self.anthropic_client:
                    response = await self._call_anthropic(
                        prompt, system_prompt, model, temperature, max_tokens
                    )
                else:
                    raise ValueError("No LLM client available. Configure USE_OLLAMA=true (local), GOOGLE_API_KEY, GROQ_API_KEY (free!), OPENAI_API_KEY, or ANTHROPIC_API_KEY.")
        else:
            # No model specified or model not in registry, use flag-based logic
            use_anthropic = use_anthropic if use_anthropic is not None else self.prefer_anthropic
            use_gemini = use_gemini if use_gemini is not None else self.prefer_gemini
            use_groq = use_groq if use_groq is not None else self.prefer_groq
            use_ollama = use_ollama if use_ollama is not None else self.prefer_ollama

            # NOTE: Removed USE_OLLAMA env override here - it was causing Gemini models to route to Ollama
            # Provider should be determined by model configuration, not global env flag
            # The USE_OLLAMA flag is now only used for initializing the Ollama client at startup

            if use_ollama and self.ollama_client:
                response = await self._call_ollama(
                    prompt, system_prompt, model, temperature, max_tokens
                )
            elif use_gemini and self.gemini_client:
                response = await self._call_gemini(
                    prompt, system_prompt, model, temperature, max_tokens
                )
            elif use_groq and self.groq_client:
                response = await self._call_groq(
                    prompt, system_prompt, model, temperature, max_tokens
                )
            elif use_anthropic and self.anthropic_client:
                response = await self._call_anthropic(
                    prompt, system_prompt, model, temperature, max_tokens
                )
            elif self.openai_client:
                response = await self._call_openai(
                    prompt, system_prompt, model, temperature, max_tokens
                )
            elif self.gemini_client:
                # Fallback to Gemini if available
                response = await self._call_gemini(
                    prompt, system_prompt, model, temperature, max_tokens
                )
            elif self.ollama_client:
                # Fallback to Ollama if available (LOCAL! - prioritize when USE_OLLAMA=true)
                response = await self._call_ollama(
                    prompt, system_prompt, model, temperature, max_tokens
                )
            elif self.groq_client:
                # Fallback to Groq if available (FREE!)
                response = await self._call_groq(
                    prompt, system_prompt, model, temperature, max_tokens
                )
            elif self.anthropic_client:
                response = await self._call_anthropic(
                    prompt, system_prompt, model, temperature, max_tokens
                )
            else:
                raise ValueError("No LLM client available. Configure USE_OLLAMA=true (local), GOOGLE_API_KEY, GROQ_API_KEY (free!), OPENAI_API_KEY, or ANTHROPIC_API_KEY.")

        response.latency_ms = int((time.time() - start_time) * 1000)
        return response

    async def generate_json(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        schema_hint: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate and parse JSON from an LLM.

        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            schema_hint: Description of expected JSON schema
            **kwargs: Additional args passed to generate()

        Returns:
            Parsed JSON dict
        """
        # Enhance system prompt for JSON output (more explicit for local models)
        json_system = system_prompt or ""
        json_system += "\n\nCRITICAL: You MUST respond with ONLY valid JSON. No markdown code blocks, no explanations, no text before or after. Start with { and end with }. The response must be parseable by json.loads()."
        if schema_hint:
            json_system += f"\n\nExpected JSON structure: {schema_hint}"
        json_system += "\n\nExample of correct response format:\n{\"key\": \"value\", ...}\n\nDo NOT wrap in ```json or ``` blocks. Return raw JSON only."

        response = await self.generate(prompt, system_prompt=json_system, **kwargs)

        # Parse JSON from response
        content = response.content.strip()

        # Remove markdown code blocks if present
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()

        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            # Try to find JSON in the response
            start = content.find("{")
            end = content.rfind("}") + 1
            if start != -1 and end > start:
                try:
                    return json.loads(content[start:end])
                except json.JSONDecodeError:
                    pass

            logger.error(
                "Failed to parse JSON response",
                exc_info=True,
                error_type=type(e).__name__,
                response_preview=content[:500],
                service="llm_service"
            )
            raise ValueError(f"LLM response was not valid JSON: {e}")

    async def generate_for_agent(
        self,
        agent_name: str,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> LLMResponse:
        """
        Generate using agent-specific model configuration.

        Uses the plug-and-play model configuration system to select
        the appropriate model and temperature for each agent.

        Args:
            agent_name: Name of the agent (e.g., "blueprint_generator")
            prompt: User prompt
            system_prompt: Optional system prompt
            **kwargs: Additional args passed to generate()

        Returns:
            LLMResponse with content and metadata
        """
        # Import here to avoid circular dependency
        from app.config.models import MODEL_REGISTRY, ModelProvider
        from app.config.agent_models import get_runtime_config

        config = get_runtime_config()
        model_key = config.get_model(agent_name)
        temperature = config.get_temperature(agent_name)
        max_tokens = config.get_max_tokens(agent_name)

        model_config = MODEL_REGISTRY.get(model_key)
        if not model_config:
            logger.warning(f"Model '{model_key}' not found, using default")
            return await self.generate(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs
            )

        # Determine provider flags
        use_anthropic = model_config.provider == ModelProvider.ANTHROPIC
        use_gemini = model_config.provider == ModelProvider.GOOGLE
        use_groq = model_config.provider == ModelProvider.GROQ
        use_ollama = model_config.provider == ModelProvider.LOCAL

        logger.debug(
            f"Agent '{agent_name}' using model '{model_config.model_id}' "
            f"(provider={model_config.provider.value}, temp={temperature}, max_tokens={max_tokens})"
        )

        return await self.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            model=model_config.model_id,
            temperature=temperature,
            max_tokens=max_tokens,
            use_anthropic=use_anthropic,
            use_gemini=use_gemini,
            use_groq=use_groq,
            use_ollama=use_ollama,
            **kwargs
        )

    async def generate_json_for_agent(
        self,
        agent_name: str,
        prompt: str,
        system_prompt: Optional[str] = None,
        schema_hint: Optional[str] = None,
        json_schema: Optional[Dict[str, Any]] = None,
        max_json_retries: int = 3,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate and parse JSON using agent-specific model configuration.

        Enhanced with:
        - Multi-stage JSON repair for malformed output
        - Retry with error feedback for persistent failures
        - Detailed logging for debugging

        Args:
            agent_name: Name of the agent
            prompt: User prompt
            system_prompt: Optional system prompt
            schema_hint: Description of expected JSON schema
            max_json_retries: Max retries for JSON parsing failures
            **kwargs: Additional args

        Returns:
            Parsed JSON dict
        """
        # Import JSON repair module
        from app.services.json_repair import repair_json, JSONRepairError, get_error_context

        # Import model config
        from app.config.models import MODEL_REGISTRY, ModelProvider
        from app.config.agent_models import get_runtime_config

        config = get_runtime_config()
        model_key = config.get_model(agent_name)
        temperature = config.get_temperature(agent_name)
        max_tokens = config.get_max_tokens(agent_name)

        model_config = MODEL_REGISTRY.get(model_key)
        if not model_config:
            logger.warning(f"Model '{model_key}' not found, using default")
            return await self.generate_json(
                prompt=prompt,
                system_prompt=system_prompt,
                schema_hint=schema_hint,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs
            )

        # Check if using local model (needs more explicit prompting)
        is_local_model = model_config.provider == ModelProvider.LOCAL

        # Build enhanced system prompt for JSON output
        json_system = self._build_json_system_prompt(
            system_prompt=system_prompt,
            schema_hint=schema_hint,
            is_local_model=is_local_model
        )

        # Determine provider flags
        use_anthropic = model_config.provider == ModelProvider.ANTHROPIC
        use_gemini = model_config.provider == ModelProvider.GOOGLE
        use_groq = model_config.provider == ModelProvider.GROQ
        use_ollama = model_config.provider == ModelProvider.LOCAL

        current_prompt = prompt
        last_error = None
        last_error_context = None

        use_sglang = os.getenv("USE_SGLANG", "").lower() == "true"
        sglang_url = os.getenv("SGLANG_URL", self.DEFAULT_SGLANG_URL)
        sglang_model = os.getenv("SGLANG_MODEL", model_config.model_id)

        if use_sglang and json_schema:
            try:
                result = await self._call_sglang_guided(
                    prompt=current_prompt,
                    system_prompt=json_system,
                    model=sglang_model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    json_schema=json_schema,
                    base_url=sglang_url
                )
                # Add metrics placeholder (SGLang doesn't return usage stats easily)
                result["_llm_metrics"] = {
                    "model": sglang_model,
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "latency_ms": 0
                }
                return result
            except Exception as e:
                logger.warning(f"SGLang guided decoding failed, falling back to standard JSON: {e}")

        for attempt in range(max_json_retries):
            logger.info(
                f"JSON gen attempt {attempt + 1}/{max_json_retries} "
                f"agent={agent_name} model={model_config.model_id} max_tok={max_tokens}"
            )

            # On retry, add error feedback to prompt
            if attempt > 0 and last_error:
                current_prompt = self._add_error_feedback_to_prompt(
                    original_prompt=prompt,
                    error=last_error,
                    error_context=last_error_context,
                    attempt=attempt
                )

            try:
                response = await self.generate(
                    prompt=current_prompt,
                    system_prompt=json_system,
                    model=model_config.model_id,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    use_anthropic=use_anthropic,
                    use_gemini=use_gemini,
                    use_groq=use_groq,
                    use_ollama=use_ollama,
                    **kwargs
                )

                content = response.content.strip() if response.content else ""

                if not content:
                    logger.error(f"Empty response from agent '{agent_name}' on attempt {attempt + 1}")
                    last_error = "Empty response from LLM"
                    continue

                logger.debug(
                    f"Agent '{agent_name}' raw response: {len(content)} chars"
                )

                # Try to parse/repair JSON using the repair module
                try:
                    result, was_repaired, repair_log = repair_json(content)

                    if was_repaired:
                        logger.warning(
                            f"Agent '{agent_name}' JSON was repaired: {repair_log}"
                        )

                    logger.info(
                        "JSON parsed successfully",
                        agent_name=agent_name,
                        attempt=attempt + 1,
                        response_length=len(content)
                    )
                    # Store metrics in result for instrumentation (will be extracted by decorator)
                    # Include truncated prompt/response for sub-stage observability
                    prompt_preview = current_prompt[:1000] + ("..." if len(current_prompt) > 1000 else "")
                    response_preview = content[:2000] + ("..." if len(content) > 2000 else "")
                    result["_llm_metrics"] = {
                        "model": response.model,
                        "prompt_tokens": response.input_tokens,
                        "completion_tokens": response.output_tokens,
                        "latency_ms": response.latency_ms,
                        "prompt_preview": prompt_preview,
                        "response_preview": response_preview,
                    }
                    return result

                except JSONRepairError as e:
                    last_error = str(e.original_error)
                    last_error_context = get_error_context(content, e.position)

                    logger.warning(
                        f"Agent '{agent_name}' JSON repair failed on attempt {attempt + 1}: "
                        f"{last_error}"
                    )
                    logger.debug(f"Error context: {last_error_context}")

            except Exception as e:
                logger.error(
                    f"Agent '{agent_name}' LLM call failed on attempt {attempt + 1}: {e}",
                    exc_info=True
                )
                last_error = str(e)
                last_error_context = None

        # All retries exhausted
        error_msg = (
            f"Failed to generate valid JSON for agent '{agent_name}' after "
            f"{max_json_retries} attempts. Last error: {last_error}"
        )
        logger.error(error_msg)
        if last_error_context:
            logger.error(f"Error context: {last_error_context}")

        raise ValueError(error_msg)

    async def _call_sglang_guided(
        self,
        prompt: str,
        system_prompt: str,
        model: str,
        temperature: float,
        max_tokens: int,
        json_schema: Dict[str, Any],
        base_url: str
    ) -> Dict[str, Any]:
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "response_format": {"type": "json_object"},
            "json_schema": json_schema,
            "guided_json": json_schema
        }

        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(f"{base_url}/v1/chat/completions", json=payload)
            response.raise_for_status()
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            return json.loads(content)

    def _build_json_system_prompt(
        self,
        system_prompt: Optional[str],
        schema_hint: Optional[str],
        is_local_model: bool
    ) -> str:
        """Build enhanced system prompt for JSON generation"""
        json_system = system_prompt or ""

        if is_local_model:
            # More explicit instructions for local models
            json_system += """

CRITICAL JSON FORMATTING RULES:
1. Return ONLY valid JSON - no text before or after
2. Start with { and end with }
3. Use double quotes for ALL strings and keys
4. Do NOT use single quotes
5. Put a comma after EVERY element except the last one in arrays/objects
6. Do NOT put a trailing comma before } or ]
7. Do NOT include comments in the JSON
8. Escape special characters in strings: use \\" for quotes, \\\\ for backslash
9. Use null (not None or undefined) for null values
10. Use true/false (lowercase, no quotes) for booleans

EXAMPLE OF CORRECT FORMAT:
{
    "key1": "string value",
    "key2": 42,
    "key3": true,
    "key4": null,
    "array": ["item1", "item2"],
    "nested": {
        "innerKey": "innerValue"
    }
}

DO NOT OUTPUT:
- Markdown code blocks (```json)
- Explanatory text before or after the JSON
- Comments (// or /* */)
- Trailing commas
"""
        else:
            # Standard prompt for cloud models
            json_system += """

CRITICAL: Respond with ONLY valid JSON. No markdown, no explanations, no text before or after.
Start with { and end with }. The response must be parseable by json.loads().
"""

        if schema_hint:
            json_system += f"\n\nExpected JSON structure: {schema_hint}"

        return json_system

    def _add_error_feedback_to_prompt(
        self,
        original_prompt: str,
        error: str,
        error_context: Optional[str],
        attempt: int
    ) -> str:
        """Add error feedback to prompt for retry"""
        feedback = f"""

--- PREVIOUS ATTEMPT {attempt} FAILED ---
Your previous response had a JSON syntax error:
ERROR: {error}
"""

        if error_context:
            feedback += f"""
ERROR LOCATION: {error_context}
"""

        feedback += """
PLEASE FIX THE JSON ERROR AND TRY AGAIN.
Make sure to:
1. Check for missing commas between elements
2. Remove any trailing commas before } or ]
3. Use double quotes for all strings and keys
4. Ensure all brackets/braces are properly closed
5. Do not include any text before { or after }
--- END FEEDBACK ---

"""

        return original_prompt + feedback

    # ========================================================================
    # Tool Calling Methods
    # ========================================================================

    async def generate_with_tools(
        self,
        prompt: str,
        tools: List[Tool],
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        max_iterations: int = 10,
        mode: str = "single",
        tool_timeout: float = 60.0,
        step_callback: Optional[StepCallback] = None
    ) -> ToolCallingResponse:
        """
        Generate with tool calling support.

        Args:
            prompt: User prompt
            tools: List of Tool objects available to the LLM
            system_prompt: Optional system prompt
            model: Model override
            temperature: Sampling temperature
            max_tokens: Maximum output tokens
            max_iterations: Max ReAct iterations (only for mode="react")
            mode: "single" (one LLM call + tools) or "react" (multi-step loop)
            tool_timeout: Timeout in seconds for tool execution
            step_callback: Optional callback for real-time ReAct step events

        Returns:
            ToolCallingResponse with content, tool calls, and metrics
        """
        start_time = time.time()

        # Determine provider and client
        from app.config.models import MODEL_REGISTRY, ModelProvider

        if model and model in MODEL_REGISTRY:
            model_config = MODEL_REGISTRY[model]
            provider = model_config.provider
        else:
            # Default to available provider
            if self.anthropic_client:
                provider = ModelProvider.ANTHROPIC
                model = self.DEFAULT_ANTHROPIC_MODEL
            elif self.openai_client:
                provider = ModelProvider.OPENAI
                model = self.DEFAULT_OPENAI_MODEL
            elif self.gemini_client:
                provider = ModelProvider.GOOGLE
                model = self.DEFAULT_GEMINI_MODEL
            else:
                raise ValueError("No tool-calling-capable LLM client available")

        if mode == "single":
            result = await self._generate_with_tools_single(
                prompt=prompt,
                tools=tools,
                system_prompt=system_prompt,
                model=model,
                provider=provider,
                temperature=temperature,
                max_tokens=max_tokens,
                tool_timeout=tool_timeout
            )
        elif mode == "react":
            result = await self._generate_with_tools_react(
                prompt=prompt,
                tools=tools,
                system_prompt=system_prompt,
                model=model,
                provider=provider,
                temperature=temperature,
                max_tokens=max_tokens,
                max_iterations=max_iterations,
                tool_timeout=tool_timeout,
                step_callback=step_callback
            )
        else:
            raise ValueError(f"Unknown mode: {mode}. Use 'single' or 'react'.")

        result.total_latency_ms = int((time.time() - start_time) * 1000)
        return result

    async def generate_with_tools_for_agent(
        self,
        agent_name: str,
        prompt: str,
        tools: List[Tool],
        system_prompt: Optional[str] = None,
        max_iterations: int = 10,
        mode: str = "single",
        tool_timeout: float = 60.0,
        step_callback: Optional[StepCallback] = None
    ) -> ToolCallingResponse:
        """
        Generate with tools using agent-specific model configuration.

        Args:
            agent_name: Name of the agent
            prompt: User prompt
            tools: List of Tool objects
            system_prompt: Optional system prompt
            max_iterations: Max ReAct iterations
            mode: "single" or "react"
            tool_timeout: Timeout for tool execution
            step_callback: Optional callback for real-time ReAct step events

        Returns:
            ToolCallingResponse with full interaction details
        """
        from app.config.agent_models import get_runtime_config

        config = get_runtime_config()
        model = config.get_model(agent_name)
        temperature = config.get_temperature(agent_name)
        max_tokens = config.get_max_tokens(agent_name)

        return await self.generate_with_tools(
            prompt=prompt,
            tools=tools,
            system_prompt=system_prompt,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            max_iterations=max_iterations,
            mode=mode,
            tool_timeout=tool_timeout,
            step_callback=step_callback
        )

    async def _generate_with_tools_single(
        self,
        prompt: str,
        tools: List[Tool],
        system_prompt: Optional[str],
        model: str,
        provider: "ModelProvider",
        temperature: float,
        max_tokens: int,
        tool_timeout: float
    ) -> ToolCallingResponse:
        """
        Single-shot tool calling: one LLM call, execute any tools, return.
        """
        from app.config.models import ModelProvider

        # Build messages
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        # Call LLM with tools
        if provider == ModelProvider.ANTHROPIC:
            response, tool_calls = await self._call_anthropic_with_tools(
                messages=messages,
                tools=tools,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens
            )
        elif provider == ModelProvider.OPENAI:
            response, tool_calls = await self._call_openai_with_tools(
                messages=messages,
                tools=tools,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens
            )
        elif provider == ModelProvider.GOOGLE:
            response, tool_calls = await self._call_gemini_with_tools(
                messages=messages,
                tools=tools,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens
            )
        else:
            raise ValueError(f"Provider {provider} does not support tool calling")

        # Execute tool calls if any
        tool_results = []
        if tool_calls:
            tool_results = await self._execute_tools(tool_calls, tools, tool_timeout)

            # If we got tool results, make a final LLM call for the response
            if tool_results:
                # Add assistant message with tool calls
                if provider == ModelProvider.ANTHROPIC:
                    final_response = await self._call_anthropic_with_tool_results(
                        messages=messages,
                        tool_calls=tool_calls,
                        tool_results=tool_results,
                        model=model,
                        temperature=temperature,
                        max_tokens=max_tokens
                    )
                elif provider == ModelProvider.OPENAI:
                    final_response = await self._call_openai_with_tool_results(
                        messages=messages,
                        tool_calls=tool_calls,
                        tool_results=tool_results,
                        model=model,
                        temperature=temperature,
                        max_tokens=max_tokens
                    )
                elif provider == ModelProvider.GOOGLE:
                    final_response = await self._call_gemini_with_tool_results(
                        messages=messages,
                        tool_calls=tool_calls,
                        tool_results=tool_results,
                        model=model,
                        temperature=temperature,
                        max_tokens=max_tokens
                    )

                return ToolCallingResponse(
                    content=final_response.content,
                    model=model,
                    tool_calls=tool_calls,
                    tool_results=tool_results,
                    iterations=1,
                    total_input_tokens=response.input_tokens + final_response.input_tokens,
                    total_output_tokens=response.output_tokens + final_response.output_tokens,
                    stop_reason="completed"
                )

        return ToolCallingResponse(
            content=response.content,
            model=model,
            tool_calls=tool_calls,
            tool_results=tool_results,
            iterations=1,
            total_input_tokens=response.input_tokens,
            total_output_tokens=response.output_tokens,
            stop_reason="completed"
        )

    async def _generate_with_tools_react(
        self,
        prompt: str,
        tools: List[Tool],
        system_prompt: Optional[str],
        model: str,
        provider: "ModelProvider",
        temperature: float,
        max_tokens: int,
        max_iterations: int,
        tool_timeout: float,
        step_callback: Optional[StepCallback] = None
    ) -> ToolCallingResponse:
        """
        ReAct loop: Reason→Act→Observe until task complete or max iterations.

        If step_callback is provided, emits LiveStepEvent objects in real-time
        as the agent reasons, acts, and observes.
        """
        from datetime import datetime
        from app.config.models import ModelProvider

        # Build ReAct system prompt
        react_system = self._build_react_system_prompt(system_prompt, tools)

        # Initialize conversation
        messages = [
            {"role": "system", "content": react_system},
            {"role": "user", "content": prompt}
        ]

        all_tool_calls = []
        all_tool_results = []
        react_trace = []
        total_input_tokens = 0
        total_output_tokens = 0
        stop_reason = "completed"

        # Track previous states for stopping condition detection
        previous_tool_call_signatures = []
        previous_thoughts = []
        no_progress_count = 0
        MAX_NO_PROGRESS = 2  # Stop if no progress for 2 iterations

        for iteration in range(max_iterations):
            logger.debug(f"ReAct iteration {iteration + 1}/{max_iterations}")

            # Call LLM
            if provider == ModelProvider.ANTHROPIC:
                response, tool_calls = await self._call_anthropic_with_tools(
                    messages=messages,
                    tools=tools,
                    model=model,
                    temperature=temperature,
                    max_tokens=max_tokens
                )
            elif provider == ModelProvider.OPENAI:
                response, tool_calls = await self._call_openai_with_tools(
                    messages=messages,
                    tools=tools,
                    model=model,
                    temperature=temperature,
                    max_tokens=max_tokens
                )
            elif provider == ModelProvider.GOOGLE:
                response, tool_calls = await self._call_gemini_with_tools(
                    messages=messages,
                    tools=tools,
                    model=model,
                    temperature=temperature,
                    max_tokens=max_tokens
                )
            else:
                raise ValueError(f"Provider {provider} does not support tool calling")

            total_input_tokens += response.input_tokens
            total_output_tokens += response.output_tokens

            # Parse thought from response
            thought = response.content or ""

            # === EMIT THOUGHT EVENT ===
            if step_callback and thought:
                await step_callback(LiveStepEvent(
                    type="thought",
                    content=thought,
                    timestamp=datetime.utcnow().isoformat(),
                    iteration=iteration
                ))

            # Check if we're done (no tool calls = final answer)
            if not tool_calls:
                # Recovery: If content is empty, force one more LLM call without tools
                # This happens when Gemini returns empty response after failed validations
                if not thought.strip() and iteration > 0:
                    logger.warning(
                        f"ReAct: Empty final answer at iteration {iteration}. "
                        f"Forcing recovery call without tools."
                    )
                    # Build recovery prompt asking LLM to produce its final answer
                    recovery_msg = {
                        "role": "user",
                        "content": (
                            "You returned an empty response. Please provide your FINAL ANSWER now.\n\n"
                            "Output ONLY a complete, valid JSON object — no markdown, no explanation.\n"
                            "Based on all the tool results you've gathered, produce the complete JSON output."
                        )
                    }
                    recovery_messages = messages + [recovery_msg]

                    try:
                        if provider == ModelProvider.ANTHROPIC:
                            recovery_resp, recovery_tc = await self._call_anthropic_with_tools(
                                messages=recovery_messages, tools=[], model=model,
                                temperature=temperature, max_tokens=max_tokens
                            )
                        elif provider == ModelProvider.OPENAI:
                            recovery_resp, recovery_tc = await self._call_openai_with_tools(
                                messages=recovery_messages, tools=[], model=model,
                                temperature=temperature, max_tokens=max_tokens
                            )
                        elif provider == ModelProvider.GOOGLE:
                            recovery_resp, recovery_tc = await self._call_gemini_with_tools(
                                messages=recovery_messages, tools=[], model=model,
                                temperature=temperature, max_tokens=max_tokens
                            )
                        else:
                            recovery_resp = None

                        if recovery_resp and recovery_resp.content and recovery_resp.content.strip():
                            thought = recovery_resp.content
                            total_input_tokens += recovery_resp.input_tokens
                            total_output_tokens += recovery_resp.output_tokens
                            logger.info(f"ReAct: Recovery call produced {len(thought)} chars")
                        else:
                            logger.warning("ReAct: Recovery call also returned empty content")
                    except Exception as recovery_err:
                        logger.warning(f"ReAct: Recovery call failed: {recovery_err}")

                # === EMIT DECISION EVENT (final answer) ===
                if step_callback:
                    await step_callback(LiveStepEvent(
                        type="decision",
                        content=thought if thought else "[Final answer provided]",
                        timestamp=datetime.utcnow().isoformat(),
                        iteration=iteration
                    ))
                react_trace.append(ReActStep(
                    thought=thought,
                    action=None,
                    observation="[FINAL ANSWER]",
                    iteration=iteration
                ))
                break

            # =====================================================================
            # ADDITIONAL STOPPING CONDITIONS (Research-backed improvements)
            # =====================================================================

            # 1. Check for repeated tool calls (no progress)
            current_signature = tuple(sorted([(tc.name, str(tc.arguments)) for tc in tool_calls]))
            if current_signature in previous_tool_call_signatures:
                no_progress_count += 1
                logger.warning(f"ReAct: Repeated tool call pattern detected (count: {no_progress_count})")
                if no_progress_count >= MAX_NO_PROGRESS:
                    react_trace.append(ReActStep(
                        thought=thought,
                        action=tool_calls[0] if tool_calls else None,
                        observation="[STOPPED: No progress - repeated tool calls]",
                        iteration=iteration
                    ))
                    stop_reason = "no_progress"
                    break
            else:
                no_progress_count = 0
            previous_tool_call_signatures.append(current_signature)

            # 2. Check for thought repetition (agent stuck in reasoning loop)
            thought_key = thought.strip().lower()[:200] if thought else ""
            if thought_key and thought_key in previous_thoughts:
                logger.warning(f"ReAct: Repeated thought pattern detected")
                react_trace.append(ReActStep(
                    thought=thought,
                    action=tool_calls[0] if tool_calls else None,
                    observation="[STOPPED: Repeated reasoning pattern]",
                    iteration=iteration
                ))
                stop_reason = "thought_repetition"
                break
            if thought_key:
                previous_thoughts.append(thought_key)

            # === EMIT ACTION EVENT (before tool execution) ===
            for tc in tool_calls:
                if step_callback:
                    await step_callback(LiveStepEvent(
                        type="action",
                        content=f"Calling {tc.name} with args: {json.dumps(tc.arguments)[:200]}",
                        tool=tc.name,
                        timestamp=datetime.utcnow().isoformat(),
                        iteration=iteration
                    ))

            # Execute tools
            tool_results = await self._execute_tools(tool_calls, tools, tool_timeout)
            all_tool_calls.extend(tool_calls)
            all_tool_results.extend(tool_results)

            # Format observation
            observation = self._format_tool_results_for_react(tool_results)

            # === EMIT OBSERVATION EVENT (after tool execution) ===
            if step_callback:
                # Summarize observation for live display (truncate if too long)
                obs_summary = observation[:500] + "..." if len(observation) > 500 else observation
                await step_callback(LiveStepEvent(
                    type="observation",
                    content=obs_summary,
                    timestamp=datetime.utcnow().isoformat(),
                    iteration=iteration
                ))

            # Record trace
            react_trace.append(ReActStep(
                thought=thought,
                action=tool_calls[0] if tool_calls else None,
                observation=observation,
                iteration=iteration
            ))

            # Update messages for next iteration
            if provider == ModelProvider.ANTHROPIC:
                messages = self._update_messages_anthropic(
                    messages, thought, tool_calls, tool_results
                )
            elif provider == ModelProvider.OPENAI:
                messages = self._update_messages_openai(
                    messages, thought, tool_calls, tool_results
                )
            elif provider == ModelProvider.GOOGLE:
                # Pass raw Gemini content to preserve thought signatures (critical for Gemini 3)
                raw_content = getattr(response, '_raw_gemini_content', None)
                messages = self._update_messages_gemini(
                    messages, thought, tool_calls, tool_results,
                    raw_gemini_content=raw_content
                )

        else:
            # Max iterations reached
            stop_reason = "max_iterations"
            logger.warning(f"ReAct loop hit max iterations ({max_iterations})")

        # Final recovery: if thought is still empty, scan conversation for last JSON
        if not thought or not thought.strip():
            logger.warning("ReAct: Final thought is empty. Scanning conversation for JSON.")
            for msg in reversed(messages):
                content = msg.get("content", "")
                if isinstance(content, str) and "{" in content and len(content) > 50:
                    thought = content
                    logger.info(f"ReAct: Recovered content from conversation history ({len(content)} chars)")
                    break

        return ToolCallingResponse(
            content=thought,
            model=model,
            tool_calls=all_tool_calls,
            tool_results=all_tool_results,
            react_trace=react_trace,
            iterations=len(react_trace),
            total_input_tokens=total_input_tokens,
            total_output_tokens=total_output_tokens,
            stop_reason=stop_reason
        )

    def _build_react_system_prompt(self, base_prompt: Optional[str], tools: List[Tool]) -> str:
        """Build system prompt for ReAct reasoning."""
        tool_descriptions = "\n".join([
            f"- {t.name}: {t.description}"
            for t in tools
        ])

        react_prompt = f"""You are an AI assistant that uses the ReAct (Reasoning and Acting) framework.

For each step:
1. THOUGHT: Think about what you need to do and why
2. ACTION: If needed, use a tool to gather information or take action
3. OBSERVATION: Receive the result of your action

Continue this cycle until you can provide a final answer.

When you have enough information to answer, respond WITHOUT using any tools.

Available tools:
{tool_descriptions}

{base_prompt or ''}

Remember:
- Think step by step
- Use tools when you need information or to take action
- When you're ready to give a final answer, just respond without tool calls
"""
        return react_prompt

    async def _execute_tools(
        self,
        tool_calls: List[ToolCall],
        tools: List[Tool],
        timeout: float,
        max_retries: int = 2,
        retry_delay: float = 1.0
    ) -> List[ToolResult]:
        """
        Execute tool calls and return results with retry logic for transient failures.

        Args:
            tool_calls: List of tool calls to execute
            tools: Available tools
            timeout: Timeout per tool call
            max_retries: Maximum retries for transient failures (default 2)
            retry_delay: Delay between retries in seconds (default 1.0)
        """
        tool_map = {t.name: t for t in tools}
        results = []

        # Transient error patterns that should trigger retry
        TRANSIENT_ERRORS = [
            "timeout",
            "rate limit",
            "429",
            "503",
            "502",
            "504",
            "connection",
            "temporary",
            "retry",
            "unavailable",
        ]

        def is_transient_error(error: str) -> bool:
            """Check if error is likely transient and worth retrying."""
            error_lower = error.lower()
            return any(pattern in error_lower for pattern in TRANSIENT_ERRORS)

        for tc in tool_calls:
            start_time = time.time()

            if tc.name not in tool_map:
                results.append(ToolResult(
                    tool_call_id=tc.id,
                    name=tc.name,
                    result=None,
                    status=ToolCallStatus.ERROR,
                    error=f"Tool '{tc.name}' not found"
                ))
                continue

            tool = tool_map[tc.name]
            last_error = None

            # Retry loop for transient failures
            for attempt in range(max_retries + 1):
                try:
                    # Execute with timeout
                    result = await asyncio.wait_for(
                        tool.function(**tc.arguments),
                        timeout=timeout
                    )

                    results.append(ToolResult(
                        tool_call_id=tc.id,
                        name=tc.name,
                        result=result,
                        status=ToolCallStatus.SUCCESS,
                        latency_ms=int((time.time() - start_time) * 1000)
                    ))
                    break  # Success, exit retry loop

                except asyncio.TimeoutError:
                    last_error = f"Tool '{tc.name}' timed out after {timeout}s"
                    if attempt < max_retries:
                        logger.warning(f"{last_error} (attempt {attempt + 1}/{max_retries + 1}), retrying...")
                        await asyncio.sleep(retry_delay)
                    else:
                        results.append(ToolResult(
                            tool_call_id=tc.id,
                            name=tc.name,
                            result=None,
                            status=ToolCallStatus.TIMEOUT,
                            error=last_error,
                            latency_ms=int((time.time() - start_time) * 1000)
                        ))

                except Exception as e:
                    last_error = str(e)

                    # Only retry if it looks like a transient error
                    if attempt < max_retries and is_transient_error(last_error):
                        logger.warning(f"Tool '{tc.name}' transient error: {last_error} (attempt {attempt + 1}/{max_retries + 1}), retrying...")
                        await asyncio.sleep(retry_delay * (attempt + 1))  # Exponential backoff
                    else:
                        logger.error(f"Tool '{tc.name}' execution error: {e}", exc_info=True)
                        results.append(ToolResult(
                            tool_call_id=tc.id,
                            name=tc.name,
                            result=None,
                            status=ToolCallStatus.ERROR,
                            error=last_error,
                            latency_ms=int((time.time() - start_time) * 1000)
                        ))
                        break  # Non-transient error, don't retry

        return results

    def _format_tool_results_for_react(self, results: List[ToolResult]) -> str:
        """Format tool results for ReAct observation."""
        parts = []
        for r in results:
            if r.status == ToolCallStatus.SUCCESS:
                result_str = json.dumps(r.result) if not isinstance(r.result, str) else r.result
                parts.append(f"[{r.name}] Result: {result_str}")
            else:
                parts.append(f"[{r.name}] Error: {r.error}")
        return "\n".join(parts)

    # ========================================================================
    # Provider-specific tool calling implementations
    # ========================================================================

    async def _call_openai_with_tools(
        self,
        messages: List[Dict],
        tools: List[Tool],
        model: str,
        temperature: float,
        max_tokens: int
    ) -> tuple[LLMResponse, List[ToolCall]]:
        """Call OpenAI with tool support."""
        if not self.openai_client:
            raise ValueError("OpenAI client not initialized")

        openai_tools = [t.to_openai_format() for t in tools]

        response = await self.openai_client.chat.completions.create(
            model=model,
            messages=messages,
            tools=openai_tools if openai_tools else None,
            temperature=temperature,
            max_tokens=max_tokens
        )

        # Parse tool calls
        tool_calls = []
        message = response.choices[0].message

        if message.tool_calls:
            for tc in message.tool_calls:
                try:
                    args = json.loads(tc.function.arguments) if tc.function.arguments else {}
                except json.JSONDecodeError:
                    args = {}

                tool_calls.append(ToolCall(
                    id=tc.id,
                    name=tc.function.name,
                    arguments=args
                ))

        llm_response = LLMResponse(
            content=message.content or "",
            model=model,
            input_tokens=response.usage.prompt_tokens if response.usage else 0,
            output_tokens=response.usage.completion_tokens if response.usage else 0
        )

        return llm_response, tool_calls

    async def _call_openai_with_tool_results(
        self,
        messages: List[Dict],
        tool_calls: List[ToolCall],
        tool_results: List[ToolResult],
        model: str,
        temperature: float,
        max_tokens: int
    ) -> LLMResponse:
        """Call OpenAI after tool execution."""
        # Build updated messages
        updated_messages = copy.deepcopy(messages)

        # Add assistant message with tool calls
        updated_messages.append({
            "role": "assistant",
            "tool_calls": [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.name,
                        "arguments": json.dumps(tc.arguments)
                    }
                }
                for tc in tool_calls
            ]
        })

        # Add tool results
        for tr in tool_results:
            result_content = (
                json.dumps(tr.result) if tr.status == ToolCallStatus.SUCCESS
                else f"Error: {tr.error}"
            )
            updated_messages.append({
                "role": "tool",
                "tool_call_id": tr.tool_call_id,
                "content": result_content
            })

        response = await self.openai_client.chat.completions.create(
            model=model,
            messages=updated_messages,
            temperature=temperature,
            max_tokens=max_tokens
        )

        return LLMResponse(
            content=response.choices[0].message.content or "",
            model=model,
            input_tokens=response.usage.prompt_tokens if response.usage else 0,
            output_tokens=response.usage.completion_tokens if response.usage else 0
        )

    def _update_messages_openai(
        self,
        messages: List[Dict],
        thought: str,
        tool_calls: List[ToolCall],
        tool_results: List[ToolResult]
    ) -> List[Dict]:
        """Update message history for OpenAI in ReAct loop."""
        updated = copy.deepcopy(messages)

        # Add assistant message
        assistant_msg = {"role": "assistant", "content": thought}
        if tool_calls:
            assistant_msg["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.name,
                        "arguments": json.dumps(tc.arguments)
                    }
                }
                for tc in tool_calls
            ]
        updated.append(assistant_msg)

        # Add tool results
        for tr in tool_results:
            result_content = (
                json.dumps(tr.result) if tr.status == ToolCallStatus.SUCCESS
                else f"Error: {tr.error}"
            )
            updated.append({
                "role": "tool",
                "tool_call_id": tr.tool_call_id,
                "content": result_content
            })

        return updated

    async def _call_anthropic_with_tools(
        self,
        messages: List[Dict],
        tools: List[Tool],
        model: str,
        temperature: float,
        max_tokens: int
    ) -> tuple[LLMResponse, List[ToolCall]]:
        """Call Anthropic with tool support."""
        if not self.anthropic_client:
            raise ValueError("Anthropic client not initialized")

        anthropic_tools = [t.to_anthropic_format() for t in tools]

        # Separate system from messages
        system_prompt = ""
        user_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system_prompt = msg["content"]
            else:
                user_messages.append(msg)

        response = await self.anthropic_client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system_prompt,
            messages=user_messages,
            tools=anthropic_tools if anthropic_tools else None,
            temperature=temperature
        )

        # Parse response content and tool calls
        text_content = ""
        tool_calls = []

        for block in response.content:
            if block.type == "text":
                text_content += block.text
            elif block.type == "tool_use":
                tool_calls.append(ToolCall(
                    id=block.id,
                    name=block.name,
                    arguments=block.input or {}
                ))

        llm_response = LLMResponse(
            content=text_content,
            model=model,
            input_tokens=response.usage.input_tokens if response.usage else 0,
            output_tokens=response.usage.output_tokens if response.usage else 0
        )

        return llm_response, tool_calls

    async def _call_anthropic_with_tool_results(
        self,
        messages: List[Dict],
        tool_calls: List[ToolCall],
        tool_results: List[ToolResult],
        model: str,
        temperature: float,
        max_tokens: int
    ) -> LLMResponse:
        """Call Anthropic after tool execution."""
        # Separate system from messages
        system_prompt = ""
        user_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system_prompt = msg["content"]
            else:
                user_messages.append(msg)

        # Add assistant message with tool use
        assistant_content = []
        for tc in tool_calls:
            assistant_content.append({
                "type": "tool_use",
                "id": tc.id,
                "name": tc.name,
                "input": tc.arguments
            })

        user_messages.append({
            "role": "assistant",
            "content": assistant_content
        })

        # Add tool results
        tool_result_content = []
        for tr in tool_results:
            result_content = (
                json.dumps(tr.result) if tr.status == ToolCallStatus.SUCCESS
                else f"Error: {tr.error}"
            )
            tool_result_content.append({
                "type": "tool_result",
                "tool_use_id": tr.tool_call_id,
                "content": result_content
            })

        user_messages.append({
            "role": "user",
            "content": tool_result_content
        })

        response = await self.anthropic_client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system_prompt,
            messages=user_messages,
            temperature=temperature
        )

        text_content = ""
        for block in response.content:
            if block.type == "text":
                text_content += block.text

        return LLMResponse(
            content=text_content,
            model=model,
            input_tokens=response.usage.input_tokens if response.usage else 0,
            output_tokens=response.usage.output_tokens if response.usage else 0
        )

    def _update_messages_anthropic(
        self,
        messages: List[Dict],
        thought: str,
        tool_calls: List[ToolCall],
        tool_results: List[ToolResult]
    ) -> List[Dict]:
        """Update message history for Anthropic in ReAct loop."""
        updated = copy.deepcopy(messages)

        # Build assistant content
        assistant_content = []
        if thought:
            assistant_content.append({"type": "text", "text": thought})

        for tc in tool_calls:
            assistant_content.append({
                "type": "tool_use",
                "id": tc.id,
                "name": tc.name,
                "input": tc.arguments
            })

        if assistant_content:
            updated.append({"role": "assistant", "content": assistant_content})

        # Add tool results as user message
        if tool_results:
            tool_result_content = []
            for tr in tool_results:
                result_content = (
                    json.dumps(tr.result) if tr.status == ToolCallStatus.SUCCESS
                    else f"Error: {tr.error}"
                )
                tool_result_content.append({
                    "type": "tool_result",
                    "tool_use_id": tr.tool_call_id,
                    "content": result_content
                })
            updated.append({"role": "user", "content": tool_result_content})

        return updated

    async def _call_gemini_with_tools(
        self,
        messages: List[Dict],
        tools: List[Tool],
        model: str,
        temperature: float,
        max_tokens: int
    ) -> tuple[LLMResponse, List[ToolCall]]:
        """
        Call Google Gemini with tool support using native Content format.

        Uses Gemini's native Content/Part structure for better multi-turn
        conversation support in agentic systems.

        IMPORTANT: For Gemini 3 models, thought signatures are automatically preserved
        when using the _raw_gemini_content field in messages. This is critical for
        multi-turn function calling to work correctly.
        """
        if not self.gemini_client:
            raise ValueError("Gemini client not initialized")

        from google.genai import types
        import asyncio

        # Build Gemini function declarations
        function_declarations = [
            types.FunctionDeclaration(
                name=t.name,
                description=t.description,
                parameters=t.parameters
            )
            for t in tools
        ]

        gemini_tools = [types.Tool(function_declarations=function_declarations)]

        # Build native Gemini Content format for better agentic support
        contents = []
        system_instruction = None

        for msg in messages:
            if msg["role"] == "system":
                # Gemini has dedicated system_instruction support
                system_instruction = msg["content"]

            # CRITICAL: Check for preserved raw Gemini content (for thought signatures)
            elif "_raw_gemini_content" in msg:
                # Use the raw content directly to preserve thought signatures (Gemini 3)
                contents.append(msg["_raw_gemini_content"])

            elif msg["role"] == "user":
                content = msg.get("content", "")
                # Handle both string content and structured content
                if isinstance(content, str):
                    contents.append(types.Content(
                        role="user",
                        parts=[types.Part.from_text(text=content)]
                    ))
                elif isinstance(content, list):
                    # Handle tool results in ReAct loop (structured content)
                    parts = []
                    for item in content:
                        if isinstance(item, dict) and item.get("type") == "function_response":
                            parts.append(types.Part.from_function_response(
                                name=item["name"],
                                response={"result": item["response"]}
                            ))
                        elif isinstance(item, dict) and "text" in item:
                            parts.append(types.Part.from_text(text=item["text"]))
                        elif isinstance(item, str):
                            parts.append(types.Part.from_text(text=item))
                    if parts:
                        contents.append(types.Content(role="user", parts=parts))

            elif msg["role"] == "assistant" or msg["role"] == "model":
                content = msg.get("content", "")
                if isinstance(content, str):
                    contents.append(types.Content(
                        role="model",
                        parts=[types.Part.from_text(text=content)]
                    ))
                elif isinstance(content, list):
                    # Handle function calls in ReAct loop
                    parts = []
                    for item in content:
                        if isinstance(item, dict) and item.get("type") == "function_call":
                            parts.append(types.Part.from_function_call(
                                name=item["name"],
                                args=item.get("args", {})
                            ))
                        elif isinstance(item, dict) and "text" in item:
                            parts.append(types.Part.from_text(text=item["text"]))
                        elif isinstance(item, str):
                            parts.append(types.Part.from_text(text=item))
                    if parts:
                        contents.append(types.Content(role="model", parts=parts))

        # Fallback: if no contents were built, use simple string format
        if not contents:
            full_prompt = "\n\n".join([
                f"{msg['role'].title()}: {msg.get('content', '')}"
                for msg in messages
            ])
            contents = full_prompt

        # Build config with tool_config for agentic control
        # Note: For Gemini 3 models, keeping temperature at default (1.0) is recommended
        # to avoid looping or degraded performance in complex reasoning tasks
        config = types.GenerateContentConfig(
            temperature=temperature,
            max_output_tokens=max_tokens,
            tools=gemini_tools if tools else None,
            tool_config=types.ToolConfig(
                function_calling_config=types.FunctionCallingConfig(
                    mode="AUTO"  # AUTO lets model decide; use "ANY" to force tool use
                )
            ) if tools else None
        )

        # Add system instruction if present
        if system_instruction:
            config.system_instruction = system_instruction

        # Run synchronous Gemini call in thread pool to avoid blocking event loop
        response = await asyncio.to_thread(
            self.gemini_client.models.generate_content,
            model=model,
            contents=contents,
            config=config
        )

        # Parse response - handle both text and function_call parts
        text_content = ""
        tool_calls = []

        # IMPORTANT: Store the raw response content for thought signature preservation
        # This is critical for Gemini 3 models in multi-turn function calling
        raw_model_content = None
        if hasattr(response, 'candidates') and response.candidates:
            raw_model_content = response.candidates[0].content

        # Always iterate through parts to capture BOTH text AND function_call parts.
        # Using response.text alone misses function_calls when the response is mixed.
        if hasattr(response, 'parts') and response.parts:
            for part in response.parts:
                if hasattr(part, 'text') and part.text:
                    text_content += part.text
                elif hasattr(part, 'function_call') and part.function_call:
                    fc = part.function_call
                    tool_calls.append(ToolCall(
                        id=f"gemini_{fc.name}_{len(tool_calls)}",
                        name=fc.name,
                        arguments=dict(fc.args) if fc.args else {}
                    ))
        elif hasattr(response, 'text') and response.text:
            text_content = response.text

        # Get token counts from usage_metadata
        input_tokens = 0
        output_tokens = 0
        if hasattr(response, 'usage_metadata') and response.usage_metadata:
            input_tokens = getattr(response.usage_metadata, 'prompt_token_count', 0) or 0
            output_tokens = getattr(response.usage_metadata, 'candidates_token_count', 0) or 0

        llm_response = LLMResponse(
            content=text_content,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens
        )

        # Store raw content for thought signature preservation (Gemini 3)
        if raw_model_content:
            llm_response._raw_gemini_content = raw_model_content

        return llm_response, tool_calls

    async def _call_gemini_with_tool_results(
        self,
        messages: List[Dict],
        tool_calls: List[ToolCall],
        tool_results: List[ToolResult],
        model: str,
        temperature: float,
        max_tokens: int
    ) -> LLMResponse:
        """
        Call Gemini after tool execution using native FunctionResponse format.

        Uses Gemini's native Content structure with FunctionCall and FunctionResponse
        parts for proper multi-turn tool calling in agentic systems.
        """
        from google.genai import types
        import asyncio

        # Build native Gemini Content format
        contents = []
        system_instruction = None

        # Process original messages
        for msg in messages:
            if msg["role"] == "system":
                system_instruction = msg["content"]
            elif msg["role"] == "user":
                content = msg.get("content", "")
                if isinstance(content, str):
                    contents.append(types.Content(
                        role="user",
                        parts=[types.Part.from_text(text=content)]
                    ))

        # Add model's function calls as a model turn
        function_call_parts = []
        for tc in tool_calls:
            function_call_parts.append(types.Part.from_function_call(
                name=tc.name,
                args=tc.arguments
            ))

        if function_call_parts:
            contents.append(types.Content(
                role="model",
                parts=function_call_parts
            ))

        # Add function responses as a user turn (Gemini convention)
        function_response_parts = []
        for tr in tool_results:
            if tr.status == ToolCallStatus.SUCCESS:
                # Ensure result is serializable
                result_data = tr.result
                if isinstance(result_data, str):
                    result_data = {"result": result_data}
                elif not isinstance(result_data, dict):
                    result_data = {"result": str(result_data)}

                function_response_parts.append(types.Part.from_function_response(
                    name=tr.name,
                    response=result_data
                ))
            else:
                # Pass error as response
                function_response_parts.append(types.Part.from_function_response(
                    name=tr.name,
                    response={"error": tr.error or "Unknown error"}
                ))

        if function_response_parts:
            contents.append(types.Content(
                role="user",
                parts=function_response_parts
            ))

        # Build config
        config = types.GenerateContentConfig(
            temperature=temperature,
            max_output_tokens=max_tokens
        )

        # Add system instruction if present
        if system_instruction:
            config.system_instruction = system_instruction

        # Run synchronous Gemini call in thread pool
        response = await asyncio.to_thread(
            self.gemini_client.models.generate_content,
            model=model,
            contents=contents,
            config=config
        )

        # Parse response
        text_content = ""
        if hasattr(response, 'text'):
            text_content = response.text
        elif hasattr(response, 'parts'):
            for part in response.parts:
                if hasattr(part, 'text') and part.text:
                    text_content += part.text

        input_tokens = 0
        output_tokens = 0
        if hasattr(response, 'usage_metadata') and response.usage_metadata:
            input_tokens = getattr(response.usage_metadata, 'prompt_token_count', 0) or 0
            output_tokens = getattr(response.usage_metadata, 'candidates_token_count', 0) or 0

        return LLMResponse(
            content=text_content,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens
        )

    def _update_messages_gemini(
        self,
        messages: List[Dict],
        thought: str,
        tool_calls: List[ToolCall],
        tool_results: List[ToolResult],
        raw_gemini_content: Any = None
    ) -> List[Dict]:
        """
        Update message history for Gemini in ReAct loop using structured format.

        Uses a structured content format that _call_gemini_with_tools can convert
        to native Gemini Content objects with FunctionCall/FunctionResponse parts.

        CRITICAL for Gemini 3: If raw_gemini_content is provided, it's stored directly
        in the message to preserve thought signatures. This is required for Gemini 3
        models to maintain their reasoning chain across multi-turn function calling.

        Args:
            messages: Current message history
            thought: The model's reasoning text
            tool_calls: List of tool calls made
            tool_results: Results from tool execution
            raw_gemini_content: Optional raw Content object from response.candidates[0].content
                               Pass this to preserve thought signatures for Gemini 3
        """
        updated = copy.deepcopy(messages)

        # CRITICAL: If we have raw Gemini content, use it directly to preserve thought signatures
        # This is required for Gemini 3 models to work correctly in multi-turn function calling
        if raw_gemini_content is not None:
            # Store the raw content - it will be used directly in _call_gemini_with_tools
            updated.append({
                "role": "model",
                "content": thought,  # Keep text for fallback/logging
                "_raw_gemini_content": raw_gemini_content
            })
        else:
            # Fallback: Build assistant content with thought and function calls
            assistant_content = []

            # Add thought as text part
            if thought:
                assistant_content.append({"type": "text", "text": thought})

            # Add function calls as structured parts
            for tc in tool_calls:
                assistant_content.append({
                    "type": "function_call",
                    "name": tc.name,
                    "args": tc.arguments
                })

            # If we have structured content, use it; otherwise fall back to string
            if assistant_content:
                updated.append({"role": "model", "content": assistant_content})
            elif thought:
                updated.append({"role": "model", "content": thought})

        # Add tool results as structured function responses
        # Note: Tool results don't need thought signature preservation
        if tool_results:
            from google.genai import types

            user_content = []
            function_response_parts = []

            for tr in tool_results:
                if tr.status == ToolCallStatus.SUCCESS:
                    result_data = tr.result
                    if isinstance(result_data, str):
                        result_data = result_data
                    elif not isinstance(result_data, dict):
                        result_data = str(result_data)
                    else:
                        result_data = json.dumps(result_data)

                    user_content.append({
                        "type": "function_response",
                        "name": tr.name,
                        "response": result_data
                    })

                    # Also build native Gemini parts for direct use
                    try:
                        response_dict = {"result": result_data} if isinstance(result_data, str) else result_data
                        if isinstance(response_dict, str):
                            response_dict = {"result": response_dict}
                        function_response_parts.append(types.Part.from_function_response(
                            name=tr.name,
                            response=response_dict
                        ))
                    except Exception:
                        pass  # Fall back to structured format
                else:
                    user_content.append({
                        "type": "function_response",
                        "name": tr.name,
                        "response": f"Error: {tr.error}"
                    })

            # Store user content with optional raw parts
            user_msg = {"role": "user", "content": user_content}
            if function_response_parts:
                try:
                    user_msg["_raw_gemini_content"] = types.Content(
                        role="user",
                        parts=function_response_parts
                    )
                except Exception:
                    pass  # Fall back to structured format

            updated.append(user_msg)

        return updated

    # ========================================================================
    # Original provider methods (without tools)
    # ========================================================================

    async def _call_openai(
        self,
        prompt: str,
        system_prompt: Optional[str],
        model: Optional[str],
        temperature: float,
        max_tokens: int
    ) -> LLMResponse:
        """Call OpenAI API with retry logic"""
        if not self.openai_client:
            raise ValueError("OpenAI client not initialized")

        model = model or self.DEFAULT_OPENAI_MODEL

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        logger.debug(f"OpenAI request - model: {model}, messages: {len(messages)}")

        # Retry loop
        last_error = None
        delay = self.retry_config.initial_delay

        for attempt in range(self.retry_config.max_retries):
            try:
                response = await self.openai_client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens
                )

                return LLMResponse(
                    content=response.choices[0].message.content,
                    model=model,
                    input_tokens=response.usage.prompt_tokens if response.usage else 0,
                    output_tokens=response.usage.completion_tokens if response.usage else 0,
                    total_tokens=response.usage.total_tokens if response.usage else 0
                )

            except Exception as e:
                last_error = e
                logger.warning(f"OpenAI attempt {attempt + 1} failed: {e}")

                if attempt < self.retry_config.max_retries - 1:
                    await asyncio.sleep(delay)
                    delay = min(
                        delay * self.retry_config.exponential_base,
                        self.retry_config.max_delay
                    )

        raise last_error

    async def _call_anthropic(
        self,
        prompt: str,
        system_prompt: Optional[str],
        model: Optional[str],
        temperature: float,
        max_tokens: int
    ) -> LLMResponse:
        """Call Anthropic API with retry logic"""
        if not self.anthropic_client:
            raise ValueError("Anthropic client not initialized")

        model = model or self.DEFAULT_ANTHROPIC_MODEL

        logger.debug(f"Anthropic request - model: {model}")

        # Retry loop
        last_error = None
        delay = self.retry_config.initial_delay

        for attempt in range(self.retry_config.max_retries):
            try:
                response = await self.anthropic_client.messages.create(
                    model=model,
                    max_tokens=max_tokens,
                    system=system_prompt or "",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=temperature
                )

                logger.debug(
                    f"Anthropic response: model={model}, stop_reason={response.stop_reason}, "
                    f"output_tokens={response.usage.output_tokens if response.usage else '?'}, "
                    f"content_len={len(response.content[0].text) if response.content else 0}"
                )

                return LLMResponse(
                    content=response.content[0].text,
                    model=model,
                    input_tokens=response.usage.input_tokens if response.usage else 0,
                    output_tokens=response.usage.output_tokens if response.usage else 0,
                    total_tokens=(
                        (response.usage.input_tokens + response.usage.output_tokens)
                        if response.usage else 0
                    )
                )

            except Exception as e:
                last_error = e
                logger.warning(f"Anthropic attempt {attempt + 1} failed: {e}")

                if attempt < self.retry_config.max_retries - 1:
                    await asyncio.sleep(delay)
                    delay = min(
                        delay * self.retry_config.exponential_base,
                        self.retry_config.max_delay
                    )

        raise last_error

    async def _call_gemini(
        self,
        prompt: str,
        system_prompt: Optional[str],
        model: Optional[str],
        temperature: float,
        max_tokens: int
    ) -> LLMResponse:
        """Call Google Gemini API with retry logic"""
        if not self.gemini_client:
            raise ValueError("Gemini client not initialized")

        model = model or self.DEFAULT_GEMINI_MODEL

        # Build the combined prompt (Gemini uses a single content string)
        full_prompt = prompt
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n{prompt}"

        logger.debug(f"Gemini request - model: {model}")

        # Retry loop
        last_error = None
        delay = self.retry_config.initial_delay

        for attempt in range(self.retry_config.max_retries):
            try:
                from google.genai import types

                # Generate content
                response = self.gemini_client.models.generate_content(
                    model=model,
                    contents=full_prompt,
                    config=types.GenerateContentConfig(
                        temperature=temperature,
                        max_output_tokens=max_tokens,
                    )
                )

                # Extract text from response
                text_content = ""
                if hasattr(response, 'text'):
                    text_content = response.text
                elif hasattr(response, 'parts'):
                    for part in response.parts:
                        if hasattr(part, 'text') and part.text:
                            text_content += part.text

                # Get token counts from usage metadata if available
                input_tokens = 0
                output_tokens = 0
                if hasattr(response, 'usage_metadata') and response.usage_metadata:
                    input_tokens = getattr(response.usage_metadata, 'prompt_token_count', 0) or 0
                    output_tokens = getattr(response.usage_metadata, 'candidates_token_count', 0) or 0

                finish_reason = None
                if hasattr(response, 'candidates') and response.candidates:
                    finish_reason = getattr(response.candidates[0], 'finish_reason', None)
                logger.debug(
                    f"Gemini response: model={model}, finish_reason={finish_reason}, "
                    f"output_tokens={output_tokens}, content_len={len(text_content)}"
                )

                return LLMResponse(
                    content=text_content,
                    model=model,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    total_tokens=input_tokens + output_tokens
                )

            except Exception as e:
                last_error = e
                logger.warning(f"Gemini attempt {attempt + 1} failed: {e}")

                if attempt < self.retry_config.max_retries - 1:
                    await asyncio.sleep(delay)
                    delay = min(
                        delay * self.retry_config.exponential_base,
                        self.retry_config.max_delay
                    )

        raise last_error

    async def _call_groq(
        self,
        prompt: str,
        system_prompt: Optional[str],
        model: Optional[str],
        temperature: float,
        max_tokens: int
    ) -> LLMResponse:
        """Call Groq API with retry logic (OpenAI-compatible)"""
        if not self.groq_client:
            raise ValueError("Groq client not initialized")

        model = model or self.DEFAULT_GROQ_MODEL

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        logger.debug(f"Groq request - model: {model}, messages: {len(messages)}")

        # Retry loop
        last_error = None
        delay = self.retry_config.initial_delay

        for attempt in range(self.retry_config.max_retries):
            try:
                response = await self.groq_client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens
                )

                return LLMResponse(
                    content=response.choices[0].message.content,
                    model=model,
                    input_tokens=response.usage.prompt_tokens if response.usage else 0,
                    output_tokens=response.usage.completion_tokens if response.usage else 0,
                    total_tokens=response.usage.total_tokens if response.usage else 0
                )

            except Exception as e:
                last_error = e
                logger.warning(f"Groq attempt {attempt + 1} failed: {e}")

                if attempt < self.retry_config.max_retries - 1:
                    await asyncio.sleep(delay)
                    delay = min(
                        delay * self.retry_config.exponential_base,
                        self.retry_config.max_delay
                    )

        raise last_error

    async def _call_ollama(
        self,
        prompt: str,
        system_prompt: Optional[str],
        model: Optional[str],
        temperature: float,
        max_tokens: int
    ) -> LLMResponse:
        """Call Ollama API with retry logic (OpenAI-compatible)"""
        if not self.ollama_client:
            raise ValueError("Ollama client not initialized")

        # Use model from config, or default, handling both "llama3.2" and "llama3.2:latest"
        if model:
            # If model is "llama3.2" without tag, add ":latest" for Ollama
            if model == "llama3.2" and ":" not in model:
                model = "llama3.2:latest"
        else:
            model = self.DEFAULT_OLLAMA_MODEL

        # Ensure model name is valid
        if not model or not model.strip():
            raise ValueError(f"Invalid Ollama model name: '{model}'")

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        logger.debug(f"Ollama request - model: {model}, base_url: {self.ollama_client.base_url}, messages: {len(messages)}")

        # Retry loop
        last_error = None
        delay = self.retry_config.initial_delay

        for attempt in range(self.retry_config.max_retries):
            try:
                response = await self.ollama_client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens
                )

                return LLMResponse(
                    content=response.choices[0].message.content,
                    model=model,
                    input_tokens=response.usage.prompt_tokens if response.usage else 0,
                    output_tokens=response.usage.completion_tokens if response.usage else 0,
                    total_tokens=response.usage.total_tokens if response.usage else 0
                )

            except Exception as e:
                last_error = e
                error_msg = str(e)
                # Provide more helpful error messages
                if "404" in error_msg:
                    logger.error(
                        f"Ollama 404 error - model '{model}' may not exist or endpoint incorrect. "
                        f"Base URL: {self.ollama_client.base_url}. "
                        f"Check: curl http://localhost:11434/v1/models"
                    )
                else:
                    logger.warning(f"Ollama attempt {attempt + 1} failed: {e}")

                if attempt < self.retry_config.max_retries - 1:
                    await asyncio.sleep(delay)
                    delay = min(
                        delay * self.retry_config.exponential_base,
                        self.retry_config.max_delay
                    )

        raise last_error

    # =========================================================================
    # Streaming Methods for Real-Time Output
    # =========================================================================

    async def _call_ollama_streaming(
        self,
        prompt: str,
        system_prompt: Optional[str],
        model: Optional[str],
        temperature: float,
        max_tokens: int,
        stream_callback: Optional[StreamCallback] = None
    ) -> LLMResponse:
        """
        Call Ollama API with streaming support (OpenAI-compatible).

        Streams tokens in real-time via the callback, while still returning
        the complete LLMResponse at the end for token tracking.
        """
        if not self.ollama_client:
            raise ValueError("Ollama client not initialized")

        # Handle model name
        if model:
            if model == "llama3.2" and ":" not in model:
                model = "llama3.2:latest"
        else:
            model = self.DEFAULT_OLLAMA_MODEL

        if not model or not model.strip():
            raise ValueError(f"Invalid Ollama model name: '{model}'")

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        logger.debug(f"Ollama streaming request - model: {model}, base_url: {self.ollama_client.base_url}")

        last_error = None
        delay = self.retry_config.initial_delay

        for attempt in range(self.retry_config.max_retries):
            try:
                # Enable streaming
                stream = await self.ollama_client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    stream=True  # Enable streaming
                )

                accumulated_content = ""
                input_tokens = 0
                output_tokens = 0

                async for chunk in stream:
                    if chunk.choices and len(chunk.choices) > 0:
                        delta = chunk.choices[0].delta
                        if delta and delta.content:
                            accumulated_content += delta.content

                            # Emit streaming callback
                            if stream_callback:
                                await stream_callback(StreamingChunk(
                                    content=delta.content,
                                    is_final=False,
                                    accumulated_content=accumulated_content
                                ))

                    # Track usage if available in chunk
                    if hasattr(chunk, 'usage') and chunk.usage:
                        input_tokens = chunk.usage.prompt_tokens or 0
                        output_tokens = chunk.usage.completion_tokens or 0

                # Final callback
                if stream_callback:
                    await stream_callback(StreamingChunk(
                        content="",
                        is_final=True,
                        accumulated_content=accumulated_content
                    ))

                return LLMResponse(
                    content=accumulated_content,
                    model=model,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    total_tokens=input_tokens + output_tokens
                )

            except Exception as e:
                last_error = e
                error_msg = str(e)
                if "404" in error_msg:
                    logger.error(f"Ollama streaming 404 error - model '{model}' may not exist")
                else:
                    logger.warning(f"Ollama streaming attempt {attempt + 1} failed: {e}")

                if attempt < self.retry_config.max_retries - 1:
                    await asyncio.sleep(delay)
                    delay = min(
                        delay * self.retry_config.exponential_base,
                        self.retry_config.max_delay
                    )

        raise last_error

    async def _call_gemini_streaming(
        self,
        prompt: str,
        system_prompt: Optional[str],
        model: Optional[str],
        temperature: float,
        max_tokens: int,
        stream_callback: Optional[StreamCallback] = None
    ) -> LLMResponse:
        """
        Call Google Gemini API with streaming support.

        Uses generate_content_stream() for real-time token emission.
        """
        if not self.gemini_client:
            raise ValueError("Gemini client not initialized")

        model = model or self.DEFAULT_GEMINI_MODEL

        full_prompt = prompt
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n{prompt}"

        logger.debug(f"Gemini streaming request - model: {model}")

        last_error = None
        delay = self.retry_config.initial_delay

        for attempt in range(self.retry_config.max_retries):
            try:
                from google.genai import types

                # Use streaming API
                stream = self.gemini_client.models.generate_content_stream(
                    model=model,
                    contents=full_prompt,
                    config=types.GenerateContentConfig(
                        temperature=temperature,
                        max_output_tokens=max_tokens,
                    )
                )

                accumulated_content = ""
                input_tokens = 0
                output_tokens = 0

                for chunk in stream:
                    # Extract text from chunk
                    chunk_text = ""
                    if hasattr(chunk, 'text') and chunk.text:
                        chunk_text = chunk.text
                    elif hasattr(chunk, 'parts'):
                        for part in chunk.parts:
                            if hasattr(part, 'text') and part.text:
                                chunk_text += part.text

                    if chunk_text:
                        accumulated_content += chunk_text

                        # Emit streaming callback
                        if stream_callback:
                            await stream_callback(StreamingChunk(
                                content=chunk_text,
                                is_final=False,
                                accumulated_content=accumulated_content
                            ))

                    # Track usage if available
                    if hasattr(chunk, 'usage_metadata') and chunk.usage_metadata:
                        input_tokens = getattr(chunk.usage_metadata, 'prompt_token_count', 0) or 0
                        output_tokens = getattr(chunk.usage_metadata, 'candidates_token_count', 0) or 0

                # Final callback
                if stream_callback:
                    await stream_callback(StreamingChunk(
                        content="",
                        is_final=True,
                        accumulated_content=accumulated_content
                    ))

                return LLMResponse(
                    content=accumulated_content,
                    model=model,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    total_tokens=input_tokens + output_tokens
                )

            except Exception as e:
                last_error = e
                logger.warning(f"Gemini streaming attempt {attempt + 1} failed: {e}")

                if attempt < self.retry_config.max_retries - 1:
                    await asyncio.sleep(delay)
                    delay = min(
                        delay * self.retry_config.exponential_base,
                        self.retry_config.max_delay
                    )

        raise last_error

    async def _call_groq_streaming(
        self,
        prompt: str,
        system_prompt: Optional[str],
        model: Optional[str],
        temperature: float,
        max_tokens: int,
        stream_callback: Optional[StreamCallback] = None
    ) -> LLMResponse:
        """
        Call Groq API with streaming support (OpenAI-compatible).
        """
        if not self.groq_client:
            raise ValueError("Groq client not initialized")

        model = model or self.DEFAULT_GROQ_MODEL

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        logger.debug(f"Groq streaming request - model: {model}")

        last_error = None
        delay = self.retry_config.initial_delay

        for attempt in range(self.retry_config.max_retries):
            try:
                stream = await self.groq_client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    stream=True
                )

                accumulated_content = ""
                input_tokens = 0
                output_tokens = 0

                async for chunk in stream:
                    if chunk.choices and len(chunk.choices) > 0:
                        delta = chunk.choices[0].delta
                        if delta and delta.content:
                            accumulated_content += delta.content

                            if stream_callback:
                                await stream_callback(StreamingChunk(
                                    content=delta.content,
                                    is_final=False,
                                    accumulated_content=accumulated_content
                                ))

                    if hasattr(chunk, 'usage') and chunk.usage:
                        input_tokens = chunk.usage.prompt_tokens or 0
                        output_tokens = chunk.usage.completion_tokens or 0

                if stream_callback:
                    await stream_callback(StreamingChunk(
                        content="",
                        is_final=True,
                        accumulated_content=accumulated_content
                    ))

                return LLMResponse(
                    content=accumulated_content,
                    model=model,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    total_tokens=input_tokens + output_tokens
                )

            except Exception as e:
                last_error = e
                logger.warning(f"Groq streaming attempt {attempt + 1} failed: {e}")

                if attempt < self.retry_config.max_retries - 1:
                    await asyncio.sleep(delay)
                    delay = min(
                        delay * self.retry_config.exponential_base,
                        self.retry_config.max_delay
                    )

        raise last_error


# Singleton instance
_llm_service: Optional[LLMService] = None


def get_llm_service() -> LLMService:
    """Get or create the singleton LLM service instance"""
    global _llm_service
    # Always check environment on each call to ensure we pick up changes
    # This allows the service to work even if .env is loaded after module import
    prefer_ollama = os.getenv("USE_OLLAMA", "").lower() == "true"
    
    # Recreate if USE_OLLAMA changed or if not initialized
    if _llm_service is None or (_llm_service.prefer_ollama != prefer_ollama):
        _llm_service = LLMService(prefer_ollama=prefer_ollama)
    return _llm_service
