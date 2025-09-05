import asyncio
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import re
from bs4 import BeautifulSoup
from .base_scraper import BaseLegalScraper
import logging

logger = logging.getLogger(__name__)

class SupremeCourtScraper(BaseLegalScraper):
    """
    Advanced scraper for Supreme Court of India judgments and orders.
    Focuses on company law and corporate governance decisions.
    """
    
    def __init__(self):
        super().__init__(
            base_url="https://main.sci.gov.in",
            rate_limit=2.0,  # Be respectful to official government sites
            respect_robots=True
        )
        
        # Supreme Court specific URLs for different types of documents
        self.judgment_urls = [
            "https://main.sci.gov.in/judgments",
            "https://main.sci.gov.in/case-status/case-status-search",
            "https://main.sci.gov.in/daily-orders"
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
        
        # Get judgment listing pages
        for base_url in self.judgment_urls:
            try:
                result = await self.fetch_with_retry(base_url)
                if result:
                    content_type, html_content = result
                    if 'text/html' in content_type:
                        pdf_links = await self.extract_pdf_links(
                            html_content.decode('utf-8', errors='ignore'), 
                            base_url
                        )
                        
                        # Filter for company law related documents
                        filtered_links = await self._filter_company_law_documents(pdf_links)
                        documents.extend(filtered_links)
                        
                        # Also look for paginated results
                        more_pages = await self._discover_paginated_urls(
                            html_content.decode('utf-8', errors='ignore'), 
                            base_url
                        )
                        
                        for page_url in more_pages[:5]:  # Limit to 5 additional pages
                            page_result = await self.fetch_with_retry(page_url)
                            if page_result:
                                _, page_html = page_result
                                page_pdfs = await self.extract_pdf_links(
                                    page_html.decode('utf-8', errors='ignore'),
                                    page_url
                                )
                                filtered_page_pdfs = await self._filter_company_law_documents(page_pdfs)
                                documents.extend(filtered_page_pdfs)
                
            except Exception as e:
                logger.error(f"Error scraping {base_url}: {e}")
                continue
        
        # Remove duplicates and add metadata
        unique_docs = await self._deduplicate_and_enrich(documents)
        
        logger.info(f"Found {len(unique_docs)} unique SC documents")
        return unique_docs
    
    async def _filter_company_law_documents(self, pdf_links: List[Dict]) -> List[Dict]:
        """Filter documents that are relevant to company law"""
        filtered = []
        
        for doc in pdf_links:
            title_lower = doc['title'].lower()
            context_lower = doc['context'].lower()
            combined_text = f"{title_lower} {context_lower}"
            
            # Check for company law keywords
            relevance_score = 0
            matched_keywords = []
            
            for keyword in self.company_law_keywords:
                if keyword in combined_text:
                    relevance_score += 1
                    matched_keywords.append(keyword)
            
            # Also check for specific section references
            companies_act_sections = re.findall(r'section\s+\d+.*companies\s+act', combined_text)
            if companies_act_sections:
                relevance_score += 2
                matched_keywords.extend(companies_act_sections)
            
            # Include if relevant (score > 0) or if it's from NCLT/NCLAT appeals
            if (relevance_score > 0 or 
                'nclt' in combined_text or 
                'nclat' in combined_text or
                'company appeal' in combined_text):
                
                doc['relevance_score'] = relevance_score
                doc['matched_keywords'] = matched_keywords
                doc['source'] = 'Supreme Court of India'
                filtered.append(doc)
        
        return filtered
    
    async def _discover_paginated_urls(self, html_content: str, base_url: str) -> List[str]:
        """Discover pagination URLs from the current page"""
        soup = BeautifulSoup(html_content, 'html.parser')
        page_urls = set()
        
        # Look for common pagination patterns
        pagination_selectors = [
            'a[href*="page="]',
            'a[href*="offset="]', 
            'a[href*="start="]',
            '.pagination a',
            '.pager a'
        ]
        
        for selector in pagination_selectors:
            links = soup.select(selector)
            for link in links[:10]:  # Limit pagination discovery
                href = link.get('href')
                if href:
                    if not href.startswith('http'):
                        href = f"{base_url.rstrip('/')}/{href.lstrip('/')}"
                    page_urls.add(href)
        
        return list(page_urls)
    
    async def _deduplicate_and_enrich(self, documents: List[Dict]) -> List[Dict]:
        """Remove duplicates and add enhanced metadata"""
        seen_urls = set()
        unique_docs = []
        
        for doc in documents:
            url = doc['url']
            if url not in seen_urls:
                seen_urls.add(url)
                
                # Add enhanced metadata
                metadata = await self.get_document_metadata(url)
                doc.update(metadata)
                
                # Add SC-specific metadata
                doc['jurisdiction'] = 'Supreme Court of India'
                doc['legal_system'] = 'Indian Law'
                doc['priority_score'] = self._calculate_priority_score(doc)
                
                unique_docs.append(doc)
        
        # Sort by priority score and recency
        unique_docs.sort(
            key=lambda x: (x.get('priority_score', 0), x.get('decision_date', '1900-01-01')),
            reverse=True
        )
        
        return unique_docs
    
    def _calculate_priority_score(self, doc: Dict) -> int:
        """Calculate priority score for document processing order"""
        score = doc.get('relevance_score', 0) * 10
        
        # Bonus for recent documents
        if 'decision_date' in doc:
            try:
                doc_date = datetime.fromisoformat(doc['decision_date'])
                days_old = (datetime.now() - doc_date).days
                if days_old < 30:
                    score += 20
                elif days_old < 90:
                    score += 10
                elif days_old < 365:
                    score += 5
            except:
                pass
        
        # Bonus for specific high-value keywords
        high_value_keywords = ['merger', 'acquisition', 'corporate governance', 'insider trading']
        for keyword in high_value_keywords:
            if any(keyword in k for k in doc.get('matched_keywords', [])):
                score += 15
        
        return score

    async def scrape_specific_case(self, case_number: str = None, year: int = None) -> List[Dict]:
        """Scrape specific case by number or year"""
        # Implementation for targeted case scraping
        logger.info(f"Scraping specific case: {case_number}, year: {year}")
        # This would implement specific case search functionality
        return []