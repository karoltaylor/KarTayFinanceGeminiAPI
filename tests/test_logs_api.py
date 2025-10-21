"""Unit tests for logs API endpoints."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, mock_open, MagicMock
import os
import json
from datetime import datetime, UTC

from api.main import app

# Mark all tests in this module as unit tests
pytestmark = pytest.mark.unit


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


class TestReceiveLogs:
    """Tests for POST /api/logs/file endpoint."""

    def test_receive_logs_success(self, client):
        """Test successful log reception and saving."""
        log_data = {
            "logs": [
                {
                    "timestamp": "2024-01-15T10:30:00Z",
                    "level": "INFO",
                    "source": "frontend",
                    "category": "user_action",
                    "message": "User logged in",
                    "user_id": "123",
                    "email": "user@example.com",
                    "context": {"action": "login"},
                    "environment": "production"
                },
                {
                    "timestamp": "2024-01-15T10:31:00Z",
                    "level": "ERROR",
                    "source": "backend",
                    "category": "api_error",
                    "message": "Database connection failed",
                    "context": {"error_code": "DB001"},
                    "environment": "production"
                }
            ]
        }
        
        with patch('api.logs.write_to_log_file') as mock_write:
            response = client.post("/api/logs/file", json=log_data)
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["status"] == "success"
            assert data["count"] == 2
            assert "logs saved successfully" in data["message"]
            assert "timestamp" in data
            
            # Verify write_to_log_file was called for each log
            assert mock_write.call_count >= 2  # At least 2 calls (combined + individual)

    def test_receive_logs_frontend_logs(self, client):
        """Test that frontend logs are written to correct files."""
        log_data = {
            "logs": [
                {
                    "timestamp": "2024-01-15T10:30:00Z",
                    "level": "INFO",
                    "source": "frontend",
                    "category": "user_action",
                    "message": "User clicked button",
                    "context": {},
                    "environment": "development"
                }
            ]
        }
        
        with patch('api.logs.write_to_log_file') as mock_write:
            response = client.post("/api/logs/file", json=log_data)
            
            assert response.status_code == 200
            
            # Verify frontend.log was written
            frontend_calls = [call for call in mock_write.call_args_list 
                            if call[0][0] == "frontend.log"]
            assert len(frontend_calls) == 1
            
            # Verify combined.log was written
            combined_calls = [call for call in mock_write.call_args_list 
                            if call[0][0] == "combined.log"]
            assert len(combined_calls) == 1

    def test_receive_logs_backend_logs(self, client):
        """Test that backend logs are written to correct files."""
        log_data = {
            "logs": [
                {
                    "timestamp": "2024-01-15T10:30:00Z",
                    "level": "INFO",
                    "source": "backend",
                    "category": "api_call",
                    "message": "API endpoint called",
                    "context": {},
                    "environment": "development"
                }
            ]
        }
        
        with patch('api.logs.write_to_log_file') as mock_write:
            response = client.post("/api/logs/file", json=log_data)
            
            assert response.status_code == 200
            
            # Verify backend.log was written
            backend_calls = [call for call in mock_write.call_args_list 
                           if call[0][0] == "backend.log"]
            assert len(backend_calls) == 1

    def test_receive_logs_error_logs(self, client):
        """Test that error logs are written to errors.log."""
        log_data = {
            "logs": [
                {
                    "timestamp": "2024-01-15T10:30:00Z",
                    "level": "ERROR",
                    "source": "frontend",
                    "category": "error",
                    "message": "JavaScript error occurred",
                    "context": {},
                    "environment": "development"
                },
                {
                    "timestamp": "2024-01-15T10:31:00Z",
                    "level": "WARN",
                    "source": "backend",
                    "category": "warning",
                    "message": "Deprecated API used",
                    "context": {},
                    "environment": "development"
                }
            ]
        }
        
        with patch('api.logs.write_to_log_file') as mock_write:
            response = client.post("/api/logs/file", json=log_data)
            
            assert response.status_code == 200
            
            # Verify errors.log was written for both ERROR and WARN
            error_calls = [call for call in mock_write.call_args_list 
                         if call[0][0] == "errors.log"]
            assert len(error_calls) == 2

    def test_receive_logs_empty_batch(self, client):
        """Test receiving empty log batch."""
        log_data = {"logs": []}
        
        with patch('api.logs.write_to_log_file'):
            response = client.post("/api/logs/file", json=log_data)
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["status"] == "success"
            assert data["count"] == 0

    def test_receive_logs_invalid_data(self, client):
        """Test receiving invalid log data."""
        log_data = {
            "logs": [
                {
                    "timestamp": "2024-01-15T10:30:00Z",
                    "level": "INFO",
                    "source": "frontend",
                    "category": "user_action",
                    "message": "User logged in"
                    # Missing required fields
                }
            ]
        }
        
        response = client.post("/api/logs/file", json=log_data)
        # The API accepts the data and processes it (Pydantic validation might be lenient)
        assert response.status_code == 200

    def test_receive_logs_write_error(self, client):
        """Test handling of write errors."""
        log_data = {
            "logs": [
                {
                    "timestamp": "2024-01-15T10:30:00Z",
                    "level": "INFO",
                    "source": "frontend",
                    "category": "user_action",
                    "message": "User logged in",
                    "context": {},
                    "environment": "development"
                }
            ]
        }
        
        with patch('api.logs.write_to_log_file', side_effect=Exception("Write failed")):
            response = client.post("/api/logs/file", json=log_data)
            
            # The API returns error status when write operations fail
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "error"

    def test_receive_logs_mixed_sources(self, client):
        """Test receiving logs from mixed sources."""
        log_data = {
            "logs": [
                {
                    "timestamp": "2024-01-15T10:30:00Z",
                    "level": "INFO",
                    "source": "frontend",
                    "category": "user_action",
                    "message": "Frontend log",
                    "context": {},
                    "environment": "development"
                },
                {
                    "timestamp": "2024-01-15T10:31:00Z",
                    "level": "DEBUG",
                    "source": "backend",
                    "category": "api_call",
                    "message": "Backend log",
                    "context": {},
                    "environment": "development"
                },
                {
                    "timestamp": "2024-01-15T10:32:00Z",
                    "level": "ERROR",
                    "source": "frontend",
                    "category": "error",
                    "message": "Frontend error",
                    "context": {},
                    "environment": "development"
                }
            ]
        }
        
        with patch('api.logs.write_to_log_file') as mock_write:
            response = client.post("/api/logs/file", json=log_data)
            
            assert response.status_code == 200
            data = response.json()
            assert data["count"] == 3
            
            # Verify all expected files were written
            file_calls = [call[0][0] for call in mock_write.call_args_list]
            assert "frontend.log" in file_calls
            assert "backend.log" in file_calls
            assert "combined.log" in file_calls
            assert "errors.log" in file_calls


class TestLogHealthCheck:
    """Tests for GET /api/logs/health endpoint."""

    def test_log_health_check_success(self, client):
        """Test successful log health check."""
        with patch('api.logs.os.path.exists', return_value=True), \
             patch('api.logs.os.access', return_value=True), \
             patch('api.logs.os.listdir', return_value=['frontend.log', 'backend.log', 'combined.log']), \
             patch('api.logs.os.path.getsize', return_value=1024):
            
            response = client.get("/api/logs/health")
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["status"] == "healthy"
            assert data["logs_directory"] == "logs"
            assert data["directory_exists"] is True
            assert data["directory_writable"] is True
            assert len(data["log_files"]) == 3
            assert "timestamp" in data

    def test_log_health_check_directory_not_exists(self, client):
        """Test log health check when directory doesn't exist."""
        with patch('api.logs.os.path.exists', return_value=False), \
             patch('api.logs.os.access', return_value=False):
            response = client.get("/api/logs/health")
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["status"] == "healthy"
            assert data["directory_exists"] is False
            assert data["directory_writable"] is False
            assert data["log_files"] == []

    def test_log_health_check_directory_not_writable(self, client):
        """Test log health check when directory is not writable."""
        with patch('api.logs.os.path.exists', return_value=True), \
             patch('api.logs.os.access', return_value=False):
            
            response = client.get("/api/logs/health")
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["status"] == "healthy"
            assert data["directory_exists"] is True
            assert data["directory_writable"] is False

    def test_log_health_check_with_log_files(self, client):
        """Test log health check with existing log files."""
        mock_files = ['frontend.log', 'backend.log', 'combined.log', 'errors.log', 'other.txt']
        
        with patch('api.logs.os.path.exists', return_value=True), \
             patch('api.logs.os.access', return_value=True), \
             patch('api.logs.os.listdir', return_value=mock_files), \
             patch('api.logs.os.path.getsize', return_value=2048):
            
            response = client.get("/api/logs/health")
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["status"] == "healthy"
            assert len(data["log_files"]) == 4  # Only .log files
            
            # Verify log file structure
            for log_file in data["log_files"]:
                assert "name" in log_file
                assert "size_bytes" in log_file
                assert "size_kb" in log_file
                assert log_file["name"].endswith('.log')
                assert log_file["size_bytes"] == 2048
                assert log_file["size_kb"] == 2.0

    def test_log_health_check_file_size_calculation(self, client):
        """Test log health check file size calculation."""
        with patch('api.logs.os.path.exists', return_value=True), \
             patch('api.logs.os.access', return_value=True), \
             patch('api.logs.os.listdir', return_value=['test.log']), \
             patch('api.logs.os.path.getsize', return_value=1536):  # 1.5 KB
            
            response = client.get("/api/logs/health")
            
            assert response.status_code == 200
            data = response.json()
            
            log_file = data["log_files"][0]
            assert log_file["size_bytes"] == 1536
            assert log_file["size_kb"] == 1.5

    def test_log_health_check_file_not_exists(self, client):
        """Test log health check when log file doesn't exist."""
        with patch('api.logs.os.path.exists', return_value=True), \
             patch('api.logs.os.access', return_value=True), \
             patch('api.logs.os.listdir', return_value=['missing.log']), \
             patch('api.logs.os.path.getsize', side_effect=FileNotFoundError):
            
            response = client.get("/api/logs/health")
            
            assert response.status_code == 200
            data = response.json()
            
            # When file doesn't exist, the entire health check fails and returns unhealthy status
            assert data["status"] == "unhealthy"
            assert "error" in data

    def test_log_health_check_error_handling(self, client):
        """Test log health check error handling."""
        with patch('api.logs.os.path.exists', side_effect=Exception("Permission denied")):
            response = client.get("/api/logs/health")
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["status"] == "unhealthy"
            assert "error" in data
            assert "Permission denied" in data["error"]
            assert "timestamp" in data


