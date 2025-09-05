from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from app.db.base import get_db
from app.services.search import search_service

router = APIRouter()

@router.get("/search")
async def search_documents(
    q: str = Query(..., description="Search query"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    court: Optional[str] = Query(None, description="Filter by court"),
    date_from: Optional[str] = Query(None, description="Filter by date from (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="Filter by date to (YYYY-MM-DD)"),
    db: Session = Depends(get_db)
):
    """Search legal documents with filters"""
    try:
        results = search_service.search_documents(
            db=db,
            query=q,
            page=page,
            per_page=per_page,
            court=court,
            date_from=date_from,
            date_to=date_to
        )
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")