# Legal-AI Backend

## Overview
Production-ready FastAPI backend for Company Secretary research platform. The system focuses on:
- Robust data gathering from authenticated legal sources
- High-quality document processing and summarization using LangChain + Gemini
- Efficient search and retrieval capabilities
- Premium grade research responses for Company Secretaries

## Recent Changes (September 05, 2025)
- Initial project setup with complete FastAPI structure
- Implemented PostgreSQL database models for documents and summaries
- Created core services: parser, storage, search, and summarizer agent
- Built API endpoints for search, documents, and summaries
- Added background task processing with Celery
- Configured quality assurance and grounding validation

## Project Architecture
- **FastAPI backend** with async support
- **PostgreSQL database** for document and summary storage
- **Redis** for Celery task queue
- **LangChain + Gemini** for AI-powered summarization
- **S3-compatible storage** for PDF documents
- **Comprehensive QA system** for summary validation

## Key Features
- Document ingestion with duplicate detection
- Full-text search across legal documents
- AI-powered summarization with grounding validation
- Quality scoring and human review workflow
- RESTful API with proper error handling
- Background task processing for scalability

## User Preferences
- Production-ready code with proper error handling
- Focus on data quality and grounding validation
- Scalable architecture supporting high data volumes
- Company Secretary specific legal research features