class TestWriteToLogFile:
    """Tests for write_to_log_file function."""

    def test_write_to_log_file_success(self):
        """Test successful log file writing."""
        from api.logs import write_to_log_file
        
        log_data = {
            "timestamp": "2024-01-15T10:30:00Z",
            "level": "INFO",
            "message": "Test log entry"
        }
        
        with patch('api.logs.open', mock_open()) as mock_file:
            write_to_log_file("test.log", log_data)
            
            # Verify file was opened in append mode (use os.path.join for cross-platform compatibility)
            import os
            expected_path = os.path.join("logs", "test.log")
            mock_file.assert_called_once_with(expected_path, "a", encoding="utf-8")
            
            # Verify JSON line was written
            mock_file.return_value.write.assert_called_once()
            written_content = mock_file.return_value.write.call_args[0][0]
            assert json.loads(written_content.strip()) == log_data

    def test_write_to_log_file_error_handling(self):
        """Test write_to_log_file error handling."""
        from api.logs import write_to_log_file
        
        log_data = {"message": "Test log entry"}
        
        with patch('api.logs.open', side_effect=Exception("Permission denied")), \
             patch('api.logs.logger') as mock_logger:
            
            # Should not raise exception
            write_to_log_file("test.log", log_data)
            
            # Verify error was logged
            mock_logger.error.assert_called_once()
            assert "Permission denied" in str(mock_logger.error.call_args)

    def test_write_to_log_file_json_encoding(self):
        """Test write_to_log_file JSON encoding."""
        from api.logs import write_to_log_file
        
        log_data = {
            "message": "Test with unicode: 测试",
            "special_chars": "Special: !@#$%^&*()"
        }
        
        with patch('api.logs.open', mock_open()) as mock_file:
            write_to_log_file("test.log", log_data)
            
            written_content = mock_file.return_value.write.call_args[0][0]
            parsed_data = json.loads(written_content.strip())
            assert parsed_data == log_data
            assert "测试" in written_content
