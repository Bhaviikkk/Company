from sqlalchemy import Column, String, Date, Text, DateTime, ForeignKey, func, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.db.base import Base
import uuid

class Document(Base):
    """Document model for storing legal documents"""
    __tablename__ = "documents"
    
    document_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String, nullable=False)
    court = Column(String)
    decision_date = Column(Date)
    url = Column(String)
    storage_path = Column(String)
    content_hash = Column(String, unique=True, index=True)
    raw_text = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    summaries = relationship("Summary", back_populates="document")

class Summary(Base):
    """Summary model for storing AI-generated summaries"""
    __tablename__ = "summaries"
    
    summary_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.document_id"), nullable=False)
    style = Column(String, default="cs_student")  # cs_student | research | advocate
    model_id = Column(String)
    prompt_version = Column(String)
    summary_short = Column(Text)
    summary_detailed = Column(Text)
    span_citations = Column(JSONB)
    quality_score = Column(String)
    human_status = Column(String, default="pending")  # pending | approved | rejected
    grounding_score = Column(String)
    citation_score = Column(String)
    consistency_score = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    document = relationship("Document", back_populates="summaries")

class ProcessingTask(Base):
    """Task tracking for background processing"""
    __tablename__ = "processing_tasks"
    
    task_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.document_id"))
    task_type = Column(String, nullable=False)  # ingestion | summarization | qa
    status = Column(String, default="pending")  # pending | running | completed | failed
    error_message = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())