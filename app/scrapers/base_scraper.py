import asyncio
import aiohttp
import logging
from urllib.robotparser import RobotFileParser
from urllib.parse import urljoin, urlparse
from typing import List, Dict, Optional, Tuple
import time
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import hashlib

logger = logging.getLogger(__name__)

class BaseLegalScraper:
    """
    Base class for legal document scrapers with robots.txt compliance,
    rate limiting, and intelligent retry mechanisms.
    """
    
    def __init__(self, base_url: str, rate_limit: float = 1.0, respect_robots: bool = True):
        self.base_url = base_url
        self.rate_limit = rate_limit  # seconds between requests
        self.respect_robots = respect_robots
        self.session = None
        self.robots_parser = None
        self.last_request_time = 0
        self.failed_urls = set()
        
        # Headers to appear like a legitimate browser
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
    
    async def __aenter__(self):
        """Async context manager entry"""
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()
    
    async def initialize(self):
        """Initialize session and robots.txt parser"""
        connector = aiohttp.TCPConnector(limit=10, limit_per_host=3)
        timeout = aiohttp.ClientTimeout(total=30, connect=10)
        
        self.session = aiohttp.ClientSession(
            headers=self.headers,
            connector=connector,
            timeout=timeout
        )
        
        if self.respect_robots:
            await self._load_robots_txt()
    
    async def close(self):
        """Close the session"""
        if self.session:
            await self.session.close()
    
    async def _load_robots_txt(self):
        """Load and parse robots.txt"""
        try:
            robots_url = urljoin(self.base_url, '/robots.txt')
            async with self.session.get(robots_url) as response:
                if response.status == 200:
                    robots_content = await response.text()
                    self.robots_parser = RobotFileParser()
                    self.robots_parser.set_url(robots_url)
                    self.robots_parser.can_fetch_text = robots_content
                    self.robots_parser.read()
                    logger.info(f"Loaded robots.txt from {robots_url}")
                else:
                    logger.warning(f"Could not load robots.txt from {robots_url}")
        except Exception as e:
            logger.warning(f"Error loading robots.txt: {e}")
    
    def can_fetch_url(self, url: str) -> bool:
        """Check if URL can be fetched according to robots.txt"""
        if not self.respect_robots or not self.robots_parser:
            return True
        
        return self.robots_parser.can_fetch(self.headers['User-Agent'], url)
    
    async def _rate_limit(self):
        """Implement rate limiting"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.rate_limit:
            sleep_time = self.rate_limit - time_since_last
            await asyncio.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    async def fetch_with_retry(self, url: str, max_retries: int = 3) -> Optional[Tuple[str, bytes]]:
        """
        Fetch URL with intelligent retry mechanism.
        Returns: (content_type, content) or None if failed
        """
        if url in self.failed_urls:
            return None
        
        if not self.can_fetch_url(url):
            logger.warning(f"Robots.txt disallows fetching: {url}")
            return None
        
        await self._rate_limit()
        
        for attempt in range(max_retries):
            try:
                async with self.session.get(url) as response:
                    if response.status == 200:
                        content = await response.read()
                        content_type = response.headers.get('content-type', '').lower()
                        logger.info(f"Successfully fetched: {url}")
                        return content_type, content
                    elif response.status == 429:  # Too Many Requests
                        retry_after = int(response.headers.get('Retry-After', 60))
                        logger.warning(f"Rate limited, waiting {retry_after}s before retry")
                        await asyncio.sleep(retry_after)
                    elif response.status in [403, 404]:
                        logger.warning(f"URL not accessible: {url} (Status: {response.status})")
                        self.failed_urls.add(url)
                        return None
                    else:
                        logger.warning(f"HTTP {response.status} for {url}")
                        
            except asyncio.TimeoutError:
                logger.warning(f"Timeout for {url} (attempt {attempt + 1})")
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
            except Exception as e:
                logger.error(f"Error fetching {url}: {e} (attempt {attempt + 1})")
                await asyncio.sleep(2 ** attempt)
        
        logger.error(f"Failed to fetch after {max_retries} attempts: {url}")
        self.failed_urls.add(url)
        return None
    
    def generate_content_hash(self, content: bytes) -> str:
        """Generate SHA256 hash for content deduplication"""
        return hashlib.sha256(content).hexdigest()
    
    async def extract_pdf_links(self, html_content: str, base_url: str) -> List[Dict[str, str]]:
        """Extract PDF links from HTML content"""
        soup = BeautifulSoup(html_content, 'html.parser')
        pdf_links = []
        
        # Find all links that might lead to PDFs
        for link in soup.find_all('a', href=True):
            href = link['href']
            
            # Handle relative URLs
            if not href.startswith('http'):
                href = urljoin(base_url, href)
            
            # Check if link is likely a PDF
            if (href.lower().endswith('.pdf') or 
                'pdf' in href.lower() or 
                'judgment' in href.lower() or
                'order' in href.lower()):
                
                # Extract metadata from link text and surrounding context
                title = link.get_text(strip=True) or 'Unknown Document'
                
                # Try to get more context from parent elements
                parent_text = ''
                for parent in link.parents:
                    if parent.name in ['p', 'div', 'li', 'td']:
                        parent_text = parent.get_text(strip=True)[:200]
                        break
                
                pdf_links.append({
                    'url': href,
                    'title': title,
                    'context': parent_text,
                    'extracted_from': base_url
                })
        
        return pdf_links
    
    async def get_document_metadata(self, url: str, content: str = None) -> Dict[str, str]:
        """Extract metadata from document URL and content"""
        metadata = {
            'url': url,
            'domain': urlparse(url).netloc,
            'extracted_date': datetime.now().isoformat()
        }
        
        # Extract metadata from URL patterns
        url_lower = url.lower()
        
        if 'supremecourt' in url_lower or 'sci.gov.in' in url_lower:
            metadata['court'] = 'Supreme Court of India'
            metadata['source_type'] = 'SC'
        elif 'nclt' in url_lower:
            metadata['court'] = 'National Company Law Tribunal'
            metadata['source_type'] = 'NCLT'
        elif 'nclat' in url_lower:
            metadata['court'] = 'National Company Law Appellate Tribunal'
            metadata['source_type'] = 'NCLAT'
        
        # Try to extract date from URL
        import re
        date_patterns = [
            r'(\d{4})[/-](\d{1,2})[/-](\d{1,2})',
            r'(\d{1,2})[/-](\d{1,2})[/-](\d{4})',
            r'(\d{4})(\d{2})(\d{2})'
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, url)
            if match:
                try:
                    if len(match.group(1)) == 4:  # YYYY-MM-DD format
                        year, month, day = match.groups()
                    else:  # DD-MM-YYYY format
                        day, month, year = match.groups()
                    
                    date_obj = datetime(int(year), int(month), int(day))
                    metadata['decision_date'] = date_obj.date().isoformat()
                    break
                except (ValueError, TypeError):
                    continue
        
        return metadata