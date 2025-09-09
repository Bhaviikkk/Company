import asyncio
import logging
import hashlib
from typing import Dict, List, Optional
from datetime importdatetime

from sqlalchemy.orm import Session
from app.db.models import Document
from app.db.base import SessionLocal
from app.scrapers.nclt_nclat_scraper import NCLTNCLATScraper
from app.scrapers.supreme_court_scraper import SupremeCourtScraper
from app.services.parser import document_parser

logger = logging.getLogger(__name__)

class IngestionService:
    """Service to handle scraping, parsing, and storing of legal documents."""

    def __init__(self):
        self.nclt_scraper = NCLTNCLATScraper()
        self.sc_scraper = SupremeCourtScraper()

    async def ingest_nclt_data(self, days_back: int = 15):
        """Scrape and ingest recent data from NCLT/NCLAT."""
        logger.info(f"Starting NCLT/NCLAT ingestion for the last {days_back} days.")
        scraped_docs = await self.nclt_scraper.scrape_recent_orders(days_back=days_back)
        await self._process_scraped_documents(scraped_docs, self.nclt_scraper)

    async def ingest_sc_data(self, days_back: int = 30):
        """Scrape and ingest recent data from the Supreme Court."""
        logger.info(f"Starting Supreme Court ingestion for the last {days_back} days.")
        scraped_docs = await self.sc_scraper.scrape_recent_judgments(days_back=days_back)
        await self._process_scraped_documents(scraped_docs, self.sc_scraper)

    async def _process_scraped_documents(self, documents: List[Dict], scraper_instance):
        """Process a list of scraped documents and store them in the database."""
        tasks = [self._process_and_store_document(doc, scraper_instance) for doc in documents]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        success_count = sum(1 for r in results if r is not None and not isinstance(r, Exception))
        error_count = sum(1 for r in results if isinstance(r, Exception))
        duplicate_count = sum(1 for r in results if r is None)

        logger.info(
            f"Ingestion complete. "
            f"Successfully stored: {success_count}, "
            f"Duplicates skipped: {duplicate_count}, "
            f"Errors: {error_count}."
        )

    async def _process_and_store_document(self, doc_meta: Dict, scraper_instance) -> Optional[str]:
        """Fetch, parse, and store a single document if it's new."""
        db: Session = SessionLocal()
        try:
            doc_url = doc_meta.get("url")
            if not doc_url:
                logger.warning(f"Skipping document with no URL: {doc_meta.get('title')}")
                return None

            fetch_result = await scraper_instance.fetch_with_retry(doc_url)
            if not fetch_result:
                raise ConnectionError(f"Could not fetch {doc_url}")
            
            content_type, content_bytes = fetch_result

            if 'pdf' in content_type.lower() or '.pdf' in doc_url.lower():
                raw_text, content_hash = document_parser.extract_text_from_pdf(content_bytes)
            else:
                raw_text = content_bytes.decode('utf-8', errors='ignore')
                normalized_text = document_parser._normalize_text(raw_text)
                content_hash = hashlib.sha256(normalized_text.encode()).hexdigest()

            if not raw_text or not raw_text.strip():
                logger.warning(f"No text extracted from {doc_url}. Skipping.")
                return None

            existing_doc = db.query(Document).filter(Document.content_hash == content_hash).first()
            if existing_doc:
                logger.info(f"Duplicate document found, skipping: {doc_url} (Hash: {content_hash[:10]})")
                return None

            logger.info(f"New document found. Storing: {doc_meta.get('title')}")
            serializable_meta = {k: v for k, v in doc_meta.items() if isinstance(v, (str, int, float, bool, list, dict, type(None)))}
            
            new_document = Document(
                title=doc_meta.get("title", "Untitled"),
                court=doc_meta.get("tribunal") or doc_meta.get("court", "Unknown"),
                url=doc_url,
                decision_date=datetime.fromisoformat(doc_meta["decision_date"]).date() if doc_meta.get("decision_date") else None,
                raw_text=raw_text,
                content_hash=content_hash,
                metadata=serializable_meta
            )
            db.add(new_document)
            db.commit()
            db.refresh(new_document)
            return str(new_document.document_id)
        except Exception as e:
            db.rollback()
            logger.error(f"Error processing document {doc_meta.get('url')}: {e}", exc_info=True)
            raise e
        finally:
            db.close()