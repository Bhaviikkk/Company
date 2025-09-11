# app/scrapers/supreme_court_scraper.py
import asyncio
from typing import List, Dict, Optional
from datetime import datetime
import re
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import httpx
from app.scrapers.base_scraper import BaseScraper
import logging

logger = logging.getLogger(__name__)

class SupremeCourtScraper(BaseScraper):
    """
    Advanced scraper for Supreme Court of India judgments and orders.
    Focuses on company law and corporate governance decisions.
    """
    
    def __init__(self, processor=None):
        super().__init__(processor=processor, rate_limit=2.0)
        
        # Updated URLs based on current search (Sep 2025) - sci.gov.in is the main domain
        self.judgment_urls = [
            "https://main.sci.gov.in/judgments",  # Updated URL
            "https://main.sci.gov.in/orders"  # Updated URL
        ]
        
        # Company law keywords to filter relevant judgments
        self.company_law_keywords = [
            "companies act", "company secretary", "corporate governance",
            "board of directors", "shareholder", "merger", "acquisition",
            "insider trading", "securities law", "nclt", "nclat",
            "corporate insolvency", "winding up", "amalgamation"
        ]
    
    async def scrape_recent_judgments(self, days_back: int = 30) -> List[Dict]:
        """Scrape recent SC judgments focusing on company law"""
        logger.info(f"Starting SC judgment scrape for last {days_back} days")
        
        documents = []
        async with httpx.AsyncClient(timeout=60.0, verify=False) as client:
            for base_url in self.judgment_urls:
                try:
                    resp = await self.fetch_with_retry(client, base_url)
                    if resp:
                        content_type = resp.headers.get("content-type", "")
                        if 'text/html' in content_type:
                            html_content = resp.text  # Use .text for decoded
                            soup = BeautifulSoup(html_content, "html.parser")
                            
                            # Robust PDF extraction
                            pdf_links = soup.find_all("a", href=lambda h: h and h.lower().endswith(".pdf"))
                            page_docs = []
                            for a in pdf_links:
                                href = a.get("href")
                                full_url = urljoin(base_url, href)
                                title = a.get_text(strip=True) or "SC Judgment"
                                context = " ".join([p.get_text(strip=True) for p in a.parents if p.name in ['p', 'div', 'li']])[:200]
                                page_docs.append({
                                    "title": title,
                                    "url": full_url,
                                    "context": context,
                                })
                            
                            # Filter for company law
                            filtered_links = self._filter_company_law_documents(page_docs)
                            documents.extend(filtered_links)
                            
                            # Pagination discovery (simplified)
                            more_pages = self._discover_paginated_urls(soup, base_url)
                            for page_url in more_pages[:3]:  # Limit to 3 pages
                                page_resp = await self.fetch_with_retry(client, page_url)
                                if page_resp:
                                    page_soup = BeautifulSoup(page_resp.text, "html.parser")
                                    page_pdf_links = page_soup.find_all("a", href=lambda h: h and h.lower().endswith(".pdf"))
                                    for a in page_pdf_links:
                                        href = a.get("href")
                                        full_url = urljoin(page_url, href)
                                        title = a.get_text(strip=True) or "SC Judgment"
                                        context = " ".join([p.get_text(strip=True) for p in a.parents if p.name in ['p', 'div', 'li']])[:200]
                                        page_doc = {
                                            "title": title,
                                            "url": full_url,
                                            "context": context,
                                        }
                                        if self._is_relevant_to_company_law(page_doc):
                                            documents.append(page_doc)
                
                except Exception as e:
                    logger.error(f"Error scraping {base_url}: {e}")
                    continue
        
        # Dedup and enrich
        unique_docs = self._deduplicate_and_enrich(documents)
        
        logger.info(f"Found {len(unique_docs)} unique SC documents")
        return unique_docs
    
    def _filter_company_law_documents(self, pdf_links: List[Dict]) -> List[Dict]:
        """Filter documents that are relevant to company law"""
        filtered = []
        
        for doc in pdf_links:
            if self._is_relevant_to_company_law(doc):
                relevance_score = self._calculate_relevance_score(doc)
                doc['relevance_score'] = relevance_score
                doc['matched_keywords'] = self._get_matched_keywords(doc)
                doc['source'] = 'Supreme Court of India'
                filtered.append(doc)
        
        return filtered
    
    def _is_relevant_to_company_law(self, doc: Dict) -> bool:
        """Quick check for relevance"""
        combined_text = f"{doc.get('title', '').lower()} {doc.get('context', '').lower()}"
        for keyword in self.company_law_keywords:
            if keyword in combined_text:
                return True
        # Check for NCLT/NCLAT or company appeal
        if any(term in combined_text for term in ['nclt', 'nclat', 'company appeal']):
            return True
        return False
    
    def _calculate_relevance_score(self, doc: Dict) -> int:
        """Calculate relevance score"""
        score = 0
        combined_text = f"{doc.get('title', '').lower()} {doc.get('context', '').lower()}"
        for keyword in self.company_law_keywords:
            if keyword in combined_text:
                score += 1
        # Bonus for sections
        if re.search(r'section\s+\d+.*companies\s+act', combined_text):
            score += 2
        return score
    
    def _get_matched_keywords(self, doc: Dict) -> list:
        """Get matched keywords"""
        matched = []
        combined_text = f"{doc.get('title', '').lower()} {doc.get('context', '').lower()}"
        for keyword in self.company_law_keywords:
            if keyword in combined_text:
                matched.append(keyword)
        return matched
    
    def _discover_paginated_urls(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """Discover pagination URLs from the current page"""
        page_urls = set()
        
        # Common pagination selectors
        pagination_selectors = [
            'a[href*="page="]',
            'a[href*="offset="]', 
            'a[href*="start="]',
            '.pagination a',
            '.pager a',
            'a:contains("Next")',
            'a:contains(">")'
        ]
        
        for selector in pagination_selectors:
            links = soup.select(selector)
            for link in links[:5]:
                href = link.get('href')
                if href and 'page' in href.lower():
                    if not href.startswith('http'):
                        href = urljoin(base_url, href)
                    page_urls.add(href)
        
        return list(page_urls)
    
    def _deduplicate_and_enrich(self, documents: List[Dict]) -> List[Dict]:
        """Remove duplicates and add enhanced metadata"""
        seen_urls = set()
        unique_docs = []
        
        for doc in documents:
            url = doc['url']
            if url not in seen_urls:
                seen_urls.add(url)
                
                # Add metadata (simplified, no extra fetch for now)
                doc['jurisdiction'] = 'Supreme Court of India'
                doc['legal_system'] = 'Indian Law'
                doc['priority_score'] = self._calculate_priority_score(doc)
                
                unique_docs.append(doc)
        
        # Sort by priority and recency (if date available)
        unique_docs.sort(key=lambda x: x.get('priority_score', 0), reverse=True)
        
        return unique_docs
    
    def _calculate_priority_score(self, doc: Dict) -> int:
        """Calculate priority score for document processing order"""
        score = doc.get('relevance_score', 0) * 10
        
        # Bonus for high-value keywords
        high_value_keywords = ['merger', 'acquisition', 'corporate governance', 'insider trading']
        for keyword in high_value_keywords:
            if any(keyword in k for k in doc.get('matched_keywords', [])):
                score += 15
        
        # If date is available, bonus for recency (using current date Sep 11, 2025)
        decision_date = doc.get('decision_date')
        if decision_date:
            try:
                doc_date = datetime.fromisoformat(decision_date)
                current_date = datetime(2025, 9, 11)
                days_old = (current_date - doc_date).days
                if days_old < 30:
                    score += 20
                elif days_old < 90:
                    score += 10
                elif days_old < 365:
                    score += 5
            except:
                pass
        
        return score

    async def scrape(self):
        """Main scrape method for integration"""
        logger.info("Starting Supreme Court scrape")
        documents = await self.scrape_recent_judgments(days_back=90)
        if documents and self.processor:
            await self.processor.process_documents(documents, source_name="supreme_court")
        logger.info("Finished Supreme Court scrape")

    async def scrape_specific_case(self, case_number: str = None, year: int = None) -> List[Dict]:
        """Scrape specific case by number or year"""
        logger.info(f"Scraping specific case: {case_number}, year: {year}")
        # Placeholder: implement search form submission if needed
        return []