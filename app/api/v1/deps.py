from typing import Generator
from sqlalchemy.orm import Session
from app.db.base import get_db

# Dependency for database session
def get_database() -> Generator[Session, None, None]:
    """Database dependency"""
    return get_db()