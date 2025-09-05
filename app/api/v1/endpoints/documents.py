from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy.orm import Session
from typing import Dict, Any
import uuid
from app.db.base import get_db
from app.db.models import Document, Summary
from app.services.storage import storage_service

router = APIRouter()

@router.get("/documents/{document_id}")
async def get_document(
    document_id: str = Path(..., description="Document UUID"),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Get document metadata and available summaries"""
    try:
        # Validate UUID
        doc_uuid = uuid.UUID(document_id)
        
        # Get document
        document = db.query(Document).filter(Document.document_id == doc_uuid).first()
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Get available summaries
        summaries = db.query(Summary).filter(
            Summary.document_id == doc_uuid,
            Summary.human_status == "approved"
        ).all()
        
        # Generate signed URL for PDF if storage path exists
        pdf_url = None
        if document.storage_path:
            pdf_url = storage_service.get_document_url(document.storage_path)
        
        return {
            "document_id": str(document.document_id),
            "title": document.title,
            "court": document.court,
            "decision_date": document.decision_date.isoformat() if document.decision_date else None,
            "url": document.url,
            "pdf_url": pdf_url,
            "created_at": document.created_at.isoformat(),
            "available_summaries": [
                {
                    "summary_id": str(s.summary_id),
                    "style": s.style,
                    "created_at": s.created_at.isoformat(),
                    "quality_score": s.quality_score
                }
                for s in summaries
            ]
        }
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid document ID format")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving document: {str(e)}")

@router.post("/documents/upload")
async def upload_document():
    """Upload and process a new document"""
    # This would be implemented for manual document uploads
    return {"message": "Document upload endpoint - to be implemented"}