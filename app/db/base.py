from sqlalchemy import create_engine
import logging
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

logger = logging.getLogger(__name__)

# Create database engine
engine = create_engine(settings.database_url)

# Create sessionmaker
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create base class for models
Base = declarative_base()

def init_db():
    """
    This is the function that was missing.
    It initializes the database and creates all tables defined in your models.
    This is the definitive solution to ensure your schema exists before ingestion.
    """
    try:
        logger.info("Initializing database schema... This will create all necessary tables.")
        # This line connects to the database and creates the tables.
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Database schema initialized successfully. Tables are now created.")
    except Exception as e:
        logger.critical(f"❌ Could not initialize the database schema. Error: {e}", exc_info=True)
        raise

def get_db():
    """Database dependency for FastAPI"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()