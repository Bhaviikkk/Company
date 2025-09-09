import asyncio
import aiohttp
import logging
from typing import List, Dict, Optional, Tuple
from urllib.parse import urljoin
from bs4 import BeautifulSoup
import re
from datetime import datetime

logger = logging.getLogger(__name__)

class BaseLegalScraper:
    """Base class for production-grade legal document scrapers."""

    def __init__(self, base_url: str, rate_limit: float = 1.0, respect_robots: bool = True):
        self.base_url = base_url
        self.rate_limit = rate_limit
        self.respect_robots = respect_robots
        self.session = None
        # In a real implementation, you would parse robots.txt here.

    async def __aenter__(self):
        self.session = aiohttp.ClientSession(headers={'User-Agent': 'LegalAISearchBot/1.0'})
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def fetch_with_retry(self, url: str, retries: int = 3, delay: float = 5.0) -> Optional[Tuple[str, bytes]]:
        """Fetch a URL with retries and rate limiting."""
        await asyncio.sleep(self.rate_limit)
        for attempt in range(retries):
            try:
                async with self.session.get(url, timeout=30) as response:
                    response.raise_for_status()
                    content_type = response.headers.get('Content-Type', '')
                    content = await response.read()
                    logger.info(f"Successfully fetched {url} (Status: {response.status})")
                    return content_type, content
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                logger.warning(f"Attempt {attempt + 1}/{retries} failed for {url}: {e}")
                if attempt < retries - 1:
                    await asyncio.sleep(delay * (attempt + 1))
        logger.error(f"Failed to fetch {url} after {retries} retries.")
        return None

    async def extract_pdf_links(self, html_content: str, page_url: str) -> List[Dict]:
        """Extract PDF links and associated metadata from HTML content."""
        soup = BeautifulSoup(html_content, 'html.parser')
        links = []
        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href']
            if '.pdf' in href.lower():
                full_url = urljoin(page_url, href)
                title = a_tag.get_text(strip=True) or "Untitled PDF"
                parent_text = a_tag.find_parent().get_text(separator=' ', strip=True)
                date_match = re.search(r'(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})', parent_text)
                decision_date = self._parse_date_from_text(parent_text)
                links.append({"url": full_url, "title": title, "context": parent_text[:500], "decision_date": decision_date, "source_page": page_url})
        return links

    async def get_document_metadata(self, url: str) -> Dict:
        """Placeholder for getting more detailed metadata for a document."""
        return {"retrieved_at": datetime.now().isoformat()}

    def _parse_date_from_text(self, text: str) -> Optional[str]:
        """Extracts and parses a date from a string, trying multiple formats."""
        date_formats = ['%d-%m-%Y', '%d/%m/%Y', '%Y-%m-%d', '%d-%m-%y', '%d/%m/%y']
        # Regex to find potential date strings
        date_patterns = re.findall(r'\b\d{1,2}[-/]\d{1,2}[-/]\d{2,4}\b', text)
        for date_str in date_patterns:
            for fmt in date_formats:
                try:
                    # Try parsing the original date string with each format for correctness
                    return datetime.strptime(date_str, fmt).date().isoformat()
                except ValueError:
                    # If it fails, move to the next format
                    continue
        return None