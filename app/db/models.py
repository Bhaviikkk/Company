# In file: app/db/models.py

import uuid
from sqlalchemy import Column, String, DateTime, Text, Index, func, Date
from sqlalchemy.dialects.postgresql import UUID
from .base import Base

class Document(Base):
    __tablename__ = 'documents'
    document_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # Adding index=True for standard, fast lookups on title
    title = Column(String(500), nullable=False, index=True)
    court = Column(String(200))
    decision_date = Column(Date)
    created_at = Column(DateTime, default=func.now())
    source_url = Column(String(1024), unique=True, nullable=True) # URLs can be null for non-web sources
    content_hash = Column(String(64), unique=True, index=True)
    raw_text = Column(Text, nullable=False)
    source = Column(String(100))
    storage_path = Column(String(1024), nullable=True)

class Company(Base):
    __tablename__ = 'companies'
    cin = Column(String(21), primary_key=True)
    # Using a standard B-Tree index, which is robust and universally supported
    company_name = Column(String(255), nullable=False, index=True)
    date_of_registration = Column(Date)
    company_status = Column(String(100))
    registered_address = Column(Text)
    created_at = Column(DateTime, default=func.now())