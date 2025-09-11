"""
Production-ready document processor that connects scrapers to PDF parsing
"""
import asyncio
import hashlib
from typing import Dict, List, Optional
import logging
from datetime import datetime

# These service/DB imports are fine as they don't depend on the scrapers
from app.services.parser import document_parser
from app.services.storage import storage_service
from app.db.base import SessionLocal
from app.db.models import Document
from sqlalchemy.orm import Session
import httpx  # For fallback download

logger = logging.getLogger(__name__)

class DocumentProcessor:
    """Process scraped documents into database with full PDF parsing"""
    
    def __init__(self):
        self.processed_hashes = set()
    
    async def process_documents(
        self, 
        documents: List[Dict], 
        source_name: str = "unknown"
    ) -> List[Dict]:
        """
        Process scraped documents through full pipeline:
        1. Download PDFs (or use raw_text if available)
        2. Extract text with PDF parser if needed
        3. Deduplicate using content hash
        4. Store in database
        5. Return processing results
        """
        logger.info(f"Processing {len(documents)} scraped documents from {source_name}")
        
        results = []
        
        semaphore = asyncio.Semaphore(5)  # Limit concurrent processing
        
        async def process_one(doc):
            async with semaphore:
                db = SessionLocal()
                try:
                    return await self._process_single_document(db, doc, source_name)
                finally:
                    db.close()
        
        tasks = [process_one(doc) for doc in documents]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Flatten results, handle exceptions
        final_results = []
        for res in results:
            if isinstance(res, Exception):
                logger.error(f"Exception in processing: {res}")
                final_results.append({"status": "error", "error": str(res)})
            else:
                final_results.append(res)
        
        logger.info(f"Completed processing {len(final_results)} documents")
        return final_results
            
    
    async def _process_single_document(
        self, 
        db: Session, 
        doc: Dict, 
        source_name: str
    ) -> Dict:
        """Process a single document through the full pipeline"""
        
        url = doc.get("source_url") or doc.get("url")
        if not url and not doc.get("raw_text"):
            return {"status": "error", "error": "No URL or raw_text provided"}
        
        # If raw_text is already available (e.g., Constitution), skip download/extraction
        if doc.get("raw_text"):
            extracted_text = doc["raw_text"]
            content_hash = hashlib.sha256(extracted_text.encode('utf-8')).hexdigest()
            extraction_metadata = {"method": "direct_html"}
        else:
            # Step 1: Download PDF content
            pdf_content = await self._download_pdf(url, source_name)
            if not pdf_content:
                return {
                    "url": url,
                    "status": "error", 
                    "error": "Failed to download PDF content"
                }
            
            # Step 2: Generate content hash for deduplication
            content_hash = hashlib.sha256(pdf_content).hexdigest()
            
            # Check if already processed
            existing = db.query(Document).filter(
                Document.content_hash == content_hash
            ).first()
            
            if existing:
                logger.debug(f"Document already exists: {url}")
                return {
                    "url": url,
                    "status": "duplicate",
                    "document_id": str(existing.document_id),
                    "existing_title": existing.title
                }
            
            # Step 3: Extract text using PDF parser
            extracted_text, extraction_metadata = document_parser.extract_text_from_pdf(pdf_content)
            
            if not extracted_text or len(extracted_text) < 100:
                return {
                    "url": url,
                    "status": "error",
                    "error": "Failed to extract sufficient text from PDF"
                }
        
        # Enhanced dedup: also check URL
        url_hash = hashlib.sha256(url.encode('utf-8')).hexdigest()
        existing_url = db.query(Document).filter(
            Document.source_url == url
        ).first()
        if existing_url:
            return {
                "url": url,
                "status": "duplicate_url",
                "document_id": str(existing_url.document_id),
                "existing_title": existing_url.title
            }
        
        # Step 4: Store document in database
        document = Document(
            title=doc.get("title", "Unknown Document")[:500],  # Truncate title
            court=doc.get("court", doc.get("tribunal", doc.get("jurisdiction", source_name)))[:200],
            decision_date=self._parse_date(doc.get("decision_date")),
            source_url=url,
            content_hash=content_hash,
            raw_text=extracted_text[:1000000],  # Cap text length to prevent bloat
            metadata=extraction_metadata  # Assuming model has metadata field; add if not
        )
        
        db.add(document)
        
        try:
            db.commit()
            db.refresh(document)
            
            logger.info(f"Successfully processed document: {url}")
            
            return {
                "url": url,
                "status": "success",
                "document_id": str(document.document_id),
                "title": document.title,
                "text_length": len(extracted_text),
                "extraction_metadata": extraction_metadata
            }
            
        except Exception as e:
            db.rollback()
            logger.error(f"Database error for {url}: {e}")
            return {
                "url": url,
                "status": "error",
                "error": f"Database error: {str(e)}"
            }
    
    async def _download_pdf(self, url: str, source_name: str) -> Optional[bytes]:
        """Download PDF content from URL using standard fetch (no source-specific scrapers for simplicity)."""
        
        if not url or not url.lower().endswith('.pdf'):
            logger.warning(f"URL not a PDF: {url}")
            return None

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await self.fetch_with_retry(client, url) if hasattr(self, 'fetch_with_retry') else await client.get(url)
            if resp and resp.status_code == 200:
                content_type = resp.headers.get("content-type", "").lower()
                if 'pdf' in content_type:
                    logger.info(f"Successfully downloaded PDF from {url}")
                    return resp.content
                else:
                    logger.warning(f"Downloaded content not PDF: {content_type}")
            logger.warning(f"Failed to download PDF from {url}. Status: {resp.status_code if resp else 'N/A'}")
            return None
    
    def _parse_date(self, date_str: str) -> Optional[datetime.date]:
        """Parse date string into datetime.date object"""
        
        if not date_str:
            return None
        
        try:
            return datetime.fromisoformat(date_str).date()
        except (ValueError, TypeError):
            # Fallback to base parser
            from app.scrapers.base_scraper import BaseScraper
            return BaseScraper()._parse_date_from_text(date_str)

# Global instance
document_processor = DocumentProcessor()