"""Error tracking and monitoring"""
from typing import Dict, Any, List
from collections import defaultdict
from datetime import datetime
from app.utils.logger import setup_logger

logger = setup_logger("error_tracker")

class ErrorTracker:
    """Track errors by type and frequency"""
    
    def __init__(self):
        self.error_counts = defaultdict(int)
        self.error_history: List[Dict[str, Any]] = []
        self.critical_errors: List[Dict[str, Any]] = []
        self.max_history = 1000
    
    def record_error(
        self,
        error_type: str,
        error_message: str,
        context: Dict[str, Any] = None,
        is_critical: bool = False
    ):
        """Record an error"""
        self.error_counts[error_type] += 1
        
        error_record = {
            "type": error_type,
            "message": error_message,
            "context": context or {},
            "timestamp": datetime.utcnow().isoformat(),
            "is_critical": is_critical
        }
        
        self.error_history.append(error_record)
        
        # Keep only recent history
        if len(self.error_history) > self.max_history:
            self.error_history = self.error_history[-self.max_history:]
        
        if is_critical:
            self.critical_errors.append(error_record)
            logger.critical(f"Critical error recorded: {error_type} - {error_message}")
            # In production, could send alert here
        else:
            logger.error(f"Error recorded: {error_type} - {error_message}")
    
    def get_error_stats(self) -> Dict[str, Any]:
        """Get error statistics"""
        return {
            "total_errors": sum(self.error_counts.values()),
            "error_counts": dict(self.error_counts),
            "critical_errors_count": len(self.critical_errors),
            "recent_errors": self.error_history[-10:] if self.error_history else []
        }
    
    def get_errors_by_type(self, error_type: str) -> List[Dict[str, Any]]:
        """Get all errors of a specific type"""
        return [
            error for error in self.error_history
            if error["type"] == error_type
        ]
    
    def clear_history(self):
        """Clear error history (for testing)"""
        self.error_counts.clear()
        self.error_history.clear()
        self.critical_errors.clear()

# Global error tracker instance
error_tracker = ErrorTracker()


