from celery import current_task
from sqlalchemy.orm import Session
import logging
import uuid
from app.tasks.celery_app import celery_app
from app.db.base import SessionLocal
from app.db.models import Document, Summary, ProcessingTask
from app.services.summariser_agent import summariser_agent

logger = logging.getLogger(__name__)

@celery_app.task(bind=True)
def summarize_document(self, document_id: str, style: str = "cs_student"):
    """
    Generate summary for document
    """
    db = SessionLocal()
    task_id = self.request.id
    
    try:
        # Get document
        document = db.query(Document).filter(
            Document.document_id == uuid.UUID(document_id)
        ).first()
        
        if not document:
            logger.error(f"Document not found: {document_id}")
            return {"error": "Document not found"}
        
        # Create processing task record
        processing_task = ProcessingTask(
            document_id=document.document_id,
            task_type="summarization",
            status="running"
        )
        db.add(processing_task)
        db.commit()
        
        logger.info(f"Starting summarization for document: {document_id}")
        
        # Check if summary already exists
        existing_summary = db.query(Summary).filter(
            Summary.document_id == document.document_id,
            Summary.style == style,
            Summary.human_status == "approved"
        ).first()
        
        if existing_summary:
            logger.info(f"Summary already exists: {existing_summary.summary_id}")
            processing_task.status = "completed"
            db.commit()
            return {"summary_id": str(existing_summary.summary_id), "status": "exists"}
        
        # Generate summary
        summary_data = summariser_agent.summarise_document(document.raw_text, style)
        
        if not summary_data:
            logger.error("Failed to generate summary")
            processing_task.status = "failed"
            processing_task.error_message = "Failed to generate summary"
            db.commit()
            return {"error": "Failed to generate summary"}
        
        # Perform quality checks
        quality_score, grounding_score = self._perform_quality_checks(
            summary_data, document.raw_text
        )
        
        # Determine approval status based on quality scores
        human_status = "approved" if grounding_score >= 0.95 else "pending"
        
        # Create summary record
        summary = Summary(
            document_id=document.document_id,
            style=style,
            model_id="gemini-1.5-pro",  # From settings
            prompt_version="1.0",
            summary_short=str(summary_data.get("holding", "")),
            summary_detailed=str(summary_data),
            span_citations=summary_data.get("span_offsets", []),
            quality_score=quality_score,
            grounding_score=str(grounding_score),
            human_status=human_status
        )
        
        db.add(summary)
        db.commit()
        
        # Update processing task
        processing_task.status = "completed"
        db.commit()
        
        logger.info(f"Summary created: {summary.summary_id}, Status: {human_status}")
        
        return {
            "summary_id": str(summary.summary_id),
            "status": human_status,
            "quality_score": quality_score,
            "grounding_score": grounding_score
        }
        
    except Exception as e:
        logger.error(f"Error in summarization task: {e}")
        processing_task.status = "failed"
        processing_task.error_message = str(e)
        db.commit()
        raise
    finally:
        db.close()
    
    def _perform_quality_checks(self, summary_data: dict, raw_text: str) -> tuple:
        """
        Perform quality checks on generated summary
        Returns: (quality_score, grounding_score)
        """
        try:
            # Basic grounding check
            span_offsets = summary_data.get("span_offsets", [])
            total_claims = len(span_offsets)
            
            if total_claims == 0:
                return "low", 0.0
            
            # Check if spans are valid
            valid_spans = 0
            for span in span_offsets:
                start = span.get("start_offset", 0)
                end = span.get("end_offset", 0)
                
                if 0 <= start < end <= len(raw_text):
                    valid_spans += 1
            
            grounding_score = valid_spans / total_claims if total_claims > 0 else 0
            
            # Assign quality score based on grounding
            if grounding_score >= 0.95:
                quality_score = "high"
            elif grounding_score >= 0.8:
                quality_score = "medium"
            else:
                quality_score = "low"
            
            return quality_score, grounding_score
            
        except Exception as e:
            logger.error(f"Error in quality checks: {e}")
            return "low", 0.0