# app/scrapers/nclt_nclat_scraper.py
import logging
import httpx
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from typing import List, Dict
from app.scrapers.base_scraper import BaseScraper

logger = logging.getLogger(__name__)

class NCLTNCLATScraper(BaseScraper):
    def __init__(self, processor=None):
        super().__init__(processor=processor, rate_limit=0.8)
        # Updated URLs based on current search (Sep 2025)
        self.nclt_urls = [
            "https://nclt.gov.in/order-date-wise-search",
            "https://nclt.gov.in/order-judgement-date-wise-search"
        ]

        self.nclat_urls = [
            "https://nclat.nic.in/display-board/judge",
            "https://nclat.nic.in/daily-order-data"
        ]

    async def scrape_recent(self, include_nclat=True) -> List[Dict]:
        documents = []
        async with httpx.AsyncClient(timeout=60.0) as client:
            for url in self.nclt_urls:
                resp = await self.fetch_with_retry(client, url)
                if not resp:
                    continue
                soup = BeautifulSoup(resp.text, "html.parser")
                # Robust PDF link extraction
                pdf_links = soup.find_all("a", href=lambda h: h and h.lower().endswith(".pdf"))
                for a in pdf_links:
                    href = a.get("href")
                    full = urljoin(url, href)
                    title = a.get_text(strip=True) or "NCLT Document"
                    documents.append({"title": title, "url": full, "tribunal": "NCLT"})
            
            if include_nclat:
                for url in self.nclat_urls:
                    resp = await self.fetch_with_retry(client, url)
                    if not resp:
                        continue
                    soup = BeautifulSoup(resp.text, "html.parser")
                    pdf_links = soup.find_all("a", href=lambda h: h and h.lower().endswith(".pdf"))
                    for a in pdf_links:
                        href = a.get("href")
                        full = urljoin(url, href)
                        title = a.get_text(strip=True) or "NCLAT Document"
                        documents.append({"title": title, "url": full, "tribunal": "NCLAT"})
        
        # Dedupe by URL
        unique = {d["url"]: d for d in documents}
        logger.info(f"NCLT/NCLAT: found {len(unique)} unique PDFs")
        return list(unique.values())

    async def scrape(self):
        documents = await self.scrape_recent(include_nclat=True)
        if documents and self.processor:
            await self.processor.process_documents(documents, source_name="nclt_nclat")