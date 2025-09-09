from app.core.celery_app import celery_app
from app.agents.agent_orchestrator import AgentOrchestrator
import asyncio
import logging

logger = logging.getLogger(__name__)

@celery_app.task(name="tasks.run_premium_analysis")
def run_premium_analysis(document_text: str, user_query: str, workflow_type: str) -> dict:
    """
    Celery task to run the multi-agent analysis asynchronously.
    """
    logger.info(f"Starting Celery task: run_premium_analysis for workflow {workflow_type}")
    orchestrator = AgentOrchestrator()
    # Use asyncio.run to execute the async orchestrator in the sync Celery worker
    result = asyncio.run(orchestrator.analyze_document(
        document_text=document_text, user_query=user_query, workflow_type=workflow_type))
    logger.info(f"Completed Celery task: run_premium_analysis")
    return result