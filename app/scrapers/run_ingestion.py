# In file: app/scrapers/run_ingestion.py

import asyncio
import logging
import sys
import os

# This ensures the script can find your 'app' module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.db.base import init_db
# API-based (commented out for now; uncomment if keys are set)
# from app.scrapers.judgment_ingestor import JudgmentIngestor
# from app.scrapers.company_data_ingestor import CompanyDataIngestor
# Web scrapers (new/updated)
from app.scrapers.companies_act_scraper import CompaniesActScraper
from app.scrapers.nclt_nclat_scraper import NCLTNCLATScraper
from app.scrapers.supreme_court_scraper import SupremeCourtScraper
from app.scrapers.constitution_scraper import ConstitutionScraper
from app.scrapers.document_processor import document_processor

# Configure clear, actionable logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [%(name)s] - %(message)s'
)
logger = logging.getLogger(__name__)

async def run_ingestor(ingestor_class, processor, name):
    """A robust wrapper to run a single ingestor and log any errors."""
    logger.info(f"\n--- 🚀 Starting Phase: Ingesting {name} ---")
    try:
        # Pass the processor instance to the ingestor's constructor
        ingestor_instance = ingestor_class(processor)
        await ingestor_instance.scrape()
        logger.info(f"--- ✅ Finished Phase: Ingesting {name} ---\n")
    except Exception as e:
        logger.error(f"--- ❌ CRITICAL FAILURE during {name} ingestion: {e} ---", exc_info=True)

async def main():
    """
    The definitive, robust main function for the entire data ingestion process.
    """
    logger.info("--- 🏛️ Starting Ultimate Backend Data Ingestion ---")

    # Step 1: Initialize the database and create all tables.
    try:
        init_db()
        logger.info("✅ Database initialized successfully.")
    except Exception:
        logger.critical("❌ Halting: Failed to create database tables.")
        return

    # Step 2: Define and run all scrapers/ingestors.
    # API ones commented out—uncomment if needed.
    ingestors_to_run = [
        # (JudgmentIngestor, "Legal Judgments"),  # Uncomment if API key set
        # (CompanyDataIngestor, "Company Master Data"),  # Uncomment if API key set
        (CompaniesActScraper, "Companies Act 2013"),
        (NCLTNCLATScraper, "NCLT/NCLAT Orders"),
        (SupremeCourtScraper, "Supreme Court Judgments"),
        (ConstitutionScraper, "Constitution of India"),
    ]

    for ingestor_class, name in ingestors_to_run:
        await run_ingestor(ingestor_class, document_processor, name)

    logger.info("--- 🎉 All Data Ingestion Phases Completed ---")
    logger.info("💾 Data collected in CockroachDB 'document' table. Query for verification.")


if __name__ == "__main__":
    asyncio.run(main())