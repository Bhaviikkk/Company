# app/scrapers/companies_act_scraper.py
import logging
import httpx
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import re
from app.scrapers.base_scraper import BaseScraper

logger = logging.getLogger(__name__)

class CompaniesActScraper(BaseScraper):
    """
    Scrape Companies Act from a stable source (indiacode or PRS).
    This scraper finds links to individual sections and returns structured documents.
    """

    # Updated URLs based on current search (Sep 2025)
    BASE_URL = "https://www.indiacode.nic.in/bitstream/123456789/2114/5/A2013-18.pdf"  # fallback full pdf
    TOC_URL = "https://www.indiacode.nic.in/handle/123456789/2114/browse?type=act&level=2"  # Updated handle

    async def scrape(self):
        documents = []
        async with httpx.AsyncClient(timeout=60.0) as client:
            # Try the table-of-contents page first (html)
            resp = await self.fetch_with_retry(client, self.TOC_URL)
            if resp and resp.headers.get("content-type", "").lower().startswith("text"):
                soup = BeautifulSoup(resp.text, "html.parser")
                # Robust selectors: look for links in lists/tables with section-like text
                possible_selectors = [
                    "a[href*='section']",
                    "a[href*='chapter']",
                    "li a",
                    ".toc a",
                    ".content a"
                ]
                links = []
                for selector in possible_selectors:
                    links.extend(soup.select(selector))
                    if links:
                        break  # Use the first successful selector
                
                seen = set()
                for a in links:
                    href = a.get("href")
                    if not href:
                        continue
                    full = urljoin(self.TOC_URL, href)
                    text = a.get_text(strip=True)
                    # Improved heuristic: section links often contain 'Section', numbers, or 'Act'
                    text_lower = text.lower()
                    if (len(text) > 3 and full not in seen and 
                        ("section" in text_lower or "chapter" in text_lower or 
                         re.search(r'\d+[A-Z]?', text) or "act" in text_lower)):
                        seen.add(full)
                        documents.append({
                            "title": text,
                            "url": full,
                            "source": "Companies Act 2013",
                        })
            else:
                # fallback: the PDF link (download single PDF)
                logger.info("TOC page not parseable, falling back to direct PDF URL")
                documents.append({
                    "title": "Companies Act 2013 (full PDF)",
                    "url": self.BASE_URL,
                    "source": "Companies Act 2013",
                })

        logger.info(f"CompaniesActScraper: found {len(documents)} entries")
        # Process via processor
        if documents and self.processor:
            await self.processor.process_documents(documents, source_name="companies_act")
        return documents