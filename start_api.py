"""Script to start the FastAPI server."""

import uvicorn
import sys

if __name__ == "__main__":
    print("=" * 70)
    print("Starting Financial Transaction API")
    print("=" * 70)
    print("\nAPI will be available at:")
    print("  - http://localhost:8000")
    print("  - API Docs: http://localhost:8000/docs")
    print("  - ReDoc: http://localhost:8000/redoc")
    print("\nPress CTRL+C to stop")
    print("=" * 70)
    print()

    # Start server
    try:
        uvicorn.run(
            "api.main:app",
            host="0.0.0.0",
            port=8000,
            reload=True,  # Auto-reload on code changes
            log_level="info",
        )
    except KeyboardInterrupt:
        print("\n\nShutting down API server...")
        sys.exit(0)
