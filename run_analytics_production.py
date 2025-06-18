#!/usr/bin/env python3
"""
Production runner for analytics service
"""
import os
import sys
import uvicorn
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)

logger = logging.getLogger(__name__)

def main():
    """Main entry point for analytics service"""
    try:
        logger.info("Starting analytics service...")
        
        # Check database configuration
        database_url = os.getenv("DATABASE_URL")
        if database_url:
            logger.info(f"Using DATABASE_URL from environment (masked): {database_url[:20]}...")
        else:
            logger.info("DATABASE_URL not found, will use individual components")
        
        # Get port from environment or use default
        port = int(os.getenv("PORT", 8000))
        host = "0.0.0.0"
        
        logger.info(f"Starting server on {host}:{port}")
        
        # Import and run the FastAPI app
        uvicorn.run(
            "src.analytics.routers:app",
            host=host,
            port=port,
            log_level="info",
            access_log=True
        )
        
    except Exception as e:
        logger.error(f"Failed to start analytics service: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 