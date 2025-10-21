"""Logging middleware for request/response logging."""

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import time
import json
from typing import Dict, Any

from src.utils.logger import logger


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log all incoming requests and responses."""

    def __init__(self, app, log_requests: bool = True, log_responses: bool = True):
        """Initialize logging middleware."""
        super().__init__(app)
        self.log_requests = log_requests
        self.log_responses = log_responses

    async def dispatch(self, request: Request, call_next):
        """Process request and response with logging."""
        start_time = time.time()

        # Extract user information from headers
        user_id = request.headers.get("X-User-ID")
        auth_header = request.headers.get("Authorization")

        # Log incoming request
        if self.log_requests:
            request_context = {
                "method": request.method,
                "path": str(request.url.path),
                "query_params": dict(request.query_params),
                "client_ip": request.client.host if request.client else "unknown",
                "user_agent": request.headers.get("User-Agent", "unknown"),
                "has_auth_header": bool(auth_header),
                "content_type": request.headers.get("Content-Type", "unknown"),
            }

            # Add request body for certain endpoints (be careful with sensitive data)
            if request.method in ["POST", "PUT", "PATCH"] and self._should_log_body(
                request
            ):
                try:
                    body = await request.body()
                    if body:
                        # Only log body for non-sensitive endpoints
                        if not self._is_sensitive_endpoint(request.url.path):
                            request_context["body_size"] = len(body)
                            # Don't log actual body content for security
                except Exception:
                    request_context["body_error"] = "Could not read request body"

            logger.info(
                "request",
                f"{request.method} {request.url.path}",
                user_id=user_id,
                context=request_context,
            )

        # Process the request
        try:
            response = await call_next(request)
        except Exception as e:
            # Log unhandled exceptions
            logger.error(
                "request_exception",
                f"{request.method} {request.url.path} - Unhandled exception",
                user_id=user_id,
                context={
                    "method": request.method,
                    "path": str(request.url.path),
                    "exception_type": type(e).__name__,
                },
                error=e,
            )
            raise

        # Calculate processing time
        duration = time.time() - start_time

        # Log response
        if self.log_responses:
            response_context = {
                "method": request.method,
                "path": str(request.url.path),
                "status_code": response.status_code,
                "duration_ms": round(duration * 1000, 2),
                "client_ip": request.client.host if request.client else "unknown",
            }

            # Add response headers for errors
            if response.status_code >= 400:
                response_context["response_headers"] = dict(response.headers)

            # Determine log level based on status code
            if response.status_code >= 500:
                logger.error(
                    "response",
                    f"{request.method} {request.url.path} - {response.status_code} (Server Error)",
                    user_id=user_id,
                    context=response_context,
                )
            elif response.status_code >= 400:
                logger.warn(
                    "response",
                    f"{request.method} {request.url.path} - {response.status_code} (Client Error)",
                    user_id=user_id,
                    context=response_context,
                )
            else:
                logger.info(
                    "response",
                    f"{request.method} {request.url.path} - {response.status_code}",
                    user_id=user_id,
                    context=response_context,
                )

        return response

    def _should_log_body(self, request: Request) -> bool:
        """Determine if request body should be logged."""
        # Only log body for certain content types
        content_type = request.headers.get("Content-Type", "")
        return any(
            ct in content_type
            for ct in [
                "application/json",
                "application/x-www-form-urlencoded",
                "multipart/form-data",
            ]
        )

    def _is_sensitive_endpoint(self, path: str) -> bool:
        """Determine if endpoint contains sensitive data."""
        sensitive_paths = [
            "/api/auth/",
            "/api/users/",
            "/api/logs/",
            "/login",
            "/register",
            "/password",
        ]
        return any(sensitive_path in path for sensitive_path in sensitive_paths)
