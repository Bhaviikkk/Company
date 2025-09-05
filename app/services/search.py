from typing import List, Dict, Any, Optional
import logging
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from app.db.models import Document, Summary

logger = logging.getLogger(__name__)

class SearchService:
    """Search service for documents and summaries"""
    
    def search_documents(
        self, 
        db: Session, 
        query: str, 
        page: int = 1, 
        per_page: int = 20,
        court: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Search documents with full-text search and filters.
        Returns: paginated results with metadata
        """
        try:
            # Build query
            db_query = db.query(Document)
            
            # Text search across title and raw_text
            if query:
                search_filter = or_(
                    Document.title.ilike(f"%{query}%"),
                    Document.raw_text.ilike(f"%{query}%")
                )
                db_query = db_query.filter(search_filter)
            
            # Apply filters
            if court:
                db_query = db_query.filter(Document.court.ilike(f"%{court}%"))
            
            if date_from:
                db_query = db_query.filter(Document.decision_date >= date_from)
            
            if date_to:
                db_query = db_query.filter(Document.decision_date <= date_to)
            
            # Get total count
            total = db_query.count()
            
            # Apply pagination
            offset = (page - 1) * per_page
            documents = db_query.offset(offset).limit(per_page).all()
            
            # Format results
            results = []
            for doc in documents:
                # Generate snippet from raw_text
                snippet = self._generate_snippet(doc.raw_text, query)
                
                results.append({
                    "document_id": str(doc.document_id),
                    "title": doc.title,
                    "court": doc.court,
                    "decision_date": doc.decision_date.isoformat() if doc.decision_date else None,
                    "snippet": snippet,
                    "url": doc.url
                })
            
            return {
                "results": results,
                "pagination": {
                    "page": page,
                    "per_page": per_page,
                    "total": total,
                    "pages": (total + per_page - 1) // per_page
                }
            }
            
        except Exception as e:
            logger.error(f"Error searching documents: {e}")
            raise
    
    def _generate_snippet(self, text: str, query: str, max_length: int = 200) -> str:
        """Generate search result snippet"""
        if not text or not query:
            return text[:max_length] + "..." if len(text) > max_length else text
        
        # Find query in text (case insensitive)
        text_lower = text.lower()
        query_lower = query.lower()
        
        pos = text_lower.find(query_lower)
        if pos == -1:
            # Query not found, return beginning of text
            return text[:max_length] + "..." if len(text) > max_length else text
        
        # Extract snippet around query
        start = max(0, pos - max_length // 2)
        end = min(len(text), pos + len(query) + max_length // 2)
        
        snippet = text[start:end]
        
        if start > 0:
            snippet = "..." + snippet
        if end < len(text):
            snippet = snippet + "..."
        
        return snippet

# Global search service instance
search_service = SearchService()