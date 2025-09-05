import asyncio
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import re
from bs4 import BeautifulSoup
from .base_scraper import BaseLegalScraper
import logging

logger = logging.getLogger(__name__)

class NCLTNCLATScraper(BaseLegalScraper):
    """
    Advanced scraper for NCLT and NCLAT orders and judgments.
    Specializes in corporate insolvency, company law, and tribunal decisions.
    """
    
    def __init__(self):
        super().__init__(
            base_url="https://nclt.gov.in",
            rate_limit=1.5,
            respect_robots=True
        )
        
        # NCLT/NCLAT specific URLs
        self.nclt_urls = [
            "https://nclt.gov.in/orders-judgments",
            "https://nclt.gov.in/daily-cause-list",
            "https://nclt.gov.in/case-status"
        ]
        
        self.nclat_urls = [
            "https://nclat.nic.in/judgments",
            "https://nclat.nic.in/orders",
            "https://nclat.nic.in/daily-orders"
        ]
        
        # Company law specific keywords for NCLT/NCLAT
        self.tribunal_keywords = [
            "corporate insolvency", "resolution process", "liquidation",
            "moratorium", "resolution professional", "committee of creditors",
            "insolvency code", "stressed assets", "resolution plan",
            "winding up", "scheme of arrangement", "merger", "demerger",
            "oppression and mismanagement", "class action suit",
            "corporate debtor", "financial creditor", "operational creditor"
        ]
    
    async def scrape_recent_orders(self, days_back: int = 15, include_nclat: bool = True) -> List[Dict]:
        """Scrape recent NCLT and NCLAT orders"""
        logger.info(f"Starting NCLT/NCLAT scrape for last {days_back} days")
        
        documents = []
        
        # Scrape NCLT documents
        for base_url in self.nclt_urls:
            try:
                result = await self.fetch_with_retry(base_url)
                if result:
                    content_type, html_content = result
                    if 'text/html' in content_type:
                        pdf_links = await self.extract_pdf_links(
                            html_content.decode('utf-8', errors='ignore'), 
                            base_url
                        )
                        
                        # Add NCLT-specific processing
                        for doc in pdf_links:
                            doc['tribunal'] = 'NCLT'
                            doc['jurisdiction'] = 'National Company Law Tribunal'
                        
                        filtered_links = await self._filter_tribunal_documents(pdf_links)
                        documents.extend(filtered_links)
                
            except Exception as e:
                logger.error(f"Error scraping NCLT {base_url}: {e}")
                continue
        
        # Scrape NCLAT documents if requested
        if include_nclat:
            # Update base_url for NCLAT
            self.base_url = "https://nclat.nic.in"
            
            for base_url in self.nclat_urls:
                try:
                    result = await self.fetch_with_retry(base_url)
                    if result:
                        content_type, html_content = result
                        if 'text/html' in content_type:
                            pdf_links = await self.extract_pdf_links(
                                html_content.decode('utf-8', errors='ignore'), 
                                base_url
                            )
                            
                            # Add NCLAT-specific processing
                            for doc in pdf_links:
                                doc['tribunal'] = 'NCLAT'
                                doc['jurisdiction'] = 'National Company Law Appellate Tribunal'
                            
                            filtered_links = await self._filter_tribunal_documents(pdf_links)
                            documents.extend(filtered_links)
                    
                except Exception as e:
                    logger.error(f"Error scraping NCLAT {base_url}: {e}")
                    continue
        
        # Process and deduplicate
        unique_docs = await self._deduplicate_and_enrich_tribunal_docs(documents)
        
        logger.info(f"Found {len(unique_docs)} unique NCLT/NCLAT documents")
        return unique_docs
    
    async def _filter_tribunal_documents(self, pdf_links: List[Dict]) -> List[Dict]:
        """Filter documents relevant to corporate law and insolvency"""
        filtered = []
        
        for doc in pdf_links:
            title_lower = doc['title'].lower()
            context_lower = doc['context'].lower()
            combined_text = f"{title_lower} {context_lower}"
            
            relevance_score = 0
            matched_keywords = []
            category_tags = set()
            
            # Check for tribunal-specific keywords
            for keyword in self.tribunal_keywords:
                if keyword in combined_text:
                    relevance_score += 2  # Higher weight for tribunal keywords
                    matched_keywords.append(keyword)
                    
                    # Categorize based on keywords
                    if keyword in ["corporate insolvency", "resolution process", "liquidation"]:
                        category_tags.add("insolvency")
                    elif keyword in ["merger", "demerger", "scheme of arrangement"]:
                        category_tags.add("corporate_restructuring")
                    elif keyword in ["oppression and mismanagement", "class action"]:
                        category_tags.add("corporate_disputes")
            
            # Check for case number patterns (NCLT/NCLAT specific)
            case_patterns = [
                r'cp\s*\(ib\)\s*no\.?\s*\d+',  # Corporate insolvency cases
                r'ca\s*\(at\)\s*\(ins\)\s*no\.?\s*\d+',  # NCLAT appeals
                r'cp\s*no\.?\s*\d+',  # Company petition
                r'ma\s*no\.?\s*\d+'   # Miscellaneous application
            ]
            
            for pattern in case_patterns:
                if re.search(pattern, combined_text, re.IGNORECASE):
                    relevance_score += 3
                    category_tags.add("formal_case")
                    break
            
            # Include if relevant or if it contains formal case references
            if relevance_score > 0 or 'cp(' in combined_text or 'ca(' in combined_text:
                doc['relevance_score'] = relevance_score
                doc['matched_keywords'] = matched_keywords
                doc['category_tags'] = list(category_tags)
                doc['case_type'] = self._determine_case_type(combined_text)
                filtered.append(doc)
        
        return filtered
    
    def _determine_case_type(self, text: str) -> str:
        """Determine the type of case based on content"""
        text_lower = text.lower()
        
        if 'cp(ib)' in text_lower or 'corporate insolvency' in text_lower:
            return 'Corporate Insolvency Resolution Process'
        elif 'ca(at)' in text_lower:
            return 'NCLAT Appeal'
        elif 'winding up' in text_lower:
            return 'Winding Up Petition'
        elif 'merger' in text_lower or 'amalgamation' in text_lower:
            return 'Corporate Restructuring'
        elif 'oppression' in text_lower:
            return 'Oppression and Mismanagement'
        else:
            return 'General Corporate Matter'
    
    async def _deduplicate_and_enrich_tribunal_docs(self, documents: List[Dict]) -> List[Dict]:
        """Remove duplicates and add tribunal-specific metadata"""
        seen_urls = set()
        unique_docs = []
        
        for doc in documents:
            url = doc['url']
            if url not in seen_urls:
                seen_urls.add(url)
                
                # Add enhanced metadata
                metadata = await self.get_document_metadata(url)
                doc.update(metadata)
                
                # Add tribunal-specific metadata
                doc['legal_system'] = 'Indian Corporate Law'
                doc['document_type'] = 'Tribunal Order/Judgment'
                doc['priority_score'] = self._calculate_tribunal_priority_score(doc)
                doc['processing_complexity'] = self._assess_processing_complexity(doc)
                
                unique_docs.append(doc)
        
        # Sort by priority and complexity
        unique_docs.sort(
            key=lambda x: (
                x.get('priority_score', 0), 
                x.get('processing_complexity', 1),
                x.get('decision_date', '1900-01-01')
            ),
            reverse=True
        )
        
        return unique_docs
    
    def _calculate_tribunal_priority_score(self, doc: Dict) -> int:
        """Calculate priority score for tribunal documents"""
        score = doc.get('relevance_score', 0) * 8
        
        # High priority for insolvency cases (hot topic for CS professionals)
        if 'insolvency' in doc.get('category_tags', []):
            score += 30
        
        # Medium priority for corporate restructuring
        if 'corporate_restructuring' in doc.get('category_tags', []):
            score += 20
        
        # Bonus for recent cases
        if 'decision_date' in doc:
            try:
                doc_date = datetime.fromisoformat(doc['decision_date'])
                days_old = (datetime.now() - doc_date).days
                if days_old < 7:
                    score += 25
                elif days_old < 30:
                    score += 15
                elif days_old < 90:
                    score += 8
            except:
                pass
        
        # NCLAT cases typically more precedential
        if doc.get('tribunal') == 'NCLAT':
            score += 10
        
        return score
    
    def _assess_processing_complexity(self, doc: Dict) -> int:
        """Assess how complex this document will be to process (1-5 scale)"""
        complexity = 1
        
        # Insolvency cases tend to be complex
        if 'insolvency' in doc.get('category_tags', []):
            complexity += 2
        
        # Multiple keywords suggest complex cases
        keywords_count = len(doc.get('matched_keywords', []))
        if keywords_count > 3:
            complexity += 1
        
        # NCLAT appeals are typically more complex
        if doc.get('tribunal') == 'NCLAT':
            complexity += 1
        
        return min(complexity, 5)  # Cap at 5
    
    async def scrape_company_specific_cases(self, company_name: str) -> List[Dict]:
        """Scrape cases related to a specific company"""
        logger.info(f"Scraping cases for company: {company_name}")
        # Implementation for company-specific case scraping
        # This would search for cases involving a specific company
        return []