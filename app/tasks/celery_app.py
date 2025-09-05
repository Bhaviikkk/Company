from celery import Celery
from app.core.config import settings

# Create Celery app
celery_app = Celery(
    "legal_ai_tasks",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.tasks.ingestion", "app.tasks.summarise"]
)

# Configure Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_routes={
        "app.tasks.ingestion.*": {"queue": "ingestion"},
        "app.tasks.summarise.*": {"queue": "summarization"},
    }
)