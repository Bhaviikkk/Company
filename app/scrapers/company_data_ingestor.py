# In file: app/scrapers/company_data_ingestor.py

import asyncio
import logging
import httpx
from app.core.config import settings
from .base_scraper import BaseScraper
from app.db.models import Company
from app.db.base import SessionLocal
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError

logger = logging.getLogger(__name__)

class CompanyDataIngestor(BaseScraper):
    """Ingests Company Master Data from the official data.gov.in API."""
    API_BASE_URL = "https://api.data.gov.in/resource/24e8367f-92a3-4923-8686-a2a31c5b8b32"

    def _store_companies_in_db(self, companies_data: list):
        if not companies_data: return
        db = SessionLocal()
        try:
            logger.info(f"Preparing to insert/update {len(companies_data)} company records.")
            
            stmt = insert(Company).values(companies_data)
            update_dict = {c.name: getattr(stmt.excluded, c.name) for c in Company.__table__.columns if not c.primary_key}
            stmt = stmt.on_conflict_do_update(index_elements=['cin'], set_=update_dict)
            
            db.execute(stmt)
            db.commit()
            logger.info(f"Successfully committed {len(companies_data)} company records.")
        except (IntegrityError, Exception) as e:
            logger.error(f"Database error during company data insertion: {e}", exc_info=True)
            db.rollback()
        finally:
            db.close()

    async def scrape(self):
        logger.info("Starting API ingestion for Company Master Data.")
        if not settings.data_gov_api_key:
            logger.error("`DATA_GOV_API_KEY` is not set. Aborting company data ingestion.")
            return

        params = { "api-key": settings.data_gov_api_key, "format": "json", "offset": 0, "limit": 1000 }

        async with httpx.AsyncClient() as client:
            # This now correctly calls the new get_with_retry method
            response = await self.get_with_retry(client, self.API_BASE_URL, params=params)
            
            if response and response.status_code == 200:
                data = response.json()
                records = data.get('records', [])
                logger.info(f"Fetched {len(records)} company records from data.gov.in.")
                
                companies_to_store = [
                    {
                        "cin": record.get('corporate_identification_number'),
                        "company_name": record.get('company_name'),
                        "date_of_registration": self._parse_date_from_text(record.get('date_of_registration')),
                        "company_status": record.get('company_status'),
                        "registered_address": record.get('registered_address')
                    }
                    for record in records if record.get('corporate_identification_number')
                ]
                
                self._store_companies_in_db(companies_to_store)
            else:
                status = response.status_code if response else 'N/A'
                logger.error(f"Failed to fetch company data. Status: {status}")

        logger.info("✅ Finished Company Master Data ingestion.")