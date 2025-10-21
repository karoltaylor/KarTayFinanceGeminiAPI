"""Logging endpoints for centralized file-based logging."""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime, UTC
import os
import json
import logging

router = APIRouter(prefix="/api/logs", tags=["Logging"])

# Ensure logs directory exists
LOGS_DIR = "logs"
os.makedirs(LOGS_DIR, exist_ok=True)

# Configure logging for this module
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LogEntry(BaseModel):
    """Individual log entry model."""

    timestamp: str
    level: str
    source: str
    category: str
    message: str
    user_id: Optional[str] = None
    email: Optional[str] = None
    context: Dict[str, Any] = {}
    environment: str = "development"
    error_stack: Optional[str] = None


class LogBatch(BaseModel):
    """Batch of log entries from frontend."""

    logs: List[LogEntry]


def write_to_log_file(filename: str, log_data: dict) -> None:
    """Write log entry to file in JSON lines format."""
    try:
        filepath = os.path.join(LOGS_DIR, filename)

        # Convert to JSON line format
        json_line = json.dumps(log_data, ensure_ascii=False) + "\n"

        # Append to file with proper encoding
        with open(filepath, "a", encoding="utf-8") as f:
            f.write(json_line)

    except Exception as e:
        # Don't fail the application if logging fails
        logger.error(f"Error writing to log file {filename}: {str(e)}")


@router.post("/file", summary="Receive batched logs from frontend")
async def receive_logs(batch: LogBatch):
    """
    Receive batched logs from frontend and store in files.

    This endpoint receives logs from the frontend application and writes them
    to various log files for centralized logging and debugging.

    **Request Body:**
    - `logs`: Array of log entries with timestamp, level, source, category, message, etc.

    **Returns:**
    - Status of log saving operation
    - Count of logs successfully saved

    **Log Files Created:**
    - `frontend.log`: All frontend logs
    - `backend.log`: All backend logs
    - `combined.log`: All logs combined
    - `errors.log`: Error and warning logs only
    """
    try:
        saved_count = 0

        for log_entry in batch.logs:
            log_dict = log_entry.dict()

            # Write to individual source files
            if log_dict["source"] == "frontend":
                write_to_log_file("frontend.log", log_dict)
            elif log_dict["source"] == "backend":
                write_to_log_file("backend.log", log_dict)

            # Write to combined log
            write_to_log_file("combined.log", log_dict)

            # Write errors and warnings to error log
            if log_dict["level"] in ["ERROR", "WARN"]:
                write_to_log_file("errors.log", log_dict)

            saved_count += 1

        return {
            "status": "success",
            "message": f"{saved_count} logs saved successfully",
            "count": saved_count,
            "timestamp": datetime.now(UTC).isoformat() + "Z",
        }

    except Exception as e:
        # Don't fail frontend if logging fails
        logger.error(f"Error saving logs: {str(e)}")
        return {
            "status": "error",
            "message": str(e),
            "count": 0,
            "timestamp": datetime.now(UTC).isoformat() + "Z",
        }


@router.get("/health", summary="Check logging system health")
async def log_health_check():
    """
    Check if the logging system is working properly.

    **Returns:**
    - Status of logging directory and files
    - Available log files
    - System health information
    """
    try:
        # Check if logs directory exists and is writable
        logs_dir_exists = os.path.exists(LOGS_DIR)
        logs_dir_writable = os.access(LOGS_DIR, os.W_OK)

        # List available log files
        log_files = []
        if logs_dir_exists:
            for file in os.listdir(LOGS_DIR):
                if file.endswith(".log"):
                    file_path = os.path.join(LOGS_DIR, file)
                    file_size = (
                        os.path.getsize(file_path) if os.path.exists(file_path) else 0
                    )
                    log_files.append(
                        {
                            "name": file,
                            "size_bytes": file_size,
                            "size_kb": round(file_size / 1024, 2),
                        }
                    )

        return {
            "status": "healthy",
            "logs_directory": LOGS_DIR,
            "directory_exists": logs_dir_exists,
            "directory_writable": logs_dir_writable,
            "log_files": log_files,
            "timestamp": datetime.now(UTC).isoformat() + "Z",
        }

    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now(UTC).isoformat() + "Z",
        }
