"""Run the demo web server."""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config.settings import settings
import uvicorn


def main():
    """Run the demo server."""
    print(f"Starting Pyxon AI Document Parser Demo...")
    print(f"Server running at http://{settings.demo_host}:{settings.demo_port}")
    print(f"Press Ctrl+C to stop")
    
    uvicorn.run(
        "src.api.main:app",
        host=settings.demo_host,
        port=settings.demo_port,
        reload=True,
    )


if __name__ == "__main__":
    main()
