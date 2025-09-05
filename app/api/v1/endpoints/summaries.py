from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional
import uuid
from app.db.base import get_db
from app.db.models import Document, Summary

router = APIRouter()

@router.get("/documents/{document_id}/summary")
async def get_document_summary(
    document_id: str = Path(..., description="Document UUID"),
    style: str = Query("cs_student", description="Summary style"),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Get approved summary for a document"""
    try:
        # Validate UUID
        doc_uuid = uuid.UUID(document_id)
        
        # Check if document exists
        document = db.query(Document).filter(Document.document_id == doc_uuid).first()
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Get summary
        summary = db.query(Summary).filter(
            Summary.document_id == doc_uuid,
            Summary.style == style,
            Summary.human_status == "approved"
        ).first()
        
        if not summary:
            raise HTTPException(
                status_code=404, 
                detail=f"No approved summary found for style '{style}'"
            )
        
        # Format response
        return {
            "summary_id": str(summary.summary_id),
            "document_id": str(summary.document_id),
            "style": summary.style,
            "summary_short": summary.summary_short,
            "summary_detailed": summary.summary_detailed,
            "span_citations": summary.span_citations,
            "quality_metrics": {
                "quality_score": summary.quality_score,
                "grounding_score": summary.grounding_score,
                "citation_score": summary.citation_score,
                "consistency_score": summary.consistency_score
            },
            "provenance": {
                "model_id": summary.model_id,
                "prompt_version": summary.prompt_version,
                "source_url": document.url,
                "content_hash": document.content_hash
            },
            "created_at": summary.created_at.isoformat()
        }
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid document ID format")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving summary: {str(e)}")