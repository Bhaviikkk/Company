from celery import Celery
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

# Create Celery instance with production configuration  
celery_app = Celery(
    "legal-ai-backend",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.tasks.ingestion", "app.tasks.summarise"]
)

# Production Celery configuration
celery_app.conf.update(
    # Task routing
    task_routes={
        'app.tasks.ingestion.*': {'queue': 'ingestion'},
        'app.tasks.summarise.*': {'queue': 'summarization'},
    },
    # Task execution
    task_serializer='json',
    result_serializer='json', 
    accept_content=['json'],
    result_expires=3600,
    timezone='UTC',
    enable_utc=True,
    # Worker configuration
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    worker_disable_rate_limits=False,
    # Monitoring
    worker_send_task_events=True,
    task_send_sent_event=True,
    # Reliability
    task_reject_on_worker_lost=True,
    task_acks_on_failure_or_timeout=True,
)