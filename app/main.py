"""
Main application file for the Ultimate Legal-AI Backend.
Sets up the FastAPI application, includes API routers, and defines startup/shutdown events.
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from sqlalchemy import text
from starlette.middleware.cors import CORSMiddleware

from app.api.v1.endpoints import (
    documents, premium_research, search, summaries, auth
)
# Correctly import the new initialization function and the engine for health checks
from app.core.database import initialize_for_production, engine
from app.core.logging import setup_logging
from app.core.rate_limiting import limiter
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from app.core.config import settings

# Set up structured logging
setup_logging()
logger = logging.getLogger(__name__)

# Use the modern lifespan context manager for startup and shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handles application startup and shutdown events."""
    logger.info("🚀 Starting Ultimate Legal-AI Backend...")
    
    # Verify database connection on startup
    initialize_for_production()
    
    logger.info("✅ All systems operational")
    logger.info("🎯 Ultimate Legal-AI Backend ready for premium research!")
    
    yield
    
    logger.info("Shutting down Ultimate Legal-AI Backend...")


# Create FastAPI app with enhanced configuration and lifespan manager
app = FastAPI(
    title="Legal-AI Ultimate Backend",
    description="""
    🏛️ **Ultimate Legal-AI Backend for Company Secretary Professionals**
    
    This is a production-grade, multi-agent AI-powered legal research platform that delivers 
    premium-quality analysis for Company Secretary professionals.
    """,
    version="2.0.0",
    contact={
        "name": "Legal-AI Ultimate Backend",
        "description": "World-class legal research AI for Company Secretaries"
    },
    lifespan=lifespan
)

# --- Middleware ---
# Enhanced CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# --- API Routers ---
app.include_router(auth.router, prefix="/api/v1/auth", tags=["🔐 Authentication"])
app.include_router(search.router, prefix="/api/v1", tags=["🔍 Search"])
app.include_router(documents.router, prefix="/api/v1", tags=["📄 Documents"])
app.include_router(summaries.router, prefix="/api/v1", tags=["📝 Summaries"])
app.include_router(premium_research.router, prefix="/api/v1", tags=["🏆 Premium AI Research"])


@app.get("/", tags=["🏠 Home"])
async def root():
    """Ultimate Legal-AI Backend API Information"""
    return {
        "message": "🏛️ Ultimate Legal-AI Backend for Company Secretary Professionals",
        "version": "2.0.0",
        "status": "🔥 ULTIMATE MODE ACTIVATED"
    }

@app.get("/health", tags=["🏥 Health"])
async def health_check():
    """Comprehensive system health check."""
    db_status = "unhealthy"
    db_error = None
    try:
        # Check database health with a simple query
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        db_status = "healthy"
    except Exception as e:
        logger.error(f"Health check failed to connect to the database: {e}")
        db_error = str(e)

    # Simplified health check response
    response = {
        "status": "🟢 SYSTEM HEALTHY" if db_status == "healthy" else "🔴 SYSTEM UNHEALTHY",
        "timestamp": __import__('datetime').datetime.now().isoformat(),
        "components": {
            "database": db_status,
            "api_server": "operational",
        }
    }
    if db_error:
        response["components"]["database_error"] = db_error

    return response


@app.get("/ultimate-capabilities", tags=["🔥 Ultimate Features"])
async def get_ultimate_capabilities():
    """Showcase the ultimate capabilities of this legal research backend"""
    return {
        "🏛️ legal_ai_backend": "ULTIMATE MODE",
        "🔥 power_level": "MAXIMUM",
        "🚀 capabilities": {
            "multi_agent_ai": {
                "description": "3 specialized AI agents working in perfect harmony",
                "agents": {
                    "legal_analyst": "🏛️ Expert in case law, precedents, and legal reasoning",
                    "cs_expert": "📋 Company Secretary specialist with practical guidance",
                    "quality_reviewer": "✅ Quality assurance with 95%+ accuracy validation"
                }
            },
        },
    }


if __name__ == "__main__":
    import uvicorn
    logger.info("🔥 Starting Ultimate Legal-AI Backend in MAXIMUM MODE!")
    uvicorn.run(
        "app.main:app",
        host=settings.fastapi_host,
        port=settings.fastapi_port,
        reload=True
    )

