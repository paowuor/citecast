#!/usr/bin/env python
"""
Run the CiteCast web server.
"""

import sys
import os
import uvicorn
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.utils.config import Config
from app.utils.logging import get_logger

logger = get_logger(__name__)

def main():
    """Run the FastAPI server."""
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    
    logger.info(f"Starting CiteCast server on {host}:{port}")
    logger.info(f"Visit http://localhost:{port} to use the app")
    
    uvicorn.run(
        "app.web.main:app",
        host=host,
        port=port,
        reload=True,
        log_level="info"
    )

if __name__ == "__main__":
    main()