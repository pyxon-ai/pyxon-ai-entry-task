"""Initialize database and create tables."""

import sys
from pathlib import Path
import logging

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config.settings import settings
from src.database.connection import db_manager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Initialize database."""
    logger.info("Initializing database...")
    
    try:
        # Initialize database manager
        db_manager.init_db()
        logger.info("Database engine initialized")
        
        # Create tables
        logger.info("Creating tables...")
        db_manager.create_tables()
        logger.info("Tables created successfully")
        
        # Initialize pgvector extension
        logger.info("Initializing pgvector extension...")
        try:
            import asyncio
            asyncio.run(db_manager.init_pgvector())
            logger.info("pgvector extension initialized")
        except Exception as e:
            logger.warning(f"Could not initialize pgvector extension: {e}")
            logger.warning("Continuing without pgvector (vector search will use fallback)")
        
        logger.info("Database initialized successfully!")
        logger.info(f"Database URL: {settings.database_url}")
        
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
