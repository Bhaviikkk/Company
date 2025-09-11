import asyncio
import logging
import httpx
from urllib.parse import urljoin
from .base_scraper import BaseScraper
from app.core.config import settings

logger = logging.getLogger(__name__)

class JudgmentIngestor(BaseScraper):
    """Fetches high-value judgments from the Indian Kanoon API using targeted queries."""
    API_BASE_URL = "https://api.indiankanoon.org/"

    async def fetch_recent_judgments(self, client: httpx.AsyncClient, query: str, pages: int = 2):
        all_docs = []
        if not settings.indian_kanoon_api_token:
            logger.error("`INDIAN_KANOON_API_TOKEN` is not set. Aborting judgment ingestion.")
            return []

        auth_headers = {"Authorization": f"Token {settings.indian_kanoon_api_token}"}
        search_url = urljoin(self.API_BASE_URL, "search/")

        for page_num in range(pages):
            logger.info(f"Querying API for: '{query}' on page {page_num + 1}/{pages}")
            payload = {"formInput": query, "pagenum": page_num}
            
            response = await self.post_with_retry(client, search_url, json_data=payload, headers=auth_headers)
            
            if response and response.status_code == 200:
                data = response.json()
                docs = data.get('docs', [])
                if docs:
                    logger.info(f"Found {len(docs)} documents for query '{query}' on page {page_num + 1}.")
                    all_docs.extend(docs)
                else:
                    logger.info(f"No more documents found for '{query}'.")
                    break
            else:
                logger.error(f"Failed to fetch page {page_num + 1} for '{query}'.")
                break
        
        return all_docs

    async def scrape(self):
        logger.info("Starting API ingestion for foundational legal judgments.")
        documents_to_process = []
        # These more specific queries are guaranteed to return relevant results.
        judgment_queries = [
            "company law oppression mismanagement",
            "insolvency and bankruptcy code section 9",
            "SEBI insider trading"
        ]

        async with httpx.AsyncClient() as client:
            for query in judgment_queries:
                docs = await self.fetch_recent_judgments(client, query)
                for doc_data in docs:
                    documents_to_process.append({
                        "title": doc_data.get('title', query),
                        "raw_text": doc_data.get('fragment', ''),
                        "source_url": doc_data.get('url', ''),
                        "source": "Indian Kanoon API",
                        "court": doc_data.get('docfragment', 'Indian Judiciary'),
                        "decision_date": self._parse_date_from_text(doc_data.get('date', ''))
                    })

        if documents_to_process:
            logger.info(f"Successfully fetched a total of {len(documents_to_process)} judgments from the API.")
            await self.processor.process_documents(documents_to_process, source_name="JudgmentIngestor")
        else:
            logger.warning("No judgments were fetched from the API. Please check your queries and API token.")

        logger.info("✅ Finished judgment ingestion.")

