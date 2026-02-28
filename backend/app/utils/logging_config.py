"""
Centralized Logging Configuration for GamED.AI v2

Provides:
- Structured logging with context
- Performance timing decorators
- Error tracking with stack traces
- Pipeline execution tracking
- Configurable log levels and formats
"""

import logging
import sys
import os
import json
import time
import traceback
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, Callable
from functools import wraps
from contextlib import contextmanager
from dataclasses import dataclass, asdict
from enum import Enum


class LogLevel(Enum):
    """Log level enumeration"""
    DEBUG = logging.DEBUG
    INFO = logging.INFO
    WARNING = logging.WARNING
    ERROR = logging.ERROR
    CRITICAL = logging.CRITICAL


@dataclass
class LogContext:
    """Context information for structured logging"""
    agent_name: Optional[str] = None
    stage: Optional[str] = None
    question_id: Optional[str] = None
    template_type: Optional[str] = None
    execution_id: Optional[str] = None
    retry_count: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary, excluding None values"""
        result = {}
        for key, value in asdict(self).items():
            if value is not None:
                result[key] = value
        return result


class StructuredFormatter(logging.Formatter):
    """Formatter that includes context in log messages"""
    
    def format(self, record: logging.LogRecord) -> str:
        # Add context if available
        context_parts = []
        
        if hasattr(record, 'log_context'):
            context = record.log_context
            if isinstance(context, LogContext):
                context_dict = context.to_dict()
                if context_dict:
                    context_parts.append(f"Context: {json.dumps(context_dict, default=str)}")
        
        # Add metadata if available
        if hasattr(record, 'log_metadata'):
            metadata = record.log_metadata
            if metadata:
                context_parts.append(f"Metadata: {json.dumps(metadata, default=str)}")
        
        # Add timing if available
        if hasattr(record, 'duration_ms'):
            context_parts.append(f"Duration: {record.duration_ms}ms")
        
        if context_parts:
            record.msg = f"{record.msg} | {' | '.join(context_parts)}"
        
        return super().format(record)


class PipelineLogger:
    """Enhanced logger with pipeline tracking capabilities"""
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self.name = name
        self._context_stack: list[LogContext] = []
        self._timings: Dict[str, float] = {}
    
    def set_context(self, context: LogContext):
        """Set logging context for subsequent log calls"""
        self._context_stack.append(context)
    
    def clear_context(self):
        """Clear current logging context"""
        if self._context_stack:
            self._context_stack.pop()
    
    @contextmanager
    def context(self, **kwargs):
        """Context manager for temporary logging context"""
        ctx = LogContext(**kwargs)
        self.set_context(ctx)
        try:
            yield
        finally:
            self.clear_context()
    
    def _add_context(self, record: logging.LogRecord, **kwargs):
        """Add context to log record"""
        # Merge current context stack with additional kwargs
        merged_context = {}
        if self._context_stack:
            for ctx in self._context_stack:
                merged_context.update(ctx.to_dict())
        merged_context.update(kwargs)
        
        if merged_context:
            # Only use valid LogContext fields, store rest as metadata
            valid_fields = {k: v for k, v in merged_context.items() if k in LogContext.__annotations__}
            metadata = {k: v for k, v in merged_context.items() if k not in LogContext.__annotations__}
            
            if valid_fields:
                record.log_context = LogContext(**valid_fields)
            if metadata:
                record.log_metadata = metadata
    
    def debug(self, message: str, **context):
        """Log debug message with context"""
        record = self.logger.makeRecord(
            self.logger.name, logging.DEBUG, "", 0, message, (), None
        )
        self._add_context(record, **context)
        self.logger.handle(record)
    
    def info(self, message: str, **context):
        """Log info message with context"""
        record = self.logger.makeRecord(
            self.logger.name, logging.INFO, "", 0, message, (), None
        )
        self._add_context(record, **context)
        self.logger.handle(record)
    
    def warning(self, message: str, **context):
        """Log warning message with context"""
        record = self.logger.makeRecord(
            self.logger.name, logging.WARNING, "", 0, message, (), None
        )
        self._add_context(record, **context)
        self.logger.handle(record)
    
    def error(self, message: str, exc_info=None, **context):
        """Log error message with context and optional exception info"""
        # Handle exc_info properly - it can be True, a tuple, or None
        if exc_info is True:
            import sys
            exc_info = sys.exc_info()
        elif exc_info is False:
            exc_info = None
        
        # Create record without exc_info first
        record = self.logger.makeRecord(
            self.logger.name, logging.ERROR, "", 0, message, (), None
        )
        # Set exc_info on record if provided
        if exc_info:
            record.exc_info = exc_info
        self._add_context(record, **context)
        self.logger.handle(record)
    
    def critical(self, message: str, exc_info=None, **context):
        """Log critical message with context"""
        # Handle exc_info properly - it can be True, a tuple, or None
        if exc_info is True:
            import sys
            exc_info = sys.exc_info()
        elif exc_info is False:
            exc_info = None
        
        # Create record without exc_info first
        record = self.logger.makeRecord(
            self.logger.name, logging.CRITICAL, "", 0, message, (), None
        )
        # Set exc_info on record if provided
        if exc_info:
            record.exc_info = exc_info
        self._add_context(record, **context)
        self.logger.handle(record)
    
    @contextmanager
    def time_operation(self, operation_name: str):
        """Context manager to time an operation"""
        start_time = time.time()
        try:
            yield
        finally:
            duration_ms = (time.time() - start_time) * 1000
            self._timings[operation_name] = duration_ms
            record = self.logger.makeRecord(
                self.logger.name, logging.DEBUG, "", 0,
                f"Operation '{operation_name}' completed",
                (), None
            )
            record.duration_ms = duration_ms
            self.logger.handle(record)
    
    def get_timings(self) -> Dict[str, float]:
        """Get all recorded timings"""
        return self._timings.copy()


def setup_logging(
    level: str = "INFO",
    log_to_file: bool = True,
    log_dir: Optional[Path] = None,
    structured: bool = False,
    include_third_party: bool = False
) -> None:
    """
    Set up centralized logging configuration
    
    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_to_file: Whether to log to file
        log_dir: Directory for log files (default: backend/logs)
        structured: Use structured JSON logging
        include_third_party: Include third-party library logs
    """
    # Parse log level
    log_level = getattr(logging, level.upper(), logging.INFO)
    
    # Get log directory
    if log_dir is None:
        log_dir = Path(__file__).parent.parent.parent / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Create formatter
    if structured:
        formatter = StructuredFormatter(
            '%(asctime)s | %(levelname)-8s | %(name)s | %(funcName)s:%(lineno)d | %(message)s'
        )
    else:
        formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(name)-30s | %(funcName)s:%(lineno)d | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    
    # File handler (if enabled)
    handlers = [console_handler]
    if log_to_file:
        log_file = log_dir / f"gamed_ai_{datetime.now().strftime('%Y%m%d')}.log"
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)  # Always log everything to file
        file_handler.setFormatter(formatter)
        handlers.append(file_handler)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.handlers = handlers  # Replace existing handlers
    
    # Configure application loggers
    app_logger = logging.getLogger("gamed_ai")
    app_logger.setLevel(log_level)
    app_logger.propagate = True
    
    logging.getLogger("app").setLevel(log_level)
    logging.getLogger("app.agents").setLevel(log_level)
    logging.getLogger("app.services").setLevel(log_level)
    
    # Configure third-party loggers
    if include_third_party:
        logging.getLogger("httpx").setLevel(logging.INFO)
        logging.getLogger("httpcore").setLevel(logging.INFO)
    else:
        # Reduce noise from third-party libraries
        logging.getLogger("httpx").setLevel(logging.WARNING)
        logging.getLogger("httpcore").setLevel(logging.WARNING)
        logging.getLogger("openai").setLevel(logging.WARNING)
        logging.getLogger("anthropic").setLevel(logging.WARNING)
        logging.getLogger("urllib3").setLevel(logging.WARNING)
        logging.getLogger("asyncio").setLevel(logging.WARNING)
    
    # Log configuration
    logging.info("=" * 80)
    logging.info("Logging Configuration Initialized")
    logging.info(f"  Level: {level}")
    logging.info(f"  Log to file: {log_to_file}")
    if log_to_file:
        logging.info(f"  Log directory: {log_dir}")
    logging.info(f"  Structured: {structured}")
    logging.info("=" * 80)


def get_logger(name: str) -> PipelineLogger:
    """
    Get a PipelineLogger instance for a module
    
    Usage:
        logger = get_logger(__name__)
        logger.info("Message", agent_name="game_planner", question_id="123")
    """
    return PipelineLogger(name)


def log_agent_execution(agent_name: str):
    """
    Decorator to log agent execution with timing and error handling
    
    Usage:
        @log_agent_execution("game_planner")
        async def game_planner_agent(state: AgentState) -> dict:
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            logger = get_logger(f"gamed_ai.agents.{agent_name}")
            start_time = time.time()
            
            # Extract state for context
            state = args[0] if args else kwargs.get('state')
            context = {}
            if state:
                context.update({
                    "agent_name": agent_name,
                    "question_id": state.get("question_id"),
                    "template_type": state.get("template_selection", {}).get("template_type") if isinstance(state.get("template_selection"), dict) else None,
                })
            
            logger.info(f"Starting {agent_name}", **context)
            
            try:
                result = await func(*args, **kwargs)
                duration_ms = (time.time() - start_time) * 1000
                logger.info(
                    f"Completed {agent_name}",
                    duration_ms=duration_ms,
                    **context
                )
                return result
            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                logger.error(
                    f"Failed {agent_name}: {str(e)}",
                    exc_info=True,
                    duration_ms=duration_ms,
                    **context
                )
                raise
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            logger = get_logger(f"gamed_ai.agents.{agent_name}")
            start_time = time.time()
            
            state = args[0] if args else kwargs.get('state')
            context = {}
            if state:
                context.update({
                    "agent_name": agent_name,
                    "question_id": state.get("question_id"),
                    "template_type": state.get("template_selection", {}).get("template_type") if isinstance(state.get("template_selection"), dict) else None,
                })
            
            logger.info(f"Starting {agent_name}", **context)
            
            try:
                result = func(*args, **kwargs)
                duration_ms = (time.time() - start_time) * 1000
                logger.info(
                    f"Completed {agent_name}",
                    duration_ms=duration_ms,
                    **context
                )
                return result
            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                logger.error(
                    f"Failed {agent_name}: {str(e)}",
                    exc_info=True,
                    duration_ms=duration_ms,
                    **context
                )
                raise
        
        # Return appropriate wrapper based on function type
        import inspect
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator


