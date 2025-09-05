from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.endpoints import search, documents, summaries
from app.core.logging import logger
from app.core.config import settings
from app.db.base import engine
from app.db.models import Base

# Create FastAPI app
app = FastAPI(
    title="Legal-AI Backend",
    description="Production-ready FastAPI backend for Company Secretary research",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(search.router, prefix="/api/v1", tags=["search"])
app.include_router(documents.router, prefix="/api/v1", tags=["documents"])
app.include_router(summaries.router, prefix="/api/v1", tags=["summaries"])

@app.on_event("startup")
async def startup_event():
    """Initialize application on startup"""
    logger.info("Starting Legal-AI Backend...")
    
    # Create database tables
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created/verified")
    except Exception as e:
        logger.error(f"Error creating database tables: {e}")

@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "Legal-AI Backend API",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "search": "/api/v1/search",
            "documents": "/api/v1/documents/{document_id}",
            "summaries": "/api/v1/documents/{document_id}/summary"
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.fastapi_host,
        port=settings.fastapi_port,
        reload=True
    )