# app/scrapers/constitution_scraper.py
import asyncio
import logging
import httpx
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from app.scrapers.base_scraper import BaseScraper

logger = logging.getLogger(__name__)

class ConstitutionScraper(BaseScraper):
    """
    Asynchronously scrapes the Constitution of India from the india.gov.in portal.
    This version is rebuilt to be resilient to common HTML structure changes.
    """
    # Updated URL based on current search (Sep 2025)
    BASE_URL = "https://legislative.gov.in/constitution-of-india/"
    constitution_pdf_url = "https://legislative.gov.in/sites/default/files/constitution-of-india.pdf"  # Updated URL

    async def scrape(self):
        logger.info(f"Starting scrape for Constitution of India from {self.BASE_URL}")
        documents_to_process = []
        seen_urls = set()   # ✅ Track processed article URLs
        seen_titles = set() # ✅ Track processed titles (backup dedup)

        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            try:
                response = await self.fetch_with_retry(client, self.BASE_URL)
                if not response:
                    logger.error("Failed to fetch the main Constitution page. Aborting scrape.")
                    return

                soup = BeautifulSoup(response.text, "html.parser")
                
                # Robust content area detection
                content_selectors = [
                    "div.text-full-text",
                    ".content",
                    "main",
                    "#content"
                ]
                content_area = None
                for selector in content_selectors:
                    content_area = soup.select_one(selector)
                    if content_area:
                        break
                
                if not content_area:
                    logger.error("Could not locate the primary content area for the Constitution TOC.")
                    return

                # Find article links robustly
                article_links_selectors = [
                    "ul li a",
                    ".toc a",
                    "ol li a",
                    "div a[href*='article']"
                ]
                article_links = []
                for selector in article_links_selectors:
                    article_links = content_area.select(selector)
                    if article_links:
                        break

                logger.info(f"Found {len(article_links)} raw links. Filtering valid Constitution links...")

                # ✅ Filter links to remove junk (social, print, etc.)
                valid_links = []
                for link in article_links:
                    href = link.get("href")
                    if not href:
                        continue

                    href = href.lower()

                    # Must belong to Constitution of India pages
                    if "constitution-of-india" not in href:
                        continue

                    # Exclude junk/social links
                    if any(x in href for x in ["facebook", "twitter", "linkedin", "print", "sharer"]):
                        continue

                    # Only accept articles/schedules
                    if not any(x in href for x in ["article", "schedule"]):
                        continue

                    # ✅ Deduplicate links by absolute URL
                    abs_url = urljoin(self.BASE_URL, href)
                    if abs_url in seen_urls:
                        continue
                    seen_urls.add(abs_url)

                    valid_links.append(link)

                logger.info(f"Filtered down to {len(valid_links)} unique Constitution links.")

                for link in valid_links[:50]:  # Limit to first 50 for testing/efficiency
                    article_title = link.text.strip()
                    article_url = urljoin(self.BASE_URL, link.get('href'))

                    # ✅ Deduplicate by title as well (backup safety)
                    if article_title in seen_titles:
                        logger.debug(f"Skipping duplicate title: {article_title}")
                        continue
                    seen_titles.add(article_title)
                    
                    logger.debug(f"Fetching: {article_title}")
                    article_response = await self.fetch_with_retry(client, article_url)
                    if not article_response:
                        logger.warning(f"Skipping article due to fetch failure: {article_title}")
                        continue

                    article_soup = BeautifulSoup(article_response.text, "html.parser")
                    # Robust content div
                    content_div_selectors = [
                        "div.field-item.even",
                        ".content",
                        "article",
                        ".full-text"
                    ]
                    article_content_div = None
                    for selector in content_div_selectors:
                        article_content_div = article_soup.select_one(selector)
                        if article_content_div:
                            break
                    
                    if article_content_div:
                        raw_text = article_content_div.get_text(separator='\n', strip=True)
                        if len(raw_text) > 50:  # Basic quality check
                            doc_data = {
                                "title": f"Constitution of India - {article_title}",
                                "raw_text": raw_text,
                                "source_url": article_url,
                                "source": "Constitution of India",
                                "court": "Government of India",
                            }
                            documents_to_process.append(doc_data)
                    else:
                        logger.warning(f"No content div found for article: {article_title}")
            
            except Exception as e:
                logger.critical(f"A critical error occurred during the Constitution scrape: {e}", exc_info=True)

        if documents_to_process:
            logger.info(f"Submitting {len(documents_to_process)} Constitution articles for processing.")
            if self.processor:
                await self.processor.process_documents(documents_to_process, source_name="constitution")

        logger.info("Finished scraping the Constitution of India.")