def log_service_call(service_name: str):
    """
    Decorator to log service calls with timing
    
    Usage:
        @log_service_call("llm_service")
        async def generate(prompt: str):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            logger = get_logger(f"gamed_ai.services.{service_name}")
            start_time = time.time()
            
            # Log call details
            call_info = {
                "service": service_name,
                "function": func.__name__,
            }
            logger.debug(f"Calling {service_name}.{func.__name__}", **call_info)
            
            try:
                result = await func(*args, **kwargs)
                duration_ms = (time.time() - start_time) * 1000
                logger.debug(
                    f"Completed {service_name}.{func.__name__}",
                    duration_ms=duration_ms,
                    **call_info
                )
                return result
            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                logger.error(
                    f"Failed {service_name}.{func.__name__}: {str(e)}",
                    exc_info=True,
                    duration_ms=duration_ms,
                    **call_info
                )
                raise
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            logger = get_logger(f"gamed_ai.services.{service_name}")
            start_time = time.time()
            
            call_info = {
                "service": service_name,
                "function": func.__name__,
            }
            logger.debug(f"Calling {service_name}.{func.__name__}", **call_info)
            
            try:
                result = func(*args, **kwargs)
                duration_ms = (time.time() - start_time) * 1000
                logger.debug(
                    f"Completed {service_name}.{func.__name__}",
                    duration_ms=duration_ms,
                    **call_info
                )
                return result
            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                logger.error(
                    f"Failed {service_name}.{func.__name__}: {str(e)}",
                    exc_info=True,
                    duration_ms=duration_ms,
                    **call_info
                )
                raise
        
        import inspect
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator
