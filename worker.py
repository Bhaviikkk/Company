#!/usr/bin/env python3
"""
Production Celery Worker Entry Point
Runs background tasks independently from the API server
"""
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.tasks.celery_app import celery_app

if __name__ == '__main__':
    celery_app.start()