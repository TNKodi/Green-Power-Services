"""
Quick startup script for the ThingsBoard Power Forecast API.
Run this to start the API server.
"""
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def main():
    """Start the API server."""
    print("="*60)
    print("ThingsBoard Power Forecast API")
    print("="*60)
    
    # Check if .env file exists
    env_file = project_root / ".env"
    if not env_file.exists():
        print("\n⚠️  WARNING: .env file not found!")
        print("Please create a .env file from .env.template")
        print("Example:")
        print("  cp .env.template .env")
        print("\nThen edit .env with your ThingsBoard credentials.")
        print("="*60)
        return
    
    print("\n✓ Configuration file found")
    print("✓ Starting API server...")
    print("\nAPI will be available at:")
    print("  - Swagger UI: http://localhost:8000/docs")
    print("  - ReDoc: http://localhost:8000/redoc")
    print("  - Health Check: http://localhost:8000/health")
    print("\nPress Ctrl+C to stop the server")
    print("="*60)
    print()
    
    # Start uvicorn
    import uvicorn

    reload_dirs = [
        str(project_root / "app"),
        str(project_root / "Scripts" / "power_predicition"),
    ]
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        reload_dirs=reload_dirs,
        reload_excludes=[".venv/*", "venv/*", "__pycache__/*", "logs/*", "*.log"],
        log_level="info"
    )


if __name__ == "__main__":
    main()
