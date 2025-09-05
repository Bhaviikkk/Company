from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

# Enhanced database configuration for production workloads
def create_production_engine():
    """Create database engine optimized for production workloads"""
    
    # CockroachDB connection string format
    if "cockroachdb://" in settings.database_url or "postgresql://" in settings.database_url:
        # Production-grade connection pool settings
        engine = create_engine(
            settings.database_url,
            # Connection pool settings for heavy workloads
            pool_size=20,           # Base pool size
            max_overflow=30,        # Additional connections
            pool_pre_ping=True,     # Validate connections
            pool_recycle=3600,      # Recycle connections after 1 hour
            # Connection timeout settings
            connect_args={
                "connect_timeout": 10,
                "application_name": "legal_ai_backend",
                "sslmode": "prefer"
            },
            # Echo SQL for debugging (disable in production)
            echo=False
        )
    else:
        # Fallback for other database types
        engine = create_engine(
            settings.database_url,
            pool_pre_ping=True,
            echo=False
        )
    
    return engine

# Create the engine
engine = create_production_engine()

# Create sessionmaker with optimized settings
SessionLocal = sessionmaker(
    autocommit=False, 
    autoflush=False, 
    bind=engine,
    expire_on_commit=False  # Keep objects accessible after commit
)

# Create base class
Base = declarative_base()

def get_db():
    """Enhanced database dependency with error handling"""
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error(f"Database session error: {e}")
        db.rollback()
        raise
    finally:
        db.close()

async def create_database_indexes():
    """Create performance indexes for heavy data workloads"""
    
    with engine.connect() as conn:
        try:
            # Indexes for document search and retrieval
            indexes = [
                "CREATE INDEX IF NOT EXISTS idx_documents_content_hash ON documents (content_hash)",
                "CREATE INDEX IF NOT EXISTS idx_documents_created_at ON documents (created_at DESC)",
                "CREATE INDEX IF NOT EXISTS idx_documents_decision_date ON documents (decision_date DESC)",
                "CREATE INDEX IF NOT EXISTS idx_documents_court ON documents (court)",
                "CREATE INDEX IF NOT EXISTS idx_documents_title_search ON documents USING GIN (to_tsvector('english', title))",
                
                # Indexes for summary operations
                "CREATE INDEX IF NOT EXISTS idx_summaries_document_id ON summaries (document_id)",
                "CREATE INDEX IF NOT EXISTS idx_summaries_style ON summaries (style)",
                "CREATE INDEX IF NOT EXISTS idx_summaries_human_status ON summaries (human_status)",
                "CREATE INDEX IF NOT EXISTS idx_summaries_quality_score ON summaries (quality_score)",
                "CREATE INDEX IF NOT EXISTS idx_summaries_created_at ON summaries (created_at DESC)",
                
                # Indexes for processing tasks
                "CREATE INDEX IF NOT EXISTS idx_processing_tasks_status ON processing_tasks (status)",
                "CREATE INDEX IF NOT EXISTS idx_processing_tasks_task_type ON processing_tasks (task_type)",
                "CREATE INDEX IF NOT EXISTS idx_processing_tasks_document_id ON processing_tasks (document_id)",
                
                # Full-text search indexes for document content
                "CREATE INDEX IF NOT EXISTS idx_documents_fulltext_search ON documents USING GIN (to_tsvector('english', coalesce(title, '') || ' ' || coalesce(raw_text, '')))",
            ]
            
            for index_sql in indexes:
                try:
                    conn.execute(text(index_sql))
                    logger.info(f"Created index: {index_sql.split(' ')[-1]}")
                except Exception as e:
                    logger.warning(f"Index creation skipped (may already exist): {e}")
            
            conn.commit()
            logger.info("Database indexes created successfully")
            
        except Exception as e:
            logger.error(f"Error creating database indexes: {e}")

async def create_partitioned_tables():
    """Create partitioned tables for heavy data storage"""
    
    with engine.connect() as conn:
        try:
            # Create partitioned documents table by date
            partition_sql = """
            -- Create partitioned documents table for heavy data workloads
            CREATE TABLE IF NOT EXISTS documents_partitioned (
                LIKE documents INCLUDING ALL
            ) PARTITION BY RANGE (created_at);
            
            -- Create monthly partitions for current and next year
            CREATE TABLE IF NOT EXISTS documents_2025 PARTITION OF documents_partitioned
                FOR VALUES FROM ('2025-01-01') TO ('2026-01-01');
            
            CREATE TABLE IF NOT EXISTS documents_2026 PARTITION OF documents_partitioned
                FOR VALUES FROM ('2026-01-01') TO ('2027-01-01');
            """
            
            conn.execute(text(partition_sql))
            conn.commit()
            
            logger.info("Partitioned tables created successfully")
            
        except Exception as e:
            logger.warning(f"Partitioned table creation skipped: {e}")

def configure_database_for_heavy_workloads():
    """Configure database settings for heavy data processing"""
    
    with engine.connect() as conn:
        try:
            # Optimize for heavy read/write workloads
            optimization_sql = [
                "SET work_mem = '256MB'",
                "SET effective_cache_size = '4GB'", 
                "SET random_page_cost = 1.1",
                "SET effective_io_concurrency = 200",
            ]
            
            for sql in optimization_sql:
                try:
                    conn.execute(text(sql))
                except Exception as e:
                    logger.debug(f"Optimization setting skipped: {e}")
            
            logger.info("Database optimized for heavy workloads")
            
        except Exception as e:
            logger.warning(f"Database optimization skipped: {e}")

async def get_database_stats():
    """Get database performance statistics"""
    
    with engine.connect() as conn:
        try:
            stats_queries = {
                "total_documents": "SELECT COUNT(*) FROM documents",
                "total_summaries": "SELECT COUNT(*) FROM summaries",
                "pending_summaries": "SELECT COUNT(*) FROM summaries WHERE human_status = 'pending'",
                "approved_summaries": "SELECT COUNT(*) FROM summaries WHERE human_status = 'approved'",
                "processing_tasks": "SELECT task_type, status, COUNT(*) FROM processing_tasks GROUP BY task_type, status",
                "database_size": "SELECT pg_size_pretty(pg_database_size(current_database())) as size"
            }
            
            stats = {}
            for name, query in stats_queries.items():
                try:
                    result = conn.execute(text(query)).fetchall()
                    stats[name] = result
                except Exception as e:
                    stats[name] = f"Error: {e}"
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting database stats: {e}")
            return {"error": str(e)}

class DatabaseManager:
    """Database management utilities for production workloads"""
    
    @staticmethod
    async def initialize_for_production():
        """Initialize database for production workloads"""
        logger.info("Initializing database for production workloads")
        
        # Create tables
        Base.metadata.create_all(bind=engine)
        
        # Create performance indexes
        await create_database_indexes()
        
        # Create partitioned tables
        await create_partitioned_tables()
        
        # Configure for heavy workloads
        configure_database_for_heavy_workloads()
        
        logger.info("Database initialization completed")
    
    @staticmethod
    async def health_check():
        """Comprehensive database health check"""
        try:
            with engine.connect() as conn:
                # Test connection
                conn.execute(text("SELECT 1"))
                
                # Get basic stats
                stats = await get_database_stats()
                
                return {
                    "status": "healthy",
                    "connection": "active",
                    "statistics": stats
                }
                
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return {
                "status": "unhealthy", 
                "error": str(e)
            }