"""Script to start the FastAPI server."""

import uvicorn
import sys
import os
import argparse
from pathlib import Path

def get_available_environments():
    """Get list of available environment configuration files."""
    env_files = []
    
    # Check for config.*.env files
    for file in Path(".").glob("config.*.env"):
        env_name = file.stem.replace("config.", "")
        env_files.append(env_name)
    
    # Also check for standard .env files
    if Path(".env").exists():
        env_files.append("default")
    if Path(".env.local").exists():
        env_files.append("local")
    if Path(".env.production").exists():
        env_files.append("production")
    
    return sorted(set(env_files))

def get_env_file_path(env_name):
    """Get the path to the environment file based on name."""
    if env_name == "default":
        return ".env"
    
    # Try config.{env_name}.env format first
    config_file = f"config.{env_name}.env"
    if Path(config_file).exists():
        return config_file
    
    # Try .env.{env_name} format
    dotenv_file = f".env.{env_name}"
    if Path(dotenv_file).exists():
        return dotenv_file
    
    raise FileNotFoundError(f"Environment file not found for '{env_name}'")

if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="Start the Financial Transaction API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python start_api.py --env local        # Use config.local.env
  python start_api.py --env production   # Use config.production.env
  python start_api.py                    # Use .env (default)
        """
    )
    
    available_envs = get_available_environments()
    parser.add_argument(
        "--env",
        type=str,
        default="local",
        choices=available_envs if available_envs else ["local"],
        help=f"Environment to use. Available: {', '.join(available_envs) if available_envs else 'none found'}"
    )
    
    parser.add_argument(
        "--host",
        type=str,
        default="0.0.0.0",
        help="Host to bind to (default: 0.0.0.0)"
    )
    
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to bind to (default: 8000)"
    )
    
    parser.add_argument(
        "--no-reload",
        action="store_true",
        help="Disable auto-reload on code changes"
    )
    
    args = parser.parse_args()
    
    # Set the environment file
    try:
        env_file = get_env_file_path(args.env)
        os.environ["ENV_FILE"] = env_file
        
        print("=" * 70)
        print("Starting Financial Transaction API")
        print("=" * 70)
        print(f"\n🌍 Environment: {args.env}")
        print(f"📄 Config file: {env_file}")
        print(f"\nAPI will be available at:")
        print(f"  - http://localhost:{args.port}")
        print(f"  - API Docs: http://localhost:{args.port}/docs")
        print(f"  - ReDoc: http://localhost:{args.port}/redoc")
        print("\nPress CTRL+C to stop")
        print("=" * 70)
        print()

        # Start server
        try:
            uvicorn.run(
                "api.main:app",
                host=args.host,
                port=args.port,
                reload=not args.no_reload,  # Auto-reload on code changes
                log_level="info",
            )
        except KeyboardInterrupt:
            print("\n\nShutting down API server...")
            sys.exit(0)
            
    except FileNotFoundError as e:
        print(f"❌ Error: {e}")
        print(f"\n💡 Available environments: {', '.join(available_envs) if available_envs else 'none found'}")
        print("\n📝 Create a config file:")
        print(f"   - config.local.env for local development")
        print(f"   - config.production.env for production")
        sys.exit(1)
