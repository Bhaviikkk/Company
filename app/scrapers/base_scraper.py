# app/scrapers/base_scraper.py
import asyncio
import logging
import httpx
from typing import Optional, Dict
from datetime import datetime
import re

logger = logging.getLogger(__name__)

class BaseScraper:
    """
    Robust base scraper: exposes fetch_with_retry for async GET/POST requests,
    standard headers, rate limiting and exponential backoff.
    """
    def __init__(self, processor=None, rate_limit: float = 0.5):
        self.processor = processor
        self.rate_limit = rate_limit
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }

    async def _make_request(self, client: httpx.AsyncClient, method: str, url: str, **kwargs) -> Optional[httpx.Response]:
        await asyncio.sleep(self.rate_limit)
        for attempt in range(3):
            try:
                resp = await client.request(method, url, timeout=60.0, follow_redirects=True, headers=self.headers, **kwargs)
                resp.raise_for_status()
                logger.debug(f"Request OK: {method} {url} ({resp.status_code})")
                return resp
            except (httpx.HTTPStatusError, httpx.RequestError) as e:
                logger.warning(f"Request error ({attempt+1}/3) for {url}: {e}")
                if attempt < 2:
                    await asyncio.sleep(2 ** attempt * 3)
        logger.error(f"All retries failed for {url}")
        return None

    async def fetch_with_retry(self, client: httpx.AsyncClient, url: str, params: Optional[Dict] = None) -> Optional[httpx.Response]:
        return await self._make_request(client, "GET", url, params=params)

    async def post_with_retry(self, client: httpx.AsyncClient, url: str, json_data: Optional[Dict] = None, headers: Optional[Dict] = None) -> Optional[httpx.Response]:
        extra_headers = {}
        if headers:
            extra_headers.update(headers)
        return await self._make_request(client, "POST", url, json=json_data, headers=extra_headers)

    def _parse_date_from_text(self, text: str) -> Optional[str]:
        """Parse date from text string into ISO format."""
        if not text:
            return None
        # Expanded regex for more date formats common in legal docs
        patterns = re.findall(r'\b(\d{1,2}[-/]\d{1,2}[-/]\d{2,4}|\d{4}[-/]\d{1,2}[-/]\d{1,2}|\d{4}-\d{2}-\d{2})\b', text)
        for p in patterns:
            for fmt in ("%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%d", "%d-%m-%y", "%Y/%m/%d", "%m/%d/%Y"):
                try:
                    parsed = datetime.strptime(p, fmt)
                    return parsed.date().isoformat()
                except ValueError:
                    continue
        return None