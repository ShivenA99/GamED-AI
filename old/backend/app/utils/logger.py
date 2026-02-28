import logging
import os
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

# Check if JSON logging is enabled
USE_JSON_LOGGING = os.getenv("JSON_LOGGING", "false").lower() == "true"

# Per-run logging configuration
_RUN_ID = None
_RUN_DIR = None

def initialize_run_logging():
    """Initialize per-run logging directory structure"""
    global _RUN_ID, _RUN_DIR
    
    if _RUN_ID is not None:
        return _RUN_ID, _RUN_DIR
    
    # Generate run ID
    run_timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    run_uuid = str(uuid.uuid4())[:8]
    _RUN_ID = f"{run_timestamp}_{run_uuid}"
    
    # Create run directory structure
    logs_base = Path("logs")
    runs_dir = logs_base / "runs"
    _RUN_DIR = runs_dir / _RUN_ID
    _RUN_DIR.mkdir(parents=True, exist_ok=True)
    
    # Create symlink to current run (for easy access)
    current_run_link = runs_dir / "current"
    if current_run_link.exists():
        try:
            if current_run_link.is_symlink():
                current_run_link.unlink()
            else:
                current_run_link.unlink()
        except OSError:
            pass  # Ignore errors when removing
    
    try:
        current_run_link.symlink_to(_RUN_ID)
    except (OSError, NotImplementedError):
        # On Windows or if symlink fails, create a text file with the run ID
        current_txt = runs_dir / "current.txt"
        with open(current_txt, 'w') as f:
            f.write(_RUN_ID)
    
    # Create run metadata file
    metadata = {
        "run_id": _RUN_ID,
        "start_time": datetime.now().isoformat(),
        "pid": os.getpid(),
    }
    with open(_RUN_DIR / "metadata.json", 'w') as f:
        json.dump(metadata, f, indent=2)
    
    return _RUN_ID, _RUN_DIR

def get_run_id() -> Optional[str]:
    """Get the current run ID"""
    return _RUN_ID

def get_run_dir() -> Optional[Path]:
    """Get the current run directory"""
    return _RUN_DIR

class StructuredFormatter(logging.Formatter):
    """JSON formatter for structured logging"""
    
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add extra context if present
        if hasattr(record, "process_id"):
            log_data["process_id"] = record.process_id
        if hasattr(record, "step_name"):
            log_data["step_name"] = record.step_name
        if hasattr(record, "user_id"):
            log_data["user_id"] = record.user_id
        if hasattr(record, "context"):
            log_data["context"] = record.context
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        return json.dumps(log_data)

def setup_logger(name: str = "ai_learning_platform", use_json: bool = None) -> logging.Logger:
    """Set up a logger with file and console handlers"""
    
    if use_json is None:
        use_json = USE_JSON_LOGGING
    
    # Initialize run logging if not already done
    if _RUN_DIR is None:
        initialize_run_logging()
    
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    
    # Avoid duplicate handlers
    if logger.handlers:
        return logger
    
    # Create formatters
    if use_json:
        file_formatter = StructuredFormatter()
        console_formatter = StructuredFormatter()
    else:
        file_formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(name)s | %(funcName)s:%(lineno)d | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(message)s',
            datefmt='%H:%M:%S'
        )
    
    # File handler - detailed logs in run directory with rotation
    from logging.handlers import RotatingFileHandler
    
    # Use run directory if available, otherwise fallback to logs directory
    if _RUN_DIR:
        log_file = _RUN_DIR / f"{name}.log"
    else:
        logs_dir = Path("logs")
        logs_dir.mkdir(exist_ok=True)
        log_file = logs_dir / f"{name}_{datetime.now().strftime('%Y%m%d')}.log"
    
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(file_formatter)
    
    # Console handler - less verbose
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(console_formatter)
    
    # Add handlers
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    # Log run initialization
    if _RUN_ID:
        logger.info(f"Logging initialized for run: {_RUN_ID}")
    
    return logger

def log_with_context(
    logger: logging.Logger,
    level: int,
    message: str,
    process_id: Optional[str] = None,
    step_name: Optional[str] = None,
    user_id: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None,
    **kwargs
):
    """Log with additional context"""
    extra = {}
    if process_id:
        extra["process_id"] = process_id
    if step_name:
        extra["step_name"] = step_name
    if user_id:
        extra["user_id"] = user_id
    if context:
        extra["context"] = context
    extra.update(kwargs)
    
    logger.log(level, message, extra=extra)

# Create main application logger (will be initialized when first logger is created)
app_logger = None

def get_app_logger():
    """Get or create the main application logger"""
    global app_logger
    if app_logger is None:
        app_logger = setup_logger("ai_learning_platform")
    return app_logger

