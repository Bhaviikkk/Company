"""
Production-ready document processor that connects scrapers to PDF parsing
"""
import asyncio
import hashlib
from typing import Dict, List, Optional, Tuple
import logging
from datetime import datetime

from app.services.parser import document_parser
from app.services.storage import storage_service
from app.db.base import SessionLocal
from app.scrapers.supreme_court_scraper import SupremeCourtScraper
from app.scrapers.nclt_nclat_scraper import NCLTNCLATScraper
from app.scrapers.constitution_scraper import ConstitutionScraper
from app.db.models import Document
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

class DocumentProcessor:
    """Process scraped documents into database with full PDF parsing"""
    
    def __init__(self):
        self.processed_hashes = set()
    
    async def process_scraped_documents(
        self, 
        documents: List[Dict], 
        source_name: str = "unknown"
    ) -> List[Dict]:
        """
        Process scraped documents through full pipeline:
        1. Download PDFs
        2. Extract text with PDF parser
        3. Deduplicate using content hash
        4. Store in database
        5. Return processing results
        """
        logger.info(f"Processing {len(documents)} scraped documents from {source_name}")
        
        results = []
        db = SessionLocal()
        
        try:
            for doc in documents:
                try:
                    result = await self._process_single_document(db, doc, source_name)
                    results.append(result)
                    
                    # Log progress
                    if len(results) % 10 == 0:
                        logger.info(f"Processed {len(results)}/{len(documents)} documents")
                        
                except Exception as e:
                    logger.error(f"Error processing document {doc.get('url', 'unknown')}: {e}")
                    results.append({
                        "url": doc.get("url"),
                        "status": "error",
                        "error": str(e)
                    })
            
            logger.info(f"Completed processing {len(results)} documents")
            return results
            
        finally:
            db.close()
    
    async def _process_single_document(
        self, 
        db: Session, 
        doc: Dict, 
        source_name: str
    ) -> Dict:
        """Process a single document through the full pipeline"""
        
        url = doc.get("url")
        if not url:
            return {"status": "error", "error": "No URL provided"}
        
        # Step 1: Download PDF content
        pdf_content = await self._download_pdf(doc, source_name)
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
        
        # Step 4: Store document in database
        try:
            document = Document(
                title=doc.get("title", "Unknown Document")[:500],  # Truncate title
                court=doc.get("court", doc.get("jurisdiction", source_name))[:200],
                decision_date=self._parse_date(doc.get("decision_date")),
                url=url,
                content_hash=content_hash,
                raw_text=extracted_text[:50000],  # Limit text size
                storage_path=None  # Could store PDF in cloud storage later
            )
            
            db.add(document)
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
    
    async def _download_pdf(self, doc: Dict, source_name: str) -> Optional[bytes]:
        """Download PDF content from URL using the appropriate scraper for the source."""
        
        url = doc.get("url")
        if not url or not url.lower().endswith('.pdf'):
            return None

        # Map the source name from the ingestion script to the correct scraper class
        scraper_class_map = {
            "sc": SupremeCourtScraper,
            "nclt": NCLTNCLATScraper,
            "constitution": ConstitutionScraper,
        }

        scraper_class = scraper_class_map.get(source_name.lower())

        if not scraper_class:
            logger.error(f"No scraper configured for source '{source_name}' to download PDF from {url}")
            return None
        
        try:
            async with scraper_class() as scraper:
                result = await scraper.fetch_with_retry(url)
                if result:
                    content_type, content = result
                    if 'pdf' in content_type.lower():
                        logger.info(f"Successfully downloaded PDF from {url} using {scraper_class.__name__}")
                        return content
            logger.warning(f"Failed to download PDF from {url} using {scraper_class.__name__}. Result was None or not a PDF.")
            return None
            
        except Exception as e:
            logger.error(f"Error downloading PDF from {url} using {scraper_class.__name__}: {e}")
            return None
    
    def _parse_date(self, date_str: str) -> Optional[datetime.date]:
        """Parse date string into datetime.date object"""
        
        if not date_str:
            return None
        
        try:
            # Try ISO format first
            if '-' in date_str and len(date_str) >= 8:
                return datetime.fromisoformat(date_str).date()
        except:
            pass
        
        # Try other common formats
        import re
        date_patterns = [
            (r'(\d{4})-(\d{1,2})-(\d{1,2})', '%Y-%m-%d'),
            (r'(\d{1,2})-(\d{1,2})-(\d{4})', '%d-%m-%Y'),
            (r'(\d{1,2})/(\d{1,2})/(\d{4})', '%d/%m/%Y'),
        ]
        
        for pattern, fmt in date_patterns:
            match = re.search(pattern, str(date_str))
            if match:
                try:
                    date_obj = datetime.strptime(match.group(), fmt.replace('(%d{', '').replace('})', ''))
                    return date_obj.date()
                except:
                    continue
        
        return None

# Global instance
document_processor = DocumentProcessor()