"""Tests for the logging system."""

import pytest
import os
import json
from datetime import datetime
from src.utils.logger import BackendLogger

# Mark all tests in this module as unit tests
pytestmark = pytest.mark.unit


class TestBackendLogger:
    """Test the BackendLogger utility."""
    
    def test_logger_initialization(self):
        """Test that logger initializes correctly."""
        logger = BackendLogger()
        assert logger.logs_dir == "logs"
        assert logger.environment in ["development", "production"]
        assert os.path.exists(logger.logs_dir)
    
    def test_log_levels(self):
        """Test all log levels work correctly."""
        logger = BackendLogger()
        
        # Test each log level
        logger.debug("test", "Debug message", context={"test": True})
        logger.info("test", "Info message", context={"test": True})
        logger.warn("test", "Warning message", context={"test": True})
        logger.error("test", "Error message", context={"test": True})
        
        # Verify files were created
        assert os.path.exists(os.path.join(logger.logs_dir, "backend.log"))
        assert os.path.exists(os.path.join(logger.logs_dir, "combined.log"))
        assert os.path.exists(os.path.join(logger.logs_dir, "errors.log"))
    
    def test_error_log_separation(self):
        """Test that errors and warnings are written to error log."""
        logger = BackendLogger()
        
        # Log different levels
        logger.info("test", "Info message")
        logger.warn("test", "Warning message")
        logger.error("test", "Error message")
        
        # Check that error log contains warnings and errors
        error_log_path = os.path.join(logger.logs_dir, "errors.log")
        with open(error_log_path, "r", encoding="utf-8") as f:
            error_log_content = f.read()
        
        assert "WARN" in error_log_content
        assert "ERROR" in error_log_content
        assert "INFO" not in error_log_content
    
    def test_log_format(self):
        """Test that logs are written in correct JSON format."""
        logger = BackendLogger()
        
        test_message = "Test log message"
        test_user_id = "test_user_123"
        test_context = {"key": "value", "number": 42}
        
        logger.info("test", test_message, user_id=test_user_id, context=test_context)
        
        # Read the log file
        log_file_path = os.path.join(logger.logs_dir, "backend.log")
        with open(log_file_path, "r", encoding="utf-8") as f:
            log_lines = f.readlines()
        
        # Find our test log entry
        test_log_line = None
        for line in log_lines:
            if test_message in line:
                test_log_line = line
                break
        
        assert test_log_line is not None
        
        # Parse JSON
        log_entry = json.loads(test_log_line.strip())
        
        # Verify structure
        assert log_entry["level"] == "INFO"
        assert log_entry["source"] == "backend"
        assert log_entry["category"] == "test"
        assert log_entry["message"] == test_message
        assert log_entry["user_id"] == test_user_id
        assert log_entry["context"] == test_context
        assert "timestamp" in log_entry
        assert log_entry["environment"] in ["development", "production"]
    
    def test_error_logging_with_exception(self):
        """Test logging with exception details."""
        logger = BackendLogger()
        
        try:
            raise ValueError("Test exception")
        except ValueError as e:
            logger.error("test", "Test error with exception", error=e)
        
        # Check that error log contains exception details
        error_log_path = os.path.join(logger.logs_dir, "errors.log")
        with open(error_log_path, "r", encoding="utf-8") as f:
            error_log_lines = f.readlines()
        
        # Find our specific test log entry
        test_log_line = None
        for line in error_log_lines:
            if "Test error with exception" in line:
                test_log_line = line
                break
        
        assert test_log_line is not None
        assert "Test exception" in test_log_line


class TestLoggingMiddleware:
    """Test the logging middleware (basic functionality)."""
    
    def test_middleware_import(self):
        """Test that middleware can be imported."""
        from src.middleware.logging_middleware import LoggingMiddleware
        assert LoggingMiddleware is not None
    
    def test_middleware_initialization(self):
        """Test middleware initialization."""
        from src.middleware.logging_middleware import LoggingMiddleware
        from fastapi import FastAPI
        
        app = FastAPI()
        middleware = LoggingMiddleware(app, log_requests=True, log_responses=True)
        
        assert middleware.log_requests is True
        assert middleware.log_responses is True


class TestLoggingAPI:
    """Test the logging API endpoints."""
    
    def test_logs_api_import(self):
        """Test that logging API can be imported."""
        from api.logs import router
        assert router is not None
    
    def test_log_entry_model(self):
        """Test LogEntry model validation."""
        from api.logs import LogEntry
        
        # Valid log entry
        log_entry = LogEntry(
            timestamp="2025-01-15T10:30:00.000Z",
            level="INFO",
            source="frontend",
            category="test",
            message="Test message",
            user_id="test_user",
            email="test@example.com",
            context={"key": "value"},
            environment="development"
        )
        
        assert log_entry.level == "INFO"
        assert log_entry.source == "frontend"
        assert log_entry.category == "test"
        assert log_entry.message == "Test message"
        assert log_entry.user_id == "test_user"
    
    def test_log_batch_model(self):
        """Test LogBatch model validation."""
        from api.logs import LogBatch, LogEntry
        
        log_entry = LogEntry(
            timestamp="2025-01-15T10:30:00.000Z",
            level="INFO",
            source="frontend",
            category="test",
            message="Test message"
        )
        
        batch = LogBatch(logs=[log_entry])
        assert len(batch.logs) == 1
        assert batch.logs[0].message == "Test message"
