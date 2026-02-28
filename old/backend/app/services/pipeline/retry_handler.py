"""Retry handler with exponential backoff and circuit breaker"""
import time
import asyncio
from typing import Callable, Any, Optional, Dict
from functools import wraps
from app.utils.logger import setup_logger

logger = setup_logger("retry_handler")

class CircuitBreaker:
    """Circuit breaker pattern for API calls"""
    
    def __init__(self, failure_threshold: int = 5, timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "closed"  # closed, open, half_open
    
    def record_success(self):
        """Record a successful call"""
        self.failure_count = 0
        self.state = "closed"
    
    def record_failure(self):
        """Record a failed call"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "open"
            logger.warning(f"Circuit breaker opened after {self.failure_count} failures")
    
    def can_proceed(self) -> bool:
        """Check if call can proceed"""
        if self.state == "closed":
            return True
        
        if self.state == "open":
            # Check if timeout has passed
            if self.last_failure_time and (time.time() - self.last_failure_time) > self.timeout:
                self.state = "half_open"
                logger.info("Circuit breaker entering half-open state")
                return True
            return False
        
        # half_open state - allow one attempt
        return True

class RetryHandler:
    """Handler for retrying operations with exponential backoff"""
    
    def __init__(
        self,
        max_retries: int = 3,
        initial_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        circuit_breaker: Optional[CircuitBreaker] = None
    ):
        self.max_retries = max_retries
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.circuit_breaker = circuit_breaker or CircuitBreaker()
    
    def calculate_delay(self, attempt: int) -> float:
        """Calculate delay for retry attempt"""
        delay = self.initial_delay * (self.exponential_base ** attempt)
        return min(delay, self.max_delay)
    
    def should_retry(self, exception: Exception, attempt: int) -> bool:
        """Determine if operation should be retried"""
        if attempt >= self.max_retries:
            return False
        
        # Don't retry on certain errors
        error_str = str(exception).lower()
        non_retryable_errors = [
            "authentication",
            "authorization",
            "invalid_api_key",
            "not found",
            "validation error"
        ]
        
        for error_type in non_retryable_errors:
            if error_type in error_str:
                logger.warning(f"Non-retryable error detected: {error_type}")
                return False
        
        return True
    
    async def execute_async(
        self,
        func: Callable,
        *args,
        **kwargs
    ) -> Any:
        """Execute async function with retry logic"""
        if not self.circuit_breaker.can_proceed():
            raise Exception("Circuit breaker is open - too many failures")
        
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                result = await func(*args, **kwargs)
                self.circuit_breaker.record_success()
                if attempt > 0:
                    logger.info(f"Operation succeeded after {attempt} retries")
                return result
            except Exception as e:
                last_exception = e
                self.circuit_breaker.record_failure()
                
                if not self.should_retry(e, attempt):
                    logger.error(f"Operation failed after {attempt + 1} attempts: {e}")
                    raise
                
                delay = self.calculate_delay(attempt)
                logger.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {delay:.2f}s...")
                await asyncio.sleep(delay)
        
        raise last_exception
    
    def execute_sync(
        self,
        func: Callable,
        *args,
        **kwargs
    ) -> Any:
        """Execute sync function with retry logic"""
        if not self.circuit_breaker.can_proceed():
            raise Exception("Circuit breaker is open - too many failures")
        
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                result = func(*args, **kwargs)
                self.circuit_breaker.record_success()
                if attempt > 0:
                    logger.info(f"Operation succeeded after {attempt} retries")
                return result
            except Exception as e:
                last_exception = e
                self.circuit_breaker.record_failure()
                
                if not self.should_retry(e, attempt):
                    logger.error(f"Operation failed after {attempt + 1} attempts: {e}")
                    raise
                
                delay = self.calculate_delay(attempt)
                logger.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {delay:.2f}s...")
                time.sleep(delay)
        
        raise last_exception

def retry_on_failure(max_retries: int = 3, initial_delay: float = 1.0):
    """Decorator for retrying functions on failure"""
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            handler = RetryHandler(max_retries=max_retries, initial_delay=initial_delay)
            return await handler.execute_async(func, *args, **kwargs)
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            handler = RetryHandler(max_retries=max_retries, initial_delay=initial_delay)
            return handler.execute_sync(func, *args, **kwargs)
        
        # Return appropriate wrapper based on function type
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator


