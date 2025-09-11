"""
Celery worker entry point.

This file initializes the Celery application, configures it with the broker (Redis)
and result backend from the application's settings, and discovers the tasks
to be executed.

To run the worker, use the following command from the project root:
celery -A worker.celery worker --loglevel=info
"""

import logging
from celery import Celery
from app.core.config import settings
import eventlet
eventlet.monkey_patch()

# Set up logging for the worker
logger = logging.getLogger(__name__)

# --- Create the Celery Application Instance ---
# The first argument is the name of the current module, which is standard practice.
# The `broker` and `backend` are configured using the REDIS_URL from your .env file.
# The `include` argument is a list of modules where your tasks are defined. Celery
# will automatically discover any @celery.task decorators in these files.
celery = Celery(
    "tasks",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.tasks.ingestion", "app.tasks.summarise"]
)

# Optional configuration to improve task tracking
celery.conf.update(
    task_track_started=True,
    broker_connection_retry_on_startup=True,
)

logger.info(f"Celery worker initialized with broker: {settings.redis_url}")
