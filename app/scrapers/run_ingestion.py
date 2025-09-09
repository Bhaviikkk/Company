import asyncio
import argparse
import logging
import os
import sys

# Add project root to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.ingestion_service import IngestionService
from app.core.logging import setup_logging

# Setup basic logging for the script
setup_logging()
logger = logging.getLogger("ingestion_script")

async def main():
    """Main function to run the ingestion process."""
    parser = argparse.ArgumentParser(description="Run data ingestion for the Legal-AI backend.")
    parser.add_argument(
        "--source",
        type=str,
        choices=["nclt", "sc", "constitution", "all"],
        default="all",
        help="The data source to ingest from."
    )
    parser.add_argument(
        "--days",
        type=int,
        default=30,
        help="The number of days back to scrape for recent documents."
    )
    args = parser.parse_args()

    logger.info("Initializing Ingestion Service...")
    ingestion_service = IngestionService()

    if args.source in ["nclt", "all"]:
        await ingestion_service.ingest_nclt_data(days_back=args.days)
    if args.source in ["sc", "all"]:
        await ingestion_service.ingest_sc_data(days_back=args.days)
    if args.source in ["constitution", "all"]:
        await ingestion_service.ingest_constitution_data()
    
    logger.info("Ingestion process finished.")

if __name__ == "__main__":
    asyncio.run(main())
