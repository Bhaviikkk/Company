"""
Handles database connections, session management, and utility functions for database interactions.
This module ensures that the application can connect to the database, manage sessions
for handling requests, and perform necessary setup tasks.
"""

import logging
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.session import Session

from app.core.config import settings

# Set up structured logging
logger = logging.getLogger(__name__)

def create_production_engine():
    """
    Creates a database engine optimized for production workloads with robust connection pooling.
    """
    try:
        logger.info("Creating production-grade database engine...")
        
        # Production-grade connection pool settings suitable for CockroachDB and PostgreSQL
        engine = create_engine(
            settings.database_url,
            pool_size=20,          # The number of connections to keep open in the pool
            max_overflow=30,       # The number of connections that can be opened beyond pool_size
            pool_pre_ping=True,    # Checks connection health before use, preventing errors from stale connections
            pool_recycle=3600,     # Recycles connections after one hour to prevent them from being closed by the DB or network
            connect_args={
                "connect_timeout": 10,  # Timeout for establishing a new connection
                "application_name": "ultimate_legal_ai_backend",
                 # For CockroachDB, helps route queries to the correct database context
                "options": f"-csearch_path={settings.database_url.split('/')[-1].split('?')[0]}"
            } if 'cockroachdb' in settings.database_url else {
                "connect_timeout": 10,
                "application_name": "ultimate_legal_ai_backend",
            }
        )
        logger.info("Database engine created successfully with production settings.")
        return engine
    except Exception as e:
        logger.exception("Failed to create database engine.", exc_info=e)
        raise

# Create the engine using the production-focused function
engine = create_production_engine()

# Create a sessionmaker
SessionLocal = sessionmaker(
    autocommit=False, 
    autoflush=False, 
    bind=engine,
    expire_on_commit=False # Good for background tasks where you might need the object after a commit
)
logger.info("Database session factory created.")

@contextmanager
def get_db() -> Generator[Session, None, None]:
    """
    Context manager to get a database session with robust error handling.
    """
    db = SessionLocal()
    try:
        yield db
    except Exception:
        logger.exception("A database session error occurred. Rolling back transaction.")
        db.rollback()
        raise
    finally:
        db.close()

def initialize_for_production():
    """
    Verifies the database connection on startup. Schema management is handled by Alembic.
    """
    logger.info("Verifying database connection for production workloads...")
    try:
        with engine.connect() as connection:
            logger.info("✅ Database connection successful. Schema management is handled by Alembic.")
    except Exception as e:
        logger.critical("🚨 CRITICAL: Could not connect to the database on startup.", exc_info=e)
        raise SystemExit(e)

