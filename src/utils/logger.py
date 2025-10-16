"""Backend logger utility for centralized file-based logging."""

from datetime import datetime, timezone
import os
import json
import logging
from typing import Dict, Any, Optional

# Configure Python logging
logging.basicConfig(level=logging.INFO)
python_logger = logging.getLogger(__name__)


class BackendLogger:
    """Backend logger for writing structured logs to files."""
    
    def __init__(self):
        """Initialize the backend logger."""
        self.logs_dir = "logs"
        os.makedirs(self.logs_dir, exist_ok=True)
        self.environment = os.getenv("ENVIRONMENT", "development")
    
    def _log(self, level: str, category: str, message: str, 
             user_id: Optional[str] = None, context: Optional[Dict[str, Any]] = None, 
             error: Optional[Exception] = None) -> None:
        """Internal logging method."""
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": level,
            "source": "backend",
            "category": category,
            "message": message,
            "user_id": user_id,
            "email": None,
            "context": context or {},
            "environment": self.environment,
            "error_stack": str(error) if error else None
        }
        
        try:
            # Write to backend log
            self._write_to_file("backend.log", log_entry)
            
            # Write to combined log
            self._write_to_file("combined.log", log_entry)
            
            # Write errors and warnings to error log
            if level in ["ERROR", "WARN"]:
                self._write_to_file("errors.log", log_entry)
                
        except Exception as e:
            # Don't break the app if logging fails
            python_logger.error(f"Error logging to file: {str(e)}")
        
        # Also log to console with Python logging
        log_message = f"[{category}] {message}"
        if user_id:
            log_message = f"[{user_id}] {log_message}"
        if error:
            log_message = f"{log_message} - Error: {str(error)}"
            
        if level == "DEBUG":
            python_logger.debug(log_message)
        elif level == "INFO":
            python_logger.info(log_message)
        elif level == "WARN":
            python_logger.warning(log_message)
        elif level == "ERROR":
            python_logger.error(log_message)
    
    def _write_to_file(self, filename: str, log_data: Dict[str, Any]) -> None:
        """Write log entry to file in JSON lines format."""
        try:
            filepath = os.path.join(self.logs_dir, filename)
            json_line = json.dumps(log_data, ensure_ascii=False) + "\n"
            
            with open(filepath, "a", encoding="utf-8") as f:
                f.write(json_line)
                
        except Exception as e:
            python_logger.error(f"Error writing to log file {filename}: {str(e)}")
    
    def debug(self, category: str, message: str, user_id: Optional[str] = None, 
              context: Optional[Dict[str, Any]] = None) -> None:
        """Log debug message."""
        self._log("DEBUG", category, message, user_id, context)
    
    def info(self, category: str, message: str, user_id: Optional[str] = None, 
             context: Optional[Dict[str, Any]] = None) -> None:
        """Log info message."""
        self._log("INFO", category, message, user_id, context)
    
    def warn(self, category: str, message: str, user_id: Optional[str] = None, 
             context: Optional[Dict[str, Any]] = None) -> None:
        """Log warning message."""
        self._log("WARN", category, message, user_id, context)
    
    def error(self, category: str, message: str, user_id: Optional[str] = None, 
              context: Optional[Dict[str, Any]] = None, error: Optional[Exception] = None) -> None:
        """Log error message."""
        self._log("ERROR", category, message, user_id, context, error)


# Create singleton instance
logger = BackendLogger()
