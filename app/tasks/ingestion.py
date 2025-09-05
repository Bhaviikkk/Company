from celery import current_task
from sqlalchemy.orm import Session
import requests
import logging
from app.tasks.celery_app import celery_app
from app.db.base import SessionLocal
from app.db.models import Document, ProcessingTask
from app.services.parser import document_parser
from app.services.storage import storage_service
from app.tasks.summarise import summarize_document

logger = logging.getLogger(__name__)

@celery_app.task(bind=True)
def fetch_and_store(self, url: str, title: str = None, court: str = None):
    """
    Fetch document from URL, parse and store
    """
    db = SessionLocal()
    task_id = self.request.id
    
    try:
        # Create processing task record
        processing_task = ProcessingTask(
            task_type="ingestion",
            status="running"
        )
        db.add(processing_task)
        db.commit()
        
        logger.info(f"Starting ingestion for URL: {url}")
        
        # Fetch document
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        if response.headers.get('content-type', '').startswith('application/pdf'):
            pdf_content = response.content
        else:
            logger.error(f"URL does not serve PDF content: {url}")
            processing_task.status = "failed"
            processing_task.error_message = "URL does not serve PDF content"
            db.commit()
            return {"error": "Not a PDF document"}
        
        # Parse document
        extracted_text, content_hash = document_parser.extract_text_from_pdf(pdf_content)
        
        # Check for duplicates
        existing_doc = db.query(Document).filter(
            Document.content_hash == content_hash
        ).first()
        
        if existing_doc:
            logger.info(f"Document already exists: {existing_doc.document_id}")
            processing_task.status = "completed"
            processing_task.document_id = existing_doc.document_id
            db.commit()
            return {"document_id": str(existing_doc.document_id), "status": "duplicate"}
        
        # Store PDF in storage
        filename = f"{content_hash}.pdf"
        storage_path = storage_service.store_document(pdf_content, filename)
        
        # Create document record
        document = Document(
            title=title or f"Document from {url}",
            court=court,
            url=url,
            storage_path=storage_path,
            content_hash=content_hash,
            raw_text=extracted_text
        )
        
        db.add(document)
        db.commit()
        
        # Update processing task
        processing_task.status = "completed"
        processing_task.document_id = document.document_id
        db.commit()
        
        logger.info(f"Document stored: {document.document_id}")
        
        # Trigger summarization
        summarize_document.delay(str(document.document_id))
        
        return {
            "document_id": str(document.document_id),
            "status": "completed",
            "storage_path": storage_path
        }
        
    except Exception as e:
        logger.error(f"Error in ingestion task: {e}")
        processing_task.status = "failed"
        processing_task.error_message = str(e)
        db.commit()
        raise
    finally:
        db.close()